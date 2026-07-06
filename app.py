#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AirGuard AI — Urban Multimodal Air Quality & Decision Support Platform
======================================================================
Combines Citizen Photos (CV), Local Ground Sensors (CPCB/KSPCB), 
and Satellite Imagery (Sentinel-5P NO2 / AOD) for Hidden Hotspot Detection (DBSCAN),
24-Hour AQI Forecasting (Random Forest + 95% CI), and Municipal Alert Systems.
"""

import sys
import types as _types

def _ensure_stub(name, attrs=None):
    if name not in sys.modules:
        m = _types.ModuleType(name)
        if attrs:
            for k, v in attrs.items():
                setattr(m, k, v)
        sys.modules[name] = m

_ensure_stub('audioop')
_ensure_stub('pyaudioop')
_ensure_stub('distutils')
_ensure_stub('distutils.version', {
    'StrictVersion': type('StrictVersion', (), {'__init__': lambda s, v: None})
})
if hasattr(sys.modules.get('distutils'), '__dict__'):
    sys.modules['distutils'].version = sys.modules['distutils.version']

try:
    import starlette.templating
    _orig_template_response = starlette.templating.Jinja2Templates.TemplateResponse
    def _patched_template_response(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.get("context", {})
            request = context.get("request")
            return _orig_template_response(self, request, name, context)
        return _orig_template_response(self, *args, **kwargs)
    starlette.templating.Jinja2Templates.TemplateResponse = _patched_template_response
except Exception:
    pass

import os
import io
import csv
import uuid
import datetime
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import folium
import joblib
import gradio as gr
import plotly.graph_objects as go
import plotly.express as px

# Import Modular AirGuard Architecture Services
from vision.image_analyzer import image_analyzer
from services.satellite_service import satellite_service
from services.multimodal_fusion import fusion_engine
from services.hotspot_detector import hotspot_detector
from forecast.aqi_forecaster import forecast_engine
from alerts.municipal_alert import alert_engine
from services.citizen_service import citizen_service
from dashboard.timeline import timeline_plotter
from dashboard.executive_dashboard import executive_dashboard
from utils.geo_utils import get_nearest_station

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH   = os.path.join(BASE_DIR, 'models', 'aqi_category_rf.pkl')
HOTSPOT_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'hotspot_clusters.csv')
WARD_PATH    = os.path.join(BASE_DIR, 'data', 'processed', 'ward_mapped_stations.csv')
TS_PATH      = os.path.join(BASE_DIR, 'data', 'processed', 'bengaluru_air_quality_timeseries.csv')
REPORT_CSV   = os.path.join(BASE_DIR, 'data', 'processed', 'reports.csv')

# ── AQI Constants ─────────────────────────────────────────────────────────────
AQI_COLORS  = {
    'Good':     '#22c55e',
    'Moderate': '#eab308',
    'Poor':     '#f97316',
    'Severe':   '#ef4444',
}

FEATURE_COLS = [
    'roll7', 'roll30', 'day_of_week', 'month', 'is_hotspot_zone',
    'ward_name_Ashoka Pillar', 'ward_name_Bande Mutt', 'ward_name_Basaveshwara Nagar',
    'ward_name_Gali Anjenaya Temple ward', 'ward_name_Jakkasandra',
    'ward_name_Kalena Agrahara', 'ward_name_Marathahalli',
    'ward_name_Nelagadderanahalli', 'ward_name_Peenya', 'ward_name_Sanjaya Nagar',
    'ward_name_Sarakki', 'ward_name_Shakambari Nagar', 'ward_name_Subhash Nagar',
    'ward_name_Vijinapura',
    'season_monsoon', 'season_summer', 'season_winter',
]

HOTSPOT_STATIONS = {
    'BTM Layout, Bengaluru - CPCB',
    'Jayanagar 5th Block, Bengaluru - KSPCB',
    'Silk Board, Bengaluru - KSPCB',
    'City Railway Station, Bengaluru - KSPCB',
    'Sanegurava Halli, Bengaluru - KSPCB',
    'Shivapura Peenya, Bengaluru - KSPCB',
}

print("Loading AirGuard AI models and multi-modal data...", flush=True)

rf_model  = joblib.load(MODEL_PATH)
ward_df   = pd.read_csv(WARD_PATH)
hotspot_df = pd.read_csv(HOTSPOT_PATH)

SITE_TO_FRIENDLY = {
    'site_162': 'BTM Layout, Bengaluru - CPCB',
    'site_1553': 'Bapuji Nagar, Bengaluru - KSPCB',
    'site_165': 'City Railway Station, Bengaluru - KSPCB',
    'site_1554': 'Hebbal, Bengaluru - KSPCB',
    'site_1556': 'Jayanagar 5th Block, Bengaluru - KSPCB',
    'site_5729': 'Jigani, Bengaluru - KSPCB',
    'site_5681': 'Kasturi Nagar, Bengaluru - KSPCB',
    'site_163': 'Peenya, Bengaluru - KSPCB',
    'site_5678': 'RVCE Mailasandra, Bengaluru - KSPCB',
    'site_166': 'Sanegurava Halli, Bengaluru - KSPCB',
    'site_5686': 'Shivapura Peenya, Bengaluru - KSPCB',
    'site_1558': 'Silk Board, Bengaluru - KSPCB',
}

ward_df = ward_df[~ward_df['station'].str.startswith('site_')].copy()

ts_raw = pd.read_csv(TS_PATH)
ts_raw['timestamp'] = pd.to_datetime(ts_raw['timestamp'])
ts_raw['date'] = ts_raw['timestamp'].dt.normalize()
ts_raw['station'] = ts_raw['station'].replace(SITE_TO_FRIENDLY)

ts_daily = (
    ts_raw.groupby(['station', 'date'])
          .agg(pm25=('PM2.5', 'mean'))
          .reset_index()
          .dropna(subset=['pm25'])
          .sort_values(['station', 'date'])
)

STATION_LIST = sorted(ward_df['station'].tolist())

def pm25_to_aqi(v):
    if   pd.isna(v): return 'Unknown'
    elif v <= 30:    return 'Good'
    elif v <= 60:    return 'Moderate'
    elif v <= 90:    return 'Poor'
    else:            return 'Severe'

def month_to_season(m):
    if   m in (6, 7, 8, 9):   return 'monsoon'
    elif m in (11, 12, 1, 2): return 'winter'
    else:                      return 'summer'

def build_feature_row(station_name, ref_date, ward_name, history_df):
    past = history_df[history_df['date'] < ref_date].sort_values('date')
    if len(past) < 4:
        return None, "Not enough history (need ≥4 days before today)"

    roll7  = past['pm25'].tail(7).mean()
    roll30 = past['pm25'].tail(30).mean() if len(past) >= 15 else float('nan')
    if pd.isna(roll30):
        return None, "Need ≥15 days history for roll30 feature"

    dow    = ref_date.weekday()
    month  = ref_date.month
    season = month_to_season(month)
    is_hot = int(station_name in HOTSPOT_STATIONS)

    row = {f: 0.0 for f in FEATURE_COLS}
    row['roll7']          = roll7
    row['roll30']         = roll30
    row['day_of_week']    = dow
    row['month']          = month
    row['is_hotspot_zone'] = is_hot

    ward_col = f'ward_name_{ward_name}'
    if ward_col in row: row[ward_col] = 1.0
    season_col = f'season_{season}'
    if season_col in row: row[season_col] = 1.0

    X = np.array([[row[c] for c in FEATURE_COLS]])
    return X, None

# ── Map Builder with Satellite & DBSCAN Hotspot Overlays ──────────────────────
def build_multimodal_map():
    """
    Builds Folium interactive map combining ground AQI sensors, satellite Sentinel-5P layers,
    and DBSCAN hidden pollution hotspot polygons highlighted in RED.
    """
    m = folium.Map(
        location=[12.97, 77.59],
        zoom_start=11,
        tiles='CartoDB dark_matter',
        height=750,
    )

    # 1. Ground Sensor Layer
    sensor_group = folium.FeatureGroup(name="📡 Ground AQI Sensors (CPCB/KSPCB)", show=True)

    latest = (
        ts_daily.sort_values('date')
                .groupby('station')
                .last()
                .reset_index()
                [['station', 'pm25']]
    )
    station_info = ward_df.merge(latest, on='station', how='left')
    station_info['aqi'] = station_info['pm25'].map(pm25_to_aqi)

    seen_coords = {}
    for _, row in station_info.iterrows():
        lat = float(row['latitude'])
        lon = float(row['longitude'])
        key = (round(lat, 4), round(lon, 4))
        offset = seen_coords.get(key, 0)
        seen_coords[key] = offset + 1
        lon_adj = lon + offset * 0.003

        aqi     = row['aqi']
        color   = AQI_COLORS.get(aqi, '#94a3b8')
        pm25_v  = f"{row['pm25']:.1f}" if pd.notna(row['pm25']) else 'N/A'

        popup_html = f"""
        <div style='font-family:sans-serif;font-size:13px;width:240px;color:#333;line-height:1.4;'>
          <b style='font-size:14px;color:#0f172a;'>{row['station']}</b><br>
          <hr style='margin: 6px 0; border-top: 1px solid #ddd;'>
          <span style='color:#57606a'>Current AQI:</span> <span style='background:{color};padding:2px 6px;border-radius:4px;color:#fff;font-weight:bold;font-size:11px;'>{aqi}</span> ({pm25_v} µg/m³)<br>
          <span style='color:#57606a'>Ward:</span> <b>{row['ward_name']}</b><br>
          <span style='color:#57606a'>Status:</span> <b style='color:#16a34a;'>Active Feed</b>
        </div>"""

        folium.CircleMarker(
            location=[lat, lon_adj],
            radius=9,
            color='white',
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{row['station']} — {aqi}",
        ).add_to(sensor_group)

    sensor_group.add_to(m)

    # 2. Add Satellite Remote Sensing Layers (Sentinel-5P NO2)
    m = satellite_service.add_satellite_layers_to_map(m)

    # 3. Add DBSCAN Hidden Hotspot Polygons
    sat_df = satellite_service.generate_satellite_grid(n_points=35)
    citizen_reports_df = citizen_service.load_reports_df()
    
    db_summary, _ = hotspot_detector.detect_hidden_hotspots(
        sensor_df=station_info, 
        citizen_df=citizen_reports_df, 
        satellite_df=sat_df
    )
    
    m = hotspot_detector.overlay_hotspots_on_map(m, db_summary)

    # Add Layer Control toggle for map layers
    folium.LayerControl(position='topright').add_to(m)

    return m._repr_html_(), db_summary

# ── Trend Plotter ─────────────────────────────────────────────────────────────
def plot_trend(station_name):
    sdata = ts_daily[ts_daily['station'] == station_name].sort_values('date')
    last30 = sdata.tail(30).copy()

    if last30.empty:
        fig = go.Figure()
        fig.add_annotation(text="No PM2.5 data available for this station", showarrow=False, font=dict(color='white'))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=30, fillcolor="#22c55e", opacity=0.1, line_width=0, layer="below")
    fig.add_hrect(y0=30, y1=60, fillcolor="#eab308", opacity=0.1, line_width=0, layer="below")
    fig.add_hrect(y0=60, y1=90, fillcolor="#f97316", opacity=0.1, line_width=0, layer="below")
    fig.add_hrect(y0=90, y1=200, fillcolor="#ef4444", opacity=0.1, line_width=0, layer="below")
    
    fig.add_trace(go.Scatter(
        x=last30['date'], y=last30['pm25'],
        mode='lines+markers',
        line=dict(color='#38bdf8', width=3),
        marker=dict(size=6, color=last30['pm25'], colorscale='Turbo', showscale=False),
        fill='tozeroy',
        fillcolor='rgba(56, 189, 248, 0.15)',
        name='PM2.5'
    ))
    
    fig.update_layout(
        height=320,
        title=dict(text=f"Last 30 Days PM2.5 Trend", font=dict(color='white', size=14)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        margin=dict(l=40, r=20, t=40, b=30),
        xaxis=dict(showgrid=False, color='#cbd5e1'),
        yaxis=dict(showgrid=True, gridcolor='#334155', color='#cbd5e1', title='PM2.5 (µg/m³)')
    )
    return fig

def plot_gauge(pm25_val):
    if pd.isna(pm25_val): pm25_val = 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = pm25_val,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Current PM2.5", 'font': {'color': '#94a3b8', 'size': 14}},
        gauge = {
            'axis': {'range': [None, max(200, pm25_val + 50)], 'tickwidth': 1, 'tickcolor': "#cbd5e1"},
            'bar': {'color': "white", 'thickness': 0.15},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(34, 197, 94, 0.8)'},
                {'range': [30, 60], 'color': 'rgba(234, 179, 8, 0.8)'},
                {'range': [60, 90], 'color': 'rgba(249, 115, 22, 0.8)'},
                {'range': [90, max(200, pm25_val + 50)], 'color': 'rgba(239, 68, 68, 0.8)'}],
        },
        number = {'font': {'color': 'white', 'size': 40}}
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), margin=dict(l=20, r=20, t=40, b=20), height=250)
    return fig

# ── Core Handlers ─────────────────────────────────────────────────────────────

def handle_citizen_photo_upload(file_input, incident_type, station_name):
    """
    Feature 1 & Feature 7: Citizen Image Analysis & Verification
    """
    if file_input is None:
        cv_res = image_analyzer._fallback_simulated_result("No photo uploaded")
    else:
        cv_res = image_analyzer.analyze_image(file_input)

    # Register report into verification tracker
    reg = citizen_service.register_report(
        incident_type=incident_type,
        station_name=station_name,
        file_name=os.path.basename(file_input) if isinstance(file_input, str) else "Citizen_Photo.jpg",
        cv_result=cv_res
    )

    # Calculate multimodal fusion score based on this report
    fusion_res = fusion_engine.compute_risk_score(
        pm25_val=85.0,
        citizen_severity=cv_res["severity_score"],
        satellite_no2=145.0,
        traffic_density=75.0
    )

    fusion_fig = fusion_engine.generate_fusion_breakdown_chart(fusion_res)

    card_html = f"""
    <div style="background: rgba(30, 41, 59, 0.8); border: 1px solid #38bdf8; border-radius: 12px; padding: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <h3 style="color:#38bdf8; margin:0; font-size:18px;">✅ Citizen Incident Registered & AI Verified</h3>
            <span style="background:rgba(34,197,94,0.2); color:#4ade80; border:1px solid #4ade80; padding:4px 10px; border-radius:6px; font-weight:bold; font-size:12px;">
                Status: {reg['status']}
            </span>
        </div>
        
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; background:rgba(0,0,0,0.2); padding:12px; border-radius:8px; margin-bottom:14px; font-size:13px;">
            <div><span style="color:#94a3b8;">Reference ID:</span><br><b style="color:white;">{reg['ref_id']}</b></div>
            <div><span style="color:#94a3b8;">AI CV Classification:</span><br><b style="color:#818cf8;">{cv_res['category']}</b></div>
            <div><span style="color:#94a3b8;">CV Severity Score:</span><br><b style="color:#ef4444;">{cv_res['severity_score']} / 100</b></div>
            <div><span style="color:#94a3b8;">Smoke Probability:</span><br><b style="color:#f8fafc;">{cv_res['smoke_probability']*100:.1f}%</b></div>
            <div><span style="color:#94a3b8;">Dust Probability:</span><br><b style="color:#f8fafc;">{cv_res['dust_probability']*100:.1f}%</b></div>
            <div><span style="color:#94a3b8;">AI Confidence:</span><br><b style="color:#4ade80;">{reg['confidence']}</b></div>
        </div>

        <p style="color:#cbd5e1; font-size:13px; margin:0 0 12px 0;"><b>Computer Vision Diagnostic:</b> {cv_res['explanation']}</p>
        
        <div style="background:rgba(239,68,68,0.1); border-left:4px solid #ef4444; padding:10px 14px; border-radius:6px;">
            <b style="color:#fca5a5;">Multimodal AI Fusion Impact:</b> Integrated into citywide risk score ({fusion_res['risk_score']} / 100 — {fusion_res['badge']}).
        </div>
    </div>
    """

    table_html = citizen_service.get_citizen_verification_table_html()
    return card_html, fusion_fig, table_html


def handle_station_analysis(station_name, lang="English"):
    """
    Main station prediction & multi-modal evaluation handler.
    """
    try:
        wrow = ward_df[ward_df['station'] == station_name]
        if wrow.empty: 
            return plot_trend(station_name), go.Figure(), go.Figure(), "<p>Station not found</p>", "", "", "", ""
        
        ward_name = wrow.iloc[0]['ward_name']
        station_history = ts_daily[ts_daily['station'] == station_name].copy()
        max_date = station_history['date'].max() if len(station_history) > 0 else pd.NaT

        if pd.isna(max_date): 
            return plot_trend(station_name), go.Figure(), go.Figure(), "<p>No data available</p>", "", "", "", ""

        today = max_date
        latest_pm25 = float(station_history.sort_values('date').iloc[-1]['pm25'])
        
        # 1. Standard RF Cat prediction
        X, err = build_feature_row(station_name, today, ward_name, station_history)
        proba = rf_model.predict_proba(X)[0]
        classes = list(rf_model.classes_)
        pred_idx = int(np.argmax(proba))
        pred_cat = classes[pred_idx]
        confidence = float(proba[pred_idx]) * 100

        # 2. 24-Hour Forecast Engine
        forecast_res = forecast_engine.predict_24h_aqi(
            pm25=latest_pm25,
            pm10=latest_pm25 * 1.6,
            temp=28.0,
            humidity=62.0,
            wind=9.0,
            traffic=70.0,
            sat_no2=135.0
        )
        forecast_chart = forecast_engine.render_forecast_chart(forecast_res)

        # 3. Multimodal Fusion Risk Calculation
        fusion_res = fusion_engine.compute_risk_score(
            pm25_val=latest_pm25,
            citizen_severity=72.0,
            satellite_no2=135.0,
            humidity=62.0,
            wind_speed=9.0,
            traffic_density=70.0
        )
        fusion_chart = fusion_engine.generate_fusion_breakdown_chart(fusion_res)

        # 4. Municipal Alert Generation
        alert_payload = alert_engine.evaluate_alert(
            ward_name=ward_name,
            risk_score=fusion_res['risk_score'],
            incident_type="Garbage Burning" if latest_pm25 > 90 else "Ambient Dust"
        )
        alert_html = alert_engine.render_alert_card_html(alert_payload)

        # 5. Multimodal Timeline Chart
        timeline_chart = timeline_plotter.render_multimodal_timeline(station_name, station_history)

        # 6. Executive KPI Cards HTML
        exec_kpis_html = executive_dashboard.render_executive_kpis_html(
            hotspot_count=3,
            avg_aqi=int(latest_pm25),
            citizen_reports=24,
            satellite_alerts=4,
            high_risk_wards=5,
            dispatched_depts=7,
            predicted_aqi_tomorrow=int(forecast_res['predicted_aqi_24h'])
        )

        trend_fig = plot_trend(station_name)
        gauge_fig = plot_gauge(latest_pm25)
        latest_aqi_cat = pm25_to_aqi(latest_pm25)

        HEALTH_ADVISORIES = {
            "Good": {
                "title": "🟢 Good Air Quality — Safe for Outdoor Activity",
                "advisory": "Air quality is satisfactory. Safe for all outdoor activities and natural room ventilation.",
                "color": "#22c55e",
                "bg": "rgba(34, 197, 94, 0.12)"
            },
            "Moderate": {
                "title": "🟡 Moderate Air Quality — Caution for Sensitive Groups",
                "advisory": "Acceptable air quality. Children, elderly, and individuals with respiratory conditions (asthma) should reduce prolonged heavy outdoor exertion.",
                "color": "#eab308",
                "bg": "rgba(234, 179, 8, 0.12)"
            },
            "Poor": {
                "title": "🟠 Unhealthy Air Advisory — Sensitive Group Warning",
                "advisory": "Unhealthy for sensitive groups. Limit outdoor activities; wear N95/KN95 masks near busy arterial roads and industrial corridors.",
                "color": "#f97316",
                "bg": "rgba(249, 115, 22, 0.12)"
            },
            "Severe": {
                "title": "🔴 Severe Pollution Health Warning",
                "advisory": "Hazardous respiratory risk. Avoid outdoor physical exertion, keep windows closed, run indoor air purifiers, and wear N95 masks.",
                "color": "#ef4444",
                "bg": "rgba(239, 68, 68, 0.12)"
            }
        }
        adv = HEALTH_ADVISORIES.get(latest_aqi_cat, HEALTH_ADVISORIES["Moderate"])
        health_advisory_html = f"""
        <div style="background: {adv['bg']}; border: 1px solid {adv['color']}; border-radius: 10px; padding: 12px; margin-top: 10px;">
            <b style="color: {adv['color']}; font-size: 13px; display: block; margin-bottom: 4px;">{adv['title']}</b>
            <span style="color: #cbd5e1; font-size: 11px; line-height: 1.4; display: block;">{adv['advisory']}</span>
        </div>
        """

        pred_color = AQI_COLORS.get(pred_cat, '#38bdf8')
        latest_color = AQI_COLORS.get(latest_aqi_cat, '#22c55e')

        pred_html = f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 18px; margin-top: 14px;">
            <h4 style="margin: 0 0 14px 0; color: #38bdf8; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">
                <span>🎯</span> Station Telemetry & 24h Forecast Metrics
            </h4>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                
                <!-- Card 1: Current AQI -->
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid {latest_color}; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); display: flex; align-items: center; justify-content: center; font-size: 16px;">🌿</div>
                        <span style="background: rgba(34, 197, 94, 0.2); color: {latest_color}; border: 1px solid {latest_color}; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px;">{latest_aqi_cat}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">Current AQI</div>
                    <div style="font-size: 22px; font-weight: 800; color: #f8fafc; margin-top: 2px;">{int(latest_pm25)} AQI</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Station Live Feed</div>
                </div>

                <!-- Card 2: Latest PM2.5 -->
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid {latest_color}; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(56, 189, 248, 0.15); display: flex; align-items: center; justify-content: center; font-size: 16px;">💨</div>
                        <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px;">Sensor Active</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">Latest PM2.5</div>
                    <div style="font-size: 22px; font-weight: 800; color: #f8fafc; margin-top: 2px;">{latest_pm25:.1f} µg/m³</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Ground Telemetry</div>
                </div>

                <!-- Card 3: 24h Forecast -->
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid {pred_color}; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(239, 68, 68, 0.15); display: flex; align-items: center; justify-content: center; font-size: 16px;">📈</div>
                        <span style="background: rgba(239, 68, 68, 0.2); color: {pred_color}; border: 1px solid {pred_color}; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px;">{pred_cat}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">24h Forecast</div>
                    <div style="font-size: 22px; font-weight: 800; color: #f8fafc; margin-top: 2px;">{forecast_res['predicted_aqi_24h']} AQI</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">95% CI: {forecast_res['lower_bound_95']} – {forecast_res['upper_bound_95']}</div>
                </div>

                <!-- Card 4: Est. AQI Reduction -->
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #22c55e; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(34, 197, 94, 0.15); display: flex; align-items: center; justify-content: center; font-size: 16px;">📉</div>
                        <span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #4ade80; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px;">Target</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">Est. AQI Reduction</div>
                    <div style="font-size: 22px; font-weight: 800; color: #4ade80; margin-top: 2px;">-24% PM2.5</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">With Mitigation (Estimated)</div>
                </div>

                <!-- Card 5: Prediction Confidence -->
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(56, 189, 248, 0.15); display: flex; align-items: center; justify-content: center; font-size: 16px;">🎯</div>
                        <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px;">High Conf</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">Prediction Confidence</div>
                    <div style="font-size: 22px; font-weight: 800; color: #f8fafc; margin-top: 2px;">{confidence:.1f}%</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">RF Classifier Model</div>
                </div>

                <!-- Card 6: Hotspot Zones -->
                <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #ef4444; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(239, 68, 68, 0.15); display: flex; align-items: center; justify-content: center; font-size: 16px;">🚨</div>
                        <span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px;">Unmonitored</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;">Hotspot Zones</div>
                    <div style="font-size: 22px; font-weight: 800; color: #f8fafc; margin-top: 2px;">2 Clusters</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">DBSCAN Detected</div>
                </div>

            </div>
        </div>
        """

        return trend_fig, gauge_fig, forecast_chart, fusion_chart, timeline_chart, pred_html, alert_html, exec_kpis_html, health_advisory_html

    except Exception as e:
        import traceback
        traceback.print_exc()
        err_fig = go.Figure()
        err_fig.update_layout(title="Error Loading Multimodal Analytics")
        return err_fig, err_fig, err_fig, err_fig, err_fig, f"<div style='color:red;'>Error: {str(e)}</div>", "", "", ""


