"""
bench/run_adjudication.py — Pillar-2 Benchmark Evaluation Runner for Eyeline.

Takes Pillar-1 CV predictions and adjudicates each detected pair with Gemini
multimodal inference to filter out intentional cinematic variations (camera
angle, focal length, lighting grade, actor nuance) while preserving genuine
continuity defects.

Standalone invocation:
    python3 -m bench.run_adjudication
    python3 -m bench.run_adjudication --help
    python3 -m bench.run_adjudication \\
        --predictions-in  bench/fixtures/measured_predictions.json \\
        --predictions-out bench/fixtures/adjudicated_predictions.json \\
        --scorecard-out   bench/fixtures/adjudicated_scorecard.json \\
        --model           gemini-2.0-flash \\
        --truth           bench/truth.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the project root is on sys.path when run as a script so that
# both `bench.*` and `src.eyeline.*` resolve correctly.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from bench.loader import GroundTruthDataset, load_benchmark_dataset  # noqa: E402
from bench.scorer import (  # noqa: E402
    BenchmarkScorecard,
    format_table,
    score_predictions,
)
from eyeline.adjudicator import ContinuityAdjudication, adjudicate_pair_delta  # noqa: E402


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_adjudication",
        description=(
            "Eyeline Pillar-2 Benchmark Evaluation Runner — "
            "adjudicates Pillar-1 CV detections with Gemini multimodal inference."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--predictions-in",
        default="bench/fixtures/measured_predictions.json",
        help="Path to Pillar-1 provenanced predictions JSON (input).",
    )
    parser.add_argument(
        "--predictions-out",
        default="bench/fixtures/adjudicated_predictions.json",
        help="Path to save Pillar-2 adjudicated predictions JSON (output).",
    )
    parser.add_argument(
        "--scorecard-out",
        default="bench/fixtures/adjudicated_scorecard.json",
        help="Path to save adjudicated scorecard JSON (output).",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Gemini model identifier for Pillar-2 adjudication.",
    )
    parser.add_argument(
        "--truth",
        default="bench/truth.json",
        help="Path to ground-truth dataset JSON.",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.3,
        help="Minimum spatial IoU for a localized true positive.",
    )
    parser.add_argument(
        "--time-tolerance",
        type=float,
        default=0.5,
        help="Timestamp tolerance in seconds for defect matching.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-pair stdout logging.",
    )
    return parser


# ---------------------------------------------------------------------------
# Adjudication loop
# ---------------------------------------------------------------------------


def _adjudicate_prediction(
    pred: Dict[str, Any],
    dataset_pairs: Dict[str, Any],
    model: str,
    client=None,
    quiet: bool = False,
) -> Dict[str, Any]:
    """Run Pillar-2 adjudication on a single detected prediction record.

    Returns a (possibly updated) copy of the prediction dict.
    """
    pair_id = pred.get("pair_id", "")
    out = dict(pred)

    # Only adjudicate detections
    if not pred.get("detected", False):
        return out

    # Look up clip paths and ground-truth metadata from the dataset
    pair = dataset_pairs.get(pair_id)
    if pair is None:
        if not quiet:
            print(f"  [SKIP] {pair_id}: not found in dataset — skipping adjudication", flush=True)
        return out

    try:
        candidate_box = pred.get("bounding_box") or pair.bounding_box
        adjudication: ContinuityAdjudication = adjudicate_pair_delta(
            ref_clip_path=pair.reference_clip,
            tgt_clip_path=pair.target_clip,
            timestamp_sec=pair.timestamp_sec,
            bounding_box=candidate_box,
            template_id=pair.template_id,
            client=client,
            model=model,
        )

        if adjudication.is_continuity_defect:
            # True positive confirmed — update confidence and category from Gemini
            out["detected"] = True
            out["confidence"] = adjudication.confidence
            out["category"] = adjudication.category
            out["reasoning"] = adjudication.reasoning
            verdict = "CONFIRMED"
        else:
            # Gemini identified this as intentional variation — retract detection
            out["detected"] = False
            out["confidence"] = adjudication.confidence
            out["category"] = adjudication.category  # 'intentional_variation'
            out["reasoning"] = adjudication.reasoning
            verdict = "RETRACTED (intentional variation)"

        if not quiet:
            print(
                f"  [{verdict:36s}] {pair_id} ({pair.category.value})"
                f"  conf={adjudication.confidence:.2f}",
                flush=True,
            )

    except RuntimeError as exc:
        # Missing API key or unreadable clip — preserve original Pillar-1 verdict
        out["reasoning"] = f"Adjudication skipped: {exc}"
        if not quiet:
            print(
                f"  [SKIP — {str(exc)[:50]:50s}] {pair_id}",
                flush=True,
            )

    return out


# ---------------------------------------------------------------------------
# Before/after comparison table
# ---------------------------------------------------------------------------


def _print_comparison(
    p1_scorecard: BenchmarkScorecard,
    p2_scorecard: BenchmarkScorecard,
) -> None:
    """Print a side-by-side comparison of Pillar-1 and Pillar-1+2 scorecards."""
    sc1, sc2 = p1_scorecard, p2_scorecard

    lines = [
        "",
        "=" * 80,
        "  EYELINE PILLAR-1 vs PILLAR-1+2 COMPARISON",
        "=" * 80,
        f"  {'Metric':<40}  {'Pillar-1 CV':>12}  {'P1+P2 Gemini':>12}",
        "-" * 80,
        f"  {'Recall (TP / P)':<40}  "
        f"{sc1.true_positives}/{sc1.defect_pairs_total} = {sc1.recall * 100:>5.1f}%  "
        f"{sc2.true_positives}/{sc2.defect_pairs_total} = {sc2.recall * 100:>5.1f}%",
        f"  {'Spatial Localisation (IoU TP / spatial)':<40}  "
        f"{sc1.localized_true_positives}/{sc1.spatial_defects_total} = {sc1.localisation_accuracy * 100:>5.1f}%  "
        f"{sc2.localized_true_positives}/{sc2.spatial_defects_total} = {sc2.localisation_accuracy * 100:>5.1f}%",
        f"  {'Control False-Alarm Rate (FP / C)':<40}  "
        f"{sc1.false_positives}/{sc1.control_pairs_total} = {sc1.control_false_positive_rate * 100:>5.1f}%  "
        f"{sc2.false_positives}/{sc2.control_pairs_total} = {sc2.control_false_positive_rate * 100:>5.1f}%",
        f"  {'False Passes (FN = P − TP)':<40}  "
        f"{'':>12}  {sc1.false_passes:>11}  {sc2.false_passes:>11}".replace(
            "  " + " " * 12 + "  ", "  "
        ),
        "-" * 80,
    ]

    # Delta arrows
    recall_delta = (sc2.recall - sc1.recall) * 100
    fpr_delta = (sc2.control_false_positive_rate - sc1.control_false_positive_rate) * 100
    lines.append(
        f"  Recall delta (P2 vs P1): {recall_delta:+.1f} pp  |  "
        f"FPR delta: {fpr_delta:+.1f} pp"
    )

    if sc2.tripped_controls:
        lines.append(
            "  Remaining tripped controls after P2 adjudication: "
            + ", ".join(f"`{t.pair_id}`" for t in sc2.tripped_controls)
        )
    else:
        lines.append("  All control pairs pass after Pillar-2 adjudication ✓")

    lines.append("=" * 80)
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # ---- Load ground-truth dataset -----------------------------------------
    if not args.quiet:
        print(f"Loading ground-truth: {args.truth}", flush=True)

    dataset: GroundTruthDataset = load_benchmark_dataset(args.truth, verify_media=True)
    pair_map = {p.pair_id: p for p in dataset.pairs}

    if not args.quiet:
        positives = len(dataset.get_positive_pairs())
        controls = len(dataset.get_negative_controls())
        print(
            f"Dataset loaded — {len(dataset.pairs)} pairs "
            f"({positives} defect, {controls} control)\n",
            flush=True,
        )

    # ---- Load Pillar-1 predictions ----------------------------------------
    p1_path = Path(args.predictions_in)
    if not p1_path.exists():
        sys.exit(f"Error: Pillar-1 predictions not found: {p1_path.resolve()}\n"
                 "Run bench/run_benchmark.py first.")

    p1_raw: Dict[str, Any] = json.loads(p1_path.read_text(encoding="utf-8"))
    p1_records: List[Dict[str, Any]] = (
        p1_raw.get("predictions", []) if isinstance(p1_raw, dict) else p1_raw
    )

    detected_count = sum(1 for p in p1_records if p.get("detected", False))
    if not args.quiet:
        print(
            f"Pillar-1 predictions loaded — {len(p1_records)} pairs, "
            f"{detected_count} flagged for adjudication\n",
            flush=True,
        )

    # ---- Score Pillar-1 alone (before) ------------------------------------
    try:
        p1_scorecard = score_predictions(
            dataset=dataset,
            predictions=p1_raw,
            iou_threshold=args.iou_threshold,
            time_tolerance_sec=args.time_tolerance,
        )
    except ValueError as exc:
        sys.exit(f"Error scoring Pillar-1 predictions: {exc}")

    # ---- Run Pillar-2 adjudication ----------------------------------------
    if not args.quiet:
        print(f"Running Pillar-2 adjudication with {args.model} ...\n", flush=True)

    # Build a shared client once so all pairs reuse the same session
    client = None
    try:
        import os
        from google import genai as _genai
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            client = _genai.Client()
    except Exception:
        pass  # adjudicate_pair_delta will surface the credential error per-pair

    adjudicated: List[Dict[str, Any]] = []
    for pred in p1_records:
        adjudicated.append(
            _adjudicate_prediction(pred, pair_map, args.model, client=client, quiet=args.quiet)
        )

    # ---- Build provenanced envelope ---------------------------------------
    payload: Dict[str, Any] = {
        "detector_provenance": {
            "detector": "src.eyeline.adjudicator:adjudicate_pair_delta",
            "model": args.model,
            "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pipeline_stage": "Pillar-1 CV + Pillar-2 Gemini Multimodal Adjudication",
            "media_format": "H.264 MP4 (CRF 18)",
            "total_pairs_evaluated": len(dataset.pairs),
        },
        "predictions": adjudicated,
    }

    # ---- Save adjudicated predictions -------------------------------------
    pred_out = Path(args.predictions_out)
    pred_out.parent.mkdir(parents=True, exist_ok=True)
    pred_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"\nAdjudicated predictions saved → {pred_out}", flush=True)

    # ---- Score Pillar-1+2 (after) -----------------------------------------
    try:
        p2_scorecard = score_predictions(
            dataset=dataset,
            predictions=payload,
            iou_threshold=args.iou_threshold,
            time_tolerance_sec=args.time_tolerance,
        )
    except ValueError as exc:
        sys.exit(f"Error scoring adjudicated predictions: {exc}")

    sc_out = Path(args.scorecard_out)
    sc_out.parent.mkdir(parents=True, exist_ok=True)
    sc_out.write_text(json.dumps(p2_scorecard.to_dict(), indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"Adjudicated scorecard saved → {sc_out}\n", flush=True)

    # ---- Print scorecards & comparison ------------------------------------
    print("\n--- PILLAR-1 SCORECARD (before adjudication) ---")
    print(format_table(p1_scorecard))

    print("\n--- PILLAR-1+2 SCORECARD (after Gemini adjudication) ---")
    print(format_table(p2_scorecard))

    _print_comparison(p1_scorecard, p2_scorecard)

    return 0


if __name__ == "__main__":
    sys.exit(main())
