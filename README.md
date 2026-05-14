# PROSPEKT

PROSPEKT is an AI-powered mineral prospectivity mapping prototype for greenfield
geological exploration in Ghana. It uses free satellite and elevation data,
extracts geospatial features, trains machine learning models, and displays
prospectivity zones in a dashboard.

This is a hackathon project built in three phases:

1. Data pipeline and machine learning model.
2. Flask web dashboard.
3. Arduino-based field sensor node.

## Current Status

Phase 1 is complete.

Completed:

- Step 1: Set up project folder structure.
- Step 2: Created Python virtual environment and installed required libraries.
- Step 3: Downloaded Sentinel-2 and SRTM data for the Tarkwa, Ghana study area.
- Step 4: Extracted zone-level geospatial features.
- Step 5: Built a weakly labeled training dataset.
- Step 6: Trained a Random Forest classifier and generated zone scores.
- Step 7: Trained an XGBoost classifier and compared it with Random Forest.
- Step 8: Created final CSV, GeoJSON, and GeoTIFF prospectivity outputs.
- Step 9: Plotted and compared feature importance for both models.

Next:

- Phase 2: Build the Flask web dashboard.

## Project Structure

```text
config/                  Region configuration files
data/raw/                Original downloaded satellite and elevation data
data/interim/            Temporary cleaned or clipped data
data/processed/          ML-ready features and labels
outputs/maps/            Prospectivity GeoTIFF outputs
outputs/scores/          Zone score CSV outputs
outputs/figures/         Model plots and feature importance figures
models/                  Trained model files
notebooks/               Experiments and visual checks
scripts/                 Runnable pipeline scripts
src/prospekt/            Reusable Python package code
dashboard/               Phase 2 Flask dashboard
hardware/                Phase 3 Arduino and sensor files
tests/                   Project tests
docs/                    Extra project documentation
```

## Environment Setup

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Phase 1 Data Pipeline

### Step 3: Download Raw Data

The study area is configured in:

```text
config/region_tarkwa.json
```

The downloader script is:

```text
scripts/download_earth_engine_data.py
```

Run:

```powershell
python scripts\download_earth_engine_data.py
```

This downloads:

```text
data/raw/sentinel2/tarkwa_ghana_sentinel2/
data/raw/srtm/tarkwa_ghana_srtm/
```

Sentinel-2 bands used:

```text
B2, B3, B4, B8, B11, B12
```

SRTM band used:

```text
elevation
```

Note: Google Earth Engine requires internet access, Google authentication, and
an Earth Engine-enabled Google Cloud project.

### Step 4: Extract Features

The feature extraction script is:

```text
scripts/extract_zone_features.py
```

Run:

```powershell
python scripts\extract_zone_features.py
```

Outputs:

```text
data/processed/features/tarkwa_zone_features.csv
data/processed/features/tarkwa_zone_features.geojson
```

Features extracted per grid zone:

```text
B2_mean
B3_mean
B4_mean
B8_mean
B11_mean
B12_mean
ndvi_mean
iron_oxide_index_mean
clay_mineral_index_mean
elevation_mean
slope_degrees_mean
```

Index formulas:

```text
NDVI = (B8 - B4) / (B8 + B4)
Iron oxide index = B4 / B2
Clay mineral index = B11 / B12
```

### Step 5: Build Weak Labels

The labeling script is:

```text
scripts/build_training_labels.py
```

Run:

```powershell
python scripts\build_training_labels.py
```

Output:

```text
data/processed/labels/tarkwa_training_dataset.csv
```

Because this is a greenfield prototype, true field labels are not available yet.
The current labels are weak labels created from a transparent remote-sensing
heuristic.

Weak prospectivity score weights:

```text
35% iron oxide index
30% clay mineral index
15% slope
10% elevation
10% low vegetation
```

The top 25% of zones by weak prospectivity score are labeled as positive:

```text
label = 1  high weak-prospectivity zone
label = 0  lower weak-prospectivity zone
```

Important: these labels are not confirmed mineral deposits. They are prototype
training signals until real ground truth is available.

### Step 6: Train Random Forest

The Random Forest training script is:

```text
scripts/train_random_forest.py
```

Run:

```powershell
python scripts\train_random_forest.py
```

Outputs:

```text
models/random_forest_tarkwa.joblib
outputs/scores/tarkwa_random_forest_scores.csv
outputs/scores/tarkwa_random_forest_metrics.json
outputs/figures/random_forest_feature_importance.png
```

Model parameters:

