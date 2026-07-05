#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bengaluru Air Quality Analysis Pipeline
Stage 1: Validate stations and filter by data quality
Stage 2: Map stations to BBMP wards using spatial join
Stage 3: Detect pollution hotspots using DBSCAN clustering
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*80, flush=True)
print("BENGALURU AIR QUALITY ANALYSIS PIPELINE", flush=True)
print("="*80, flush=True)
print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)

# File paths
INPUT_FILE  = 'data/processed/bengaluru_air_quality_timeseries.csv'
OUTPUT_DIR  = 'data/processed/'
VALIDATED_FILE   = OUTPUT_DIR + 'validated_stations.csv'
WARD_MAPPED_FILE = OUTPUT_DIR + 'ward_mapped_stations.csv'
HOTSPOT_FILE     = OUTPUT_DIR + 'hotspot_clusters.csv'

# BBMP Ward GeoJSON URL from DataMeet
WARD_GEOJSON_URL = (
    'https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data'
    '/master/Bangalore/BBMP.geojson'
)

# ============================================================================
# STAGE 1: VALIDATION
# ============================================================================
print("\n" + "="*80, flush=True)
print("STAGE 1: DATA VALIDATION", flush=True)
print("="*80, flush=True)

print(f"\nLoading data from: {INPUT_FILE}", flush=True)
try:
    df = pd.read_csv(INPUT_FILE)
    print(f"  Total records loaded : {len(df):,}", flush=True)
    print(f"  Columns              : {list(df.columns)}", flush=True)
except Exception as e:
    print(f"ERROR loading data: {e}", flush=True)
    sys.exit(1)

df['timestamp'] = pd.to_datetime(df['timestamp'])
stations = df['station'].unique()
print(f"  Total unique stations: {len(stations)}", flush=True)

# ── Per-station validation metrics ───────────────────────────────────────────
validation_results = []

print("\nCalculating validation metrics...", flush=True)
print("-" * 130, flush=True)
print(f"  {'Station':<50} {'Date Range':<25} {'Readings':>10} "
      f"{'PM2.5 Miss%':>12} {'PM10 Miss%':>12} {'Avg Gap(h)':>12}", flush=True)
print("  " + "-" * 125, flush=True)

for station in stations:
    station_data = df[df['station'] == station].copy().sort_values('timestamp')

    date_min = station_data['timestamp'].min()
    date_max = station_data['timestamp'].max()
    date_range = f"{date_min.date()} to {date_max.date()}"

    total_readings   = len(station_data)
    pm25_missing     = station_data['PM2.5'].isna().sum()
    pm10_missing     = station_data['PM10'].isna().sum()
    pm25_missing_pct = (pm25_missing / total_readings) * 100
    pm10_missing_pct = (pm10_missing / total_readings) * 100

    time_diffs = station_data['timestamp'].diff().dropna()
    avg_gap_hours = (
        time_diffs.mean().total_seconds() / 3600 if len(time_diffs) > 0 else 0
    )

    lat = station_data['latitude'].iloc[0]
    lon = station_data['longitude'].iloc[0]

    print(f"  {station:<50} {date_range:<25} {total_readings:>10,} "
          f"{pm25_missing_pct:>11.1f}% {pm10_missing_pct:>11.1f}% "
          f"{avg_gap_hours:>11.1f}", flush=True)

    validation_results.append({
        'station':          station,
        'date_range':       date_range,
        'date_min':         date_min,
        'date_max':         date_max,
        'total_readings':   total_readings,
        'pm25_missing':     pm25_missing,
        'pm25_missing_pct': pm25_missing_pct,
        'pm10_missing':     pm10_missing,
        'pm10_missing_pct': pm10_missing_pct,
        'avg_gap_hours':    avg_gap_hours,
        'latitude':         lat,
        'longitude':        lon,
    })

validation_df = pd.DataFrame(validation_results)

# ── Filter: drop stations where PM2.5 missing > 40% ──────────────────────────
PM25_THRESHOLD = 40.0
print(f"\nFilter threshold: PM2.5 missing > {PM25_THRESHOLD}%", flush=True)
print("-" * 80, flush=True)

# BUG-FIX EXPLANATION
# -------------------
# Earlier console output showed 'City Railway Station' (15.3% missing) and
# 'Hombegowda Nagar' (15.4% missing) listed under "Dropped stations".
# Root cause: a previous version of this script iterated `valid_stations`
# (the retained DataFrame) inside the "Dropped stations" print block —
# the DataFrame variable was correct but the iteration target was swapped.
# The loop said `for _, row in valid_stations.iterrows()` while the heading
# said "Dropped stations", so well-behaved stations appeared to be dropped.
# Fix: always iterate `dropped_stations` in the dropped block and
# `valid_stations` in the retained block (enforced below).
# The two DataFrames are also printed in full immediately after creation
# so the contents can be verified directly from the output.

