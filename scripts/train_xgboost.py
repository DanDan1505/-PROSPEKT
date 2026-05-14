"""
Train an XGBoost classifier for PROSPEKT Phase 1.

XGBoost is trained on the same weak labels as the Random Forest model so their
test metrics can be compared fairly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


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
    parser = argparse.ArgumentParser(description="Train the PROSPEKT XGBoost model.")
    parser.add_argument(
        "--training-data",
        type=Path,
        default=Path("data/processed/labels/tarkwa_training_dataset.csv"),
        help="CSV containing features and weak labels.",
    )
    parser.add_argument(
        "--random-forest-metrics",
        type=Path,
        default=Path("outputs/scores/tarkwa_random_forest_metrics.json"),
        help="Random Forest metrics JSON used for comparison.",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("models/xgboost_tarkwa.joblib"),
        help="Where to save the trained XGBoost model.",
    )
    parser.add_argument(
        "--scores-output",
        type=Path,
        default=Path("outputs/scores/tarkwa_xgboost_scores.csv"),
        help="Where to save zone prospectivity scores.",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("outputs/scores/tarkwa_xgboost_metrics.json"),
        help="Where to save XGBoost evaluation metrics.",
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=Path("outputs/scores/model_comparison.csv"),
        help="Where to save Random Forest vs XGBoost comparison.",
    )
    parser.add_argument(
        "--importance-output",
        type=Path,
        default=Path("outputs/figures/xgboost_feature_importance.png"),
        help="Where to save the feature importance plot.",
    )
    return parser.parse_args()


def train_model(x_train: pd.DataFrame, y_train: pd.Series) -> XGBClassifier:
    """Train and return an XGBoost classifier."""
    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    scale_pos_weight = negative_count / positive_count

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    return model


def save_feature_importance(model: XGBClassifier, output_path: Path) -> None:
    """Save a horizontal bar chart of XGBoost feature importances."""
    importance = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(9, 6))
    plt.barh(importance["feature"], importance["importance"])
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.title("XGBoost Feature Importance")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def load_random_forest_accuracy(metrics_path: Path) -> float | None:
    """Load Random Forest accuracy if its metrics file exists."""
    if not metrics_path.exists():
        return None

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return float(metrics["accuracy"])


def main() -> None:
    args = parse_args()
    data = pd.read_csv(args.training_data)

    x = data[FEATURE_COLUMNS]
    y = data["label"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = train_model(x_train, y_train)
    predictions = model.predict(x_test)

    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, output_dict=True)
    matrix = confusion_matrix(y_test, predictions).tolist()

    probabilities = model.predict_proba(x)[:, 1]
    scores = data[
        [
            "zone_id",
            "center_longitude",
            "center_latitude",
            "weak_prospectivity_score",
            "label",
        ]
    ].copy()
    scores["xgboost_score"] = (probabilities * 100).round(2)

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.scores_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.comparison_output.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, args.model_output)
    scores.to_csv(args.scores_output, index=False)
    save_feature_importance(model, args.importance_output)

    metrics = {
        "accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": matrix,
        "feature_columns": FEATURE_COLUMNS,
        "model_parameters": model.get_params(),
    }
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    random_forest_accuracy = load_random_forest_accuracy(args.random_forest_metrics)
    comparison_rows = []
    if random_forest_accuracy is not None:
        comparison_rows.append(
            {"model": "Random Forest", "accuracy": round(random_forest_accuracy, 3)}
        )
    comparison_rows.append({"model": "XGBoost", "accuracy": round(accuracy, 3)})
    pd.DataFrame(comparison_rows).to_csv(args.comparison_output, index=False)

    print(f"Training rows: {len(x_train)}")
    print(f"Test rows: {len(x_test)}")
    print(f"Accuracy: {accuracy:.3f}")
    print("Confusion matrix:")
    print(matrix)
    print(f"Model saved to: {args.model_output}")
    print(f"Scores saved to: {args.scores_output}")
    print(f"Metrics saved to: {args.metrics_output}")
    print(f"Comparison saved to: {args.comparison_output}")
    print(f"Feature importance plot saved to: {args.importance_output}")


if __name__ == "__main__":
    main()
