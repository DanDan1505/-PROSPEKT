# Phase 2 Notes

Phase 2 built the Flask dashboard for exploring prospectivity zones.

## Dashboard Run Command

```powershell
python dashboard\run.py
```

Open:

```text
http://127.0.0.1:5000/
```

## Backend

The dashboard uses SQLite:

```text
dashboard/prospekt.db
```

Tables:

```text
zones
raster_metadata
```

The loader script is:

```text
scripts/load_outputs_to_sqlite.py
```

The Flask API endpoint for map data is:

```text
/api/zones
```

It returns all 700 zones as GeoJSON.

## Frontend

Main dashboard files:

```text
dashboard/prospekt_dashboard/templates/index.html
dashboard/prospekt_dashboard/static/js/map.js
dashboard/prospekt_dashboard/static/css/styles.css
```

The map uses Leaflet. Leaflet is bundled locally:

```text
dashboard/prospekt_dashboard/static/vendor/leaflet/
```

OpenStreetMap tiles load only when internet is available. Offline, the app uses
a local fallback background while still showing the zone polygons.

## Dashboard Features

- Color-coded prospectivity zones.
- Zone click popups.
- Selected-zone detail panel.
- Top driver features per zone.
- Highest-confidence zone log.
- Plain-language query interface.
- Threshold alert system.

## Query Examples

```text
show zones with high iron oxide near Tarkwa
high confidence zones with steep slope
medium confidence clay zones
show exposed low vegetation zones
```

## Color Rules

```text
red     prospectivity_score > 70
yellow  prospectivity_score >= 40 and <= 70
green   prospectivity_score < 40
```

## Offline Behavior

Works offline:

```text
zone polygons
SQLite data
plain-language filtering
threshold alerts
zone log
selected-zone details
Leaflet CSS and JS
```

Needs internet:

```text
OpenStreetMap basemap tiles
```
