"""
AirGuard AI -- Bengaluru Historical AQI Data Generator
=======================================================
Generates 90-day historical air quality data for Bengaluru using:

  1. REAL station metadata fetched from the official CPCB / data.gov.in API
     (Ministry of Environment, Government of India)
  2. Statistically calibrated synthetic daily readings based on published
     CPCB annual AQI reports for Bengaluru (2022-2026)

WHY SYNTHETIC DATA IS NECESSARY:
---------------------------------
- OpenAQ API v3: Requires a registered API key (returns 401 without one).
- data.gov.in API: Provides ONLY a real-time snapshot (no historical endpoint).
- CPCB CCR Dashboard: Manual-only download, limited to 7-day batches.
- No free, programmatic API exists for Bengaluru historical AQI.

This script uses REAL station names, coordinates, and CPCB-published pollution
ranges to generate statistically realistic data suitable for ML prototyping
(DBSCAN clustering, Random Forest prediction).

Data Sources:
- Station metadata: data.gov.in CPCB Real-Time AQI API
- Pollution ranges: CPCB Annual AQI Bulletin (Bengaluru, 2022-2026)

Author : AirGuard AI Team
Version: 1.0.0
"""

import sys
import io
import json
import urllib.request
import urllib.error
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ================================================================
# 1. CONFIGURATION
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "bengaluru_historical_aqi.csv"

# data.gov.in CPCB API (public demo key -- no registration required)
CPCB_API_BASE = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
CPCB_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

HISTORY_DAYS = 90
RANDOM_SEED = 42

# CPCB-published Bengaluru AQI ranges (daily averages, ug/m3)
# Source: CPCB National Air Quality Index Reports, Bengaluru 2022-2026
# PM2.5 and PM10 are the primary monitoring parameters
POLLUTANT_PROFILES = {
    "PM2.5": {
        "mean": 35.0,     # CPCB Bengaluru annual mean ~30-40
        "std": 18.0,
        "min": 5.0,
        "max": 180.0,
        "seasonal_amplitude": 15.0,  # Winter peaks, monsoon lows
    },
    "PM10": {
        "mean": 65.0,     # CPCB Bengaluru annual mean ~55-75
        "std": 28.0,
        "min": 15.0,
        "max": 300.0,
        "seasonal_amplitude": 20.0,
    },
}

# Station-specific bias factors (traffic/industrial areas run higher)
STATION_BIAS = {
    "Silk Board, Bengaluru - KSPCB": 1.25,         # Heavy traffic junction
    "BTM Layout, Bengaluru - CPCB": 1.15,          # Dense residential + traffic
    "City Railway Station, Bengaluru - KSPCB": 1.20,  # Rail + road traffic
    "Peenya, Bengaluru - KSPCB": 1.30,             # Industrial area
    "Hebbal, Bengaluru - KSPCB": 1.10,             # Highway junction
    "Jayanagar 5th Block, Bengaluru - KSPCB": 0.95, # Residential
    "Hombegowda Nagar, Bengaluru - KSPCB": 0.90,   # Residential
    "Bapuji Nagar, Bengaluru - KSPCB": 1.00,       # Mixed use
    "Kasturi Nagar, Bengaluru - KSPCB": 0.95,      # Residential
    "Jigani, Bengaluru - KSPCB": 1.20,             # Industrial suburb
}


# ================================================================
# 2. FETCH REAL STATION METADATA FROM CPCB API
# ================================================================

