"""
Geo Service
===========
Provides:
  - City-to-coordinate lookup for major Indian industrial cities
  - Haversine distance calculation (km)
  - Location score normalisation (0.0 – 1.0 where 1.0 = same city)

The built-in city table covers the 150+ most relevant Indian manufacturing
hubs. Users can also supply explicit lat/lon coordinates which take priority.
"""

from __future__ import annotations

import math
from typing import NamedTuple


class Coordinates(NamedTuple):
    lat: float
    lon: float
    city: str = ""


# ---------------------------------------------------------------------------
# Built-in city → coordinate table (sourced from public domain geocoding data)
# ---------------------------------------------------------------------------

_CITY_COORDS: dict[str, Coordinates] = {
    # Maharashtra
    "mumbai": Coordinates(19.0760, 72.8777, "Mumbai"),
    "pune": Coordinates(18.5204, 73.8567, "Pune"),
    "nagpur": Coordinates(21.1458, 79.0882, "Nagpur"),
    "nashik": Coordinates(19.9975, 73.7898, "Nashik"),
    "aurangabad": Coordinates(19.8762, 75.3433, "Aurangabad"),
    "solapur": Coordinates(17.6805, 75.9064, "Solapur"),
    "kolhapur": Coordinates(16.7050, 74.2433, "Kolhapur"),
    "thane": Coordinates(19.2183, 72.9781, "Thane"),
    "navi mumbai": Coordinates(19.0368, 73.0158, "Navi Mumbai"),
    # Gujarat
    "ahmedabad": Coordinates(23.0225, 72.5714, "Ahmedabad"),
    "surat": Coordinates(21.1702, 72.8311, "Surat"),
    "vadodara": Coordinates(22.3072, 73.1812, "Vadodara"),
    "rajkot": Coordinates(22.3039, 70.8022, "Rajkot"),
    "gandhinagar": Coordinates(23.2156, 72.6369, "Gandhinagar"),
    "anand": Coordinates(22.5645, 72.9289, "Anand"),
    "bhavnagar": Coordinates(21.7645, 72.1519, "Bhavnagar"),
    "jamnagar": Coordinates(22.4707, 70.0577, "Jamnagar"),
    "dahej": Coordinates(21.7272, 72.5443, "Dahej"),
    "hazira": Coordinates(21.0880, 72.6348, "Hazira"),
    "mundra": Coordinates(22.8391, 69.7141, "Mundra"),
    # Karnataka
    "bengaluru": Coordinates(12.9716, 77.5946, "Bengaluru"),
    "bangalore": Coordinates(12.9716, 77.5946, "Bangalore"),
    "mysuru": Coordinates(12.2958, 76.6394, "Mysuru"),
    "hubli": Coordinates(15.3647, 75.1240, "Hubli"),
    "mangaluru": Coordinates(12.9141, 74.8560, "Mangaluru"),
    "bellary": Coordinates(15.1394, 76.9214, "Bellary"),
    "tumkur": Coordinates(13.3409, 77.1007, "Tumkur"),
    # Tamil Nadu
    "chennai": Coordinates(13.0827, 80.2707, "Chennai"),
    "coimbatore": Coordinates(11.0168, 76.9558, "Coimbatore"),
    "madurai": Coordinates(9.9252, 78.1198, "Madurai"),
    "tiruchirappalli": Coordinates(10.7905, 78.7047, "Tiruchirappalli"),
    "tirupur": Coordinates(11.1085, 77.3411, "Tirupur"),
    "salem": Coordinates(11.6643, 78.1460, "Salem"),
    "ambattur": Coordinates(13.1143, 80.1548, "Ambattur"),
    # Telangana
    "hyderabad": Coordinates(17.3850, 78.4867, "Hyderabad"),
    "warangal": Coordinates(17.9784, 79.5941, "Warangal"),
    "nizamabad": Coordinates(18.6725, 78.0941, "Nizamabad"),
    # Andhra Pradesh
    "visakhapatnam": Coordinates(17.6868, 83.2185, "Visakhapatnam"),
    "vijayawada": Coordinates(16.5062, 80.6480, "Vijayawada"),
    "tirupati": Coordinates(13.6288, 79.4192, "Tirupati"),
    "guntur": Coordinates(16.3067, 80.4365, "Guntur"),
    # West Bengal
    "kolkata": Coordinates(22.5726, 88.3639, "Kolkata"),
    "durgapur": Coordinates(23.5204, 87.3119, "Durgapur"),
    "asansol": Coordinates(23.6739, 86.9524, "Asansol"),
    "haldia": Coordinates(22.0257, 88.0583, "Haldia"),
    "howrah": Coordinates(22.5958, 88.2636, "Howrah"),
    # Rajasthan
    "jaipur": Coordinates(26.9124, 75.7873, "Jaipur"),
    "jodhpur": Coordinates(26.2389, 73.0243, "Jodhpur"),
    "udaipur": Coordinates(24.5854, 73.7125, "Udaipur"),
    "kota": Coordinates(25.2138, 75.8648, "Kota"),
    "bhilwara": Coordinates(25.3407, 74.6313, "Bhilwara"),
    "alwar": Coordinates(27.5530, 76.6346, "Alwar"),
    "neemrana": Coordinates(27.9726, 76.3813, "Neemrana"),
    # Uttar Pradesh
    "lucknow": Coordinates(26.8467, 80.9462, "Lucknow"),
    "kanpur": Coordinates(26.4499, 80.3319, "Kanpur"),
    "agra": Coordinates(27.1767, 78.0081, "Agra"),
    "varanasi": Coordinates(25.3176, 82.9739, "Varanasi"),
    "ghaziabad": Coordinates(28.6692, 77.4538, "Ghaziabad"),
    "noida": Coordinates(28.5355, 77.3910, "Noida"),
    "greater noida": Coordinates(28.4744, 77.5040, "Greater Noida"),
    "meerut": Coordinates(28.9845, 77.7064, "Meerut"),
    # Delhi / NCR
    "delhi": Coordinates(28.7041, 77.1025, "Delhi"),
    "new delhi": Coordinates(28.6139, 77.2090, "New Delhi"),
    "gurugram": Coordinates(28.4595, 77.0266, "Gurugram"),
    "faridabad": Coordinates(28.4089, 77.3178, "Faridabad"),
    "manesar": Coordinates(28.3574, 76.9380, "Manesar"),
    # Haryana
    "ambala": Coordinates(30.3782, 76.7767, "Ambala"),
    "yamunanagar": Coordinates(30.1290, 77.2674, "Yamunanagar"),
    "rohtak": Coordinates(28.8955, 76.6066, "Rohtak"),
    "panipat": Coordinates(29.3909, 76.9635, "Panipat"),
    "sonipat": Coordinates(28.9931, 77.0151, "Sonipat"),
    # Punjab
    "ludhiana": Coordinates(30.9010, 75.8573, "Ludhiana"),
    "amritsar": Coordinates(31.6340, 74.8723, "Amritsar"),
    "jalandhar": Coordinates(31.3260, 75.5762, "Jalandhar"),
    "patiala": Coordinates(30.3398, 76.3869, "Patiala"),
    # Madhya Pradesh
    "indore": Coordinates(22.7196, 75.8577, "Indore"),
    "bhopal": Coordinates(23.2599, 77.4126, "Bhopal"),
    "gwalior": Coordinates(26.2183, 78.1828, "Gwalior"),
    "jabalpur": Coordinates(23.1815, 79.9864, "Jabalpur"),
    "pithampur": Coordinates(22.6171, 75.6882, "Pithampur"),
    # Chhattisgarh
    "raipur": Coordinates(21.2514, 81.6296, "Raipur"),
    "bhilai": Coordinates(21.1938, 81.3509, "Bhilai"),
    "bilaspur": Coordinates(22.0796, 82.1391, "Bilaspur"),
    # Odisha
    "bhubaneswar": Coordinates(20.2961, 85.8245, "Bhubaneswar"),
    "cuttack": Coordinates(20.4625, 85.8830, "Cuttack"),
    "rourkela": Coordinates(22.2604, 84.8536, "Rourkela"),
    "paradip": Coordinates(20.3165, 86.6100, "Paradip"),
    # Jharkhand
    "ranchi": Coordinates(23.3441, 85.3096, "Ranchi"),
    "jamshedpur": Coordinates(22.8046, 86.2029, "Jamshedpur"),
    "dhanbad": Coordinates(23.7957, 86.4304, "Dhanbad"),
    # Bihar
    "patna": Coordinates(25.5941, 85.1376, "Patna"),
    "muzaffarpur": Coordinates(26.1209, 85.3647, "Muzaffarpur"),
    # Kerala
    "kochi": Coordinates(9.9312, 76.2673, "Kochi"),
    "thiruvananthapuram": Coordinates(8.5241, 76.9366, "Thiruvananthapuram"),
    "kozhikode": Coordinates(11.2588, 75.7804, "Kozhikode"),
    # Himachal Pradesh
    "baddi": Coordinates(30.9558, 76.7908, "Baddi"),
    "bilaspur hp": Coordinates(31.3309, 76.7587, "Bilaspur HP"),
    # Uttarakhand
    "haridwar": Coordinates(29.9457, 78.1642, "Haridwar"),
    "dehradun": Coordinates(30.3165, 78.0322, "Dehradun"),
    "rudrapur": Coordinates(28.9805, 79.4000, "Rudrapur"),
    "pantnagar": Coordinates(29.0061, 79.4775, "Pantnagar"),
    # Assam
    "guwahati": Coordinates(26.1445, 91.7362, "Guwahati"),
    "dibrugarh": Coordinates(27.4728, 94.9120, "Dibrugarh"),
    # Goa
    "panaji": Coordinates(15.4909, 73.8278, "Panaji"),
    "vasco da gama": Coordinates(15.3958, 73.8110, "Vasco da Gama"),
}


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------

