# Phase 1 Notes

Phase 1 built the data pipeline and machine learning model for the Tarkwa,
Ghana study area.

## Data Sources

- Sentinel-2 surface reflectance from Google Earth Engine.
- SRTM elevation from Google Earth Engine.
- Study area configured in `config/region_tarkwa.json`.

Downloaded data:

```text
data/raw/sentinel2/tarkwa_ghana_sentinel2/
data/raw/srtm/tarkwa_ghana_srtm/
```

## Extracted Features

Each grid zone includes:

```text
B2_mean, B3_mean, B4_mean, B8_mean, B11_mean, B12_mean
ndvi_mean
iron_oxide_index_mean
clay_mineral_index_mean
elevation_mean
slope_degrees_mean
```

Main formulas:

```text
NDVI = (B8 - B4) / (B8 + B4)
Iron oxide index = B4 / B2
Clay mineral index = B11 / B12
```

## Weak Labels

Because this is a greenfield prototype, confirmed field labels are not available
yet. The model uses weak labels from a transparent heuristic:

```text
35% iron oxide index
30% clay mineral index
15% slope
10% elevation
10% low vegetation
```

The top 25% of zones are labeled positive.

## Models

Random Forest:

```text
Accuracy: 0.950
Confusion matrix: [[103, 2], [5, 30]]
```

XGBoost:

```text
Accuracy: 0.943
Confusion matrix: [[100, 5], [3, 32]]
```

Random Forest is used as the default map model because it performed slightly
better on the weak-label test split.

## Final Outputs

```text
outputs/scores/tarkwa_final_zone_scores.csv
outputs/maps/tarkwa_final_zone_scores.geojson
outputs/maps/tarkwa_random_forest_prospectivity.tif
outputs/figures/feature_importance_comparison.png
```

## Main Scripts

```text
scripts/download_earth_engine_data.py
scripts/extract_zone_features.py
scripts/build_training_labels.py
scripts/train_random_forest.py
scripts/train_xgboost.py
scripts/create_prospectivity_outputs.py
scripts/compare_feature_importance.py
```
