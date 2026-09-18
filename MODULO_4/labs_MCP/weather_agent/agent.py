# weather_agent/agent.py
# Cliente MCP: un agente ADK que consume un servidor MCP propio (weather_mcp_server.py,
# escrito con FastMCP) lanzándolo como subproceso y hablándole por stdio.
#
# Es el mismo patrón que maps_agent (MCPToolset + StdioConnectionParams); lo único
# que cambia es qué proceso lanza StdioServerParameters: acá es un servidor nuestro
# en Python, allá es un servidor externo que se baja con npx.
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()

# Ruta absoluta al servidor, derivada de la ubicación de este archivo.
# StdioServerParameters resuelve las rutas relativas contra el directorio desde
# el que se lanza `adk web`, no contra este archivo: una ruta relativa se rompe
# apenas se corre desde otra carpeta.
WEATHER_SERVER = str(Path(__file__).parent.parent / "weather_mcp_server.py")

root_agent = LlmAgent(
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    name="weather_mcp_client_agent",
    instruction=(
        "Sos un asistente de clima para ciudades argentinas. Usá las "
        "herramientas disponibles para responder sobre clima actual y "
        "pronósticos. Si la ciudad pedida no está disponible, avisá y "
        "listá las ciudades soportadas. Presentá temperaturas en Celsius "
        "salvo que pidan Fahrenheit."
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    # sys.executable = el Python del venv activo, que tiene fastmcp instalado.
                    command=sys.executable,
                    args=[WEATHER_SERVER],
                ),
                timeout=15,
            ),
        )
    ],
)
