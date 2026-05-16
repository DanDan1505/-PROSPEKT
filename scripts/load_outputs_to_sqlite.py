"""
Load PROSPEKT Phase 1 outputs into SQLite for the Flask dashboard.

This script creates a local dashboard database from the final zone CSV,
map-ready GeoJSON, and prospectivity GeoTIFF metadata.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load PROSPEKT outputs into a SQLite dashboard database."
    )
    parser.add_argument(
        "--zone-csv",
        type=Path,
        default=Path("outputs/scores/tarkwa_final_zone_scores.csv"),
        help="Final zone-score CSV from Phase 1.",
    )
    parser.add_argument(
        "--zone-geojson",
        type=Path,
        default=Path("outputs/maps/tarkwa_final_zone_scores.geojson"),
        help="Final zone-score GeoJSON from Phase 1.",
    )
    parser.add_argument(
        "--prospectivity-geotiff",
        type=Path,
        default=Path("outputs/maps/tarkwa_random_forest_prospectivity.tif"),
        help="Final prospectivity GeoTIFF from Phase 1.",
    )
    parser.add_argument(
        "--feature-csv",
        type=Path,
        default=Path("data/processed/features/tarkwa_zone_features.csv"),
        help="Zone feature CSV from Phase 1.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("dashboard/prospekt.db"),
        help="SQLite database output path.",
    )
    return parser.parse_args()


def create_schema(connection: sqlite3.Connection) -> None:
    """Create dashboard tables from scratch."""
    connection.executescript(
        """
        DROP TABLE IF EXISTS zones;
        DROP TABLE IF EXISTS raster_metadata;

        CREATE TABLE zones (
            zone_id TEXT PRIMARY KEY,
            center_longitude REAL NOT NULL,
            center_latitude REAL NOT NULL,
            weak_prospectivity_score REAL NOT NULL,
            label INTEGER NOT NULL,
            random_forest_score REAL NOT NULL,
            xgboost_score REAL NOT NULL,
            best_model TEXT NOT NULL,
            prospectivity_score REAL NOT NULL,
            confidence_class TEXT NOT NULL,
            satellite_date_range TEXT NOT NULL,
            prediction_status TEXT NOT NULL,
            ndvi_mean REAL NOT NULL,
            iron_oxide_index_mean REAL NOT NULL,
            clay_mineral_index_mean REAL NOT NULL,
            elevation_mean REAL NOT NULL,
            slope_degrees_mean REAL NOT NULL,
            geometry_geojson TEXT NOT NULL
        );

        CREATE INDEX idx_zones_confidence_class
            ON zones (confidence_class);

        CREATE INDEX idx_zones_prospectivity_score
            ON zones (prospectivity_score);

        CREATE TABLE raster_metadata (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            path TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            crs TEXT NOT NULL,
            min_score REAL NOT NULL,
            max_score REAL NOT NULL,
            bounds_json TEXT NOT NULL
        );
        """
    )


def geometry_to_geojson_text(geometry) -> str:
    """Convert a Shapely geometry into compact GeoJSON text."""
    return json.dumps(geometry.__geo_interface__, separators=(",", ":"))


def load_zones(
    connection: sqlite3.Connection,
    zone_csv_path: Path,
    zone_geojson_path: Path,
    feature_csv_path: Path,
) -> int:
    """Load final zone scores and geometries into SQLite."""
    scores = pd.read_csv(zone_csv_path)
    features = pd.read_csv(feature_csv_path)[
        [
            "zone_id",
            "ndvi_mean",
            "iron_oxide_index_mean",
            "clay_mineral_index_mean",
            "elevation_mean",
            "slope_degrees_mean",
        ]
    ]
    zones = gpd.read_file(zone_geojson_path)[["zone_id", "geometry"]]
    merged = scores.merge(features, on="zone_id", how="left")
    merged = merged.merge(zones, on="zone_id", how="left")
    merged["geometry_geojson"] = merged["geometry"].apply(geometry_to_geojson_text)

    records = merged[
        [
            "zone_id",
            "center_longitude",
            "center_latitude",
            "weak_prospectivity_score",
            "label",
            "random_forest_score",
            "xgboost_score",
            "best_model",
            "prospectivity_score",
            "confidence_class",
            "satellite_date_range",
            "prediction_status",
            "ndvi_mean",
            "iron_oxide_index_mean",
            "clay_mineral_index_mean",
            "elevation_mean",
            "slope_degrees_mean",
            "geometry_geojson",
        ]
    ].to_records(index=False)

    connection.executemany(
        """
        INSERT INTO zones (
            zone_id,
            center_longitude,
            center_latitude,
            weak_prospectivity_score,
            label,
            random_forest_score,
            xgboost_score,
            best_model,
            prospectivity_score,
            confidence_class,
            satellite_date_range,
            prediction_status,
            ndvi_mean,
            iron_oxide_index_mean,
            clay_mineral_index_mean,
            elevation_mean,
            slope_degrees_mean,
            geometry_geojson
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        records,
    )

    return len(records)


def load_raster_metadata(
    connection: sqlite3.Connection,
    geotiff_path: Path,
) -> None:
    """Load basic GeoTIFF metadata into SQLite."""
    with rasterio.open(geotiff_path) as src:
        data = src.read(1)
        metadata = {
            "path": str(geotiff_path),
            "width": src.width,
            "height": src.height,
            "crs": src.crs.to_string(),
            "min_score": float(data.min()),
            "max_score": float(data.max()),
            "bounds_json": json.dumps(
                {
                    "min_longitude": src.bounds.left,
                    "min_latitude": src.bounds.bottom,
                    "max_longitude": src.bounds.right,
                    "max_latitude": src.bounds.top,
                }
            ),
        }

    connection.execute(
        """
        INSERT INTO raster_metadata (
            id,
            path,
            width,
            height,
            crs,
            min_score,
            max_score,
            bounds_json
        )
        VALUES (1, :path, :width, :height, :crs, :min_score, :max_score, :bounds_json);
        """,
        metadata,
    )


def main() -> None:
    args = parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(args.database) as connection:
        create_schema(connection)
        zone_count = load_zones(
            connection,
            args.zone_csv,
            args.zone_geojson,
            args.feature_csv,
        )
        load_raster_metadata(connection, args.prospectivity_geotiff)

    print(f"SQLite database created: {args.database}")
    print(f"Zones loaded: {zone_count}")
    print("Tables created: zones, raster_metadata")


if __name__ == "__main__":
    main()
