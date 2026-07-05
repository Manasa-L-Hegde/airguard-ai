"""
AirGuard AI — Data Preprocessing Pipeline
==========================================
Preprocesses raw CPCB real-time AQI data from long format to wide format.
Cleans, transforms, and filters the dataset for downstream analysis.

Author : AirGuard AI Team
Version: 1.0.0
"""

import os
import sys
import io
import pandas as pd
import numpy as np
from pathlib import Path

# ──────────────────────────────────────────────
# Fix Windows console encoding for Unicode output
# ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────
# 1. CONFIGURATION
# ──────────────────────────────────────────────

# Resolve project root relative to this script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "realtime_aqi.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "bengaluru_air_quality.csv"

# Pivot configuration
INDEX_COLS = ["station", "city", "state", "latitude", "longitude", "last_update"]
PIVOT_COLUMN = "pollutant_id"
PIVOT_VALUE = "pollutant_avg"

# City filter — handles both spellings used by CPCB
BENGALURU_NAMES = ["Bengaluru", "Bangalore", "bengaluru", "bangalore"]


# ──────────────────────────────────────────────
# 2. DATA LOADING
# ──────────────────────────────────────────────

def load_raw_data(filepath: Path) -> pd.DataFrame:
    """Load the raw CSV file into a pandas DataFrame."""
    if not filepath.exists():
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    df = pd.read_csv(filepath)
    print("=" * 70)
    print("STEP 1: RAW DATA LOADED SUCCESSFULLY")
    print("=" * 70)
    return df


# ──────────────────────────────────────────────
# 3. EXPLORATORY DATA INSPECTION
# ──────────────────────────────────────────────

def inspect_raw_data(df: pd.DataFrame) -> None:
    """Print key metadata about the raw dataset."""
    print("\n" + "=" * 70)
    print("STEP 2: RAW DATA INSPECTION")
    print("=" * 70)

    print(f"\n[SHAPE]   Dataset Shape        : {df.shape[0]} rows x {df.shape[1]} columns")

    print(f"\n[COLS]    Column Names         :\n   {list(df.columns)}")

    print(f"\n[TYPES]   Data Types           :")
    for col, dtype in df.dtypes.items():
        print(f"   {col:<20} -> {dtype}")

    print(f"\n[MISSING] Missing Values       :")
    missing = df.isnull().sum()
    for col, count in missing.items():
        flag = "[!]" if count > 0 else "[OK]"
        print(f"   {flag} {col:<20} -> {count}")

    print(f"\n[DUPES]   Duplicate Rows       : {df.duplicated().sum()}")

    print(f"\n[POLLUT]  Unique Pollutants    : {df['pollutant_id'].nunique()}")
    print(f"   {sorted(df['pollutant_id'].unique())}")

    print(f"\n[STNS]    Monitoring Stations  : {df['station'].nunique()}")


# ──────────────────────────────────────────────
# 4. DATA CLEANING
# ──────────────────────────────────────────────

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the raw dataframe:
      - Replace string 'NA' with np.nan
      - Convert pollutant_avg to numeric
      - Parse last_update as datetime
    """
    print("\n" + "=" * 70)
    print("STEP 3: DATA CLEANING")
    print("=" * 70)

    # 4a. Replace the string literal "NA" with proper NaN across the entire DF
    df = df.replace("NA", np.nan)
    print("   [OK] Replaced string 'NA' values with NaN")

    # 4b. Convert pollutant columns to numeric (coerce any remaining non-numeric)
    for col in ["pollutant_min", "pollutant_max", "pollutant_avg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print("   [OK] Converted pollutant_min, pollutant_max, pollutant_avg to numeric")

    # 4c. Parse last_update into datetime
    df["last_update"] = pd.to_datetime(df["last_update"], format="%d-%m-%Y %H:%M:%S", errors="coerce")
    print("   [OK] Converted last_update to datetime format")

    # Print post-cleaning missing value counts
    print(f"\n   Missing values after cleaning:")
    for col in ["pollutant_avg", "last_update"]:
        n_missing = df[col].isna().sum()
        print(f"      {col:<20} -> {n_missing} NaN values")

    return df


# ──────────────────────────────────────────────
# 5. PIVOT: LONG -> WIDE FORMAT
# ──────────────────────────────────────────────

def pivot_to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot from long format (one row per pollutant) to wide format
    (one row per station-timestamp, one column per pollutant).
    """
    print("\n" + "=" * 70)
    print("STEP 4: PIVOTING FROM LONG TO WIDE FORMAT")
    print("=" * 70)

    df_wide = df.pivot_table(
        index=INDEX_COLS,
        columns=PIVOT_COLUMN,
        values=PIVOT_VALUE,
        aggfunc="mean"   # handles duplicates during pivot via averaging
    ).reset_index()

    # Flatten column names (remove multi-index from pivot)
    df_wide.columns.name = None

    print(f"   [OK] Pivoted successfully")
    print(f"   [SHAPE] Wide-format shape: {df_wide.shape[0]} rows x {df_wide.shape[1]} columns")
    print(f"   [COLS]  Columns: {list(df_wide.columns)}")

    return df_wide


