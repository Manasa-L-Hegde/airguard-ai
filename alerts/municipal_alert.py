# -*- coding: utf-8 -*-
"""
AirGuard AI — Municipal Alert Engine & Resource Deployment Simulator
=====================================================================
Triggers automated civic response alerts when Risk Score > 75 or severe hotspots occur.
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
                "budget": "₹3.8 Lakhs (Estimated)"
            },
            {
                "dispatch_id": "DSP-2026-002",
                "ward": "Silk Board Junction",
                "resource": "3x Mechanical Night Sweepers + Anti-Smog Gun",
                "status": "En Route",
                "est_completion": "Today 18:30",
                "budget": "₹4.5 Lakhs (Estimated)"
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

        # Structured Action Item Cards with stars, cost, and AQI impact
        if "Burning" in incident_type:
            action_items = [
                {
                    "title": "Immediate Water Mist Cannon Deployment",
                    "desc": "Deploy 2x mobile high-pressure water mist cannons to suppress particulate matter & smoke plumes.",
                    "stars": "⭐⭐⭐⭐⭐ Critical",
                    "cost": "₹1.2 Lakhs (Estimated)",
                    "impact": "-14% PM2.5 (Estimated)",
                    "dept": "BBMP Solid Waste & Sanitation Wing"
                },
                {
                    "title": "Sanitation Clearing & Fire Containment",
                    "desc": "Dispatch BBMP Sanitation Rapid Response team for immediate fire suppression and waste clearing.",
                    "stars": "⭐⭐⭐⭐ High Priority",
                    "cost": "₹0.8 Lakhs (Estimated)",
                    "impact": "-6% PM2.5 (Estimated)",
                    "dept": "BBMP Sanitation Wing"
                },
                {
                    "title": "Ward Health Advisory & Sensor Placement",
                    "desc": "Issue automated ward health warning for sensitive groups & deploy micro-sensor for tracking.",
                    "stars": "⭐⭐⭐ Moderate",
                    "cost": "₹0.5 Lakhs (Estimated)",
                    "impact": "-4% Exposure (Estimated)",
                    "dept": "Health & Environment Directorate"
                }
            ]
            dept = "BBMP Solid Waste Management & Sanitation Wing"
            budget = "₹2.5 Lakhs (Estimated)"
            reduction = "-24% PM2.5 (Estimated)"
            pop_affected = "48,500 Citizens (Estimated)"
        elif "Industrial" in incident_type or "Peenya" in ward_name:
            action_items = [
                {
                    "title": "Stack Emission Inspection & Compliance Check",
                    "desc": "Mandate immediate stack emission compliance check on active industrial units in Peenya corridor.",
                    "stars": "⭐⭐⭐⭐⭐ Critical",
                    "cost": "₹2.0 Lakhs (Estimated)",
                    "impact": "-10% NO₂ / PM (Estimated)",
                    "dept": "KSPCB Regional Enforcement Inspectorate"
                },
                {
                    "title": "Heavy Diesel Commercial Transport Restriction",
                    "desc": "Restrict heavy diesel freight transport during peak thermal inversion hours (06:00 - 10:00).",
                    "stars": "⭐⭐⭐⭐ High Priority",
                    "cost": "₹1.2 Lakhs (Estimated)",
                    "impact": "-5% PM2.5 (Estimated)",
                    "dept": "Bengaluru Traffic Police"
                },
                {
                    "title": "Industrial Buffer Dust Suppression Spraying",
                    "desc": "Deploy misting vehicles along industrial boundary roads and unpaved buffer zones.",
                    "stars": "⭐⭐⭐ Moderate",
                    "cost": "₹1.0 Lakhs (Estimated)",
                    "impact": "-3% PM2.5 (Estimated)",
                    "dept": "BBMP Works Dept"
                }
            ]
            dept = "KSPCB Regional Inspectorate & Traffic Police"
            budget = "₹4.2 Lakhs (Estimated)"
            reduction = "-18% PM2.5 (Estimated)"
            pop_affected = "62,000 Citizens (Estimated)"
        else:
            action_items = [
                {
                    "title": "Intersection Anti-Smog Spray Operations",
                    "desc": "Deploy anti-smog water spray cannons at major traffic bottlenecks and intersections.",
                    "stars": "⭐⭐⭐⭐ High Priority",
                    "cost": "₹1.8 Lakhs (Estimated)",
                    "impact": "-8% PM2.5 (Estimated)",
                    "dept": "Bengaluru Traffic Police"
                },
                {
                    "title": "Construction Site Dust Cover Enforcement",
                    "desc": "Enforce mandatory construction dust suppression tarpaulins & perimeter water sprinkling.",
                    "stars": "⭐⭐⭐⭐ High Priority",
                    "cost": "₹1.0 Lakhs (Estimated)",
                    "impact": "-4% Dust (Estimated)",
                    "dept": "BBMP Works Dept"
                },
                {
                    "title": "Nighttime Mechanical Road Sweeping",
                    "desc": "Deploy heavy mechanical road sweepers during night non-peak hours to clear road dust.",
                    "stars": "⭐⭐⭐ Moderate",
                    "cost": "₹0.7 Lakhs (Estimated)",
                    "impact": "-3% Road Dust (Estimated)",
                    "dept": "BBMP Sanitation Wing"
                }
            ]
            dept = "Bengaluru Traffic Police & BBMP Works Dept"
            budget = "₹3.5 Lakhs (Estimated)"
            reduction = "-15% PM2.5 (Estimated)"
            pop_affected = "55,000 Citizens (Estimated)"

        alert_payload = {
            "is_triggered": is_triggered,
            "priority": priority,
            "priority_color": priority_color,
            "ward_name": ward_name,
            "risk_score": risk_score,
            "reason": reason,
            "action_items": action_items,
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
            "budget": "₹3.2 Lakhs (Estimated)"
        }
        self.dispatch_history.insert(0, entry)
        return entry

    def render_alert_card_html(self, alert_payload):
        """
        Generate HTML layout for High Pollution Alert Banner and Municipal Decision Support Action Cards.
        """
        if not alert_payload["is_triggered"]:
            return """
            <div style="background: rgba(30, 41, 59, 0.75); border: 1px solid #22c55e; border-left: 5px solid #22c55e; border-radius: 12px; padding: 18px; display: flex; align-items: center; gap: 14px;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0;">
                    🟢
                </div>
                <div>
                    <h4 style="margin: 0; color: #4ade80; font-size: 15px; font-weight: 700;">Normal Municipal Operations</h4>
                    <p style="margin: 4px 0 0 0; color: #cbd5e1; font-size: 13px;">No critical pollution alerts triggered for this ward. Risk Score is within acceptable parameters.</p>
                </div>
            </div>
            """

        # Generate action item cards HTML
        action_cards_html = ""
        for item in alert_payload["action_items"]:
            action_cards_html += f"""
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-left: 4px solid {alert_payload['priority_color']}; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 11px; font-weight: 700; color: #fbbf24;">{item['stars']}</span>
                        <span style="font-size: 10px; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">{item['dept']}</span>
                    </div>
                    <h5 style="color: #f8fafc; margin: 0 0 6px 0; font-size: 14px; font-weight: 700;">{item['title']}</h5>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 0 0 10px 0; line-height: 1.4;">{item['desc']}</p>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 8px; font-size: 11px;">
                    <div>
                        <span style="color: #94a3b8;">Cost: </span>
                        <b style="color: #fbbf24;">{item['cost']}</b>
                    </div>
                    <div>
                        <span style="color: #94a3b8;">AQI Impact: </span>
                        <b style="color: #4ade80;">{item['impact']}</b>
                    </div>
                </div>
            </div>
            """

        card_html = f"""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(239, 68, 68, 0.08) 100%); border: 1px solid rgba(239, 68, 68, 0.4); border-left: 5px solid {alert_payload['priority_color']}; border-radius: 12px; padding: 20px; box-shadow: 0 4px 20px rgba(239,68,68,0.15); margin-top: 16px;">
            
            <!-- High Pollution Alert Banner Header -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 50%; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0;">
                        🚨
                    </div>
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <h4 style="margin: 0; color: #f8fafc; font-size: 16px; font-weight: 800;">HIGH POLLUTION ALERT BANNER</h4>
                            <span style="background: {alert_payload['priority_color']}; color: white; padding: 2px 8px; border-radius: 6px; font-weight: bold; font-size: 11px; text-transform: uppercase;">
                                {alert_payload['priority']}
                            </span>
                        </div>
                        <p style="margin: 2px 0 0 0; color: #fca5a5; font-size: 13px; font-weight: 500;">{alert_payload['reason']}</p>
                    </div>
                </div>
            </div>

            <!-- Municipal Decision Support Recommendations Section Header -->
            <div style="margin-top: 16px; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <h5 style="color: #38bdf8; margin: 0; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">
                        <span>🏛️</span> Municipal Decision Support — Action Recommendations
                    </h5>
                    <span style="font-size: 11px; color: #cbd5e1;">Target: <b>{alert_payload['ward_name']}</b></span>
                </div>
            </div>

            <!-- Grid of Action Recommendation Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px;">
                {action_cards_html}
            </div>

            <!-- Summary Bar -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255,255,255,0.08); padding: 12px; border-radius: 10px; margin-top: 14px; font-size: 12px;">
                <div>
                    <span style="color: #94a3b8; text-transform: uppercase; font-size: 10px; font-weight: 600;">Affected Population</span>
                    <div style="color: white; font-weight: bold; font-size: 13px; margin-top: 2px;">{alert_payload['affected_population']}</div>
                </div>
                <div>
                    <span style="color: #94a3b8; text-transform: uppercase; font-size: 10px; font-weight: 600;">Total Est. AQI Reduction</span>
                    <div style="color: #4ade80; font-weight: bold; font-size: 13px; margin-top: 2px;">📉 {alert_payload['expected_aqi_reduction']}</div>
                </div>
                <div>
                    <span style="color: #94a3b8; text-transform: uppercase; font-size: 10px; font-weight: 600;">Total Cleanup Budget</span>
                    <div style="color: #fbbf24; font-weight: bold; font-size: 13px; margin-top: 2px;">{alert_payload['estimated_budget']}</div>
                </div>
            </div>

            <div style="margin-top: 10px; text-align: right; color: #64748b; font-size: 11px;">
                Lead Authority: <b style="color: #cbd5e1;">{alert_payload['responsible_dept']}</b>
            </div>
        </div>
        """

        return card_html


# Global instance
alert_engine = MunicipalAlertEngine()
