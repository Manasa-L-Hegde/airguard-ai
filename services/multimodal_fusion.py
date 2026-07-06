# -*- coding: utf-8 -*-
"""
AirGuard AI — Multimodal AI Fusion Engine
===========================================
Fuses heterogeneous signals (Citizen Photo CV confidence & severity, ground CPCB/KSPCB sensors,
satellite Sentinel-5P NO2/AOD rasters, meteorological parameters, and simulated traffic density)
into a unified neighbourhood-level Pollution Risk Score (0-100).
"""

import numpy as np
import plotly.graph_objects as go


class MultimodalFusionEngine:
    """
    Multimodal AI Fusion engine calculating composite urban pollution risk
    and explainable feature contribution weights.
    """

    def __init__(self):
        # Default modality feature weights
        self.weights = {
            "sensor_pm25": 0.30,
            "citizen_image": 0.25,
            "satellite_no2": 0.20,
            "traffic_density": 0.15,
            "meteorology": 0.10
        }

    def compute_risk_score(self, 
                           pm25_val=85.0, 
                           citizen_severity=75.0, 
                           satellite_no2=140.0, 
                           humidity=65.0, 
                           wind_speed=8.0, 
                           traffic_density=70.0):
        """
        Compute composite Multi-modal Pollution Risk Score (0-100).
        
        Inputs:
        - pm25_val: float (Ground PM2.5 µg/m³)
        - citizen_severity: float (0-100 CV score from photo)
        - satellite_no2: float (Sentinel-5P NO2 umol/m²)
        - humidity: float (Relative Humidity %)
        - wind_speed: float (Wind speed in km/h)
        - traffic_density: float (Traffic congestion index 0-100)
        
        Returns dict with score, classification, color, and modal contributions.
        """
        # 1. Normalize PM2.5 sub-index (0-100 scale; 150 µg/m³ maps to 100)
        sensor_score = min(100.0, (pm25_val / 150.0) * 100.0)
        
        # 2. Normalize Citizen Image severity (0-100 scale)
        citizen_score = float(np.clip(citizen_severity, 0.0, 100.0))
        
        # 3. Normalize Satellite NO2 sub-index (200 µmol/m² maps to 100)
        sat_score = min(100.0, (satellite_no2 / 200.0) * 100.0)
        
        # 4. Normalize Traffic sub-index (0-100 scale)
        traffic_score = float(np.clip(traffic_density, 0.0, 100.0))
        
        # 5. Meteorology penalty: High humidity (>70%) & Low wind (<5 km/h) traps pollutants
        met_penalty = 0.0
        if humidity > 70: met_penalty += 15.0
        if wind_speed < 6: met_penalty += 20.0
        met_score = min(100.0, met_penalty + 30.0)

        # Composite Multi-modal Weighted Sum
        composite_score = (
            self.weights["sensor_pm25"] * sensor_score +
            self.weights["citizen_image"] * citizen_score +
            self.weights["satellite_no2"] * sat_score +
            self.weights["traffic_density"] * traffic_score +
            self.weights["meteorology"] * met_score
        )
        
        risk_score = round(float(np.clip(composite_score, 0.0, 100.0)), 1)

        # Classification thresholds
        if risk_score >= 80.0:
            classification = "Critical"
            color = "#ef4444"
            badge = "🚨 CRITICAL RISK"
        elif risk_score >= 60.0:
            classification = "High"
            color = "#f97316"
            badge = "⚠️ HIGH RISK"
        elif risk_score >= 35.0:
            classification = "Moderate"
            color = "#eab308"
            badge = "🟡 MODERATE RISK"
        else:
            classification = "Low"
            color = "#22c55e"
            badge = "🟢 LOW RISK"

        contributions = {
            "Ground AQI Sensors": round(self.weights["sensor_pm25"] * sensor_score, 1),
            "Citizen Image AI": round(self.weights["citizen_image"] * citizen_score, 1),
            "Satellite NO₂": round(self.weights["satellite_no2"] * sat_score, 1),
            "Traffic Congestion": round(self.weights["traffic_density"] * traffic_score, 1),
            "Weather / Stagnation": round(self.weights["meteorology"] * met_score, 1)
        }

        return {
            "risk_score": risk_score,
            "classification": classification,
            "color": color,
            "badge": badge,
            "sub_scores": {
                "sensor": round(sensor_score, 1),
                "citizen": round(citizen_score, 1),
                "satellite": round(sat_score, 1),
                "traffic": round(traffic_score, 1),
                "meteorology": round(met_score, 1)
            },
            "contributions": contributions
        }

    def generate_fusion_breakdown_chart(self, fusion_result):
        """
        Generate Plotly Horizontal Bar / Radar breakdown chart for Explainable Multimodal AI.
        """
        contribs = fusion_result["contributions"]
        categories = list(contribs.keys())
        values = list(contribs.values())

        fig = go.Figure(go.Bar(
            x=values,
            y=categories,
            orientation='h',
            marker=dict(
                color=['#38bdf8', '#818cf8', '#ec4899', '#f59e0b', '#10b981'],
                line=dict(color='rgba(255,255,255,0.2)', width=1)
            ),
            text=[f"{v:.1f} pts" for v in values],
            textposition='auto',
            textfont=dict(color='white', size=12)
        ))

        fig.update_layout(
            title=dict(
                text=f"Multimodal Risk Contribution Breakdown (Total: {fusion_result['risk_score']} / 100)",
                font=dict(color='white', size=14)
            ),
            height=260,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cbd5e1'),
            margin=dict(l=140, r=20, t=40, b=20),
            xaxis=dict(showgrid=True, gridcolor='#334155', range=[0, 35], title="Points Contributed"),
            yaxis=dict(showgrid=False)
        )
        return fig


# Global instance
fusion_engine = MultimodalFusionEngine()