def fetch_cpcb_station_metadata() -> list[dict]:
    """
    Fetch real Bengaluru monitoring station metadata from the
    official CPCB data.gov.in API.

    Returns a list of unique station dicts with name, lat, lon.
    Falls back to hardcoded metadata if API is unreachable.
    """
    print("=" * 70)
    print("STEP 1: FETCHING BENGALURU STATION METADATA FROM CPCB API")
    print("=" * 70)

    stations_seen = {}
    offset = 0
    page_size = 10  # data.gov.in caps at 10 per page

    try:
        while True:
            url = (
                f"{CPCB_API_BASE}"
                f"?api-key={CPCB_API_KEY}"
                f"&format=json"
                f"&limit={page_size}"
                f"&offset={offset}"
                f"&filters[city]=Bengaluru"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "AirGuardAI/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            records = data.get("records", [])
            if not records:
                break

            for rec in records:
                stn_name = rec["station"]
                if stn_name not in stations_seen:
                    stations_seen[stn_name] = {
                        "station_name": stn_name,
                        "latitude": float(rec["latitude"]),
                        "longitude": float(rec["longitude"]),
                    }

            total = int(data.get("total", 0))
            offset += page_size
            if offset >= total:
                break

        if stations_seen:
            print(f"   [OK] Fetched {len(stations_seen)} stations from CPCB API")
            for stn in stations_seen.values():
                print(f"      - {stn['station_name']} ({stn['latitude']}, {stn['longitude']})")
            return list(stations_seen.values())

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as e:
        print(f"   [WARNING] CPCB API unavailable: {e}")

    # Fallback: hardcoded real CPCB station metadata
    print("   [FALLBACK] Using hardcoded CPCB Bengaluru station metadata")
    return _get_fallback_stations()


def _get_fallback_stations() -> list[dict]:
    """
    Hardcoded Bengaluru CPCB/KSPCB station metadata.
    Source: CPCB CAAQMS Network, verified via data.gov.in API (July 2026).
    """
    return [
        {"station_name": "BTM Layout, Bengaluru - CPCB",             "latitude": 12.913522, "longitude": 77.595080},
        {"station_name": "Silk Board, Bengaluru - KSPCB",            "latitude": 12.917348, "longitude": 77.622813},
        {"station_name": "City Railway Station, Bengaluru - KSPCB",  "latitude": 12.975684, "longitude": 77.566075},
        {"station_name": "Hebbal, Bengaluru - KSPCB",                "latitude": 13.029152, "longitude": 77.585901},
        {"station_name": "Jayanagar 5th Block, Bengaluru - KSPCB",   "latitude": 12.920984, "longitude": 77.584908},
        {"station_name": "Hombegowda Nagar, Bengaluru - KSPCB",      "latitude": 12.938539, "longitude": 77.590100},
        {"station_name": "Bapuji Nagar, Bengaluru - KSPCB",          "latitude": 12.951913, "longitude": 77.539784},
        {"station_name": "Kasturi Nagar, Bengaluru - KSPCB",         "latitude": 13.003872, "longitude": 77.664217},
        {"station_name": "Jigani, Bengaluru - KSPCB",                "latitude": 12.781628, "longitude": 77.629915},
        {"station_name": "Peenya, Bengaluru - KSPCB",                "latitude": 13.030000, "longitude": 77.520000},
    ]


# ================================================================
# 3. GENERATE HISTORICAL DATA
# ================================================================

def generate_historical_data(stations: list[dict]) -> pd.DataFrame:
    """
    Generate 90-day historical PM2.5 and PM10 data for each station.

    The generation model incorporates:
      - CPCB-published annual mean and variance for Bengaluru
      - Seasonal variation (monsoon suppression, winter peaks)
      - Station-specific bias (traffic/industrial areas higher)
      - Day-to-day autocorrelation (weather persistence)
      - Random sensor noise (~5% of reading)
      - Realistic missing data (~3% NaN rate, as seen in CPCB feeds)
    """
    print("\n" + "=" * 70)
    print("STEP 2: GENERATING 90-DAY HISTORICAL DATA")
    print("=" * 70)

    rng = np.random.default_rng(RANDOM_SEED)
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=HISTORY_DAYS)

    # Generate daily timestamps (one reading per day per station)
    dates = pd.date_range(start=start_date, end=end_date - timedelta(days=1), freq="D")
    n_days = len(dates)

    print(f"   Date range: {dates[0].strftime('%Y-%m-%d')} -> {dates[-1].strftime('%Y-%m-%d')}")
    print(f"   Days: {n_days}, Stations: {len(stations)}")

    all_rows = []

    for stn in stations:
        stn_name = stn["station_name"]
        bias = STATION_BIAS.get(stn_name, 1.0)

        for pollutant_name, profile in POLLUTANT_PROFILES.items():
            # Base signal: mean + seasonal component
            # Bengaluru monsoon (Jun-Sep) lowers PM; winter (Nov-Feb) raises PM
            day_of_year = np.array([d.timetuple().tm_yday for d in dates])
            seasonal = profile["seasonal_amplitude"] * np.cos(
                2 * np.pi * (day_of_year - 15) / 365  # Peak around Jan 15
            )

            # Autocorrelated daily noise (AR(1) process, rho=0.7)
            noise = np.zeros(n_days)
            noise[0] = rng.normal(0, profile["std"] * 0.5)
            for i in range(1, n_days):
                noise[i] = 0.7 * noise[i - 1] + rng.normal(0, profile["std"] * 0.35)

            # Combine: mean + seasonal + noise, then apply station bias
            values = (profile["mean"] + seasonal + noise) * bias

            # Add sensor-level noise (~5%)
            values += rng.normal(0, profile["mean"] * 0.05, n_days)

            # Clip to physical bounds
            values = np.clip(values, profile["min"], profile["max"])
            values = np.round(values, 1)

            # Introduce realistic missing data (~3%, matching CPCB patterns)
            missing_mask = rng.random(n_days) < 0.03
            values[missing_mask] = np.nan

            for i, dt in enumerate(dates):
                all_rows.append({
                    "station_name": stn_name,
                    "latitude": stn["latitude"],
                    "longitude": stn["longitude"],
                    "datetime": dt,
                    pollutant_name: values[i],
                })

    # Build DataFrame and merge PM2.5 + PM10 columns per (station, date)
    df_raw = pd.DataFrame(all_rows)

    # Pivot pollutant rows into columns
    df_pm25 = df_raw[df_raw["PM2.5"].notna() | df_raw["PM10"].isna()].dropna(subset=["PM2.5"], how="all") if "PM2.5" in df_raw.columns else pd.DataFrame()

    # Simpler approach: group by station+date and take first non-null
    merge_keys = ["station_name", "latitude", "longitude", "datetime"]
    df_merged = df_raw.groupby(merge_keys, as_index=False).first()

    print(f"   [OK] Generated {len(df_merged)} records")

    return df_merged


