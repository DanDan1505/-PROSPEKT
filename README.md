# PROSPEKT

AI-powered mineral prospectivity mapping for greenfield geological exploration
in Ghana.

PROSPEKT uses free satellite and elevation data to identify zones that may be
worth field investigation. The current prototype focuses on the Tarkwa gold
belt area and includes a machine learning pipeline plus an offline-friendly
Flask dashboard.

## What It Does

```text
Satellite + elevation data
        -> geospatial feature extraction
        -> Random Forest and XGBoost models
        -> prospectivity scores from 0-100%
        -> interactive dashboard map
```

Important: the current labels are weak labels from remote-sensing heuristics,
not confirmed mineral deposits. The system prioritizes zones for investigation;
it does not prove minerals are present.

## Current Status

```text
Phase 1: Data pipeline + ML model      Complete
Phase 2: Flask dashboard               Complete
Phase 3: Arduino sensor node           Next
```

## Main Features Built

- Downloads Sentinel-2 and SRTM data for Tarkwa, Ghana.
- Extracts spectral, vegetation, alteration, elevation, and slope features.
- Trains Random Forest and XGBoost classifiers.
- Produces CSV, GeoJSON, and GeoTIFF prospectivity outputs.
- Shows prospectivity zones on a Leaflet dashboard map.
- Supports plain-language filtering such as `high iron oxide near Tarkwa`.
- Flags zones above a confidence threshold.
- Works offline for local zone data, filters, alerts, and dashboard controls.

## Quick Start

Create and activate the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the dashboard:

```powershell
python dashboard\run.py
```

Open:

```text
http://127.0.0.1:5000/
```

Keep the terminal open while using the dashboard.

## Key Outputs

```text
outputs/scores/tarkwa_final_zone_scores.csv
outputs/maps/tarkwa_final_zone_scores.geojson
outputs/maps/tarkwa_random_forest_prospectivity.tif
outputs/figures/feature_importance_comparison.png
dashboard/prospekt.db
```

## Model Results

```text
Random Forest accuracy: 0.950
XGBoost accuracy:       0.943
```

These scores are measured against weak labels, so they show how well the models
learned the prototype heuristic.

## Dashboard

The dashboard includes:

- OpenStreetMap base layer when internet is available.
- Local fallback background when offline.
- Red/yellow/green zone colors:

```text
red     score > 70%
yellow  score 40-70%
green   score < 40%
```

- Zone detail panel with coordinates, score, status, and top drivers.
- Zone log table.
- Plain-language query box.
- Threshold alert panel.

## Project Structure

```text
config/        Region settings
data/          Raw and processed geospatial data
outputs/       Maps, scores, and figures
models/        Trained ML models
scripts/       Pipeline and utility scripts
dashboard/     Flask dashboard
hardware/      Phase 3 Arduino files
docs/          More detailed phase notes
```

## More Details

- [Phase 1 Notes](docs/PHASE_1.md)
- [Phase 2 Notes](docs/PHASE_2.md)
- [Phase 3 Plan](docs/PHASE_3_PLAN.md)

## Demo Message

PROSPEKT helps exploration teams reduce risk by using satellite data and ML to
prioritize zones before field visits. Phase 3 will connect field sensor readings
back to the dashboard so zones can be upgraded from `satellite-predicted` to
`ground-confirmed`.
