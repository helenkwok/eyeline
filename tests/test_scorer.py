"""
tests/test_scorer.py — Unit tests for Eyeline's empirical benchmark scorer.
"""

from __future__ import annotations

import subprocess
import sys
from typing import List

import pytest

from bench.loader import BenchmarkPair, GroundTruthDataset, GroundTruthLabel, PairCategory
from bench.scorer import compute_iou, score_predictions


# ---------------------------------------------------------------------------
# Test IoU Math
# ---------------------------------------------------------------------------


def test_compute_iou_identical_boxes():
    box = [0.2, 0.3, 0.6, 0.8]
    assert compute_iou(box, box) == pytest.approx(1.0)


def test_compute_iou_disjoint_boxes():
    box_a = [0.0, 0.0, 0.2, 0.2]
    box_b = [0.5, 0.5, 0.8, 0.8]
    assert compute_iou(box_a, box_b) == 0.0


def test_compute_iou_partial_overlap():
    # Box A: [0.0, 0.0, 0.4, 0.4] -> area = 0.16
    # Box B: [0.2, 0.2, 0.6, 0.6] -> area = 0.16
    # Intersection: [0.2, 0.2, 0.4, 0.4] -> area = 0.04
    # Union: 0.16 + 0.16 - 0.04 = 0.28
    # IoU: 0.04 / 0.28 = 1 / 7 ≈ 0.142857
    box_a = [0.0, 0.0, 0.4, 0.4]
    box_b = [0.2, 0.2, 0.6, 0.6]
    expected = 0.04 / 0.28
    assert compute_iou(box_a, box_b) == pytest.approx(expected)


def test_compute_iou_touching_edges_zero():
    box_a = [0.0, 0.0, 0.5, 0.5]
    box_b = [0.5, 0.5, 1.0, 1.0]
    assert compute_iou(box_a, box_b) == 0.0


def test_compute_iou_invalid_or_none():
    assert compute_iou(None, [0.1, 0.1, 0.5, 0.5]) == 0.0
    assert compute_iou([0.1, 0.1, 0.5, 0.5], None) == 0.0
    assert compute_iou([0.5, 0.5, 0.1, 0.1], [0.1, 0.1, 0.5, 0.5]) == 0.0  # Inverted coords
    assert compute_iou([0.1, 0.1], [0.1, 0.1, 0.5, 0.5]) == 0.0  # Malformed length


# ---------------------------------------------------------------------------
# Test Metric Calculations with Synthetic Dataset
# ---------------------------------------------------------------------------


@pytest.fixture
def mini_dataset() -> GroundTruthDataset:
    pairs: List[BenchmarkPair] = [
        BenchmarkPair(
            pair_id="d1",
            template_id="t1",
            category=PairCategory.PROP_STATE,
            ground_truth_label=GroundTruthLabel.DEFECT,
            reference_clip="r1.mp4",
            target_clip="t1.mp4",
            timestamp_sec=2.0,
            timecode="00:00:02:00",
            bounding_box=[0.2, 0.2, 0.5, 0.5],
            defect_description="Defect 1",
        ),
        BenchmarkPair(
            pair_id="d2",
            template_id="t1",
            category=PairCategory.WARDROBE,
            ground_truth_label=GroundTruthLabel.DEFECT,
            reference_clip="r2.mp4",
            target_clip="t2.mp4",
            timestamp_sec=4.0,
            timecode="00:00:04:00",
            bounding_box=[0.1, 0.1, 0.4, 0.4],
            defect_description="Defect 2",
        ),
        BenchmarkPair(
            pair_id="c1",
            template_id="t1",
            category=PairCategory.CONTROL_LIGHTING,
            ground_truth_label=GroundTruthLabel.CONTROL,
            reference_clip="rc1.mp4",
            target_clip="tc1.mp4",
            timestamp_sec=2.0,
            timecode="00:00:02:00",
            bounding_box=None,
            control_description="Control 1",
        ),
        BenchmarkPair(
            pair_id="c2",
            template_id="t1",
            category=PairCategory.CONTROL_CAMERA_ANGLE,
            ground_truth_label=GroundTruthLabel.CONTROL,
            reference_clip="rc2.mp4",
            target_clip="tc2.mp4",
            timestamp_sec=4.0,
            timecode="00:00:04:00",
            bounding_box=None,
            control_description="Control 2",
        ),
    ]
    return GroundTruthDataset(
        schema_version="1.0.0",
        description="Mini test dataset",
        pairs=pairs,
    )


