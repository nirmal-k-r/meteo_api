from pydantic import BaseModel
from typing import Optional


class CurrentWeather(BaseModel):
    location: str
    temperature_c: int
    conditions: str
    wind: str
    humidity: str
    source: str


class DailyForecast(BaseModel):
    date: str
    conditions: str
    temp_max_c: int
    temp_min_c: int
    probability: str
    wind: str
    sea_state: Optional[str] = None
    details: Optional[str] = None


class WeatherBulletin(BaseModel):
    general_situation: str
    forecast_text: str
    max_temp_range: str
    min_temp_range: str
    wind: str
    sea_conditions: str
    tides: Optional[str] = None
    sunrise_sunset: Optional[str] = None
    source: str


class WeekForecast(BaseModel):
    location: str
    forecasts: list[DailyForecast]
    source: str
