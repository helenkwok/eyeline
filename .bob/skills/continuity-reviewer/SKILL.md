---
name: continuity-reviewer
description: Systematic protocol for inspecting visual continuity between paired takes, candidate bounding boxes, and temporal incident categorization.
---

# Continuity Reviewer Skill

This skill guides an agent through verifying continuity between two film takes (Setup A reference vs. Setup B current take).

## Procedure

### Step 1: Ingest Take Metadata & Pair Context
- Check scene number, shot descriptor, camera setup (e.g. Master wide vs. Medium close-up).
- Note deliberate directorial changes (e.g. dramatic lighting dim, camera repositioning, lens switch).
- Identify whether the pair is tagged as a **Negative Control** (held-out variation where no continuity defects exist).

### Step 2: Spatial Difference Analysis
- Locate candidate bounding boxes provided by the classical CV preprocessor.
- Ensure all coordinates conform to normalized floats `[ymin, xmin, ymax, xmax]` in range `[0.0, 1.0]`.
- Discard candidate regions that correspond to uniform global shifts (camera pan/tilt) or slight lens breathing.

### Step 3: Categorical Adjudication
For each remaining candidate region, inspect the visual crop and classify:
1. `Prop State`: Consumption level (glass/cup), burn level (cigarette), damage accumulation.
2. `Prop Position`: Object placed on table vs held in hand, missing items.
3. `Wardrobe`: Buttons, collars, ties, jewelry, sleeve rolled vs down.
4. `Hair & Makeup`: Hair part, perspiration, makeup smudging, wound consistency.
5. `Blocking / Eyeline`: Head turn direction, 180-degree line crosses, stance.
6. `Pass (Controlled Variation)`: Difference is attributable to camera perspective, focal length compression, or natural dramatic action.

### Step 4: Remediation Recommendation
- If defect is minor or actor is already released: Propose a **Veo Generative Cutaway** (e.g. 2s insert shot of clock, prop, or reaction).
- If defect is jarring: Flag for immediate **On-Set Retake** before scene wrap.
