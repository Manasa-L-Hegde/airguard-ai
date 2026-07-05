"""
Build a merged Bengaluru AQI timeseries from raw historical and live CSV files.

The script normalizes mixed source formats into a single schema:
station, timestamp, PM2.5, PM10, NO2, SO2, CO, OZONE, NH3, latitude, longitude
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

import numpy as np
import pandas as pd


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_SOURCE_DIRS = [
    PROJECT_ROOT / "data" / "raw" / "Historical",
    PROJECT_ROOT / "data" / "raw" / "historical",
    PROJECT_ROOT / "data" / "raw" / "live",
]
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "bengaluru_air_quality_timeseries.csv"

TARGET_COLUMNS = [
    "station",
    "timestamp",
    "PM2.5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "OZONE",
    "NH3",
    "latitude",
    "longitude",
]

POLLUTANT_COLUMNS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "OZONE", "NH3"]
MONTH_LOOKUP = {month.lower(): index for index, month in enumerate(calendar.month_name) if month}
MONTH_LOOKUP.update({month.lower(): index for index, month in enumerate(calendar.month_abbr) if month})
NUMERIC_NULLS = {"", "NA", "N/A", "na", "null", "None", "none", "nan", "NaN"}


@dataclass(frozen=True)
class StationMetadata:
    station: str
    latitude: float
    longitude: float
    aliases: tuple[str, ...]


STATION_REGISTRY: tuple[StationMetadata, ...] = (
    StationMetadata("BTM Layout, Bengaluru - CPCB", 12.913522, 77.595080, ("btmlayout", "blrbtmlayoutcpcb", "btm-layout")),
    StationMetadata("Silk Board, Bengaluru - KSPCB", 12.917348, 77.622813, ("centralsilkboard", "silkboard", "blrsilkboard", "silk-board")),
    StationMetadata("City Railway Station, Bengaluru - KSPCB", 12.975684, 77.566075, ("cityrailwaystation", "blrcityrailwaystation", "city-railway-station")),
    StationMetadata("Hebbal, Bengaluru - KSPCB", 13.029152, 77.585901, ("hebbal", "blrhebbal")),
    StationMetadata("Jayanagar 5th Block, Bengaluru - KSPCB", 12.920984, 77.584908, ("jayanagar5thblock", "blrjayanagar5thblock", "jayanagar-5th-block")),
    StationMetadata("Hombegowda Nagar, Bengaluru - KSPCB", 12.938539, 77.590100, ("hombegowdanagar", "blrhombegowdanagar", "hombegowda-nagar")),
    StationMetadata("Bapuji Nagar, Bengaluru - KSPCB", 12.951913, 77.539784, ("bapujinagar", "blrbapujinagar", "bapuji-nagar")),
    StationMetadata("Kasturi Nagar, Bengaluru - KSPCB", 13.003872, 77.664217, ("kasturinagar", "blrkasturinagar", "kasturi-nagar")),
    StationMetadata("Jigani, Bengaluru - KSPCB", 12.781628, 77.629915, ("jigani", "blrjigani")),
    StationMetadata("Peenya, Bengaluru - KSPCB", 13.030000, 77.520000, ("peenya", "blrpeenya", "peenyacpcb")),
    StationMetadata("RVCE Mailasandra, Bengaluru - KSPCB", 12.9232191, 77.5006464, ("rvcemailasandra", "blrrvcemailasandra", "mailasandra", "rvce-mailasandra")),
    StationMetadata("Sanegurava Halli, Bengaluru - KSPCB", 12.9904292, 77.5422438, ("saneguruvahalli", "saneguravahalli", "saneguruvanahalli", "blrsaneguravahalli", "saneguruva-halli")),
    StationMetadata("Shivapura Peenya, Bengaluru - KSPCB", 13.0160480, 77.5045057, ("shivapurapeenya", "blrshivapurapeenya", "shivapura-peenya")),
    StationMetadata("Kadubeesanahalli, Bengaluru - CPCB", 12.9389650, 77.6964066, ("kadubeesanahalli", "bwssbkadubeesanahalli", "blrkadubeesanahalli")),
)

TABULAR_ALIASES = {
    "station": ("station", "station name", "station_name"),
    "timestamp": ("timestamp", "datetime", "last_update", "date", "date_time", "time"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng", "long"),
    "PM2.5": ("pm2.5", "pm2_5", "pm25", "pm 2.5", "pm2 5"),
    "PM10": ("pm10", "pm 10"),
    "NO2": ("no2",),
    "SO2": ("so2",),
    "CO": ("co",),
    "OZONE": ("ozone", "o3"),
    "NH3": ("nh3",),
}


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def unique_existing_dirs(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        key = path.resolve().as_posix().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


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
    station = cleaned if cleaned else file_path.stem

    return StationMetadata(station=station, latitude=np.nan, longitude=np.nan, aliases=(normalized_stem,))


def parse_month_name(value: str) -> int | None:
    return MONTH_LOOKUP.get(value.strip().lower())


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

    return pd.to_numeric(text.replace(",", ""), errors="coerce")


def find_matching_column(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    normalized_map = {normalize_key(column): column for column in columns}
    for alias in aliases:
        normalized_alias = normalize_key(alias)
        for normalized_column, original_column in normalized_map.items():
            if normalized_alias == normalized_column or normalized_alias in normalized_column:
                return original_column
    return None


def detect_file_format(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            row = [cell.strip().strip('"') for cell in raw_row]
            if not row or all(cell == "" for cell in row):
                continue

            first_value = row[0].strip()
            if first_value.lower() == "year":
                return "monthly_grid"

            if re.match(r"^[A-Za-z]+\s*[-/]\s*\d{4}$", first_value):
                return "monthly_grid"

            break

    return "tabular"


def parse_monthly_grid_file(file_path: Path, metadata: StationMetadata) -> pd.DataFrame:
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
                reading = coerce_numeric(values[hour_index])

                rows.append(
                    {
                        "station": metadata.station,
                        "timestamp": timestamp,
                        "PM2.5": reading,
                        "PM10": np.nan,
                        "NO2": np.nan,
                        "SO2": np.nan,
                        "CO": np.nan,
                        "OZONE": np.nan,
                        "NH3": np.nan,
                        "latitude": metadata.latitude,
                        "longitude": metadata.longitude,
                    }
                )

    return pd.DataFrame(rows, columns=TARGET_COLUMNS)


def parse_tabular_file(file_path: Path, metadata: StationMetadata) -> pd.DataFrame:
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    df = df.replace({null_value: np.nan for null_value in NUMERIC_NULLS})

    standardized = pd.DataFrame(index=df.index)

    for target_column, aliases in TABULAR_ALIASES.items():
        source_column = find_matching_column(list(df.columns), aliases)
        standardized[target_column] = df[source_column] if source_column is not None else np.nan

    if standardized["station"].isna().all():
        standardized["station"] = metadata.station
    else:
        standardized["station"] = standardized["station"].fillna(metadata.station).astype("string").str.strip()

    if standardized["timestamp"].notna().any():
        standardized["timestamp"] = pd.to_datetime(standardized["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
    else:
        standardized["timestamp"] = pd.NaT

    for pollutant in POLLUTANT_COLUMNS:
        standardized[pollutant] = pd.to_numeric(standardized[pollutant], errors="coerce")

    if standardized["latitude"].notna().any():
        standardized["latitude"] = pd.to_numeric(standardized["latitude"], errors="coerce")
    standardized["latitude"] = standardized["latitude"].fillna(metadata.latitude)

    if standardized["longitude"].notna().any():
        standardized["longitude"] = pd.to_numeric(standardized["longitude"], errors="coerce")
    standardized["longitude"] = standardized["longitude"].fillna(metadata.longitude)

    standardized = standardized.reindex(columns=TARGET_COLUMNS)
    return standardized


def load_single_file(file_path: Path) -> pd.DataFrame:
    metadata = infer_station_metadata(file_path)
    file_format = detect_file_format(file_path)

    if file_format == "monthly_grid":
        frame = parse_monthly_grid_file(file_path, metadata)
    else:
        frame = parse_tabular_file(file_path, metadata)

    if frame.empty:
        return frame.reindex(columns=TARGET_COLUMNS)

    frame["station"] = frame["station"].astype("string").str.strip()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)

    for pollutant in POLLUTANT_COLUMNS:
        frame[pollutant] = pd.to_numeric(frame[pollutant], errors="coerce")

    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    return frame.reindex(columns=TARGET_COLUMNS)


def collect_csv_files() -> list[Path]:
    source_dirs = unique_existing_dirs(RAW_SOURCE_DIRS)
    csv_files: list[Path] = []

    for source_dir in source_dirs:
        csv_files.extend(sorted(source_dir.rglob("*.csv")))

    unique_files: list[Path] = []
    seen: set[str] = set()
    for file_path in csv_files:
        key = file_path.resolve().as_posix().lower()
        if key in seen:
            continue
        seen.add(key)
        unique_files.append(file_path)

    return unique_files


def build_timeseries() -> pd.DataFrame:
    csv_files = collect_csv_files()
    if not csv_files:
        raise FileNotFoundError("No CSV files found in data/raw/Historical, data/raw/historical, or data/raw/live")

    frames: list[pd.DataFrame] = []
    for file_path in csv_files:
        print(f"[LOAD] {file_path.relative_to(PROJECT_ROOT)}")
        frame = load_single_file(file_path)
        print(f"       rows: {len(frame):,}")
        frames.append(frame)

    merged = pd.concat(frames, ignore_index=True)
    merged["station"] = merged["station"].astype("string").str.strip()
    merged["timestamp"] = pd.to_datetime(merged["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)

    for pollutant in POLLUTANT_COLUMNS:
        merged[pollutant] = pd.to_numeric(merged[pollutant], errors="coerce")

    merged["latitude"] = pd.to_numeric(merged["latitude"], errors="coerce")
    merged["longitude"] = pd.to_numeric(merged["longitude"], errors="coerce")

    merged = merged.dropna(subset=["station", "timestamp"]).sort_values(["station", "timestamp"], kind="mergesort").reset_index(drop=True)
    merged = merged.reindex(columns=TARGET_COLUMNS)
    return merged


def save_dataset(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 72)
    print("BENGALURU AIR QUALITY TIMESERIES SUMMARY")
    print("=" * 72)
    print(f"Total rows      : {len(df):,}")
    print(f"Unique stations  : {df['station'].nunique():,}")

    if df["timestamp"].notna().any():
        print(f"Date range       : {df['timestamp'].min()} -> {df['timestamp'].max()}")
    else:
        print("Date range       : unavailable")

    print(f"Output file      : {OUTPUT_PATH}")


def main() -> None:
    print("=" * 72)
    print("AirGuard AI - Bengaluru Air Quality Timeseries Builder")
    print("=" * 72)

    merged = build_timeseries()
    save_dataset(merged, OUTPUT_PATH)
    print_summary(merged)


if __name__ == "__main__":
    main()