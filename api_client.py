import httpx
from models import CurrentWeather, DailyForecast, WeekForecast

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MAURITIUS_LAT = -20.16194
MAURITIUS_LON = 57.49889

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


async def fetch_open_meteo(
    hourly: str = "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
    daily: str = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
    forecast_days: int = 7,
    current: str = "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
) -> dict:
    params = {
        "latitude": MAURITIUS_LAT,
        "longitude": MAURITIUS_LON,
        "timezone": "Indian/Mauritius",
        "forecast_days": forecast_days,
    }
    if hourly:
        params["hourly"] = hourly
    if daily:
        params["daily"] = daily
    if current:
        params["current"] = current

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_current_weather() -> CurrentWeather:
    data = await fetch_open_meteo(hourly="", daily="", current="temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m")
    current = data.get("current", {})
    code = current.get("weather_code", 0)
    return CurrentWeather(
        location="Port Louis, Mauritius",
        temperature_c=int(current.get("temperature_2m", 0)),
        conditions=WMO_CODES.get(code, f"Code {code}"),
        wind=f"{current.get('wind_speed_10m', 0)} km/h",
        humidity=f"{current.get('relative_humidity_2m', 0)}%",
        source="open-meteo.com",
    )


async def get_weather_today() -> DailyForecast:
    data = await fetch_open_meteo(
        hourly="temperature_2m,weather_code",
        daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        forecast_days=1,
    )
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    return DailyForecast(
        date=dates[0] if dates else "Today",
        conditions=WMO_CODES.get(daily.get("weather_code", [0])[0], "Unknown"),
        temp_max_c=int(daily.get("temperature_2m_max", [0])[0]),
        temp_min_c=int(daily.get("temperature_2m_min", [0])[0]),
        probability=f"{daily.get('precipitation_probability_max', [0])[0]}%",
        wind=f"{daily.get('wind_speed_10m_max', [0])[0]} km/h",
        source="open-meteo.com",
    )


async def get_weather_week() -> WeekForecast:
    data = await fetch_open_meteo(
        hourly="",
        daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        forecast_days=7,
    )
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    probs = daily.get("precipitation_probability_max", [])
    winds = daily.get("wind_speed_10m_max", [])

    forecasts = []
    for i in range(len(dates)):
        forecasts.append(DailyForecast(
            date=dates[i],
            conditions=WMO_CODES.get(codes[i], "Unknown") if i < len(codes) else "N/A",
            temp_max_c=int(max_temps[i]) if i < len(max_temps) else 0,
            temp_min_c=int(min_temps[i]) if i < len(min_temps) else 0,
            probability=f"{probs[i]}%" if i < len(probs) else "N/A",
            wind=f"{winds[i]} km/h" if i < len(winds) else "N/A",
        ))

    return WeekForecast(
        location="Port Louis, Mauritius",
        forecasts=forecasts,
        source="open-meteo.com",
    )
