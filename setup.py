# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# ANSI colors for styling
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
NC = "\033[0m"

BANNER = f"""{BLUE}
  ____                      _        __        __           _                               
 / ___| ___   ___   __ _  | |  ___  \\ \\      / /___  _ __ | | __ ___  _ __   __ _   ___  ___ 
| |  _ / _ \\ / _ \\ / _` | | | / _ \\  \\ \\ /\\ / // _ \\| '__|| |/ // __|| '_ \\ / _` | / __|/ _ \\
| |_| | (_) | (_) | (_| | | ||  __/   \\ V  V /| (_) || |   |   < \\__ \\| |_) | (_| || (__|  __/
 \\____|\\___/ \\___/ \\__, | |_| \\___|    \\_/\\_/  \\___/ |_|   |_|\\_\\|___/| .__/ \\__,_| \\___|\\___|
                   |___/                                              |_|                     
{NC}"""


def print_step(title: str):
    print(f"\n{BLUE}{BOLD}[*] {title}{NC}")


def print_success(msg: str):
    print(f"{GREEN}✔ {msg}{NC}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠ {msg}{NC}")


def print_error(msg: str):
    print(f"{RED}✘ {msg}{NC}")


def safe_input(prompt: str, default: str = "") -> str:
    try:
        return input(prompt)
    except EOFError:
        print()
        return default


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Google Workspace MCP Server setup tool"
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="Profile name to configure (defaults to 'default')",
    )
    args, unknown = parser.parse_known_args()
    profile = args.profile

    print(BANNER)
    print(
        f"{BOLD}Welcome to the Google Workspace MCP Server setup tool! (Profile: '{profile}'){NC}\n"
    )

    project_dir = Path(__file__).parent.resolve()

    # -------------------------------------------------------------------------
    # Step 1: Virtual Environment Setup
    # -------------------------------------------------------------------------
    print_step("Setting up virtual Python environment...")
    venv_dir = project_dir / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_success("Virtual environment created.")
    else:
        print("Virtual environment already exists.")

    # Determine paths inside venv
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
        venv_auth = venv_dir / "Scripts" / "gws-auth.exe"
        venv_serve = venv_dir / "Scripts" / "gws-serve.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"
        venv_auth = venv_dir / "bin" / "gws-auth"
        venv_serve = venv_dir / "bin" / "gws-serve"

    install_serve = venv_serve
    install_auth = venv_auth

    # Install package
    print("Installing dependencies...")
    # Check if uv is available in the user path
    uv_path = shutil.which("uv")
    if uv_path:
        print("Detected 'uv'. Installing package in editable mode via uv...")
        subprocess.run(
            [uv_path, "pip", "install", "--python", str(venv_python), "-e", "."],
            check=True,
        )
    else:
        print("Installing package in editable mode via pip...")
        subprocess.run([str(venv_pip), "install", "-e", "."], check=True)
    print_success("Package installed successfully.")

    # Link/Install Executables to ~/.local/bin (Unix only)
    if sys.platform != "win32":
        local_bin_dir = Path.home() / ".local" / "bin"
        try:
            local_bin_dir.mkdir(parents=True, exist_ok=True)
            for bin_name in ["gws-auth", "gws-serve", "gws-purge"]:
                venv_bin_path = venv_dir / "bin" / bin_name
                target_bin_path = local_bin_dir / bin_name
                if venv_bin_path.exists():
                    if target_bin_path.exists() or target_bin_path.is_symlink():
                        target_bin_path.unlink()
                    target_bin_path.symlink_to(venv_bin_path)
            print_success(f"Linked command line tools to {local_bin_dir}")
            install_serve = local_bin_dir / "gws-serve"
            install_auth = local_bin_dir / "gws-auth"
        except Exception as e:
            print_warning(
                f"Could not symlink command line tools to {local_bin_dir}: {e}"
            )

    # -------------------------------------------------------------------------
    # Step 2: Google Workspace Credentials
    # -------------------------------------------------------------------------
    print_step("Checking Google Cloud credentials...")

    # Resolve target directory based on OS
    if sys.platform == "win32":
        app_dir = Path(os.environ.get("APPDATA")) / "gws" / "google-workspace-mcp"
    elif sys.platform == "darwin":
        app_dir = (
            Path.home() / "Library" / "Application Support" / "google-workspace-mcp"
        )
    else:
        app_dir = Path.home() / ".config" / "google-workspace-mcp"

    credentials_path = app_dir / "credentials.json"

    if not credentials_path.exists():
        print_warning(
            f"No credentials.json found at default location: {credentials_path}"
        )
        print("To fetch your Google API credentials:")
        print("  1. Go to Google Cloud Console (https://console.cloud.google.com).")
        print("  2. Create a desktop application OAuth Client ID.")
        print("  3. Download the client secrets JSON file.")

        user_input = safe_input(
            "\nEnter path to downloaded client secret JSON file (leave empty to skip): ",
            default="",
        ).strip()
        if user_input:
            src_file = Path(user_input).expanduser().resolve()
            if src_file.exists():
                app_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, credentials_path)
                print_success(f"Copied credentials to {credentials_path}")
            else:
                print_error(f"File not found: {src_file}. Skipping credentials copy.")
        else:
            print("Skipped copying credentials. Remember to copy them later.")
    else:
        print_success(f"Credentials verified at {credentials_path}")

    # -------------------------------------------------------------------------
    # Step 3: OAuth Authentication
    # -------------------------------------------------------------------------
    if credentials_path.exists():
        print_step("OAuth Authentication")
        run_auth = (
            safe_input(
                "Would you like to run the authentication loop now? (y/N): ",
                default="n",
            )
            .strip()
            .lower()
        )
        if run_auth == "y" or run_auth == "yes":
            try:
                subprocess.run([str(install_auth), "--profile", profile], check=True)
                print_success("OAuth authentication completed successfully.")
            except subprocess.CalledProcessError:
                print_error(
                    f"OAuth authentication failed. You can run it later using 'gws-auth --profile {profile}'."
                )
    else:
        print_warning(
            "Skipping OAuth authentication since credentials.json is not present."
        )

    # -------------------------------------------------------------------------
    # Step 4: Configure MCP Clients
    # -------------------------------------------------------------------------
    print_step("Auto-detecting and configuring MCP clients...")

    # --- Claude Desktop ---
    if sys.platform == "darwin":
        claude_config_path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    else:
        claude_config_path = (
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        )

    if claude_config_path.parent.exists() or safe_input(
        "Configure Claude Desktop server settings anyway? (y/N): ", default="n"
    ).strip().lower() in ["y", "yes"]:
        try:
            claude_config_path.parent.mkdir(parents=True, exist_ok=True)
            if claude_config_path.exists():
                with open(claude_config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            else:
                config_data = {}

            if "mcpServers" not in config_data:
                config_data["mcpServers"] = {}

            server_name = (
                "google-workspace"
                if profile == "default"
                else f"google-workspace-{profile}"
            )

            # Add google-workspace server entry
            config_data["mcpServers"][server_name] = {
                "command": str(install_serve),
                "args": ["--profile", profile, "--readonly", "--pii-mode", "redact"],
            }

            with open(claude_config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)

            print_success(f"Configured Claude Desktop at {claude_config_path}")
        except Exception as e:
            print_error(f"Failed to update Claude Desktop configuration: {e}")

    server_name = (
        "google-workspace" if profile == "default" else f"google-workspace-{profile}"
    )

    # --- Cursor ---
    print("\n--- Cursor Integration ---")
    print("To configure the server in Cursor IDE:")
    print("  1. Open Cursor -> Settings -> Features -> MCP.")
    print("  2. Add new MCP server:")
    print(f"     - Name: {server_name}")
    print("     - Type: command")
    print(
        f"     - Command: {install_serve} --profile {profile} --readonly --pii-mode redact"
    )

    # --- Antigravity ---
    print("\n--- Antigravity CLI Integration ---")
    print(
        "To run this server in the Antigravity Terminal Agent environment, add the server to"
    )
    print("your agent configurations:")
    print(f"  Command: {install_serve}")
    print(f"  Arguments: --profile {profile} --readonly --pii-mode redact")

    # --- OpenAPI / Other Agents ---
    print("\n--- OpenAPI & General Agents Integration ---")
    print("This server is fully standard-compliant over stdio.")
    print(
        f"You can launch it as a subprocess using: {install_serve} --profile {profile}"
    )

    print_step("Setup Complete!")
    print("You can run your server with Full or Read-Only modes.")
    print("Feel free to test out tool runs or start your calendar workflow.")
    print(f"{GREEN}Ready to serve!{NC}\n")


if __name__ == "__main__":
    main()
