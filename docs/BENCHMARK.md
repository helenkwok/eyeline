# Eyeline Benchmark: Ground-Truth Continuity Protocol

---

## 1. The Core Scientific Imperative: Why Control Pairs Are Mandatory

Any anomaly detector evaluated solely on a positive test set can achieve 100% detection trivially: flag every single frame as an error. In a live production environment, a system that flags everything is worse than no system at all—it halts production with false alarms and gets immediately disabled by the crew.

To establish an honest, un-gameable claim, the Eyeline benchmark mandates an evaluation suite divided into two equal, balanced testing cohorts:

| Cohort | Contents | Target System Behavior |
|---|---|---|
| **Positive Pairs ($P$)** | Exactly one seeded continuity error + normal camera/actor variation | Detect the error and localize the region |
| **Control Pairs ($C$)** | Purely legitimate cinematographic variation (no continuity defect) | Remain completely silent (no flag) |

**Without negative control pairs, a reported detection rate is scientifically meaningless.**

---

## 2. Taxonomy of Continuity Errors (Positives)

Positive test pairs inject a single controlled defect across one of seven canonical continuity failure classes:

1. **Prop Position**: An interactive prop relocated across a surface between takes.
2. **Prop Presence**: An object present in the reference take that disappears in the current take (or vice versa).
3. **Prop State / Consumables**: Consumable items showing backward progression (e.g., wine glass fuller in take 2, cigarette longer, lit candle restored, door opened vs closed).
4. **Wardrobe & Costuming**: Apparel discrepancies (e.g., button fastened/unfastened, jacket collar popped, wristwatch side swapped, tie knot relaxed).
5. **Hair & Grooming**: Discrepancies in styling across cuts (e.g., hair parting flipped, bangs repositioned, visible makeup/sweat differences).
6. **Actor Blocking & Handedness**: Physical staging mismatches (e.g., actor holding coffee cup in right hand instead of left, crossed legs reversed).
7. **Set Dressing**: Background environmental shifts (e.g., wall picture askew, background chair repositioned, background practical lamp toggled).

---

## 3. Taxonomy of Permissible Variations (Controls)

Control pairs deliberately subject the detector to legitimate variations that occur naturally between setups and takes. The system **must not flag** any of the following:

- **Performance Variation**: Changes in actor facial expression, timing of delivery, breathing, and natural conversational cadence.
- **Camera Staging & Angles**: Moderate pan/tilt adjustments, parallax shifts, and focal length differences between takes.
- **Optics & Focus**: Shallow depth of field differences, rack focus changes, and slight lens breathing.
- **Exposure & Lighting Drift**: Ambient light fluctuations, minor key-to-fill ratio shifts, and color temperature drift.
- **Framing & Framing Scales**: Slight crop adjustments (e.g., medium shot vs medium-close).
- **Temporal Dynamics**: Motion blur, sensor noise, compression artifacts, and grain.

---

## 4. Benchmark Quantitative Metrics

Let:
- $P$ = Total count of positive pairs.
- $C$ = Total count of control pairs.
- $TP$ = Seeded continuity breaks correctly identified.
- $TP_{loc}$ = Identified breaks whose predicted bounding box overlaps the ground-truth annotation ($\text{IoU} \ge 0.3$).
- $FP$ = Control pairs erroneously generating one or more flags.
- $FN$ = Positive pairs where the continuity defect was missed ($P - TP$).

### Key Metrics Defined:

1. **Recall**:
   $$\text{Recall} = \frac{TP}{P}$$
2. **Localisation Accuracy**:
   $$\text{Localisation} = \frac{TP_{loc}}{TP}$$
   *(A flag on the wrong region or incorrect object is scored as an unlocalized detection.)*
3. **False-Positive Rate (FPR)**:
   $$\text{FPR} = \frac{FP}{C}$$
4. **False Passes (Critical Operational Risk)**:
   $$\text{False Passes} = FN = P - TP$$
   *(On set, this is the exact metric that dictates whether a broken take slips into the edit bay.)*

### The Verifiable Headline Sentence:

All published evaluation summaries must report results in this exact standardized format:

> *"Detected **TP** of **P** seeded continuity breaks (**TP_{loc}** localized), with **FP** false alarms across **C** control pairs containing legitimate variation."*

---

## 5. Execution Protocol & Integrity Rules

1. **Upfront Ground-Truth Commitment**: Ground-truth coordinates, defect descriptions, and pair categorizations are recorded in `bench/truth.json` prior to running the detector.
2. **Detector Isolation**: The detection engine has zero access to `bench/truth.json`. Evaluation is executed exclusively via an external scoring script.
3. **Complete Unfiltered Reporting**: Every evaluated pair is reported in the final metrics table. Discarding or cherry-picking pairs after evaluation is prohibited.
4. **Dual Footage Strategy & Honest Disclosure**:
   - **Quantitative Suite (HyperFrames)**: Large-scale benchmark pairs ($P$ positives and $C$ controls) are rendered deterministically using HyperFrames (headless HTML/CSS to MP4). This provides mathematically exact pixel bounding boxes for ground truth and enables precise control pair variations (lighting drift via CSS filters, camera angle shifts via 3D transforms, scale, and noise) with zero cloud quota risk.
   - **Cinematic Qualitative Suite (Google Cloud Veo on Vertex AI)**: 2–3 hero film setups are generated via Veo to demonstrate the system on authentic cinematic footage (photorealistic textures, film grain, organic human blocking) within the UI inspection stage and video trailer.
   - **Explicit Limitation Statement**: The headline quantitative metric is measured on synthetic scenes with exact ground truth; cinematic setups are qualitative demonstrations. Both are clearly labeled as synthetic across the interface and documentation.
