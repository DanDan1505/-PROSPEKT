"""
Build weak training labels for PROSPEKT Phase 1.

In a real exploration workflow, labels should come from ground truth:
known deposits, assay results, drill holes, or official mineral occurrence data.

For this hackathon prototype, we create transparent weak labels from remote
sensing and terrain heuristics so the ML models have a target to learn.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "B2_mean",
    "B3_mean",
    "B4_mean",
    "B8_mean",
    "B11_mean",
    "B12_mean",
    "ndvi_mean",
    "iron_oxide_index_mean",
    "clay_mineral_index_mean",
    "elevation_mean",
    "slope_degrees_mean",
]


def min_max_scale(series: pd.Series) -> pd.Series:
    """Scale a numeric column to a 0-1 range."""
    minimum = series.min()
    maximum = series.max()

    if np.isclose(maximum, minimum):
        return pd.Series(0.0, index=series.index)

    return (series - minimum) / (maximum - minimum)


def build_weak_prospectivity_score(features: pd.DataFrame) -> pd.Series:
    """Create a heuristic score from geological remote-sensing indicators."""
    iron = min_max_scale(features["iron_oxide_index_mean"])
    clay = min_max_scale(features["clay_mineral_index_mean"])
    slope = min_max_scale(features["slope_degrees_mean"])
    elevation = min_max_scale(features["elevation_mean"])
    ndvi = min_max_scale(features["ndvi_mean"])

    # High vegetation can hide exposed rock and alteration signatures.
    low_vegetation = 1 - ndvi

    # Weighted heuristic:
    # - Iron oxide and clay alteration are the strongest satellite indicators.
    # - Moderate/high slope can expose bedrock and structural features.
    # - Elevation gets a small weight as terrain context, not as direct evidence.
    # - Low vegetation helps because bare or sparse ground exposes geology better.
    score = (
        (0.35 * iron)
        + (0.30 * clay)
        + (0.15 * slope)
        + (0.10 * elevation)
        + (0.10 * low_vegetation)
    )

    return score * 100


def assign_labels(scores: pd.Series, positive_quantile: float) -> pd.Series:
    """Convert weak prospectivity scores into binary labels."""
    threshold = scores.quantile(positive_quantile)
    return (scores >= threshold).astype(int)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create weak labels for PROSPEKT model training."
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/processed/features/tarkwa_zone_features.csv"),
        help="Input feature CSV created by extract_zone_features.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/labels/tarkwa_training_dataset.csv"),
        help="Output CSV containing features plus weak labels.",
    )
    parser.add_argument(
        "--positive-quantile",
        type=float,
        default=0.75,
        help="Zones at or above this score quantile are labeled positive.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = pd.read_csv(args.features)

    weak_scores = build_weak_prospectivity_score(features)
    labels = assign_labels(weak_scores, args.positive_quantile)

    training_data = features.copy()
    training_data["weak_prospectivity_score"] = weak_scores.round(3)
    training_data["label"] = labels
    training_data["label_source"] = "weak_remote_sensing_heuristic"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    training_data.to_csv(args.output, index=False)

    positive_count = int(training_data["label"].sum())
    negative_count = int(len(training_data) - positive_count)

    print(f"Created training dataset: {args.output}")
    print(f"Rows: {len(training_data)}")
    print(f"Positive weak labels: {positive_count}")
    print(f"Negative weak labels: {negative_count}")
    print("Feature columns used for modeling:")
    for column in FEATURE_COLUMNS:
        print(f"  - {column}")


if __name__ == "__main__":
    main()
