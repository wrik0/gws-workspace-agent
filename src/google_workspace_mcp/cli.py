import sys
import argparse

def auth() -> None:
    """gws-auth command entrypoint. Initiates OAuth workflow."""
    print("gws-auth: Initiating authentication flow...")
    # Stub implementation

def serve() -> None:
    """gws-serve command entrypoint. Runs FastMCP server."""
    parser = argparse.ArgumentParser(description="Run the Workspace MCP server")
    parser.add_argument("--init-rules", action="store_true", help="Write gws_agent_rules.md to current directory")
    parser.add_argument("--export-colors", action="store_true", help="Write colors.default.json to current directory")
    args = parser.parse_args()

    if args.init_rules:
        print("gws-serve: Exporting agent rules...")
        # Stub implementation
        sys.exit(0)

    if args.export-colors:
        print("gws-serve: Exporting default colors config...")
        # Stub implementation
        sys.exit(0)

    print("gws-serve: Launching FastMCP Server...")
    # Stub implementation

def purge() -> None:
    """gws-purge command entrypoint. Deletes user tokens/credentials."""
    parser = argparse.ArgumentParser(description="Purge application configurations and tokens")
    parser.add_argument("--token-only", action="store_true", help="Purge only credentials token, keeping GCP secret configuration")
    args = parser.parse_args()
    
    print("gws-purge: Purging files...")
    # Stub implementation
