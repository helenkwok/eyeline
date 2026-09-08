"""Eyeline — Pillar 2: Multimodal Continuity Adjudication via Gemini.

Takes candidate regions flagged by Pillar-1 classical CV and asks Gemini 3.8
Flash to distinguish intentional cinematic variations (camera angle, focal
length, lighting mood, actor performance nuance) from genuine continuity
defects (prop displacement, wardrobe, blocking, hair/makeup, set dressing).

Rule 7.B Compliance:
  AI inference ONLY via google-genai (Gemini on Google Cloud / Vertex AI).
  No third-party neural object detectors permitted.
"""

from __future__ import annotations

import io
import os
from typing import Optional

import cv2
import numpy as np
from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    genai_types = None  # type: ignore
    _GENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------


class ContinuityAdjudication(BaseModel):
    """Structured adjudication verdict from Gemini multimodal inference."""

    is_continuity_defect: bool = Field(
        description=(
            "True if the delta between reference and target is a genuine "
            "continuity defect (prop, wardrobe, blocking, etc.). "
            "False if it is an intentional cinematic variation (camera angle, "
            "focal length, lighting grade, actor performance nuance)."
        )
    )
    category: str = Field(
        description=(
            "Exactly one of: 'prop_state', 'prop_position', 'wardrobe', "
            "'blocking', 'hair_makeup', 'set_dressing', 'eyeline_axis', "
            "or 'intentional_variation'."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Calibrated confidence score in [0.0, 1.0].",
    )
    reasoning: str = Field(
        description=(
            "Concise technical explanation referencing specific visual "
            "landmarks observed in the frame patches."
        )
    )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_ADJUDICATION_PROMPT = """\
You are a script supervisor's AI copilot reviewing two frames from a film shoot.
Your task is to determine whether a visual delta between the reference frame and
the target frame constitutes a GENUINE CONTINUITY DEFECT or an INTENTIONAL
CINEMATIC VARIATION.

CRITICAL DISCRIMINATIVE PRINCIPLE:
1. GLOBAL VS LOCAL:
   - If the difference involves a global camera rotation, pan, tilt, perspective shift, focal length / zoom change, or global exposure/color grading across the entire frame, this is an INTENTIONAL CINEMATIC VARIATION (set is_continuity_defect=False, category='intentional_variation').
   - Legitimate continuity defects are LOCALIZED to an isolated element (e.g. a specific prop moved while the table stays stationary, a liquid level jumped, a jacket unbuttoned, an actor posture changed while background stays identical).
   - If candidate bounding boxes arise because the camera moved or the lens zoomed, do NOT flag them as blocking or prop defects.

INTENTIONAL VARIATIONS (must NOT be flagged as defects — set is_continuity_defect=False, category='intentional_variation'):
- Camera angle, pan, tilt, or position change
- Focal length, lens, or zoom change
- Deliberate lighting grade change or exposure dim
- Natural actor performance nuance (subtle mouth/eye dialogue timing)
- Color grade, saturation, or LUT change

GENUINE CONTINUITY DEFECTS (MUST be flagged — set is_continuity_defect=True):
- prop_state: Object consumption or fill level jumped impossibly within a scene beat (e.g. cup refilled).
- prop_position: An isolated prop physically moved to a different spot while the rest of the scene remains consistent.
- wardrobe: Garment inconsistency (collar flipped, jacket unbuttoned, watch absent, apron strap fallen).
- blocking: Actor physically seated vs standing, or positioned at a different mark with stationary camera/background.
- hair_makeup: Hair part changed, prosthetic/wound lighter or absent, makeup smudge inconsistency.
- set_dressing: Background dressing changed — artwork erased, prop added/removed from the wall/table without scripted reason.
- eyeline_axis: 180-degree rule violated — actor gazes in opposite screen direction.

Respond with valid JSON matching the ContinuityAdjudication schema exactly.
Be conservative: prefer 'intentional_variation' when shifts are consistent with camera movement or global changes.
""".strip()


# ---------------------------------------------------------------------------
# Frame helpers
# ---------------------------------------------------------------------------


def _extract_frame(video_path: str, timestamp_sec: float) -> Optional[np.ndarray]:
    """Return a BGR frame from *video_path* at *timestamp_sec*, or None on failure."""
    # Try direct image load first (synthetic PNGs / JPEGs used in tests)
    frame = cv2.imread(video_path)
    if frame is not None:
        return frame

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(timestamp_sec * fps)))
        ret, frame = cap.read()
        return frame if ret else None
    finally:
        cap.release()


def _bgr_to_jpeg_bytes(bgr: np.ndarray, max_dim: int = 768) -> bytes:
    """Resize *bgr* so the longest dimension ≤ *max_dim* and encode as JPEG bytes."""
    h, w = bgr.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return bytes(buf)


