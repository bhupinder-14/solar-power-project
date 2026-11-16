"""
SolarCast AI - Dataset Download Script
=======================================
Downloads the 'Renewable Power Generation and Weather Conditions' dataset from Kaggle.

Usage:
    Option 1 (Kaggle API): python scripts/download_data.py --kaggle
    Option 2 (Manual):     Download from https://www.kaggle.com/datasets/pythonafroz/renewable-power-generation-and-weather-conditions
                           and place the CSV file in ml/data/raw/

Requirements:
    - For --kaggle: Kaggle API credentials in ~/.kaggle/kaggle.json
"""

import argparse
import logging
import shutil
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "ml" / "data" / "raw"

KAGGLE_DATASET = "pythonafroz/renewable-power-generation-and-weather-conditions"


def download_with_kaggle_api() -> None:
    """Download dataset using the Kaggle API."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        logger.error(
            "kaggle package not installed. Install with: pip install kaggle"
        )
        raise

    logger.info("Authenticating with Kaggle API...")
    api = KaggleApi()
    api.authenticate()

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading dataset '{KAGGLE_DATASET}' to {RAW_DATA_DIR}...")
    api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_DATA_DIR), unzip=True)

    logger.info("Download complete. Files in raw data directory:")
    for f in RAW_DATA_DIR.iterdir():
        size_mb = f.stat().st_size / (1024 * 1024)
        logger.info(f"  {f.name} ({size_mb:.2f} MB)")


def extract_if_zipped() -> None:
    """Extract any zip files in the raw data directory."""
    for zip_file in RAW_DATA_DIR.glob("*.zip"):
        logger.info(f"Extracting {zip_file.name}...")
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(RAW_DATA_DIR)
        logger.info(f"Extracted. Removing zip file.")
        zip_file.unlink()


def check_manual_download() -> bool:
    """Check if data was manually downloaded."""
    csv_files = list(RAW_DATA_DIR.glob("*.csv"))
    if csv_files:
        logger.info(f"Found {len(csv_files)} CSV file(s) in {RAW_DATA_DIR}:")
        for f in csv_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            logger.info(f"  {f.name} ({size_mb:.2f} MB)")
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download SolarCast AI dataset")
    parser.add_argument(
        "--kaggle",
        action="store_true",
        help="Use Kaggle API to download (requires ~/.kaggle/kaggle.json)",
    )
    args = parser.parse_args()

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if check_manual_download():
        logger.info("Dataset already exists. Skipping download.")
        return

    if args.kaggle:
        download_with_kaggle_api()
    else:
        logger.info(
            "\n"
            "=" * 70 + "\n"
            "  MANUAL DOWNLOAD INSTRUCTIONS\n"
            "=" * 70 + "\n"
            "\n"
            "1. Go to: https://www.kaggle.com/datasets/pythonafroz/\n"
            "   renewable-power-generation-and-weather-conditions\n"
            "\n"
            "2. Click 'Download' (you need a free Kaggle account)\n"
            "\n"
            f"3. Extract the CSV file to:\n"
            f"   {RAW_DATA_DIR}\n"
            "\n"
            "4. Re-run this script to verify.\n"
            "\n"
            "Alternatively, run with --kaggle flag if you have\n"
            "Kaggle API credentials configured.\n"
            "=" * 70
        )


if __name__ == "__main__":
    main()
