import pandas as pd

df = pd.read_csv('data/processed/bengaluru_air_quality_timeseries.csv')
print(f'Rows: {len(df)}')
print(f'Stations: {df["station"].nunique()}')
print('\nFirst 5 stations:')
for s in df['station'].unique()[:5]:
    print(f'  - {s}')

# Made with Bob
