"""
AirGuard AI - Bengaluru Historical AQI Ingestion Pipeline
=========================================================
Reads every CSV in data/raw/historical, normalizes station-specific formats,
and writes a single master dataset to data/processed/bengaluru_historical_master.csv.

The historical source files in this project are primarily month/day/hour grids
with station metadata embedded in the filename. This pipeline also supports
standard tabular AQI exports so the ingestion code remains reusable if the raw
folder changes later.
"""

from __future__ import annotations

import calendar
import csv
import io
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_HISTORICAL_DIR = PROJECT_ROOT / "data" / "raw" / "historical"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "bengaluru_historical_master.csv"

REQUIRED_COLUMNS = [
    "station_name",
    "datetime",
    "PM2.5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "OZONE",
    "NH3",
    "AQI",
    "latitude",
    "longitude",
]

POLLUTANT_COLUMNS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "OZONE", "NH3", "AQI"]

MONTH_LOOKUP = {month.lower(): index for index, month in enumerate(calendar.month_name) if month}
MONTH_LOOKUP.update({month.lower(): index for index, month in enumerate(calendar.month_abbr) if month})

NUMERIC_NULLS = {"", "NA", "N/A", "na", "null", "None", "none", "nan", "NaN"}


@dataclass(frozen=True)
class StationMetadata:
    station_name: str
    latitude: float
    longitude: float
    aliases: tuple[str, ...]


STATION_REGISTRY: tuple[StationMetadata, ...] = (
    StationMetadata(
        station_name="BTM Layout, Bengaluru - CPCB",
        latitude=12.913522,
        longitude=77.595080,
        aliases=("btmlayout", "blrbtmlayoutcpcb", "btm-layout"),
    ),
    StationMetadata(
        station_name="Silk Board, Bengaluru - KSPCB",
        latitude=12.917348,
        longitude=77.622813,
        aliases=("centralsilkboard", "silkboard", "blrsilkboard"),
    ),
    StationMetadata(
        station_name="City Railway Station, Bengaluru - KSPCB",
        latitude=12.975684,
        longitude=77.566075,
        aliases=("cityrailwaystation", "blrcityrailwaystation"),
    ),
    StationMetadata(
        station_name="Hebbal, Bengaluru - KSPCB",
        latitude=13.029152,
        longitude=77.585901,
        aliases=("hebbal", "blrhebbal"),
    ),
    StationMetadata(
        station_name="Jayanagar 5th Block, Bengaluru - KSPCB",
        latitude=12.920984,
        longitude=77.584908,
        aliases=("jayanagar5thblock", "blrjayanagar5thblock"),
    ),
    StationMetadata(
        station_name="Hombegowda Nagar, Bengaluru - KSPCB",
        latitude=12.938539,
        longitude=77.590100,
        aliases=("hombegowdanagar", "blrhombegowdanagar"),
    ),
    StationMetadata(
        station_name="Bapuji Nagar, Bengaluru - KSPCB",
        latitude=12.951913,
        longitude=77.539784,
        aliases=("bapujinagar", "blrbapujinagar"),
    ),
    StationMetadata(
        station_name="Kasturi Nagar, Bengaluru - KSPCB",
        latitude=13.003872,
        longitude=77.664217,
        aliases=("kasturinagar", "blrkasturinagar"),
    ),
    StationMetadata(
        station_name="Jigani, Bengaluru - KSPCB",
        latitude=12.781628,
        longitude=77.629915,
        aliases=("jigani", "blrjigani"),
    ),
    StationMetadata(
        station_name="Peenya, Bengaluru - KSPCB",
        latitude=13.030000,
        longitude=77.520000,
        aliases=("peenya", "blrpeenya", "peenyacpcb"),
    ),
    StationMetadata(
        station_name="RVCE Mailasandra, Bengaluru - KSPCB",
        latitude=12.9232191,
        longitude=77.5006464,
        aliases=("rvcemailasandra", "blrrvcemailasandra", "mailasandra"),
    ),
    StationMetadata(
        station_name="Sanegurava Halli, Bengaluru - KSPCB",
        latitude=12.9904292,
        longitude=77.5422438,
        aliases=("saneguruvahalli", "saneguravahalli", "saneguruvanahalli", "blrsaneguravahalli"),
    ),
    StationMetadata(
        station_name="Shivapura Peenya, Bengaluru - KSPCB",
        latitude=13.0160480,
        longitude=77.5045057,
        aliases=("shivapurapeenya", "blrshivapurapeenya"),
    ),
    StationMetadata(
        station_name="Kadubeesanahalli, Bengaluru - CPCB",
        latitude=12.9389650,
        longitude=77.6964066,
        aliases=("kadubeesanahalli", "bwssbkadubeesanahalli", "blrkadubeesanahalli"),
    ),
)

