"""
Compare Random Forest and XGBoost feature importances.

This script creates a combined CSV and chart so the two models can be explained
side by side.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare feature importance for PROSPEKT models."
    )
    parser.add_argument(
        "--random-forest-model",
        type=Path,
        default=Path("models/random_forest_tarkwa.joblib"),
        help="Saved Random Forest model.",
    )
    parser.add_argument(
        "--xgboost-model",
        type=Path,
        default=Path("models/xgboost_tarkwa.joblib"),
        help="Saved XGBoost model.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("outputs/figures/feature_importance_comparison.csv"),
        help="Output CSV for combined feature importances.",
    )
    parser.add_argument(
        "--plot-output",
        type=Path,
        default=Path("outputs/figures/feature_importance_comparison.png"),
        help="Output PNG for combined feature importances.",
    )
    return parser.parse_args()


def normalize_importance(values) -> list[float]:
    """Scale importance values so each model sums to 1."""
    total = sum(values)
    if total == 0:
        return [0.0 for _ in values]
    return [float(value / total) for value in values]


def build_importance_table(random_forest_model_path: Path, xgboost_model_path: Path) -> pd.DataFrame:
    """Load both models and return a combined feature-importance table."""
    random_forest = joblib.load(random_forest_model_path)
    xgboost = joblib.load(xgboost_model_path)

    table = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "random_forest_importance": normalize_importance(
                random_forest.feature_importances_
            ),
            "xgboost_importance": normalize_importance(xgboost.feature_importances_),
        }
    )
    table["average_importance"] = (
        table["random_forest_importance"] + table["xgboost_importance"]
    ) / 2
    return table.sort_values("average_importance", ascending=False)


def save_plot(table: pd.DataFrame, output_path: Path) -> None:
    """Save a grouped horizontal bar chart."""
    plot_table = table.sort_values("average_importance", ascending=True)
    y_positions = range(len(plot_table))
    bar_height = 0.38

    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.barh(
        [position - bar_height / 2 for position in y_positions],
        plot_table["random_forest_importance"],
        height=bar_height,
        label="Random Forest",
    )
    plt.barh(
        [position + bar_height / 2 for position in y_positions],
        plot_table["xgboost_importance"],
        height=bar_height,
        label="XGBoost",
    )
    plt.yticks(list(y_positions), plot_table["feature"])
    plt.xlabel("Normalized Importance")
    plt.ylabel("Feature")
    plt.title("Feature Importance Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def main() -> None:
    args = parse_args()
    table = build_importance_table(args.random_forest_model, args.xgboost_model)

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.csv_output, index=False)
    save_plot(table, args.plot_output)

    print(f"Combined feature importance CSV saved to: {args.csv_output}")
    print(f"Combined feature importance plot saved to: {args.plot_output}")
    print("Top combined features:")
    print(table.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
