"""
Servidor MCP de datos de clima, implementado con FastMCP (SDK oficial).
Expone tres tools: get_current_weather, get_forecast y list_available_cities.

No necesita credenciales ni acceso a ninguna API: es protocolo MCP puro sobre
datos de ejemplo (mock). Lo lanza weather_agent/agent.py como subproceso stdio.
"""
from datetime import datetime, timedelta
from typing import Literal
import random

from fastmcp import FastMCP

mcp = FastMCP("weather-mcp-server")

# Datos de ejemplo de clima por ciudad
WEATHER_DATA = {
    "Buenos Aires": {"temp": 22, "humidity": 65, "conditions": "parcialmente nublado", "wind_kph": 18},
    "Córdoba":      {"temp": 28, "humidity": 40, "conditions": "soleado", "wind_kph": 12},
    "Rosario":      {"temp": 25, "humidity": 55, "conditions": "nublado", "wind_kph": 22},
    "Mendoza":      {"temp": 18, "humidity": 30, "conditions": "viento", "wind_kph": 45},
    "Salta":        {"temp": 30, "humidity": 70, "conditions": "parcialmente nublado", "wind_kph": 8},
}

# El conjunto de ciudades disponibles queda expresado en el type hint: FastMCP
# lo traduce automáticamente a un "enum" en el inputSchema JSON de la tool.
City = Literal["Buenos Aires", "Córdoba", "Rosario", "Mendoza", "Salta"]


@mcp.tool
def get_current_weather(city: City, unit: Literal["celsius", "fahrenheit"] = "celsius") -> dict:
    """Get the current weather conditions for a specific Argentine city.

    Use this when the user asks about current weather, temperature, or
    conditions for a city. Do NOT use for multi-day forecasts — use
    get_forecast instead. Available cities: Buenos Aires, Córdoba,
    Rosario, Mendoza, Salta.
    """
    data = WEATHER_DATA[city].copy()
    temp = data["temp"]
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32, 1)

    return {
        "city": city,
        "temperature": temp,
        "unit": unit,
        "humidity_pct": data["humidity"],
        "conditions": data["conditions"],
        "wind_kph": data["wind_kph"],
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool
def get_forecast(city: City, days: int = 3) -> dict:
    """Get a weather forecast for the next 1 to 5 days for a specific Argentine city.

    Use this when the user asks about future weather, 'tomorrow', 'this week',
    or asks for multiple days. For current conditions, use get_current_weather
    instead.
    """
    days = min(max(days, 1), 5)  # Se fuerza el rango 1-5: nunca confiar en lo que mande el LLM
    base = WEATHER_DATA[city]
    forecast = []

    for i in range(1, days + 1):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        temp_variation = random.randint(-3, 3)
        forecast.append({
            "date": date,
            "temperature_celsius": base["temp"] + temp_variation,
            "conditions": base["conditions"],
            "probability_rain_pct": random.randint(10, 60),
        })

    return {"city": city, "forecast_days": days, "forecast": forecast}


@mcp.tool
def list_available_cities() -> dict:
    """List all Argentine cities available for weather queries.

    Use this when the user asks which cities are supported, or after
    get_current_weather / get_forecast rechaza una ciudad no disponible.
    """
    return {"cities": list(WEATHER_DATA.keys())}


if __name__ == "__main__":
    mcp.run(show_banner=False)
