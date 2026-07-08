# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import os
import sys
import shutil
import argparse


def auth() -> None:
    """gws-auth command entrypoint. Initiates OAuth workflow with user selection."""
    parser = argparse.ArgumentParser(
        description="Initiate Google Workspace MCP OAuth flow"
    )
    parser.add_argument(
        "--profile",
        help="Access profile name. Overrides GWS_PROFILE environment variable.",
    )
    args = parser.parse_args()

    if args.profile:
        os.environ["GWS_PROFILE"] = args.profile

    # Load dependencies locally after environment override is applied
    from .config import TOKEN_PATH
    from .auth import load_credentials

    print("========================================")
    print(" Google Workspace MCP - OAuth Setup     ")
    print("========================================")
    print("Select Google Calendar access scope:")
    print("  1. Full Access (Read/Write events) [DEFAULT]")
    print("  2. Read-only Access (View events only)")
    print("========================================")

    try:
        choice = input("Enter selection [1/2]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAuthentication setup cancelled.")
        sys.exit(1)

    mode = "readonly" if choice == "2" else "full"
    print(f"\nInitiating OAuth flow for mode: '{mode}'...")

    try:
        creds = load_credentials(mode=mode, interactive=True)
        print("\n[+] Authentication completed successfully!")
        print(f"Token saved to: {TOKEN_PATH}")
        print(f"Verified Scope(s): {', '.join(creds.scopes)}")
    except Exception as e:
        print(f"\n[-] Authentication failed: {e}")
        sys.exit(1)


def serve() -> None:
    """gws-serve command entrypoint. Runs FastMCP server."""
    parser = argparse.ArgumentParser(description="Run the Workspace MCP server")
    parser.add_argument(
        "--init-rules",
        action="store_true",
        help="Write gws_agent_rules.md to current directory",
    )
    parser.add_argument(
        "--export-colors",
        action="store_true",
        help="Write colors.default.json to current directory",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "readonly"],
        help="Access mode (full/readonly). Overrides GWS_MODE environment variable.",
    )
    parser.add_argument(
        "--readonly",
        action="store_true",
        help="Shortcut to run the server in read-only mode. Overrides GWS_MODE.",
    )
    parser.add_argument(
        "--pii-mode",
        choices=["none", "redact", "metadata_only"],
        help="PII scrubbing level (none/redact/metadata_only). Overrides GWS_PII_MODE environment variable.",
    )
    parser.add_argument(
        "--profile",
        help="Access profile name. Overrides GWS_PROFILE environment variable.",
    )
    parser.add_argument(
        "--allowed-domains",
        help="Comma-separated internal domains. Overrides GWS_ALLOWED_DOMAINS environment variable.",
    )
    args = parser.parse_args()

    if args.profile:
        os.environ["GWS_PROFILE"] = args.profile
    if args.readonly:
        os.environ["GWS_MODE"] = "readonly"
    elif args.mode:
        os.environ["GWS_MODE"] = args.mode
    if args.pii_mode:
        os.environ["GWS_PII_MODE"] = args.pii_mode
    if args.allowed_domains:
        os.environ["GWS_ALLOWED_DOMAINS"] = args.allowed_domains

    # Load dependencies locally after overrides are applied
    from .config import (
        GWS_MODE,
        GWS_PII_MODE,
        GWS_ALLOWED_DOMAINS,
        GWS_PROFILE,
        TOKEN_PATH,
        CREDENTIALS_PATH,
    )

    if args.init_rules:
        from pathlib import Path

        print("gws-serve: Exporting agent rules...")
        from .templates import DEFAULT_AGENT_RULES

        try:
            Path("gws_agent_rules.md").write_text(DEFAULT_AGENT_RULES, encoding="utf-8")
            print("Successfully exported gws_agent_rules.md to current directory.")
        except Exception as e:
            print(f"Error exporting agent rules: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.export_colors:
        from pathlib import Path

        print("gws-serve: Exporting default colors config...")
        from .templates import DEFAULT_COLORS_JSON

        try:
            Path("colors.default.json").write_text(
                DEFAULT_COLORS_JSON, encoding="utf-8"
            )
            print("Successfully exported colors.default.json to current directory.")
        except Exception as e:
            print(f"Error exporting colors config: {e}")
            sys.exit(1)
        sys.exit(0)

    # Output starting parameters to stderr so we don't corrupt the stdout stdio channel
    sys.stderr.write("========================================\n")
    sys.stderr.write(" Google Workspace MCP Server Starting   \n")
    sys.stderr.write("========================================\n")
    sys.stderr.write(f" Profile:             {GWS_PROFILE}\n")
    sys.stderr.write(f" Access Mode:         {GWS_MODE}\n")
    sys.stderr.write(f" PII Scrubbing Mode:  {GWS_PII_MODE}\n")
    if GWS_ALLOWED_DOMAINS:
        sys.stderr.write(f" Whitelisted Domains: {', '.join(GWS_ALLOWED_DOMAINS)}\n")
    else:
        sys.stderr.write(
            " Whitelisted Domains: (None configured - fallback to primary calendar domain)\n"
        )
    sys.stderr.write(f" Token Storage Path:  {TOKEN_PATH}\n")
    sys.stderr.write(f" Credentials Path:    {CREDENTIALS_PATH}\n")
    sys.stderr.write("========================================\n")
    sys.stderr.flush()

    from .server import run as run_server

    run_server()


def purge() -> None:
    """gws-purge command entrypoint. Deletes user tokens/credentials."""
    parser = argparse.ArgumentParser(
        description="Purge application configurations and tokens"
    )
    parser.add_argument(
        "--token-only",
        action="store_true",
        help="Purge only credentials token, keeping GCP secret configuration",
    )
    parser.add_argument(
        "--profile",
        help="Access profile name. Overrides GWS_PROFILE environment variable.",
    )
    args = parser.parse_args()

    if args.profile:
        os.environ["GWS_PROFILE"] = args.profile

    # Load dependencies locally after overrides are applied
    from .config import TOKEN_PATH, APP_DIR

    if args.token_only:
        if TOKEN_PATH.exists():
            print(f"Removing token file: {TOKEN_PATH}")
            try:
                TOKEN_PATH.unlink()
                print("Token purged successfully.")
            except Exception as e:
                print(f"Error removing token file: {e}")
                sys.exit(1)
        else:
            print(f"No token file found at {TOKEN_PATH} to purge.")
    else:
        print(
            f"WARNING: This will delete the entire configuration directory: {APP_DIR}"
        )
        try:
            confirm = (
                input("Are you sure you want to continue? [y/N]: ").strip().lower()
            )
        except (KeyboardInterrupt, EOFError):
            print("\nPurge cancelled.")
            sys.exit(1)

        if confirm == "y":
            if APP_DIR.exists():
                print(f"Deleting config directory: {APP_DIR}")
                try:
                    shutil.rmtree(APP_DIR)
                    print("All configurations purged successfully.")
                except Exception as e:
                    print(f"Error removing config directory: {e}")
                    sys.exit(1)
            else:
                print(f"Config directory does not exist: {APP_DIR}")
        else:
            print("Purge cancelled.")