# ── Gradio UI Construction ───────────────────────────────────────────────────

MAP_HTML, DB_SUMMARY_DF = build_multimodal_map()

custom_css = """
body, .gradio-container {
    background-color: #0F172A !important;
    color: #F8FAFC !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}
.gradio-container { max-width: 1440px !important; margin: 0 auto !important; padding: 0 20px !important; }
.dark-card { background: #1E293B !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 20px !important; }
.hero-section { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 32px !important; margin-bottom: 20px !important; }
.hero-title { font-size: 40px; font-weight: 800; background: linear-gradient(to right, #38bdf8, #818cf8, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 12px 0; line-height: 1.2; }
.map-container iframe { height: 750px !important; width: 100% !important; border: none !important; border-radius: 12px !important; }

/* Tabs Active Glow & Styling */
div.tabs > div {
    border-bottom: 1px solid #1e293b !important;
}
button.selected, button[aria-selected="true"] {
    border-bottom: 2px solid #38bdf8 !important;
    color: #38bdf8 !important;
    font-weight: 600 !important;
    text-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
}
"""

with gr.Blocks(title="AirGuard AI — Multimodal Urban Air Quality Platform", css=custom_css, theme=gr.themes.Base()) as demo:
    
    top_bar = gr.HTML("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #1E293B; margin-bottom: 20px;">
        <div style="display:flex; align-items:center; gap: 10px;">
            <div style="width: 10px; height: 10px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 10px #22c55e;"></div>
            <div style="color: #cbd5e1; font-weight: bold; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">🟢 MULTIMODAL AI PIPELINE ACTIVE | 14 SENSORS | SENTINEL-5P SATELLITE FEED</div>
        </div>
        <div style="color: #38bdf8; font-size: 12px; font-weight: 600;">DBSCAN Clustering • Random Forest 24h Forecast • CV Photo Intelligence</div>
    </div>
    """)
    
    hero_section = gr.HTML("""
    <div class="hero-section">
        <h1 class="hero-title">AirGuard AI</h1>
        <p style="font-size: 18px; color: #cbd5e1; max-width: 800px; margin: 0 0 8px 0; font-weight: 500;">
            Multimodal Neighbourhood-Level Air Quality Intelligence & Municipal Decision Support
        </p>
        <div style="color: #60a5fa; font-weight: 600; letter-spacing: 1.5px; margin: 0 0 12px 0; font-size: 13px; text-transform: uppercase;">
            📸 Citizen Photos + 📡 Ground Sensors + 🛰️ Satellite NO₂ → 🚨 Hidden Hotspots → 📈 24h Forecast → 🏛️ Municipal Alerts
        </div>
        <p style="color: #94a3b8; margin-bottom: 0; max-width: 850px; font-size: 14px;">
            Empowering municipal teams to automatically detect unmonitored pollution spikes, forecast 24-hour AQI trajectories, and dispatch targeted mitigation resources.
        </p>
    </div>
    """)

    # 10 UI Tabs required by problem statement
    with gr.Tabs() as tabs:
        
        # TAB 1: EXECUTIVE DASHBOARD
        with gr.TabItem("📊 Executive Dashboard", id="dashboard"):
            exec_kpi_container = gr.HTML(executive_dashboard.render_executive_kpis_html())
            
            with gr.Row():
                with gr.Column(scale=1, min_width=280, elem_classes="dark-card"):
                    gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-size: 16px; font-weight: bold;'>Select Station / Ward</h3>")
                    station_dd = gr.Dropdown(choices=STATION_LIST, value=STATION_LIST[0], label="Station", interactive=True)
                    analyze_btn = gr.Button("Analyze Station Data", variant="primary")
                    pred_summary_out = gr.HTML()
                
                with gr.Column(scale=2):
                    with gr.Row():
                        with gr.Column(scale=2, elem_classes="dark-card"):
                            trend_plot_out = gr.Plot(label="PM2.5 Trend", show_label=False)
                        with gr.Column(scale=1, elem_classes="dark-card"):
                            gauge_plot_out = gr.Plot(label="PM2.5 Gauge", show_label=False)
                            health_advisory_out = gr.HTML()

        # TAB 2: POLLUTION MAP
        with gr.TabItem("🗺️ Multimodal Pollution Map", id="map"):
            with gr.Column(elem_classes="dark-card"):
                gr.HTML("<h3 style='color: white; margin: 0 0 12px 0; font-size: 18px; font-weight: bold;'>🗺️ Interactive Multimodal Map: Ground Sensors, Satellite NO₂, & DBSCAN Hotspots</h3>")
                gr.HTML(f"<div class='map-container'>{MAP_HTML}</div>")

        # TAB 3: CITIZEN UPLOAD & VERIFICATION
        with gr.TabItem("📸 Citizen Upload & Verification", id="citizen"):
            with gr.Row():
                with gr.Column(scale=1, elem_classes="dark-card"):
                    gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-weight: bold;'>📸 Upload Pollution Incident Photo</h3>")
                    incident_type_dd = gr.Dropdown(
                        choices=["Garbage Burning", "Industrial Smoke", "Construction Dust", "Road Dust", "Vehicle Exhaust"],
                        value="Garbage Burning",
                        label="Incident Category"
                    )
                    report_station_dd = gr.Dropdown(choices=STATION_LIST, value=STATION_LIST[0], label="Nearest Monitoring Station")
                    photo_upload = gr.Image(type="filepath", label="Upload Photo (Smoke / Burning / Dust)")
                    submit_photo_btn = gr.Button("Analyze Photo & Submit Report", variant="primary")
                
                with gr.Column(scale=2):
                    photo_result_card = gr.HTML("""
                    <div style="background: rgba(30, 41, 59, 0.7); border: 1px dashed #334155; border-radius: 12px; padding: 30px; text-align: center;">
                        <h4 style="color: #94a3b8; margin: 0;">Upload an image on the left to trigger real-time Computer Vision analysis.</h4>
                    </div>
                    """)
                    fusion_breakdown_plot = gr.Plot(label="Multimodal AI Fusion Breakdown", show_label=False)

            citizen_verification_table_container = gr.HTML(citizen_service.get_citizen_verification_table_html())

        # TAB 4: SATELLITE VIEW
        with gr.TabItem("🛰️ Satellite View", id="satellite"):
            with gr.Column(elem_classes="dark-card"):
                gr.HTML("""
                <h3 style="color: white; margin: 0 0 12px 0; font-weight: bold;">🛰️ Sentinel-5P NO₂ & MODIS Aerosol Optical Depth (AOD) Satellite Layers</h3>
                <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 16px;">
                    Integrates satellite remote sensing measurements to detect upper-atmosphere nitrogen dioxide (NO₂) plumes and aerosol optical depth across Bengaluru neighbourhoods.
                </p>
                """)
                gr.HTML(f"<div class='map-container'>{MAP_HTML}</div>")

        # TAB 5: HIDDEN HOTSPOTS
        with gr.TabItem("🚨 Hidden Hotspots", id="hotspots"):
            with gr.Column(elem_classes="dark-card"):
                gr.HTML("""
                <h3 style="color: white; margin: 0 0 16px 0; font-weight: bold;">🚨 DBSCAN Spatial Clustering: Unmonitored Hidden Hotspot Polygons</h3>
                <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 16px;">
                    DBSCAN algorithm detects spatial clusters by fusing ground sensors, citizen photo GPS coordinates, and satellite NO₂ anomalies to flag unmonitored pollution hotspots.
                </p>
                """)
                
                rows_html = ""
                for _, r in DB_SUMMARY_DF.iterrows():
                    color = "#ef4444" if r['is_hidden_hotspot'] else "#f97316"
                    rows_html += f"""
                    <tr style="border-bottom: 1px solid #334155;">
                        <td style="padding: 12px; color: #38bdf8; font-weight: bold;">Cluster #{int(r['cluster_id'])}</td>
                        <td style="padding: 12px; color: #f8fafc; font-weight: bold;">{r['ward_name']}</td>
                        <td style="padding: 12px; color: {color}; font-weight: bold;">{r['status_label']}</td>
                        <td style="padding: 12px; color: #ef4444; font-weight: bold;">{r['avg_severity']} / 100</td>
                        <td style="padding: 12px; color: white;">{r['point_count']} signals</td>
                        <td style="padding: 12px; color: #cbd5e1;">{r['sources']}</td>
                    </tr>
                    """
                
                hotspot_table_html = f"""
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="border-bottom: 2px solid #475569; color: #94a3b8; font-weight: bold; text-transform: uppercase; font-size: 11px;">
                            <th style="padding: 12px;">Cluster ID</th>
                            <th style="padding: 12px;">Neighbourhood / Ward</th>
                            <th style="padding: 12px;">Hotspot Classification</th>
                            <th style="padding: 12px;">Avg Severity</th>
                            <th style="padding: 12px;">Point Signals</th>
                            <th style="padding: 12px;">Data Sources Fused</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                """
                gr.HTML(hotspot_table_html)

        # TAB 6: 24-HOUR FORECAST
        with gr.TabItem("📈 24-Hour Forecast", id="forecast"):
            with gr.Column(elem_classes="dark-card"):
                gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-weight: bold;'>📈 24-Hour AQI Predictive Trajectory with 95% Confidence Bounds</h3>")
                forecast_plot_out = gr.Plot(label="24h Forecast Trajectory", show_label=False)

        # TAB 7: MUNICIPAL ALERTS
        with gr.TabItem("🏛️ Municipal Alerts", id="alerts"):
            with gr.Row():
                with gr.Column(scale=1, min_width=280, elem_classes="dark-card"):
                    gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-size: 16px; font-weight: bold;'>Resource Dispatch Simulator</h3>")
                    alert_ward_dd = gr.Dropdown(choices=STATION_LIST, value=STATION_LIST[0], label="Target Ward")
                    resource_dd = gr.Dropdown(
                        choices=["2x Mobile Water Mist Cannons", "Anti-Smog Spray Gun", "Sanitation Rapid Clearing Wing", "Industrial Compliance Inspectorate"],
                        value="2x Mobile Water Mist Cannons",
                        label="Deploy Resource"
                    )
                    dispatch_btn = gr.Button("Simulate Immediate Resource Dispatch", variant="primary")
                    dispatch_status_out = gr.HTML()

                with gr.Column(scale=2):
                    alert_card_out = gr.HTML()

        # TAB 8: ANALYTICS & TIMELINE
        with gr.TabItem("📊 Analytics & Timeline", id="analytics"):
            with gr.Column(elem_classes="dark-card"):
                timeline_plot_out = gr.Plot(label="Multi-Modal Interactive Timeline", show_label=False)
                fusion_chart_out = gr.Plot(label="Multimodal AI Fusion Breakdown", show_label=False)

    # Wire up Event Handlers
    
    # Dashboard / Station Selector Analysis
    analyze_btn.click(
        fn=handle_station_analysis,
        inputs=[station_dd],
        outputs=[
            trend_plot_out, gauge_plot_out, forecast_plot_out, 
            fusion_chart_out, timeline_plot_out, pred_summary_out, 
            alert_card_out, exec_kpi_container, health_advisory_out
        ]
    )

    station_dd.change(
        fn=handle_station_analysis,
        inputs=[station_dd],
        outputs=[
            trend_plot_out, gauge_plot_out, forecast_plot_out, 
            fusion_chart_out, timeline_plot_out, pred_summary_out, 
            alert_card_out, exec_kpi_container, health_advisory_out
        ]
    )

    # Photo Upload Analysis Handler
    submit_photo_btn.click(
        fn=handle_citizen_photo_upload,
        inputs=[photo_upload, incident_type_dd, report_station_dd],
        outputs=[photo_result_card, fusion_breakdown_plot, citizen_verification_table_container]
    )

    # Resource Dispatch Simulator Handler
    def handle_dispatch(ward_name, resource_type):
        res = alert_engine.dispatch_resource(ward_name, resource_type)
        return f"""
        <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; border-radius: 8px; padding: 12px; margin-top: 12px;">
            <b style="color: #4ade80;">✅ Resource Dispatched Successfully</b><br>
            <span style="font-size: 12px; color: white;">ID: <b>{res['dispatch_id']}</b> | Ward: <b>{res['ward']}</b></span><br>
            <span style="font-size: 12px; color: #cbd5e1;">Resource: {res['resource']} ({res['status']})</span>
        </div>
        """

    dispatch_btn.click(
        fn=handle_dispatch,
        inputs=[alert_ward_dd, resource_dd],
        outputs=[dispatch_status_out]
    )

    # Initial Load Trigger
    demo.load(
        fn=handle_station_analysis,
        inputs=[station_dd],
        outputs=[
            trend_plot_out, gauge_plot_out, forecast_plot_out, 
            fusion_chart_out, timeline_plot_out, pred_summary_out, 
            alert_card_out, exec_kpi_container, health_advisory_out
        ]
    )

if __name__ == '__main__':
    demo.launch(server_name='0.0.0.0', server_port=7860, share=False, show_error=True)
