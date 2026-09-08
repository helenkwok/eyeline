# IBM Bob Task Execution Queue

---

## Provenance & Budget Overview

Every discrete subsystem in Eyeline is implemented in focused, cost-controlled tasks authored via **IBM Bob**. Non-interactive execution logs are archived in `.bob-transcripts/` as verifiable proof of development provenance for the IBM Partner Track.

### Execution Command Pattern:
```bash
# Wrap in wall-clock alarm (600s); pass credentials via shell expansion; disable unneeded tools for ~4x cost reduction
BOBSHELL_API_KEY=$(cat ~/.bob/apikey) BOB_API_KEY=$(cat ~/.bob/apikey) \
perl -e 'alarm shift; exec @ARGV' 600 \
bob run \
  --workspace /Users/helen/workspace/eyeline \
  --trust \
  --mode continuity-supervisor \
  --disable-mcp \
  --disable-subagents \
  --max-turns <N> \
  --max-cost <M> \
  --format json \
  --log-level error \
  "<task_specification>" \
  < /dev/null > .bob-transcripts/<task_name>.json 2>&1
```

### Allocation & Accounting (Total Budget: 50 Bobcoins):

| Task # | Subsystem Description | Cost Cap | Actual Spend | Status |
|---|---|---|---|---|
| **1** | Visual Diff UI Shell & Fixture Player | 3.0 | 1.61 | **Complete** |
| **2** | Ground-Truth Schema & Benchmark Loader | 2.0 | 1.56 | **Complete** |
| **3** | Deterministic Frame Alignment & Diff Engine | 4.0 | — | Queued |
| **4** | Gemini Multimodal Continuity Classifier | 4.0 | — | Queued |
| **5** | Empirical Evaluation & Scoring Harness | 2.0 | 0.00 | **Complete** |
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

### Task 4: Google ADK Continuity Agent & Gemini Reasoner
- **Objective**: Implement the `ContinuityAgent` using the **Google Agent Development Kit (`google-adk`)**, registering deterministic CV tools and executing multimodal reasoning on Gemini 3.8 Flash on Vertex AI (deployable to Google Cloud Agent Builder).
- **Requirements**:
  - Instantiate `google.adk.agents.Agent` with `Gemini(model="gemini-3.8-flash")`.
  - Expose deterministic candidate extraction and CV tools directly to the agent.
  - Query Gemini with structured instructions to classify whether candidate deltas represent intentional variation or accidental defects.
  - Output structured JSON: `is_continuity_error`, `category`, `confidence`, and `reasoning`.

### Task 5: Empirical Benchmark Scoring Harness
- **Objective**: Automated calculation of benchmark performance without human intervention.
- **Requirements**:
  - Ingest raw detector predictions and `bench/truth.json`.
  - Calculate Recall, Bounding Box IoU Localisation, Control False-Positive Rate, and False Passes.
  - Emit machine-readable scorecard and print the canonical headline verification statement.

### Task 6: Veo Generative Cutaway Tool (Google ADK)
- **Objective**: Emergency pickup generator for continuity defects discovered after the set is struck, registered as a **Google ADK tool** callable by the Agent.
- **Requirements**:
  - Automated integration with Google Cloud Veo on Vertex AI via `google-genai` / Vertex AI SDK.
  - Expose `generate_veo_pickup` as a tool to the Google ADK Agent.
  - Generate a ~2-second contextual insert shot (e.g., tight macro insert of a prop, cutaway to clock or environment) to bridge continuity mismatches in the edit timeline.
  - Inject mandatory "SYNTHETIC ASSET" visual bug and metadata watermark on all generated media.
