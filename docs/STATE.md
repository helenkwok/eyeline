# Eyeline — Project State & Empirical Scoreboard

> **Living project state document.** Updated before completing every task.  
> Enables recovery from interruptions in a single file read and provides judges with an immediate orientation on a fresh clone.

---

## 1. Quick Orientation for Judges (Fresh Clone)

Eyeline is an autonomous on-set continuity copilot for film script supervisors competing in the **Agentic Cinema Hackathon** (**IBM Partner Track**).

- **Core Mission**: Catch physical continuity breaks (props, wardrobe, blocking, consumables) while the set is still standing (2-minute window) to prevent five-figure reshoots after set strike.
- **Zero-Credential Guarantee**: All schemas, 32 benchmark pairs, baseline prediction fixtures, and the interactive Judge UI run completely offline with zero API keys or cloud dependencies.
- **30-Second Verification**:
  ```bash
  # 1. Validate the 32-pair ground-truth dataset (16 defects + 16 controls)
  python3 -m bench.loader

  # 2. Score baseline predictions and output canonical headline statement
  python3 -m bench.scorer

  # 3. Launch the On-Set Review Station & Judge Index
  python3 -m http.server 8080 -d ui/
  # Open http://localhost:8080/judge.html in your browser
  ```

---

## 2. Benchmark Numbers & Status

> [!WARNING]
> **FIXTURE-DERIVED PLACEHOLDER — NOT AN EMPIRICAL MEASUREMENT OF FOOTAGE**  
> The scorecard numbers below are computed by scoring the baseline test fixture (`bench/fixtures/sample_predictions.json`) against `bench/truth.json`. They validate the scoring engine, IoU calculations, and CLI contract.  
> **They do NOT yet represent empirical detector performance over video frames.** Currently, no media files exist under `bench/clips/`, and `vision.py` is not yet wired to run across real footage. Media generation (the 32 take pairs) is the immediate critical path. Once real frames are rendered and processed by the detector, this section will record real, measured detector output.

| Metric | Current Placeholder Value | Standard / Formula | Meaning |
|---|---|---|---|
| **Defect Detection Recall** | **15 / 16 (93.8%)** *(Fixture)* | $TP / P$ | Contract target: 15 of 16 defect pairs caught. |
| **Defect Localisation Accuracy** | **14 / 16 (87.5%)** *(Fixture)* | $TP_{\text{loc}} / TP_{\text{spatial}}$ ($IoU \ge 0.3$) | Contract target: 14 of 16 localized within ground-truth bbox. |
| **Control False-Positive Rate** | **1 / 16 (6.25%)** *(Fixture)* | $FPR = FP / C$ | Target demonstration: 1 false alarm (`pair_017` lighting dim). |
| **False Passes (Critical Risk)** | **1 / 16 (6.25%)** *(Fixture)* | $FN = P - TP$ | Target demonstration: 1 escaped break (`pair_016` subtle practical lamp). |
| **Pillar-1 CV Latency** | *Pending live run* | OpenCV / scikit-image | Fast classical prefilter latency. |
| **Pillar-2 ADK Latency** | *Pending live run* | Gemini 3.8 Flash on Vertex | Multimodal crop adjudication latency. |

### Canonical Baseline Statement (Fixture Contract Validation):
> *"Detected **15** of **16** seeded continuity breaks (**14** localized), with **1** false alarm across **16** control pairs containing legitimate variation ($FPR = 6.25\%$). Tripped control: `pair_017` (fixture baseline)."*

---

## 3. IBM Bob Spend & Provenance Accounting

**Total Allocated Budget: 50.0 Bobcoins**

| **Task #** | **Subsystem Description** | **Cost Cap** | **Actual Spend** | **Status** | **Provenance Artifact** |
|---|---|---|---|---|---|
| **1** | Visual Diff UI Shell & Fixture Player | 3.0 | 1.61 | **Complete** | `.bob-transcripts/task1-ui.json` |
| **2** | Ground-Truth Schema & Pydantic Loader | 2.0 | 1.56 | **Complete** | `.bob-transcripts/task2-schema.json` |
| **3** | Classical CV Alignment & Diff Engine | 4.0 | 2.03 | *In Flight* | `.bob-transcripts/task3-vision.json` |
| **4** | Google ADK Continuity Agent & Gemini 3.8 | 4.0 | — | Queued | `src/eyeline/agent.py` |
| **5** | Empirical Evaluation & Scoring Harness | 2.0 | 1.61 | **Complete** | `.bob-transcripts/task5-scorer.json` |
| **6** | Veo Generative Cutaway Bridge Tool | 4.0 | — | Queued | Vertex AI Veo pipeline |
| **TOTAL** | | **19.0** | **6.81** | *43.19 Bobcoins Remaining* | |

