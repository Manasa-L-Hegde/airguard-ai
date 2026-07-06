# 🌿 AirGuard AI
> **Intelligent Urban Pollution Hotspot Detection & Clean Street Decision Support**
> 
> *Tagline: "Predict Pollution Before It Happens"*

[![Live Demo](https://img.shields.io/badge/%E2%9A%A1-Live%20Demo-brightgreen?style=for-the-badge)](https://huggingface.co/spaces/manasahegde/airguard.ai)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue?style=for-the-badge)](https://huggingface.co/spaces/manasahegde/airguard.ai)

---

## 📌 1. Problem Statement
Rapid urbanization and rising vehicle density in metropolitan cities like Bengaluru have led to localized air pollution hotspots that go undetected until the Air Quality Index (AQI) reaches critical, health-hazardous levels. 

The primary challenges are:
* **Delayed Detection**: Traditional pollution monitoring is reactive, identifying bad air days only after they occur.
* **Lack of Actionability**: Municipal authorities and traffic commissioners lack real-time, explainable, and localized decision support systems to implement targeted street-level cleaning, traffic diversion, and industrial dust control.
* **Lack of Civic Integration**: Environmental management tools operate in silos without integrating crowdsourced citizen reports on illegal garbage burning or construction dust.

This project was built for the **Hack2Skill "Build with AI: Code for Communities" Hackathon (Track 2: CleanAir & Clear Streets)** by **Team DataPulse** to address these challenges head-on.

---

## 💡 2. Solution Overview
**AirGuard AI** is a predictive, explainable, and actionable decision-support platform designed for smart city administrators. By combining machine learning (Random Forest forecasting & DBSCAN spatial clustering) with real-world sensor data, AirGuard AI identifies high-density pollution clusters before they form. It equips municipal departments with estimated playbooks (including budget guidance, agency ownership, and citizen impact metrics) to clean urban streets and divert traffic dynamically.

---

## ✨ 3. Key Features
* 🌍 **Real-Time AQI Monitoring**: Interactive dashboard mapping real-time PM2.5 readings and AQI categories across 14 active CPCB and KSPCB monitoring stations in Bengaluru (historical data spanning 2017–2025).
* 📈 **ML-Based Pollution Forecasting**: A Random Forest classifier predicts next-day AQI levels (Good, Moderate, Poor, Severe) with explicit confidence percentages (achieving a validated test accuracy of 58.4%).
* 🚨 **DBSCAN Hotspot Clustering**: Automatically groups stations into spatial clusters (detecting 2 active regional hotspots and highlighting 4 standalone high-priority stations on the map).
* 🧠 **Explainable AI (XAI)**: Breaks down primary, secondary, and background drivers of localized pollution based on the ward type (e.g., Peenya industrial stack emissions vs. Silk Board automotive congestion) to give administrators transparent context.
* 🏛️ **Municipal Decision Support & Action Cards**: Dynamically renders estimated priority and indicative resource playbooks based on severity and ward classification.
  * *Note*: Budget ranges (₹0.8L–₹8.7L), citizen risk figures, and projected AQI reductions (e.g., 18% reduction) are **illustrative estimates for demonstration purposes**, designed to be calibrated with real municipal financial and census data in production.
* 🚯 **Citizen Reporting Portal**: Provides a crowdsourced environmental incident reporting form (station selector, incident type, and optional image upload) that logs submissions with unique reference IDs directly to a persistent local CSV dataset. *This portal serves as an administrative proof-of-concept and does not trigger real-world civic dispatches.*
* 🌐 **Language Accessibility Toggle**: Lightweight language switcher (English, ಕನ್ನಡ, हिंदी) for all static UI labels and dynamically generated dashboard elements, directly embedded inside `app.py` for community inclusivity.

---

## 🛠️ 4. Tech Stack
* **Programming Language**: Python 3.11 (Hugging Face Spaces Deployment Container) / Python 3.12 (Local Development Environment)
* **User Interface**: Gradio (v3.50.2 on Spaces / Gradio 6.x supported locally)
* **Machine Learning**: Scikit-Learn (Random Forest classification & DBSCAN clustering), NumPy, Joblib (model serialization)
* **Geospatial & Visualizations**: Folium (interactive maps), Plotly (gauge charts and historical time-series graphs), Pandas (data manipulation)
* **AI Calibration**: Google Gemini API (used offline to pre-generate and calibrate localized policy playbooks, avoiding real-time API latency and rate-limit dependencies during execution)

---

## ⚙️ 5. Project Directory Structure
```
airguard-ai/
├── data/
│   ├── processed/
│   │   ├── bengaluru_air_quality.csv      # Preprocessed timeseries dataset
│   │   └── reports.csv                    # Citizen incident reports dataset
│   └── raw/                               # Raw telemetry logs
├── models/
│   └── aqi_category_rf.pkl                # Trained Random Forest classifier weights
├── screenshots/                           # UI dashboard screenshots
│   ├── airguard_hero_metrics_1783267505484.png
│   └── dashboard_recommendations_1783267930581.png
├── scripts/
│   ├── build_bengaluru_air_quality_timeseries.py
│   ├── fetch_bengaluru_historical.py
│   ├── generate_policy_recommendations.py  # Gemini offline policy generator
│   ├── ingest_bengaluru_historical.py
│   ├── preprocess_aqi.py
│   ├── train_pm25_forecast.py             # RandomForest model training script
│   └── validate_ward_hotspot_analysis.py  # DBSCAN clustering script
├── LICENSE                                # MIT license
├── README.md                              # Main documentation file
├── app.py                                 # Core Gradio dashboard source code
└── requirements.txt                       # Python dependencies
```

---

## ⚠️ 6. Limitations & Future Scope
1. **Inclusivity & Accessibility Gap**: While the dashboard features a hardcoded translation dictionary for English, Kannada, and Hindi labels, it currently lacks real-time voice input and dynamic translation for citizen comments. Future iterations will integrate Google Cloud Speech-to-Text and Google Translation APIs.
2. **Single-City Scope**: The platform is currently configured specifically for Bengaluru's ward boundaries and KSPCB/CPCB stations. The underlying software architecture, however, is modular and designed to generalize to any city globally provided compatible geo-boundary and air quality telemetry data are supplied.
3. **Pollution Spike Predictions**: The RandomForest model relies on lag features and historical AQI averages, limiting its ability to forecast sudden, extreme air quality spikes (e.g., transition to Severe) caused by immediate weather changes. Future scope includes integrating real-time meteorological variables (temperature, relative humidity, wind speed, wind direction).

---

## 📸 7. Screenshots

### Executive Summary Grid & Upgraded UI
![AirGuard AI Dashboard Top Half](https://raw.githubusercontent.com/Manasa-L-Hegde/airguard-ai/main/screenshots/airguard_hero_metrics_1783267505484.png)

### Model Forecasts, AI Explanations & Action Cards
![AirGuard AI Action Cards and Details](https://raw.githubusercontent.com/Manasa-L-Hegde/airguard-ai/main/screenshots/dashboard_recommendations_1783267930581.png)

---

## 💻 8. Setup & Run Locally

### Prerequisites
* Python 3.11 or 3.12
* Git

### Local Execution Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Manasa-L-Hegde/airguard-ai.git
   cd airguard-ai
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the App**:
   ```bash
   python app.py
   ```
   Navigate to `http://localhost:7860/` in your web browser.

---

## 🌐 9. Live Demo
Explore the interactive model predictions, hotspot clusters, and explainable decision-support cards live on Hugging Face Spaces:
👉 **[AirGuard AI Live Web App](https://huggingface.co/spaces/manasahegde/airguard.ai)**

---

## 👥 10. Team & Acknowledgments
* **Team Name**: DataPulse
* Built with 💙 for the Google **Code for Communities 2026** Hackathon / Hack2Skill.
* Calibration air quality datasets sourced from the Central Pollution Control Board (CPCB) and Karnataka State Pollution Control Board (KSPCB).

---

## 📄 11. License
This project is licensed under the MIT License - see the `LICENSE` file for details.

