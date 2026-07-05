import os
import pandas as pd
from google import genai
import time

# INSTRUCTIONS FOR GETTING A FREE GEMINI API KEY:
# 1. Go to Google AI Studio: https://aistudio.google.com/
# 2. Sign in with your Google account.
# 3. Click "Create API key" and copy your new key.
# 4. Set it as an environment variable before running this script or app.py:
#    Linux/Mac: export GEMINI_API_KEY="your_api_key_here"
#    Windows CMD: set GEMINI_API_KEY="your_api_key_here"
#    Windows PowerShell: $env:GEMINI_API_KEY="your_api_key_here"

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set. Using fallback recommendations.")
        client = None
    else:
        client = genai.Client(api_key=api_key)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hotspot_path = os.path.join(base_dir, 'data', 'processed', 'hotspot_clusters.csv')
    out_path = os.path.join(base_dir, 'data', 'processed', 'policy_recommendations.csv')

    if not os.path.exists(hotspot_path):
        print(f"Error: {hotspot_path} not found.")
        return

    hotspot_df = pd.read_csv(hotspot_path)

    # Prepare list of hotspots
    hotspots = []
    for _, row in hotspot_df.iterrows():
        hotspots.append({
            'cluster_id': f"Cluster {int(row['cluster_id'])}",
            'wards': row['wards'],
            'avg_severity': row['avg_severity'],
            'avg_pm25': row['avg_pm25'],
            'avg_pm10': row['avg_pm10'] if 'avg_pm10' in row and pd.notna(row['avg_pm10']) else 'N/A',
            'stations': row['stations']
        })

    # Add 4 standalone high-priority stations
    standalone = [
        {
            'cluster_id': 'Standalone - Kasturi Nagar',
            'wards': 'Vijinapura',
            'avg_severity': 98.2,
            'avg_pm25': 'N/A',
            'avg_pm10': 'N/A',
            'stations': 'Kasturi Nagar'
        },
        {
            'cluster_id': 'Standalone - RVCE Mailasandra',
            'wards': 'Bande Mutt',
            'avg_severity': 96.6,
            'avg_pm25': 'N/A',
            'avg_pm10': 'N/A',
            'stations': 'RVCE Mailasandra'
        },
        {
            'cluster_id': 'Standalone - Kadubeesanahalli',
            'wards': 'Marathahalli',
            'avg_severity': 72.8,
            'avg_pm25': 'N/A',
            'avg_pm10': 'N/A',
            'stations': 'Kadubeesanahalli'
        },
        {
            'cluster_id': 'Standalone - Jigani',
            'wards': 'Kalena Agrahara',
            'avg_severity': 72.2,
            'avg_pm25': 'N/A',
            'avg_pm10': 'N/A',
            'stations': 'Jigani'
        }
    ]
    hotspots.extend(standalone)

    results = []

    for hs in hotspots:
        print(f"Generating recommendation for {hs['cluster_id']}...")
        prompt = f"""
You are an urban air quality expert advising an MP's office in Bengaluru.
Based on the following pollution hotspot data, provide a 2-3 sentence practical policy recommendation.
State what likely causes the pollution (e.g. traffic, industrial, construction) and what intervention to prioritize (e.g. traffic signal timing, dust suppression, monitoring frequency).
Make the recommendation highly actionable and specific to the given wards/stations if possible. Do not use markdown formatting like asterisks or bullet points.

Hotspot Details:
- Cluster/Station: {hs['cluster_id']}
- Wards involved: {hs['wards']}
- Included Stations: {hs['stations']}
- Average Severity Score: {hs['avg_severity']}
- Average PM2.5: {hs['avg_pm25']}
- Average PM10: {hs['avg_pm10']}
"""
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            recommendation = response.text.strip().replace('\n', ' ')
        except Exception as e:
            print(f"Error generating for {hs['cluster_id']}: {e}")
            recommendation = (
                "Likely pollution sources include heavy traffic, construction activity "
                "and industrial emissions. Increase roadside AQI monitoring, deploy "
                "water-mist cannons during peak hours, enforce dust suppression at "
                "construction sites, and conduct periodic industrial emission inspections."
            )
            
        results.append({
            'cluster_id': hs['cluster_id'],
            'wards': hs['wards'],
            'recommendation_text': recommendation
        })
        time.sleep(1) # simple rate limit to avoid 429

    res_df = pd.DataFrame(results)
    res_df.to_csv(out_path, index=False)
    print(f"Saved recommendations to {out_path}")

if __name__ == '__main__':
    main()
