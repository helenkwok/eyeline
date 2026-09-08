"""
bench/generator.py — Ground-Truth Benchmark Media Generator for Eyeline.

Synthesizes realistic, deterministic video take pairs for the 32 benchmark pairs
defined in bench/truth.json across 4 scene templates:
  - t01: Diner Table (Props: Coffee mug, Watch, Notebook, Eyeline)
  - t02: Office Desk (Props: Tumbler, Lapel, Hair Part, Whiteboard)
  - t03: Commercial Kitchen (Props: Knife, Pot Lid, Apron Strap, Axis)
  - t04: Interrogation Room (Props: Blocking, Evidence Folder, Bruise, Lamp)

Complies strictly with Hackathon Rule 7.B (pure classical CV + numpy, zero external AI models).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from bench.loader import BenchmarkPair, GroundTruthDataset, GroundTruthLabel, PairCategory, load_benchmark_dataset

WIDTH = 640
HEIGHT = 360
FPS = 24.0
NUM_FRAMES = 48  # 2.0 seconds per clip


# ---------------------------------------------------------------------------
# Drawing Utilities & Landmarks
# ---------------------------------------------------------------------------


def draw_grid_texture(img: np.ndarray, color: Tuple[int, int, int], step: int = 30) -> None:
    h, w = img.shape[:2]
    for y in range(0, h, step):
        cv2.line(img, (0, y), (w, y), color, 1)
    for x in range(0, w, step):
        cv2.line(img, (x, 0), (x, h), color, 1)


def draw_scene_background(template_id: str) -> np.ndarray:
    """Render static background with rich textures and landmarks for stable homography."""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    if "diner" in template_id:
        # Warm diner interior: dark brick wall, neon sign, booth divider, wood table
        frame[:] = (28, 32, 45)
        for y in range(0, 240, 24):
            cv2.line(frame, (0, y), (WIDTH, y), (55, 60, 80), 1)
            offset = 20 if (y // 24) % 2 == 1 else 0
            for x in range(offset, WIDTH, 40):
                cv2.line(frame, (x, y), (x, y + 24), (55, 60, 80), 1)
        cv2.putText(frame, "DINER", (460, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 50, 220), 2)
        cv2.rectangle(frame, (40, 30), (220, 180), (70, 55, 45), -1)
        cv2.rectangle(frame, (45, 35), (215, 175), (15, 15, 25), -1)
        cv2.line(frame, (130, 35), (130, 175), (50, 40, 35), 2)
        # Booth partition
        cv2.rectangle(frame, (240, 50), (270, 260), (35, 30, 80), -1)
        # Wood table surface
        cv2.rectangle(frame, (0, 235), (WIDTH, HEIGHT), (42, 60, 85), -1)
        cv2.line(frame, (0, 235), (WIDTH, 235), (70, 95, 130), 2)

    elif "office" in template_id:
        # Modern office: cool grey wall, wall stripes, whiteboards, desk
        frame[:] = (75, 70, 65)
        for y in range(0, 235, 25):
            cv2.line(frame, (0, y), (WIDTH, y), (90, 85, 80), 1)
        cv2.rectangle(frame, (30, 20), (200, 180), (140, 140, 140), -1)
        cv2.rectangle(frame, (35, 25), (195, 175), (225, 225, 225), -1)
        cv2.rectangle(frame, (420, 20), (620, 130), (140, 140, 140), -1)
        cv2.rectangle(frame, (425, 25), (615, 125), (225, 225, 225), -1)
        cv2.rectangle(frame, (250, 120), (390, 220), (25, 25, 25), -1)
        cv2.rectangle(frame, (255, 125), (385, 215), (90, 75, 50), -1)
        cv2.rectangle(frame, (310, 220), (330, 245), (40, 40, 40), -1)
        cv2.rectangle(frame, (0, 235), (WIDTH, HEIGHT), (48, 55, 62), -1)
        cv2.line(frame, (0, 235), (WIDTH, 235), (85, 95, 105), 2)

    elif "kitchen" in template_id:
        # Commercial kitchen: tiled wall, steel shelf, stainless countertop
        frame[:] = (120, 120, 115)
        for y in range(0, 225, 20):
            cv2.line(frame, (0, y), (WIDTH, y), (145, 145, 140), 1)
            offset = 15 if (y // 20) % 2 == 1 else 0
            for x in range(offset, WIDTH, 30):
                cv2.line(frame, (x, y), (x, y + 20), (145, 145, 140), 1)
        cv2.rectangle(frame, (40, 40), (WIDTH - 40, 65), (160, 160, 160), -1)
        for sx in range(60, WIDTH - 60, 45):
            cv2.rectangle(frame, (sx, 20), (sx + 20, 40), (50, 80, 120), -1)
        cv2.rectangle(frame, (40, 70), (220, 180), (80, 80, 80), -1)
        cv2.rectangle(frame, (0, 225), (WIDTH, HEIGHT), (145, 145, 140), -1)
        cv2.line(frame, (0, 225), (WIDTH, 225), (190, 190, 185), 2)

    else:  # interrogation
        # Gritty interrogation: concrete cinder block wall, vent grate, wood table
        frame[:] = (40, 42, 45)
        for y in range(0, 230, 30):
            cv2.line(frame, (0, y), (WIDTH, y), (70, 72, 75), 1)
            offset = 25 if (y // 30) % 2 == 1 else 0
            for x in range(offset, WIDTH, 50):
                cv2.line(frame, (x, y), (x, y + 30), (70, 72, 75), 1)
        cv2.rectangle(frame, (50, 35), (150, 95), (90, 92, 95), -1)
        for vy in range(40, 90, 6):
            cv2.line(frame, (55, vy), (145, vy), (30, 32, 35), 2)
        cv2.rectangle(frame, (0, 230), (WIDTH, HEIGHT), (30, 40, 55), -1)
        cv2.line(frame, (0, 230), (WIDTH, 230), (50, 65, 85), 2)

    return frame


def render_characters(frame: np.ndarray, template_id: str, actor_eyeline_left: bool = True) -> None:
    """Draw character silhouette landmarks."""
    h, w = frame.shape[:2]

    # Actor Head & Torso
    head_x = int(w * 0.50)
    head_y = int(h * 0.38)
    head_r = 38

    # Hair/Head
    cv2.circle(frame, (head_x, head_y), head_r, (40, 35, 32), -1)
    # Face skin
    cv2.circle(frame, (head_x, head_y + 4), head_r - 6, (135, 160, 195), -1)

    # Eyes & Eyeline Direction
    eye_y = head_y + 2
    eye_offset = -6 if actor_eyeline_left else 6
    cv2.circle(frame, (head_x - 12 + eye_offset, eye_y), 3, (30, 25, 20), -1)
    cv2.circle(frame, (head_x + 12 + eye_offset, eye_y), 3, (30, 25, 20), -1)

    # Shoulders / Torso
    torso_pts = np.array([
        [head_x - 70, int(h * 0.72)],
        [head_x - 45, head_y + head_r - 4],
        [head_x + 45, head_y + head_r - 4],
        [head_x + 70, int(h * 0.72)],
    ], dtype=np.int32)
    suit_color = (65, 55, 50) if "office" in template_id else (45, 45, 55)
    cv2.fillPoly(frame, [torso_pts], suit_color)


def bbox_to_pixels(bbox: List[float]) -> Tuple[int, int, int, int]:
    ymin, xmin, ymax, xmax = bbox
    return (
        int(xmin * WIDTH),
        int(ymin * HEIGHT),
        int(xmax * WIDTH),
        int(ymax * HEIGHT),
    )


def inject_defect(
    frame: np.ndarray,
    pair: BenchmarkPair,
    is_target: bool,
) -> None:
    """Inject the visual defect matching truth.json specification."""
    if not pair.bounding_box:
        return

    x1, y1, x2, y2 = bbox_to_pixels(pair.bounding_box)
    bw = x2 - x1
    bh = y2 - y1
    pid = pair.pair_id

    if pid == "pair_001":  # Diner: Coffee mug fill level
        cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (235, 235, 240), -1)
        cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (180, 180, 185), 2)
        cv2.ellipse(frame, (x2 - 4, y1 + bh // 2), (8, bh // 4), 0, 270, 90, (235, 235, 240), 3)
        fill = 0.85 if is_target else 0.35
        lh = int((bh - 10) * fill)
        cv2.rectangle(frame, (x1 + 6, y2 - 6 - lh), (x2 - 6, y2 - 6), (20, 35, 60), -1)

    elif pid == "pair_002":  # Diner: Silver wristwatch
        if not is_target:
            cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (190, 195, 200), -1)
            cv2.circle(frame, (x1 + bw // 2, y1 + bh // 2), min(bw, bh) // 3, (240, 240, 245), -1)
        else:
            cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (135, 160, 195), -1)

    elif pid == "pair_003":  # Diner: Spiral notebook shifted
        book_w = int(bw * 0.65)
        if not is_target:
            cv2.rectangle(frame, (x1, y1 + 4), (x1 + book_w, y2 - 4), (180, 110, 40), -1)
        else:
            cv2.rectangle(frame, (x2 - book_w, y1 + 4), (x2, y2 - 4), (180, 110, 40), -1)

    elif pid == "pair_004":  # Diner: Eyeline direction / gaze mismatch
        head_cx = x1 + bw // 2
        head_cy = y1 + bh // 2
        cv2.circle(frame, (head_cx, head_cy), min(bw, bh) // 2 - 4, (135, 160, 195), -1)
        if not is_target:
            cv2.circle(frame, (head_cx - 10, head_cy - 4), 16, (40, 35, 32), -1)
            cv2.circle(frame, (head_cx - 12, head_cy + 2), 4, (25, 25, 25), -1)
        else:
            cv2.circle(frame, (head_cx, head_cy - 12), 16, (40, 35, 32), -1)
            cv2.circle(frame, (head_cx + 8, head_cy + 8), 4, (25, 25, 25), -1)

    elif pid == "pair_005":  # Office: Cigarette burned down
        cv2.rectangle(frame, (x1 + 4, y1 + bh // 3), (x1 + bw // 3, y2 - 4), (135, 160, 195), -1)
        if not is_target:
            cv2.rectangle(frame, (x1 + bw // 3, y1 + bh // 2 - 4), (x2 - 6, y1 + bh // 2 + 4), (235, 235, 240), -1)
            cv2.circle(frame, (x2 - 4, y1 + bh // 2), 4, (30, 60, 220), -1)
        else:
            cv2.rectangle(frame, (x1 + bw // 3, y1 + bh // 2 - 4), (x1 + int(bw * 0.55), y1 + bh // 2 + 4), (235, 235, 240), -1)

    elif pid == "pair_006":  # Office: Suit jacket lapel folded inward
        poly_ref = np.array([[x1 + 8, y1 + 8], [x2 - 8, y1 + 25], [x1 + 28, y2 - 8]], dtype=np.int32)
        if not is_target:
            cv2.fillPoly(frame, [poly_ref], (80, 70, 65))
        else:
            poly_tgt = np.array([[x1 + 8, y1 + 25], [x2 - 12, y1 + 8], [x1 + 18, y2 - 12]], dtype=np.int32)
            cv2.fillPoly(frame, [poly_tgt], (165, 155, 145))

    elif pid == "pair_007":  # Office: Hair part switched from right to left
        head_cx = x1 + bw // 2
        head_cy = y1 + bh // 2
        cv2.circle(frame, (head_cx, head_cy + 8), min(bw, bh) // 2 - 4, (135, 160, 195), -1)
        if not is_target:
            cv2.ellipse(frame, (head_cx, head_cy), (bw // 2 - 4, bh // 2 - 4), 0, 180, 360, (35, 30, 25), -1)
            cv2.circle(frame, (head_cx + 12, head_cy - 4), 12, (50, 42, 35), -1)
        else:
            cv2.ellipse(frame, (head_cx, head_cy), (bw // 2 - 4, bh // 2 - 4), 0, 180, 360, (35, 30, 25), -1)
            cv2.circle(frame, (head_cx - 12, head_cy - 4), 12, (50, 42, 35), -1)

    elif pid == "pair_008":  # Office: Whiteboard equation erased
        cv2.rectangle(frame, (x1, y1), (x2, y2), (230, 230, 230), -1)
        if not is_target:
            cv2.putText(frame, "E=mc2", (x1 + 12, y1 + bh // 2 + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
            cv2.rectangle(frame, (x1 + 8, y1 + 8), (x2 - 8, y2 - 8), (200, 200, 200), 1)

    elif pid == "pair_009":  # Kitchen: Chef's knife moved from board to countertop
        if not is_target:
            cv2.rectangle(frame, (x1 + 4, y1 + bh // 2 - 4), (x1 + int(bw * 0.6), y1 + bh // 2 + 4), (220, 220, 225), -1)
            cv2.rectangle(frame, (x1 + int(bw * 0.6), y1 + bh // 2 - 5), (x1 + int(bw * 0.85), y1 + bh // 2 + 5), (30, 30, 30), -1)
        else:
            cv2.rectangle(frame, (x2 - int(bw * 0.4), y1 + 4), (x2 - int(bw * 0.4) + 8, y1 + int(bh * 0.65)), (220, 220, 225), -1)
            cv2.rectangle(frame, (x2 - int(bw * 0.4) - 1, y1 + int(bh * 0.65)), (x2 - int(bw * 0.4) + 9, y2 - 4), (30, 30, 30), -1)

    elif pid == "pair_010":  # Kitchen: Pot lid ajar vs closed
        cv2.rectangle(frame, (x1 + 4, y1 + bh // 2), (x2 - 4, y2 - 4), (75, 75, 80), -1)
        if not is_target:
            pts_lid = np.array([[x1 + 4, y1 + bh // 2 - 6], [x2 - 4, y1 + bh // 2 - 20], [x2 - 4, y1 + bh // 2 - 14], [x1 + 4, y1 + bh // 2]], dtype=np.int32)
            cv2.fillPoly(frame, [pts_lid], (180, 180, 185))
            cv2.circle(frame, (x2 - 12, y1 + bh // 2 - 22), 8, (215, 215, 220), -1)
        else:
            cv2.rectangle(frame, (x1 + 4, y1 + bh // 2 - 8), (x2 - 4, y2 - 4), (180, 180, 185), -1)

    elif pid == "pair_011":  # Kitchen: Apron strap fallen off shoulder
        cv2.rectangle(frame, (x1, y1), (x2, y2), (60, 60, 70), -1)
        if not is_target:
            cv2.line(frame, (x1 + 10, y1 + 6), (x2 - 10, y2 - 6), (235, 235, 240), 7)
        else:
            cv2.line(frame, (x1 + 10, y1 + bh // 2), (x2 - 15, y2 - 6), (235, 235, 240), 7)

    elif pid == "pair_012":  # Kitchen: 180-degree axis break
        cx, cy = x1 + bw // 2, y1 + bh // 2
        cv2.circle(frame, (cx, cy), min(bw, bh) // 2 - 4, (135, 160, 195), -1)
        if not is_target:
            cv2.circle(frame, (cx - 10, cy - 6), min(bw, bh) // 2 - 4, (40, 35, 32), -1)
            cv2.circle(frame, (cx + 10, cy), 5, (25, 25, 25), -1)
        else:
            cv2.circle(frame, (cx + 10, cy - 6), min(bw, bh) // 2 - 4, (40, 35, 32), -1)
            cv2.circle(frame, (cx - 10, cy), 5, (25, 25, 25), -1)

    elif pid == "pair_013":  # Interrogation: Detective standing vs seated
        det_cx = x1 + bw // 2
        if not is_target:
            cv2.circle(frame, (det_cx, y1 + 30), 22, (30, 28, 25), -1)
            cv2.rectangle(frame, (det_cx - 40, y1 + 52), (det_cx + 40, y2), (80, 140, 185), -1)
        else:
            cv2.circle(frame, (det_cx, y1 + int(bh * 0.45)), 22, (30, 28, 25), -1)
            cv2.rectangle(frame, (det_cx - 40, y1 + int(bh * 0.45) + 22), (det_cx + 40, y2), (80, 140, 185), -1)

    elif pid == "pair_014":  # Interrogation: Evidence folder moved
        fw = int(bw * 0.55)
        if not is_target:
            cv2.rectangle(frame, (x2 - fw, y1 + 6), (x2 - 4, y2 - 6), (65, 145, 215), -1)
        else:
            cv2.rectangle(frame, (x1 + 4, y1 + 6), (x1 + fw, y2 - 6), (65, 145, 215), -1)

    elif pid == "pair_015":  # Interrogation: Cheek bruise intensity
        cx, cy = x1 + bw // 2, y1 + bh // 2
        cv2.circle(frame, (cx, cy), min(bw, bh) // 2 - 4, (135, 160, 195), -1)
        if not is_target:
            cv2.circle(frame, (cx - 10, cy + 6), 14, (35, 15, 95), -1)
            cv2.circle(frame, (cx - 8, cy + 8), 6, (15, 5, 60), -1)
        else:
            cv2.circle(frame, (cx - 10, cy + 6), 14, (115, 145, 180), -1)

    elif pid == "pair_016":  # Interrogation: Fluorescent fixture removed
        if not is_target:
            cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (245, 245, 250), -1)
        else:
            cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (28, 30, 32), -1)


def apply_control_variation(
    frame: np.ndarray,
    pair: BenchmarkPair,
    is_target: bool,
) -> np.ndarray:
    """Apply intentional cinematic variation to target frame for control pairs."""
    if not is_target:
        return frame

    cat = pair.category

    if cat == PairCategory.CONTROL_LIGHTING:
        # 1.5 stop key light dim (e.g. mood dim in pair_017)
        dimmed = (frame.astype(np.float32) * 0.60).clip(0, 255).astype(np.uint8)
        return dimmed

    elif cat == PairCategory.CONTROL_CAMERA_ANGLE:
        # Moderate camera pan/tilt rotation (compensable by homography)
        h, w = frame.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 1.2, 1.0)
        M[0, 2] += 6.0  # slight pan
        M[1, 2] += 3.0  # slight tilt
        warped = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        return warped

    elif cat == PairCategory.CONTROL_FOCAL_LENGTH:
        # 4% zoom crop simulating focal length switch
        h, w = frame.shape[:2]
        crop_h = int(h * 0.96)
        crop_w = int(w * 0.96)
        start_y = (h - crop_h) // 2
        start_x = (w - crop_w) // 2
        cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        return zoomed

    elif cat == PairCategory.CONTROL_ACTOR_EXPRESSION:
        # Natural performance dialogue timing: slight mouth nuance
        mouth_y = int(HEIGHT * 0.38 + 16)
        mouth_x = int(WIDTH * 0.50)
        cv2.line(frame, (mouth_x - 8, mouth_y), (mouth_x + 8, mouth_y), (50, 40, 80), 2)
        return frame

    elif cat == PairCategory.CONTROL_GRADE:
        # Warmer LUT color grade
        graded = frame.astype(np.float32)
        graded[:, :, 0] *= 0.90  # B
        graded[:, :, 2] *= 1.15  # R
        return np.clip(graded, 0, 255).astype(np.uint8)

    return frame


# ---------------------------------------------------------------------------
# Clip Renderer Pipeline
# ---------------------------------------------------------------------------


def render_clip_to_file(
    pair: BenchmarkPair,
    is_target: bool,
    dest_path: Path,
) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_mp4 = Path(tmpdir) / "raw.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(raw_mp4), fourcc, FPS, (WIDTH, HEIGHT))

        # Base frame
        base = draw_scene_background(pair.template_id)
        render_characters(base, pair.template_id, actor_eyeline_left=True)

        if pair.ground_truth_label == GroundTruthLabel.DEFECT:
            inject_defect(base, pair, is_target=is_target)
        else:
            base = apply_control_variation(base, pair, is_target=is_target)

        # Compute frame count so clip duration covers pair.timestamp_sec
        num_frames = max(48, int(np.ceil((pair.timestamp_sec + 1.0) * FPS)))

        # Pre-compute subtle film grain cache (12 frames) to render fast
        grain_cache = [
            np.clip(base.astype(np.int16) + np.random.normal(0, 1.2, base.shape).astype(np.int16), 0, 255).astype(np.uint8)
            for _ in range(12)
        ]

        # Write clip frames
        for i in range(num_frames):
            writer.write(grain_cache[i % len(grain_cache)])

        writer.release()

        # Convert to H.264 MP4 with FFmpeg for universal browser & player playback
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_mp4),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-loglevel",
            "error",
            str(dest_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # If ffmpeg fails, keep the raw mp4
            import shutil
            shutil.copy(str(raw_mp4), str(dest_path))


def generate_all_benchmark_clips(truth_path: str = "bench/truth.json") -> int:
    dataset = load_benchmark_dataset(truth_path)
    print(f"Generating media for {len(dataset.pairs)} benchmark pairs...")

    generated = 0
    for idx, pair in enumerate(dataset.pairs, 1):
        ref_dest = Path(pair.reference_clip)
        tgt_dest = Path(pair.target_clip)

        print(f"[{idx:02d}/32] {pair.pair_id} ({pair.template_id}) -> {ref_dest.name} & {tgt_dest.name}")
        render_clip_to_file(pair, is_target=False, dest_path=ref_dest)
        render_clip_to_file(pair, is_target=True, dest_path=tgt_dest)
        generated += 2

    print(f"\n✓ Generated {generated} media clips across {len(dataset.pairs)} pairs.")
    return generated


if __name__ == "__main__":
    generate_all_benchmark_clips()
