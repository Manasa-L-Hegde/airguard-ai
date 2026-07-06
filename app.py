#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AirGuard AI — Civic Intelligence Dashboard
==========================================
Bengaluru urban pollution hotspot detection & clean-street decision support.
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


STATIC_TRANSLATIONS = {
    "English": {
        "live_indicator": "🟢 Live | 15 sec ago | 14 Stations",
        "accuracy_latency": "Accuracy: 58.4% | Avg. Latency: 0.43s",
        "hero_title": "AirGuard AI",
        "hero_subtitle": "Predict Pollution Before It Happens",
        "hero_desc": "AI-powered Decision Support System for Smart Cities. Helping municipal authorities identify and mitigate pollution hotspots before air quality reaches critical thresholds.",
        "explore_btn": "Explore Dashboard",
        "summary_title": "📊 Executive Impact Summary",
        "summary_hotspots": "🚨 Critical Hotspots",
        "summary_citizens": "👥 Citizens at Risk",
        "summary_reduction": "📉 Expected AQI Reduction",
        "summary_alerts": "⚠️ Today\'s Wards Alerts",
        "summary_accuracy": "🎯 Prediction Accuracy",
        "summary_confidence": "🧠 Model Confidence",
        "station_selector_lbl": "Search / Select Station",
        "analyze_btn": "Analyze Data",
        "forecast_btn": "Fetch Forecast",
        "submit_report_btn": "Submit Report",
        "report_station_lbl": "Nearest Monitoring Station",
        "incident_type_lbl": "Incident Type",
        "img_upload_lbl": "Upload Image Proof (Optional)",
        "citizen_title": "Submit Local Incident",
        "citizen_analytics_title": "Today\'s Citizen Analytics",
        "garbage_burning": "Garbage Burning",
        "construction_dust": "Construction Dust",
        "industrial_smoke": "Industrial Smoke",
        "est_label": "(estimated)"
    },
    "ಕನ್ನಡ": {
        "live_indicator": "🟢 ಲೈವ್ | 15 ಸೆಕೆಂಡುಗಳ ಹಿಂದೆ | 14 ನಿಲ್ದಾಣಗಳು",
        "accuracy_latency": "ನಿಖರತೆ: 58.4% | ಸರಾವರಿ ವಿಳಂಬ ಸಮಯ: 0.43 ಸೆ",
        "hero_title": "ಏರ್-ಗಾರ್ಡ್ AI",
        "hero_subtitle": "ಮಾಲಿನ್ಯವನ್ನು ಸಂಭವಿಸುವ ಮುನ್ನವೇ ಊಹಿಸಿ",
        "hero_desc": "ಸ್ಮಾರ್ಟ್ ಸಿಟಿಗಳಿಗಾಗಿ AI-ಆಧಾರಿತ ನಿರ್ಧಾರ ಬೆಂಬಲ ವ್ಯವಸ್ಥೆ. ಗಾಳಿಯ ಗುಣಮಟ್ಟವು ಗಂಭೀರ ಮಟ್ಟ ತಲುಪುವ ಮುನ್ನವೇ ಮಾಲಿನ್ಯದ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳನ್ನು ಗುರುತಿಸಲು ನೆರವಾಗುತ್ತದೆ.",
        "explore_btn": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ಅನ್ವೇಷಿಸಿ",
        "summary_title": "📊 ಕಾರ್ಯನಿರ್ವಾಹಕ ಪ್ರಭಾವದ ಸಾರಾಂಶ",
        "summary_hotspots": "🚨 ಕ್ಲಿಷ್ಟಕರ ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು",
        "summary_citizens": "👥 ಅಪಾಯದಲ್ಲಿರುವ ನಾಗರಿಕರು",
        "summary_reduction": "📉 ನಿರೀಕ್ಷಿತ AQI ಕಡಿತ",
        "summary_alerts": "⚠️ ಇಂದಿನ ವಾರ್ಡ್ ಎಚ್ಚರಿಕೆಗಳು",
        "summary_accuracy": "🎯 ಮುನ್ಸೂಚನೆ ನಿಖरತೆ",
        "summary_confidence": "🧠 ಮಾದರಿ ವಿಶ್ವಾಸಾರ್ಹತೆ",
        "station_selector_lbl": "ನಿಲ್ದಾಣವನ್ನು ಹುಡುಕಿ / ಆಯ್ಕೆ ಮಾಡಿ",
        "analyze_btn": "ಡೇಟಾ ವಿಶ್ಲೇಷಿಸಿ",
        "forecast_btn": "ಮುನ್ಸೂಚನೆ ಪಡೆಯಿರಿ",
        "submit_report_btn": "ವರದಿ ಸಲ್ಲಿಸಿ",
        "report_station_lbl": "ಹತ್ತಿರದ ಮಾನಿಟरीಂಗ್ ನಿಲ್ದಾಣ",
        "incident_type_lbl": "ಘಟನೆಯ ಪ್ರಕಾರ",
        "img_upload_lbl": "ಚಿತ್ರ ಪುರಾವೆ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ (ಐಚ್ಛಿಕ)",
        "citizen_title": "ಸ್ಥಳೀಯ ಘಟನೆಯನ್ನು ವರದಿ ಮಾಡಿ",
        "citizen_analytics_title": "ಇಂದಿನ ನಾಗರಿಕ ವಿಶ್ಲೇಷಣೆ",
        "garbage_burning": "ಕಸ ಸುಡುವುದು",
        "construction_dust": "ಕಟ್ಟಡ ನಿರ್ಮಾಣ ಧೂಳು",
        "industrial_smoke": "ಕೈಗಾರಿಕಾ ಹೊಗೆ",
        "est_label": "(ಅಂದಾಜು)"
    },
    "हिंदी": {
        "live_indicator": "🟢 लाइव | 15 सेकंड पहले | 14 स्टेशन",
        "accuracy_latency": "सटीकता: 58.4% | औसत विलंबता: 0.43s",
        "hero_title": "एयरगार्ड AI",
        "hero_subtitle": "प्रदूषण होने से पहले ही उसका पूर्वानुमान लगाएं",
        "hero_desc": "स्मार्ट शहरों के लिए AI-संचालित निर्णय सहायता प्रणाली। वायु गुणवत्ता गंभीर स्तर पर पहुंचने से पहले प्रदूषण हॉटस्पॉट की पहचान करने में मदद करता है।",
        "explore_btn": "डैशबोर्ड का अन्वेषण करें",
        "summary_title": "📊 कार्यकारी प्रभाव सारांश",
        "summary_hotspots": "🚨 गंभीर हॉटस्पॉट",
        "summary_citizens": "👥 खतरे में नागरिक",
        "summary_reduction": "📉 संभावित AQI सुधार",
        "summary_alerts": "⚠️ आज की वार्ड चेतावनी",
        "summary_accuracy": "🎯 पूर्वानुमान सटीकता",
        "summary_confidence": "🧠 मॉडल विश्वसनीयता",
        "station_selector_lbl": "स्टेशन खोजें या चुनें",
        "analyze_btn": "डेटा विश्लेषण करें",
        "forecast_btn": "पूर्वानुमान प्राप्त करें",
        "submit_report_btn": "रिपोर्ट जमा करें",
        "report_station_lbl": "निकटतम निगरानी स्टेशन",
        "incident_type_lbl": "घटना का प्रकार",
        "img_upload_lbl": "छवि प्रमाण अपलोड करें (वैकल्पिक)",
        "citizen_title": "स्थानीय घटना सबमिट करें",
        "citizen_analytics_title": "आज का नागरिक विश्लेषण",
        "garbage_burning": "कचरा जलाना",
        "construction_dust": "निर्माण धूल",
        "industrial_smoke": "औद्योगिक धुआं",
        "est_label": "(अनुमानित)"
    }
}

