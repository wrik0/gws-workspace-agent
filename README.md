# Google Workspace MCP Server

[![CI Status](https://github.com/wrik0/gws-workspace-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/wrik0/gws-workspace-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

A hardened, safety-first Google Calendar Model Context Protocol (MCP) server designed for enterprise reliability, strict data isolation, and deep agentic workflow integrations. This server empowers AI agents (like Claude Desktop, Cursor, or Antigravity) to read and manage calendars while enforcing strict user-defined security limits at runtime.

---

## ✨ Core Features & Safety Constraints

To protect user accounts and prevent unauthorized modifications, the server implements multiple runtime safeguards:

*   **🔒 Domain Boundary Whitelist**: Blocks agents from sending calendar invites to external or unauthorized email domains (via `GWS_ALLOWED_DOMAINS`).
*   **🛡️ PII & Description Scrubber**: Redacts email addresses, phone numbers, and meeting details dynamically based on privacy levels (`GWS_PII_MODE`).
*   **👥 Double-Booking Prevention**: Checks calendar availability automatically before booking an event unless the client explicitly requests an override (`ignore_availability=True`).
*   **⚠️ Two-Turn Delete Flow**: Forces a dry-run confirmation step for event deletions, returning a detailed preview card before executing changes.
*   **📁 Profile-Based Token Storage**: Isolates authentication tokens based on `GWS_PROFILE` to allow multi-tenant/account setups (e.g., separating personal and corporate accounts).
*   **⏱️ API Rate Limiter**: Enforces a global minimum interval of 100ms between calls to avoid flooding Google Cloud API quotas.
*   **📝 Structured Audit Logging**: Appends timestamped, owner-only readable (`chmod 600`) JSON log lines for all modifying actions.

---

## 🚀 Quick Start & Installation

### 1. Run the Interactive Installer (Recommended)
We provide an interactive installer script that handles virtual environments, fetches dependencies, guides you through placing your Google credentials, runs the auth flow, and auto-injects configuration settings into Claude Desktop:

```bash
# Clone the repository and kick off the configuration engine
curl -fsSL https://raw.githubusercontent.com/wrik0/gws-workspace-agent/master/setup.sh | bash
```

Alternatively, if you already cloned the repository locally:
```bash
./setup.sh
```

You can also configure a custom profile (e.g., `work`) during setup:
```bash
./setup.sh --profile work
```

### 2. Manual Installation
If you prefer to configure the environment manually:
```bash
# Clone the repository
git clone https://github.com/wrik0/gws-workspace-agent.git
cd gws-workspace-agent

# Set up environment and install package in editable mode
uv venv
uv pip install -e ".[dev]"
```

### 3. Google OAuth Setup
Before running the server, place your Google Cloud Client Secrets file (`credentials.json`) in the standard application data folder:
*   **Linux**: `~/.config/google-workspace-mcp/credentials.json`
*   **macOS**: `~/Library/Application Support/google-workspace-mcp/credentials.json`
*   **Windows**: `%APPDATA%\gws\google-workspace-mcp\credentials.json`

Next, run the CLI authorization utility:
```bash
# Performs browser login and caches the OAuth token
# On Unix (using the symlinked binary):
gws-auth
# Or directly via virtual environment:
.venv/bin/gws-auth
```

---

## ⚙️ Environment Configuration

You can configure the server behaviour using environment variables or equivalent command-line options when serving:

| Environment Variable | CLI Option | Default | Description |
| :--- | :--- | :--- | :--- |
| `GWS_PROFILE` | `--profile` | `default` | Workspace profile name. Resolves to `token_{GWS_PROFILE}.json`. |
| `GWS_MODE` | `--mode` / `--readonly` | `full` | Mode of operation: `full` (read/write tools) or `readonly` (read tools only). |
| `GWS_PII_MODE` | `--pii-mode` | `redact` | Privacy filter: `none` (no masking), `redact` (phone/emails masked), `metadata_only` (description/title removed). |
| `GWS_ALLOWED_DOMAINS`| `--allowed-domains` | None | Comma-separated domain whitelist for invitees (e.g. `company.com,partner.org`). |
| `GWS_TIMEZONE` | None | System Local | Local timezone database name (e.g. `America/New_York` or `Asia/Kolkata`). |
| `GWS_AUDIT_LOG` | None | `APP_DIR/audit.log` | Destination path for the append-only JSON audit logs. |

---

## 🛠 Command Line Interface (CLI)

The package exposes three entry points:

### `gws-serve`
Starts the stdio FastMCP server.
```bash
gws-serve --mode readonly --pii-mode redact --allowed-domains company.com
```

### `gws-auth`
Starts the OAuth token refresh browser loop.
```bash
# Request only read-only scopes from Google
gws-auth --mode readonly
# Request write scopes (requires verification if app is in sandbox)
gws-auth --mode full
```

### `gws-purge`
Purges cached tokens and credentials files.
```bash
# Deletes cached token file but leaves credentials.json intact
gws-purge --token-only
# Deletes the entire application config directory
gws-purge --all
```

---

## 🔌 Client Integration

### Claude Desktop
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "~/.local/bin/gws-serve",
      "args": ["--readonly", "--pii-mode", "redact"],
      "env": {
        "GWS_ALLOWED_DOMAINS": "mycompany.com"
      }
    }
  }
}
```

### Cursor IDE
Navigate to **Cursor Settings** > **Features** > **MCP** > **+ Add New MCP Server**:
*   **Name**: `google-workspace`
*   **Type**: `command`
*   **Command**: `~/.local/bin/gws-serve --readonly --pii-mode redact`

---

## 📦 MCP Tools Reference

### Read Tools (Available in `readonly` and `full` modes)
*   **`list_calendars()`**: Lists all calendars in the account with their name, ID, and access roles (e.g. owner, reader).
*   **`view_schedule(time_min, time_max, calendar_id="primary")`**: Displays events in a specific window. Outputs summary, times, descriptions, and color emojis (derived from Google Color IDs).
*   **`find_slots(time_min, time_max, duration_minutes, calendar_id="primary")`**: Queries free/busy state and aggregates open slots available for scheduling.

### Write Tools (Available only in `full` mode)
*   **`create_event(summary, start_iso, end_iso, ...)`**: Creates a calendar event. Validates invitee domains, checks double-booking conflicts, and records the action in `audit.log`.
*   **`move_event(event_id, new_start_iso, new_end_iso)`**: Shift events in time via a single `PATCH` API request.
*   **`modify_event(event_id, ...)`**: Dynamically updates text details or appends new whitelisted attendees.
*   **`delete_event(event_id, confirm=False)`**: Two-turn deletion flow. Run with `confirm=False` to inspect the event details card, and run with `confirm=True` to execute the API call.

---

## 🧪 Developer & Testing Suite

We use `pytest` for unit testing. The test suite uses mocks to fully simulate Google Cloud services and config directories:

```bash
# Run pytest locally
.venv/bin/pytest -v
```

### Style & Format Enforcement
To maintain code quality, run Ruff checkers:
```bash
# Format codebase
.venv/bin/ruff format
# Run linter checks
.venv/bin/ruff check --fix
```

---

## 📄 License
This project is licensed under the terms of the MIT license.
