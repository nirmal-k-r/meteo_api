import traceback
from fastmcp import FastMCP
import scraper
import api_client

mcp = FastMCP("Mauritius Weather")


async def _get_current_weather():
    try:
        return await scraper.get_current_weather_by_location("Vacoas")
    except Exception:
        traceback.print_exc()
        return await api_client.get_current_weather()


async def _get_week_forecast():
    try:
        return await scraper.get_week_forecast()
    except Exception:
        traceback.print_exc()
        return await api_client.get_weather_week()


async def _get_forecast_bulletin():
    try:
        return await scraper.get_forecast_bulletin()
    except Exception:
        traceback.print_exc()
        return None


@mcp.tool()
async def get_current_weather(location: str = "Vacoas") -> str:
    """Get current weather conditions in Mauritius.

    Args:
        location: Location name (e.g., Vacoas, Port Louis, Plaisance). Defaults to Vacoas.

    Returns:
        Current weather data including temperature, conditions, wind, and humidity.
    """
    try:
        weather = await scraper.get_current_weather_by_location(location)
        if weather:
            return (
                f"Current Weather in {weather.location}\n"
                f"Temperature: {weather.temperature_c}°C\n"
                f"Conditions: {weather.conditions}\n"
                f"Wind: {weather.wind}\n"
                f"Humidity: {weather.humidity}\n"
                f"Source: {weather.source}"
            )
        return "Location not found. Available: Vacoas, Port Louis, Plaisance, Agalega, Rodrigues"
    except Exception:
        traceback.print_exc()
        try:
            w = await api_client.get_current_weather()
            return (
                f"Current Weather in {w.location} (fallback)\n"
                f"Temperature: {w.temperature_c}°C\n"
                f"Conditions: {w.conditions}\n"
                f"Wind: {w.wind}\n"
                f"Humidity: {w.humidity}\n"
                f"Source: {w.source}"
            )
        except Exception as e2:
            return f"Error fetching weather: {e2}"


@mcp.tool()
async def get_weather_today() -> str:
    """Get today's weather forecast for Mauritius.

    Returns:
        Today's forecast including temperature range, conditions, and wind.
    """
    try:
        forecast = await scraper.get_week_forecast()
        if forecast.forecasts:
            today = forecast.forecasts[0]
            return (
                f"Today's Forecast ({today.date})\n"
                f"Conditions: {today.conditions}\n"
                f"Max Temperature: {today.temp_max_c}°C\n"
                f"Min Temperature: {today.temp_min_c}°C\n"
                f"Rain Probability: {today.probability}\n"
                f"Wind: {today.wind}\n"
                f"Sea State: {today.sea_state or 'N/A'}\n"
                f"Source: {forecast.source}"
            )
        return "No forecast data available"
    except Exception:
        traceback.print_exc()
        try:
            f = await api_client.get_weather_today()
            return (
                f"Today's Forecast ({f.date})\n"
                f"Conditions: {f.conditions}\n"
                f"Max Temperature: {f.temp_max_c}°C\n"
                f"Min Temperature: {f.temp_min_c}°C\n"
                f"Rain Probability: {f.probability}\n"
                f"Wind: {f.wind}\n"
                f"Source: {f.source}"
            )
        except Exception as e2:
            return f"Error fetching forecast: {e2}"


@mcp.tool()
async def get_weather_tomorrow() -> str:
    """Get tomorrow's weather forecast for Mauritius.

    Returns:
        Tomorrow's forecast including temperature range, conditions, and wind.
    """
    try:
        forecast = await scraper.get_week_forecast()
        if len(forecast.forecasts) > 1:
            tomorrow = forecast.forecasts[1]
            return (
                f"Tomorrow's Forecast ({tomorrow.date})\n"
                f"Conditions: {tomorrow.conditions}\n"
                f"Max Temperature: {tomorrow.temp_max_c}°C\n"
                f"Min Temperature: {tomorrow.temp_min_c}°C\n"
                f"Rain Probability: {tomorrow.probability}\n"
                f"Wind: {tomorrow.wind}\n"
                f"Sea State: {tomorrow.sea_state or 'N/A'}\n"
                f"Source: {forecast.source}"
            )
        return "Tomorrow's forecast not available"
    except Exception:
        traceback.print_exc()
        return "Error fetching tomorrow's forecast"


@mcp.tool()
async def get_weather_week() -> str:
    """Get 7-day weather forecast for Mauritius.

    Returns:
        Full week forecast with daily temperature, conditions, wind, and rain probability.
    """
    try:
        forecast = await _get_week_forecast()
        lines = [f"7-Day Forecast for {forecast.location} (Source: {forecast.source})\n"]
        for f in forecast.forecasts:
            lines.append(
                f"  {f.date}: {f.conditions}, {f.temp_min_c}-{f.temp_max_c}°C, "
                f"Rain: {f.probability}, Wind: {f.wind}"
                + (f", Sea: {f.sea_state}" if f.sea_state else "")
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching week forecast: {e}"


@mcp.tool()
async def get_forecast_bulletin() -> str:
    """Get the detailed forecast bulletin from Mauritius Met Service.

    Returns:
        Full text bulletin including general situation, temperature ranges, wind, sea, and tides.
    """
    try:
        bulletin = await _get_forecast_bulletin()
        if bulletin:
            parts = [
                f"Forecast Bulletin (Source: {bulletin.source})\n",
                f"General Situation:\n{bulletin.general_situation}\n",
                f"Forecast:\n{bulletin.forecast_text}\n",
                f"Max Temp: {bulletin.max_temp_range}",
                f"Min Temp: {bulletin.min_temp_range}",
                f"Wind: {bulletin.wind}",
                f"Sea: {bulletin.sea_conditions}",
            ]
            if bulletin.tides:
                parts.append(f"Tides: {bulletin.tides}")
            if bulletin.sunrise_sunset:
                parts.append(f"Sun: {bulletin.sunrise_sunset}")
            return "\n".join(parts)
        return "Bulletin not available"
    except Exception as e:
        return f"Error fetching bulletin: {e}"


if __name__ == "__main__":
    mcp.run()
