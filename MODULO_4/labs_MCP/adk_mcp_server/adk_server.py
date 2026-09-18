# adk_mcp_server/adk_server.py
# Servidor MCP propio que expone una herramienta de ADK (load_web_page) por stdio.
# Lo lanza web_reader_agent/agent.py como subproceso.
#
# Ojo: en un servidor stdio, stdout es el canal del protocolo MCP (JSON-RPC).
# Los logs de depuración van a stderr para no mezclarse con los mensajes.
import asyncio
import json
import sys

from dotenv import load_dotenv

# MCP Server Imports
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.load_web_page import load_web_page

# ADK <-> MCP Conversion Utility
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# Load Environment Variables
load_dotenv()


def log(*args):
    print(*args, file=sys.stderr)


# Prepare the ADK Tool
log("Initializing ADK load_web_page tool...")
adk_tool_to_expose = FunctionTool(load_web_page)
log(
    f"ADK tool '{adk_tool_to_expose.name}' initialized and ready to be exposed via MCP."
)

# MCP Server Setup
log("Creating MCP Server instance...")
app = Server("adk-tool-exposing-mcp-server")


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    log("MCP Server: Received list_tools request.")
    mcp_tool_schema = adk_to_mcp_tool_type(adk_tool_to_expose)
    log(f"MCP Server: Advertising tool: {mcp_tool_schema.name}")
    return [mcp_tool_schema]


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    """MCP handler to execute a tool call requested by an MCP client."""
    log(
        f"MCP Server: Received call_tool request for '{name}' with args: {arguments}"
    )

    if name == adk_tool_to_expose.name:
        try:
            adk_tool_response = await adk_tool_to_expose.run_async(
                args=arguments,
                tool_context=None,
            )
            log(
                f"MCP Server: ADK tool '{name}' executed. Response: {adk_tool_response}"
            )

            response_text = json.dumps(adk_tool_response, indent=2)
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            log(f"MCP Server: Error executing ADK tool '{name}': {e}")
            error_text = json.dumps(
                {"error": f"Failed to execute tool '{name}': {str(e)}"}
            )
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        log(f"MCP Server: Tool '{name}' not found/exposed by this server.")
        error_text = json.dumps(
            {"error": f"Tool '{name}' not implemented by this server."}
        )
        return [mcp_types.TextContent(type="text", text=error_text)]


# MCP Server Runner
async def run_mcp_stdio_server():
    """Runs the MCP server, listening for connections over standard input/output."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        log("MCP Stdio Server: Starting handshake with client...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        log("MCP Stdio Server: Run loop finished or client disconnected.")


if __name__ == "__main__":
    log("Launching MCP Server to expose ADK tools via stdio...")
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        log("\nMCP Server (stdio) stopped by user.")
    except Exception as e:
        log(f"MCP Server (stdio) encountered an error: {e}")
    finally:
        log("MCP Server (stdio) process exiting.")
