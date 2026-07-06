# -*- coding: utf-8 -*-
"""
AirGuard AI — Citizen Verification Service
============================================
Handles registration, AI verification, status tracking (Pending/Verified/Resolved),
GPS mapping, and persistent storage of citizen-uploaded incident reports.
"""

import os
import csv
import uuid
import datetime
import pandas as pd


class CitizenVerificationService:
    """
    Citizen Incident Verification and Lifecycle Tracker.
    Appends citizen reports to CSV, assigns Reference IDs, AI confidence, and verification status.
    """

    HEADERS = [
        "Reference ID", "Timestamp", "Station", "Incident Type", 
        "File Name", "AI Category", "AI Confidence", "Severity Score", 
        "GPS Coords", "Status"
    ]

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self._ensure_csv()

    def _ensure_csv(self):
        """Ensure destination CSV directory and valid 10-column headers exist."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
        needs_init = False
        if not os.path.exists(self.csv_path):
            needs_init = True
        else:
            # Check if header matches expected 10 columns
            try:
                df_check = pd.read_csv(self.csv_path, nrows=1)
                if len(df_check.columns) < len(self.HEADERS) or "AI Category" not in df_check.columns:
                    needs_init = True
            except Exception:
                needs_init = True

        if needs_init:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)
                # Seed realistic verified sample rows for initial display
                sample_rows = [
                    ["ARG-2026-9B41A", "2026-07-06 10:15:00", "Silk Board, Bengaluru - KSPCB", "Garbage Burning", "incident_smoke_01.jpg", "Garbage Burning", "94.2%", "82 / 100", "12.9172, 77.6228", "Verified"],
                    ["ARG-2026-3C82D", "2026-07-06 09:40:00", "Peenya, Bengaluru - KSPCB", "Industrial Smoke", "factory_plume.jpg", "Industrial Smoke", "88.5%", "78 / 100", "13.0285, 77.5197", "Verified"],
                    ["ARG-2026-7F19E", "2026-07-06 08:20:00", "Sanegurava Halli, Bengaluru - KSPCB", "Construction Dust", "site_dust.jpg", "Construction Dust", "91.0%", "65 / 100", "12.9860, 77.5400", "Resolved"],
                    ["ARG-2026-1E50F", "2026-07-06 07:55:00", "BTM Layout, Bengaluru - CPCB", "Vehicle Exhaust", "road_haze.jpg", "Road Dust", "76.4%", "54 / 100", "12.9166, 77.6101", "Pending"]
                ]
                for r in sample_rows:
                    writer.writerow(r)

    def register_report(self, incident_type, station_name, file_name, cv_result, lat=12.9716, lon=77.5946):
        """
        Register a citizen incident report with AI vision verification.
        """
        self._ensure_csv()
        ref_id = f"ARG-2026-{str(uuid.uuid4())[:5].upper()}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        category = cv_result.get("category", incident_type or "Garbage Burning")
        
        raw_conf = cv_result.get('confidence', 0.85)
        if isinstance(raw_conf, (int, float)):
            confidence_str = f"{raw_conf * 100:.1f}%" if raw_conf <= 1.0 else f"{raw_conf:.1f}%"
            conf_val = raw_conf if raw_conf <= 1.0 else raw_conf / 100.0
        else:
            confidence_str = str(raw_conf)
            conf_val = 0.85

        raw_sev = cv_result.get("severity_score", 75)
        severity_str = f"{raw_sev} / 100" if isinstance(raw_sev, (int, float)) else str(raw_sev)

        gps_str = f"{lat:.4f}, {lon:.4f}"
        status = "Verified" if conf_val >= 0.70 else "Pending"

        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                ref_id, timestamp, station_name, incident_type,
                file_name or "Citizen_Photo.jpg", category, confidence_str,
                severity_str, gps_str, status
            ])

        return {
            "ref_id": ref_id,
            "timestamp": timestamp,
            "station": station_name,
            "incident_type": incident_type,
            "ai_category": category,
            "confidence": confidence_str,
            "severity": severity_str,
            "gps": gps_str,
            "status": status,
            "explanation": cv_result.get("explanation", "")
        }

    def load_reports_df(self):
        """Load registered reports into DataFrame ensuring correct columns."""
        self._ensure_csv()
        try:
            df = pd.read_csv(self.csv_path)
            for col in self.HEADERS:
                if col not in df.columns:
                    df[col] = "N/A"
            return df
        except Exception:
            return pd.DataFrame(columns=self.HEADERS)

    def get_citizen_verification_table_html(self):
        """Render glassmorphism status table for citizen reports dashboard."""
        df = self.load_reports_df()
        
        if df.empty:
            rows_html = '<tr><td colspan="8" style="padding:15px; text-align:center; color:#94a3b8;">No reports logged yet.</td></tr>'
        else:
            rows_html = ""
            for _, r in df.tail(10).iloc[::-1].iterrows():
                status = str(r.get('Status', 'Verified'))
                status_color = "#22c55e" if status == "Verified" else ("#38bdf8" if status == "Resolved" else "#eab308")
                
                ref_id = str(r.get('Reference ID', 'N/A'))
                ts = str(r.get('Timestamp', 'N/A'))
                stn = str(r.get('Station', 'N/A'))
                inc_type = str(r.get('Incident Type', 'N/A'))
                ai_cat = str(r.get('AI Category', 'N/A'))
                conf = str(r.get('AI Confidence', 'N/A'))
                sev = str(r.get('Severity Score', 'N/A'))

                rows_html += f"""
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px; color: #38bdf8; font-weight: bold;">{ref_id}</td>
                    <td style="padding: 10px; color: #cbd5e1;">{ts}</td>
                    <td style="padding: 10px; color: #f8fafc;">{stn}</td>
                    <td style="padding: 10px; color: #f8fafc;">{inc_type}</td>
                    <td style="padding: 10px; color: #818cf8; font-weight: 600;">{ai_cat}</td>
                    <td style="padding: 10px; color: #4ade80; font-weight: 600;">{conf}</td>
                    <td style="padding: 10px; color: #ef4444; font-weight: bold;">{sev}</td>
                    <td style="padding: 10px;"><span style="background:{status_color}20; color:{status_color}; border:1px solid {status_color}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:11px;">{status}</span></td>
                </tr>
                """

        return f"""
        <div class="dark-card" style="margin-top: 20px;">
            <h3 style="color: white; margin: 0 0 16px 0; font-weight: bold; display: flex; align-items: center; gap: 8px;">
                <span>📱</span> Live Citizen Verification Status Tracker
            </h3>
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                <thead>
                    <tr style="border-bottom: 2px solid #475569; color: #94a3b8; font-weight: bold; text-transform: uppercase; font-size: 11px;">
                        <th style="padding: 10px;">Reference ID</th>
                        <th style="padding: 10px;">Timestamp</th>
                        <th style="padding: 10px;">Station</th>
                        <th style="padding: 10px;">Reported Type</th>
                        <th style="padding: 10px;">AI CV Classification</th>
                        <th style="padding: 10px;">AI Confidence</th>
                        <th style="padding: 10px;">Severity</th>
                        <th style="padding: 10px;">Verification Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """


# Global instance initialized with default reports path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_CSV = os.path.join(BASE_DIR, 'data', 'processed', 'reports.csv')
citizen_service = CitizenVerificationService(REPORT_CSV)