TABULAR_ALIASES = {
    "station_name": ("station_name", "station name", "station"),
    "datetime": ("datetime", "timestamp", "last_update", "date", "date_time"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng", "long"),
    "PM2.5": ("pm2.5", "pm2_5", "pm25", "pm 2.5", "pm2 5"),
    "PM10": ("pm10", "pm 10"),
    "NO2": ("no2",),
    "SO2": ("so2",),
    "CO": ("co",),
    "OZONE": ("ozone", "o3"),
    "NH3": ("nh3",),
    "AQI": ("aqi", "air quality index", "airqualityindex"),
}


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def first_existing_alias(text: str, aliases: Iterable[str]) -> bool:
    for alias in aliases:
        if alias in text:
            return True
    return False


def infer_station_metadata(file_path: Path) -> StationMetadata:
    normalized_stem = normalize_key(file_path.stem)

    best_match: StationMetadata | None = None
    best_alias_length = -1

    for metadata in STATION_REGISTRY:
        for alias in metadata.aliases:
            normalized_alias = normalize_key(alias)
            if normalized_alias and normalized_alias in normalized_stem and len(normalized_alias) > best_alias_length:
                best_match = metadata
                best_alias_length = len(normalized_alias)

    if best_match is not None:
        return best_match

    cleaned = re.sub(r"\b(2017|2018|2019|2020|2021|2022|2023|2024|2025|2026)\b", "", file_path.stem)
    cleaned = re.sub(r"(?i)hourly aqi data", "", cleaned)
    cleaned = re.sub(r"(?i)cpcb|kspcb|bengaluru|bangalore|blr", "", cleaned)
    cleaned = re.sub(r"[-_]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    station_name = cleaned if cleaned else file_path.stem

    return StationMetadata(station_name=station_name, latitude=np.nan, longitude=np.nan, aliases=(normalized_stem,))


def parse_month_name(value: str) -> int | None:
    value = value.strip().lower()
    return MONTH_LOOKUP.get(value)


def parse_hour_label(value: str, fallback_hour: int) -> int:
    match = re.match(r"^(\d{1,2})", value.strip())
    if match:
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return hour
    return fallback_hour


def coerce_numeric(value: object) -> float:
    if value is None:
        return np.nan
    if isinstance(value, float) and np.isnan(value):
        return np.nan

    text = str(value).strip().strip('"').strip("'")
    if text in NUMERIC_NULLS:
        return np.nan

    text = text.replace(",", "")
    return pd.to_numeric(text, errors="coerce")


def standardize_output_frame(df: pd.DataFrame, station_name: str, latitude: float, longitude: float) -> pd.DataFrame:
    df = df.copy()

    if "station_name" not in df.columns:
        df["station_name"] = station_name
    else:
        df["station_name"] = df["station_name"].fillna(station_name).replace("", station_name)

    if "datetime" not in df.columns:
        df["datetime"] = pd.NaT

    for pollutant in POLLUTANT_COLUMNS:
        if pollutant not in df.columns:
            df[pollutant] = np.nan

    if "latitude" not in df.columns:
        df["latitude"] = latitude
    else:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(latitude)

    if "longitude" not in df.columns:
        df["longitude"] = longitude
    else:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(longitude)

    df["station_name"] = df["station_name"].astype("string").str.strip()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    for pollutant in POLLUTANT_COLUMNS:
        df[pollutant] = pd.to_numeric(df[pollutant], errors="coerce")

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df.reindex(columns=REQUIRED_COLUMNS)
    return df


def parse_monthly_hourly_file(file_path: Path, metadata: StationMetadata) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    current_year: int | None = None
    current_month: int | None = None
    hour_labels: list[str] = []

    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            row = [cell.strip().strip('"') for cell in raw_row]
            if not row or all(cell == "" for cell in row):
                continue

            first_value = row[0].strip()
            if first_value.lower() == "year" and len(row) > 1:
                match = re.search(r"(\d{4})", row[1])
                if match:
                    current_year = int(match.group(1))
                continue

            month_match = re.match(r"^([A-Za-z]+)\s*[-/]\s*(\d{4})$", first_value)
            if month_match:
                current_month = parse_month_name(month_match.group(1))
                current_year = int(month_match.group(2))
                hour_labels = row[1:]
                continue

            if current_year is None or current_month is None:
                continue

            if not re.fullmatch(r"\d{1,2}", first_value):
                continue

            day = int(first_value)
            try:
                base_date = datetime(current_year, current_month, day)
            except ValueError:
                continue

            values = row[1:25]
            if len(values) < 24:
                values.extend([np.nan] * (24 - len(values)))

            for hour_index in range(24):
                hour_value = parse_hour_label(hour_labels[hour_index], hour_index) if hour_index < len(hour_labels) else hour_index
                timestamp = base_date + timedelta(hours=hour_value)
                aqi_value = coerce_numeric(values[hour_index])

                rows.append(
                    {
                        "station_name": metadata.station_name,
                        "datetime": timestamp,
                        "PM2.5": np.nan,
                        "PM10": np.nan,
                        "NO2": np.nan,
                        "SO2": np.nan,
                        "CO": np.nan,
                        "OZONE": np.nan,
                        "NH3": np.nan,
                        "AQI": aqi_value,
                        "latitude": metadata.latitude,
                        "longitude": metadata.longitude,
                    }
                )

    return standardize_output_frame(pd.DataFrame(rows), metadata.station_name, metadata.latitude, metadata.longitude)


def find_matching_column(columns: Iterable[str], aliases: tuple[str, ...]) -> str | None:
    normalized_map = {normalize_key(column): column for column in columns}
    for alias in aliases:
        normalized_alias = normalize_key(alias)
        for normalized_column, original_column in normalized_map.items():
            if normalized_alias == normalized_column or normalized_alias in normalized_column:
                return original_column
    return None


def parse_tabular_file(file_path: Path, metadata: StationMetadata) -> pd.DataFrame:
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    df = df.replace({null_value: np.nan for null_value in NUMERIC_NULLS})

    standardized = pd.DataFrame(index=df.index)

    for target_column, aliases in TABULAR_ALIASES.items():
        source_column = find_matching_column(df.columns, aliases)
        if source_column is None:
            standardized[target_column] = np.nan
        else:
            standardized[target_column] = df[source_column]

    if standardized["station_name"].isna().all():
        standardized["station_name"] = metadata.station_name
    else:
        standardized["station_name"] = standardized["station_name"].fillna(metadata.station_name)

    if standardized["datetime"].notna().any():
        standardized["datetime"] = pd.to_datetime(standardized["datetime"], errors="coerce")
    else:
        standardized["datetime"] = pd.NaT

    for pollutant in POLLUTANT_COLUMNS:
        if pollutant in standardized.columns:
            standardized[pollutant] = pd.to_numeric(standardized[pollutant], errors="coerce")
        else:
            standardized[pollutant] = np.nan

    if standardized["latitude"].notna().any():
        standardized["latitude"] = pd.to_numeric(standardized["latitude"], errors="coerce")
    standardized["latitude"] = standardized["latitude"].fillna(metadata.latitude)

    if standardized["longitude"].notna().any():
        standardized["longitude"] = pd.to_numeric(standardized["longitude"], errors="coerce")
    standardized["longitude"] = standardized["longitude"].fillna(metadata.longitude)

    standardized = standardize_output_frame(
        standardized,
        station_name=metadata.station_name,
        latitude=metadata.latitude,
        longitude=metadata.longitude,
    )

    return standardized


def detect_file_format(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            row = [cell.strip().strip('"') for cell in raw_row]
            if not row or all(cell == "" for cell in row):
                continue

            first_value = row[0].strip().lower()
            if first_value == "year":
                return "monthly_hourly"

            if re.match(r"^[A-Za-z]+\s*[-/]\s*\d{4}$", row[0].strip()):
                return "monthly_hourly"

            break

    return "tabular"


def load_single_file(file_path: Path) -> pd.DataFrame:
    metadata = infer_station_metadata(file_path)
    file_format = detect_file_format(file_path)

    if file_format == "monthly_hourly":
        frame = parse_monthly_hourly_file(file_path, metadata)
    else:
        frame = parse_tabular_file(file_path, metadata)

    return frame


def build_master_dataset(raw_dir: Path) -> pd.DataFrame:
    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir}")

    frames: list[pd.DataFrame] = []
    for file_path in csv_files:
        print(f"[LOAD] {file_path.name}")
        frame = load_single_file(file_path)
        print(f"       rows: {len(frame):,}")
        frames.append(frame)

    master = pd.concat(frames, ignore_index=True)

    master = master.replace({null_value: np.nan for null_value in NUMERIC_NULLS})
    master["station_name"] = master["station_name"].astype("string").str.strip()
    master["datetime"] = pd.to_datetime(master["datetime"], errors="coerce")

    for pollutant in POLLUTANT_COLUMNS:
        master[pollutant] = pd.to_numeric(master[pollutant], errors="coerce")

    master["latitude"] = pd.to_numeric(master["latitude"], errors="coerce")
    master["longitude"] = pd.to_numeric(master["longitude"], errors="coerce")

    master = master.dropna(subset=["station_name", "datetime"], how="any")
    master = master.drop_duplicates().sort_values(["station_name", "datetime"]).reset_index(drop=True)
    master = master.reindex(columns=REQUIRED_COLUMNS)

    return master


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 72)
    print("BENGALURU HISTORICAL MASTER SUMMARY")
    print("=" * 72)

    print(f"Stations          : {df['station_name'].nunique():,}")
    print(f"Total records     : {len(df):,}")
    print("\nMissing values")
    print(df.isna().sum().to_string())

    if df["datetime"].notna().any():
        date_min = df["datetime"].min()
        date_max = df["datetime"].max()
        print(f"\nDate range        : {date_min} -> {date_max}")
    else:
        print("\nDate range        : unavailable")

    print("\nData types")
    print(df.dtypes.to_string())


def save_dataset(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSaved dataset to  : {output_path}")


def main() -> None:
    print("=" * 72)
    print("AirGuard AI - Bengaluru Historical Ingestion Pipeline")
    print("=" * 72)
    print(f"Input folder      : {RAW_HISTORICAL_DIR}")
    print(f"Output file       : {OUTPUT_PATH}")

    master = build_master_dataset(RAW_HISTORICAL_DIR)
    print_summary(master)
    save_dataset(master, OUTPUT_PATH)


if __name__ == "__main__":
    main()