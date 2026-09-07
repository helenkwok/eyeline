"""Eyeline Continuity Agent orchestrated via Google ADK (Agent Development Kit)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from google.adk.agents import Agent
    from google.adk.models.google_llm import Gemini
except ImportError:
    # Fallback placeholder when google-adk is pending installation in clean env
    Agent = None  # type: ignore
    Gemini = None  # type: ignore


class ContinuityDiscrepancy(BaseModel):
    """Structured representation of a detected continuity discrepancy."""
    id: str = Field(description="Unique incident ID")
    category: str = Field(description="Category: Prop State, Wardrobe, Prop Position, Blocking, Hair/Makeup, Set Dressing")
    timestamp_sec: float = Field(description="Active timestamp in seconds")
    timecode: str = Field(description="SMPTE timecode (HH:MM:SS:FF)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    bounding_box: Optional[List[float]] = Field(
        default=None,
        description="Normalized coordinates [ymin, xmin, ymax, xmax] if spatial",
    )
    summary: str = Field(description="Detailed technical reason for the discrepancy")
    remediation: Optional[str] = Field(
        default=None,
        description="Recommended on-set or post-production remediation",
    )


def build_continuity_agent(
    model_name: str = "gemini-2.5-flash",
    instruction: Optional[str] = None,
    tools: Optional[List[Any]] = None,
) -> Any:
    """Instantiate the Eyeline ContinuityAgent using Google ADK."""
    default_instruction = (
        "You are Eyeline's on-set continuity supervisor agent. "
        "Your role is to inspect candidate frame regions between reference setups "
        "and current takes on film productions. "
        "Carefully distinguish intentional variations (lighting, angle, camera movement, "
        "natural performance nuances) from accidental continuity errors (prop movement, "
        "liquid consumption level reversals, wardrobe displacement, blocking mismatches). "
        "Never auto-pass anomalies without human review."
    )

    if Agent is None:
        raise RuntimeError("google-adk package is required to instantiate the Agent.")

    return Agent(
        name="eyeline_continuity_agent",
        description="Autonomous on-set script supervisor copilot for visual continuity verification.",
        model=Gemini(model=model_name),
        instruction=instruction or default_instruction,
        tools=tools or [],
    )
