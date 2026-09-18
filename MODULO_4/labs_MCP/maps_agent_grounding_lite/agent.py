# maps_agent_grounding_lite/agent.py
# ADK como cliente MCP del servidor oficial y gestionado por Google
# "Maps Grounding Lite", vía HTTP (mapstools.googleapis.com). Mismo caso de uso
# que maps_agent, pero con un servidor remoto oficial en vez de un proceso local
# comunitario: sirve para comparar transporte stdio vs. HTTP.
import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

load_dotenv()

google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
if not google_maps_api_key:
    raise ValueError(
        "Falta GOOGLE_MAPS_API_KEY en el archivo .env (ver el README de esta "
        "carpeta) — Maps Grounding Lite la necesita para autenticar la llamada MCP."
    )

root_agent = LlmAgent(
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    name="maps_grounding_lite_agent",
    instruction=(
        "Usá las herramientas de Google Maps Grounding Lite disponibles para "
        "responder preguntas sobre lugares, clima y rutas entre ubicaciones."
    ),
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="https://mapstools.googleapis.com/mcp",
                headers={
                    "X-Goog-Api-Key": google_maps_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            ),
        )
    ],
)
