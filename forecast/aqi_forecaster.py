# -*- coding: utf-8 -*-
"""
AirGuard AI — 24-Hour AQI Forecast Engine
==========================================
Predicts air quality spikes over the next 24 hours using Random Forest Regression,
incorporating ground PM2.5, PM10, meteorological features, traffic density,
and satellite NO2 column density. Computes 95% confidence intervals.
"""

import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor


class AQIForecastEngine:
    """
    24-Hour Predictive Engine with Confidence Intervals.
    Calculates 24-hour AQI numerical trajectory and confidence upper/lower bounds.
    """

    def __init__(self):
        # Initialize internal lightweight RandomForestRegressor model
        self.model = RandomForestRegressor(n_estimators=40, max_depth=8, random_state=42)
        self._is_trained = False
        self._train_dummy_data()

    def _train_dummy_data(self):
        """Fit model on synthetic multi-modal historical features."""
        np.random.seed(42)
        N = 300
        pm25 = np.random.uniform(20, 180, N)
        pm10 = pm25 * np.random.uniform(1.4, 2.1, N)
        temp = np.random.uniform(20, 35, N)
        humidity = np.random.uniform(40, 85, N)
        wind = np.random.uniform(3, 18, N)
        traffic = np.random.uniform(30, 95, N)
        sat_no2 = np.random.uniform(40, 220, N)

        # Target: AQI after 24 hours
        y = 0.55 * pm25 + 0.20 * pm10 + 0.15 * sat_no2 + 0.10 * traffic - 0.8 * wind + np.random.normal(0, 8, N)
        y = np.clip(y, 15, 380)

        X = np.column_stack([pm25, pm10, temp, humidity, wind, traffic, sat_no2])
        self.model.fit(X, y)
        self._is_trained = True

    def predict_24h_aqi(self, pm25=75.0, pm10=130.0, temp=28.0, humidity=60.0, wind=10.0, traffic=65.0, sat_no2=130.0):
        """
        Predict 24-Hour future AQI trajectory & confidence bounds.
        Returns dict containing:
        - target_aqi_24h (float)
        - lower_bound_95 (float)
        - upper_bound_95 (float)
        - category (str)
        - hours_timeline (list)
        - hourly_predictions (list)
        - upper_curve (list)
        - lower_curve (list)
        """
        X_input = np.array([[pm25, pm10, temp, humidity, wind, traffic, sat_no2]])
        
        # Extract predictions from individual tree estimators for variance / CI computation
        tree_preds = [tree.predict(X_input)[0] for tree in self.model.estimators_]
        mean_pred = float(np.mean(tree_preds))
        std_pred = float(np.std(tree_preds))
        
        # 95% Confidence Interval (1.96 * std)
        ci_half = max(8.0, 1.96 * std_pred)
        lower_bound = max(10.0, mean_pred - ci_half)
        upper_bound = mean_pred + ci_half

        # Construct 24-hour timeline (hourly points from t=0 to t=24h)
        now = datetime.datetime.now()
        hours_timeline = [(now + datetime.timedelta(hours=h)).strftime("%H:00") for h in range(25)]
        
        # Interpolate diurnal curve (traffic peak around 9am and 7pm)
        current_aqi = pm25 * 1.1 # Rough current AQI scale
        hourly_preds = []
        upper_curve = []
        lower_curve = []

        for h in range(25):
            frac = h / 24.0
            # Diurnal fluctuation factor
            diurnal = 1.0 + 0.12 * np.sin(frac * 2 * np.pi - 1.2)
            val = (current_aqi * (1.0 - frac) + mean_pred * frac) * diurnal
            ub = val + (ci_half * (0.3 + 0.7 * frac))
            lb = max(10.0, val - (ci_half * (0.3 + 0.7 * frac)))

            hourly_preds.append(round(float(val), 1))
            upper_curve.append(round(float(ub), 1))
            lower_curve.append(round(float(lb), 1))

        # Categorize 24h predicted AQI
        pred_val = hourly_preds[-1]
        if pred_val <= 50: cat = "Good"
        elif pred_val <= 100: cat = "Moderate"
        elif pred_val <= 200: cat = "Unhealthy for Sensitive Groups"
        elif pred_val <= 300: cat = "Severe / Unhealthy"
        else: cat = "Hazardous"

        return {
            "predicted_aqi_24h": round(pred_val, 1),
            "lower_bound_95": round(lower_bound, 1),
            "upper_bound_95": round(upper_bound, 1),
            "confidence_margin": round(ci_half, 1),
            "category": cat,
            "hours_timeline": hours_timeline,
            "hourly_predictions": hourly_preds,
            "upper_curve": upper_curve,
            "lower_curve": lower_curve
        }

    def render_forecast_chart(self, forecast_data):
        """
        Generate interactive Plotly line chart with shaded 95% Confidence Interval band.
        """
        x_vals = forecast_data["hours_timeline"]
        y_vals = forecast_data["hourly_predictions"]
        y_upper = forecast_data["upper_curve"]
        y_lower = forecast_data["lower_curve"]

        fig = go.Figure()

        # Shaded 95% Confidence Band
        fig.add_trace(go.Scatter(
            x=x_vals + x_vals[::-1],
            y=y_upper + y_lower[::-1],
            fill='toself',
            fillcolor='rgba(56, 189, 248, 0.15)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name='95% Confidence Band'
        ))

        # Main predicted trajectory line
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            name='Predicted AQI Trajectory',
            line=dict(color='#38bdf8', width=3),
            marker=dict(size=5, color='#38bdf8')
        ))

        # Annotate 24h point
        fig.add_annotation(
            x=x_vals[-1],
            y=y_vals[-1],
            text=f"24h AQI: {y_vals[-1]} ({forecast_data['category']})",
            showarrow=True,
            arrowhead=2,
            arrowcolor='#4ade80',
            font=dict(color='#4ade80', size=12, family="Inter")
        )

        fig.update_layout(
            title=dict(
                text=f"📈 24-Hour Predictive AQI Trajectory (Range: {forecast_data['lower_bound_95']} – {forecast_data['upper_bound_95']})",
                font=dict(color='white', size=14)
            ),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cbd5e1'),
            margin=dict(l=40, r=20, t=40, b=30),
            xaxis=dict(showgrid=False, color='#cbd5e1', title="Timeline (Next 24 Hours)"),
            yaxis=dict(showgrid=True, gridcolor='#334155', color='#cbd5e1', title="Predicted AQI Value")
        )

        return fig


# Global instance
forecast_engine = AQIForecastEngine()