def _crop_patch(frame: np.ndarray, bbox: list[float], margin: float = 0.15) -> np.ndarray:
    """Crop *frame* to *bbox* (normalized [ymin, xmin, ymax, xmax]) plus *margin*."""
    h, w = frame.shape[:2]
    ymin, xmin, ymax, xmax = bbox
    dy = (ymax - ymin) * margin
    dx = (xmax - xmin) * margin
    y0 = max(0.0, ymin - dy)
    x0 = max(0.0, xmin - dx)
    y1 = min(1.0, ymax + dy)
    x1 = min(1.0, xmax + dx)
    r0, c0 = int(y0 * h), int(x0 * w)
    r1, c1 = int(y1 * h), int(x1 * w)
    r1, c1 = max(r1, r0 + 1), max(c1, c0 + 1)  # guarantee non-empty
    return frame[r0:r1, c0:c1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def adjudicate_pair_delta(
    ref_clip_path: str,
    tgt_clip_path: str,
    timestamp_sec: float,
    bounding_box: Optional[list[float]] = None,
    template_id: str = "",
    client=None,
    model: str = "gemini-3.8-flash",
) -> ContinuityAdjudication:
    """Adjudicate whether the delta between a reference and target clip frame is a
    genuine continuity defect or an intentional cinematic variation.

    Args:
        ref_clip_path:  Path to reference take video (or image file for tests).
        tgt_clip_path:  Path to target take video (or image file for tests).
        timestamp_sec:  Frame position to sample from each clip.
        bounding_box:   Optional candidate region from Pillar-1, normalized
                        [ymin, xmin, ymax, xmax].  Cropped patches are sent
                        alongside the full frames when provided.
        template_id:    Scene template label for contextual framing.
        client:         Pre-constructed ``genai.Client`` (injected for tests /
                        shared sessions).  Constructed from env if None.
        model:          Gemini model name to call.

    Returns:
        ContinuityAdjudication with verdict, category, confidence, and reasoning.

    Raises:
        RuntimeError: When no API key is available in the environment (both
                      GEMINI_API_KEY and GOOGLE_API_KEY are absent).
    """
    # --- Check credentials before loading heavy frames ----------------------
    if not _GENAI_AVAILABLE:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        )

    if client is None:
        has_key = bool(
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )
        if not has_key:
            raise RuntimeError(
                "No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY "
                "in the environment before calling adjudicate_pair_delta."
            )
        try:
            client = genai.Client()
        except ValueError as exc:
            raise RuntimeError(
                f"Failed to initialize Gemini client: {exc}. "
                "Ensure GEMINI_API_KEY or GOOGLE_API_KEY is set."
            ) from exc

    # --- Extract frames ------------------------------------------------------
    ref_frame = _extract_frame(ref_clip_path, timestamp_sec)
    tgt_frame = _extract_frame(tgt_clip_path, timestamp_sec)

    if ref_frame is None or tgt_frame is None:
        missing = []
        if ref_frame is None:
            missing.append(f"reference ({ref_clip_path!r})")
        if tgt_frame is None:
            missing.append(f"target ({tgt_clip_path!r})")
        raise RuntimeError(f"Could not extract frame from: {', '.join(missing)}")

    # Normalise dimensions
    if tgt_frame.shape[:2] != ref_frame.shape[:2]:
        tgt_frame = cv2.resize(tgt_frame, (ref_frame.shape[1], ref_frame.shape[0]))

    # --- Build image parts ---------------------------------------------------
    context_note = (
        f" Scene template: {template_id}." if template_id else ""
    )
    prompt_text = _ADJUDICATION_PROMPT + context_note

    parts: list = [prompt_text]

    # Full frames
    parts.append(genai_types.Part.from_bytes(
        data=_bgr_to_jpeg_bytes(ref_frame),
        mime_type="image/jpeg",
    ))
    parts.append("Reference frame (above). Target frame (below):")
    parts.append(genai_types.Part.from_bytes(
        data=_bgr_to_jpeg_bytes(tgt_frame),
        mime_type="image/jpeg",
    ))

    # Cropped patches — helps Gemini focus on the flagged region
    if bounding_box and len(bounding_box) == 4:
        ref_crop = _crop_patch(ref_frame, bounding_box)
        tgt_crop = _crop_patch(tgt_frame, bounding_box)
        parts.append("Close-up crop of the candidate region — reference (above):")
        parts.append(genai_types.Part.from_bytes(
            data=_bgr_to_jpeg_bytes(ref_crop, max_dim=512),
            mime_type="image/jpeg",
        ))
        parts.append("Close-up crop of the candidate region — target (above):")
        parts.append(genai_types.Part.from_bytes(
            data=_bgr_to_jpeg_bytes(tgt_crop, max_dim=512),
            mime_type="image/jpeg",
        ))

    # --- Call Gemini ---------------------------------------------------------
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ContinuityAdjudication,
        ),
    )

    return ContinuityAdjudication.model_validate_json(response.text)
