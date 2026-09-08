# Eyeline Architecture Specification

Eyeline is an autonomous on-set continuity copilot for film script supervisors. It operates at the intersection of three foundational technologies:
1. **IBM Bob**: Agentic development environment, custom modes, skills, rules, and MCP-integrated tooling.
2. **Google ADK (Agent Development Kit)**: Code-first multi-tool agent framework executing multimodal continuity adjudication.
3. **Google Cloud Agent Builder**: Enterprise reasoning engine runtime and managed OpenAPI deployment target on Vertex AI.

---

## 1. System Overview

```
                          ┌────────────────────────────────────────────────────────┐
                          │                      FILM SET                          │
                          │   Reference Setup A  ──┬──  Current Take B             │
                          └────────────────────────┼───────────────────────────────┘
                                                   │
                                                   ▼
                                ┌────────────────────────────────────┐
                                │   Pillar 1: Classical CV Engine    │
                                │  (OpenCV-headless / scikit-image)  │
                                │   - Exposure / Histogram Matching  │
                                │   - Perspective Homography Align   │
                                │   - Spatial Difference Mask        │
                                └──────────────────┬─────────────────┘
                                                   │ Candidate Bounding Boxes
                                                   ▼
                                ┌────────────────────────────────────┐
                                │    Pillar 2: Google ADK Agent      │
                                │  (Gemini 3.8-Flash on Vertex AI)   │
                                │   - Intentional Variation Filter   │
                                │   - Incident Classification        │
                                │   - Confidence Calibration         │
                                └──────────────────┬─────────────────┘
                                                   │ Discrepancy Verdicts
                         ┌─────────────────────────┴─────────────────────────┐
                         ▼                                                   ▼
         ┌───────────────────────────────┐                   ┌───────────────────────────────┐
         │     On-Set Review Station     │                   │ Pillar 3: Generative Pickup   │
         │ (ui/index.html + app.js)      │                   │ (Google Cloud Veo on Vertex)  │
         │  - Dual Synced Viewports      │                   │  - Contextual B-Roll Inserts  │
         │  - Interactive SVG Overlay    │                   │  - Post-Wrap Editorial Patch  │
         │  - Real-Time Proof Telemetry  │                   │  - Synthetic Asset Watermark  │
         └───────────────────────────────┘                   └───────────────────────────────┘
```

---

## 2. IBM Bob Depth: Modes, Skills, Rules & MCP

Eyeline leverages IBM Bob not merely as a CLI generator, but as a fully customized, project-specific agent development platform:

### A. Custom Mode (`.bob/custom_modes.yaml`)
- **Mode Slug**: `continuity-supervisor`
- **Role**: On-set continuity engineering specialist enforcing script supervisor conventions, camera axis awareness, and Rule 7.B compliance.
- **Permission Groups**: `read`, `edit`, `execute`, `mcp`, `skill`, `todo`, `subagent`.

### B. Project Skills (`.bob/skills/continuity-reviewer/SKILL.md`)
- Anthropic-compatible procedural guide detailing:
  - Coordinate normalization (`[ymin, xmin, ymax, xmax]` in range `[0.0, 1.0]`).
  - Spatial difference inspection and high-frequency noise filtering.
  - Incident taxonomy classification (`Prop State`, `Wardrobe`, `Prop Position`, `Blocking`, `Hair/Makeup`, `Lighting`).
  - Negative control validation (guaranteeing zero false alarms on intentional shifts).

### C. Project Rules (`AGENTS.md` & `.bob/rules/`)
- Root `AGENTS.md`: Core system architecture, bounded model paradigms, coordinate conventions.
- `.bob/rules/continuity-standards.md`: Workspace rules enforcing Rule 7.B compliance and negative control invariance.
- `.bob/rules-continuity-supervisor/workflow.md`: Mode-specific adjudication decision trees.

### D. Model Context Protocol (MCP) Server (`.bob/mcp.json`)
- **Server Name**: `eyeline-inspector`
- **Implementation**: [`src/eyeline/mcp_server.py`](file:///Users/helen/workspace/eyeline/src/eyeline/mcp_server.py) (FastMCP).
- **Tools**:
  - `get_take_telemetry`: Extract clip dimensions, FPS, SMPTE timecodes.
  - `inspect_discrepancies`: Query incident logs and verification stats.
  - `verify_negative_control`: Programmatically test false-positive rates on controlled takes.

---

## 3. Google ADK & Google Cloud Agent Builder Integration

### A. Google ADK (Code-First)
Implemented in [`src/eyeline/agent.py`](file:///Users/helen/workspace/eyeline/src/eyeline/agent.py):
- Instantiates `google.adk.agents.Agent` with `Gemini(model="gemini-3.8-flash")`.
- Registers native Python tools:
  - `cv_spatial_diff`: Deterministic alignment and candidate mask generation.
  - `candidate_crop_inspect`: Multimodal crop extraction.
  - `adjudicate_incident`: Structured verdict resolution.
  - `generate_veo_pickup`: Synthetic pickup generation via Google Cloud Veo.

### B. Google Cloud Agent Builder (Managed Reasoning Engine)
Exported in [`src/eyeline/agent_builder_spec.json`](src/eyeline/agent_builder_spec.json):
- Targets Vertex AI Agent Builder Reasoning Engine runtime (`google-adk-python3.10`).
- Declares OpenAPI parameter specifications for all tools.
- Embeds explicit Rule 7.B compliance metadata verifying exclusive use of Google Cloud Vertex AI models.

---

## 4. Rule 7.B Compliance Audit

| Requirement | Eyeline Architecture | Status |
|---|---|---|
| **Permitted AI Models** | Google Cloud Gemini 3.8-Flash & Google Cloud Veo on Vertex AI | **COMPLIANT** |
| **Prohibited Models** | No YOLO, SAM, GroundingDINO, MobileNet, or non-Google AI models | **COMPLIANT** |
| **CV Preprocessing** | Classical algorithms only (`opencv-python-headless`, `scikit-image`, `scenedetect`) | **COMPLIANT** |
| **Licenses** | Apache-2.0, BSD-2, BSD-3, MIT only | **COMPLIANT** |
