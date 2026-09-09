# Eyeline — IBM Bob Provenance & Verification Index

> **Agentic Cinema Hackathon — IBM Partner Track Submission Artifact**  
> Repository: [https://github.com/helenkwok/eyeline](https://github.com/helenkwok/eyeline)  
> Live Cloud Run Deployment: [https://eyeline-akewulk3vq-uc.a.run.app/](https://eyeline-akewulk3vq-uc.a.run.app/)  
> Video Walkthrough: [https://youtu.be/T6W_apEthdA](https://youtu.be/T6W_apEthdA)

---

## 1. Provenance Statement & Division of Labour

Eyeline combines autonomous code authoring via **IBM Bob** with frontend visual orchestration via **Antigravity CLI (`agy`)**, operating strictly within **Rule 7.B** of the Agentic Cinema Hackathon guidelines:
- **IBM Bob** authored the foundational backend modules: the Pydantic ground-truth schema, classical CV perspective alignment and difference masking engine, Gemini 3.8 Flash multimodal adjudication runner, Veo 3.1 generative pickup pipeline, empirical evaluation scoring harness, and anti-circularity forcing functions.
- **Antigravity (`agy`)** orchestrated the visual presentation layer, responsive styling, and 30-second judge presets.
- **Raw Transcripts**: All eight JSON transcripts in `transcripts/` represent the verbatim, unedited machine output from headless `bob run --mode continuity-supervisor --format json` executions.

---

## 2. IBM Bob Task Accounting & Commit Provenance

| Task # | What Bob Authored | Bobcoins Spent | Git Commit | Transcript Artifact |
|:---:|---|:---:|:---:|---|
| **1** | Visual Diff UI Shell & Fixture Player | 1.61 | [`1cbff58`](https://github.com/helenkwok/eyeline/commit/1cbff58) | `transcripts/task1-ui.json` |
| **2** | Ground-Truth Pydantic Schema & Loader | 1.56 | [`6955247`](https://github.com/helenkwok/eyeline/commit/6955247) | `transcripts/task2-schema.json` |
| **3** | Classical CV Alignment & Diff Engine | 2.03 | [`5cca888`](https://github.com/helenkwok/eyeline/commit/5cca888) | `transcripts/task3-vision.json` |
| **4** | Pillar 2 Multimodal Adjudicator & Runner | 2.46 | [`33617e2`](https://github.com/helenkwok/eyeline/commit/33617e2) | `transcripts/task4-adjudicator.json` |
| **5** | Empirical Evaluation & Scoring Harness | 1.61 | [`5cca888`](https://github.com/helenkwok/eyeline/commit/5cca888) | `transcripts/task5-scorer.json` |
| **6** | Pillar 3 Veo Generative Cutaway Generator | 2.14 | [`1a3d89a`](https://github.com/helenkwok/eyeline/commit/1a3d89a) | `transcripts/task6-veo.json` |
| **7** | Benchmark Evaluation Runner CLI | 1.55 | [`281a5a7`](https://github.com/helenkwok/eyeline/commit/281a5a7) | `transcripts/task7-runner.json` |
| **8** | Anti-Circularity Forcing Functions | 1.88 | [`50dab7a`](https://github.com/helenkwok/eyeline/commit/50dab7a) | `transcripts/task8-forcing-functions.json` |
| **TOTAL** | **8 Focused Architectural Subsystems** | **14.84 / 50.00** | — | *35.16 Bobcoins Remaining* |

---

## 3. Custom Domain Configuration (`custom_modes.yaml`)

Rather than invoking generic conversational defaults, Bob was configured specifically for the domain with a dedicated `continuity-supervisor` mode (`custom_modes.yaml`):
```yaml
customModes:
  - slug: continuity-supervisor
    name: Continuity Supervisor
    roleDefinition: >-
      You are Eyeline's on-set continuity engineering agent. You specialize in
      classical computer vision verification, cinematic script supervisor workflows,
      temporal continuity defect detection (prop displacement, wardrobe shifts,
      lighting mismatch), and strict compliance with Agentic Cinema Hackathon rules.
    whenToUse: Use when developing, inspecting, or running continuity inspection tasks.
    description: On-set script supervisor continuity copilot mode for Eyeline.
    groups: [read, edit, execute, mcp, skill, todo, subagent]
```
This tailored role definition ensured Bob adhered strictly to permissive licensing (Apache-2.0, OpenCV-headless), normalized coordinate conventions `[ymin, xmin, ymax, xmax]`, and Rule 7.B boundaries throughout development.

---

## 4. Empirical Evaluation Ablation Scorecards (`measurements/`)

To prevent circular self-grading, the evaluation harness scores detector predictions against held-out ground truth (`bench/truth.json`) across 32 take pairs (64 H.264 MP4 clips):

1. **`measurements/scorecard.json` (Pillar 1: Classical CV Alone)**:
   - **Defect Detection Recall**: **15 / 16 (93.8%)**
   - **Control False-Positive Rate (FPR)**: **7 / 16 (43.8%)**
   - *Findings*: Classical difference masks exhibit 0% false alarms on lighting dims and color grading, but perspective shifts from camera angle pans and focal zooms trip spatial masks.

2. **`measurements/adjudicated_scorecard.json` (Pillar 1 + Pillar 2: Gemini 3.8 Flash Adjudication)**:
   - **Defect Detection Recall**: **15 / 16 (93.8%)** (100% retained)
   - **Control False-Positive Rate (FPR)**: **3 / 16 (18.8%)** (**-25.0 pp reduction**)
   - *Findings*: Gemini multimodal reasoning inspected cropped delta patches against scene metadata, successfully retracting 4 of 7 false alarms with zero regressions (exact McNemar $p = 0.0625$, $n=16$).

Both machine-readable scorecards are included in full so judges can inspect the raw data and verify that all headline numbers derive directly from deterministic execution rather than hand-authored claims.
