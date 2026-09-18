# maps_agent/agent.py
# ADK como cliente MCP del servidor comunitario de Google Maps
# (@modelcontextprotocol/server-google-maps) vía stdio. El servidor se baja y
# ejecuta con npx.
import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()

google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
if not google_maps_api_key:
    raise ValueError(
        "Falta GOOGLE_MAPS_API_KEY en el archivo .env (ver el README de esta "
        "carpeta) — el servidor MCP de Maps la necesita para llamar a las APIs de Google Maps."
    )

root_agent = LlmAgent(
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    name="maps_mcp_client_agent",
    instruction=(
        "Usá las herramientas de Google Maps disponibles para responder preguntas "
        "sobre direcciones, distancias y rutas entre lugares."
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-google-maps",
                    ],
                    env={"GOOGLE_MAPS_API_KEY": google_maps_api_key},
                ),
                timeout=15,
            ),
        )
    ],
)
