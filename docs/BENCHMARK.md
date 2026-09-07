# Eyeline Benchmark: Continuity Evaluation Protocol

---

## 1. Scientific Rationale: The Mandatory Role of Control Pairs

A continuity detector evaluated solely against a positive test set can score 100% trivially by flagging every frame as an error. On a live production set, an over-sensitive tool that halts shooting with false alarms will be immediately silenced by the crew.

To produce a defensible and assessable evaluation, the Eyeline benchmark balances two testing cohorts:

| Cohort | Contents | Target System Behavior |
|---|---|---|
| **Positive Pairs ($P$)** | Exactly one intentional continuity discrepancy plus controlled background variation | Flag the defect, identify the category, and localize the region/interval |
| **Control Pairs ($C$)** | Controlled variations representing legitimate on-set shifts (no continuity error) | Remain completely silent (no flag raised) |

**Without negative control pairs, a reported detection rate provides no evidence of discriminative capability.**

---

## 2. Taxonomy of Continuity Defects (Positives)

Positive test pairs inject a single controlled discrepancy across one of seven canonical continuity classes:

1. **Prop Position**: An interactive prop relocated across a surface between takes.
2. **Prop Presence**: An object present in the reference take that is absent in the current take (or vice versa).
3. **Prop State & Consumables**: Consumable items exhibiting backward temporal progression (e.g., coffee cup fill level increased, candle length restored, door opened vs closed).
4. **Wardrobe & Costuming**: Apparel discrepancies (e.g., button fastened/unfastened, jacket collar adjusted, wristwatch removed, glasses on/off).
5. **Hair & Grooming**: Discrepancies in styling across cuts (e.g., hair parting shifted, bangs repositioned, visible sweat differences).
6. **Actor Blocking & Handedness**: Physical staging mismatches (e.g., prop held in right hand instead of left, seated posture reversed).
7. **Set Dressing**: Background environmental shifts (e.g., wall artwork askew, background chair repositioned, practical lamp toggled).

### Annotation Representation & Spatial Scope:
- **Temporal Interval**: Every defect is annotated with an active time interval $[t_{\text{start}}, t_{\text{end}}]$.
- **Spatial Localisation Applicability**:
  - *Locally Bounded Defects* (Props, Wardrobe, Grooming, Set Dressing): Annotated with a normalized bounding box $[y_{\text{min}}, x_{\text{min}}, y_{\text{max}}, x_{\text{max}}]$ targeting the visible extent of the discrepancy.
  - *Relational / Staging Defects* (Blocking, Stance, Eyeline): May represent distributed spatial conditions where a single localized box is inapplicable; these are evaluated on temporal alignment and category attribution.

---

## 3. Taxonomy of Legitimate Variations (Controls)

Control pairs deliberately subject the detector to legitimate camera and scene variations that occur naturally between setups. The system **must not flag** any of the following:

- **Performance Variation**: Changes in actor facial expression, timing of dialogue delivery, breathing, and natural conversational pauses.
- **Camera Staging & Angles**: Moderate pan/tilt adjustments, parallax shifts, and focal length differences between setups.
- **Optics & Focus**: Shallow depth-of-field differences, rack focus transitions, and lens breathing.
- **Exposure & Lighting Drift**: Ambient light fluctuations, minor key-to-fill ratio shifts, and color temperature drift.
- **Framing & Framing Scales**: Slight crop adjustments (e.g., medium shot vs medium-close).
- **Temporal Dynamics**: Sensor grain, motion blur, and video compression artifacts.

---

## 4. Evaluation Metrics & Standards

Let:
- $P$ = Total count of positive pairs evaluated.
- $C$ = Total count of control pairs evaluated.
- $TP$ = Seeded continuity breaks correctly identified within temporal tolerance ($\pm 0.5$s).
- $TP_{\text{loc}}$ = Identified breaks whose predicted bounding box achieves spatial overlap ($\text{IoU} \ge 0.3$) with the ground-truth region (evaluated for locally bounded classes).
- $FP$ = Control pairs generating one or more false alarms.
- $FN$ = Positive pairs where the defect was missed ($P - TP$).
- $ERR$ = System abstentions, runtime exceptions, or malformed outputs (reported explicitly, never omitted).

### Core Metrics:

1. **Recall**:
   $$\text{Recall} = \frac{TP}{P}$$
2. **Localisation Accuracy**:
   $$\text{Localisation} = \frac{TP_{\text{loc}}}{TP_{\text{spatial}}}$$
   *(A detection on the wrong object or region is scored as unlocalized.)*
3. **False-Positive Rate (FPR)**:
   $$\text{FPR} = \frac{FP}{C}$$
4. **False Passes (Critical Operational Risk)**:
   $$\text{False Passes} = FN = P - TP$$
   *(On set, this represents defective footage that escapes into post-production.)*

### Standardized Headline Statement:

> *"Detected **TP** of **P** seeded continuity breaks (**TP_{loc}** localized), with **FP** false alarms across **C** control pairs containing legitimate variation."*

---

## 5. Dataset Generation & Footage Provenance

To decouple empirical measurement from external cloud quota dependencies while preserving film aesthetic validation, Eyeline uses a two-tier evaluation strategy:

### Tier 1: Quantitative Benchmark Suite (HyperFrames)
- **Role**: Systematic numerical measurement of detection recall, false passes, and control false-alarm rates across all 7 defect classes.
- **Renderer**: HyperFrames is used strictly as a local, headless HTML/CSS-to-MP4 video encoder (running in headless Chromium). It executes zero non-Google AI models or agent frameworks (compliant with Rule 7.B).
- **Annotation Methodology**: Annotations are programmatically generated and verified against rendered frames. Browser layout boxes (`getBoundingClientRect`) include padding and borders; annotations are adjusted and audited to reflect visible-object boundaries.
- **Template Separation**: Scene templates used for tuning detector prompts and classical CV thresholds are strictly separated from held-out templates used for the reported benchmark evaluation, preventing template leakage.
- **Reproducibility**: Renderings are generated under a pinned, documented environment (fixed viewport 1280x720, fixed framerate 24fps, pinned CSS fonts, fixed random seeds).

### Tier 2: Qualitative Cinematic Demonstration (Google Cloud Veo on Vertex AI)
- **Role**: Qualitative demonstration of the pipeline operating on film-style footage with photorealistic textures, optical depth of field, and natural human motion.
- **Footage Inspection**: Generated clips are manually inspected and annotated based on what actually appears on screen. The generation prompt is not treated as ground truth, ensuring unintended model artifacts are cataloged.
- **Scope**: 2–3 selected hero pairs featured in the on-set review interface and submission trailer.

### Limitations Declared Upfront:
- The headline quantitative metric is measured on synthetic scenes with programmatically generated annotations verified against rendered frames.
- Veo-generated clips are qualitative demonstrations on generated footage, not real-world production dailies.
- Transparent declaration of these boundaries allows judges to assess the system's exact capabilities without ambiguity.
