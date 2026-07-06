# -*- coding: utf-8 -*-
"""
AirGuard AI — Municipal Alert Engine & Resource Deployment Simulator
=====================================================================
Triggers automated civic response alerts when Risk Score > 80 or severe hotspots occur.
Provides action plans, affected population estimates, expected AQI reduction %,
budget calculations, and a simulated resource dispatch system for city officials.
"""

import datetime


class MunicipalAlertEngine:
    """
    Municipal Alert Engine generating targeted civic response cards
    and tracking active resource dispatches across Bengaluru wards.
    """

    def __init__(self):
        self.dispatch_history = [
            {
                "dispatch_id": "DSP-2026-001",
                "ward": "Peenya Industrial Area",
                "resource": "2x Water Mist Cannons + Mobile Inspection Wing",
                "status": "In Progress (Deployed 35 mins ago)",
                "est_completion": "Today 16:00",
                "budget": "₹3.8 Lakhs"
            },
            {
                "dispatch_id": "DSP-2026-002",
                "ward": "Silk Board Junction",
                "resource": "3x Mechanical Night Sweepers + Anti-Smog Gun",
                "status": "En Route",
                "est_completion": "Today 18:30",
                "budget": "₹4.5 Lakhs"
            }
        ]

    def evaluate_alert(self, ward_name="Peenya Industrial Area", risk_score=84.5, incident_type="Garbage Burning"):
        """
        Evaluate pollution risk score and generate structured municipal alert card.
        """
        is_triggered = risk_score > 75.0 or "Burning" in incident_type or "Industrial" in incident_type
        
        priority = "CRITICAL" if risk_score >= 80.0 else ("HIGH" if risk_score >= 65.0 else "MODERATE")
        priority_color = "#ef4444" if priority == "CRITICAL" else ("#f97316" if priority == "HIGH" else "#eab308")

        # Dynamic Reason construction based on modalities
        reason = f"Unmitigated {incident_type.lower()} detected in {ward_name} with rising PM2.5 levels and high satellite NO₂ column density anomaly (Risk Score: {risk_score}/100)."

        # Action plan recommendations
        if "Burning" in incident_type:
            actions = [
                "Deploy water mist cannon to suppress ambient particulates",
                "Dispatch BBMP Sanitation Rapid Response team for immediate fire suppression & clearing",
                "Issue ward health notice for vulnerable populations (pediatric & elderly)"
            ]
            dept = "BBMP Solid Waste Management & Sanitation Wing"
            budget = "₹2.8 Lakhs"
            reduction = "24%"
            pop_affected = "48,500 Citizens"
        elif "Industrial" in incident_type or "Peenya" in ward_name:
            actions = [
                "Mandate immediate stack emission compliance check on active industrial units",
                "Dispatch KSPCB Regional Enforcement Inspectorate",
                "Restrict heavy diesel commercial transport during peak thermal inversion hours"
            ]
            dept = "KSPCB Regional Inspectorate & Traffic Police"
            budget = "₹4.2 Lakhs"
            reduction = "18%"
            pop_affected = "62,000 Citizens"
        else:
            actions = [
                "Deploy anti-smog water spray cannons at major traffic intersections",
                "Enforce construction site dust suppression tarpaulins & water sprinkling",
                "Deploy mechanical road sweepers during night non-peak hours"
            ]
            dept = "Bengaluru Traffic Police & BBMP Works Dept"
            budget = "₹3.5 Lakhs"
            reduction = "15%"
            pop_affected = "55,000 Citizens"

        alert_payload = {
            "is_triggered": is_triggered,
            "priority": priority,
            "priority_color": priority_color,
            "ward_name": ward_name,
            "risk_score": risk_score,
            "reason": reason,
            "actions": actions,
            "responsible_dept": dept,
            "affected_population": pop_affected,
            "expected_aqi_reduction": reduction,
            "estimated_budget": budget,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return alert_payload

    def dispatch_resource(self, ward_name, resource_type):
        """Simulate dispatching a municipal response resource."""
        dispatch_id = f"DSP-2026-{len(self.dispatch_history) + 1:03d}"
        entry = {
            "dispatch_id": dispatch_id,
            "ward": ward_name,
            "resource": resource_type,
            "status": "Dispatched (Just Now)",
            "est_completion": "Within 2 Hours",
            "budget": "₹3.2 Lakhs"
        }
        self.dispatch_history.insert(0, entry)
        return entry

    def render_alert_card_html(self, alert_payload):
        """
        Generate glassmorphism HTML layout for Municipal Alert response card.
        """
        if not alert_payload["is_triggered"]:
            return """
            <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid #22c55e; border-radius: 12px; padding: 20px;">
                <h4 style="margin: 0; color: #4ade80; font-size: 16px;">🟢 Normal Municipal Operations</h4>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 13px;">No critical pollution alerts triggered for this ward. Risk Score is within acceptable parameters.</p>
            </div>
            """

        actions_html = "".join([f"<li style='margin-bottom:6px; color:#f8fafc;'>{act}</li>" for act in alert_payload["actions"]])

        card_html = f"""
        <div style="background: rgba(30, 41, 59, 0.8); border: 2px solid {alert_payload['priority_color']}; border-radius: 12px; padding: 20px; box-shadow: 0 0 15px rgba(239,68,68,0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">🚨</span>
                    <span style="font-size: 16px; font-weight: bold; color: white;">AUTOMATED MUNICIPAL ALERT ENGINE</span>
                </div>
                <span style="background: {alert_payload['priority_color']}; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 12px; text-transform: uppercase;">
                    PRIORITY: {alert_payload['priority']}
                </span>
            </div>

            <div style="margin-bottom: 14px;">
                <div style="color: #94a3b8; font-size: 11px; text-transform: uppercase;">Alert Cause / Driver</div>
                <p style="margin: 4px 0 0 0; color: #fca5a5; font-size: 14px; font-weight: 500;">{alert_payload['reason']}</p>
            </div>

            <div style="margin-bottom: 14px; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px;">
                <div style="color: #38bdf8; font-size: 12px; font-weight: bold; text-transform: uppercase; margin-bottom: 6px;">Recommended Action Protocol</div>
                <ul style="margin: 0; padding-left: 18px; font-size: 13px;">
                    {actions_html}
                </ul>
            </div>

            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 8px; font-size: 12px;">
                <div>
                    <span style="color: #94a3b8; text-transform: uppercase; font-size: 10px;">Affected Population</span>
                    <div style="color: white; font-weight: bold; font-size: 13px;">{alert_payload['affected_population']}</div>
                </div>
                <div>
                    <span style="color: #94a3b8; text-transform: uppercase; font-size: 10px;">Est. AQI Reduction</span>
                    <div style="color: #4ade80; font-weight: bold; font-size: 13px;">📉 {alert_payload['expected_aqi_reduction']}</div>
                </div>
                <div>
                    <span style="color: #94a3b8; text-transform: uppercase; font-size: 10px;">Cleanup Budget</span>
                    <div style="color: #fbbf24; font-weight: bold; font-size: 13px;">{alert_payload['estimated_budget']}</div>
                </div>
            </div>

            <div style="margin-top: 12px; text-align: right; color: #64748b; font-size: 11px;">
                Responsible Authority: <b style="color: #cbd5e1;">{alert_payload['responsible_dept']}</b>
            </div>
        </div>
        """

        return card_html


# Global instance
alert_engine = MunicipalAlertEngine()