def generate_historical_data_v2(stations: list[dict]) -> pd.DataFrame:
    """
    Cleaner generation: one row per (station, date) with both PM2.5 and PM10.
    """
    print("\n" + "=" * 70)
    print("STEP 2: GENERATING 90-DAY HISTORICAL DATA")
    print("=" * 70)

    rng = np.random.default_rng(RANDOM_SEED)
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=HISTORY_DAYS)
    dates = pd.date_range(start=start_date, end=end_date - timedelta(days=1), freq="D")
    n_days = len(dates)

    print(f"   Date range: {dates[0].strftime('%Y-%m-%d')} -> {dates[-1].strftime('%Y-%m-%d')}")
    print(f"   Days: {n_days}, Stations: {len(stations)}")

    rows = []

    for stn in stations:
        stn_name = stn["station_name"]
        bias = STATION_BIAS.get(stn_name, 1.0)

        # Generate PM2.5 and PM10 series for this station
        pollutant_values = {}
        for pollutant_name, profile in POLLUTANT_PROFILES.items():
            # Seasonal component: monsoon (Jun-Sep) lowers PM, winter (Nov-Feb) raises PM
            day_of_year = np.array([d.timetuple().tm_yday for d in dates])
            seasonal = profile["seasonal_amplitude"] * np.cos(
                2 * np.pi * (day_of_year - 15) / 365
            )

            # Autocorrelated daily noise (AR(1), rho=0.7 -- weather persistence)
            noise = np.zeros(n_days)
            noise[0] = rng.normal(0, profile["std"] * 0.5)
            for i in range(1, n_days):
                noise[i] = 0.7 * noise[i - 1] + rng.normal(0, profile["std"] * 0.35)

            # Combine components
            values = (profile["mean"] + seasonal + noise) * bias

            # Sensor-level noise (~5%)
            values += rng.normal(0, profile["mean"] * 0.05, n_days)

            # Clip to physical bounds
            values = np.clip(values, profile["min"], profile["max"])
            values = np.round(values, 1)

            # Realistic missing data (~3%, as observed in CPCB feeds)
            missing_mask = rng.random(n_days) < 0.03
            values = values.astype(float)
            values[missing_mask] = np.nan

            pollutant_values[pollutant_name] = values

        # Build rows for this station
        for i, dt in enumerate(dates):
            rows.append({
                "station_name": stn_name,
                "latitude": stn["latitude"],
                "longitude": stn["longitude"],
                "datetime": dt,
                "PM2.5": pollutant_values["PM2.5"][i],
                "PM10": pollutant_values["PM10"][i],
            })

    df = pd.DataFrame(rows)
    print(f"   [OK] Generated {len(df)} records")

    return df


