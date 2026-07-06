# -*- coding: utf-8 -*-
"""
AirGuard AI — Satellite Imagery & Remote Sensing Service
==========================================================
Integrates satellite remote sensing layer data (Sentinel-5P NO2, MODIS/VIIRS PM2.5,
and Aerosol Optical Depth) for neighbourhood-level pollution mapping across Bengaluru.
"""

import folium
import numpy as np
import pandas as pd


class SatelliteService:
    """
    Service to fetch satellite remote sensing measurements and render map layers.
    Simulates high-resolution Sentinel-5P NO2 tropospheric column density
    and MODIS AOD aerosol index data overlaid on ground coordinates.
    """

    def __init__(self):
        # Coordinates grid covering Bengaluru urban region
        self.grid_bounds = {
            'lat_min': 12.85, 'lat_max': 13.12,
            'lon_min': 77.45, 'lon_max': 77.75
        }

    def generate_satellite_grid(self, n_points=40):
        """
        Generate grid of satellite sensor readings across Bengaluru.
        Simulates Sentinel-5P tropospheric NO2 (umol/m^2) and AOD (0-1).
        """
        np.random.seed(42)
        lats = np.random.uniform(self.grid_bounds['lat_min'], self.grid_bounds['lat_max'], n_points)
        lons = np.random.uniform(self.grid_bounds['lon_min'], self.grid_bounds['lon_max'], n_points)

        satellite_records = []
        for i in range(n_points):
            lat, lon = lats[i], lons[i]
            
            # Hotspot bias near Peenya (13.03, 77.52) and Silk Board (12.91, 77.62)
            dist_peenya = np.sqrt((lat - 13.03)**2 + (lon - 77.52)**2)
            dist_silk = np.sqrt((lat - 12.91)**2 + (lon - 77.62)**2)

            if dist_peenya < 0.05:
                no2_val = float(np.random.uniform(180, 240)) # umol/m^2
                aod_val = float(np.random.uniform(0.75, 0.95))
            elif dist_silk < 0.05:
                no2_val = float(np.random.uniform(160, 210))
                aod_val = float(np.random.uniform(0.70, 0.90))
            else:
                no2_val = float(np.random.uniform(40, 130))
                aod_val = float(np.random.uniform(0.20, 0.65))

            satellite_records.append({
                "pixel_id": f"SAT-S5P-{i+1:03d}",
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "no2_column_density": round(no2_val, 2), # umol/m2
                "aerosol_optical_depth": round(aod_val, 3), # AOD
                "pm25_satellite_est": round(no2_val * 0.55 + aod_val * 60, 1),
                "timestamp": "Live Sentinel-5P Orbit Feed"
            })

        return pd.DataFrame(satellite_records)

    def add_satellite_layers_to_map(self, folium_map):
        """
        Add interactive Sentinel-5P NO2 and AOD overlay circles / heat tiles to a Folium map.
        """
        sat_df = self.generate_satellite_grid(n_points=35)
        
        # Create FeatureGroup for Satellite Sentinel-5P NO2 Layer
        no2_group = folium.FeatureGroup(name="🛰️ Sentinel-5P NO2 Layer", show=True)
        
        for _, row in sat_df.iterrows():
            no2 = row['no2_column_density']
            
            # Color gradient based on NO2 density
            if no2 > 170:
                color = '#dc2626' # Red
                radius = 18
            elif no2 > 120:
                color = '#f97316' # Orange
                radius = 14
            elif no2 > 80:
                color = '#eab308' # Yellow
                radius = 11
            else:
                color = '#38bdf8' # Blue
                radius = 8

            popup_content = f"""
            <div style="font-family:sans-serif; font-size:12px; color:#0f172a; width:200px;">
                <b>🛰️ Sentinel-5P Satellite Pixel</b><br>
                <hr style="margin:4px 0;">
                <b>Pixel ID:</b> {row['pixel_id']}<br>
                <b>NO₂ Density:</b> <b style="color:{color};">{no2} µmol/m²</b><br>
                <b>Aerosol Optical Depth (AOD):</b> {row['aerosol_optical_depth']}<br>
                <b>Est. PM2.5 Surface:</b> {row['pm25_satellite_est']} µg/m³
            </div>
            """

            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=radius,
                color=color,
                weight=1,
                fill=True,
                fill_color=color,
                fill_opacity=0.35,
                popup=folium.Popup(popup_content, max_width=220),
                tooltip=f"Satellite NO₂: {no2} µmol/m²"
            ).add_to(no2_group)

        no2_group.add_to(folium_map)
        return folium_map


# Global instance
satellite_service = SatelliteService()