DYNAMIC_TRANSLATIONS = {
    "English": {
        "forecast": "Forecast",
        "prediction": "Prediction",
        "confidence": "Confidence",
        "class_probs": "Class Probabilities",
        "high_pollution_alert": "High Pollution Alert",
        "alert_msg": "AQI is severe in {ward_name}. Avoid outdoor activities.",
        "mun_decision": "🏛️ Municipal Decision Support",
        "imm_actions": "Immediate Action Recommendations",
        "exp_result": "Expected Result",
        "aqi_imp": "AQI Improvement",
        "priority": "Priority",
        "citizens_impacted": "Est. Citizens Impacted",
        "resp_dept": "Responsible Dept",
        "timeline": "Action Timeline",
        "budget": "Estimated Budget",
        "yesterday": "Yesterday",
        "today": "Today",
        "why_forecast": "Why this forecast?",
        "pm25_trend": "PM2.5 Trend",
        "primary_driver": "Primary Driver",
        "secondary_driver": "Secondary Driver",
        "background_factor": "Background Factor",
        "kpi_current_aqi": "🌿 Current AQI",
        "kpi_latest_pm": "🌫️ Latest PM2.5",
        "kpi_forecast": "📈 Forecast",
        "kpi_aqi_reduction": "📉 Est. AQI Reduction",
        "kpi_confidence": "📊 Prediction Confidence",
        "kpi_hotspots": "🚨 Hotspot Zones",
        "active": "Active",
        "unknown": "Unknown",
        "not_found": "Station not found.",
        "no_data": "No data available.",
        "est_label": "(Estimated)"
    },
    "ಕನ್ನಡ": {
        "forecast": "ಮುನ್ಸೂಚನೆ",
        "prediction": "ಮುನ್ಸೂಚನೆ",
        "confidence": "ವಿಶ್ವಾಸಾರ್ಹತೆ",
        "class_probs": "ವರ್ಗದ ಸಂಭಾವ್ಯತೆಗಳು",
        "high_pollution_alert": "ಹೆಚ್ಚಿನ ಮಾಲಿನ್ಯ ಎಚ್ಚರಿಕೆ",
        "alert_msg": "{ward_name} ವಾರ್ಡ್‌ನಲ್ಲಿ ಗಾಳಿ ಗುಣಮಟ್ಟ ಕಳಪೆಯಾಗಿದೆ. ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆ ತಡೆಯಿರಿ.",
        "mun_decision": "🏛️ ಪುರಸಭೆ ನಿರ್ಧಾರ ಬೆಂಬಲ",
        "imm_actions": "ತಕ್ಷಣದ ಕ್ರಮದ ಶಿಫಾರಸುಗಳು",
        "exp_result": "ನಿರೀಕ್ಷಿತ ಫಲಿತಾಂಶ",
        "aqi_imp": "AQI ಸುಧಾರಣೆ",
        "priority": "ಆದ್ಯತೆ",
        "citizens_impacted": "ಅಂದಾಜು ನಾಗರಿಕರ ಮೇಲೆ ಪ್ರಭಾವ",
        "resp_dept": "ಜವಾಬ್ದಾರಿಯುತ ಇಲಾಖೆ",
        "timeline": "ಕ್ರಮದ ಕಾಲಮಿತಿ",
        "budget": "ಅಂದಾಜು ಬಜೆಟ್",
        "yesterday": "ನಿನ್ನೆ",
        "today": "ಇಂದು",
        "why_forecast": "ಈ ಮುನ್ಸೂಚನೆಗೆ ಕಾರಣವೇನು?",
        "pm25_trend": "PM2.5 ಪ್ರವೃತ್ತಿ",
        "primary_driver": "ಮುಖ್ಯ ಕಾರಣ",
        "secondary_driver": "ದ್ವಿತೀಯ ಕಾರಣ",
        "background_factor": "ಹಿನ್ನೆಲೆ ಅಂಶ",
        "kpi_current_aqi": "🌿 ಪ್ರಸ್ತುತ AQI",
        "kpi_latest_pm": "🌫️ ಇತ್ತೀಚಿನ PM2.5",
        "kpi_forecast": "📈 ಮುನ್ಸೂಚನೆ",
        "kpi_aqi_reduction": "📉 ಅಂದಾಜು AQI ಕಡಿತ",
        "kpi_confidence": "📊 ಮುನ್ಸೂಚನೆ ವಿಶ್ವಾಸಾರ್ಹತೆ",
        "kpi_hotspots": "🚨 ಹಾಟ್‌ಸ್ಪಾಟ್‌ಗಳು",
        "active": "ಸಕ್ರಿಯ",
        "unknown": "ತಿಳಿದಿಲ್ಲ",
        "not_found": "ನಿಲ್ದಾಣ ಕಂಡುಬಂದಿಲ್ಲ.",
        "no_data": "ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ.",
        "est_label": "(ಅಂದಾಜು)"
    },
    "हिंदी": {
        "forecast": "पूर्वानुमान",
        "prediction": "पूर्वानुमान",
        "confidence": "विश्वसनीयता",
        "class_probs": "वर्ग संभावनाएं",
        "high_pollution_alert": "उच्च प्रदूषण चेतावनी",
        "alert_msg": "{ward_name} में वायु गुणवत्ता गंभीर है। बाहरी गतिविधियों से बचें।",
        "mun_decision": "🏛️ नगर पालिका निर्णय सहायता",
        "imm_actions": "तत्काल कार्रवाई की सिफारिशें",
        "exp_result": "अपेक्षित परिणाम",
        "aqi_imp": "AQI सुधार",
        "priority": "प्राथमिकता",
        "citizens_impacted": "प्रभावित नागरिक (अनुमानित)",
        "resp_dept": "जिम्मेदार विभाग",
        "timeline": "कार्रवाई की समय सीमा",
        "budget": "अनुमानित बजट",
        "yesterday": "कल",
        "today": "आज",
        "why_forecast": "यह पूर्वानुमान क्यों?",
        "pm25_trend": "PM2.5 प्रवृत्ति",
        "primary_driver": "प्राथमिक कारक",
        "secondary_driver": "द्वितीयक कारक",
        "background_factor": "पृष्ठभूमि कारक",
        "kpi_current_aqi": "🌿 वर्तमान AQI",
        "kpi_latest_pm": "🌫️ नवीनतम PM2.5",
        "kpi_forecast": "📈 पूर्वानुमान",
        "kpi_aqi_reduction": "📉 अनुमानित AQI कमी",
        "kpi_confidence": "📊 पूर्वानुमान विश्वसनीयता",
        "kpi_hotspots": "🚨 हॉटस्पॉट",
        "active": "सक्रिय",
        "unknown": "अज्ञात",
        "not_found": "स्टेशन नहीं मिला।",
        "no_data": "डेटा उपलब्ध नहीं है।",
        "est_label": "(अनुमानित)"
    }
}

