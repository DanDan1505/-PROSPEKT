"""Routes for the main PROSPEKT dashboard pages."""

import json

from flask import Blueprint, jsonify, render_template

from prospekt_dashboard.database import get_connection


main_bp = Blueprint("main", __name__)

DRIVER_COLUMNS = {
    "iron_oxide_index_mean": "Iron oxide index",
    "clay_mineral_index_mean": "Clay mineral index",
    "slope_degrees_mean": "Slope",
    "elevation_mean": "Elevation",
    "ndvi_mean": "Low vegetation exposure",
}


def normalize_feature(value, minimum, maximum):
    """Scale one feature value to 0-1 for driver ranking."""
    if maximum == minimum:
        return 0
    return (value - minimum) / (maximum - minimum)


def zone_drivers(row, feature_ranges):
    """Return the three strongest normalized driver features for a zone."""
    candidates = []
    for column, label in DRIVER_COLUMNS.items():
        minimum, maximum = feature_ranges[column]
        raw_value = float(row[column])
        normalized_value = normalize_feature(raw_value, minimum, maximum)
        if column == "ndvi_mean":
            normalized_value = 1 - normalized_value
        candidates.append((label, raw_value, normalized_value))

    sorted_candidates = sorted(candidates, key=lambda item: item[2], reverse=True)
    return [
        {
            "name": name,
            "value": round(raw_value, 3),
            "relative_strength": round(normalized_value, 3),
        }
        for name, raw_value, normalized_value in sorted_candidates[:3]
    ]


@main_bp.route("/")
def index():
    """Render the dashboard landing view."""
    return render_template("index.html")


@main_bp.route("/api/zones")
def zones_api():
    """Return prospectivity zones as GeoJSON for the Leaflet map."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                zone_id,
                center_longitude,
                center_latitude,
                random_forest_score,
                xgboost_score,
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
            FROM zones
            ORDER BY prospectivity_score DESC;
            """
        ).fetchall()

    feature_ranges = {}
    for column in DRIVER_COLUMNS:
        values = [float(row[column]) for row in rows]
        feature_ranges[column] = (min(values), max(values))

    features = []
    for row in rows:
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(row["geometry_geojson"]),
                "properties": {
                    "zone_id": row["zone_id"],
                    "center_longitude": row["center_longitude"],
                    "center_latitude": row["center_latitude"],
                    "random_forest_score": row["random_forest_score"],
                    "xgboost_score": row["xgboost_score"],
                    "prospectivity_score": row["prospectivity_score"],
                    "confidence_class": row["confidence_class"],
                    "satellite_date_range": row["satellite_date_range"],
                    "prediction_status": row["prediction_status"],
                    "ndvi_mean": row["ndvi_mean"],
                    "iron_oxide_index_mean": row["iron_oxide_index_mean"],
                    "clay_mineral_index_mean": row["clay_mineral_index_mean"],
                    "elevation_mean": row["elevation_mean"],
                    "slope_degrees_mean": row["slope_degrees_mean"],
                    "top_drivers": zone_drivers(row, feature_ranges),
                },
            }
        )

    return jsonify({"type": "FeatureCollection", "features": features})
