# Continuity Standards & Engineering Rules

## 1. Hackathon Rule 7.B Compliance
- Eyeline is restricted to **Google Cloud Gemini on Vertex AI** for all generative and perceptual multimodal inference.
- **NEVER** import or introduce external pre-trained object detectors or segmentation models (e.g. YOLO, Ultralytics, SAM, GroundingDINO, Detectron). Doing so violates Rule 7.B and Apache-2.0.
- All spatial delta preprocessing must use classical computer vision algorithms (`opencv-python-headless`, `scikit-image`, `scenedetect`, `imagehash`).

## 2. Benchmark Negative Controls
- Every evaluation set contains matched negative controls: identical setups with intentional variations in camera angle, lighting grade, focal length, or performance nuances.
- The system must exhibit high specificity: an algorithm that reports defects on negative controls is invalid.
- Distinguish between **intentional cinematic variation** (e.g. key light dimmed for mood) and **accidental continuity mismatch** (e.g. coffee mug disappearing between shot-reverse-shot).

## 3. Coordinate System Standard
- All spatial bounding boxes across fixtures, UI overlays, and agent tools use normalized float coordinates:
  `[ymin, xmin, ymax, xmax]` where `0.0 <= val <= 1.0`.
- Top-left of frame is `(0.0, 0.0)`, bottom-right is `(1.0, 1.0)`.

## 4. Headless & Non-Interactive Safety
- Automated pipelines must run non-interactively. Avoid TTY prompts or interactive input requests.
- All headless agent commands must be wrapped in a wall-clock timeout (e.g. `perl -e 'alarm shift; exec @ARGV' 600 ...`) to guard against unrecoverable network stalls that hang at 0% CPU.