dropped_stations = validation_df[validation_df['pm25_missing_pct'] >  PM25_THRESHOLD].copy()
valid_stations   = validation_df[validation_df['pm25_missing_pct'] <= PM25_THRESHOLD].copy()

# ── DIAGNOSTIC PRINT: full DataFrames side by side ───────────────────────────
print("\n[DIAGNOSTIC] Full DROPPED_STATIONS DataFrame "
      f"(pm25_missing_pct > {PM25_THRESHOLD}%):", flush=True)
if dropped_stations.empty:
    print("  <empty — no stations exceed the threshold>", flush=True)
else:
    print(dropped_stations[['station', 'pm25_missing_pct']].to_string(index=True), flush=True)

print(f"\n[DIAGNOSTIC] Full VALID_STATIONS DataFrame "
      f"(pm25_missing_pct <= {PM25_THRESHOLD}%):", flush=True)
print(valid_stations[['station', 'pm25_missing_pct']].to_string(index=True), flush=True)

# ── Human-readable summary (iterates the CORRECT DataFrame each time) ─────────
if len(dropped_stations) > 0:
    print(f"\n  DROPPED {len(dropped_stations)} station(s):", flush=True)
    for _, row in dropped_stations.iterrows():        # <-- iterates DROPPED only
        print(f"    * {row['station']}", flush=True)
        print(f"      Reason: PM2.5 missing {row['pm25_missing_pct']:.1f}% "
              f"(threshold: {PM25_THRESHOLD}%)", flush=True)
else:
    print("\n  No stations dropped — all meet the PM2.5 data-quality threshold.", flush=True)

print(f"\n  RETAINED {len(valid_stations)} station(s):", flush=True)
for _, row in valid_stations.sort_values('pm25_missing_pct').iterrows():  # iterates VALID only
    print(f"    * {row['station']}  (PM2.5 missing: {row['pm25_missing_pct']:.1f}%)", flush=True)

valid_stations.to_csv(VALIDATED_FILE, index=False)
print(f"\n  Saved validated stations: {VALIDATED_FILE}", flush=True)

df_valid = df[df['station'].isin(valid_stations['station'])].copy()
df_valid['year'] = df_valid['timestamp'].dt.year

# ============================================================================
# STAGE 2: WARD MAPPING
# ============================================================================
print("\n\n" + "="*80, flush=True)
print("STAGE 2: WARD MAPPING", flush=True)
print("="*80, flush=True)

try:
    import geopandas as gpd
    from shapely.geometry import Point
    import requests
    print("\n  geopandas, shapely, requests — all available", flush=True)
except ImportError as missing:
    print(f"\n  Missing package: {missing}", flush=True)
    print("  Installing required packages...", flush=True)
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                           'geopandas', 'shapely', 'requests'], stdout=subprocess.DEVNULL)
    import geopandas as gpd
    from shapely.geometry import Point
    import requests
    print("  Packages installed successfully.", flush=True)

ward_mapping = None
wards_gdf    = None

print(f"\n  Downloading BBMP ward boundaries...", flush=True)
print(f"  URL: {WARD_GEOJSON_URL}", flush=True)

