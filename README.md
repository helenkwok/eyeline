# Eyeline: Autonomous Continuity Copilot for Live Sets

> **Eyeline watches continuity while the set is still standing, so a break costs one more take instead of a reshoot.**

Built for the **Agentic Cinema Hackathon** (IBM Partner Track) using **IBM Bob** and **Google Cloud AI** (Gemini 2.5 & Veo on Vertex AI).

---

## 🎬 The Core Problem

In film and episodic television production, physical continuity across takes, angles, and lighting setups is manually tracked by a script supervisor. When a continuity error escapes notice on set:
- **Discovered on set (set standing)**: Costs ~2 minutes for an immediate retake.
- **Discovered in the edit bay (set struck)**: Requires an emergency reshoot, expensive VFX cleanup, or a compromised cut.

Eyeline acts as an automated visual continuity copilot that inspects consecutive takes against reference setups in real time.

---

## 🏛️ Architecture: The Three Pillars

Eyeline enforces a strict three-part architecture ceiling to prevent feature bloat and ensure production-grade reliability:

1. **Live Setup Comparison**: Deterministic frame alignment and change segmentation paired with Gemini multimodal classification to detect physical discrepancies (props, wardrobe, blocking) between takes.
2. **Seeded Ground-Truth Benchmark**: An un-gameable empirical evaluation protocol balancing positive defect pairs with negative control pairs containing legitimate cinematic variations (lighting drift, focal changes, natural actor performance).
3. **Veo Generative Pickups**: A Vertex AI Veo fallback pipeline synthesizing ~2-second contextual insert cutaways to bridge unavoidable continuity breaks caught after striking the set.

---

## 🤖 Built with IBM Bob (IBM Partner Track)

All core subsystems in Eyeline are designed and implemented in structured, cost-capped tasks using **IBM Bob**:

- **Provenance Records**: Non-interactive command transcripts and turn logs are preserved in [`.bob-transcripts/`](.bob-transcripts/).
- **Task Queue & Budgets**: Detailed task breakdowns and Bobcoin cost caps are tracked in [`docs/BOB-TASKS.md`](docs/BOB-TASKS.md).

---

## 🔬 Benchmark & Control Pairs

A continuity detector evaluated only on positive defect pairs is trivial to game by flagging every frame. Eyeline evaluates across both:
- **Positive Pairs ($P$)**: Seeded with exactly one specific continuity defect across 7 classes.
- **Control Pairs ($C$)**: Containing only legitimate camera, lighting, and performance drift where the detector must stay completely silent.

Read the full protocol and metrics formula in [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

---

## 🚀 Quickstart

### Prerequisites
- Node.js 18+ and Python 3.10+
- FFmpeg (for video frame alignment)

### Setup & Run
```bash
# Clone repository
git clone https://github.com/helenkwok/eyeline.git
cd eyeline

# Launch the visual diff UI (demo fixture mode)
npx serve ui/
```

For full setup details and the fresh-clone rehearsal protocol, see [`docs/SUBMISSION-CHECKLIST.md`](docs/SUBMISSION-CHECKLIST.md).

---

## 📄 Documentation

- [`docs/CONCEPT.md`](docs/CONCEPT.md): System concept, user persona, and bounded model architecture.
- [`docs/BENCHMARK.md`](docs/BENCHMARK.md): Evaluation metrics, control pair taxonomy, and scoring equations.
- [`docs/BOB-TASKS.md`](docs/BOB-TASKS.md): IBM Bob task queue and cost tracking.
- [`docs/SUBMISSION-CHECKLIST.md`](docs/SUBMISSION-CHECKLIST.md): Zero-failure submission gates and rehearsal tests.

---

## ⚖️ License

Distributed under the [Apache 2.0 License](LICENSE).
