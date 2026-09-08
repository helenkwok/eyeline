"""
bench/run_benchmark.py — Pillar-1 Benchmark Evaluation Runner for Eyeline.

Wires the classical CV detector (src/eyeline/vision.py::inspect_take_pair)
to the ground-truth benchmark suite (bench/loader.py::load_benchmark_dataset)
and scoring harness (bench/scorer.py::score_predictions).

Standalone invocation:
    python3 bench/run_benchmark.py
    python3 -m bench.run_benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure the project root is on sys.path when run as a script so that
# both `bench.*` and `src.eyeline.*` resolve correctly.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from bench.loader import GroundTruthDataset, load_benchmark_dataset  # noqa: E402
from bench.scorer import BenchmarkScorecard, format_table, score_predictions  # noqa: E402
from eyeline.vision import inspect_take_pair  # noqa: E402


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_benchmark",
        description="Eyeline Pillar-1 Benchmark Evaluation Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--truth",
        default="bench/truth.json",
        help="Path to ground-truth JSON",
    )
    parser.add_argument(
        "--predictions-out",
        default="bench/fixtures/measured_predictions.json",
        help="Path to save measured predictions JSON",
    )
    parser.add_argument(
        "--scorecard-out",
        default="bench/fixtures/scorecard.json",
        help="Path to save scored summary JSON",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.3,
        help="Minimum spatial IoU for a localized true positive",
    )
    parser.add_argument(
        "--time-tolerance",
        type=float,
        default=0.5,
        help="Timestamp tolerance in seconds for defect matching",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-pair stdout logging",
    )
    return parser


# ---------------------------------------------------------------------------
# Per-pair inference
# ---------------------------------------------------------------------------


def run_pair(pair: Any, quiet: bool) -> Dict[str, Any]:
    """Call inspect_take_pair for *pair* and return a scored prediction dict."""
    ref = pair.reference_clip
    tgt = pair.target_clip

    ref_exists = Path(ref).exists()
    tgt_exists = Path(tgt).exists()

    if not ref_exists or not tgt_exists:
        missing = []
        if not ref_exists:
            missing.append(f"reference_clip={ref!r}")
        if not tgt_exists:
            missing.append(f"target_clip={tgt!r}")
        if not quiet:
            print(
                f"  [SKIP] {pair.pair_id}: clip(s) not found on disk — {', '.join(missing)}",
                flush=True,
            )
        return {
            "pair_id": pair.pair_id,
            "template_id": pair.template_id,
            "ground_truth_label": pair.ground_truth_label.value,
            "category": pair.category.value,
            "detected": False,
            "timestamp_sec": pair.timestamp_sec,
            "timecode": pair.timecode,
            "bounding_box": None,
            "candidate_bounding_boxes": [],
            "alignment_error": 0.0,
            "latency_ms": 0.0,
            "confidence": 0.10,
            "reasoning": f"Clip(s) missing on disk — skipped ({', '.join(missing)})",
            "error": f"Missing clips: {', '.join(missing)}",
        }

    result = inspect_take_pair(ref, tgt, timestamp_sec=pair.timestamp_sec)

    detected: bool = result.get("detected", False)
    primary_box = result.get("primary_bounding_box")
    candidate_boxes: list = result.get("candidate_bounding_boxes", [])
    alignment_error: float = result.get("alignment_error", 0.0)
    latency_ms: float = result.get("latency_ms", 0.0)
    error_msg = result.get("error")

    if not quiet:
        status = "DETECTED" if detected else "clean"
        box_count = len(candidate_boxes)
        print(
            f"  [{status:8s}] {pair.pair_id} ({pair.category.value})"
            f"  boxes={box_count}"
            f"  align_err={alignment_error:.1f}px"
            f"  {latency_ms:.0f}ms"
            + (f"  ERR: {error_msg}" if error_msg else ""),
            flush=True,
        )

    return {
        "pair_id": pair.pair_id,
        "template_id": pair.template_id,
        "ground_truth_label": pair.ground_truth_label.value,
        "category": pair.category.value,
        "detected": detected,
        "timestamp_sec": pair.timestamp_sec,
        "timecode": pair.timecode,
        "bounding_box": primary_box,
        "candidate_bounding_boxes": candidate_boxes,
        "alignment_error": alignment_error,
        "latency_ms": latency_ms,
        "confidence": 0.90 if detected else 0.10,
        "reasoning": (
            f"Pillar-1 CV delta isolation on {pair.template_id}"
            f" at {pair.timestamp_sec:.2f}s"
        ),
    }


# ---------------------------------------------------------------------------
# Scorecard stdout renderer
# ---------------------------------------------------------------------------


def print_markdown_scorecard(scorecard: BenchmarkScorecard) -> None:
    """Print a Markdown scorecard block to stdout."""
    sc = scorecard
    recall_pct = sc.recall * 100
    loc_pct = sc.localisation_accuracy * 100
    fpr_pct = sc.control_false_positive_rate * 100

    lines = [
        "",
        "## Eyeline Pillar-1 Benchmark Results",
        "",
        f"> {sc.headline_statement}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Recall** (TP / P) | {sc.true_positives} / {sc.defect_pairs_total} = **{recall_pct:.1f}%** |",
        f"| **Spatial Localisation** (IoU TP / spatial defects) | {sc.localized_true_positives} / {sc.spatial_defects_total} = **{loc_pct:.1f}%** |",
        f"| **Control FPR** (FP / C) | {sc.false_positives} / {sc.control_pairs_total} = **{fpr_pct:.1f}%** |",
        f"| False Passes (FN) | {sc.false_passes} |",
        "",
    ]

    if sc.tripped_controls:
        lines.append("### Tripped Controls Catalogue")
        lines.append("")
        lines.append("| pair_id | template | category | confidence | reasoning |")
        lines.append("|---------|----------|----------|-----------|-----------|")
        for t in sc.tripped_controls:
            conf_str = f"{t.confidence:.2f}" if t.confidence is not None else "—"
            reason = (t.reasoning or "").replace("|", "\\|")
            lines.append(
                f"| `{t.pair_id}` | {t.template_id} | {t.category} | {conf_str} | {reason} |"
            )
        lines.append("")
    else:
        lines.append("### Tripped Controls Catalogue")
        lines.append("")
        lines.append("_None — all control pairs passed without false alarm._")
        lines.append("")

    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # ---- Load ground-truth dataset -----------------------------------------
    if not args.quiet:
        print(f"Loading ground-truth: {args.truth}", flush=True)

    dataset: GroundTruthDataset = load_benchmark_dataset(args.truth)

    if not args.quiet:
        positives = len(dataset.get_positive_pairs())
        controls = len(dataset.get_negative_controls())
        print(
            f"Dataset loaded — {len(dataset.pairs)} pairs "
            f"({positives} defect, {controls} control)\n",
            flush=True,
        )

    # ---- Run inference loop ------------------------------------------------
    predictions: List[Dict[str, Any]] = []
    for pair in dataset.pairs:
        predictions.append(run_pair(pair, quiet=args.quiet))

    # ---- Persist predictions -----------------------------------------------
    pred_out = Path(args.predictions_out)
    pred_out.parent.mkdir(parents=True, exist_ok=True)
    pred_out.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"\nPredictions saved → {pred_out}", flush=True)

    # ---- Score --------------------------------------------------------------
    scorecard = score_predictions(
        dataset=dataset,
        predictions=predictions,
        iou_threshold=args.iou_threshold,
        time_tolerance_sec=args.time_tolerance,
    )

    sc_out = Path(args.scorecard_out)
    sc_out.parent.mkdir(parents=True, exist_ok=True)
    sc_out.write_text(json.dumps(scorecard.to_dict(), indent=2), encoding="utf-8")
    if not args.quiet:
        print(f"Scorecard saved   → {sc_out}\n", flush=True)

    # ---- Print formatted Markdown scorecard --------------------------------
    print_markdown_scorecard(scorecard)

    return 0


if __name__ == "__main__":
    sys.exit(main())
