"""
bench/loader.py — Ground-truth schema & benchmark loader for Eyeline.

Pydantic v2 models that validate bench/truth.json at import time.
All bounding boxes use normalized [ymin, xmin, ymax, xmax] floats in [0.0, 1.0].
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PairCategory(str, Enum):
    # Defect categories
    PROP_STATE = "prop_state"
    PROP_POSITION = "prop_position"
    WARDROBE = "wardrobe"
    BLOCKING = "blocking"
    HAIR_MAKEUP = "hair_makeup"
    SET_DRESSING = "set_dressing"
    EYELINE_AXIS = "eyeline_axis"

    # Negative-control categories
    CONTROL_LIGHTING = "control_lighting"
    CONTROL_CAMERA_ANGLE = "control_camera_angle"
    CONTROL_FOCAL_LENGTH = "control_focal_length"
    CONTROL_ACTOR_EXPRESSION = "control_actor_expression"
    CONTROL_GRADE = "control_grade"


class GroundTruthLabel(str, Enum):
    DEFECT = "defect"
    CONTROL = "control"


# ---------------------------------------------------------------------------
# Core benchmark pair model
# ---------------------------------------------------------------------------


class BenchmarkPair(BaseModel):
    pair_id: str
    template_id: str
    category: PairCategory
    ground_truth_label: GroundTruthLabel
    reference_clip: str
    target_clip: str
    timestamp_sec: float
    timecode: str
    bounding_box: Optional[List[float]]
    # Exactly one of these will be present depending on label
    defect_description: Optional[str] = None
    control_description: Optional[str] = None

    @field_validator("bounding_box")
    @classmethod
    def _validate_bbox(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError(
                f"bounding_box must have exactly 4 elements [ymin, xmin, ymax, xmax]; got {len(v)}"
            )
        for i, coord in enumerate(v):
            if not (0.0 <= coord <= 1.0):
                raise ValueError(
                    f"bounding_box coordinate at index {i} ({coord!r}) is out of range [0.0, 1.0]"
                )
        ymin, xmin, ymax, xmax = v
        if ymin >= ymax:
            raise ValueError(f"bounding_box ymin ({ymin}) must be < ymax ({ymax})")
        if xmin >= xmax:
            raise ValueError(f"bounding_box xmin ({xmin}) must be < xmax ({xmax})")
        return v

    @model_validator(mode="after")
    def _cross_field_constraints(self) -> "BenchmarkPair":
        if self.ground_truth_label == GroundTruthLabel.DEFECT:
            if self.bounding_box is None:
                raise ValueError(
                    f"pair_id={self.pair_id!r}: bounding_box must not be None for a defect pair"
                )
            if self.defect_description is None:
                raise ValueError(
                    f"pair_id={self.pair_id!r}: defect_description required for defect pairs"
                )
        else:  # GroundTruthLabel.CONTROL
            if self.bounding_box is not None:
                raise ValueError(
                    f"pair_id={self.pair_id!r}: bounding_box must be None for control pairs"
                )
            if self.control_description is None:
                raise ValueError(
                    f"pair_id={self.pair_id!r}: control_description required for control pairs"
                )
        return self


# ---------------------------------------------------------------------------
# Top-level dataset model
# ---------------------------------------------------------------------------


class GroundTruthDataset(BaseModel):
    schema_version: str
    description: str
    pairs: List[BenchmarkPair]

    # ------------------------------------------------------------------
    # Helper accessors
    # ------------------------------------------------------------------

    def get_positive_pairs(self) -> List[BenchmarkPair]:
        """Return all pairs with ground_truth_label == 'defect'."""
        return [p for p in self.pairs if p.ground_truth_label == GroundTruthLabel.DEFECT]

    def get_negative_controls(self) -> List[BenchmarkPair]:
        """Return all pairs with ground_truth_label == 'control'."""
        return [p for p in self.pairs if p.ground_truth_label == GroundTruthLabel.CONTROL]

    def get_pairs_by_template(self, template_id: str) -> List[BenchmarkPair]:
        """Return all pairs whose template_id matches the given string."""
        return [p for p in self.pairs if p.template_id == template_id]


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_benchmark_dataset(
    truth_path: str = "bench/truth.json",
    verify_media: bool = True,
) -> GroundTruthDataset:
    """
    Load and validate bench/truth.json, returning a fully-typed GroundTruthDataset.

    Args:
        truth_path: Path to the ground-truth JSON file.
        verify_media: When True, assert that every pair's reference_clip and
            target_clip physically exist on disk.  Raises FileNotFoundError
            naming the missing path and pair_id on the first missing clip.

    Raises:
        FileNotFoundError: if *truth_path* does not exist, or (when
            verify_media=True) if any clip path is missing.
        pydantic.ValidationError: if any entry fails schema or constraint validation.
    """
    path = Path(truth_path)
    if not path.exists():
        raise FileNotFoundError(f"Ground-truth file not found: {path.resolve()}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    dataset = GroundTruthDataset.model_validate(raw)

    if verify_media:
        for pair in dataset.pairs:
            for clip_attr, clip_path in (
                ("reference_clip", pair.reference_clip),
                ("target_clip", pair.target_clip),
            ):
                if not Path(clip_path).exists():
                    raise FileNotFoundError(
                        f"[pair_id={pair.pair_id!r}] {clip_attr} not found on disk: "
                        f"{clip_path!r}"
                    )

    return dataset


# ---------------------------------------------------------------------------
# Standalone validation entrypoint
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import sys

    truth_file = sys.argv[1] if len(sys.argv) > 1 else "bench/truth.json"
    print(f"Loading benchmark dataset from: {truth_file}")

    dataset = load_benchmark_dataset(truth_file)

    positives = dataset.get_positive_pairs()
    controls = dataset.get_negative_controls()
    templates = sorted({p.template_id for p in dataset.pairs})

    print(f"\nSchema version  : {dataset.schema_version}")
    print(f"Total pairs     : {len(dataset.pairs)}")
    print(f"Defect pairs    : {len(positives)}")
    print(f"Control pairs   : {len(controls)}")
    print(f"Templates       : {len(templates)}")

    for tid in templates:
        subset = dataset.get_pairs_by_template(tid)
        defects = [p for p in subset if p.ground_truth_label == GroundTruthLabel.DEFECT]
        ctls = [p for p in subset if p.ground_truth_label == GroundTruthLabel.CONTROL]
        print(f"  {tid}: {len(subset)} pairs ({len(defects)} defect, {len(ctls)} control)")

    print("\nAll entries passed schema validation. ✓")