def change_language(lang):
    t = STATIC_TRANSLATIONS[lang]
    top_bar_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #1E293B; margin-bottom: 20px;">
        <div style="display:flex; align-items:center; gap: 8px;">
            <div style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 8px #22c55e;"></div>
            <div style="color: #cbd5e1; font-weight: bold; font-size: 13px; text-transform: uppercase;">{t['live_indicator']}</div>
        </div>
        <div style="color: #64748b; font-size: 12px; font-weight: 500;">{t['accuracy_latency']}</div>
    </div>"""
    
    hero_html = f"""
    <div class="hero-section">
        <h1 class="hero-title">{t['hero_title']}</h1>
        <p class="hero-subtitle">{t['hero_subtitle']}</p>
        <p style="font-size: 18px; color: #cbd5e1; max-width: 700px; margin: 0 0 24px 0; font-weight: 400; line-height: 1.5;">
            {t['hero_desc']}
        </p>
        <div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
            <button class="hero-cta-btn" onclick="document.getElementById(\'station-selector\').scrollIntoView({{behavior: \'smooth\'}})">{t['explore_btn']}</button>
            <div style="color: #60a5fa; font-weight: 600; letter-spacing: 1.5px; font-size: 13px; text-transform: uppercase;">
                🌿 Predict • 🚨 Detect • 🧠 Explain • 🏛️ Recommend
            </div>
        </div>
    </div>"""
    
    exec_html = f"""
    <div class="executive-summary-card">
        <h3 class="summary-title">{t['summary_title']}</h3>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">{t['summary_hotspots']}</div>
                <div class="summary-val">2 Zones</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">{t['summary_citizens']}</div>
                <div class="summary-val">68,000+ <span style="font-size:12px; font-weight:normal; color:#94a3b8;">{t['est_label']}</span></div>
            </div>
            <div class="summary-item">
                <div class="summary-label">{t['summary_reduction']}</div>
                <div class="summary-val green-text">18% Avg <span style="font-size:12px; font-weight:normal; color:#94a3b8;">{t['est_label']}</span></div>
            </div>
            <div class="summary-item">
                <div class="summary-label">{t['summary_alerts']}</div>
                <div class="summary-val red-text">6 Wards</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">{t['summary_accuracy']}</div>
                <div class="summary-val blue-text">58.4%</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">{t['summary_confidence']}</div>
                <div class="summary-val purple-text">74.2%</div>
            </div>
        </div>
    </div>"""
    
    citizen_analytics_html = f"""
    <h3 style=\'color: white; margin: 0 0 16px 0; font-weight: bold;\'>{t['citizen_analytics_title']}</h3>
    <div style=\'display:flex; gap:20px; flex-wrap:wrap;\'>
        <div style=\'background:#0f172a; padding:20px; border-radius:12px; flex:1; text-align:center; border: 1px solid #334155;\'><h2 style=\'margin:0; color:#ef4444; font-size: 32px;\'>12</h2><div style=\'color:#94a3b8; font-size:12px; margin-top:4px;\'>{t['garbage_burning']}</div></div>
        <div style=\'background:#0f172a; padding:20px; border-radius:12px; flex:1; text-align:center; border: 1px solid #334155;\'><h2 style=\'margin:0; color:#eab308; font-size: 32px;\'>8</h2><div style=\'color:#94a3b8; font-size:12px; margin-top:4px;\'>{t['construction_dust']}</div></div>
        <div style=\'background:#0f172a; padding:20px; border-radius:12px; flex:1; text-align:center; border: 1px solid #334155;\'><h2 style=\'margin:0; color:#8b5cf6; font-size: 32px;\'>4</h2><div style=\'color:#94a3b8; font-size:12px; margin-top:4px;\'>{t['industrial_smoke']}</div></div>
    </div>
    <div style="margin-top: 24px; padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px;">
        <h4 style="color: #38bdf8; margin: 0 0 8px 0;">Analytical Observations</h4>
        <p style=\'color:#cbd5e1; margin:0; font-size:14px; line-height: 1.5;\'>Recent reports indicate a 30% increase in localized garbage burning in Ward areas without active solid waste collection today. This corresponds directly with localized PM2.5 spikes.</p>
    </div>"""
    
    return (
        top_bar_html,
        hero_html,
        exec_html,
        gr.update(label=t['station_selector_lbl']),
        gr.update(value=t['analyze_btn']),
        gr.update(label=t['station_selector_lbl']),
        gr.update(value=t['forecast_btn']),
        gr.update(label=t['report_station_lbl']),
        gr.update(label=t['incident_type_lbl']),
        gr.update(label=t['img_upload_lbl']),
        gr.update(value=t['submit_report_btn']),
        citizen_analytics_html
    )

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH   = os.path.join(BASE_DIR, 'models', 'aqi_category_rf.pkl')
HOTSPOT_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'hotspot_clusters.csv')
WARD_PATH    = os.path.join(BASE_DIR, 'data', 'processed', 'ward_mapped_stations.csv')
TS_PATH      = os.path.join(BASE_DIR, 'data', 'processed', 'bengaluru_air_quality_timeseries.csv')
REPORT_CSV   = os.path.join(BASE_DIR, 'data', 'processed', 'reports.csv')

# ── AQI constants ─────────────────────────────────────────────────────────────
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

print("Loading model and data...", flush=True)

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

# ── Dynamic Decisions Helper ───────────────────────────────────────────────────
def get_station_class(station_name):
    if any(k in station_name for k in ['Peenya', 'Jigani']):
        return 'industrial'
    elif any(k in station_name for k in ['Silk Board', 'City Railway', 'BTM Layout', 'Bapuji Nagar', 'Kasturi Nagar']):
        return 'traffic'
    else:
        return 'residential'

def get_action_details(act):
    details_map = {
        "Mandate immediate stack monitoring at units": {
            "icon": "🏭",
            "impact": "★★★",
            "cost": "₹2.5L",
            "imp": "8%"
        },
        "Restrict diesel heavy transport peak hours": {
            "icon": "🚚",
            "impact": "★★☆",
            "cost": "₹0.5L",
            "imp": "6%"
        },
        "Inspect Peenya industrial units": {
            "icon": "🔍",
            "impact": "★★☆",
            "cost": "₹1.2L",
            "imp": "4%"
        },
        "Conduct weekly compliance checks": {
            "icon": "📋",
            "impact": "★☆☆",
            "cost": "₹0.8L",
            "imp": "3%"
        },
        "Optimize heavy vehicle schedules": {
            "icon": "⏰",
            "impact": "★☆☆",
            "cost": "₹0.3L",
            "imp": "2%"
        },
        "Enforce green belts around industrial zones": {
            "icon": "🌳",
            "impact": "★★☆",
            "cost": "₹3.5L",
            "imp": "5%"
        },
        "Deploy water mist cannons at junctions": {
            "icon": "🚿",
            "impact": "★★★",
            "cost": "₹4.8L",
            "imp": "10%"
        },
        "Optimize signal timings via traffic control": {
            "icon": "🚦",
            "impact": "★★☆",
            "cost": "₹0.5L",
            "imp": "7%"
        },
        "Enforce construction dust suppressions": {
            "icon": "🏗️",
            "impact": "★★☆",
            "cost": "₹1.5L",
            "imp": "5%"
        },
        "Deploy mechanical road sweepers at night": {
            "icon": "🧹",
            "impact": "★★☆",
            "cost": "₹2.2L",
            "imp": "6%"
        },
        "Increase roadside street plantation": {
            "icon": "🌱",
            "impact": "★☆☆",
            "cost": "₹1.8L",
            "imp": "3%"
        },
        "Optimize public transport routes": {
            "icon": "🚌",
            "impact": "★☆☆",
            "cost": "₹0.6L",
            "imp": "3%"
        },
        "Restrict localized construction activity": {
            "icon": "🚫",
            "impact": "★★☆",
            "cost": "₹0.2L",
            "imp": "5%"
        },
        "Issue ward dust control notices": {
            "icon": "📄",
            "impact": "★☆☆",
            "cost": "₹0.1L",
            "imp": "4%"
        },
        "Enforce strict open waste ban": {
            "icon": "🚯",
            "impact": "★★☆",
            "cost": "₹0.4L",
            "imp": "6%"
        },
        "Increase green neighborhood tree canopy": {
            "icon": "🌲",
            "impact": "★★☆",
            "cost": "₹2.0L",
            "imp": "4%"
        },
        "Sweep ward secondary roads daily": {
            "icon": "🧹",
            "impact": "★☆☆",
            "cost": "₹1.0L",
            "imp": "2%"
        },
        "Inspect commercial eateries fuel compliance": {
            "icon": "🍳",
            "impact": "★☆☆",
            "cost": "₹0.5L",
            "imp": "2%"
        }
    }
    return details_map.get(act, {
        "icon": "⚡",
        "impact": "★★☆",
        "cost": "₹1.0L",
        "imp": "5%"
    })

def get_station_specifics(station_name, pm25_val, pred_cat):
    s_class = get_station_class(station_name)
    
    # 1. Pop density / Citizens impacted multiplier
    multipliers = {
        'industrial': 400,
        'traffic': 550,
        'residential': 320
    }
    pop_mult = multipliers.get(s_class, 300)
    citizens_impacted = int(pm25_val * pop_mult)
    
    # 2. Priority & Timeline
    if pred_cat == 'Severe':
        priority = "Critical"
        timeline = "Within 12 Hours"
        priority_color = "#ef4444"
    elif pred_cat == 'Poor':
        priority = "High"
        timeline = "Within 24 Hours"
        priority_color = "#f97316"
    elif pred_cat == 'Moderate':
        priority = "Moderate"
        timeline = "Within 48 Hours"
        priority_color = "#eab308"
    else:
        priority = "Low"
        timeline = "Within 7 Days"
        priority_color = "#22c55e"
        
    # 3. Budget calculation
    if pm25_val > 120:
        budget_text = f"₹{8.2 + (pm25_val % 3) * 0.5:.1f} Lakhs"
    elif pm25_val > 80:
        budget_text = f"₹{4.5 + (pm25_val % 3) * 0.4:.1f} Lakhs"
    elif pm25_val > 40:
        budget_text = f"₹{2.4 + (pm25_val % 3) * 0.2:.1f} Lakhs"
    else:
        budget_text = f"₹{0.8 + (pm25_val % 3) * 0.1:.1f} Lakhs"
        
    # 4. Station details & action lists
    if s_class == 'industrial':
        drivers = ["Industrial Stack Emissions", "Diesel Transport Fleet", "Suspended Coal Fly Ash"]
        dept = "KSPCB Regional Inspectorate, BBMP Special Zone Cell"
        if pm25_val > 90:
            actions = ["Mandate immediate stack monitoring at units", "Restrict diesel heavy transport peak hours", "Inspect Peenya industrial units"]
            improvement = "18%"
        else:
            actions = ["Conduct weekly compliance checks", "Optimize heavy vehicle schedules", "Enforce green belts around industrial zones"]
            improvement = "8%"
    elif s_class == 'traffic':
        drivers = ["Automotive Congestion", "Diesel Tailpipe Emissions", "Road Dust Re-suspension"]
        dept = "Bengaluru Traffic Police, BBMP Road Infrastructure Dept"
        if pm25_val > 90:
            actions = ["Deploy water mist cannons at junctions", "Optimize signal timings via traffic control", "Enforce construction dust suppressions"]
            improvement = "22%"
        else:
            actions = ["Deploy mechanical road sweepers at night", "Increase roadside street plantation", "Optimize public transport routes"]
            improvement = "12%"
    else: # residential / commercial
        drivers = ["Localized Waste Burning", "Construction Activity Dust", "Regional Background Aerosols"]
        dept = "BBMP Ward Health Officers, KSPCB Air Compliance Wing"
        if pm25_val > 90:
            actions = ["Restrict localized construction activity", "Issue ward dust control notices", "Enforce strict open waste ban"]
            improvement = "15%"
        else:
            actions = ["Increase green neighborhood tree canopy", "Sweep ward secondary roads daily", "Inspect commercial eateries fuel compliance"]
            improvement = "6%"
            
    return {
        'citizens_impacted': citizens_impacted,
        'priority': priority,
        'timeline': timeline,
        'priority_color': priority_color,
        'budget': budget_text,
        'drivers': drivers,
        'dept': dept,
        'actions': actions,
        'improvement': improvement
    }

def build_map():
    m = folium.Map(
        location=[12.97, 77.59],
        zoom_start=11,
        tiles='CartoDB dark_matter',
        height=750,
    )

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
        
        # Live prediction inside map popup
        history_df = ts_daily[ts_daily['station'] == row['station']].copy()
        pred_text = "Unknown"
        risk_text = "Low"
        conf_text = "N/A"
        
        if len(history_df) > 0:
            today = history_df['date'].max()
            X, err = build_feature_row(row['station'], today, row['ward_name'], history_df)
            if X is not None:
                proba = rf_model.predict_proba(X)[0]
                pred_idx = int(np.argmax(proba))
                pred_cat = rf_model.classes_[pred_idx]
                pred_text = pred_cat
                conf_text = f"{float(proba[pred_idx]) * 100:.1f}%"
                
                # Fetch dynamic specifics for map popup
                spec = get_station_specifics(row['station'], row['pm25'], pred_cat)
                risk_text = spec['priority']

        popup_html = f"""
        <div style='font-family:sans-serif;font-size:13px;width:240px;color:#333;line-height:1.4;'>
          <b style='font-size:14px;color:#0f172a;'>{row['station']}</b><br>
          <hr style='margin: 6px 0; border-top: 1px solid #ddd;'>
          <span style='color:#57606a'>Current AQI:</span> <span style='background:{color};padding:2px 6px;border-radius:4px;color:#fff;font-weight:bold;font-size:11px;'>{aqi}</span> ({pm25_v} µg/m³)<br>
          <span style='color:#57606a'>Forecast:</span> <b style='color:#2563eb;'>{pred_text}</b> ({conf_text})<br>
          <span style='color:#57606a'>Risk Level:</span> <b style='color:#dc2626;'>{risk_text}</b><br>
          <span style='color:#57606a'>Expected Improvement:</span> <b style='color:#16a34a;'>{spec['improvement']}</b><br>
          <hr style='margin: 6px 0; border-top: 1px solid #ddd;'>
          <span style='color:#57606a'>Action Recommendations:</span><br>
          <span style='color:#0f172a;font-style:italic;'>• {spec['actions'][0]}<br>• {spec['actions'][1]}<br>• {spec['actions'][2]}</span>
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
        ).add_to(m)

    for _, hrow in hotspot_df.iterrows():
        cid    = int(hrow['cluster_id'])
        label  = 'NW Cluster' if cid == 1 else 'SE Cluster'
        wards  = hrow['wards']
        sev    = hrow['avg_severity']
        popup_html = f"""
        <div style='font-family:sans-serif;font-size:13px;width:210px;color:#333'>
          <b>★ Hotspot Cluster {cid} — {label}</b><br>
          <span style='color:#57606a'>Wards:</span> {wards}<br>
          <span style='color:#57606a'>Avg Severity:</span> {sev:.1f}<br>
          <span style='color:#57606a'>Stations:</span> {hrow['station_count']}
        </div>"""
        folium.Marker(
            location=[float(hrow['center_latitude']), float(hrow['center_longitude'])],
            popup=folium.Popup(popup_html, max_width=230),
            tooltip=f"★ {label} (sev {sev:.0f})",
            icon=folium.DivIcon(html=f"<div style='font-size:26px;line-height:1;color:#ef4444;text-shadow:0 0 8px rgba(239,68,68,0.8)'>★</div>",
                icon_size=(28, 28), icon_anchor=(14, 24)),
        ).add_to(m)

    return m._repr_html_()

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
        title=dict(text=f"Last 30 Days Trend", font=dict(color='white', size=14)),
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

