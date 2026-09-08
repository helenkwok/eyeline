"""Eyeline — Pillar 1: Deterministic Alignment & Candidate Region Generator.

Classical CV pipeline (opencv-python-headless, scikit-image, numpy only).

Rule 7.B Compliance:
  PERMITTED  : cv2, skimage, numpy
  PROHIBITED : Any neural object detector or segmentation model
               (no YOLO / Ultralytics, SAM, GroundingDINO, MobileNet, Torch)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from skimage.exposure import match_histograms


# ---------------------------------------------------------------------------
# 1. Frame extraction
# ---------------------------------------------------------------------------

def extract_frame_at_timestamp(
    video_path: str,
    timestamp_sec: float,
) -> Optional[np.ndarray]:
    """Extract a single BGR frame from *video_path* at *timestamp_sec*.

    Returns the BGR ndarray on success, or None if the file cannot be opened
    or the requested position is past the end of the stream.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        target_frame = int(round(timestamp_sec * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ret, frame = cap.read()
        return frame if ret else None
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# 2. Exposure / histogram normalization
# ---------------------------------------------------------------------------

def match_exposure_histogram(
    source: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """Normalize *source* luminance/color to match *reference* histogram.

    Operates in YCrCb space: matches only the Y (luminance) channel to avoid
    introducing colour cast while correcting for exposure differences between
    takes shot under varying lighting conditions.

    Returns a uint8 BGR image with the same spatial dimensions as *source*.
    """
    # Work in YCrCb so chrominance is untouched
    src_ycrcb = cv2.cvtColor(source, cv2.COLOR_BGR2YCrCb)
    ref_ycrcb = cv2.cvtColor(reference, cv2.COLOR_BGR2YCrCb)

    # match_histograms expects float or uint8; channel_axis selects Y only
    matched_y = match_histograms(
        src_ycrcb[:, :, 0].astype(np.float32),
        ref_ycrcb[:, :, 0].astype(np.float32),
    ).astype(np.uint8)

    result_ycrcb = src_ycrcb.copy()
    result_ycrcb[:, :, 0] = matched_y
    return cv2.cvtColor(result_ycrcb, cv2.COLOR_YCrCb2BGR)


# ---------------------------------------------------------------------------
# 3. Perspective alignment via homography
# ---------------------------------------------------------------------------

def align_frames_homography(
    source: np.ndarray,
    reference: np.ndarray,
) -> Tuple[np.ndarray, Optional[np.ndarray], float]:
    """Align *source* to *reference* using ORB feature matching + RANSAC homography.

    Accounts for slight camera repositioning between setups (pan/tilt wobble,
    operator position drift) without invoking any neural model.

    Returns:
        aligned_frame    : *source* warped onto *reference* perspective (BGR uint8).
        homography       : 3×3 float64 matrix, or None if alignment failed (< 8 matches).
        alignment_error  : Mean reprojection error of inlier correspondences (pixels),
                           or 0.0 when alignment is skipped due to insufficient matches.
    """
    gray_src = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    gray_ref = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

    # ORB: permissive Apache-2.0 / BSD-3 — no patent concerns in OpenCV headless
    orb = cv2.ORB_create(nfeatures=2000)
    kp_src, des_src = orb.detectAndCompute(gray_src, None)
    kp_ref, des_ref = orb.detectAndCompute(gray_ref, None)

    if des_src is None or des_ref is None or len(kp_src) < 8 or len(kp_ref) < 8:
        return source.copy(), None, 0.0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw_matches = matcher.knnMatch(des_src, des_ref, k=2)

    # Lowe ratio test
    good: list = []
    for pair in raw_matches:
        if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance:
            good.append(pair[0])

    if len(good) < 8:
        return source.copy(), None, 0.0

    pts_src = np.float32([kp_src[m.queryIdx].pt for m in good])
    pts_ref = np.float32([kp_ref[m.trainIdx].pt for m in good])

    H, mask = cv2.findHomography(pts_src, pts_ref, cv2.RANSAC, ransacReprojThreshold=4.0)
    if H is None:
        return source.copy(), None, 0.0

    h, w = reference.shape[:2]
    aligned = cv2.warpPerspective(source, H, (w, h))

    # Compute mean reprojection error on inliers
    inlier_mask = mask.ravel().astype(bool)
    if inlier_mask.sum() > 0:
        pts_proj = cv2.perspectiveTransform(pts_src[inlier_mask].reshape(-1, 1, 2), H).reshape(-1, 2)
        error = float(np.mean(np.linalg.norm(pts_proj - pts_ref[inlier_mask], axis=1)))
    else:
        error = 0.0

    return aligned, H, error


# ---------------------------------------------------------------------------
# 4. Spatial difference mask
# ---------------------------------------------------------------------------

def compute_spatial_difference_mask(
    aligned_frame: np.ndarray,
    reference_frame: np.ndarray,
    threshold: int = 30,
) -> np.ndarray:
    """Compute a binary mask of significant luminance differences between frames.

    Processing steps:
      1. Convert both frames to grayscale.
      2. Absolute luminance difference.
      3. Gaussian blur (5×5) to suppress high-frequency sensor noise.
      4. Binary threshold at *threshold* (0–255).
      5. Morphological closing (11×11 kernel) to fill small holes.
      6. Morphological opening (5×5 kernel) to discard isolated speckle noise.

    Returns a uint8 binary mask (0 or 255) with the same H×W as inputs.
    """
    gray_aligned = cv2.cvtColor(aligned_frame, cv2.COLOR_BGR2GRAY)
    gray_ref = cv2.cvtColor(reference_frame, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray_aligned, gray_ref)

    # Suppress sensor noise with a small Gaussian blur before thresholding
    blurred = cv2.GaussianBlur(diff, (5, 5), sigmaX=1.5)

    _, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY)

    # Morphological close: join nearby activated pixels (prop regions tend to be contiguous)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

    # Morphological open: remove tiny isolated speckles (sensor noise survivors)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, open_kernel)

    return cleaned


# ---------------------------------------------------------------------------
# 5. Candidate bounding box extraction
# ---------------------------------------------------------------------------

def extract_candidate_bounding_boxes(
    diff_mask: np.ndarray,
    min_area_ratio: float = 0.002,
    max_area_ratio: float = 0.45,
) -> List[List[float]]:
    """Extract normalized bounding boxes from *diff_mask* contours.

    Boxes are expressed in [ymin, xmin, ymax, xmax] normalized to [0.0, 1.0]
    per the Eyeline coordinate convention (top-left = (0.0, 0.0)).

    Contour areas outside [min_area_ratio, max_area_ratio] × total frame area
    are discarded:
      - Below min: sensor speckle and sub-pixel edge ringing.
      - Above max: global camera movement masquerading as a prop change.
    """
    h, w = diff_mask.shape[:2]
    total_area = float(h * w)

    contours, _ = cv2.findContours(
        diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes: List[List[float]] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        ratio = area / total_area
        if ratio < min_area_ratio or ratio > max_area_ratio:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        ymin = float(y) / h
        xmin = float(x) / w
        ymax = float(y + bh) / h
        xmax = float(x + bw) / w

        # Clamp to [0, 1] for safety (warpPerspective edge artefacts)
        boxes.append([
            max(0.0, min(1.0, ymin)),
            max(0.0, min(1.0, xmin)),
            max(0.0, min(1.0, ymax)),
            max(0.0, min(1.0, xmax)),
        ])

    return boxes


# ---------------------------------------------------------------------------
# 6. High-level pipeline
# ---------------------------------------------------------------------------

def inspect_take_pair(
    ref_path: str,
    cur_path: str,
    timestamp_sec: float = 0.0,
    diff_threshold: int = 30,
    min_area_ratio: float = 0.002,
    max_area_ratio: float = 0.45,
) -> Dict[str, Any]:
    """Run the full Pillar-1 pipeline on a reference/current take pair.

    Loads both frames, aligns perspective, normalizes exposure, computes
    the difference mask, and returns candidate bounding boxes alongside
    latency telemetry.

    Args:
        ref_path        : Path to reference take video (or image file).
        cur_path        : Path to current take video (or image file).
        timestamp_sec   : Position in seconds to sample from each video.
        diff_threshold  : Luminance delta threshold (0–255).
        min_area_ratio  : Minimum contour area fraction to retain.
        max_area_ratio  : Maximum contour area fraction to retain.

    Returns a dict with keys:
        ref_path, cur_path, timestamp_sec,
        frame_shape [H, W],
        alignment_error (pixels),
        homography_available (bool),
        candidate_bounding_boxes [[ymin, xmin, ymax, xmax], ...],
        latency_ms (total wall-clock time),
        error (str | None)
    """
    t0 = time.perf_counter()

    # --- load frames --------------------------------------------------------
    def _load(path: str) -> Optional[np.ndarray]:
        # Try as image first (synthetic test frames / JPEG / PNG)
        frame = cv2.imread(path)
        if frame is not None:
            return frame
        # Fall back to video extraction
        return extract_frame_at_timestamp(path, timestamp_sec)

    ref_frame = _load(ref_path)
    cur_frame = _load(cur_path)

    if ref_frame is None or cur_frame is None:
        return {
            "ref_path": ref_path,
            "cur_path": cur_path,
            "timestamp_sec": timestamp_sec,
            "error": "Failed to load one or both frames.",
            "candidate_bounding_boxes": [],
            "latency_ms": (time.perf_counter() - t0) * 1000,
        }

    # Resize current to reference dimensions if they differ
    if cur_frame.shape[:2] != ref_frame.shape[:2]:
        cur_frame = cv2.resize(cur_frame, (ref_frame.shape[1], ref_frame.shape[0]))

    # --- pipeline -----------------------------------------------------------
    # Step A: Exposure normalization (match current → reference histogram)
    cur_matched = match_exposure_histogram(cur_frame, ref_frame)

    # Step B: Perspective alignment
    aligned, homography, alignment_error = align_frames_homography(cur_matched, ref_frame)

    # Step C: Difference mask
    diff_mask = compute_spatial_difference_mask(aligned, ref_frame, threshold=diff_threshold)

    # Step D: Candidate boxes
    boxes = extract_candidate_bounding_boxes(
        diff_mask,
        min_area_ratio=min_area_ratio,
        max_area_ratio=max_area_ratio,
    )

    latency_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "ref_path": ref_path,
        "cur_path": cur_path,
        "timestamp_sec": timestamp_sec,
        "frame_shape": list(ref_frame.shape[:2]),
        "alignment_error": round(alignment_error, 3),
        "homography_available": homography is not None,
        "candidate_bounding_boxes": boxes,
        "latency_ms": round(latency_ms, 1),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Standalone self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, os, json

    print("=" * 60)
    print("Eyeline vision.py — Pillar-1 self-test")
    print("Synthetic prop-shift: small rectangle moved in lower-right quadrant")
    print("=" * 60)

    # Build two 480×640 BGR frames that are identical except for a 60×80
    # prop-shaped white rectangle that shifts by ~100 px horizontally.
    H, W = 480, 640
    base = np.full((H, W, 3), 80, dtype=np.uint8)          # mid-grey background

    ref_frame = base.copy()
    cv2.rectangle(ref_frame, (380, 300), (460, 380), (220, 220, 220), -1)  # prop @ left pos

    cur_frame = base.copy()
    cv2.rectangle(cur_frame, (490, 300), (570, 380), (220, 220, 220), -1)  # prop @ right pos (shifted)

    # Persist as PNG so inspect_take_pair can load them via cv2.imread
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_path = os.path.join(tmpdir, "ref_frame.png")
        cur_path = os.path.join(tmpdir, "cur_frame.png")
        cv2.imwrite(ref_path, ref_frame)
        cv2.imwrite(cur_path, cur_frame)

        result = inspect_take_pair(ref_path, cur_path)

    print(json.dumps(result, indent=2))

    # Validate output contract
    boxes = result["candidate_bounding_boxes"]
    assert result["error"] is None, f"Pipeline error: {result['error']}"
    assert len(boxes) >= 1, "Expected at least one candidate bounding box; got none."

    for box in boxes:
        assert len(box) == 4, f"Box must have 4 values [ymin,xmin,ymax,xmax]; got {box}"
        ymin, xmin, ymax, xmax = box
        for v in (ymin, xmin, ymax, xmax):
            assert 0.0 <= v <= 1.0, f"Coordinate {v} out of [0.0, 1.0] range in {box}"
        assert ymin < ymax, f"ymin >= ymax in {box}"
        assert xmin < xmax, f"xmin >= xmax in {box}"

    print()
    print(f"✓  {len(boxes)} candidate box(es) detected, all in normalized [ymin,xmin,ymax,xmax]")
    print(f"✓  Latency: {result['latency_ms']} ms")
    print(f"✓  Alignment error: {result['alignment_error']} px")
    print("All assertions passed — Pillar-1 pipeline operational.")
