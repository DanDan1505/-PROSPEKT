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

- Phase 2 Step 2: Load Phase 1 outputs into SQLite.

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

## Phase 2 Web Dashboard

Phase 2 is in progress.

Completed:

- Step 1: Set up Flask app structure with an app factory and main blueprint.
- Step 2: Loaded Phase 1 output files into SQLite.
- Step 3: Rendered an interactive Leaflet.js map with color-coded zones.
- Step 4: Added a zone log table and selected-zone detail panel.
- Step 5: Added a plain-language query interface for filtering zones.
- Step 6: Added a threshold alert system for high-confidence zones.
- Step 7: Added offline-safe dashboard assets and map fallback behavior.

Next:

- Phase 3: Build the Arduino-based ground sensor node.

### Step 1: Flask App Structure

Dashboard files:

```text
dashboard/run.py
dashboard/prospekt_dashboard/__init__.py
dashboard/prospekt_dashboard/main/routes.py
dashboard/prospekt_dashboard/templates/base.html
dashboard/prospekt_dashboard/templates/index.html
dashboard/prospekt_dashboard/static/css/styles.css
```

Run the dashboard from the project root:

```powershell
python dashboard\run.py
```

Keep that terminal open while using the dashboard, then open:

```text
http://127.0.0.1:5000/
```

The app uses the Flask app factory pattern:

```text
create_app()
```

This keeps the app easier to grow as we add SQLite, map routes, query routes,
and alert routes.

Typography:

```text
Instrument Serif  Dashboard brand and display headings
IBM Plex Mono      Labels, status pills, metadata, and future data controls
System sans        Body text for readability
```

The dashboard currently loads these fonts from Google Fonts. Before the offline
demo step, the font files should be bundled locally.

### Step 2: Load Outputs Into SQLite

The SQLite loader script is:

```text
scripts/load_outputs_to_sqlite.py
```

Run:

```powershell
python scripts\load_outputs_to_sqlite.py
```

Input files:

```text
outputs/scores/tarkwa_final_zone_scores.csv
outputs/maps/tarkwa_final_zone_scores.geojson
outputs/maps/tarkwa_random_forest_prospectivity.tif
```

Output database:

```text
dashboard/prospekt.db
```

Tables:

```text
zones
raster_metadata
```

Current database contents:

```text
700 zones
159 high confidence zones
18 medium confidence zones
523 low confidence zones
```

The dashboard database helper lives in:

```text
dashboard/prospekt_dashboard/database.py
```

### Step 3: Leaflet Prospectivity Map

The dashboard now exposes zone data as GeoJSON:

```text
/api/zones
```

Frontend files:

```text
dashboard/prospekt_dashboard/templates/index.html
dashboard/prospekt_dashboard/static/js/map.js
dashboard/prospekt_dashboard/static/css/styles.css
```

Map colors:

```text
red     prospectivity_score > 70
yellow  prospectivity_score >= 40 and <= 70
green   prospectivity_score < 40
```

Each zone popup currently shows:

```text
zone_id
confidence_class
prospectivity_score
random_forest_score
xgboost_score
prediction_status
```

The map is centered on Tarkwa, Ghana:

```text
latitude:  5.3
longitude: -2.0
```

The map currently loads Leaflet and OpenStreetMap tiles from the internet.
Before the offline demo step, Leaflet files and offline basemap tiles should be
bundled locally or replaced with a local fallback layer.

### Step 4: Zone Log And Details

The dashboard now includes:

```text
Selected-zone detail panel
Highest-confidence zone log table
Click map zone to inspect details
Click table row to locate the zone on the map
```

The SQLite loader now stores feature values needed for zone explanation:

```text
ndvi_mean
iron_oxide_index_mean
clay_mineral_index_mean
elevation_mean
slope_degrees_mean
```

The selected-zone panel shows:

```text
coordinates
confidence score
satellite date range
prediction status
top driver features
```

Top drivers are ranked from normalized feature signals, with NDVI interpreted
as low vegetation exposure because exposed ground is easier to inspect from
satellite imagery.

### Step 5: Plain-Language Query Interface

The dashboard now includes a local rule-based query interface above the map.
It does not call an online AI API, so the filtering logic can still work
offline once map assets are bundled locally.

Example queries:

```text
show zones with high iron oxide near Tarkwa
high confidence zones with steep slope
medium confidence clay zones
show exposed low vegetation zones
```

Recognized query ideas:

```text
high confidence        prospectivity_score > 70
medium confidence      prospectivity_score between 40 and 70
low confidence         prospectivity_score < 40
iron                   top 25% iron oxide index
clay                   top 25% clay mineral index
slope or steep         top 25% slope
vegetation or exposed  bottom 25% NDVI
near Tarkwa            close to 5.3 latitude, -2.0 longitude
```

The filtered result updates:

```text
map polygons
zone log table
selected-zone detail panel
query result summary
```

### Step 6: Threshold Alerts

The dashboard now includes a threshold alert panel. The default threshold is:

```text
70%
```

At the default threshold, the current data flags:

```text
159 zones
```

The alert system updates:

```text
map polygon outlines
alert summary count
alert log table
```

Changing the threshold also respects any active plain-language query. For
example, if the map is filtered to zones near Tarkwa, the alert count only
applies to the currently filtered result.

### Step 7: Offline Demo Readiness

Leaflet is now bundled locally:

```text
dashboard/prospekt_dashboard/static/vendor/leaflet/leaflet.css
dashboard/prospekt_dashboard/static/vendor/leaflet/leaflet.js
dashboard/prospekt_dashboard/static/vendor/leaflet/marker-icon.png
dashboard/prospekt_dashboard/static/vendor/leaflet/marker-icon-2x.png
dashboard/prospekt_dashboard/static/vendor/leaflet/marker-shadow.png
```

The dashboard no longer depends on CDN Leaflet files.

Offline behavior:

```text
Zone polygons load from local SQLite
Plain-language filtering works locally
Threshold alerts work locally
Zone log and selected-zone details work locally
Leaflet JavaScript and CSS load locally
```

Online behavior:

```text
OpenStreetMap tiles load when internet is available
```

If internet is unavailable, the map falls back to a local neutral background
while keeping all zone polygons and dashboard controls usable.
