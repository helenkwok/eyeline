"""Eyeline — Pillar 3: Google Cloud Veo Generative Cutaway Pickup Pipeline.

Generates 4-8 second contextual B-roll insert shots via the Google Veo 3.1 API
(google-genai SDK) and burns a mandatory SYNTHETIC CONTINUITY INSERT watermark
badge onto every frame using classical OpenCV.

Rule 7.B Compliance:
  Video generation ONLY via google-genai / Google Cloud Veo on Vertex AI.
  No third-party neural models are introduced here.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    _GENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_DURATIONS = (4, 6, 8)
_DEFAULT_WATERMARK = "SYNTHETIC CONTINUITY INSERT * VEO 3.1"
_DEFAULT_MODEL = "veo-3.1-generate-preview"
_DEFAULT_OUT = "ui/assets/veo_pickup.mp4"

# Watermark visual parameters
_WM_FONT = cv2.FONT_HERSHEY_DUPLEX
_WM_SCALE = 0.55
_WM_THICKNESS = 1
_WM_BG_COLOR = (0, 0, 0)         # black box
_WM_TEXT_COLOR = (255, 255, 255)  # white text
_WM_ALPHA = 0.72                  # badge opacity
_WM_PADDING = (6, 10)            # (vertical, horizontal) px


# ---------------------------------------------------------------------------
# Watermark helper
# ---------------------------------------------------------------------------

def _burn_watermark(frame_bgr: np.ndarray, watermark: str) -> np.ndarray:
    """Overlay a semi-transparent watermark badge in the bottom-left corner."""
    frame = frame_bgr.copy()
    h, w = frame.shape[:2]

    (tw, th), baseline = cv2.getTextSize(watermark, _WM_FONT, _WM_SCALE, _WM_THICKNESS)
    pad_y, pad_x = _WM_PADDING

    box_x0 = 10
    box_y0 = h - (th + baseline + 2 * pad_y + 10)
    box_x1 = box_x0 + tw + 2 * pad_x
    box_y1 = box_y0 + th + baseline + 2 * pad_y

    # Clamp to frame boundaries
    box_x0 = max(0, box_x0)
    box_y0 = max(0, box_y0)
    box_x1 = min(w, box_x1)
    box_y1 = min(h, box_y1)

    # Semi-transparent badge background
    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x0, box_y0), (box_x1, box_y1), _WM_BG_COLOR, -1)
    cv2.addWeighted(overlay, _WM_ALPHA, frame, 1.0 - _WM_ALPHA, 0, frame)

    # Crisp text on top
    text_x = box_x0 + pad_x
    text_y = box_y1 - pad_y - baseline
    cv2.putText(frame, watermark, (text_x, text_y),
                _WM_FONT, _WM_SCALE, _WM_TEXT_COLOR, _WM_THICKNESS, cv2.LINE_AA)
    return frame


def _stamp_watermark_onto_video(src_path: str, dst_path: str, watermark: str) -> None:
    """Read *src_path*, stamp every frame with *watermark*, write H.264 to *dst_path*."""
    cap = cv2.VideoCapture(src_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video for watermarking: {src_path!r}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"avc1")  # H.264
    out = cv2.VideoWriter(dst_path, fourcc, fps, (width, height))
    if not out.isOpened():
        cap.release()
        # Fallback codec on Linux / some macOS builds
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(dst_path, fourcc, fps, (width, height))
        if not out.isOpened():
            cap.release()
            raise RuntimeError(
                f"VideoWriter failed to open {dst_path!r}. "
                "Ensure ffmpeg/avc1 support is present in opencv-python-headless."
            )

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            stamped = _burn_watermark(frame, watermark)
            out.write(stamped)
    finally:
        cap.release()
        out.release()


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download_video_bytes(uri: str, api_key: str) -> bytes:
    """Fetch video bytes from *uri* using API key or bearer credential."""
    import urllib.request  # stdlib — no extra dependency
    headers = {}
    if api_key:
        headers["x-goog-api-key"] = api_key
        if not api_key.startswith("AIza"):
            headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(uri, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_veo_insert(
    prompt: str,
    duration_sec: int = 4,
    out_path: str = _DEFAULT_OUT,
    watermark: str = _DEFAULT_WATERMARK,
    client=None,
    model: str = _DEFAULT_MODEL,
) -> dict:
    """Generate a Veo 3.1 contextual B-roll insert and burn in the disclosure watermark.

    Args:
        prompt:       Text description of the B-roll insert shot.
        duration_sec: Video duration — must be one of (4, 6, 8) seconds (Veo API constraint).
        out_path:     Output path for the watermarked H.264 MP4.
        watermark:    Text burned into every frame as the mandatory disclosure badge.
        client:       Pre-constructed ``genai.Client``. Constructed from env if None.
        model:        Veo model identifier on Vertex AI / AI Studio.

    Returns:
        dict with keys: status, model, duration_sec, file, watermark, prompt.

    Raises:
        ValueError:   If duration_sec is not in (4, 6, 8).
        RuntimeError: If google-genai is not installed, API key is missing, or
                      video generation/download fails.
    """
    # --- Validate duration ---------------------------------------------------
    if duration_sec not in _VALID_DURATIONS:
        raise ValueError(
            f"duration_sec must be one of {_VALID_DURATIONS}; got {duration_sec!r}."
        )

    # --- SDK availability ----------------------------------------------------
    if not _GENAI_AVAILABLE:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        )

    # --- Resolve API key & client --------------------------------------------
    api_key = (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    )
    if client is None:
        if not api_key:
            raise RuntimeError(
                "No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY "
                "in the environment before calling generate_veo_insert."
            )
        try:
            client = genai.Client()
        except (ValueError, Exception) as exc:
            raise RuntimeError(
                f"Failed to initialize Gemini/Veo client: {exc}. "
                "Ensure GEMINI_API_KEY or GOOGLE_API_KEY is set."
            ) from exc

    # --- Dispatch video generation -------------------------------------------
    operation = client.models.generate_videos(
        model=model,
        source=types.GenerateVideosSource(prompt=prompt),
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=duration_sec,
        ),
    )

    # --- Poll until done (with exponential back-off) -------------------------
    poll_interval = 5  # seconds
    max_wait = 600     # 10 minutes ceiling
    elapsed = 0
    while not operation.done:
        time.sleep(poll_interval)
        elapsed += poll_interval
        operation = client.operations.get(operation)
        if elapsed >= max_wait:
            raise RuntimeError(
                f"Veo generation timed out after {max_wait}s for prompt: {prompt!r}"
            )
        # Progressive back-off capped at 30 s
        poll_interval = min(poll_interval * 2, 30)

    # --- Extract video URI ---------------------------------------------------
    try:
        video_uri = operation.response.generated_videos[0].video.uri
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected Veo API response structure: {exc}. "
            f"Full response: {operation.response!r}"
        ) from exc

    # --- Download video bytes ------------------------------------------------
    raw_bytes = _download_video_bytes(video_uri, api_key)

    # Write raw bytes to a temp file so OpenCV can process it
    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = str(Path(out_path).with_suffix(".tmp.mp4"))
    try:
        Path(tmp_path).write_bytes(raw_bytes)

        # --- Burn watermark onto every frame ---------------------------------
        _stamp_watermark_onto_video(tmp_path, str(out_path), watermark)
    finally:
        # Remove temp file regardless of success/failure
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "status": "success",
        "model": model,
        "duration_sec": duration_sec,
        "file": str(out_path),
        "watermark": watermark,
        "prompt": prompt,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m eyeline.veo",
        description=(
            "Pillar 3 — Veo 3.1 Generative Cutaway Pickup Pipeline.\n\n"
            "Generates a contextual B-roll insert shot via Google Cloud Veo 3.1,\n"
            "downloads the resulting media, and burns the mandatory disclosure\n"
            "watermark ('SYNTHETIC CONTINUITY INSERT * VEO 3.1') onto every frame."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables:\n"
            "  GEMINI_API_KEY   API key for Google AI Studio / Vertex AI\n"
            "  GOOGLE_API_KEY   Alias accepted if GEMINI_API_KEY is absent\n\n"
            "Examples:\n"
            "  python3 -m eyeline.veo \\\n"
            "    --prompt 'Extreme close-up of a coffee mug on a diner counter, steady shot' \\\n"
            "    --duration 4 --output ui/assets/veo_pickup.mp4\n"
        ),
    )
    parser.add_argument(
        "--prompt",
        default="Close-up insert shot of a film set prop on a neutral surface, cinematic lighting",
        help="Text description of the B-roll shot to generate (default: generic prop insert).",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=4,
        choices=_VALID_DURATIONS,
        metavar="{4,6,8}",
        help="Video duration in seconds. Veo API accepts 4, 6, or 8 (default: 4).",
    )
    parser.add_argument(
        "--output",
        default=_DEFAULT_OUT,
        metavar="PATH",
        help=f"Output path for the watermarked H.264 MP4 (default: {_DEFAULT_OUT}).",
    )
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help=f"Veo model identifier (default: {_DEFAULT_MODEL}).",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    try:
        result = generate_veo_insert(
            prompt=args.prompt,
            duration_sec=args.duration,
            out_path=args.output,
            model=args.model,
        )
        print(f"[veo] status     : {result['status']}")
        print(f"[veo] model      : {result['model']}")
        print(f"[veo] duration   : {result['duration_sec']}s")
        print(f"[veo] output     : {result['file']}")
        print(f"[veo] watermark  : {result['watermark']}")
        print(f"[veo] prompt     : {result['prompt']}")
        sys.exit(0)
    except (ValueError, RuntimeError) as exc:
        print(f"[veo] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
