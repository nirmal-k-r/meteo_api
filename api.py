import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

TOOLS = [
    {
        "name": "get_current_weather",
        "description": "Get current weather conditions in Mauritius. Returns temperature, conditions, wind, humidity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location name (e.g., Vacoas, Port Louis, Plaisance)",
                    "default": "Vacoas"
                }
            }
        }
    },
    {
        "name": "get_weather_today",
        "description": "Get today's weather forecast for Mauritius including temperature, conditions, wind, sea state.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_weather_tomorrow",
        "description": "Get tomorrow's weather forecast for Mauritius.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_weather_week",
        "description": "Get 7-day weather forecast for Mauritius.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_forecast_bulletin",
        "description": "Get detailed forecast bulletin from Mauritius Met Service with tides, sunrise/sunset.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


async def handle_tool_call(name: str, arguments: dict) -> str:
    if name == "get_current_weather":
        location = arguments.get("location", "Vacoas")
        try:
            weather = await scraper.get_current_weather_by_location(location)
            if weather:
                return json.dumps(weather.model_dump(), indent=2)
            w = await api_client.get_current_weather()
            return json.dumps(w.model_dump(), indent=2)
        except Exception:
            w = await api_client.get_current_weather()
            return json.dumps(w.model_dump(), indent=2)

    elif name == "get_weather_today":
        try:
            forecast = await scraper.get_week_forecast()
            if forecast.forecasts:
                return json.dumps(forecast.forecasts[0].model_dump(), indent=2)
        except Exception:
            pass
        f = await api_client.get_weather_today()
        return json.dumps(f.model_dump(), indent=2)

    elif name == "get_weather_tomorrow":
        try:
            forecast = await scraper.get_week_forecast()
            if len(forecast.forecasts) > 1:
                return json.dumps(forecast.forecasts[1].model_dump(), indent=2)
        except Exception:
            pass
        return json.dumps({"error": "Tomorrow's forecast not available"}, indent=2)

    elif name == "get_weather_week":
        try:
            forecast = await scraper.get_week_forecast()
            return json.dumps(forecast.model_dump(), indent=2)
        except Exception:
            forecast = await api_client.get_weather_week()
            return json.dumps(forecast.model_dump(), indent=2)

    elif name == "get_forecast_bulletin":
        try:
            bulletin = await scraper.get_forecast_bulletin()
            if bulletin:
                return json.dumps(bulletin.model_dump(), indent=2)
        except Exception:
            pass
        return json.dumps({"error": "Bulletin not available"}, indent=2)

    return json.dumps({"error": f"Unknown tool: {name}"})


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})

    method = body.get("method")
    msg_id = body.get("id")

    if method == "initialize":
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "mauritius-weather", "version": "1.0.0"}
            }
        })

    elif method == "notifications/initialized":
        return JSONResponse(content={"jsonrpc": "2.0"})

    elif method == "tools/list":
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS}
        })

    elif method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result_text = await handle_tool_call(tool_name, arguments)
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": result_text}]
            }
        })

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    })


@app.get("/mcp")
async def mcp_sse():
    return JSONResponse(content={"error": "Use POST /mcp for MCP protocol"})


@app.get("/")
def root():
    return {"status": "ok", "service": "Mauritius Weather API", "mcp_endpoint": "/mcp"}


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
    port = int(os.environ.get("PORT", 3013))
    uvicorn.run(app, host="0.0.0.0", port=port)