---

## 4. What's Done

1. **Empirical Scorer & Evaluation Harness (Task 5 — IBM Bob)**:
   - Authored by IBM Bob (1.61 Bobcoins, 15 tool calls, `.bob-transcripts/task5-scorer.json`).
   - Standalone CLI evaluator in `bench/scorer.py` (`python3 -m bench.scorer`).
   - Computes Recall ($TP/P$), Spatial Localisation ($TP_{\text{loc}} / TP$), empirical False-Positive Rate ($FP/C$), and False Passes ($FN$).
   - Explicitly catalogues tripped controls rather than demanding zero false alarms.
   - Baseline fixture in `bench/fixtures/sample_predictions.json` for zero-dependency contract validation.
   - Complete automated test suite in `tests/test_scorer.py` (10/10 tests passing).
2. **Pillar 1 Classical CV (Task 3 Scaffold)**: Classical CV engine in `src/eyeline/vision.py` with YCrCb exposure matching, ORB + RANSAC homography, morphological diff masking, and normalized bounding box clustering.
3. **Pillar 2 Foundation**: Google ADK integration in `src/eyeline/agent.py` declaring `ContinuityAgent` with Vertex AI Reasoning Engine spec in `src/eyeline/agent_builder_spec.json`.
4. **Pillar 3 Tool Interface**: `generate_veo_pickup` tool contract declaring the verified Vertex AI model endpoint `veo-3.1-generate-preview` with synthetic asset watermarking.
5. **Verified AI Model Identifiers**:
   - Multimodal Reasoner: `gemini-3.8-flash` (verified against `google-genai` and `google-adk`).
   - Video Generator: `veo-3.1-generate-preview` (verified live Vertex AI model ID; avoided 404 shorthand).
6. **Ground-Truth Dataset (Task 2 — IBM Bob)**: 32 balanced pairs in `bench/truth.json` validated via Pydantic v2 models in `bench/loader.py` (`.bob-transcripts/task2-schema.json`).
7. **Visual Inspection Dashboard (Task 1 — IBM Bob)**: Synchronized dual-take player in `ui/index.html` + `ui/app.js` with canvas overlays and fallback fixtures (`.bob-transcripts/task1-ui.json`).
8. **Judge Index & 30-Second Path**: Dedicated review interface in `ui/judge.html` + `ui/judge.js` featuring interactive presets (defect, control pass, resample), empirical receipt table, and honest limitation disclosures.
9. **FastMCP Server**: Operational inspection server in `src/eyeline/mcp_server.py` exposing telemetry, discrepancy queries, and empirical control logging over stdio.

---

## 5. What's In Flight (Critical Path)

1. **CRITICAL PATH — Benchmark Media Generation (`bench/clips/`)**:
   - Status: Zero video/image files currently exist in `bench/clips/`.
   - Goal: Render all 32 take pairs (16 defect pairs with visible, timecoded physical discontinuities + 16 control pairs with camera/light/expression variations) across the 4 scene templates (`t01_diner`, `t02_office`, `t03_kitchen`, `t04_interrogation`).
   - Impact: Required to feed `vision.py`, generate genuine predictions, give the UI actual video footage to scrub, and film the demo video.
2. **Detector-to-Benchmark Wiring**:
   - Wire `src/eyeline/vision.py` + agent pipeline to ingest `bench/clips/` and produce live prediction JSON rather than static fixtures.
3. **Task 3 (Vision Engine Self-Test Fix)**:
   - File: `src/eyeline/vision.py`
   - Issue: Synthetic plain-color rectangle in self-test produced insufficient ORB features; needs textured patches or direct diff-mask verification.

---

## 6. What's Next

1. Implement the media generator script (`bench/generator.py` or synthetic canvas/OpenCV renderer) to synthesize the 32 MP4 take pairs into `bench/clips/`.
2. Run `vision.py` across `bench/clips/` to emit empirical detections.
3. Run `bench/scorer.py` on real predictions and record genuine, non-fixture empirical metrics in `docs/STATE.md`.
4. Update UI with real clip assets for live scrub playback.
5. Record demo video walk-through.
