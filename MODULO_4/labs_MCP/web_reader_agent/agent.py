# web_reader_agent/agent.py
# Patrón invertido: ADK exponiendo una tool propia (load_web_page) como servidor
# MCP (adk_mcp_server/adk_server.py), y otro agente ADK consumiéndola como cliente.
import os
import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()

# Ruta absoluta al servidor MCP propio (adk_mcp_server/adk_server.py, en la raíz de labs_MCP/).
PATH_TO_YOUR_MCP_SERVER_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "adk_mcp_server",
    "adk_server.py",
)

root_agent = LlmAgent(
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    name="web_reader_mcp_client_agent",
    instruction="Use the 'load_web_page' tool to fetch content from a URL provided by the user.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    # sys.executable = el Python del venv activo, que tiene google-adk instalado.
                    command=sys.executable,
                    args=[PATH_TO_YOUR_MCP_SERVER_SCRIPT],
                ),
                timeout=15,
            ),
            tool_filter=["load_web_page"],
        )
    ],
)