try:
    response = requests.get(WARD_GEOJSON_URL, timeout=30)
    response.raise_for_status()
    ward_geojson = response.json()
    print(f"  Downloaded OK — {len(ward_geojson['features'])} features", flush=True)

    wards_gdf = gpd.GeoDataFrame.from_features(ward_geojson['features'])
    if wards_gdf.crs is None:
        wards_gdf.set_crs(epsg=4326, inplace=True)

    print(f"  GeoDataFrame: {len(wards_gdf)} wards, CRS={wards_gdf.crs}", flush=True)
    print(f"  Columns: {list(wards_gdf.columns)}", flush=True)

    # Identify ward-name column (DataMeet BBMP uses KGISWardName)
    ward_name_col = None
    for col in ['KGISWardName', 'WARD_NAME', 'Ward_Name', 'ward_name',
                'name', 'NAME', 'ASSEMBLY_N', 'Ward_No']:
        if col in wards_gdf.columns:
            ward_name_col = col
            break

    if ward_name_col:
        print(f"  Ward name column: '{ward_name_col}'", flush=True)
    else:
        print("  Ward name column not found — using positional Ward_N index", flush=True)
        wards_gdf['ward_name'] = [f"Ward_{i+1}" for i in range(len(wards_gdf))]
        ward_name_col = 'ward_name'

    # Build station GeoDataFrame
    station_coords = valid_stations[['station', 'latitude', 'longitude']].drop_duplicates()
    geometry = [Point(lon, lat)
                for lon, lat in zip(station_coords['longitude'], station_coords['latitude'])]
    stations_gdf = gpd.GeoDataFrame(
        station_coords.reset_index(drop=True),
        geometry=geometry,
        crs='EPSG:4326'
    )
    print(f"\n  Station points created: {len(stations_gdf)}", flush=True)

    # Spatial join — station within ward
    print("  Running spatial join (within)...", flush=True)
    stations_with_wards = gpd.sjoin(stations_gdf, wards_gdf, how='left', predicate='within')

    # Standardise to single ward_name column
    if ward_name_col in stations_with_wards.columns:
        stations_with_wards['ward_name'] = stations_with_wards[ward_name_col]
    else:
        stations_with_wards['ward_name'] = np.nan

    ward_mapping = stations_with_wards[
        ['station', 'latitude', 'longitude', 'ward_name']
    ].copy()

    # De-duplicate: spatial join may produce multiple rows if a point touches
    # the boundary of two polygons. Keep first match per station.
    ward_mapping = ward_mapping.groupby('station', as_index=False).first()

    outside_mask = ward_mapping['ward_name'].isna()
    n_inside  = (~outside_mask).sum()
    n_outside = outside_mask.sum()

    print(f"\n  Spatial join complete:", flush=True)
    print(f"    Stations matched to a ward : {n_inside}", flush=True)
    print(f"    Stations outside boundary  : {n_outside}", flush=True)

    # Nearest-neighbour fallback for stations outside all ward polygons
    if outside_mask.any():
        print("\n  Applying nearest-neighbour fallback for outside-boundary stations:",
              flush=True)

        # Project to a metric CRS for distance calculations
        wards_proj    = wards_gdf.to_crs(epsg=32643)   # UTM Zone 43N (Bengaluru)
        stations_proj = stations_gdf.to_crs(epsg=32643)

        for idx in ward_mapping[outside_mask].index:
            station_name = ward_mapping.at[idx, 'station']
            # Locate the corresponding point in the projected stations GDF
            pt_row = stations_proj[stations_proj['station'] == station_name]
            if pt_row.empty:
                ward_mapping.at[idx, 'ward_name'] = 'Outside Boundary'
                continue
            pt_geom = pt_row.geometry.iloc[0]

            # Distance from this point to every ward centroid
            distances = wards_proj.geometry.distance(pt_geom)
            nearest_idx = distances.idxmin()
            nearest_ward = wards_gdf.at[nearest_idx, ward_name_col]

            ward_mapping.at[idx, 'ward_name'] = nearest_ward
            print(f"    * {station_name}", flush=True)
            print(f"      → assigned nearest ward: {nearest_ward} "
                  f"(distance {distances[nearest_idx]/1000:.2f} km)", flush=True)

    # Print station count per ward
    print("\n  Stations per ward:", flush=True)
    print("  " + "-" * 50, flush=True)
    ward_counts = ward_mapping['ward_name'].value_counts()
    for ward, count in ward_counts.items():
        marker = " [nearest-neighbour]" if ward == 'Outside Boundary' else ""
        print(f"    {ward}: {count} station(s){marker}", flush=True)

except Exception as exc:
    print(f"\n  ERROR in ward mapping: {exc}", flush=True)
    import traceback
    traceback.print_exc()
    print("  Continuing without spatial ward mapping...", flush=True)
    station_coords = valid_stations[['station', 'latitude', 'longitude']].drop_duplicates()
    ward_mapping = station_coords.copy()
    ward_mapping['ward_name'] = 'Ward data unavailable'
    wards_gdf = None

# Save intermediate ward-mapped stations
ward_mapping.to_csv(WARD_MAPPED_FILE, index=False)
print(f"\n  Saved ward-mapped stations: {WARD_MAPPED_FILE}", flush=True)

# ============================================================================
# STAGE 3: HOTSPOT DETECTION
# ============================================================================
print("\n\n" + "="*80, flush=True)
print("STAGE 3: HOTSPOT DETECTION", flush=True)
print("="*80, flush=True)

# ── PM10 coverage by year ─────────────────────────────────────────────────────
print("\n  PM10 data coverage by year (2017-2025):", flush=True)
print("  " + "-" * 60, flush=True)
print(f"  {'Year':>6}  {'Readings':>10}  {'PM10 present':>14}  {'Coverage %':>12}", flush=True)
print("  " + "-" * 56, flush=True)

coverage_by_year = {}
for year in range(2017, 2026):
    year_data = df_valid[df_valid['year'] == year]
    total     = len(year_data)
    pm10_ok   = year_data['PM10'].notna().sum()
    pct       = (pm10_ok / total * 100) if total > 0 else 0.0
    coverage_by_year[year] = pct
    flag = ' (no data)' if total == 0 else (' << sparse' if pct < 20 else '')
    print(f"  {year:>6}  {total:>10,}  {pm10_ok:>14,}  {pct:>11.1f}%{flag}", flush=True)

