# IBM Bob Task Execution Queue

---

## Provenance & Budget Overview

Every discrete subsystem in Eyeline is implemented in focused, cost-controlled tasks authored via **IBM Bob**. Non-interactive execution logs are archived in `.bob-transcripts/` as verifiable proof of development provenance for the IBM Partner Track.

### Execution Command Pattern:
```bash
BOBSHELL_API_KEY=$(cat ~/.bob/apikey) bob run \
  --max-turns <N> \
  --max-cost <M> \
  --format json \
  --log-level error \
  "<task_specification>"
```

### Allocation & Accounting (Total Budget: 50 Bobcoins):

| Task # | Subsystem Description | Cost Cap | Actual Spend | Status |
|---|---|---|---|---|
| **1** | Visual Diff UI Shell & Fixture Player | 3.0 | 1.61 | **Complete** |
| **2** | Ground-Truth Schema & Benchmark Loader | 2.0 | — | Queued |
| **3** | Deterministic Frame Alignment & Diff Engine | 4.0 | — | Queued |
| **4** | Gemini Multimodal Continuity Classifier | 4.0 | — | Queued |
| **5** | Empirical Evaluation & Scoring Harness | 2.0 | — | Queued |
| **6** | Veo Generative Cutaway Generator | 4.0 | — | Queued |

---

## Detailed Task Specifications

### Task 1: Visual Diff UI Shell (Front-End First)
- **Objective**: Construct a single-page operational dashboard for script supervisors.
- **Components**:
  - Side-by-side synchronized video players with a unified scrub bar and frame-accurate stepping controls.
  - Interactive canvas/SVG overlay displaying color-coded bounding boxes on flagged regions.
  - Verdict drawer listing flagged discrepancies with classification tag, confidence score, and timecode.
  - Prominent verification banner displaying real-time benchmark summary metrics.
  - Backed by a standalone static JSON fixture (`bench/fixtures/sample_diff.json`) for zero-dependency standalone execution.

### Task 2: Ground-Truth Schema & Benchmark Loader
- **Objective**: Formalize the benchmark annotation format in `bench/truth.json`.
- **Requirements**:
  - JSON schema validating pair metadata: `pair_id`, `category` (1 of 7 positive classes or `control`), `reference_clip`, `target_clip`, `timestamp_sec`, and normalized bounding coordinates (`ymin`, `xmin`, `ymax`, `xmax`).
  - Strict validation loader ensuring no malformed ground-truth assets can enter the pipeline.
  - Air-gapped isolation: the detector module must have no runtime access to this package.

### Task 3: Deterministic Alignment & Candidate Region Generator
- **Objective**: Build the non-AI preprocessing engine to isolate visual deltas.
- **Requirements**:
  - Extract matching timecoded frames from setup pairs via OpenCV / FFmpeg.
  - Apply exposure normalization (histogram matching) and perspective alignment to handle minor camera movement.
  - Compute spatial difference masks and cluster candidate bounding boxes for multimodal inspection.
  - Filter out uniform high-frequency sensor noise and minor lighting flicker deterministically.

### Task 4: Gemini Multimodal Continuity Classifier
- **Objective**: Connect candidate visual regions to Google Cloud Gemini models via official SDKs (`google-genai` / `google-cloud-aiplatform`).
- **Requirements**:
  - Pass cropped reference and target frame regions along with camera setup metadata.
  - Query Gemini with structured system instructions to classify whether the change is intentional cinematic variation (lighting, lens, posture) or an accidental continuity error.
  - Output structured JSON: `is_continuity_error` (boolean), `category`, `confidence`, and `reasoning`.

### Task 5: Empirical Benchmark Scoring Harness
- **Objective**: Automated calculation of benchmark performance without human intervention.
- **Requirements**:
  - Ingest raw detector predictions and `bench/truth.json`.
  - Calculate Recall, Bounding Box IoU Localisation, Control False-Positive Rate, and False Passes.
  - Emit machine-readable scorecard and print the canonical headline verification statement.

### Task 6: Veo Generative Cutaway Generator
- **Objective**: Emergency pickup generator for continuity defects discovered after the set is struck.
- **Requirements**:
  - Automated integration with Google Cloud Veo on Vertex AI.
  - Generate a ~2-second contextual insert shot (e.g., tight macro insert of a prop, cutaway to clock or environment) to bridge continuity mismatches in the edit timeline.
  - Inject mandatory "SYNTHETIC ASSET" visual bug and metadata watermark on all generated media.
