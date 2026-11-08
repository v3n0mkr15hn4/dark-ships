"""Small geometry helpers. Pure functions, work on numbers, numpy arrays or pandas Series."""
import numpy as np

EARTH_RADIUS_KM = 6371.0
KM_PER_NM = 1.852


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two points given in decimal degrees."""
    lat1, lon1, lat2, lon2 = (np.radians(x) for x in (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def haversine_nm(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    return haversine_km(lat1, lon1, lat2, lon2) / KM_PER_NM


def angle_diff_deg(a, b):
    """Smallest absolute difference between two compass angles, 0..180 degrees."""
    d = np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)) % 360
    return np.minimum(d, 360 - d)