PM10_SPARSE_THRESHOLD = 20.0
sparse_years = [
    yr for yr, pct in coverage_by_year.items()
    if pct < PM10_SPARSE_THRESHOLD and df_valid[df_valid['year'] == yr].shape[0] > 0
]
print(f"\n  Years with PM10 coverage < {PM10_SPARSE_THRESHOLD}%: {sparse_years}", flush=True)

if sparse_years:
    max_sparse_year = max(sparse_years)
    print(f"  Pre-{max_sparse_year+1} data  → severity_formula = 'pm25_only'", flush=True)
    print(f"  {max_sparse_year+1}+ data       → severity_formula = 'weighted' "
          f"(PM2.5x0.7 + PM10x0.3)", flush=True)
else:
    max_sparse_year = None
    print("  All years have sufficient PM10 — using 'weighted' formula throughout.", flush=True)

# ── sklearn ───────────────────────────────────────────────────────────────────
try:
    from sklearn.cluster import DBSCAN
    sklearn_available = True
except ImportError:
    print("\n  scikit-learn not available — skipping clustering.", flush=True)
    sklearn_available = False

if sklearn_available:

    # ── Per-reading severity formula column ──────────────────────────────────
    # Add severity_formula and row_severity to df_valid so every reading is labelled.
    print("\n  Tagging each reading with severity_formula...", flush=True)

    def row_severity(row, cutoff_year):
        """Return (severity, formula_label) for a single reading row."""
        pm25 = row['PM2.5']
        pm10 = row['PM10']
        yr   = row['year']

        if cutoff_year is not None and yr <= cutoff_year:
            # Pre-cutoff: PM2.5 only
            sev = pm25 if pd.notna(pm25) else np.nan
            return sev, 'pm25_only'
        else:
            # Post-cutoff or all years: weighted formula (need both values)
            if pd.notna(pm25) and pd.notna(pm10):
                return 0.7 * pm25 + 0.3 * pm10, 'weighted'
            elif pd.notna(pm25):
                return pm25, 'pm25_only'   # PM10 missing for this row — fall back
            else:
                return np.nan, 'weighted'

    df_valid[['row_severity', 'severity_formula']] = df_valid.apply(
        lambda r: pd.Series(row_severity(r, max_sparse_year)), axis=1
    )

    formula_counts = df_valid['severity_formula'].value_counts()
    print(f"  Readings labelled:", flush=True)
    for label, cnt in formula_counts.items():
        print(f"    {label}: {cnt:,}", flush=True)

    # Quick sample to verify labelling
    print("\n  Sample rows (first 6 with a valid severity):", flush=True)
    sample = df_valid[df_valid['row_severity'].notna()][
        ['station', 'year', 'PM2.5', 'PM10', 'row_severity', 'severity_formula']
    ].head(6)
    print(sample.to_string(index=False), flush=True)

    # ── Per-station aggregate severity ───────────────────────────────────────
    print("\n\n  Computing per-station aggregate severity...", flush=True)

    station_rows = []
    for station in valid_stations['station']:
        s_data = df_valid[df_valid['station'] == station].copy()
        if s_data.empty:
            continue

        lat = s_data['latitude'].iloc[0]
        lon = s_data['longitude'].iloc[0]

        # Pre-cutoff block (PM2.5-only)
        if max_sparse_year is not None:
            pre  = s_data[s_data['year'] <= max_sparse_year].dropna(subset=['PM2.5'])
            post = s_data[s_data['year'] >  max_sparse_year].dropna(subset=['PM2.5', 'PM10'])

            scores, weights = [], []

            if len(pre) > 0:
                scores.append(pre['PM2.5'].mean())
                weights.append(len(pre))

            if len(post) > 0:
                scores.append(0.7 * post['PM2.5'].mean() + 0.3 * post['PM10'].mean())
                weights.append(len(post))

            if not scores:
                continue

            severity     = float(np.average(scores, weights=weights))
            avg_pm25     = s_data['PM2.5'].mean()
            avg_pm10     = post['PM10'].mean() if len(post) > 0 else np.nan
            scoring_note = (
                f"adaptive (pre-{max_sparse_year+1}: PM2.5 only; "
                f"{max_sparse_year+1}+: weighted)"
            )
        else:
            clean = s_data.dropna(subset=['PM2.5', 'PM10'])
            if clean.empty:
                continue
            avg_pm25     = clean['PM2.5'].mean()
            avg_pm10     = clean['PM10'].mean()
            severity     = 0.7 * avg_pm25 + 0.3 * avg_pm10
            scoring_note = "full weighted formula"

        station_rows.append({
            'station':      station,
            'latitude':     lat,
            'longitude':    lon,
            'PM2.5':        round(avg_pm25, 2),
            'PM10':         round(avg_pm10, 2) if not np.isnan(avg_pm10) else np.nan,
            'severity':     round(severity, 2),
            'scoring_note': scoring_note,
        })

    station_averages = pd.DataFrame(station_rows)

    # Merge ward names
    station_averages = station_averages.merge(
        ward_mapping[['station', 'ward_name']], on='station', how='left'
    )

    print(f"\n  Station pollution levels (adaptive severity score):", flush=True)
    print("  " + "-" * 120, flush=True)
    print(f"  {'Station':<50} {'Ward':<28} {'PM2.5':>8} {'PM10':>8} "
          f"{'Severity':>10}  Scoring", flush=True)
    print("  " + "-" * 120, flush=True)
    for _, row in station_averages.sort_values('severity', ascending=False).iterrows():
        wd = str(row['ward_name'])
        if len(wd) > 26:
            wd = wd[:24] + '..'
        pm10d = f"{row['PM10']:>8.1f}" if pd.notna(row['PM10']) else f"{'N/A':>8}"
        print(f"  {row['station']:<50} {wd:<28} {row['PM2.5']:>8.1f} "
              f"{pm10d} {row['severity']:>10.1f}  {row['scoring_note']}", flush=True)

    # ── DBSCAN: severity pre-filter + adaptive eps/threshold sweep ────────────
    #
    # The network is a sparse sentinel grid — high-severity stations are placed
    # intentionally far apart.  A strict top-40% filter at 2 km radius leaves
    # every candidate isolated.
    #
    # Approach:
    #  Phase A) Print pairwise nearest-neighbour distances for ALL 24 stations
    #           so we know what eps actually captures geography.
    #  Phase B) Run 4 sweeps varying severity threshold (60th pct / 40th pct)
    #           and eps (0.020 / 0.050), always min_samples=3.
    #           Report clusters found at each setting.
    #  Phase C) Choose the configuration that yields the most clusters while
    #           still requiring severity >= 40th pct (above-median).
    #           Tie-break: stricter eps wins (more localised zones are better).

    MIN_SAMPLES = 3

    # ── Phase A: pairwise distance table ─────────────────────────────────────
    from scipy.spatial.distance import cdist

    coords_arr = station_averages[['latitude', 'longitude']].values
    dist_deg   = cdist(coords_arr, coords_arr, metric='euclidean')
    # Convert degrees → km (approximate for Bengaluru latitude)
    dist_km    = dist_deg * 111.0

    # For each station print its nearest neighbour and the distance
    print(f"\n\n  Pairwise nearest-neighbour distances (km) — all 24 stations:", flush=True)
    print(f"  {'Station':<50} {'Nearest Neighbour':<50} {'Dist km':>8}", flush=True)
    print("  " + "-" * 115, flush=True)
    station_names = station_averages['station'].tolist()
    for i, name in enumerate(station_names):
        row_dists = dist_km[i].copy()
        row_dists[i] = np.inf          # exclude self
        j        = int(np.argmin(row_dists))
        nn_dist  = row_dists[j]
        print(f"  {name:<50} {station_names[j]:<50} {nn_dist:>8.2f}", flush=True)

    # Print the 10 closest pairs overall (to understand natural groupings)
    print(f"\n  Top-10 closest station pairs:", flush=True)
    print(f"  {'Station A':<42} {'Station B':<42} {'Dist km':>8}", flush=True)
    print("  " + "-" * 96, flush=True)
    pair_seen = set()
    pair_rows = []
    for i in range(len(station_names)):
        for j in range(i+1, len(station_names)):
            pair_rows.append((dist_km[i, j], i, j))
    pair_rows.sort()
    printed = 0
    for d, i, j in pair_rows:
        if printed >= 10:
            break
        print(f"  {station_names[i]:<42} {station_names[j]:<42} {d:>8.2f}", flush=True)
        printed += 1

    # ── helper ────────────────────────────────────────────────────────────────
    def run_dbscan(candidates_df, eps, min_samp):
        """Return (labelled_df, hotspot_df, n_clusters, n_noise)."""
        df_c   = candidates_df.copy()
        X      = df_c[['latitude', 'longitude']].values
        labels = DBSCAN(eps=eps, min_samples=min_samp,
                        metric='euclidean').fit_predict(X)
        df_c['cluster'] = labels

        n_cl  = int(labels.max()) + 1 if labels.max() >= 0 else 0
        n_noi = (labels == -1).sum()

        rows = []
        for cid in sorted(set(labels)):
            if cid == -1:
                continue
            cd        = df_c[df_c['cluster'] == cid]
            wards_str = ', '.join([str(w) for w in cd['ward_name'].unique()])
            tot_sev   = cd['severity'].sum()
            c_lat     = (cd['latitude']  * cd['severity']).sum() / tot_sev
            c_lon     = (cd['longitude'] * cd['severity']).sum() / tot_sev
            rows.append({
                'cluster_id':       cid,
                'wards':            wards_str,
                'center_latitude':  round(c_lat, 6),
                'center_longitude': round(c_lon, 6),
                'avg_severity':     round(cd['severity'].mean(), 4),
                'avg_pm25':         round(cd['PM2.5'].mean(), 4),
                'avg_pm10':         (round(cd['PM10'].mean(), 4)
                                     if pd.notna(cd['PM10'].mean()) else np.nan),
                'station_count':    len(cd),
                'stations':         '; '.join(cd['station'].tolist()),
            })

        hdf = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=['cluster_id', 'wards', 'center_latitude', 'center_longitude',
                     'avg_severity', 'avg_pm25', 'avg_pm10', 'station_count', 'stations'])
        if not hdf.empty:
            hdf = hdf.sort_values('avg_severity', ascending=False).reset_index(drop=True)

        return df_c, hdf, n_cl, n_noi

    # ── Phase B: four sweeps ──────────────────────────────────────────────────
    # Severity thresholds: 60th pct (top-40%) and 40th pct (above-median / top-60%)
    # eps values         : 0.020 (~2.2 km) and 0.050 (~5.6 km)
    pct_60 = float(np.percentile(station_averages['severity'], 60))
    pct_40 = float(np.percentile(station_averages['severity'], 40))

    sweep_configs = [
        {'label': 'A',  'sev_pct': 60, 'cutoff': pct_60, 'eps': 0.020},
        {'label': 'B',  'sev_pct': 60, 'cutoff': pct_60, 'eps': 0.050},
        {'label': 'C',  'sev_pct': 40, 'cutoff': pct_40, 'eps': 0.020},
        {'label': 'D',  'sev_pct': 40, 'cutoff': pct_40, 'eps': 0.050},
    ]

    print(f"\n\n  Severity percentile reference:", flush=True)
    print(f"    40th pct (above-median, top-60%): {pct_40:.2f}", flush=True)
    print(f"    60th pct (top-40%)              : {pct_60:.2f}", flush=True)

    sweep_results = {}
    for cfg in sweep_configs:
        cands  = station_averages[station_averages['severity'] >= cfg['cutoff']].copy()
        excl   = station_averages[station_averages['severity'] <  cfg['cutoff']]
        lab, hdf, n_cl, n_noi = run_dbscan(cands, cfg['eps'], MIN_SAMPLES)
        sweep_results[cfg['label']] = {
            'cfg':        cfg,
            'candidates': cands,
            'excluded':   excl,
            'labelled':   lab,
            'hotspot_df': hdf,
            'n_clusters': n_cl,
            'n_noise':    n_noi,
        }

    # --- print summary comparison table ──────────────────────────────────────
    print(f"\n\n  {'='*80}", flush=True)
    print(f"  SWEEP COMPARISON  (min_samples={MIN_SAMPLES} throughout)", flush=True)
    print(f"  {'='*80}", flush=True)
    print(f"  {'Sweep':<7} {'Sev pct':>8} {'Cutoff':>8} {'eps':>6} "
          f"{'Candidates':>11} {'Clusters':>9} {'Noise':>6}", flush=True)
    print("  " + "-" * 62, flush=True)
    for cfg in sweep_configs:
        r = sweep_results[cfg['label']]
        print(f"  {cfg['label']:<7} {cfg['sev_pct']:>7}%  {cfg['cutoff']:>7.2f}  "
              f"{cfg['eps']:>6.3f}  {len(r['candidates']):>11}  "
              f"{r['n_clusters']:>9}  {r['n_noise']:>6}", flush=True)

    # --- detailed output per sweep ───────────────────────────────────────────
    for cfg in sweep_configs:
        r         = sweep_results[cfg['label']]
        km_approx = cfg['eps'] * 111.0
        print(f"\n{'='*80}", flush=True)
        print(f"SWEEP {cfg['label']}  |  severity >= {cfg['sev_pct']}th pct ({cfg['cutoff']:.1f})  "
              f"|  eps={cfg['eps']} (~{km_approx:.1f} km)  "
              f"|  {len(r['candidates'])} candidates", flush=True)
        print("="*80, flush=True)
        print(f"  Clusters : {r['n_clusters']}   Noise : {r['n_noise']}", flush=True)

        if r['n_noise'] > 0:
            noise_df = r['labelled'][r['labelled']['cluster'] == -1]
            for _, nr in noise_df.sort_values('severity', ascending=False).iterrows():
                print(f"    [noise] {nr['station']}  sev={nr['severity']:.1f}", flush=True)

        hdf = r['hotspot_df']
        if hdf.empty:
            print("  → No clusters formed.", flush=True)
        else:
            print(f"\n  {'Rank':<5} {'ID':<5} {'Wards':<34} {'Center Lat/Lon':<24} "
                  f"{'Severity':>9} {'PM2.5':>7} {'PM10':>7} {'N':>4}", flush=True)
            print("  " + "-" * 102, flush=True)
            for rank, (_, row) in enumerate(hdf.iterrows(), 1):
                coords = f"({row['center_latitude']:.4f}, {row['center_longitude']:.4f})"
                ws     = row['wards'][:32] + '..' if len(row['wards']) > 34 else row['wards']
                pm10d  = (f"{row['avg_pm10']:>7.1f}"
                          if pd.notna(row['avg_pm10']) else f"{'N/A':>7}")
                print(f"  {rank:<5} {int(row['cluster_id']):<5} {ws:<34} {coords:<24} "
                      f"{row['avg_severity']:>9.1f} {row['avg_pm25']:>7.1f} {pm10d} "
                      f"{row['station_count']:>4}", flush=True)

            for rank, (_, row) in enumerate(hdf.iterrows(), 1):
                pm10l = f"{row['avg_pm10']:.1f}" if pd.notna(row['avg_pm10']) else 'N/A'
                print(f"\n    #{rank} Cluster {int(row['cluster_id'])}", flush=True)
                print(f"       Wards    : {row['wards']}", flush=True)
                print(f"       Center   : ({row['center_latitude']:.4f}, "
                      f"{row['center_longitude']:.4f})", flush=True)
                print(f"       Severity : {row['avg_severity']:.1f}  "
                      f"PM2.5: {row['avg_pm25']:.1f}  PM10: {pm10l}", flush=True)
                print(f"       Stations ({row['station_count']}): {row['stations']}", flush=True)

    # ── Phase C: choose best configuration ───────────────────────────────────
    # Priority:
    #  1. Prefer severity threshold >= 40th pct (won't use severity-unfiltered data)
    #  2. Among configurations that satisfy (1), pick most clusters
    #  3. Tie-break: smaller eps (tighter zones are more actionable)
    eligible = [cfg['label'] for cfg in sweep_configs if cfg['sev_pct'] >= 40]
    best_label = min(
        eligible,
        key=lambda lbl: (
            -sweep_results[lbl]['n_clusters'],      # most clusters first
            sweep_results[lbl]['cfg']['eps'],        # then smallest eps
        )
    )
    best_cfg   = sweep_results[best_label]['cfg']
    chosen     = sweep_results[best_label]
    hotspot_df = chosen['hotspot_df']
    n_clusters = chosen['n_clusters']
    n_noise    = chosen['n_noise']
    sev_cutoff = best_cfg['cutoff']
    high_sev   = chosen['candidates']
    low_sev    = chosen['excluded']
    best_eps   = best_cfg['eps']

    print(f"\n\n{'='*80}", flush=True)
    print(f"CHOSEN: Sweep {best_label}  "
          f"sev >= {best_cfg['sev_pct']}th pct ({sev_cutoff:.1f})  "
          f"eps={best_eps} (~{best_eps*111:.1f} km)  "
          f"→  {n_clusters} cluster(s)", flush=True)
    print("="*80, flush=True)

    # --- annotate station_averages with final cluster labels -----------------
    # -2 = below severity threshold (not a candidate)
    # -1 = candidate but isolated noise
    # >=0 = hotspot cluster ID
    station_averages['cluster'] = -2
    chosen_labelled = chosen['labelled'][['station', 'cluster']].rename(
        columns={'cluster': '_cl'}
    )
    station_averages = station_averages.merge(chosen_labelled, on='station', how='left')
    station_averages['cluster'] = station_averages.apply(
        lambda r: int(r['_cl']) if pd.notna(r['_cl']) else r['cluster'], axis=1
    )
    station_averages.drop(columns=['_cl'], inplace=True)

    # ── Save outputs ──────────────────────────────────────────────────────────
    hotspot_df.to_csv(HOTSPOT_FILE, index=False)
    print(f"\n  Saved hotspot clusters  : {HOTSPOT_FILE}", flush=True)

    # Re-save ward_mapped_stations enriched with severity + cluster
    ward_mapped_full = ward_mapping.merge(
        station_averages[['station', 'PM2.5', 'PM10', 'severity', 'cluster', 'scoring_note']],
        on='station', how='left'
    )
    ward_mapped_full.to_csv(WARD_MAPPED_FILE, index=False)
    print(f"  Updated ward-mapped file: {WARD_MAPPED_FILE}", flush=True)
    print(f"  (cluster=-2 = station below 60th-pct severity threshold; "
          f"cluster=-1 = isolated noise; cluster>=0 = hotspot cluster)", flush=True)