class GeoService:
    """Geolocation utilities for CircuLink."""

    @staticmethod
    def lookup_city(city: str) -> Coordinates | None:
        """Return coordinates for a city name (case-insensitive). None if unknown."""
        return _CITY_COORDS.get(city.strip().lower())

    @staticmethod
    def all_known_cities() -> list[str]:
        """Return sorted list of canonical city names."""
        return sorted({c.city for c in _CITY_COORDS.values()})

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance in kilometres between two points."""
        R = 6371.0  # Earth radius in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def location_score(
        buyer_lat: float,
        buyer_lon: float,
        seller_lat: float,
        seller_lon: float,
        max_radius_km: float = 2000.0,
    ) -> float:
        """
        Normalised location score in [0.0, 1.0].

        Score = 1.0 at 0 km distance, decays toward 0.0 at max_radius_km.
        Uses an exponential decay so nearby suppliers score much higher.
        """
        dist_km = GeoService.haversine_km(buyer_lat, buyer_lon, seller_lat, seller_lon)
        if dist_km <= 0:
            return 1.0
        # Exponential decay: half-score at ~350 km for default max_radius
        score = math.exp(-dist_km / (max_radius_km / 5.0))
        return max(0.0, min(1.0, score))

    @staticmethod
    def resolve_coordinates(
        city: str,
        lat: float | None = None,
        lon: float | None = None,
    ) -> Coordinates | None:
        """
        Resolve coordinates preferring explicit lat/lon; fall back to city lookup.
        Returns None if neither source is available.
        """
        if lat is not None and lon is not None and lat != 0 and lon != 0:
            return Coordinates(lat, lon, city)
        return GeoService.lookup_city(city)
