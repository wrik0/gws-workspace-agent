# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

from mcp.server.fastmcp import FastMCP
from .config import GWS_MODE
from .tools.read import register_read_tools
from .tools.write import register_write_tools

# Initialize FastMCP Server
mcp = FastMCP("WorkspaceAgent")


def register_tools() -> None:
    """Register read and optionally write tools based on configured mode."""
    register_read_tools(mcp)
    if GWS_MODE == "full":
        register_write_tools(mcp)


# Run execution wrapper
def run() -> None:
    register_tools()
    mcp.run()
