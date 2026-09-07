# Eyeline: Autonomous Continuity Copilot for Live Sets

> **Eyeline watches continuity while the set is still standing, so a break costs one more take instead of a reshoot.**

Built for the **Agentic Cinema Hackathon** (IBM Partner Track) combining **IBM Bob**, **Google ADK (`google-adk`)**, **Google Cloud Agent Builder**, and **Vertex AI** (Gemini 2.5 & Veo).

---

## 🎬 The Core Problem

In film and episodic television production, physical continuity across takes, camera setups, and lighting setups is manually tracked by a script supervisor. When a continuity error escapes notice on set:
- **Discovered on set (set standing)**: Costs ~2 minutes for an immediate retake.
- **Discovered in the edit bay (set struck)**: Requires an emergency reshoot, expensive digital paint/VFX cleanup, or a compromised cut.

Eyeline acts as an automated visual continuity copilot that inspects consecutive takes against reference setups in real time.

---

## 🏛️ Architecture: The Three Pillars

Eyeline enforces a strict three-part architecture ceiling to prevent feature bloat and ensure production-grade reliability:

1. **Live Setup Comparison**: Deterministic frame alignment and candidate change segmentation paired with an agentic multimodal inspection loop to detect physical discrepancies (props, wardrobe, blocking) between takes.
2. **Seeded Ground-Truth Benchmark**: An un-gameable empirical evaluation protocol balancing positive defect pairs with negative control pairs containing legitimate cinematic variations (lighting drift, focal changes, natural actor performance).
3. **Veo Generative Pickups**: A Vertex AI Veo fallback pipeline synthesizing ~2-second contextual insert cutaways to bridge unavoidable continuity breaks caught after striking the set.

---

## 🤖 Core Technologies: IBM Bob, Google ADK & Agent Builder

| Technology | Layer | Role in Eyeline | Eligibility & Provenance |
|---|---|---|---|
| **IBM Bob** | Autonomous Development | Authors core modules across cost-capped tasks; non-interactive turn logs and provenance preserved in [`.bob-transcripts/`](.bob-transcripts/). | **IBM Partner Track Mandate**: Complete transcripts recorded and linked. |
| **Google ADK (`google-adk`)** | Agent Architecture & Orchestration | Implements `ContinuityAgent` via `google.adk.agents.Agent`, binding classical CV tools and driving the multi-step verification loop. | **Google Cloud Ecosystem**: Runtime package imported and executed. |
| **Google Cloud Agent Builder** | Enterprise Agent Hosting | Enterprise deployment target providing managed agent execution, Cloud IAM security, and session state. | **Google Cloud Ecosystem**: Production agent runtime platform. |
| **Gemini 2.5 on Vertex AI** | Multimodal Reasoning | Evaluates candidate regions to distinguish legitimate cinematographic variation from accidental defects. | **Sole AI Model Vendor**: 100% compliant with Rule 7.B. |
| **Veo on Vertex AI** | Generative Cutaway Bridge | Generates ~2s contextual insert pickups for late-caught continuity errors. | **Google Cloud Generative Media**: Integrated via Vertex AI. |
| **Classical CV Stack** | Deterministic Preprocessing | `scenedetect` (take boundaries), `opencv-python-headless` (homography/alignment), `scikit-image` (SSIM diff), `imagehash` (filtering). | **Permissive Open Source**: Apache-2.0 / BSD, zero non-Google AI models. |

---

## 🦾 Built with IBM Bob (IBM Partner Track)

Eyeline leverages **IBM Bob** not just as a one-off code generator, but as a fully tailored, project-specific development and inspection environment:

- **Custom Project Mode** ([`.bob/custom_modes.yaml`](.bob/custom_modes.yaml)): Configures the dedicated `continuity-supervisor` persona equipped with tool groups (`read`, `edit`, `execute`, `mcp`, `skill`, `todo`, `subagent`) and script supervisor domain knowledge.
- **Anthropic-Format Project Skill** ([`.bob/skills/continuity-reviewer/SKILL.md`](.bob/skills/continuity-reviewer/SKILL.md)): Embeds domain-specific inspection procedures, coordinate normalization (`[ymin, xmin, ymax, xmax]`), and negative-control verification rules.
- **Project Rules & Instructions** ([`AGENTS.md`](AGENTS.md), [`.bob/rules/continuity-standards.md`](.bob/rules/continuity-standards.md), [`.bob/rules-continuity-supervisor/workflow.md`](.bob/rules-continuity-supervisor/workflow.md)): Enforces strict Hackathon Rule 7.B compliance (Google Cloud AI only, no third-party object detectors) and negative control invariance across all agent interactions.
- **Model Context Protocol (MCP) Server** ([`.bob/mcp.json`](.bob/mcp.json) & [`src/eyeline/mcp_server.py`](src/eyeline/mcp_server.py)): Exposes native `eyeline-inspector` tools (`get_take_telemetry`, `inspect_discrepancies`, `verify_negative_control`) directly to Bob and external agents over stdio.
- **Provenance Records**: Full non-interactive command transcripts and turn logs are preserved in [`.bob-transcripts/`](.bob-transcripts/).
- **Task Queue & Budgets**: Detailed task breakdowns and Bobcoin cost caps are tracked in [`docs/BOB-TASKS.md`](docs/BOB-TASKS.md).
- **Task 1 Milestone**: Root commit [`1cbff58`](file:///Users/helen/workspace/eyeline) authored by IBM Bob delivering the visual diff UI inspection dashboard (`ui/`) for **1.61 Bobcoins** across 10 tool calls (see [`.bob-transcripts/task1-ui.json`](.bob-transcripts/task1-ui.json)).

---

## 🧠 Google ADK & Agent Builder Pipeline

The `ContinuityAgent` is instantiated in Python using **Google ADK (`google-adk`)**:

```python
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from eyeline.tools import (
    align_setup_frames,
    extract_candidate_regions,
    measure_structural_ssim,
    generate_veo_pickup,
)

# Root continuity review agent orchestrated with Google ADK
continuity_agent = Agent(
    name="eyeline_continuity_agent",
    description="Inspects film takes against reference setups to identify physical continuity errors.",
    model=Gemini(model="gemini-2.5-flash"),
    tools=[
        align_setup_frames,
        extract_candidate_regions,
        measure_structural_ssim,
        generate_veo_pickup,
    ],
    instruction="""
    Analyze candidate frame discrepancies between the Reference Setup and Current Take.
    Distinguish legitimate camera/lighting/performance variation from genuine continuity defects.
    Emit structured classification, bounding box, confidence, and recommended remediation.
    """,
)
```

The agent is deployable directly to **Google Cloud Agent Builder** / Vertex AI Agent Engine for enterprise production serving. The concrete exported manifest is tracked in [`src/eyeline/agent_builder_spec.json`](src/eyeline/agent_builder_spec.json), detailing reasoning engine configuration, tool schemas, and Rule 7.B compliance metadata. Full architectural specifications can be found in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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
- FFmpeg (for video frame extraction)

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
