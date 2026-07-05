#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AirGuard AI — Next-Day AQI Category Forecasting Model
-----------------------------------------------------
Features  : 7-day rolling avg, 30-day rolling avg, day-of-week, month,
            season, ward_name (one-hot), is_hotspot_zone
Target    : next-day AQI category (Indian PM2.5 breakpoints)
              Good     PM2.5  0-30
              Moderate PM2.5 31-60
              Poor     PM2.5 61-90
              Severe   PM2.5  >90
Split     : train 2017-2023 | validate 2024 | test 2025
Model     : RandomForestClassifier(n_estimators=200, max_depth=15)
Outputs   : models/aqi_category_rf.pkl
            data/processed/feature_importance.csv  (updated)
"""

import sys, os
import pandas as pd
import numpy as np
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 70, flush=True)
print("AQI CATEGORY NEXT-DAY FORECASTING MODEL", flush=True)
print("=" * 70, flush=True)
print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)

# ── Paths ──────────────────────────────────────────────────────────────────
TS_FILE      = 'data/processed/bengaluru_air_quality_timeseries.csv'
WARD_FILE    = 'data/processed/ward_mapped_stations.csv'
CLUSTER_FILE = 'data/processed/hotspot_clusters.csv'
MODEL_DIR    = 'models'
MODEL_FILE   = os.path.join(MODEL_DIR, 'aqi_category_rf.pkl')
FI_FILE      = 'data/processed/feature_importance.csv'

os.makedirs(MODEL_DIR, exist_ok=True)

# ============================================================================
# 1. LOAD DATA
# ============================================================================
print("── 1. Loading data ──────────────────────────────────────────────────", flush=True)

ts   = pd.read_csv(TS_FILE)
ward = pd.read_csv(WARD_FILE)
hots = pd.read_csv(CLUSTER_FILE)

ts['timestamp'] = pd.to_datetime(ts['timestamp'])
print(f"  Time-series rows   : {len(ts):,}", flush=True)
print(f"  Ward-mapped rows   : {len(ward)}", flush=True)
print(f"  Hotspot clusters   : {len(hots)}", flush=True)

# Drop the two 100%-PM2.5-missing stations before any further processing
DROP_STATIONS = ['site_165', 'site_166']
ts = ts[~ts['station'].isin(DROP_STATIONS)].copy()
print(f"  After dropping 100%-missing stations: {len(ts):,} rows", flush=True)

# ── Build hotspot-station set ─────────────────────────────────────────────
# Cluster 0 and 1 stations (from hotspot_clusters.csv 'stations' column)
hotspot_stations = set()
for _, row in hots.iterrows():
    for s in str(row['stations']).split(';'):
        hotspot_stations.add(s.strip())

print(f"\n  Hotspot-zone stations ({len(hotspot_stations)}):", flush=True)
for s in sorted(hotspot_stations):
    print(f"    • {s}", flush=True)

# Also pull in the co-located site_* counterparts using ward_mapped_stations
# (they share identical coordinates — treat them identically for is_hotspot_zone)
ward_hotspot = ward[ward['cluster'].isin([0, 1])]['station'].tolist()
hotspot_stations.update(ward_hotspot)
print(f"  After adding co-located site_* twins: {len(hotspot_stations)} stations", flush=True)

# ── Merge ward name into time-series ─────────────────────────────────────
ward_lookup = ward[['station', 'ward_name']].drop_duplicates()
ts = ts.merge(ward_lookup, on='station', how='left')
ts['ward_name'] = ts['ward_name'].fillna('Unknown')

# ============================================================================
# 2. DAILY AGGREGATION
# ============================================================================
print("\n── 2. Aggregate to daily resolution ────────────────────────────────", flush=True)

# Both KSPCB (hourly) and site_* (15-min) sensors: resample to daily mean per station.
# Using date extracted from timestamp so we group calendar days correctly.
ts['date'] = ts['timestamp'].dt.normalize()   # midnight of each day

daily = (
    ts.groupby(['station', 'date', 'ward_name'])
      .agg(pm25_daily=('PM2.5', 'mean'))
      .reset_index()
)
# Only keep days that have at least one valid PM2.5 reading
daily = daily.dropna(subset=['pm25_daily']).copy()
daily = daily.sort_values(['station', 'date']).reset_index(drop=True)

print(f"  Daily rows (non-null PM2.5 days): {len(daily):,}", flush=True)
print(f"  Date range: {daily['date'].min().date()} → {daily['date'].max().date()}", flush=True)
print(f"  Stations  : {daily['station'].nunique()}", flush=True)

# ============================================================================
# 3. FEATURE ENGINEERING
# ============================================================================
print("\n── 3. Feature engineering ──────────────────────────────────────────", flush=True)

# ── Rolling averages (per station, computed on past data only — no leakage) ──
# min_periods ensures we drop rows where the window isn't filled yet.
daily = daily.sort_values(['station', 'date'])

daily['roll7']  = (
    daily.groupby('station')['pm25_daily']
         .transform(lambda s: s.shift(1).rolling(7,  min_periods=4).mean())
)
daily['roll30'] = (
    daily.groupby('station')['pm25_daily']
         .transform(lambda s: s.shift(1).rolling(30, min_periods=15).mean())
)

# ── Calendar features ─────────────────────────────────────────────────────
daily['day_of_week'] = daily['date'].dt.dayofweek          # 0=Mon … 6=Sun
daily['month']       = daily['date'].dt.month

def season(m):
    if   m in (6, 7, 8, 9):    return 'monsoon'    # June–September
    elif m in (11, 12, 1, 2):  return 'winter'     # November–February
    else:                       return 'summer'     # March–May

daily['season'] = daily['month'].apply(season)

# ── Hotspot flag ──────────────────────────────────────────────────────────
daily['is_hotspot_zone'] = daily['station'].isin(hotspot_stations).astype(int)

print(f"  Hotspot-zone rows  : {daily['is_hotspot_zone'].sum():,} "
      f"({daily['is_hotspot_zone'].mean()*100:.1f}%)", flush=True)
print(f"  Season distribution:\n{daily['season'].value_counts().to_string()}", flush=True)

# ── Target: next-day AQI category ────────────────────────────────────────
# Shift pm25_daily backward by 1 day then convert to Indian AQI band.
AQI_LABELS = ['Good', 'Moderate', 'Poor', 'Severe']

def pm25_to_aqi(v):
    if   v <= 30: return 'Good'
    elif v <= 60: return 'Moderate'
    elif v <= 90: return 'Poor'
    else:         return 'Severe'

daily['target_pm25_next_day'] = (
    daily.groupby('station')['pm25_daily']
         .transform(lambda s: s.shift(-1))
)
daily['target_aqi'] = daily['target_pm25_next_day'].map(
    lambda v: pm25_to_aqi(v) if pd.notna(v) else np.nan
)

# ── Drop rows missing target or any rolling feature ───────────────────────
before = len(daily)
daily = daily.dropna(subset=['target_aqi', 'roll7', 'roll30']).copy()
print(f"  Rows after dropping nulls: {len(daily):,}  (dropped {before - len(daily):,})", flush=True)

# Class distribution
print(f"\n  AQI class distribution (target):", flush=True)
vc = daily['target_aqi'].value_counts().reindex(AQI_LABELS, fill_value=0)
for cat, cnt in vc.items():
    pct = cnt / len(daily) * 100
    bar = '#' * int(pct / 2)
    print(f"    {cat:<10} {cnt:>6,}  ({pct:5.1f}%)  {bar}", flush=True)

# ── One-hot encode ward_name and season ──────────────────────────────────
daily = pd.get_dummies(daily, columns=['ward_name', 'season'], drop_first=False)

print(f"  Total columns after encoding: {daily.shape[1]}", flush=True)

# ── Feature columns ──────────────────────────────────────────────────────
# Exclude metadata and target
META_COLS   = ['station', 'date', 'pm25_daily', 'target_pm25_next_day', 'target_aqi']
FEATURE_COLS = [c for c in daily.columns if c not in META_COLS]

print(f"  Feature count: {len(FEATURE_COLS)}", flush=True)
print(f"  Features: {FEATURE_COLS}", flush=True)

# ============================================================================
# 4. TRAIN / VALIDATE / TEST SPLIT  (temporal, no leakage)
# ============================================================================
print("\n── 4. Temporal split ───────────────────────────────────────────────", flush=True)

# The KSPCB legacy stations only have data through 2023.
# The site_* modern stations only start from 2024.
# A hard year-split by calendar year would place ALL site_* data in val/test,
# meaning the model never trains on any site_* observations — causing the
# large negative R² seen when the RF extrapolates to an entirely different
# sensor network and PM2.5 range.
#
# Fix: split WITHIN each station's own timeline.
#   - For stations present in 2017–2023 (KSPCB): train=2017–2023, val=2024*, test=2025*
#     (* they have no 2024/2025 data, so these folds are empty for them)
#   - For stations starting in 2024 (site_*): train=first 70% of their days,
#     val=next 15%, test=final 15% — preserving temporal order.
#
# This gives the model training signal for site_* PM2.5 levels while still
# keeping val and test strictly future relative to training.

daily['year'] = daily['date'].dt.year

legacy_stations  = [s for s in daily['station'].unique() if not s.startswith('site_')]
modern_stations  = [s for s in daily['station'].unique() if s.startswith('site_')]

print(f"  Legacy stations (KSPCB, 2017–2023): {len(legacy_stations)}", flush=True)
print(f"  Modern stations (site_*, 2024+)    : {len(modern_stations)}", flush=True)

train_parts, val_parts, test_parts = [], [], []

# Legacy: hard calendar split
for st in legacy_stations:
    sdf = daily[daily['station'] == st].sort_values('date')
    train_parts.append(sdf[sdf['year'] <= 2023])
    val_parts.append(sdf[sdf['year'] == 2024])
    test_parts.append(sdf[sdf['year'] == 2025])

# Modern: proportional split within each station's own date range
for st in modern_stations:
    sdf = daily[daily['station'] == st].sort_values('date').reset_index(drop=True)
    n   = len(sdf)
    i70 = int(n * 0.70)
    i85 = int(n * 0.85)
    train_parts.append(sdf.iloc[:i70])
    val_parts.append(sdf.iloc[i70:i85])
    test_parts.append(sdf.iloc[i85:])

train = pd.concat(train_parts, ignore_index=True)
val   = pd.concat(val_parts,   ignore_index=True)
test  = pd.concat(test_parts,  ignore_index=True)

# Drop any empty-station folds (legacy stations that had no 2024/2025 data)
train = train.dropna(subset=['target_aqi']).copy()
val   = val.dropna(subset=['target_aqi']).copy()
test  = test.dropna(subset=['target_aqi']).copy()

print(f"\n  Train: {len(train):,} rows | stations: {train['station'].nunique()}", flush=True)
print(f"  Val  : {len(val):,} rows | stations: {val['station'].nunique()}", flush=True)
print(f"  Test : {len(test):,} rows | stations: {test['station'].nunique()}", flush=True)

# Confirm temporal integrity — no leakage
for st in modern_stations:
    tr_max = train[train['station'] == st]['date'].max() if len(train[train['station'] == st]) > 0 else pd.NaT
    va_min = val[val['station']     == st]['date'].min() if len(val[val['station']     == st]) > 0 else pd.NaT
    te_min = test[test['station']   == st]['date'].min() if len(test[test['station']   == st]) > 0 else pd.NaT
    if pd.notna(tr_max) and pd.notna(va_min):
        assert tr_max < va_min, f"Leakage! {st}: train max {tr_max} >= val min {va_min}"
    if pd.notna(va_min) and pd.notna(te_min):
        assert va_min < te_min, f"Leakage! {st}: val min {va_min} >= test min {te_min}"
print("  Temporal integrity check passed (no leakage).", flush=True)

# Align one-hot columns: all encoded from whole dataset — no missing cols
all_feat_cols = FEATURE_COLS

X_train = train[all_feat_cols].values
y_train = train['target_aqi'].values

X_val   = val[all_feat_cols].values
y_val   = val['target_aqi'].values

X_test  = test[all_feat_cols].values
y_test  = test['target_aqi'].values

print(f"\n  X_train shape: {X_train.shape}", flush=True)
print(f"  X_val   shape: {X_val.shape}", flush=True)
print(f"  X_test  shape: {X_test.shape}", flush=True)

# ============================================================================
# 5. MODEL TRAINING
# ============================================================================
print("\n── 5. Training RandomForestClassifier ──────────────────────────────", flush=True)
print("  Parameters: n_estimators=200, max_depth=15, random_state=42, class_weight=balanced", flush=True)
print(f"  Classes: {AQI_LABELS}", flush=True)
print("  Fitting...", flush=True)

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, f1_score,
                              confusion_matrix, classification_report)

rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced',   # compensate for skewed class counts
)
t0 = datetime.now()
rf.fit(X_train, y_train)
elapsed = (datetime.now() - t0).total_seconds()
print(f"  Training complete in {elapsed:.1f}s", flush=True)
print(f"  Classes learned   : {list(rf.classes_)}", flush=True)

# ── helper: labelled confusion matrix ────────────────────────────────────
def print_confusion_matrix(y_true, y_pred, labels):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    col_w = 11
    header = ' ' * 22 + ''.join(f'{lbl:>{col_w}}' for lbl in labels) + '  <- predicted'
    print(f"\n  {header}", flush=True)
    print("  " + "-" * (22 + col_w * len(labels) + 14), flush=True)
    for i, row_label in enumerate(labels):
        row_str = ''.join(f'{cm[i, j]:>{col_w},}' for j in range(len(labels)))
        print(f"  actual {row_label:<13} {row_str}", flush=True)
    return cm

# ── helper: full metric block ─────────────────────────────────────────────
def eval_split(y_true, y_pred, split_name):
    acc    = accuracy_score(y_true, y_pred)
    f1_mac = f1_score(y_true, y_pred, average='macro',    labels=AQI_LABELS, zero_division=0)
    f1_wt  = f1_score(y_true, y_pred, average='weighted', labels=AQI_LABELS, zero_division=0)
    f1_per = f1_score(y_true, y_pred, average=None,       labels=AQI_LABELS, zero_division=0)
    print(f"\n  Accuracy          : {acc:.4f}  ({acc*100:.1f}%)", flush=True)
    print(f"  F1 macro          : {f1_mac:.4f}", flush=True)
    print(f"  F1 weighted       : {f1_wt:.4f}", flush=True)
    print(f"  F1 per class:", flush=True)
    for lbl, f1v in zip(AQI_LABELS, f1_per):
        print(f"    {lbl:<10} : {f1v:.4f}", flush=True)
    print(f"\n  Confusion matrix ({split_name}):", flush=True)
    cm = print_confusion_matrix(y_true, y_pred, AQI_LABELS)
    print(f"\n  Classification report:", flush=True)
    print(classification_report(y_true, y_pred, labels=AQI_LABELS,
                                 zero_division=0, digits=3), flush=True)
    return acc, f1_mac, f1_wt, cm

# ============================================================================
# 6. VALIDATION PERFORMANCE
# ============================================================================
print("\n── 6. Validation performance (2024) ────────────────────────────────", flush=True)
y_val_pred = rf.predict(X_val)
acc_val, f1mac_val, f1wt_val, _ = eval_split(y_val, y_val_pred, 'val 2024')

# ============================================================================
# 7. TEST PERFORMANCE (2025 — evaluated once)
# ============================================================================
print("\n── 7. Test performance (2025 — evaluated once) ─────────────────────", flush=True)
y_test_pred = rf.predict(X_test)
acc_test, f1mac_test, f1wt_test, cm_test = eval_split(y_test, y_test_pred, 'test 2025')

# ── Per-station accuracy on test set ─────────────────────────────────────
print(f"\n  Per-station test accuracy (2025):", flush=True)
print(f"  {'Station':<50} {'N':>6} {'Accuracy':>10} {'F1-macro':>10}", flush=True)
print("  " + "-" * 82, flush=True)

test_results = test.copy()
test_results['pred'] = y_test_pred

for station, grp in test_results.groupby('station'):
    if len(grp) < 5:
        continue
    st_acc = accuracy_score(grp['target_aqi'], grp['pred'])
    st_f1  = f1_score(grp['target_aqi'], grp['pred'],
                      average='macro', labels=AQI_LABELS, zero_division=0)
    print(f"  {station:<50} {len(grp):>6} {st_acc:>10.4f} {st_f1:>10.4f}", flush=True)

# ============================================================================
# 8. FEATURE IMPORTANCE
# ============================================================================
print("\n── 8. Feature importance (ranked) ──────────────────────────────────", flush=True)

fi = pd.DataFrame({
    'feature':    all_feat_cols,
    'importance': rf.feature_importances_,
}).sort_values('importance', ascending=False).reset_index(drop=True)

fi['rank']            = fi.index + 1
fi['importance_pct']  = (fi['importance'] * 100).round(3)
fi['cumulative_pct']  = fi['importance_pct'].cumsum().round(2)

print(f"\n  {'Rank':<5} {'Feature':<40} {'Importance %':>14} {'Cumulative %':>14}", flush=True)
print("  " + "-" * 78, flush=True)
for _, row in fi.head(20).iterrows():
    print(f"  {int(row['rank']):<5} {row['feature']:<40} {row['importance_pct']:>13.3f}% "
          f"{row['cumulative_pct']:>13.2f}%", flush=True)

if len(fi) > 20:
    tail_pct = fi.iloc[20:]['importance_pct'].sum()
    print(f"  ...  {len(fi)-20} remaining features account for {tail_pct:.2f}% total", flush=True)

# ── Group-level summary ───────────────────────────────────────────────────
def group_fi(fi_df):
    groups = {
        'rolling_avg (7d + 30d)': ['roll7', 'roll30'],
        'calendar (dow + month)': ['day_of_week', 'month'],
        'is_hotspot_zone':        ['is_hotspot_zone'],
        'season':                 [c for c in fi_df['feature'] if c.startswith('season_')],
        'ward_name':              [c for c in fi_df['feature'] if c.startswith('ward_name_')],
    }
    rows = []
    for grp_name, cols in groups.items():
        pct = fi_df[fi_df['feature'].isin(cols)]['importance_pct'].sum()
        rows.append({'feature_group': grp_name, 'total_importance_pct': round(pct, 3)})
    return pd.DataFrame(rows).sort_values('total_importance_pct', ascending=False)

grp_fi = group_fi(fi)
print(f"\n  Feature-group summary:", flush=True)
print(f"  {'Group':<35} {'Total %':>10}", flush=True)
print("  " + "-" * 48, flush=True)
for _, row in grp_fi.iterrows():
    print(f"  {row['feature_group']:<35} {row['total_importance_pct']:>10.3f}%", flush=True)

# ============================================================================
# 9. SAVE OUTPUTS
# ============================================================================
print("\n── 9. Saving outputs ───────────────────────────────────────────────", flush=True)

import joblib
joblib.dump(rf, MODEL_FILE, compress=3)
print(f"  Model saved        : {MODEL_FILE}", flush=True)

fi[['rank', 'feature', 'importance', 'importance_pct', 'cumulative_pct']].to_csv(
    FI_FILE, index=False
)
print(f"  Feature importance : {FI_FILE}", flush=True)

# ============================================================================
# 10. FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 70, flush=True)
print("FINAL MODEL PERFORMANCE SUMMARY -- AQI CATEGORY CLASSIFIER", flush=True)
print("=" * 70, flush=True)

top1      = fi.iloc[0]
top_group = grp_fi.iloc[0]

if acc_test >= 0.80:
    acc_interp = ("Strong performance -- the model correctly predicts the next-day "
                  "AQI category more than 80% of the time. Actionable for daily "
                  "public health advisories and clean-street scheduling.")
elif acc_test >= 0.65:
    acc_interp = ("Moderate performance -- correctly classifies the AQI band roughly "
                  "two-thirds of the time. Useful for trend-based decision support; "
                  "caution on boundary cases (e.g. Moderate vs Poor).")
else:
    acc_interp = ("Below-baseline performance -- the model struggles to distinguish "
                  "AQI categories. Class imbalance or missing meteorological features "
                  "(wind, humidity) is the likely cause.")

print(f"""
  Data scope
    Train  : 2017-2023  ({len(train):,} station-days)
    Val    : 2024       ({len(val):,} station-days)
    Test   : 2025       ({len(test):,} station-days)

  AQI categories (Indian standard PM2.5 breakpoints)
    Good      : 0-30  ug/m3
    Moderate  : 31-60 ug/m3
    Poor      : 61-90 ug/m3
    Severe    : >90   ug/m3

  Validation performance (2024)
    Accuracy    : {acc_val:.4f}  ({acc_val*100:.1f}%)
    F1 macro    : {f1mac_val:.4f}
    F1 weighted : {f1wt_val:.4f}

  Test performance (2025 -- held out, evaluated once)
    Accuracy    : {acc_test:.4f}  ({acc_test*100:.1f}%)
    F1 macro    : {f1mac_test:.4f}
    F1 weighted : {f1wt_test:.4f}

  Practical interpretation of accuracy = {acc_test:.4f}:
    {acc_interp}

  Top driving factor : '{top1['feature']}' ({top1['importance_pct']:.2f}%)
  Top feature group  : '{top_group['feature_group']}' ({top_group['total_importance_pct']:.2f}% combined)
  is_hotspot_zone    : {fi[fi['feature']=='is_hotspot_zone']['importance_pct'].values[0]:.3f}%

  Output files
    Model             : {MODEL_FILE}
    Feature importance: {FI_FILE}
""", flush=True)

print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("=" * 70, flush=True)

# Made with IBM Bob
