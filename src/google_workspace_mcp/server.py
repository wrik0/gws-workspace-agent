import os
from mcp.server.fastmcp import FastMCP
from .config import GWS_MODE

# Initialize FastMCP Server
mcp = FastMCP("WorkspaceAgent")

def register_tools() -> None:
    """Register read and optionally write tools based on configured mode."""
    # Stub: read tools are always registered
    # Stub: write tools registered only if GWS_MODE is "full"
    pass

# Run execution wrapper
def run() -> None:
    register_tools()
    mcp.run()
