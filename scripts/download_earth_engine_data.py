"""
Download Sentinel-2 and SRTM data for the PROSPEKT Phase 1 study area.

This script uses Google Earth Engine, so it requires:
1. Internet access.
2. A Google account with Earth Engine access enabled.
3. A Google Cloud project ID for Earth Engine initialization.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import ee
import requests


SENTINEL2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
SRTM_IMAGE = "USGS/SRTMGL1_003"
SENTINEL2_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]


def load_region(region_path: Path) -> dict:
    """Read the region JSON file and return it as a Python dictionary."""
    with region_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_rectangle(region: dict) -> ee.Geometry:
    """Create an Earth Engine rectangle from the region bounding box."""
    bbox = region["bbox"]
    return ee.Geometry.Rectangle(
        [
            bbox["min_longitude"],
            bbox["min_latitude"],
            bbox["max_longitude"],
            bbox["max_latitude"],
        ]
    )


def initialize_earth_engine(project_id: str | None, authenticate: bool) -> None:
    """Authenticate and initialize the Earth Engine client."""
    if authenticate:
        ee.Authenticate()

    try:
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
    except Exception as error:
        message = (
            "Earth Engine could not initialize.\n\n"
            "Try these commands in your activated virtual environment:\n"
            "  earthengine authenticate\n"
            "  earthengine set_project YOUR_GOOGLE_CLOUD_PROJECT_ID\n\n"
            "Then run this script again. Original error:\n"
            f"{error}"
        )
        raise RuntimeError(message) from error


def build_sentinel2_composite(
    area: ee.Geometry,
    start_date: str,
    end_date: str,
    max_cloud_percent: int,
) -> ee.Image:
    """Build a median Sentinel-2 surface reflectance composite for the area."""
    collection = (
        ee.ImageCollection(SENTINEL2_COLLECTION)
        .filterBounds(area)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percent))
        .select(SENTINEL2_BANDS)
    )

    # Sentinel-2 surface reflectance values are stored as integers scaled by 10000.
    return collection.median().clip(area).divide(10000)


def build_srtm_elevation(area: ee.Geometry) -> ee.Image:
    """Clip the SRTM elevation raster to the study area."""
    return ee.Image(SRTM_IMAGE).select("elevation").clip(area)


def download_image_as_zip(
    image: ee.Image,
    area: ee.Geometry,
    output_zip: Path,
    scale: int,
    crs: str = "EPSG:4326",
) -> None:
    """Download an Earth Engine image as a zipped GeoTIFF."""
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    download_url = image.getDownloadURL(
        {
            "scale": scale,
            "crs": crs,
            "region": area,
            "fileFormat": "GeoTIFF",
        }
    )

    response = requests.get(download_url, timeout=120)
    response.raise_for_status()
    output_zip.write_bytes(response.content)


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    """Extract a downloaded Earth Engine ZIP file into a folder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Sentinel-2 and SRTM data for PROSPEKT."
    )
    parser.add_argument(
        "--region",
        type=Path,
        default=Path("config/region_tarkwa.json"),
        help="Path to the region JSON file.",
    )
    parser.add_argument(
        "--start-date",
        default="2024-01-01",
        help="Start date for Sentinel-2 imagery, formatted as YYYY-MM-DD.",
    )
    parser.add_argument(
        "--end-date",
        default="2024-12-31",
        help="End date for Sentinel-2 imagery, formatted as YYYY-MM-DD.",
    )
    parser.add_argument(
        "--max-cloud-percent",
        type=int,
        default=20,
        help="Maximum scene cloud cover percentage allowed.",
    )
    parser.add_argument(
        "--sentinel-scale",
        type=int,
        default=30,
        help=(
            "Sentinel-2 download resolution in meters. "
            "Use 30 for small direct downloads; 20 may exceed Earth Engine limits."
        ),
    )
    parser.add_argument(
        "--srtm-scale",
        type=int,
        default=30,
        help="SRTM download resolution in meters.",
    )
    parser.add_argument(
        "--ee-project",
        default=None,
        help="Google Cloud project ID to use for Earth Engine.",
    )
    parser.add_argument(
        "--authenticate",
        action="store_true",
        help="Run Earth Engine browser authentication before downloading.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    region = load_region(args.region)
    region_name = region["region_name"]

    initialize_earth_engine(args.ee_project, args.authenticate)
    area = build_rectangle(region)

    sentinel2 = build_sentinel2_composite(
        area=area,
        start_date=args.start_date,
        end_date=args.end_date,
        max_cloud_percent=args.max_cloud_percent,
    )
    srtm = build_srtm_elevation(area)

    sentinel_zip = Path("data/raw/sentinel2") / f"{region_name}_sentinel2.zip"
    srtm_zip = Path("data/raw/srtm") / f"{region_name}_srtm.zip"

    print("Downloading Sentinel-2 composite...")
    download_image_as_zip(sentinel2, area, sentinel_zip, scale=args.sentinel_scale)
    extract_zip(sentinel_zip, sentinel_zip.with_suffix(""))

    print("Downloading SRTM elevation...")
    download_image_as_zip(srtm, area, srtm_zip, scale=args.srtm_scale)
    extract_zip(srtm_zip, srtm_zip.with_suffix(""))

    print("Done.")
    print(f"Sentinel-2 saved under: {sentinel_zip.with_suffix('')}")
    print(f"SRTM saved under: {srtm_zip.with_suffix('')}")


if __name__ == "__main__":
    main()
