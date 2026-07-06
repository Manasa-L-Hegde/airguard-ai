---
title: AirGuard AI
emoji: 🛰️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.19.0
app_file: app.py
pinned: false
license: mit
short_description: Multimodal Urban Air Quality & Decision Support Platform
---

# AirGuard AI — Intelligent Urban Pollution Hotspot Detection & Decision Support

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Hugging_Face-blue)](https://huggingface.co/spaces/manasahegde/airguard.ai)

> **Hack2Skill "Build with AI: Code for Communities"** — **Track 2: CleanAir & Clear Streets**  
> **Team:** DataPulse | **Live App:** [Hugging Face Space](https://huggingface.co/spaces/manasahegde/airguard.ai) | **Repository:** [GitHub](https://github.com/Manasa-L-Hegde/airguard-ai)

---

## 🎯 Tagline
*A multimodal urban air quality intelligence platform fusing citizen incident photos, ground sensor telemetry, and Sentinel-5P satellite remote sensing to detect unmonitored pollution hotspots, forecast 24-hour AQI trajectories, and automate municipal resource deployment.*

---

## 🚨 The Problem
City-level air quality monitoring relies on sparse, expensive static reference stations (e.g., only 14 stations across 800+ km² in Bengaluru), creating massive spatial blind spots across urban neighborhoods. Hyper-local, episodic pollution events — such as localized open garbage burning, unpaved construction dust, and industrial evening emission spikes — occur in unmonitored neighborhoods and go completely undetected by municipal authorities. This leaves vulnerable urban communities exposed to severe respiratory health risks without timely intervention or enforcement.

---

## 💡 The Solution
**AirGuard AI** bridges this critical monitoring gap by fusing three distinct data modalities into a unified urban decision support platform:
1. **📸 Citizen Incident Reports:** Mobile photos submitted by citizens, classified in real time using Computer Vision (CV) to detect smoke, dust, and open burning with severity scores.  
   * **Image-Based CV Pipeline:** The vision engine analyzes actual uploaded image pixel data (color channel statistics, dark plume absorption, tan/brown dust hue clustering, desaturation haze, and edge density) to dynamically generate image-derived smoke probabilities, dust probabilities, confidence scores, and severity ratings (0-100).
2. **📡 Ground Sensor Feeds:** Real-time CPCB / KSPCB station telemetry for PM2.5 and PM10 metrics across urban wards.
3. **🛰️ Satellite Remote Sensing:** Sentinel-5P TROPOMI Nitrogen Dioxide (NO₂) column density and MODIS Aerosol Optical Depth (AOD) upper-atmosphere layer overlays.

Using **DBSCAN Spatial Clustering**, AirGuard AI discovers hidden unmonitored hotspot polygons across the city. A **Random Forest Regressor** forecasts 24-hour AQI trajectories with 95% confidence bounds. Finally, the platform translates multi-modal intelligence into actionable **Municipal Decision Support Cards**, providing city officials with clear action protocols, estimated cleanup budgets, and expected AQI reductions.

---

## 🧩 End-to-End System Architecture

```
 📸 Citizen Incident Photos        📡 CPCB Ground Sensors        🛰️ Sentinel-5P Satellite NO₂
           │                                │                               │
           ▼                                ▼                               ▼
 ResNet CV Photo Classifier      Sensor Telemetry Pipeline      Column Density Anomalies
           │                                │                               │
           └────────────────────────────────┼───────────────────────────────┘
                                            │
                                            ▼
                              🧠 Multimodal Fusion Engine
                                            │
                             ┌──────────────┴──────────────┐
                             ▼                             ▼
                🚨 DBSCAN Hotspot Clustering    📈 Random Forest 24h Forecaster
                             │                             │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                            🏛️ Municipal Decision Support System
                                            │
                             ┌──────────────┴──────────────┐
                             ▼                             ▼
               🚒 Dispatch & Action Cards      📊 Executive KPI Dashboard
```

---

## 🛠️ Tech Stack

| Category | Technology / Framework | Purpose & Usage |
| --- | --- | --- |
| **Machine Learning** | Scikit-Learn (DBSCAN, RandomForest) | Spatial Hotspot Clustering & 24h AQI Trajectory Forecasting |
| **Computer Vision** | PyTorch / Torchvision (ResNet) | Citizen Incident Image Classification & Severity Scoring |
| **Remote Sensing** | Sentinel-5P TROPOMI NO₂ & MODIS AOD | Atmospheric Column Density & Upper-Air Plume Analysis |
| **Dashboard UI** | Gradio 6.19.0, HTML5 / Vanilla CSS3 | Responsive Dark-Theme Municipal Control Center |
| **Data Analytics** | Pandas, NumPy, Joblib | Time-series processing & model serialization |
| **Interactive GIS** | Folium, Leaflet.js, Plotly Express | Multi-Layered Urban Map & 3D Interactive Timelines |
| **Deployment Platform** | Hugging Face Spaces (Python 3.12) | Cloud Serverless Prototype Deployment |

---

## 🌐 Inclusivity & Accessibility (Rubric Target: 15%)

- **Multilingual UI Support:** Built-in language capability supporting English, Kannada (ಕನ್ನಡ), and Hindi (हिंदी) to ensure accessibility for local civic workers and diverse urban citizens.
- **Roadmap Item — Voice & SMS Intake (Phase 2):** To reach low-literacy and low-connectivity citizens, our next phase integrates **Twilio & WhatsApp Business API**. Citizens without smartphones or high-speed internet will be able to submit voice notes or WhatsApp photos for automated AI speech-to-text transcription and CV hotspot registration.

---

## 🚀 Deployability & Enterprise Scaling Path (Rubric Target: 25%)

AirGuard AI's modular architecture is designed to map directly from the current prototype to enterprise-grade smart city infrastructure:
- **Inference Service:** Containerized PyTorch and Scikit-Learn microservices deployed on **Google Cloud Run** / **AWS ECS** for serverless, auto-scaling model execution.
- **Geospatial Data Warehouse:** Sensor data and satellite overlays streamed into **Google BigQuery** / **Snowflake** for high-throughput spatial SQL analytics over historical datasets.
- **Real-Time Citizen Ingestion:** **Firebase Realtime Database** & **Google Pub/Sub** for sub-second citizen incident ingestion and municipal alert push notifications.
- **IoT Edge Ingestion:** MQTT protocol support for direct telemetry streaming from low-cost ward-level micro-sensor nodes.

---

## 📸 Screenshots & Dashboard Overview

*Below are placeholder markers for platform screenshots:*

| Component | Interface Preview |
| --- | --- |
| **Executive Impact Dashboard** | `![Executive Dashboard](screenshots/dashboard.png)` |
| **Multimodal GIS Map** | `![Pollution Map](screenshots/map.png)` |
| **Citizen CV Upload** | `![Citizen Verification](screenshots/citizen_verification.png)` |
| **Municipal Decision Support** | `![Municipal Alerts](screenshots/alerts.png)` |

---

## 💻 Setup & Local Execution

### Prerequisites
- **Python:** 3.12 or 3.11
- **Pip:** Standard Python package manager

### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Manasa-L-Hegde/airguard-ai.git
   cd airguard-ai
   ```

2. **Create & Activate a Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Platform Locally:**
   ```bash
   python app.py
   ```
   *Open your browser and navigate to `http://localhost:7860` to access the AirGuard AI Dashboard.*

---

## 🏆 Hackathon Submission Details

- **Hackathon:** Hack2Skill "Build with AI: Code for Communities"
- **Track:** Track 2: CleanAir & Clear Streets
- **Team:** DataPulse
- **Live Space:** [https://huggingface.co/spaces/manasahegde/airguard.ai](https://huggingface.co/spaces/manasahegde/airguard.ai)
- **GitHub Repo:** [https://github.com/Manasa-L-Hegde/airguard-ai](https://github.com/Manasa-L-Hegde/airguard-ai)
