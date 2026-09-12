import httpx
from bs4 import BeautifulSoup
from models import CurrentWeather, DailyForecast, WeekForecast, WeatherBulletin

BASE_URL = "http://metservice.intnet.mu"


async def fetch_page(url: str) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.text


async def get_current_weather() -> list[CurrentWeather]:
    html = await fetch_page(f"{BASE_URL}/index.php")
    soup = BeautifulSoup(html, "lxml")
    results = []
    for li in soup.select("ul.bjqs li"):
        loc_el = li.select_one(".vacoas_plaisance")
        cond_el = li.select_one(".conditions")
        temp_el = li.select_one(".temperature")
        wind_el = li.select("span.fgrey")
        if not (loc_el and temp_el):
            continue
        loc = loc_el.get_text(strip=True).replace("\n", " ")
        conditions = cond_el.get_text(strip=True) if cond_el else "N/A"
        temp = temp_el.get_text(strip=True).replace("°", "").replace("\xa0", "")
        wind = wind_el[0].get_text(strip=True) if len(wind_el) > 0 else "N/A"
        humidity = wind_el[1].get_text(strip=True) if len(wind_el) > 1 else "N/A"
        results.append(CurrentWeather(
            location=loc,
            temperature_c=int(temp),
            conditions=conditions,
            wind=wind,
            humidity=humidity,
            source="metservice.intnet.mu",
        ))
    return results


async def get_current_weather_by_location(location: str = "Vacoas") -> CurrentWeather | None:
    all_weather = await get_current_weather()
    for w in all_weather:
        if location.lower() in w.location.lower():
            return w
    return all_weather[0] if all_weather else None


async def get_week_forecast() -> WeekForecast:
    html = await fetch_page(f"{BASE_URL}/probabilistic-forecast.php")
    soup = BeautifulSoup(html, "lxml")
    forecasts = []

    for div in soup.find_all("div", class_=lambda c: c and ("forecast" in c or "7dayforecast_hori" in c or "backgroundcolored" in c)):
        day_el = div.select_one(".fdaynew, .fday")
        cond_el = div.select_one(".fconditionnew, .fcondition")
        max_el = div.select_one(".maxtemp .ftemp")
        min_el = div.select_one(".min .ftemp")

        if not day_el:
            continue

        date = day_el.get_text(strip=True)
        conditions = cond_el.get_text(strip=True) if cond_el else "N/A"

        max_temp_text = max_el.get_text(strip=True) if max_el else "0"
        max_temp = int(max_temp_text.replace("°C", "").replace("°", "").strip())

        min_temp = 0
        if min_el:
            min_temp_text = min_el.get_text(strip=True)
            min_temp = int(min_temp_text.replace("°C", "").replace("°", "").strip())

        probability = "N/A"
        wind = "N/A"
        sea_state = None

        for p in div.find_all("p"):
            text = p.get_text(strip=True)
            if "Prob:" in text:
                prob_span = p.select_one("span.fgrey")
                if prob_span:
                    probability = prob_span.get_text(strip=True)
            elif ".Wind" in text or "Wind" in text:
                span = p.select_one("span.fgrey")
                if span:
                    detail = span.get_text(strip=True)
                    if ".Wind" in detail:
                        parts = detail.split(".Wind")
                        if len(parts) > 1:
                            wind_part = parts[1].split(".")[0].strip()
                            wind = wind_part
                    elif "Wind" in detail:
                        parts = detail.split("Wind")
                        if len(parts) > 1:
                            wind_part = parts[1].split(".")[0].strip()
                            wind = wind_part
                    if "Sea" in detail:
                        sea_idx = detail.find("Sea")
                        sea_text = detail[sea_idx:].split(".")[0].strip()
                        sea_state = sea_text

        forecasts.append(DailyForecast(
            date=date,
            conditions=conditions,
            temp_max_c=max_temp,
            temp_min_c=min_temp,
            probability=probability,
            wind=wind,
            sea_state=sea_state,
        ))

    return WeekForecast(
        location="Mauritius",
        forecasts=forecasts,
        source="metservice.intnet.mu",
    )


async def get_forecast_bulletin() -> WeatherBulletin:
    html = await fetch_page(f"{BASE_URL}/forecast-bulletin-english-mauritius.php")
    soup = BeautifulSoup(html, "lxml")

    content_div = soup.select_one("div.left_content")
    if not content_div:
        return WeatherBulletin(
            general_situation="N/A",
            forecast_text="N/A",
            max_temp_range="N/A",
            min_temp_range="N/A",
            wind="N/A",
            sea_conditions="N/A",
            source="metservice.intnet.mu",
        )

    paragraphs = content_div.find_all("p")
    full_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    general = ""
    forecast = ""
    max_temp = ""
    min_temp = ""
    wind = ""
    sea = ""
    tides = ""
    sun = ""

    for p in paragraphs:
        text = p.get_text(strip=True)
        if "General situation" in text:
            idx = full_text.find("General situation")
            general = full_text[idx:idx+300].split("Forecast for")[0].strip()
        elif "Forecast for the next 24 hours" in text:
            idx = full_text.find("Forecast for the next 24 hours")
            forecast = full_text[idx:idx+800].split("High tides")[0].strip()
            if "maximum temperature will be between" in forecast.lower():
                max_idx = forecast.lower().find("maximum temperature will be between")
                max_temp = forecast[max_idx:max_idx+150].split(".")[0].strip() + "."
            if "minimum temperature will be between" in forecast.lower():
                min_idx = forecast.lower().find("minimum temperature will be between")
                min_temp = forecast[min_idx:min_idx+150].split(".")[0].strip() + "."
            if "wind will blow" in forecast.lower():
                wind_idx = forecast.lower().find("wind will blow")
                wind = forecast[wind_idx:wind_idx+100].split(".")[0].strip() + "."
            if "sea" in forecast.lower() and "reef" in forecast.lower():
                sea_idx = forecast.lower().find("sea")
                sea = forecast[sea_idx:sea_idx+150].split(".")[0].strip() + "."
        elif "tides" in text.lower():
            tides = text
        elif "sunset" in text.lower() or "sunrise" in text.lower():
            sun = text

    if wind == "Not available" and forecast:
        if "wind" in forecast.lower():
            wind_idx = forecast.lower().find("wind")
            wind = forecast[wind_idx:wind_idx+100].split(".")[0].strip() + "."

    if sea == "Not available" and forecast:
        if "sea" in forecast.lower():
            sea_idx = forecast.lower().find("sea")
            sea = forecast[sea_idx:sea_idx+150].split(".")[0].strip() + "."

    return WeatherBulletin(
        general_situation=general or "Not available",
        forecast_text=forecast or full_text[:500],
        max_temp_range=max_temp or "Not available",
        min_temp_range=min_temp or "Not available",
        wind=wind or "Not available",
        sea_conditions=sea or "Not available",
        tides=tides or None,
        sunrise_sunset=sun or None,
        source="metservice.intnet.mu",
    )