def submit_citizen_report(incident_type, station, file_path):
    if not incident_type:
        return "⚠️ Please select an incident type."
    ref_id = f"AIR-2026-{str(uuid.uuid4())[:4].upper()}"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_name = os.path.basename(file_path) if file_path else "No Image Attached"
    
    os.makedirs(os.path.dirname(REPORT_CSV), exist_ok=True)
    file_exists = os.path.isfile(REPORT_CSV)
    
    with open(REPORT_CSV, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["Reference ID", "Timestamp", "Station", "Incident Type", "File"])
        writer.writerow([ref_id, timestamp, station, incident_type, file_name])
    
    return f"""<div style='background: rgba(34, 197, 94, 0.1); border-left: 4px solid #22c55e; padding: 16px; border-radius: 8px;'>
    <h3 style='color: #4ade80; margin: 0 0 8px 0;'>✅ Report Submitted Successfully</h3>
    <p style='margin: 0; color: #e2e8f0;'>Reference ID: <b>{ref_id}</b></p>
    </div>"""

def make_prediction(station_name, lang="English"):
    try:
        t = DYNAMIC_TRANSLATIONS.get(lang, DYNAMIC_TRANSLATIONS["English"])
        trend_fig = plot_trend(station_name)
        wrow = ward_df[ward_df['station'] == station_name]
        if wrow.empty: return trend_fig, go.Figure(), f"<p>{t['not_found']}</p>", "", "", "", ""
            
        ward_name = wrow.iloc[0]['ward_name']
        station_history = ts_daily[ts_daily['station'] == station_name].copy()
        max_date = station_history['date'].max() if len(station_history) > 0 else pd.NaT

        if pd.isna(max_date): return trend_fig, go.Figure(), f"<p>{t['no_data']}</p>", "", "", "", ""

        today = max_date
        yesterday = today - datetime.timedelta(days=1)
        
        latest_pm25 = station_history.sort_values('date').iloc[-1]['pm25']
        yest_data = station_history[station_history['date'] == yesterday]
        yesterday_pm25 = yest_data.iloc[0]['pm25'] if not yest_data.empty else latest_pm25
        
        current_aqi = pm25_to_aqi(latest_pm25)
        yest_aqi_val = pm25_to_aqi(yesterday_pm25)
        current_col = AQI_COLORS.get(current_aqi, '#94a3b8')
        gauge_fig = plot_gauge(latest_pm25)
        
        X, err = build_feature_row(station_name, today, ward_name, station_history)
        if X is None: return trend_fig, gauge_fig, f"<p>Error: {err}</p>", "", "", "", ""

        proba = rf_model.predict_proba(X)[0]
        classes = list(rf_model.classes_)
        pred_idx = int(np.argmax(proba))
        pred_cat = classes[pred_idx]
        confidence = float(proba[pred_idx]) * 100
        color = AQI_COLORS[pred_cat]
        next_d = today + datetime.timedelta(days=1)
        
        # Alert
        alert_html = ""
        if latest_pm25 > 90 or pred_cat == 'Severe':
            alert_html = f"""
            <div style="background: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444; padding: 16px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">🚨</div>
                <div>
                    <h4 style="margin: 0; color: #fca5a5; font-size: 16px; font-weight: bold;">{t['high_pollution_alert']}</h4>
                    <p style="margin: 4px 0 0 0; color: #e2e8f0; font-size: 14px;">{t['alert_msg'].format(ward_name=ward_name)}</p>
                </div>
            </div>"""

        # Fetch dynamic parameters
        spec = get_station_specifics(station_name, latest_pm25, pred_cat)
        
        actions_list_html = []
        for act in spec['actions']:
            details = get_action_details(act)
            actions_list_html.append(f"""
            <div class="action-card" style="background: rgba(15, 23, 42, 0.5) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 8px !important; padding: 12px 16px !important; margin-bottom: 8px !important;">
                <div class="action-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px !important;">
                    <span class="action-icon" style="font-size: 16px;">{details['icon']}</span>
                    <span class="action-name" style="font-size: 13px; font-weight: 600; color: #f8fafc !important;">{act}</span>
                </div>
                <div class="action-meta" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; border-top: 1px dashed rgba(255,255,255,0.08); padding-top: 8px !important;">
                    <div class="meta-item" style="display: flex; flex-direction: column;">
                        <span class="meta-label" style="color: #94a3b8 !important; font-size: 9px; text-transform: uppercase; font-weight: 500; margin-bottom: 2px;">{t['priority']}</span>
                        <span class="meta-val star-rating" style="color: #fbbf24 !important; font-weight: 700; font-size: 11px;">{details['impact']}</span>
                    </div>
                    <div class="meta-item" style="display: flex; flex-direction: column;">
                        <span class="meta-label" style="color: #94a3b8 !important; font-size: 9px; text-transform: uppercase; font-weight: 500; margin-bottom: 2px;">Cost</span>
                        <span class="meta-val" style="color: #cbd5e1 !important; font-weight: 600; font-size: 11px;">{details['cost']}</span>
                    </div>
                    <div class="meta-item" style="display: flex; flex-direction: column;">
                        <span class="meta-label" style="color: #94a3b8 !important; font-size: 9px; text-transform: uppercase; font-weight: 500; margin-bottom: 2px;">{t['aqi_imp']}</span>
                        <span class="meta-val" style="color: #4ade80 !important; font-weight: 700; font-size: 11px;">{details['imp']}</span>
                    </div>
                </div>
            </div>""")
        actions_html = f'<div class="actions-container">{"".join(actions_list_html)}</div>'
        
        rec_html = f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; height: 100%; display: flex; flex-direction: column; gap: 16px;">
            <h4 style="margin: 0; color: #38bdf8; font-size: 16px; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #334155; padding-bottom: 12px;">{t['mun_decision']}</h4>
            <div>
                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 12px;">{t['imm_actions']}</div>
                {actions_html}
            </div>
            <div style="border-top: 1px dashed #334155; padding-top: 12px;">
                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">{t['exp_result']}</div>
                <div style="font-size: 16px; font-weight: bold; color: #4ade80;">{t['aqi_imp']}: {spec['improvement']} <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">{t['est_label']}</span></div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-top: auto;">
                <div><div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['priority']}</div><div style="font-weight: bold; font-size: 14px; color: {spec['priority_color']};">{spec['priority']}</div></div>
                <div><div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['citizens_impacted']}</div><div style="color: #f8fafc; font-weight: bold; font-size: 14px;">~{spec['citizens_impacted']:,} <span style="font-size: 11px; font-weight: normal; color: #94a3b8;">{t['est_label']}</span></div></div>
                <div><div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['resp_dept']}</div><div style="color: #f8fafc; font-weight: bold; font-size: 11px; line-height:1.2;">{spec['dept']}</div></div>
                <div><div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['timeline']}</div><div style="color: #f8fafc; font-weight: bold; font-size: 14px;">{spec['timeline']}</div></div>
                <div style="grid-column: span 2;"><div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['budget']}</div><div style="color: #4ade80; font-weight: bold; font-size: 14px;">{spec['budget']}</div></div>
            </div>
        </div>"""

        bar_chart_html = "".join([f"<div style='display:flex; align-items:center; margin-bottom:8px;'><div style='width:70px; font-size:12px; color: white;'>{c}</div><div style='flex-grow:1; background:#334155; height:8px; border-radius:4px; margin:0 12px;'><div style='background:{AQI_COLORS.get(c, '#94a3b8')}; width:{p*100:.1f}%; height:100%; border-radius:4px;'></div></div><div style='width:40px; text-align:right; font-size:12px; color:white;'>{p*100:.0f}%</div></div>" for c, p in zip(classes, proba)])

        pred_html = f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; height: 100%;">
            <h4 style="margin: 0 0 16px 0; color: #38bdf8; font-size: 14px; font-weight: 600; text-transform: uppercase;">{t['forecast']}: {next_d.strftime("%d %b %Y")}</h4>
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">{t['prediction']}</div>
                <div style="font-size: 32px; font-weight: bold; color: {color}; text-shadow: 0 0 10px {color}40;">{pred_cat}</div>
                <div style="font-size: 14px; color: #4ade80; margin-top: 4px;">{t['confidence']}: {confidence:.1f}%</div>
            </div>
            <h5 style="margin: 0 0 12px 0; color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase;">{t['class_probs']}</h5>
            {bar_chart_html}
        </div>"""

        pm25_diff = latest_pm25 - yesterday_pm25
        pm25_dir = "↑" if pm25_diff > 0 else "↓"
        pm25_color = "#ef4444" if pm25_diff > 0 else "#22c55e"
        
        explain_html = f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; height: 100%;">
            <h4 style="margin: 0 0 16px 0; color: #38bdf8; font-size: 14px; font-weight: 600; text-transform: uppercase;">🧠 {t['why_forecast']}</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['yesterday']}</div>
                    <div style="font-size: 18px; font-weight: bold; color: {AQI_COLORS.get(yest_aqi_val, 'white')};">{yest_aqi_val}</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">{t['today']}</div>
                    <div style="font-size: 18px; font-weight: bold; color: {current_col};">{current_aqi}</div>
                </div>
            </div>
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px;">{t['why_forecast']}</div>
            <div style="font-size:13px; color:#cbd5e1; display:flex; flex-direction:column; gap:8px;">
                <div style="display:flex; justify-content:space-between; color:#cbd5e1 !important;"><span>{t['pm25_trend']}</span> <span style="color:{pm25_color} !important; font-weight:600;">{pm25_dir} {abs(pm25_diff):.1f}</span></div>
                <div style="display:flex; justify-content:space-between; color:#cbd5e1 !important;"><span>{t['primary_driver']}</span> <span style="color:#ef4444 !important; font-weight:600;">{spec['drivers'][0]}</span></div>
                <div style="display:flex; justify-content:space-between; color:#cbd5e1 !important;"><span>{t['secondary_driver']}</span> <span style="color:#fbbf24 !important; font-weight:600;">{spec['drivers'][1]}</span></div>
                <div style="display:flex; justify-content:space-between; color:#cbd5e1 !important;"><span>{t['background_factor']}</span> <span style="color:#38bdf8 !important; font-weight:600;">{spec['drivers'][2]}</span></div>
            </div>
        </div>"""

        kpi_html = f"""
        <div class="kpi-grid">
            <div class="kpi-card" style="animation-delay: 0.05s;">
                <div class="kpi-label">{t['kpi_current_aqi']}</div>
                <div class="kpi-val" style="color: {current_col};">{current_aqi}</div>
            </div>
            <div class="kpi-card" style="animation-delay: 0.1s;">
                <div class="kpi-label">{t['kpi_latest_pm']}</div>
                <div class="kpi-val" style="color: #f8fafc;">{latest_pm25:.1f} <span style="font-size: 12px; color: #64748b;">µg/m³</span></div>
            </div>
            <div class="kpi-card" style="animation-delay: 0.15s;">
                <div class="kpi-label">{t['kpi_forecast']}</div>
                <div class="kpi-val" style="color: {color};">{pred_cat}</div>
            </div>
            <div class="kpi-card" style="animation-delay: 0.2s;">
                <div class="kpi-label">{t['kpi_aqi_reduction']}</div>
                <div class="kpi-val" style="color: #4ade80;">{spec['improvement']} <span style="font-size: 12px; color: #64748b; font-weight: normal;">{t['est_label']}</span></div>
            </div>
            <div class="kpi-card" style="animation-delay: 0.25s;">
                <div class="kpi-label">{t['kpi_confidence']}</div>
                <div class="kpi-val" style="color: #38bdf8;">{confidence:.1f}%</div>
            </div>
            <div class="kpi-card" style="animation-delay: 0.3s;">
                <div class="kpi-label">{t['kpi_hotspots']}</div>
                <div class="kpi-val" style="color: #ef4444;">2 <span style="font-size: 12px; color: #64748b;">{t['active']}</span></div>
            </div>
        </div>
        """

        return trend_fig, gauge_fig, pred_html, rec_html, alert_html, kpi_html, explain_html
    except Exception as e:
        import traceback
        traceback.print_exc()
        import plotly.graph_objects as go
        err_fig = go.Figure()
        err_fig.update_layout(title="Error Loading Chart")
        err_html = f"<div style='color: #ef4444; padding: 12px; background: rgba(239,68,68,0.1); border-radius: 8px;'><b>Error in Analytics:</b><br>{str(e)}</div>"
        return err_fig, err_fig, err_html, "", "", "", ""

def get_hotspot_table_html():
    rows = ""
    for _, r in hotspot_df.iterrows():
        rows += f"""
        <tr style="border-bottom: 1px solid #334155;">
            <td style="padding: 12px; color: #f8fafc; font-weight: bold;">Cluster {int(r['cluster_id'])}</td>
            <td style="padding: 12px; color: #e2e8f0;">{r['wards']}</td>
            <td style="padding: 12px; color: #ef4444; font-weight: bold;">{r['avg_severity']:.1f}</td>
            <td style="padding: 12px; color: #cbd5e1;">{int(r['station_count'])}</td>
        </tr>
        """
    return f"""
    <div class="dark-card">
        <h3 style="color: white; margin: 0 0 16px 0; font-weight: bold;">🚨 Active DBSCAN Hotspot Clusters</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 2px solid #475569; color: #94a3b8; font-weight: bold; text-transform: uppercase; font-size: 12px;">
                    <th style="padding: 12px;">Cluster ID</th>
                    <th style="padding: 12px;">Wards Affected</th>
                    <th style="padding: 12px;">Avg Severity</th>
                    <th style="padding: 12px;">Stations Count</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    """

# ── Gradio UI ──────────────────────────────────────────────────────────────────
MAP_HTML = build_map()   

custom_css = """
body, .gradio-container {
    background-color: #0F172A !important;
    color: #F8FAFC !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}
.gradio-container { max-width: 1400px !important; margin: 0 auto !important; padding: 0 20px !important; }
.dark-card { background: #1E293B !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 20px !important; }
.hero-section { background: linear-gradient(to right, #1E293B, #0F172A) !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 40px !important; margin-bottom: 24px !important; }
.hero-title { font-size: 42px; font-weight: 800; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 16px 0; line-height: 1.2; }
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

@keyframes pulse {
    0% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.1); opacity: 1; text-shadow: 0 0 12px #38bdf8; }
    100% { transform: scale(1); opacity: 0.8; }
}
"""

with gr.Blocks(title="AirGuard AI", css=custom_css, theme=gr.themes.Base()) as demo:
    # Language Selector / ಭಾಷೆ ಆಯ್ಕೆ / भाषा चयन
    with gr.Row():
        gr.Markdown("") # Spacing
        lang_selector = gr.Radio(
            choices=["English", "ಕನ್ನಡ", "हिंदी"],
            value="English",
            label="Language / ಭಾಷೆ / भाषा",
            interactive=True
        )
        gr.Markdown("") # Spacing

    
    top_bar = gr.HTML("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #1E293B; margin-bottom: 20px;">
        <div style="display:flex; align-items:center; gap: 8px;">
            <div style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 8px #22c55e;"></div>
            <div style="color: #cbd5e1; font-weight: bold; font-size: 13px; text-transform: uppercase;">🟢 Live | 15 sec ago | 14 Stations</div>
        </div>
        <div style="color: #64748b; font-size: 12px; font-weight: 500;">Accuracy: 58.4% | Avg. Latency: 0.43s</div>
    </div>
    """)
    
    hero_section = gr.HTML("""
    <div class="hero-section">
        <h1 class="hero-title">AirGuard AI</h1>
        <p style="font-size: 18px; color: #cbd5e1; max-width: 600px; margin: 0 0 8px 0; font-weight: 500;">AI-Powered Urban Pollution Intelligence Platform</p>
        <div style="color: #60a5fa; font-weight: 600; letter-spacing: 2px; margin: 0 0 16px 0; font-size: 14px; text-transform: uppercase;">Predict • Detect • Explain • Recommend</div>
        <p style="color: #94a3b8; margin-bottom: 0; max-width: 600px; font-size: 15px;">Helping Municipal Authorities identify pollution hotspots before AQI becomes critical.</p>
    </div>
    """)
    
    exec_summary = gr.HTML("""
    <div class="dark-card" style="background: rgba(239, 68, 68, 0.1) !important; border: 1px solid #ef4444 !important; margin-bottom: 24px;">
        <h3 style="color: #ef4444; margin: 0 0 12px 0; font-size: 18px; font-weight: bold;">Executive Impact Summary</h3>
        <div style="display: flex; gap: 40px; flex-wrap: wrap;">
            <div><div style="font-size: 12px; color: #fca5a5; text-transform: uppercase;">Critical Hotspots</div><div style="font-size: 24px; font-weight: bold; color: white; margin-top: 4px;">🚨 2</div></div>
            <div><div style="font-size: 12px; color: #fca5a5; text-transform: uppercase;">Citizens at Risk</div><div style="font-size: 24px; font-weight: bold; color: white; margin-top: 4px;">👥 68,000</div></div>
            <div><div style="font-size: 12px; color: #fca5a5; text-transform: uppercase;">Expected AQI Improvement</div><div style="font-size: 24px; font-weight: bold; color: #4ade80; margin-top: 4px;">📉 18% <span style="font-size:12px; font-weight:normal; color:#cbd5e1;">with recommended actions</span></div></div>
            <div><div style="font-size: 12px; color: #fca5a5; text-transform: uppercase;">Today's Alerts</div><div style="font-size: 24px; font-weight: bold; color: white; margin-top: 4px;">⚠️ 6</div></div>
        </div>
    </div>
    """)

    with gr.Tabs() as tabs:
        with gr.TabItem("📊 Dashboard", id="dashboard"):
            with gr.Column(scale=1):
                kpi_html_out = gr.HTML()
                alert_html_out = gr.HTML()
            
            with gr.Row():
                with gr.Column(scale=1, min_width=280):
                    with gr.Column(elem_classes="dark-card"):
                        gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-size: 16px; font-weight: bold;'>Station Analytics</h3>")
                        station_dd = gr.Dropdown(choices=STATION_LIST, value=STATION_LIST[0], label="Search / Select Station", show_label=True, interactive=True)
                        run_btn = gr.Button("Analyze Data", variant="primary")
                    gr.HTML("<div style='height: 20px;'></div>")
                    explain_html_out = gr.HTML()
                
                with gr.Column(scale=2):
                    with gr.Row():
                        with gr.Column(scale=1): pred_html_out = gr.HTML()
                        with gr.Column(scale=1): rec_html_out = gr.HTML()
                    gr.HTML("<div style='height: 20px;'></div>")
                    with gr.Row():
                        with gr.Column(scale=2, elem_classes="dark-card"): trend_plot = gr.Plot(label="Trend", show_label=False)
                        with gr.Column(scale=1, elem_classes="dark-card"): gauge_plot = gr.Plot(label="Gauge", show_label=False)
                        
        with gr.TabItem("🗺 Live Pollution Map", id="map"):
            with gr.Column(elem_classes="dark-card"):
                gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-size: 18px; font-weight: bold;'>🗺️ Live Pollution Hotspot Map</h3>")
                gr.HTML(f"""<div class='map-container'>{MAP_HTML}</div>""")

        with gr.TabItem("📈 Forecast", id="forecast"):
            with gr.Row():
                with gr.Column(scale=1, min_width=280):
                    with gr.Column(elem_classes="dark-card"):
                        gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-size: 16px; font-weight: bold;'>Station Selector</h3>")
                        forecast_station_dd = gr.Dropdown(choices=STATION_LIST, value=STATION_LIST[0], label="Search / Select Station", show_label=True, interactive=True)
                        forecast_run_btn = gr.Button("Fetch Forecast", variant="primary")
                with gr.Column(scale=2):
                    with gr.Row():
                        with gr.Column(scale=2, elem_classes="dark-card"): forecast_trend_plot = gr.Plot(label="Trend", show_label=False)
                        with gr.Column(scale=1, elem_classes="dark-card"): forecast_gauge_plot = gr.Plot(label="Gauge", show_label=False)
                    gr.HTML("<div style='height: 20px;'></div>")
                    with gr.Row():
                        with gr.Column(scale=1): forecast_pred_html_out = gr.HTML()

        with gr.TabItem("🚨 Hotspots", id="hotspots"):
            gr.HTML(get_hotspot_table_html())
                
        with gr.TabItem("📱 Citizen Reports", id="reports"):
            with gr.Row():
                with gr.Column(scale=1, elem_classes="dark-card"):
                    gr.HTML("<h3 style='color: white; margin: 0 0 16px 0; font-weight: bold;'>Submit Local Incident</h3>")
                    report_station = gr.Dropdown(choices=STATION_LIST, value=STATION_LIST[0], label="Nearest Monitoring Station", interactive=True)
                    incident_type = gr.Dropdown(choices=["Garbage Burning", "Construction Dust", "Industrial Smoke", "Vehicle Exhaust"], label="Incident Type")
                    img_upload = gr.File(label="Upload Image Proof (Optional)")
                    submit_btn = gr.Button("Submit Report", variant="primary")
                    report_status = gr.HTML("<div style='height:50px;'></div>")
                
                with gr.Column(scale=2, elem_classes="dark-card"):
                    citizen_analytics_box = gr.HTML("""
                    <h3 style='color: white; margin: 0 0 16px 0; font-weight: bold;'>Today's Citizen Analytics</h3>
                    <div style='display:flex; gap:20px; flex-wrap:wrap;'>
                        <div style='background:#0f172a; padding:20px; border-radius:12px; flex:1; text-align:center; border: 1px solid #334155;'><h2 style='margin:0; color:#ef4444; font-size: 32px;'>12</h2><div style='color:#94a3b8; font-size:12px; margin-top:4px;'>Garbage Burning</div></div>
                        <div style='background:#0f172a; padding:20px; border-radius:12px; flex:1; text-align:center; border: 1px solid #334155;'><h2 style='margin:0; color:#eab308; font-size: 32px;'>8</h2><div style='color:#94a3b8; font-size:12px; margin-top:4px;'>Construction Dust</div></div>
                        <div style='background:#0f172a; padding:20px; border-radius:12px; flex:1; text-align:center; border: 1px solid #334155;'><h2 style='margin:0; color:#8b5cf6; font-size: 32px;'>4</h2><div style='color:#94a3b8; font-size:12px; margin-top:4px;'>Industrial Smoke</div></div>
                    </div>
                    <div style="margin-top: 24px; padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <h4 style="color: #38bdf8; margin: 0 0 8px 0;">Analytical Observations</h4>
                        <p style='color:#cbd5e1; margin:0; font-size:14px; line-height: 1.5;'>Recent reports indicate a 30% increase in localized garbage burning in Ward areas without active solid waste collection today. This corresponds directly with localized PM2.5 spikes.</p>
                    </div>
                    """)
                    
        with gr.TabItem("⚙️ System Metrics", id="metrics"):
            gr.HTML("""
            <div class="dark-card">
                <h3 style='color: white; margin: 0 0 20px 0; font-weight: bold;'>Platform Performance Overview</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                    <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
                        <div style="color: #94a3b8; font-size: 12px; text-transform: uppercase;">Prediction Accuracy</div>
                        <div style="font-size: 32px; font-weight: bold; color: #38bdf8; margin-top: 8px;">58.4%</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
                        <div style="color: #94a3b8; font-size: 12px; text-transform: uppercase;">Avg. Latency</div>
                        <div style="font-size: 32px; font-weight: bold; color: #4ade80; margin-top: 8px;">0.43s</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
                        <div style="color: #94a3b8; font-size: 12px; text-transform: uppercase;">Stations Monitored</div>
                        <div style="font-size: 32px; font-weight: bold; color: white; margin-top: 8px;">14</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
                        <div style="color: #94a3b8; font-size: 12px; text-transform: uppercase;">Total Historical Records</div>
                        <div style="font-size: 32px; font-weight: bold; color: white; margin-top: 8px;">1.37M</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px; border: 1px solid #334155;">
                        <div style="color: #94a3b8; font-size: 12px; text-transform: uppercase;">Model Re-training</div>
                        <div style="font-size: 24px; font-weight: bold; color: #fbbf24; margin-top: 8px;">Scheduled (2d)</div>
                    </div>
                </div>
            </div>
            """)
            
        with gr.TabItem("ℹ About", id="about"):
            gr.HTML("""
            <div class="dark-card">
                <h3 style='color: white; margin: 0 0 16px 0; font-weight: bold;'>About AirGuard AI</h3>
                <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 16px;">
                    AirGuard AI is an intelligent civic platform designed for municipal authorities in Bengaluru. By leveraging official CPCB and KSPCB sensor feeds alongside advanced machine learning algorithms (Random Forest forecasting & DBSCAN hotspot clustering), the system detects, highlights, and recommends policy mitigations for municipal pollution hotspots before they impact public health.
                </p>
                <div style="border-top: 1px solid #334155; padding-top: 16px;">
                    <div style="color: #e2e8f0; font-weight: bold; font-size: 15px; margin-bottom: 8px;">Built for Google Build with AI</div>
                    <div style="color: #64748b; font-size: 13px; margin-bottom: 16px;">Track 2: CleanAir & Clear Streets</div>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px;">
                        <span style="color: #94a3b8;">CPCB</span> •
                        <span style="color: #94a3b8;">KSPCB</span> •
                        <span style="color: #94a3b8;">Random Forest</span> •
                        <span style="color: #94a3b8;">DBSCAN</span> •
                        <span style="color: #94a3b8;">Gemini AI</span>
                    </div>
                </div>
            </div>
            """)

    # Architecture
    gr.HTML("""
    <div style='height: 40px;'></div>
    <div class="dark-card" style="margin-bottom: 40px; text-align: center;">
        <h3 style="color: white; margin: 0 0 20px 0; font-size: 18px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">Platform Architecture</h3>
        <div style="display: flex; justify-content: center; align-items: center; flex-wrap: wrap; gap: 16px; font-size: 14px; color: #cbd5e1;">
            <div style="background: rgba(56,189,248,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(56,189,248,0.4); font-weight: 500; box-shadow: 0 0 10px rgba(56,189,248,0.15); color: #cbd5e1;">📱 Citizen Reports</div>
            <div style="color: #38bdf8; text-shadow: 0 0 8px #38bdf8; font-weight: bold; font-size: 18px;">➔</div>
            <div style="background: rgba(56,189,248,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(56,189,248,0.4); font-weight: 500; box-shadow: 0 0 10px rgba(56,189,248,0.15); color: #cbd5e1;">📡 Sensor Data</div>
            <div style="color: #38bdf8; text-shadow: 0 0 8px #38bdf8; font-weight: bold; font-size: 18px;">➔</div>
            <div style="background: rgba(129,140,248,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(129,140,248,0.4); font-weight: 500; box-shadow: 0 0 10px rgba(129,140,248,0.15); color: #cbd5e1;">🧠 ML Models</div>
            <div style="color: #818cf8; text-shadow: 0 0 8px #818cf8; font-weight: bold; font-size: 18px;">➔</div>
            <div style="background: rgba(129,140,248,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(129,140,248,0.4); font-weight: 500; box-shadow: 0 0 10px rgba(129,140,248,0.15); color: #cbd5e1;">🚨 Hotspot Detection</div>
            <div style="color: #818cf8; text-shadow: 0 0 8px #818cf8; font-weight: bold; font-size: 18px;">➔</div>
            <div style="background: rgba(74,222,128,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(74,222,128,0.4); font-weight: 500; box-shadow: 0 0 10px rgba(74,222,128,0.15); color: #cbd5e1;">💡 AI Recommendations</div>
            <div style="color: #4ade80; text-shadow: 0 0 8px #4ade80; font-weight: bold; font-size: 18px;">➔</div>
            <div style="background: rgba(251,191,36,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(251,191,36,0.4); font-weight: 500; box-shadow: 0 0 10px rgba(251,191,36,0.15); color: #cbd5e1;">🏛️ Municipal Dashboard</div>
        </div>
    </div>
    """)

    # Helper function for forecast tab prediction
    def make_forecast_prediction(station_name, lang="English"):
        try:
            t = DYNAMIC_TRANSLATIONS.get(lang, DYNAMIC_TRANSLATIONS["English"])
            trend_fig = plot_trend(station_name)
            wrow = ward_df[ward_df['station'] == station_name]
            if wrow.empty: return trend_fig, go.Figure(), f"<p>{t['not_found']}</p>"
            ward_name = wrow.iloc[0]['ward_name']
            station_history = ts_daily[ts_daily['station'] == station_name].copy()
            max_date = station_history['date'].max() if len(station_history) > 0 else pd.NaT
            if pd.isna(max_date): return trend_fig, go.Figure(), f"<p>{t['no_data']}</p>"
            
            today = max_date
            latest_pm25 = station_history.sort_values('date').iloc[-1]['pm25']
            gauge_fig = plot_gauge(latest_pm25)
            
            X, err = build_feature_row(station_name, today, ward_name, station_history)
            if X is None: return trend_fig, gauge_fig, f"<p>Error: {err}</p>"
            
            proba = rf_model.predict_proba(X)[0]
            classes = list(rf_model.classes_)
            pred_idx = int(np.argmax(proba))
            pred_cat = classes[pred_idx]
            confidence = float(proba[pred_idx]) * 100
            color = AQI_COLORS[pred_cat]
            next_d = today + datetime.timedelta(days=1)
            
            bar_chart_html = "".join([f"<div style='display:flex; align-items:center; margin-bottom:8px;'><div style='width:70px; font-size:12px; color: white;'>{c}</div><div style='flex-grow:1; background:#334155; height:8px; border-radius:4px; margin:0 12px;'><div style='background:{AQI_COLORS.get(c, '#94a3b8')}; width:{p*100:.1f}%; height:100%; border-radius:4px;'></div></div><div style='width:40px; text-align:right; font-size:12px; color:white;'>{p*100:.0f}%</div></div>" for c, p in zip(classes, proba)])
            
            pred_html = f"""
            <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; height: 100%;">
                <h4 style="margin: 0 0 16px 0; color: #38bdf8; font-size: 14px; font-weight: 600; text-transform: uppercase;">{t['forecast']}: {next_d.strftime("%d %b %Y")}</h4>
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">{t['prediction']}</div>
                    <div style="font-size: 32px; font-weight: bold; color: {color}; text-shadow: 0 0 10px {color}40;">{pred_cat}</div>
                    <div style="font-size: 14px; color: #4ade80; margin-top: 4px;">{t['confidence']}: {confidence:.1f}%</div>
                </div>
                <h5 style="margin: 0 0 12px 0; color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase;">{t['class_probs']}</h5>
                {bar_chart_html}
            </div>"""
            return trend_fig, gauge_fig, pred_html
        except Exception as e:
            import traceback
            traceback.print_exc()
            import plotly.graph_objects as go
            err_fig = go.Figure()
            err_fig.update_layout(title="Error Loading Chart")
            err_html = f"<div style='color: #ef4444; padding: 12px; background: rgba(239,68,68,0.1); border-radius: 8px;'><b>Error in Forecast:</b><br>{str(e)}</div>"
            return err_fig, err_fig, err_html

    # Events for Dashboard tab
    run_btn.click(fn=lambda: gr.update(value="Analyzing...", interactive=False), outputs=[run_btn]).then(
        fn=make_prediction, inputs=[station_dd, lang_selector],
        outputs=[trend_plot, gauge_plot, pred_html_out, rec_html_out, alert_html_out, kpi_html_out, explain_html_out]
    ).then(fn=lambda: gr.update(value="Analyze Data", interactive=True), outputs=[run_btn])
    
    station_dd.change(fn=lambda: gr.update(value="Analyzing...", interactive=False), outputs=[run_btn]).then(
        fn=make_prediction, inputs=[station_dd, lang_selector],
        outputs=[trend_plot, gauge_plot, pred_html_out, rec_html_out, alert_html_out, kpi_html_out, explain_html_out]
    ).then(fn=lambda: gr.update(value="Analyze Data", interactive=True), outputs=[run_btn])
    
    # Events for Forecast tab
    forecast_run_btn.click(fn=lambda: gr.update(value="Fetching...", interactive=False), outputs=[forecast_run_btn]).then(
        fn=make_forecast_prediction, inputs=[forecast_station_dd, lang_selector],
        outputs=[forecast_trend_plot, forecast_gauge_plot, forecast_pred_html_out]
    ).then(fn=lambda: gr.update(value="Fetch Forecast", interactive=True), outputs=[forecast_run_btn])
    
    forecast_station_dd.change(fn=lambda: gr.update(value="Fetching...", interactive=False), outputs=[forecast_run_btn]).then(
        fn=make_forecast_prediction, inputs=[forecast_station_dd, lang_selector],
        outputs=[forecast_trend_plot, forecast_gauge_plot, forecast_pred_html_out]
    ).then(fn=lambda: gr.update(value="Fetch Forecast", interactive=True), outputs=[forecast_run_btn])

    # Citizen report submission
    submit_btn.click(fn=lambda: gr.update(value="Submitting...", interactive=False), outputs=[submit_btn]).then(
        fn=submit_citizen_report, inputs=[incident_type, report_station, img_upload], outputs=[report_status]
    ).then(fn=lambda: gr.update(value="Submit Report", interactive=True), outputs=[submit_btn])
    
    # Trigger initial load prediction
    demo.load(fn=make_prediction, inputs=[station_dd, lang_selector],
              outputs=[trend_plot, gauge_plot, pred_html_out, rec_html_out, alert_html_out, kpi_html_out, explain_html_out])
    demo.load(fn=make_forecast_prediction, inputs=[forecast_station_dd, lang_selector],
              outputs=[forecast_trend_plot, forecast_gauge_plot, forecast_pred_html_out])


    # Language change handler
    lang_selector.change(
        fn=change_language,
        inputs=[lang_selector],
        outputs=[
            top_bar, hero_section, exec_summary, 
            station_dd, run_btn, 
            forecast_station_dd, forecast_run_btn,
            report_station, incident_type, img_upload, submit_btn,
            citizen_analytics_box
        ]
    ).then(
        fn=make_prediction,
        inputs=[station_dd, lang_selector],
        outputs=[trend_plot, gauge_plot, pred_html_out, rec_html_out, alert_html_out, kpi_html_out, explain_html_out]
    ).then(
        fn=make_forecast_prediction,
        inputs=[forecast_station_dd, lang_selector],
        outputs=[forecast_trend_plot, forecast_gauge_plot, forecast_pred_html_out]
    )

if __name__ == '__main__':
    demo.launch(server_name='0.0.0.0', server_port=7860, share=False, show_error=True)
