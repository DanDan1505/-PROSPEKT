"""
Extract grid-zone features from Sentinel-2 and SRTM rasters.

The output is a machine-learning table where each row represents one
geographic grid zone around Tarkwa, Ghana.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window, bounds as window_bounds
from shapely.geometry import box


SENTINEL_DIR = Path("data/raw/sentinel2/tarkwa_ghana_sentinel2")
SRTM_PATH = Path("data/raw/srtm/tarkwa_ghana_srtm/SRTMGL1_003.elevation.tif")

BAND_PATHS = {
    "B2": SENTINEL_DIR / "download.B2.tif",
    "B3": SENTINEL_DIR / "download.B3.tif",
    "B4": SENTINEL_DIR / "download.B4.tif",
    "B8": SENTINEL_DIR / "download.B8.tif",
    "B11": SENTINEL_DIR / "download.B11.tif",
    "B12": SENTINEL_DIR / "download.B12.tif",
}


def read_raster(path: Path) -> tuple[np.ndarray, rasterio.Affine, str]:
    """Read one raster band as a floating-point array."""
    with rasterio.open(path) as src:
        array = src.read(1).astype("float32")
        transform = src.transform
        crs = src.crs.to_string()

        if src.nodata is not None:
            array[array == src.nodata] = np.nan

    return array, transform, crs


def calculate_slope_degrees(elevation: np.ndarray, transform: rasterio.Affine) -> np.ndarray:
    """Estimate slope in degrees from an elevation raster."""
    pixel_width_degrees = abs(transform.a)
    pixel_height_degrees = abs(transform.e)

    # Earth Engine downloaded these rasters in EPSG:4326, where units are degrees.
    # Around Ghana, one degree is close to 111 km, so this converts pixel spacing
    # into approximate meters for a simple hackathon-ready slope estimate.
    meters_per_degree = 111_320
    x_spacing = pixel_width_degrees * meters_per_degree
    y_spacing = pixel_height_degrees * meters_per_degree

    gradient_y, gradient_x = np.gradient(elevation, y_spacing, x_spacing)
    slope_radians = np.arctan(np.sqrt((gradient_x**2) + (gradient_y**2)))
    return np.degrees(slope_radians)


def safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Divide arrays while avoiding infinite values from zero denominators."""
    result = np.divide(
        numerator,
        denominator,
        out=np.full_like(numerator, np.nan, dtype="float32"),
        where=denominator != 0,
    )
    return result.astype("float32")


def mean_for_window(array: np.ndarray, window: Window) -> float:
    """Calculate the mean value inside one grid window."""
    row_start = int(window.row_off)
    row_end = int(window.row_off + window.height)
    col_start = int(window.col_off)
    col_end = int(window.col_off + window.width)
    values = array[row_start:row_end, col_start:col_end]
    return float(np.nanmean(values))


def build_feature_table(grid_size_pixels: int) -> gpd.GeoDataFrame:
    """Build a GeoDataFrame of zone-level features."""
    bands = {}
    reference_transform = None
    reference_crs = None

    for band_name, band_path in BAND_PATHS.items():
        bands[band_name], transform, crs = read_raster(band_path)
        if reference_transform is None:
            reference_transform = transform
            reference_crs = crs

    elevation, elevation_transform, _ = read_raster(SRTM_PATH)
    slope = calculate_slope_degrees(elevation, elevation_transform)

    ndvi = safe_divide(bands["B8"] - bands["B4"], bands["B8"] + bands["B4"])
    iron_oxide_index = safe_divide(bands["B4"], bands["B2"])
    clay_mineral_index = safe_divide(bands["B11"], bands["B12"])

    height, width = bands["B2"].shape
    records = []
    zone_number = 1

    for row in range(0, height, grid_size_pixels):
        for col in range(0, width, grid_size_pixels):
            window_height = min(grid_size_pixels, height - row)
            window_width = min(grid_size_pixels, width - col)
            window = Window(col, row, window_width, window_height)
            min_x, min_y, max_x, max_y = window_bounds(window, reference_transform)
            geometry = box(min_x, min_y, max_x, max_y)
            centroid = geometry.centroid

            record = {
                "zone_id": f"TZ-{zone_number:04d}",
                "center_longitude": centroid.x,
                "center_latitude": centroid.y,
                "B2_mean": mean_for_window(bands["B2"], window),
                "B3_mean": mean_for_window(bands["B3"], window),
                "B4_mean": mean_for_window(bands["B4"], window),
                "B8_mean": mean_for_window(bands["B8"], window),
                "B11_mean": mean_for_window(bands["B11"], window),
                "B12_mean": mean_for_window(bands["B12"], window),
                "ndvi_mean": mean_for_window(ndvi, window),
                "iron_oxide_index_mean": mean_for_window(iron_oxide_index, window),
                "clay_mineral_index_mean": mean_for_window(clay_mineral_index, window),
                "elevation_mean": mean_for_window(elevation, window),
                "slope_degrees_mean": mean_for_window(slope, window),
                "geometry": geometry,
            }
            records.append(record)
            zone_number += 1

    return gpd.GeoDataFrame(records, geometry="geometry", crs=reference_crs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract PROSPEKT grid-zone features from downloaded rasters."
    )
    parser.add_argument(
        "--grid-size-pixels",
        type=int,
        default=30,
        help="Width and height of each grid zone in raster pixels.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("data/processed/features/tarkwa_zone_features.csv"),
        help="Output path for the ML-ready CSV table.",
    )
    parser.add_argument(
        "--geojson-output",
        type=Path,
        default=Path("data/processed/features/tarkwa_zone_features.geojson"),
        help="Output path for the map-ready GeoJSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = build_feature_table(args.grid_size_pixels)

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    args.geojson_output.parent.mkdir(parents=True, exist_ok=True)

    csv_table = pd.DataFrame(features.drop(columns="geometry"))
    csv_table.to_csv(args.csv_output, index=False)
    features.to_file(args.geojson_output, driver="GeoJSON")

    print(f"Created {len(features)} grid zones.")
    print(f"CSV saved to: {args.csv_output}")
    print(f"GeoJSON saved to: {args.geojson_output}")


if __name__ == "__main__":
    main()
