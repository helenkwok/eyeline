# Eyeline: Production Concept & Architecture

*Agentic Cinema Hackathon — IBM Partner Track*  
*Submission Deadline: September 9, 2026 at 14:00 PDT*

---

## Executive Summary

**Eyeline verifies continuity live on film sets while the set is still standing, turning a potential multi-thousand-dollar reshoot into a 30-second retake.**

In film and episodic television production, physical continuity across takes and camera angles is traditionally tracked manually by a single script supervisor using polaroids, tablet logs, and raw observation. When continuity errors slip through unnoticed:
- **Caught on set (set standing)**: Costs minutes and an extra take.
- **Caught in editorial (set struck)**: Requires expensive reshoots, complex digital post-production fixes, or abandoning the preferred take.

Eyeline operates as an automated continuity copilot that inspects camera takes against reference setups in near real time.

---

## Architecture: The Three-Pillar Ceiling

To preserve product clarity and avoid architectural bloat, Eyeline maintains a hard ceiling of three core capabilities:

```
+-----------------------------------------------------------------------+
|                              EYELINE                                  |
+-----------------------------------------------------------------------+
|  1. Live Setup Comparison                                             |
|     Deterministic frame alignment + candidate region segmentation     |
+-----------------------------------------------------------------------+
|  2. Seeded Ground-Truth Benchmark                                     |
|     Empirical recall & false-alarm evaluation (positives vs controls) |
+-----------------------------------------------------------------------+
|  3. Veo Generative Pickups                                            |
|     Automated ~2s insert cutaways on Vertex AI for late-caught breaks |
+-----------------------------------------------------------------------+
```

1. **Live Setup Comparison**: Compares consecutive takes against designated reference setups, highlighting localized discrepancies for supervisor review.
2. **Seeded Ground-Truth Benchmark**: An empirical evaluation protocol running identical detectors against positive break pairs and negative control pairs to report verifiable recall, localisation accuracy, and false-pass rates.
3. **Veo Generative Pickups**: A post-strike fallback pipeline using Veo on Google Cloud Vertex AI to synthesize contextual insert cutaways (~2s clips) that allow editors to bridge unavoidable continuity mismatches without scheduling a reshoot.

---

## Bounded Model Architecture

High-reliability cinematic workflows require strict boundaries between deterministic algorithms and multimodal reasoning:

- **Deterministic Layer (Outside the Hot Path)**:
  - Video decoding, timecode synchronization, and shot metadata indexing.
  - Perspective alignment, exposure normalisation, and motion estimation.
  - Pixel-difference thresholding and bounding-box candidate clustering.
  - Prevents hallucination and keeps large models from running continuously across redundant high-framerate frames.

- **Multimodal AI Layer (Gemini on Google Cloud)**:
  - Evaluates isolated candidate regions.
  - Distinguishes intentional cinematic variation (lighting setup changes, camera angle adjustments, focus shifts, natural actor performance nuances) from continuity defects (displaced props, wardrobe shifts, altered liquid levels).
  - Emits structured classifications: error category, confidence score, localized coordinates, and concise explanatory rationale.

- **Human Adjudication Gate**:
  - The model never auto-passes or silences anomalies. All candidate flags are presented to the script supervisor for final sign-off.

---

## Integrity & Limitations

- **Footage Provenance**: Demo and benchmark footage is synthetically generated via Google Cloud Veo on Vertex AI to establish mathematically exact ground truth. All synthetic assets are explicitly marked as synthetic in the interface, code, and documentation.
- **Empirical Transparency**: A continuity detector that flags every minor variance is unusable on set. Eyeline reports false-positive rates on control setups alongside raw detection rates.
- **Unverified Figures**: No unverified industry cost statistics (e.g., speculative reshoot costs) will be cited in product copy, documentation, or video presentations without primary source verification.

---

## IBM Bob Track Provenance

Per IBM Partner Track eligibility rules:
- Substantive components across the lifecycle are authored and orchestrated using **IBM Bob**.
- Non-interactive execution transcripts are systematically logged under `.bob-transcripts/` as verifiable provenance.
- The project documentation and demo video feature dedicated coverage of IBM Bob tooling and development workflows.
