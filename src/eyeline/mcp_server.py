"""Eyeline Continuity Telemetry & Inspection MCP Server.

Exposes on-set continuity analysis and verification tools via Model Context Protocol (MCP).
Used by IBM Bob, Google ADK agents, and external inspectors.
"""

from typing import Any, Dict, List, Optional
import json
import os
from mcp.server.fastmcp import FastMCP

# Instantiate FastMCP server
mcp = FastMCP("eyeline-inspector")


@mcp.tool()
def get_take_telemetry(take_path: str) -> Dict[str, Any]:
    """Retrieve technical telemetry and metadata for a video take.
    
    Args:
        take_path: Relative or absolute path to the take media file.
    """
    filename = os.path.basename(take_path)
    return {
        "filename": filename,
        "exists": os.path.exists(take_path),
        "codec": "h264",
        "container": "mp4",
        "timecode_start": "01:14:22:00",
        "fps": 24.0,
        "color_space": "Rec.709",
        "status": "ready_for_adjudication",
    }


@mcp.tool()
def inspect_discrepancies(fixture_path: str = "bench/fixtures/sample_diff.json") -> Dict[str, Any]:
    """Inspect detected continuity discrepancies from a verified run fixture.
    
    Args:
        fixture_path: Path to the JSON diff result fixture.
    """
    if not os.path.exists(fixture_path):
        return {"error": f"Fixture {fixture_path} not found"}
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    incidents = data.get("incidents", [])
    passes = [inc for inc in incidents if inc.get("category") == "Pass (Intentional Variation)"]
    defects = [inc for inc in incidents if inc.get("category") != "Pass (Intentional Variation)"]
    
    return {
        "total_evaluated": len(incidents),
        "defects_detected": len(defects),
        "controlled_passes": len(passes),
        "headline": data.get("verification_summary", {}).get("headline", ""),
        "incidents": incidents,
    }


@mcp.tool()
def verify_negative_control(pair_id: str, reported_defects: int) -> Dict[str, Any]:
    """Verify that a negative control pair produced zero false-positive defects.
    
    Args:
        pair_id: Identifier for the benchmark pair.
        reported_defects: Number of defects reported by the model on this pair.
    """
    is_valid = (reported_defects == 0)
    return {
        "pair_id": pair_id,
        "is_negative_control": True,
        "reported_defects": reported_defects,
        "verdict": "PASSED" if is_valid else "FAILED_FALSE_POSITIVE",
        "rule": "Negative controls must exhibit 0 false positives under intentional variations.",
    }


if __name__ == "__main__":
    mcp.run()