```text
n_estimators=300        Train 300 decision trees
max_depth=None          Let trees expand until stopping rules are reached
min_samples_split=2     A node can split if it has at least 2 samples
min_samples_leaf=1      A leaf can contain 1 sample
max_features="sqrt"     Each split considers a square-root-sized feature subset
class_weight="balanced" Adjust for fewer positive labels than negative labels
random_state=42         Make results reproducible
n_jobs=-1               Use all available CPU cores
```

Current Random Forest test result:

```text
Accuracy: 0.950
Confusion matrix: [[103, 2], [5, 30]]
```

Interpretation:

```text
103 true negatives
30 true positives
2 false positives
5 false negatives
```

Important: this accuracy is measured against weak labels, not confirmed field
truth. It shows that the model learned the heuristic pattern well.

### Step 7: Train XGBoost

The XGBoost training script is:

```text
scripts/train_xgboost.py
```

Run:

```powershell
python scripts\train_xgboost.py
```

Outputs:

```text
models/xgboost_tarkwa.joblib
outputs/scores/tarkwa_xgboost_scores.csv
outputs/scores/tarkwa_xgboost_metrics.json
outputs/scores/model_comparison.csv
outputs/figures/xgboost_feature_importance.png
```

Model parameters:

```text
n_estimators=300          Train 300 boosting rounds
max_depth=4               Keep each tree fairly simple
learning_rate=0.05        Learn gradually from each tree
subsample=0.8             Train each tree on 80% of rows
colsample_bytree=0.8      Train each tree on 80% of features
objective="binary:logistic" Output probability for class 1
eval_metric="logloss"     Use binary probability loss during training
scale_pos_weight          Balance fewer positive labels against negatives
random_state=42           Make results reproducible
n_jobs=-1                 Use all available CPU cores
```

Current XGBoost test result:

```text
Accuracy: 0.943
Confusion matrix: [[100, 5], [3, 32]]
```

Model comparison:

```text
Random Forest accuracy: 0.950
XGBoost accuracy:       0.943
```

In this run, Random Forest has slightly higher accuracy. XGBoost catches more
positive weak-label zones, but also creates more false positives.

### Step 8: Create Prospectivity Outputs

The output creation script is:

```text
scripts/create_prospectivity_outputs.py
```

Run:

```powershell
python scripts\create_prospectivity_outputs.py
```

Outputs:

```text
outputs/scores/tarkwa_final_zone_scores.csv
outputs/maps/tarkwa_final_zone_scores.geojson
outputs/maps/tarkwa_random_forest_prospectivity.tif
```

The final CSV includes:

```text
zone_id
center_longitude
center_latitude
weak_prospectivity_score
label
random_forest_score
xgboost_score
best_model
prospectivity_score
confidence_class
satellite_date_range
prediction_status
```

Random Forest is currently used as the default map model because it had the
slightly higher test accuracy.

Confidence classes:

```text
high    score >= 70
medium  score >= 40 and < 70
low     score < 40
```

Current zone counts:

```text
low:    523
medium: 18
high:   159
```

The GeoTIFF stores prospectivity values from 0 to 100 and is aligned to the
downloaded Sentinel-2 raster grid.

### Step 9: Compare Feature Importance

The feature-importance comparison script is:

```text
scripts/compare_feature_importance.py
```

Run:

```powershell
python scripts\compare_feature_importance.py
```

Outputs:

```text
outputs/figures/random_forest_feature_importance.png
outputs/figures/xgboost_feature_importance.png
outputs/figures/feature_importance_comparison.csv
outputs/figures/feature_importance_comparison.png
```

Top combined features:

```text
slope_degrees_mean
elevation_mean
iron_oxide_index_mean
B2_mean
clay_mineral_index_mean
ndvi_mean
```

Interpretation:

```text
Both models relied strongly on terrain and alteration-related features.
Slope and elevation describe terrain context.
Iron oxide and clay indices describe possible alteration signatures.
NDVI helps identify where vegetation may hide exposed geology.
```

## Phase 1 Summary

Phase 1 built a complete prototype data and ML pipeline:

```text
Earth Engine data download
Sentinel-2 and SRTM raster preparation
Grid-zone feature extraction
Weak label generation for greenfield conditions
Random Forest training
XGBoost training
Model comparison
Final CSV, GeoJSON, and GeoTIFF prospectivity outputs
Feature-importance plots
```

Main final outputs:

```text
outputs/scores/tarkwa_final_zone_scores.csv
outputs/maps/tarkwa_final_zone_scores.geojson
outputs/maps/tarkwa_random_forest_prospectivity.tif
outputs/figures/feature_importance_comparison.png
```