else:
    hotspot_df = pd.DataFrame()
    n_noise    = 0
    n_clusters = 0
    best_eps   = None
    sev_cutoff = None
    high_sev   = pd.DataFrame()
    low_sev    = pd.DataFrame()
    print("\n  Hotspot detection skipped (scikit-learn unavailable).", flush=True)

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n\n" + "="*80, flush=True)
print("FINAL SUMMARY", flush=True)
print("="*80, flush=True)

print(f"\n  Stage 1 — Validation:", flush=True)
print(f"    Total stations    : {len(validation_df)}", flush=True)
print(f"    Dropped           : {len(dropped_stations)}  "
      f"(PM2.5 missing > {PM25_THRESHOLD}%)", flush=True)
print(f"    Retained          : {len(valid_stations)}", flush=True)

# Confirm the bug is fixed
print(f"\n  Dropped-stations bug fix confirmed:", flush=True)
if len(dropped_stations) == 0:
    print(f"    No stations dropped. City Railway Station (15.3%) and "
          f"Hombegowda Nagar (15.4%) correctly appear only in VALID_STATIONS.",
          flush=True)
else:
    dropped_names = dropped_stations['station'].tolist()
    # Verify that City Railway Station and Hombegowda Nagar are NOT in dropped
    false_drops = [n for n in ['City Railway Station, Bengaluru - KSPCB',
                               'Hombegowda Nagar, Bengaluru - KSPCB']
                   if n in dropped_names]
    if false_drops:
        print(f"    BUG STILL PRESENT: {false_drops} appear in dropped_stations "
              f"but should not!", flush=True)
    else:
        print(f"    City Railway Station and Hombegowda Nagar are correctly "
              f"in VALID_STATIONS (not dropped).", flush=True)

