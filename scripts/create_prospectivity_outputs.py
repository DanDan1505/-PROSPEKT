"""
Create final PROSPEKT prospectivity outputs.

This script combines model scores with grid-zone geometry and writes:
1. A final CSV of zone scores.
2. A GeoJSON file for dashboard mapping.
3. A GeoTIFF raster map where pixel values are prospectivity scores from 0-100.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.features import rasterize


REFERENCE_RASTER = Path("data/raw/sentinel2/tarkwa_ghana_sentinel2/download.B2.tif")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create final PROSPEKT prospectivity map outputs."
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/processed/features/tarkwa_zone_features.geojson"),
        help="GeoJSON containing grid-zone geometries.",
    )
    parser.add_argument(
        "--random-forest-scores",
        type=Path,
        default=Path("outputs/scores/tarkwa_random_forest_scores.csv"),
        help="Random Forest zone score CSV.",
    )
    parser.add_argument(
        "--xgboost-scores",
        type=Path,
        default=Path("outputs/scores/tarkwa_xgboost_scores.csv"),
        help="XGBoost zone score CSV.",
    )
    parser.add_argument(
        "--final-csv",
        type=Path,
        default=Path("outputs/scores/tarkwa_final_zone_scores.csv"),
        help="Final combined zone-score CSV.",
    )
    parser.add_argument(
        "--final-geojson",
        type=Path,
        default=Path("outputs/maps/tarkwa_final_zone_scores.geojson"),
        help="Final map-ready zone-score GeoJSON.",
    )
    parser.add_argument(
        "--geotiff-output",
        type=Path,
        default=Path("outputs/maps/tarkwa_random_forest_prospectivity.tif"),
        help="Output prospectivity GeoTIFF.",
    )
    parser.add_argument(
        "--score-column",
        default="random_forest_score",
        help="Score column to rasterize into the GeoTIFF.",
    )
    return parser.parse_args()


def classify_confidence(score: float) -> str:
    """Convert a numeric score into a dashboard-friendly confidence class."""
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def build_zone_outputs(
    zones_path: Path,
    random_forest_scores_path: Path,
    xgboost_scores_path: Path,
) -> gpd.GeoDataFrame:
    """Join geometry, Random Forest scores, and XGBoost scores by zone_id."""
    zones = gpd.read_file(zones_path)
    random_forest_scores = pd.read_csv(random_forest_scores_path)
    xgboost_scores = pd.read_csv(xgboost_scores_path)[["zone_id", "xgboost_score"]]

    joined = zones.merge(random_forest_scores, on="zone_id", how="left")
    joined = joined.merge(xgboost_scores, on="zone_id", how="left")
    joined["best_model"] = "Random Forest"
    joined["prospectivity_score"] = joined["random_forest_score"]
    joined["confidence_class"] = joined["prospectivity_score"].apply(classify_confidence)
    joined["satellite_date_range"] = "2024-01-01 to 2024-12-31"
    joined["prediction_status"] = "satellite-predicted"

    return joined


def write_geotiff(
    zones: gpd.GeoDataFrame,
    output_path: Path,
    score_column: str,
) -> None:
    """Rasterize zone scores into a GeoTIFF aligned to the Sentinel-2 grid."""
    with rasterio.open(REFERENCE_RASTER) as reference:
        profile = reference.profile.copy()
        transform = reference.transform
        out_shape = (reference.height, reference.width)

    shapes = [
        (geometry, float(score))
        for geometry, score in zip(zones.geometry, zones[score_column])
        if pd.notna(score)
    ]

    raster = rasterize(
        shapes,
        out_shape=out_shape,
        transform=transform,
        fill=0,
        dtype="float32",
    )

    profile.update(
        driver="GTiff",
        count=1,
        dtype="float32",
        nodata=0,
        compress="lzw",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(raster, 1)


def main() -> None:
    args = parse_args()
    zones = build_zone_outputs(
        zones_path=args.zones,
        random_forest_scores_path=args.random_forest_scores,
        xgboost_scores_path=args.xgboost_scores,
    )

    args.final_csv.parent.mkdir(parents=True, exist_ok=True)
    args.final_geojson.parent.mkdir(parents=True, exist_ok=True)

    csv_columns = [
        "zone_id",
        "center_longitude_x",
        "center_latitude_x",
        "weak_prospectivity_score",
        "label",
        "random_forest_score",
        "xgboost_score",
        "best_model",
        "prospectivity_score",
        "confidence_class",
        "satellite_date_range",
        "prediction_status",
    ]
    output_csv = zones[csv_columns].rename(
        columns={
            "center_longitude_x": "center_longitude",
            "center_latitude_x": "center_latitude",
        }
    )
    output_csv.to_csv(args.final_csv, index=False)
    zones.to_file(args.final_geojson, driver="GeoJSON")
    write_geotiff(zones, args.geotiff_output, args.score_column)

    print(f"Final zone CSV saved to: {args.final_csv}")
    print(f"Final zone GeoJSON saved to: {args.final_geojson}")
    print(f"Prospectivity GeoTIFF saved to: {args.geotiff_output}")
    print("Confidence class counts:")
    print(output_csv["confidence_class"].value_counts().to_string())


if __name__ == "__main__":
    main()