# ================================================================
# 4. DATA CLEANING
# ================================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the generated dataset:
      - Handle missing values (forward fill within each station)
      - Ensure datetime format
      - Remove duplicates
    """
    print("\n" + "=" * 70)
    print("STEP 3: CLEANING DATA")
    print("=" * 70)

    # Report missing values before cleaning
    pm25_missing = df["PM2.5"].isna().sum()
    pm10_missing = df["PM10"].isna().sum()
    print(f"   Missing values before cleaning:")
    print(f"      PM2.5: {pm25_missing}")
    print(f"      PM10 : {pm10_missing}")

    # Forward fill within each station (simulates sensor coming back online)
    df = df.sort_values(["station_name", "datetime"]).reset_index(drop=True)
    df["PM2.5"] = df.groupby("station_name")["PM2.5"].transform(
        lambda x: x.ffill().bfill()
    )
    df["PM10"] = df.groupby("station_name")["PM10"].transform(
        lambda x: x.ffill().bfill()
    )

    # Ensure datetime type
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates(subset=["station_name", "datetime"]).reset_index(drop=True)
    after = len(df)

    pm25_missing_after = df["PM2.5"].isna().sum()
    pm10_missing_after = df["PM10"].isna().sum()

    print(f"\n   Missing values after cleaning:")
    print(f"      PM2.5: {pm25_missing_after}")
    print(f"      PM10 : {pm10_missing_after}")
    print(f"\n   Duplicates removed: {before - after}")
    print(f"   [OK] Cleaned dataset: {len(df)} records")

    return df


# ================================================================
# 5. SAVE OUTPUT
# ================================================================

def save_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save cleaned dataset to CSV."""
    print("\n" + "=" * 70)
    print("STEP 4: SAVING DATASET")
    print("=" * 70)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    file_size_kb = output_path.stat().st_size / 1024

    print(f"   [OK] Saved to: {output_path}")
    print(f"   [SIZE] {file_size_kb:.1f} KB")


# ================================================================
# 6. SUMMARY
# ================================================================

def print_summary(df: pd.DataFrame) -> None:
    """Print final dataset summary."""
    print("\n" + "=" * 70)
    print("STEP 5: FINAL DATASET SUMMARY")
    print("=" * 70)

    # Stations
    stations = df["station_name"].unique()
    print(f"\n   [STATIONS] {len(stations)} monitoring stations:")
    for stn in sorted(stations):
        n_records = len(df[df["station_name"] == stn])
        print(f"      - {stn} ({n_records} records)")

    # Total records
    print(f"\n   [RECORDS]  Total records: {len(df)}")

    # Date range
    date_min = df["datetime"].min()
    date_max = df["datetime"].max()
    print(f"\n   [DATES]    Date range: {date_min.strftime('%Y-%m-%d')} -> {date_max.strftime('%Y-%m-%d')}")
    n_days = (date_max - date_min).days + 1
    print(f"              Span: {n_days} days")

    # First 10 rows
    print(f"\n   [PREVIEW]  First 10 rows:")
    print("-" * 70)
    print(df.head(10).to_string(index=False))

    # Summary statistics
    print(f"\n   [STATS]    Summary statistics:")
    print("-" * 70)
    print(df[["PM2.5", "PM10"]].describe().round(2).to_string())

    print("\n" + "=" * 70)
    print("[DONE] HISTORICAL DATA GENERATION COMPLETE")
    print("=" * 70)

    # Data provenance notice
    print("\n" + "-" * 70)
    print("DATA PROVENANCE NOTICE:")
    print("-" * 70)
    print("Station metadata : CPCB / data.gov.in (Government of India)")
    print("Pollution values : Synthetic, calibrated to CPCB Bengaluru")
    print("                   annual AQI reports (2022-2026)")
    print("Intended use     : ML prototyping (DBSCAN, Random Forest)")
    print("NOT suitable for : Regulatory compliance or health advisories")
    print("-" * 70)


# ================================================================
# 7. MAIN PIPELINE
# ================================================================

def main():
    """Execute the full historical data pipeline."""
    print("\n" + "=" * 70)
    print("   AirGuard AI -- Bengaluru Historical AQI Data Pipeline")
    print("=" * 70)

    # Step 1: Fetch real station metadata from CPCB API
    stations = fetch_cpcb_station_metadata()

    # Step 2: Generate 90-day historical data
    df = generate_historical_data_v2(stations)

    # Step 3: Clean data
    df = clean_data(df)

    # Step 4: Save
    save_data(df, OUTPUT_PATH)

    # Step 5: Summary
    print_summary(df)


if __name__ == "__main__":
    main()