print(f"\n  Stage 2 — Ward Mapping:", flush=True)
if wards_gdf is not None:
    mapped_ok     = ward_mapping[
        ~ward_mapping['ward_name'].isin(['Outside Boundary', 'Ward data unavailable'])
    ]
    unique_wards  = mapped_ok['ward_name'].nunique()
    outside_count = (ward_mapping['ward_name'] == 'Outside Boundary').sum()
    print(f"    BBMP wards in file: {len(wards_gdf)}", flush=True)
    print(f"    Wards covered      : {unique_wards}  "
          f"({unique_wards/len(wards_gdf)*100:.1f}% of all BBMP wards)", flush=True)
    print(f"    Outside boundary   : {outside_count} station(s) "
          f"(all assigned via nearest-neighbour)", flush=True)
else:
    print("    Ward mapping unavailable (check network / geopandas install)", flush=True)
    unique_wards = 0

_eps_label = f"eps={best_eps}" if best_eps is not None else "eps=N/A"
print(f"\n  Stage 3 — Hotspot Detection "
      f"(DBSCAN {_eps_label}, min_samples=3, severity >= 60th pct):", flush=True)
if len(hotspot_df) > 0:
    print(f"    Severity cutoff   : {sev_cutoff:.2f}  "
          f"(top-40%: {len(high_sev)} candidate stations)", flush=True)
    print(f"    Chosen eps        : {best_eps}  (~{best_eps*111:.1f} km radius)", flush=True)
    print(f"    Clusters found    : {len(hotspot_df)}", flush=True)
    print(f"    Noise stations    : {n_noise}  (candidates that are too isolated)", flush=True)
    print(f"    Below-threshold   : {len(low_sev)}  (cluster=-2, not candidates)", flush=True)
    print(f"    Highest severity  : Cluster "
          f"{int(hotspot_df.iloc[0]['cluster_id'])}  — "
          f"{hotspot_df.iloc[0]['avg_severity']:.1f}", flush=True)
    print(f"    Lowest  severity  : Cluster "
          f"{int(hotspot_df.iloc[-1]['cluster_id'])}  — "
          f"{hotspot_df.iloc[-1]['avg_severity']:.1f}", flush=True)
else:
    print("    No clusters formed — all candidates are noise at all eps settings.", flush=True)

print(f"\n  PM10 Scoring Approach:", flush=True)
if max_sparse_year is not None:
    print(f"    Years {min(sparse_years)}–{max_sparse_year}: "
          f"pm25_only  (PM10 coverage < {PM10_SPARSE_THRESHOLD}%)", flush=True)
    print(f"    Years {max_sparse_year+1}–2025 : "
          f"weighted   (0.7×PM2.5 + 0.3×PM10)", flush=True)
else:
    print(f"    All years: weighted formula (0.7×PM2.5 + 0.3×PM10)", flush=True)

print("\n\n" + "="*80, flush=True)
print("OUTPUT FILES", flush=True)
print("="*80, flush=True)
print(f"  1. {VALIDATED_FILE}", flush=True)
print(f"  2. {WARD_MAPPED_FILE}", flush=True)
print(f"  3. {HOTSPOT_FILE}", flush=True)

print("\n" + "="*80, flush=True)
print(f"Pipeline completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("="*80, flush=True)

# Made with IBM Bob