# ──────────────────────────────────────────────
# 6. DEDUPLICATION
# ──────────────────────────────────────────────

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows from the wide-format dataframe."""
    print("\n" + "=" * 70)
    print("STEP 5: REMOVING DUPLICATES")
    print("=" * 70)

    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    after = len(df)
    removed = before - after

    print(f"   Rows before : {before}")
    print(f"   Rows after  : {after}")
    print(f"   Removed     : {removed} duplicate(s)")

    return df


# ──────────────────────────────────────────────
# 7. CITY FILTER (Bengaluru / Bangalore)
# ──────────────────────────────────────────────

def filter_bengaluru(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for Bengaluru/Bangalore records.
    If no matching records exist, retain the full dataset and warn the user.
    """
    print("\n" + "=" * 70)
    print("STEP 6: FILTERING FOR BENGALURU / BANGALORE")
    print("=" * 70)

    # Case-insensitive match
    mask = df["city"].str.strip().str.lower().isin([name.lower() for name in BENGALURU_NAMES])
    df_filtered = df[mask].copy()

    if df_filtered.empty:
        print("   [WARNING] No Bengaluru/Bangalore records found in the dataset.")
        print("   [INFO]    Retaining the FULL cleaned dataset for analysis.")
        print(f"   [SHAPE]   Dataset shape: {df.shape[0]} rows x {df.shape[1]} columns")

        # List available cities for reference
        available_cities = sorted(df["city"].unique())
        print(f"\n   Available cities ({len(available_cities)}):")
        for city in available_cities:
            print(f"      - {city}")

        return df.reset_index(drop=True)
    else:
        print(f"   [OK] Found {df_filtered.shape[0]} Bengaluru record(s)")
        return df_filtered.reset_index(drop=True)


# ──────────────────────────────────────────────
# 8. SAVE PROCESSED DATA
# ──────────────────────────────────────────────

def save_processed(df: pd.DataFrame, output_path: Path) -> None:
    """Save the cleaned, wide-format dataframe to CSV."""
    print("\n" + "=" * 70)
    print("STEP 7: SAVING PROCESSED DATA")
    print("=" * 70)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
    file_size_kb = output_path.stat().st_size / 1024

    print(f"   [OK] Saved to: {output_path}")
    print(f"   [SIZE] File size: {file_size_kb:.1f} KB")


# ──────────────────────────────────────────────
# 9. FINAL SUMMARY
# ──────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Print final dataset summary statistics."""
    print("\n" + "=" * 70)
    print("STEP 8: FINAL DATASET SUMMARY")
    print("=" * 70)

    # Number of monitoring stations
    print(f"\n[STATIONS]   Number of Stations  : {df['station'].nunique()}")

    # Available pollutant columns (exclude index/metadata columns)
    pollutant_cols = [c for c in df.columns if c not in INDEX_COLS]
    print(f"\n[POLLUTANTS] Available Pollutants: {pollutant_cols}")

    # Date range
    if pd.api.types.is_datetime64_any_dtype(df["last_update"]):
        date_min = df["last_update"].min()
        date_max = df["last_update"].max()
        print(f"\n[DATES]      Date Range          : {date_min} -> {date_max}")
    else:
        print(f"\n[DATES]      Date Range          : {df['last_update'].min()} -> {df['last_update'].max()}")

    # First 10 rows
    print(f"\n[PREVIEW] First 10 Rows:")
    print("-" * 70)
    print(df.head(10).to_string(index=False))

    # Summary statistics
    print(f"\n[STATS] Summary Statistics (Pollutants):")
    print("-" * 70)
    if pollutant_cols:
        print(df[pollutant_cols].describe().round(2).to_string())
    else:
        print("   No pollutant columns found.")

    print("\n" + "=" * 70)
    print("[DONE] PREPROCESSING COMPLETE")
    print("=" * 70)


# ──────────────────────────────────────────────
# 10. MAIN PIPELINE ORCHESTRATOR
# ──────────────────────────────────────────────

def main():
    """Execute the full preprocessing pipeline."""
    print("\n" + "=" * 70)
    print("   AirGuard AI -- Data Preprocessing Pipeline")
    print("=" * 70 + "\n")

    # Step 1: Load raw data
    df = load_raw_data(RAW_DATA_PATH)

    # Step 2: Inspect raw data
    inspect_raw_data(df)

    # Step 3: Clean data (NA handling, type conversions)
    df = clean_data(df)

    # Step 4: Pivot long -> wide format
    df_wide = pivot_to_wide(df)

    # Step 5: Remove duplicates
    df_wide = remove_duplicates(df_wide)

    # Step 6: Filter for Bengaluru (graceful fallback if not found)
    df_final = filter_bengaluru(df_wide)

    # Step 7: Save processed output
    save_processed(df_final, OUTPUT_PATH)

    # Step 8: Print final summary
    print_summary(df_final)


if __name__ == "__main__":
    main()
