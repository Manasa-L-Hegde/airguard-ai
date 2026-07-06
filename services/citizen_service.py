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

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self._ensure_csv()

    def _ensure_csv(self):
        """Ensure destination CSV directory and headers exist."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Reference ID", "Timestamp", "Station", "Incident Type", 
                    "File Name", "AI Category", "AI Confidence", "Severity Score", 
                    "GPS Coords", "Status"
                ])

    def register_report(self, incident_type, station_name, file_name, cv_result, lat=12.9716, lon=77.5946):
        """
        Register a citizen incident report with AI vision verification.
        """
        ref_id = f"ARG-2026-{str(uuid.uuid4())[:5].upper()}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        category = cv_result.get("category", incident_type or "Garbage Burning")
        confidence = f"{cv_result.get('confidence', 0.85)*100:.1f}%"
        severity = cv_result.get("severity_score", 75)
        gps_str = f"{lat:.4f}, {lon:.4f}"
        status = "Verified" if cv_result.get("confidence", 0.8) > 0.70 else "Pending"

        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                ref_id, timestamp, station_name, incident_type,
                file_name or "No Image Attached", category, confidence,
                severity, gps_str, status
            ])

        return {
            "ref_id": ref_id,
            "timestamp": timestamp,
            "station": station_name,
            "incident_type": incident_type,
            "ai_category": category,
            "confidence": confidence,
            "severity": severity,
            "gps": gps_str,
            "status": status,
            "explanation": cv_result.get("explanation", "")
        }

    def load_reports_df(self):
        """Load registered reports into DataFrame."""
        if not os.path.exists(self.csv_path):
            return pd.DataFrame()
        try:
            return pd.read_csv(self.csv_path)
        except Exception:
            return pd.DataFrame()

    def get_citizen_verification_table_html(self):
        """Render glassmorphism status table for citizen reports dashboard."""
        df = self.load_reports_df()
        
        if df.empty:
            # Provide sample verified reports if CSV is currently empty
            sample_rows = [
                ("ARG-2026-9B41A", "2026-07-06 10:15", "Silk Board", "Garbage Burning", "Garbage Burning", "94.2%", "82", "Verified"),
                ("ARG-2026-3C82D", "2026-07-06 09:40", "Peenya", "Industrial Smoke", "Industrial Smoke", "88.5%", "78", "Verified"),
                ("ARG-2026-7F19E", "2026-07-06 08:20", "Sanegurava Halli", "Construction Dust", "Construction Dust", "91.0%", "65", "Resolved"),
                ("ARG-2026-1E50F", "2026-07-06 07:55", "BTM Layout", "Vehicle Exhaust", "Road Dust", "76.4%", "54", "Pending")
            ]
            rows_html = ""
            for r in sample_rows:
                status_color = "#22c55e" if r[7] == "Verified" else ("#38bdf8" if r[7] == "Resolved" else "#eab308")
                rows_html += f"""
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px; color: #38bdf8; font-weight: bold;">{r[0]}</td>
                    <td style="padding: 10px; color: #cbd5e1;">{r[1]}</td>
                    <td style="padding: 10px; color: #f8fafc;">{r[2]}</td>
                    <td style="padding: 10px; color: #f8fafc;">{r[3]}</td>
                    <td style="padding: 10px; color: #818cf8;">{r[4]}</td>
                    <td style="padding: 10px; color: #4ade80;">{r[5]}</td>
                    <td style="padding: 10px; color: #ef4444; font-weight: bold;">{r[6]}</td>
                    <td style="padding: 10px;"><span style="background:{status_color}20; color:{status_color}; border:1px solid {status_color}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:11px;">{r[7]}</span></td>
                </tr>
                """
        else:
            rows_html = ""
            for _, r in df.tail(10).iloc[::-1].iterrows():
                status = str(r.get('Status', 'Verified'))
                status_color = "#22c55e" if status == "Verified" else ("#38bdf8" if status == "Resolved" else "#eab308")
                rows_html += f"""
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px; color: #38bdf8; font-weight: bold;">{r.get('Reference ID', 'N/A')}</td>
                    <td style="padding: 10px; color: #cbd5e1;">{r.get('Timestamp', 'N/A')}</td>
                    <td style="padding: 10px; color: #f8fafc;">{r.get('Station', 'N/A')}</td>
                    <td style="padding: 10px; color: #f8fafc;">{r.get('Incident Type', 'N/A')}</td>
                    <td style="padding: 10px; color: #818cf8;">{r.get('AI Category', 'N/A')}</td>
                    <td style="padding: 10px; color: #4ade80;">{r.get('AI Confidence', 'N/A')}</td>
                    <td style="padding: 10px; color: #ef4444; font-weight: bold;">{r.get('Severity Score', 'N/A')}</td>
                    <td style="padding: 10px;"><span style="background:{status_color}20; color:{status_color}; border:1px solid {status_color}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:11px;">{status}</span></td>
                </tr>
                """

        return f"""
        <div class="dark-card" style="margin-top: 20px;">
            <h3 style="color: white; margin: 0 0 16px 0; font-weight: bold;">📱 Live Citizen Verification Status Tracker</h3>
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
