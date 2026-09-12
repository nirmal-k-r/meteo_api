from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import scraper
import api_client
from models import CurrentWeather, DailyForecast, WeekForecast, WeatherBulletin

app = FastAPI(title="Mauritius Weather API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "Mauritius Weather API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/current")
async def get_current_weather(location: str = "Vacoas"):
    try:
        weather = await scraper.get_current_weather_by_location(location)
        if weather:
            return weather.model_dump()
        return await _fallback_current()
    except Exception:
        return await _fallback_current()


async def _fallback_current():
    try:
        w = await api_client.get_current_weather()
        return w.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/today")
async def get_weather_today():
    try:
        forecast = await scraper.get_week_forecast()
        if forecast.forecasts:
            return forecast.forecasts[0].model_dump()
        return await _fallback_today()
    except Exception:
        return await _fallback_today()


async def _fallback_today():
    try:
        f = await api_client.get_weather_today()
        return f.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tomorrow")
async def get_weather_tomorrow():
    try:
        forecast = await scraper.get_week_forecast()
        if len(forecast.forecasts) > 1:
            return forecast.forecasts[1].model_dump()
        raise HTTPException(status_code=404, detail="Tomorrow's forecast not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/week")
async def get_weather_week():
    try:
        forecast = await scraper.get_week_forecast()
        return forecast.model_dump()
    except Exception:
        try:
            forecast = await api_client.get_weather_week()
            return forecast.model_dump()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bulletin")
async def get_forecast_bulletin():
    try:
        bulletin = await scraper.get_forecast_bulletin()
        if bulletin:
            return bulletin.model_dump()
        raise HTTPException(status_code=404, detail="Bulletin not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3012)
