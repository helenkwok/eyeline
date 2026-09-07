# Project Instructions: Eyeline On-Set Continuity Copilot

Eyeline is an autonomous on-set continuity copilot for film script supervisors competing in the **Agentic Cinema Hackathon** (IBM Partner Track & Google Cloud Track).

---

## 1. System Architecture & Bounded Paradigm

Eyeline operates under a strict **3-Pillar Ceiling**:
1. **Pillar 1: Deterministic Alignment & Delta Isolation (Classical CV)**
   - OpenCV-headless, scikit-image, scenedetect.
   - Computes histogram matching, exposure normalization, perspective alignment, and spatial difference masks.
   - High-pass thresholding filters sensor noise, minor flicker, and global shifts.
2. **Pillar 2: Multimodal Continuity Adjudication (Google ADK & Gemini 2.5 on Vertex AI)**
   - Orchestrated via `google.adk.agents.Agent`.
   - Inspects cropped candidate regions alongside take metadata and scene context.
   - Distinguishes intentional variations (lighting mood, camera angle, actor performance nuances) from accidental continuity defects (prop displacement, liquid level jumps, wardrobe shifts, hair/makeup, blocking).
3. **Pillar 3: Generative Emergency Pickup Tool (Google Cloud Veo)**
   - Generates 2-second contextual B-roll inserts (macro prop inserts, clock/environment cutaways) to bridge editorial continuity breaks when sets have already been struck.

---

## 2. Strict Hackathon Track & Rule Constraints

- **Rule 7.B Compliance**: The ONLY permitted AI generative and inference models are **Google Cloud Gemini & Google Cloud Veo on Vertex AI**.
  - **PROHIBITED**: Off-the-shelf third-party object detection/segmentation neural networks (YOLO / Ultralytics, SAM, GroundingDINO, MobileNet). Use of these violates Rule 7.B and Apache-2.0.
  - **PERMITTED**: Classical CV libraries under permissive licenses (`opencv-python-headless` [Apache-2.0], `scikit-image` [BSD-3], `scenedetect` [BSD-3], `imagehash` [BSD-2]).
- **IBM Track Provenance**: Substantive, modular code components are authored by **IBM Bob**. Transcripts are preserved in `.bob-transcripts/`.
- **Negative Control Invariance**:
  - The benchmark suite contains mandatory negative control pairs (identical setups with variations only in camera angle, focal length, lighting grade, or actor expression).
  - The detector MUST report 0 false positives on negative controls. Any system that flags all deltas as defects is immediately penalized.
- **Coordinate Conventions**:
  - All spatial bounding boxes must use normalized coordinates: `[ymin, xmin, ymax, xmax]` where values are floats in `[0.0, 1.0]`.

---

## 3. Environment & Development Conventions

- Python 3.10+ with type hints and Pydantic models for structured contracts.
- Never write credentials or hardcoded keys into code. Never read `.env` or secret files.
- Tests are executed only when explicitly requested.
- When running IBM Bob in headless mode, always specify `--workspace <path> --trust --mode continuity-supervisor --format json < /dev/null`.
- **Wall-Clock Timeout Mandate**: Wrap all headless Bob runs in a wall-clock timeout (e.g. `perl -e 'alarm shift; exec @ARGV' 600 bob run ...`) because network stalls can cause Bob to hang indefinitely without CPU or coin expenditure.
