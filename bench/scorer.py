"""
bench/scorer.py — Empirical Benchmark Scoring Harness for Eyeline.

Evaluates continuity detector predictions against ground-truth pairs from bench/truth.json.
Calculates Recall, Spatial Localisation (IoU), False-Positive Rate on Controls (FPR),
and False Passes without requiring zero false alarms or artificial constraints.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bench.loader import GroundTruthDataset, GroundTruthLabel, load_benchmark_dataset


# ---------------------------------------------------------------------------
# Spatial IoU
# ---------------------------------------------------------------------------


def compute_iou(
    box_a: Optional[List[float]],
    box_b: Optional[List[float]],
) -> float:
    """
    Compute Intersection-over-Union (IoU) between two bounding boxes.

    Boxes use normalized coordinates [ymin, xmin, ymax, xmax] in range [0.0, 1.0].
    Returns 0.0 if either box is None, ill-formed, or non-overlapping.
    """
    if not box_a or not box_b or len(box_a) != 4 or len(box_b) != 4:
        return 0.0

    y1_a, x1_a, y2_a, x2_a = box_a
    y1_b, x1_b, y2_b, x2_b = box_b

    # Validate coordinate ordering
    if y1_a >= y2_a or x1_a >= x2_a or y1_b >= y2_b or x1_b >= x2_b:
        return 0.0

    # Compute intersection rectangle
    inter_y1 = max(y1_a, y1_b)
    inter_x1 = max(x1_a, x1_b)
    inter_y2 = min(y2_a, y2_b)
    inter_x2 = min(x2_a, x2_b)

    if inter_y2 <= inter_y1 or inter_x2 <= inter_x1:
        return 0.0

    inter_area = (inter_y2 - inter_y1) * (inter_x2 - inter_x1)
    area_a = (y2_a - y1_a) * (x2_a - x1_a)
    area_b = (y2_b - y1_b) * (x2_b - x1_b)
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0

    return inter_area / union_area


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class TrippedControl:
    pair_id: str
    template_id: str
    category: str
    predicted_category: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None


@dataclass
class BenchmarkScorecard:
    total_pairs: int = 0
    defect_pairs_total: int = 0         # P
    control_pairs_total: int = 0        # C
    true_positives: int = 0             # TP
    localized_true_positives: int = 0   # TP_loc
    spatial_defects_total: int = 0      # Defects where ground-truth has bbox
    false_positives: int = 0            # FP (control false alarms)
    false_passes: int = 0               # FN = P - TP
    recall: float = 0.0                 # TP / P
    localisation_accuracy: float = 0.0  # TP_loc / spatial_defects_total
    control_false_positive_rate: float = 0.0  # FPR = FP / C
    tripped_controls: List[TrippedControl] = field(default_factory=list)
    missed_defects: List[str] = field(default_factory=list)
    headline_statement: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["recall_percent"] = round(self.recall * 100, 1)
        d["localisation_percent"] = round(self.localisation_accuracy * 100, 1)
        d["fpr_percent"] = round(self.control_false_positive_rate * 100, 1)
        return d


# ---------------------------------------------------------------------------
# Scoring Engine
# ---------------------------------------------------------------------------


def score_predictions(
    dataset: GroundTruthDataset,
    predictions: List[Dict[str, Any]] | Dict[str, Dict[str, Any]],
    iou_threshold: float = 0.3,
    time_tolerance_sec: float = 0.5,
) -> BenchmarkScorecard:
    """
    Score a collection of predictions against the GroundTruthDataset.

    Args:
        dataset: Loaded GroundTruthDataset (e.g. from bench/truth.json).
        predictions: List of dicts or dict mapping pair_id -> prediction dict.
        iou_threshold: Minimum spatial IoU for localized TP (default 0.3).
        time_tolerance_sec: Max allowed discrepancy in seconds (default 0.5).

    Returns:
        Fully populated BenchmarkScorecard with exact empirical metrics.
    """
    # Normalize predictions into pair_id mapping
    pred_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(predictions, dict):
        pred_map = predictions
    elif isinstance(predictions, list):
        for p in predictions:
            pid = p.get("pair_id")
            if pid:
                pred_map[pid] = p

    p_count = 0
    c_count = 0
    tp = 0
    tp_loc = 0
    spatial_defects = 0
    fp = 0
    tripped: List[TrippedControl] = []
    missed: List[str] = []

    for pair in dataset.pairs:
        pred = pred_map.get(pair.pair_id, {})
        detected = bool(pred.get("detected", False))
        pred_time = pred.get("timestamp_sec")
        pred_box = pred.get("bounding_box")

        if pair.ground_truth_label == GroundTruthLabel.DEFECT:
            p_count += 1
            has_bbox = pair.bounding_box is not None
            if has_bbox:
                spatial_defects += 1

            # Check temporal match
            time_match = True
            if pred_time is not None:
                time_match = abs(pred_time - pair.timestamp_sec) <= time_tolerance_sec

            if detected and time_match:
                tp += 1
                if has_bbox and pred_box:
                    iou = compute_iou(pred_box, pair.bounding_box)
                    if iou >= iou_threshold:
                        tp_loc += 1
            else:
                missed.append(pair.pair_id)

        elif pair.ground_truth_label == GroundTruthLabel.CONTROL:
            c_count += 1
            if detected:
                fp += 1
                tripped.append(
                    TrippedControl(
                        pair_id=pair.pair_id,
                        template_id=pair.template_id,
                        category=pair.category.value,
                        predicted_category=pred.get("category"),
                        confidence=pred.get("confidence"),
                        reasoning=pred.get("reasoning"),
                    )
                )

    fn = p_count - tp
    recall = tp / p_count if p_count > 0 else 0.0
    loc_acc = tp_loc / spatial_defects if spatial_defects > 0 else 0.0
    fpr = fp / c_count if c_count > 0 else 0.0

    tripped_summary = (
        ", ".join(f"`{t.pair_id}` ({t.category})" for t in tripped)
        if tripped
        else "None"
    )

    headline = (
        f"Detected {tp} of {p_count} seeded continuity breaks ({tp_loc} localized), "
        f"with {fp} false alarm(s) across {c_count} control pairs containing legitimate "
        f"variation (FPR = {fpr * 100:.1f}%). Tripped controls: {tripped_summary}."
    )

    return BenchmarkScorecard(
        total_pairs=len(dataset.pairs),
        defect_pairs_total=p_count,
        control_pairs_total=c_count,
        true_positives=tp,
        localized_true_positives=tp_loc,
        spatial_defects_total=spatial_defects,
        false_positives=fp,
        false_passes=fn,
        recall=recall,
        localisation_accuracy=loc_acc,
        control_false_positive_rate=fpr,
        tripped_controls=tripped,
        missed_defects=missed,
        headline_statement=headline,
    )


# ---------------------------------------------------------------------------
# CLI Formatting
# ---------------------------------------------------------------------------


def format_table(scorecard: BenchmarkScorecard) -> str:
    lines = [
        "=" * 72,
        "  EYELINE EMPIRICAL CONTINUITY BENCHMARK SCORECARD",
        "=" * 72,
        f"  Total Pairs Evaluated       : {scorecard.total_pairs} ({scorecard.defect_pairs_total} Defect + {scorecard.control_pairs_total} Control)",
        f"  True Positives (TP)         : {scorecard.true_positives} / {scorecard.defect_pairs_total} (Recall: {scorecard.recall * 100:.1f}%)",
        f"  Spatial Localisation (IoU)  : {scorecard.localized_true_positives} / {scorecard.spatial_defects_total} ({scorecard.localisation_accuracy * 100:.1f}%)",
        f"  False Passes (FN)           : {scorecard.false_passes} (Operational risk: escaped breaks)",
        f"  Control False Alarms (FP)   : {scorecard.false_positives} / {scorecard.control_pairs_total} (FPR: {scorecard.control_false_positive_rate * 100:.1f}%)",
        "-" * 72,
        "  Tripped Controls Catalog:",
    ]
    if scorecard.tripped_controls:
        for t in scorecard.tripped_controls:
            conf_str = f" [conf={t.confidence:.2f}]" if t.confidence is not None else ""
            lines.append(f"    - {t.pair_id} ({t.template_id}): {t.category}{conf_str}")
            if t.reasoning:
                lines.append(f"      reason: {t.reasoning}")
    else:
        lines.append("    (None - all controls passed without false alarm)")

    if scorecard.missed_defects:
        lines.append(f"  Missed Defect Pairs: {', '.join(scorecard.missed_defects)}")

    lines.extend([
        "=" * 72,
        "  CANONICAL VERIFICATION STATEMENT:",
        f"  {scorecard.headline_statement}",
        "=" * 72,
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Eyeline Empirical Benchmark Scoring Harness"
    )
    parser.add_argument(
        "--truth",
        default="bench/truth.json",
        help="Path to ground-truth dataset JSON (default: bench/truth.json)",
    )
    parser.add_argument(
        "--predictions",
        default="bench/fixtures/sample_predictions.json",
        help="Path to predictions JSON (default: bench/fixtures/sample_predictions.json)",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.3,
        help="IoU threshold for spatial localisation (default: 0.3)",
    )
    parser.add_argument(
        "--time-tolerance",
        type=float,
        default=0.5,
        help="Time tolerance in seconds for defect matching (default: 0.5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON scorecard instead of human-readable table",
    )

    args = parser.parse_args()

    truth_path = Path(args.truth)
    if not truth_path.exists():
        sys.exit(f"Error: Ground-truth file not found: {truth_path.resolve()}")

    pred_path = Path(args.predictions)
    if not pred_path.exists():
        sys.exit(f"Error: Predictions file not found: {pred_path.resolve()}")

    dataset = load_benchmark_dataset(str(truth_path))
    predictions_raw = json.loads(pred_path.read_text(encoding="utf-8"))

    scorecard = score_predictions(
        dataset=dataset,
        predictions=predictions_raw,
        iou_threshold=args.iou_threshold,
        time_tolerance_sec=args.time_tolerance,
    )

    if args.json:
        print(json.dumps(scorecard.to_dict(), indent=2))
    else:
        print(format_table(scorecard))


if __name__ == "__main__":
    main()
