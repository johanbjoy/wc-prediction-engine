import os
import requests
import logging

logger = logging.getLogger(__name__)

def get_weather_factor(city_name: str) -> float:
    """
    Fetches real-time weather from OpenWeatherMap for the match city.
    Calculates a weather dampening factor. High wind/rain reduces the expected goals.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key or not city_name:
        return 1.0

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return 1.0
            
        data = resp.json()
        wind_speed = data.get("wind", {}).get("speed", 0.0) # m/s
        rain_1h = data.get("rain", {}).get("1h", 0.0) # mm
        
        factor = 1.0
        # Dampen goals by 5% if very windy (>22 mph / 10 m/s)
        if wind_speed > 10.0:
            factor -= 0.05
        # Dampen goals by 10% if heavy rain (>5mm/hr)
        if rain_1h > 5.0:
            factor -= 0.10
            
        return max(0.80, factor) # Floor at 80%

    except Exception as e:
        logger.warning(f"Weather API failed for {city_name}: {e}")
        return 1.0
