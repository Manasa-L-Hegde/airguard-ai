# 🌿 AirGuard AI — Multimodal Urban Air Quality Platform
> **Neighbourhood-Level Pollution Mapping via Citizen Photos, Ground Sensors & Satellite Imagery**
> 
> *Tagline: "Predict, Detect & Resolve Urban Pollution Before It Happens"*

[![Live Demo](https://img.shields.io/badge/%E2%9A%A1-Live%20Demo-brightgreen?style=for-the-badge)](https://huggingface.co/spaces/manasahegde/airguard.ai)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue?style=for-the-badge)](https://huggingface.co/spaces/manasahegde/airguard.ai)

---

## 📌 1. Hackathon Problem Statement & Objective
> *"Build a neighbourhood-level pollution map combining citizen-uploaded photos of smoke/dust, local sensor readings, and satellite imagery. The system should automatically detect hidden pollution hotspots, predict air quality spikes over the next 24 hours, and alert municipal teams so they can deploy resources."*

**AirGuard AI** satisfies 100% of these requirements by establishing an end-to-end **Multimodal AI Pipeline**:
$$\text{Citizen Photo (CV)} + \text{Ground Sensor (CPCB/KSPCB)} + \text{Satellite Imagery (Sentinel-5P)} \xrightarrow{} \text{Hidden Hotspot (DBSCAN)} \xrightarrow{} \text{24h Forecast (RF + 95\% CI)} \xrightarrow{} \text{Municipal Alert System}$$

---

## ✨ 2. Multi-Modal AI Features Implemented

### 📸 Feature 1: Citizen Pollution Image Analysis (`vision/`)
- Analyzes photos of smoke, garbage burning, industrial emissions, road dust, and construction dust using computer vision.
- Computes: **Smoke Probability**, **Dust Probability**, **AI Confidence**, **Severity Score (0–100)**, and detailed visual diagnostic explanations.
- Features automatic offline image processing fallback when internet or heavy deep learning runtime is unavailable.

### 🛰️ Feature 2: Satellite Remote Sensing Layer (`services/satellite_service.py`)
- Integrates **Sentinel-5P NO₂ Tropospheric Column Density** ($\mu\text{mol/m}^2$) and MODIS **Aerosol Optical Depth (AOD)** overlays.
- Interactive Folium layer controls to toggle satellite pollution raster heatmaps across Bengaluru wards.

### 🧠 Feature 3: Multimodal AI Fusion Engine (`services/multimodal_fusion.py`)
- Fuses heterogeneous data sources (Citizen Image Severity + Ground Sensor AQI + PM2.5 + Humidity & Wind + Satellite NO₂ + Traffic Density) into a unified **Pollution Risk Score (0–100)**.
- Classifies risk into **Low**, **Moderate**, **High**, and **Critical**.
- Generates Plotly explainable AI (XAI) feature contribution breakdown charts.

### 🚨 Feature 4: DBSCAN Hidden Hotspot Detection (`services/hotspot_detector.py`)
- Executes Density-Based Spatial Clustering of Applications with Noise (`sklearn.cluster.DBSCAN`).
- Fuses coordinates from ground sensors, citizen reports, and satellite anomalies.
- Flags **Unmonitored / Hidden Hotspots** (areas with high citizen/satellite signals where ground sensors are absent) and renders **RED Pulsing Polygons** on Folium.

### 📈 Feature 5: 24-Hour AQI Predictive Forecasting (`forecast/aqi_forecaster.py`)
- Random Forest Regression model incorporating multi-modal features (PM2.5, PM10, Temp, Humidity, Wind, Traffic, Satellite NO₂).
- Computes **95% Confidence Intervals** (upper and lower bounds from decision tree variance).
- Renders interactive 24-hour predictive trajectory line charts with shaded confidence bands in Plotly.

### 🏛️ Feature 6: Automated Municipal Alert Engine (`alerts/municipal_alert.py`)
- Triggers when Pollution Risk Score > 75 or Critical hotspots occur.
- Generates automatic response cards:
  - **Priority**: HIGH / CRITICAL
  - **Reason**: Detailed explanation of pollution drivers.
  - **Recommended Protocol**: Deploy water mist cannons, anti-smog guns, or sanitation clearing teams.
  - **Metrics**: Affected population estimate, expected AQI reduction %, and estimated cleanup budget.
- Includes an interactive **Resource Dispatch Simulator** for city administrators.

### 📱 Feature 7: Citizen Incident Verification Tracker (`services/citizen_service.py`)
- Assigns every uploaded image a Reference ID (`ARG-2026-XXXX`), GPS coordinates, timestamp, AI confidence, and Verification Status (`Pending`, `Verified`, `Resolved`).
- Real-time status tracking table saved to persistent local dataset (`data/processed/reports.csv`).

### 📊 Feature 8: Interactive Multi-Modal Timeline (`dashboard/timeline.py`)
- Subplot time-series chart showing Past AQI, Present AQI, 24h Predicted AQI, Citizen Report volume bars, and Satellite NO₂ trend lines.

### 📊 Feature 9: Executive Impact Dashboard (`dashboard/executive_dashboard.py`)
- High-level KPI summary cards for city leadership:
  1. Active Pollution Hotspots (🚨 3 Zones)
  2. Average AQI (🌿 78 - Moderate)
  3. Critical Wards (⚠️ Peenya, Silk Board)
  4. Citizen Reports Today (📱 28 Verified)
  5. Satellite NO₂ Anomalies (🛰️ 4 Signals)
  6. High Risk Wards (🚨 6 Active)
  7. Departments Dispatched (🚒 8 Teams)
  8. Predicted AQI Tomorrow (📈 115 Unhealthy)

### 🏗️ Feature 10: Production Architecture & Clean Directory Structure
- Clean modular package architecture (`vision/`, `services/`, `forecast/`, `alerts/`, `dashboard/`, `utils/`).
- Seamless single entry point (`app.py`) working on local environments and Hugging Face Spaces with zero breaking changes.

---

## 🛠️ 3. Technology Stack
- **Core Platform**: Python 3.11 / 3.12 / 3.14 (with runtime shims)
- **UI Framework**: Gradio (v3.50.2 with custom Dark Theme Glassmorphism)
- **Machine Learning & AI**: Scikit-Learn (Random Forest & DBSCAN clustering), NumPy, Joblib, Computer Vision (PIL / OpenCV)
- **Geospatial & Visualization**: Folium (Interactive Map with Layer Control), Plotly (Multi-modal charts & gauges), Pandas
- **Remote Sensing Integration**: Sentinel-5P NO₂ tropospheric column density & AOD satellite grid simulation

---

## ⚙️ 4. Project Directory Structure
```
airguard-ai/
├── alerts/
│   ├── __init__.py
│   └── municipal_alert.py        # Municipal Alert Engine & Resource Simulator
├── dashboard/
│   ├── __init__.py
│   ├── executive_dashboard.py    # Executive KPI summary cards
│   └── timeline.py               # Multi-modal interactive timeline plotter
├── data/
│   ├── processed/
│   │   ├── bengaluru_air_quality_timeseries.csv
│   │   ├── hotspot_clusters.csv
│   │   ├── reports.csv           # Citizen report database
│   │   └── ward_mapped_stations.csv
├── forecast/
│   ├── __init__.py
│   └── aqi_forecaster.py         # 24-Hour Random Forest AQI Forecaster + 95% CI
├── models/
│   ├── aqi_category_rf.pkl
│   └── pm25_forecast_rf.pkl
├── services/
│   ├── __init__.py
│   ├── citizen_service.py        # Citizen Verification & Status Tracker
│   ├── hotspot_detector.py       # DBSCAN Hidden Hotspot Detector
│   ├── multimodal_fusion.py      # Multimodal AI Risk Score Fusion Engine
│   └── satellite_service.py      # Sentinel-5P Satellite Remote Sensing Service
├── utils/
│   ├── __init__.py
│   └── geo_utils.py              # Spatial calculations & Haversine distance
├── vision/
│   ├── __init__.py
│   └── image_analyzer.py         # Computer Vision photo analyzer (Smoke/Dust)
├── app.py                        # Single entry point Gradio Web Application
├── README.md                     # Main project documentation
└── requirements.txt              # Python package dependencies
```

---

## 💻 5. Setup & Run Locally

```bash
# 1. Clone Repository
git clone https://github.com/Manasa-L-Hegde/airguard-ai.git
cd airguard-ai

# 2. Create Virtual Environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Launch AirGuard AI Platform
python app.py
```
Open `http://localhost:7860/` in your web browser.

---

## 🌐 6. Live Production Deployment
🚀 **[AirGuard AI Live Application on Hugging Face Spaces](https://huggingface.co/spaces/manasahegde/airguard.ai)**

---

## 📄 7. License
This project is licensed under the **MIT License**.
