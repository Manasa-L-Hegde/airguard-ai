# -*- coding: utf-8 -*-
"""
AirGuard AI — Geo Utilities
===========================
Helper utility functions for geospatial mapping, distance calculation,
and ward spatial matching in Bengaluru.
"""

import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points 
    on the Earth surface in kilometers using Haversine formula.
    """
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_nearest_station(lat, lon, station_df):
    """
    Find the closest monitoring station to a given GPS coordinate.
    """
    min_dist = float('inf')
    nearest_station = None
    
    for _, row in station_df.iterrows():
        s_lat = float(row['latitude'])
        s_lon = float(row['longitude'])
        dist = calculate_haversine_distance(lat, lon, s_lat, s_lon)
        if dist < min_dist:
            min_dist = dist
            nearest_station = row['station']
            
    return nearest_station, min_dist