def test_score_predictions_perfect(mini_dataset):
    predictions = [
        {"pair_id": "d1", "detected": True, "timestamp_sec": 2.0, "bounding_box": [0.2, 0.2, 0.5, 0.5]},
        {"pair_id": "d2", "detected": True, "timestamp_sec": 4.0, "bounding_box": [0.1, 0.1, 0.4, 0.4]},
        {"pair_id": "c1", "detected": False},
        {"pair_id": "c2", "detected": False},
    ]
    card = score_predictions(mini_dataset, predictions)
    assert card.true_positives == 2
    assert card.localized_true_positives == 2
    assert card.false_positives == 0
    assert card.false_passes == 0
    assert card.recall == pytest.approx(1.0)
    assert card.localisation_accuracy == pytest.approx(1.0)
    assert card.control_false_positive_rate == pytest.approx(0.0)
    assert len(card.tripped_controls) == 0


def test_score_predictions_tripped_control_and_miss(mini_dataset):
    predictions = [
        {"pair_id": "d1", "detected": True, "timestamp_sec": 2.0, "bounding_box": [0.2, 0.2, 0.5, 0.5]},
        {"pair_id": "d2", "detected": False},  # Missed defect
        {"pair_id": "c1", "detected": True, "category": "control_lighting", "confidence": 0.88, "reasoning": "Falsely flagged key light"},  # Tripped
        {"pair_id": "c2", "detected": False},  # Clean pass
    ]
    card = score_predictions(mini_dataset, predictions)
    assert card.true_positives == 1
    assert card.false_passes == 1
    assert card.false_positives == 1
    assert card.recall == pytest.approx(0.5)
    assert card.control_false_positive_rate == pytest.approx(0.5)
    assert len(card.tripped_controls) == 1
    assert card.tripped_controls[0].pair_id == "c1"
    assert card.tripped_controls[0].confidence == 0.88
    assert "c1" in card.headline_statement


# ---------------------------------------------------------------------------
# Test Production Benchmark Baseline Fixture
# ---------------------------------------------------------------------------


def test_baseline_fixture_scoring():
    from bench.loader import load_benchmark_dataset
    import json

    dataset = load_benchmark_dataset("bench/truth.json")
    with open("bench/fixtures/sample_predictions.json", "r") as f:
        preds = json.load(f)

    scorecard = score_predictions(dataset, preds)
    assert scorecard.total_pairs == 32
    assert scorecard.defect_pairs_total == 16
    assert scorecard.control_pairs_total == 16
    assert scorecard.true_positives == 15
    assert scorecard.localized_true_positives == 14
    assert scorecard.false_positives == 1
    assert scorecard.false_passes == 1
    assert scorecard.recall == pytest.approx(15 / 16)
    assert scorecard.control_false_positive_rate == pytest.approx(1 / 16)
    assert len(scorecard.tripped_controls) == 1
    assert scorecard.tripped_controls[0].pair_id == "pair_017"


# ---------------------------------------------------------------------------
# Test CLI Entry Point
# ---------------------------------------------------------------------------


def test_cli_execution():
    result = subprocess.run(
        [sys.executable, "-m", "bench.scorer"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "EYELINE EMPIRICAL CONTINUITY BENCHMARK SCORECARD" in result.stdout
    assert "CANONICAL VERIFICATION STATEMENT" in result.stdout
    assert "pair_017" in result.stdout


def test_cli_json_execution():
    import json

    result = subprocess.run(
        [sys.executable, "-m", "bench.scorer", "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["total_pairs"] == 32
    assert data["recall_percent"] == 93.8
    assert data["fpr_percent"] == 6.2
