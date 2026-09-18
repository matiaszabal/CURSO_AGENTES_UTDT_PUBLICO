# mcp_agent/agent.py
# ADK como cliente MCP del servidor oficial de filesystem
# (@modelcontextprotocol/server-filesystem, se baja y ejecuta con npx).
# El agente no tiene ni una línea de código de manejo de archivos: todo lo hace el servidor MCP.
import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()

# Carpeta ABSOLUTA a la que el servidor MCP puede acceder (y solo a esa).
# Vive junto a este agent.py.
TARGET_FOLDER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "archivos_demo"
)

root_agent = LlmAgent(
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    name="filesystem_assistant_agent",
    instruction="Help the user manage their files. You can list files, read files, etc.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",  # npx instala el paquete sin pedir confirmación
                        "@modelcontextprotocol/server-filesystem",
                        # Debe ser una ruta ABSOLUTA a una carpeta accesible por el proceso npx.
                        os.path.abspath(TARGET_FOLDER_PATH),
                    ],
                ),
            ),
            # Opcional: limitar qué tools del servidor MCP ve el agente.
            # tool_filter=['list_directory', 'read_file']
        )
    ],
)
