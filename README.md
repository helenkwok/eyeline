# Eyeline: Autonomous On-Set Continuity Copilot

> **Eyeline catches physical continuity breaks while the set is still standing, so a break costs one more take instead of a $50,000 reshoot.**

Built for the **Agentic Cinema Hackathon** (**IBM Partner Track**) combining **IBM Bob**, **Google ADK (`google-adk`)**, **Google Cloud Agent Builder**, **Gemini 3.8 Flash**, and **Google Cloud Veo 3.1**.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/Agentic_Cinema_Hackathon-IBM_Partner_Track-purple.svg)](https://devpost.com)
[![Models](https://img.shields.io/badge/Models-Gemini_3.8_Flash_%2B_Veo_3.1-4285F4.svg)](docs/ARCHITECTURE.md)
[![IBM Bob Provenance](https://img.shields.io/badge/IBM_Bob-14.84_Coins_Spent-052FAD.svg)](.bob-transcripts/)

---

## 📺 2-Minute Demo Video Walkthrough

> **[▶ Watch the Full 1080p Walkthrough Video](docs/demo/eyeline_walkthrough.mp4)**  
> *(Also bundled and playable directly inside the web UI at `ui/assets/eyeline_walkthrough.mp4`)*

A comprehensive 102-second walk-through demonstrating:
1. **The 2-Minute On-Set Window**: Why post-strike reshoots cost $50k and how script supervisors use Eyeline.
2. **Interactive On-Set Review Station**: Dual synchronized 24fps HTML5 video players scrubbing real MP4 takes with canvas bounding boxes.
3. **30-Second Judge Path**: Instant evaluation of bundled Defect, Control Pass, and Resample presets.
4. **Pillar 2 False Alarm Retraction**: Live Gemini 3.8 Flash adjudication cutting control false alarms from 43.8% down to 18.8%.
5. **Pillar 3 Veo 3.1 Pickup**: Real macro insert cutaway with burned-in `SYNTHETIC CONTINUITY INSERT` disclosure watermark.

---

## ⚡ 30-Second Judge Quickstart (Zero-Credential Guarantee)

Eyeline requires **zero API keys and zero cloud configuration** to evaluate the entire benchmark dataset, run the detector, and scrub live clips in the interactive review station:

```bash
# 1. Clone repository
git clone https://github.com/helenkwok/eyeline.git
cd eyeline

# 2. Validate the 32-pair ground-truth benchmark (16 defect + 16 control)
python3 -m bench.loader

# 3. Run the Classical CV detector across all 64 real H.264 MP4 clips
python3 -m bench.run_benchmark

# 4. Launch the On-Set Review Station & Judge Index
python3 -m http.server 8080 -d ui/
```
- Open **`http://localhost:8080/`** for the **On-Set Review Station** (real video playback, 32-pair selector, timecodes, incident inspector).
- Open **`http://localhost:8080/judge.html`** for the **Judge Index & Verification Receipts** (30-second preset path, live Veo playback, empirical receipts).

---

## 📊 Live Empirical Scoreboard (Measured on Real MP4 Video)

> [!NOTE]
> **EMPIRICALLY MEASURED ON RENDERED VIDEO FOOTAGE — ZERO HAND-WRITTEN METRICS**  
> Evaluated across all 64 H.264 MP4 video clips in `bench/clips/` (CRF 18). Predictions in `bench/fixtures/measured_predictions.json`; scorecard in `bench/fixtures/scorecard.json`. Synchronized via `bench/sync_state.py`.

| Metric | Pillar 1 (Classical CV Alone) | Pillar 1 + Pillar 2 (Gemini 3.8 Adjudicated) | Delta / Impact | Meaning |
|---|---|---|---|---|
| **Defect Recall** | **15 / 16 (93.8%)** | **15 / 16 (93.8%)** | **100% Retained** | Seeded breaks detected (escaped: `pair_007`). |
| **Control False-Positive Rate** | **7 / 16 (43.8%)** | **3 / 16 (18.8%)** | **-25.0 pp (-57% relative)** | False alarms on intentional camera/lighting changes. |
| **Spatial Localisation** ($IoU \ge 0.3$) | **6 / 16 (37.5%)** | **6 / 16 (37.5%)** | Baseline preserved | Classical CV isolates exact pixel-delta sliver. |
| **Average Detection Latency** | **27.4 ms** (CPU) | **27.4ms** (CV) + **580ms** (Gemini) | Real-time ready | Executes well within the 2-minute on-set window. |

### Statistical Disclosure & Retracted Controls
Across 16 paired negative control setups, Gemini 3.8 Flash adjudication retracted **4 of 7 false alarms with 0 regressions** (one-sided exact McNemar $p = 0.0625$, $n=16$; 95% CI $[4.0\%, 45.6\%]$).
- **Retracted False Alarms**: `pair_018` (lighting dim), `pair_019` (zoom), `pair_026` (camera angle), `pair_031` (zoom).
- **Surviving Tripped Controls**: `pair_017` (camera angle), `pair_022` (camera angle), `pair_023` (focal length).

### Spatial Localisation ($IoU \ge 0.3$) Containment Analysis
In **10 of 16 defect pairs**, the detector bounding box is **93.1% to 100% contained** inside the ground-truth region (`Inter / Pred_Area` $\approx 1.0$). Standard IoU falls below 0.3 because ground-truth boxes delineate the **entire semantic entity** (e.g. full actor body for blocking), whereas classical CV isolates the **exact displaced pixel sliver** ($\text{Area}_{\text{delta}} \ll \text{Area}_{\text{entity}}$).

---

## 🏛️ System Architecture: The Strict 3-Pillar Ceiling

Eyeline adheres strictly to **Rule 7.B** of the Agentic Cinema Hackathon: **strictly Google Cloud Gemini & Veo on Vertex AI, zero third-party object detectors (no YOLO, SAM, or GroundingDINO)**.

```
                  ┌─────────────────────────────────────────┐
                  │          Take Pair Video Feeds          │
                  │   Reference Setup  vs.  Current Take    │
                  └────────────────────┬────────────────────┘
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        │                                                             │
        ▼                                                             │
┌────────────────────────────────────────────────────────┐            │
│ PILLAR 1: Deterministic Alignment & Delta Isolation     │            │
│ Classical CV (OpenCV-headless, scikit-image)           │            │
│ • YCrCb illumination & histogram normalization         │            │
│ • ORB keypoint matching + RANSAC homography alignment  │            │
│ • Multi-channel max difference masking & opening       │            │
│ • Sub-100ms candidate bounding box extraction          │            │
└──────────────────────────────┬─────────────────────────┘            │
                               │                                      │
                               │ Candidate Crops & Metadata           │
                               ▼                                      │
┌────────────────────────────────────────────────────────┐            │
│ PILLAR 2: Multimodal Continuity Adjudication           │            │
│ Google ADK Agent & Gemini 3.8 Flash on Vertex AI       │            │
│ • Inspects cropped delta against scene context         │            │
│ • Discriminates intentional camera/lighting changes    │            │
│ • Retracts false alarms (-25.0 pp FPR reduction)       │            │
└──────────────────────────────┬─────────────────────────┘            │
                               │                                      │
                               │ Continuity Certificate               │
                               ▼                                      │
         ┌───────────────────────────────────────────┐                │
         │         Script Supervisor Verdict         │                │
         │  [Pass]   [Borderline Resample]   [Retake]│                │
         └─────────────────────┬─────────────────────┘                │
                               │ (If Set Struck & Unresolved)         │
                               ▼                                      │
┌────────────────────────────────────────────────────────┐            │
│ PILLAR 3: Generative Emergency Pickup Tool             │            │
│ Google Cloud Veo 3.1 (`veo-3.1-generate-preview`)      │◄───────────┘
│ • Synthesizes 4.0s–6.0s macro insert cutaway B-roll   │
│ • Matches scene lighting, color temperature & props    │
│ • Mandatory `SYNTHETIC CONTINUITY INSERT` watermark    │
└────────────────────────────────────────────────────────┘
```

---

## 🦾 Built with IBM Bob (IBM Partner Track Provenance)

Substantive modular components of Eyeline were authored using **IBM Bob** in headless execution mode. Transcripts for all 8 development tasks are permanently preserved in [`.bob-transcripts/`](.bob-transcripts/):

**Total Budget: 50.0 Bobcoins | Actual Spend: 14.84 Bobcoins | Remaining: 35.16 Bobcoins**

| Task # | Subsystem Description | Budget Cap | Actual Cost | Status | Transcript Artifact |
|---|---|---|---|---|---|
| **1** | Visual Diff UI Shell & Fixture Player | 3.0 | 1.61 | **Complete** | [`.bob-transcripts/task1-ui.json`](.bob-transcripts/task1-ui.json) |
| **2** | Ground-Truth Schema & Pydantic Loader | 2.0 | 1.56 | **Complete** | [`.bob-transcripts/task2-schema.json`](.bob-transcripts/task2-schema.json) |
| **3** | Classical CV Alignment & Diff Engine | 4.0 | 2.03 | **Complete** | [`.bob-transcripts/task3-vision.json`](.bob-transcripts/task3-vision.json) |
| **4** | Pillar 2 Multimodal Adjudicator & Runner | 3.5 | 2.46 | **Complete** | [`.bob-transcripts/task4-adjudicator.json`](.bob-transcripts/task4-adjudicator.json) |
| **5** | Empirical Evaluation & Scoring Harness | 2.0 | 1.61 | **Complete** | [`.bob-transcripts/task5-scorer.json`](.bob-transcripts/task5-scorer.json) |
| **6** | Pillar 3 Veo Generative Cutaway Generator | 4.0 | 2.14 | **Complete** | [`.bob-transcripts/task6-veo.json`](.bob-transcripts/task6-veo.json) |
| **7** | Benchmark Evaluation Runner CLI | 2.5 | 1.55 | **Complete** | [`.bob-transcripts/task7-runner.json`](.bob-transcripts/task7-runner.json) |
| **8** | Anti-Circularity Forcing Functions | 3.0 | 1.88 | **Complete** | [`.bob-transcripts/task8-forcing-functions.json`](.bob-transcripts/task8-forcing-functions.json) |

---

## 🐳 Docker & Google Cloud Run Deployment

Eyeline includes a production-grade `Dockerfile` using `nginx:alpine` configured with byte-range streaming for HTML5 video seeking:

```bash
# Build the standalone container locally
docker build -t eyeline:latest .

# Run container (serves UI, clips, and receipts on port 8080)
docker run -p 8080:8080 eyeline:latest
```

### Turnkey Cloud Run Deploy:
```bash
# Deploy with unauthenticated access for hackathon judges
./deploy/deploy_cloud_run.sh
```

---

## 📜 Full Documentation Suite

- [`docs/STATE.md`](docs/STATE.md): Living project state, active numbers, and sync status.
- [`docs/DEVPOST.md`](docs/DEVPOST.md): Complete Devpost submission text and project narrative.
- [`docs/BENCHMARK.md`](docs/BENCHMARK.md): 32-pair benchmark protocol, metrics, and negative control design.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Technical architecture specification and tool bindings.
- [`docs/BOB-TASKS.md`](docs/BOB-TASKS.md): Detailed task breakdown, costs, and tool accounting for IBM Bob.

---

## ⚖️ License & Rule 7.B Compliance

- **Code License**: [Apache 2.0 License](LICENSE).
- **Rule 7.B Compliance**: Permitted AI generative and inference models are strictly **Google Cloud Gemini & Google Cloud Veo on Vertex AI**. Zero third-party deep learning object detectors were used or included.
