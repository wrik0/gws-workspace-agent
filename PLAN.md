# google-workspace-mcp — Complete Project Plan

> **Status:** Pre-implementation planning complete  
> **Last updated:** 2026-07-06  
> **Source:** Synthesized from base project analysis, competitive gap research, and two AI planning sessions

---

## Table of Contents

1. [Project Identity & Pitch](#1-project-identity--pitch)
2. [Why This Exists — The 6 Gaps](#2-why-this-exists--the-6-gaps)
3. [Competitive Landscape](#3-competitive-landscape)
4. [Architecture Overview](#4-architecture-overview)
5. [Folder Structure](#5-folder-structure)
6. [Package & Distribution](#6-package--distribution)
7. [Configuration & Storage](#7-configuration--storage)
8. [Authentication Module](#8-authentication-module)
9. [Tool Specifications](#9-tool-specifications)
   - 9a. [delete_event — Full Design](#9a-delete_event--full-design)
10. [Safety Harness (6 Layers)](#10-safety-harness-6-layers)
11. [Agent Behavior Rules](#11-agent-behavior-rules-gws_agent_rulesmd)
12. [CLI Commands](#12-cli-commands)
13. [Color System](#13-color-system)
14. [Milestone Checklist](#14-milestone-checklist)
15. [Open Questions](#15-open-questions)

---

## 1. Project Identity & Pitch

| Field | Value |
|---|---|
| Package name | `google-workspace-mcp` |
| Repo | `wrik0/gws-mcp-agent` |
| CLI prefix | `gws-*` |
| Primary scope | Google Calendar (v1) |
| Gmail / Drive | Stubs only — v2+ |
| License | MIT |

**The pitch:**
> *"The Calendar MCP server that doesn't break, enforces real safety boundaries, and ships with agent behavior rules built in."*

**What this is NOT:**
- Not a taylorwilsdon replacement (12 services — don't compete on breadth)
- Not a Gmail server (too risky, sidelined to v2)
- Not enterprise-first (no Service Account auth in v1)

**What this IS:**
- The server people switch **to** when their current one breaks at 1am
- Calendar-focused, depth over breadth
- Safety-first: read-only mode enforced at OAuth scope AND tool level
- Agent-first: ships `gws_agent_rules.md` (no other MCP server does this)

---

## 2. Why This Exists — The 6 Gaps

Every major alternative shares the same production bugs and missing safety primitives.

### Gap 1 — Token Refresh Persistence Bug 🔴 CRITICAL

**Problem:** All servers call `Credentials.refresh(Request())` but never write
the updated token back to disk. The server works for ~1 hour, then fails silently.

**Root cause in existing servers:**
```python
# What everyone does (broken):
creds.refresh(Request())
return build(api_name, api_version, credentials=creds)
# token.json on disk is now stale — next restart fails
```

**Our fix:**
```python
# What we do (correct):
creds.refresh(Request())
with open(TOKEN_PATH, "w") as f:
    f.write(creds.to_json())  # ← THE 3 LINES NOBODY WRITES
TOKEN_PATH.chmod(0o600)
return build(api_name, api_version, credentials=creds)
```

---

### Gap 2 — True Read-Only Mode 🔴 CRITICAL

**Problem:** Competitors either:
- Grant full write scope but tell the agent not to use write tools (honor system)
- Remove write tools by hand in a fork (blunt, not configurable)

Neither enforces at the OAuth layer. OpenAI Codex Issue #23995:
> *"Relying on agent behavior to avoid write tools is not a sufficiently strong trust boundary."*

**Our approach — two simultaneous enforcement layers:**

```
GWS_MODE=readonly
    │
    ├── OAuth layer: requests calendar.readonly scope
    │   (Google will reject write API calls server-side)
    │
    └── Tool layer: write tools are NOT REGISTERED
        (agent never sees them in its tool list — not just disabled)
```

Write tools are **hidden**, not erroring. The agent's context is clean.

---

### Gap 3 — MCP Tool Annotations 🟠 HIGH

**Problem:** MCP spec (post-2025) added tool-level annotations. Nobody uses them.

**What they enable:** Claude Desktop, Cursor, AGY can enforce their own
confirmation UX based on `destructiveHint` without server-side logic.

**Our implementation:**
```python
@mcp.tool(annotations={"readOnlyHint": True})
def view_schedule(...): ...

@mcp.tool(annotations={"destructiveHint": True})
def delete_event(...): ...
```

This is forward-compatible — as MCP clients evolve, they'll use these.

---

### Gap 4 — Availability Query (find_slots) 🟠 HIGH

**Problem:** No `freebusy` API integration. Agents must call `view_schedule`,
parse all events, infer free slots — burning LLM tokens on parsing work.

**Our fix:** `find_slots()` wraps `freebusy().query()` directly.
- One API call returns busy blocks for user AND invitees simultaneously
- Tool returns available windows (not busy blocks) — agent-ready output
- No event parsing by the LLM required

---

### Gap 5 — Multi-Calendar Support 🟠 HIGH

**Problem:** Everything hardcodes `calendarId="primary"`.
Power users have work, personal, and shared team calendars.

**Our fix:** `calendar_id: str = "primary"` parameter on all tools
plus a `list_calendars()` tool to discover available IDs.

---

### Gap 6 — Agent Behavior Rules (Meta-Agent Layer) 🟡 DIFFERENTIATOR

**Problem:** No competitor ships behavioral instructions for the agent.
They ship Python. The agent figures out safety on its own.

**Our fix:** `gws_agent_rules.md` — a template that ships with the package,
dropped into the user's agent config directory via `gws-serve --init-rules`.

This is **meta-agent design** — a layer above the MCP tools.
No other MCP server in the ecosystem does this.

---

## 3. Competitive Landscape

| Project | Lang | Services | Auth | Token Bug | Read-Only | Annotations | AGENTS.md |
|---|---|---|---|---|---|---|---|
| taylorwilsdon/google_workspace_mcp | Python | 12 | OAuth 2.1 | ❌ Yes | ❌ Scope only | ❌ | ❌ |
| tumf/fastmcp-gsuite | Python/FastMCP | 3 | OAuth 2.0 | ❌ Yes | ❌ | ❌ | ❌ |
| j3k0/mcp-google-workspace | Python | 2 | OAuth 2.0 | ❌ Yes | ❌ | ❌ | ❌ |
| ngs/google-mcp-server | Go | 7 | OAuth + SA | ❌ Yes | ❌ | ❌ | ❌ |
| c0webster/hardened-gws-mcp | Python | 1 (read) | OAuth 2.0 | ❌ Yes | ⚠️ Tool removal | ❌ | ❌ |
| **This project** | Python/FastMCP | 1 (deep) | OAuth 2.0 | ✅ Fixed | ✅ Scope + tools | ✅ | ✅ |

**Positioning:** Don't compete on breadth. Win on reliability + safety + agent UX.

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client                               │
│         (Claude Desktop / Cursor / AGY / etc.)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ stdio / MCP protocol
┌──────────────────────▼──────────────────────────────────────┐
│                  gws-serve (FastMCP)                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              server.py                              │   │
│  │  Mode-gated tool registration                       │   │
│  │  GWS_MODE=readonly → register READ tools only       │   │
│  │  GWS_MODE=full     → register READ + WRITE tools    │   │
│  └──────────────┬──────────────────┬───────────────────┘   │
│                 │                  │                        │
│  ┌──────────────▼────┐   ┌─────────▼──────────────────┐   │
│  │   tools/read.py   │   │     tools/write.py          │   │
│  │                   │   │                             │   │
│  │  view_schedule    │   │  create_event               │   │
│  │  list_calendars   │   │  move_event                 │   │
│  │  find_slots       │   │  modify_event               │   │
│  └──────────────┬────┘   │  delete_event (dry-run)     │   │
│                 │        └─────────┬──────────────────-┘   │
│                 └────────┬─────────┘                        │
│                          │                                   │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │              middleware/                             │   │
│  │  rate_limiter.py  → token bucket (100ms between)    │   │
│  │  audit.py         → JSON mutation log               │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │              auth.py                                │   │
│  │  load_credentials() → fixed refresh + re-save       │   │
│  │  7-day expiry detection + clean error               │   │
│  │  chmod 600 enforcement                              │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────▼─────────────────────────────┐   │
│  │              config.py                              │   │
│  │  platformdirs XDG paths                             │   │
│  │  Env vars: GWS_MODE, GWS_TIMEZONE, etc.             │   │
│  │  Color map: JSON config with safe fallback          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │   Google Calendar API  │
              │   (OAuth 2.0 scopes)   │
              └────────────────────────┘
```

---

## 5. Folder Structure

```
gws-mcp-agent/
│
├── PLAN.md                          ← This file
│
├── pyproject.toml                   ← uv/pip build config, entry points
├── README.md                        ← GCP setup, uvx one-liner, security notice
├── CHANGELOG.md
│
├── src/
│   └── google_workspace_mcp/
│       │
│       ├── __init__.py              ← version, __all__
│       │
│       ├── cli.py                   ← gws-auth, gws-serve, gws-purge entry points
│       │                              gws-serve --init-rules
│       │                              gws-serve --export-colors
│       │
│       ├── server.py                ← FastMCP("WorkspaceAgent") init
│       │                              Mode-gated tool registration
│       │                              mcp.run() entrypoint
│       │
│       ├── auth.py                  ← load_credentials() — fixed token lifecycle
│       │                              7-day expiry detection
│       │                              _save_token() — chmod 600 enforced
│       │
│       ├── config.py                ← platformdirs paths (XDG compliant)
│       │                              All env var defaults
│       │                              Color map loader with fallback
│       │                              SCOPE_SETS dict (full vs readonly)
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   │
│       │   ├── read.py              ← view_schedule (color-coded output)
│       │   │                          list_calendars
│       │   │                          find_slots (freebusy API)
│       │   │
│       │   └── write.py             ← create_event (with color_id, recurrence,
│       │                                             attendees, ignore_availability)
│       │                              move_event
│       │                              modify_event
│       │                              delete_event (self-contained dry-run)
│       │
│       └── middleware/
│           ├── __init__.py
│           ├── rate_limiter.py      ← @rate_limited decorator, 100ms bucket
│           └── audit.py             ← _audit(action, payload) → JSON log
│
├── templates/
│   ├── gws_agent_rules.md           ← Dropped by --init-rules into CWD
│   └── colors.default.json          ← Default color map, exported by --export-colors
│
├── tests/
│   ├── conftest.py                  ← Mocked Google API service fixtures
│   ├── test_auth.py                 ← Token refresh, expiry, chmod
│   ├── test_read_tools.py           ← view_schedule, find_slots, list_calendars
│   ├── test_write_tools.py          ← create, move, modify, delete (dry-run + confirm)
│   └── test_config.py               ← Color map fallback, env var overrides
│
├── examples/
│   ├── mcp.example.json             ← Generic MCP client config template
│   ├── claude_desktop_setup.md      ← Step-by-step Claude Desktop guide
│   └── antigravity_setup.md         ← AGY / Antigravity CLI guide
│
└── .github/
    └── workflows/
        └── ci.yml                   ← ruff + mypy + pytest on every PR
```

---

## 6. Package & Distribution

### Package Manager: `uv` (primary)

The MCP ecosystem has converged on `uv`. Claude Desktop and Cursor support
`uvx` as a zero-install runner — no `pip install` required by end users.

**User's `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["google-workspace-mcp", "serve"],
      "env": {
        "GWS_MODE": "full",
        "GWS_TIMEZONE": "Asia/Kolkata"
      }
    }
  }
}
```

**`pyproject.toml`:**
```toml
[project]
name = "google-workspace-mcp"
version = "0.1.0"
description = "A hardened Google Calendar MCP server with agent safety built in"
requires-python = ">=3.11"

dependencies = [
    "mcp>=1.27",
    "google-api-python-client>=2.197",
    "google-auth>=2.54",
    "google-auth-oauthlib>=1.4",
    "google-auth-httplib2>=0.4",
    "platformdirs>=4.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff", "mypy"]

[project.scripts]
gws-auth  = "google_workspace_mcp.cli:auth"
gws-serve = "google_workspace_mcp.cli:serve"
gws-purge = "google_workspace_mcp.cli:purge"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 7. Configuration & Storage

### XDG-Compliant Cross-Platform Paths (`platformdirs`)

```python
from platformdirs import user_config_dir
from pathlib import Path

APP_DIR = Path(user_config_dir("google-workspace-mcp", "gws"))
# Linux:   ~/.config/google-workspace-mcp/
# macOS:   ~/Library/Application Support/google-workspace-mcp/
# Windows: %APPDATA%\gws\google-workspace-mcp\

TOKEN_PATH       = APP_DIR / "token.json"
CREDENTIALS_PATH = APP_DIR / "credentials.json"
COLOR_CONFIG     = APP_DIR / "colors.json"
AUDIT_LOG        = APP_DIR / "audit.log"
```

### Environment Variables (all optional, have defaults)

| Variable | Default | Description |
|---|---|---|
| `GWS_MODE` | `full` | `full` or `readonly` |
| `GWS_TIMEZONE` | `UTC` | IANA timezone string |
| `GWS_MAX_WINDOW_DAYS` | `90` | Max date range for view_schedule |
| `GWS_TOKEN_PATH` | XDG path | Override token location |
| `GWS_CREDENTIALS_PATH` | XDG path | Override credentials location |
| `GWS_COLOR_CONFIG` | XDG path | Override color map JSON |
| `GWS_AUDIT_LOG` | XDG path | Override audit log path |

---

## 8. Authentication Module

### The Fixed Token Lifecycle

```python
# auth.py

SCOPE_SETS = {
    "full":     ["https://www.googleapis.com/auth/calendar"],
    "readonly": ["https://www.googleapis.com/auth/calendar.readonly"],
}

def load_credentials(mode: str = "full") -> Credentials:
    scopes = SCOPE_SETS[mode]

    # Security: warn if token file is world-readable
    if TOKEN_PATH.exists():
        perms = oct(TOKEN_PATH.stat().st_mode)[-3:]
        if perms not in ("600", "400"):
            warnings.warn(f"Token at {TOKEN_PATH} has perms {perms}. Run: chmod 600")

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _save_token(creds)          # ← The fix. Always persist.
            except Exception as e:
                if "revoked" in str(e).lower() or "invalid_grant" in str(e).lower():
                    raise RuntimeError(
                        "Refresh token revoked.\n\n"
                        "If your GCP app is in 'Testing' mode, Google revokes tokens\n"
                        "after 7 days. Fix:\n"
                        "  1. Go to GCP Console → OAuth consent screen → Publish, OR\n"
                        "     add your email as a test user to reset the 7-day timer\n"
                        "  2. Run: gws-purge --token-only && gws-auth"
                    )
                raise
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), scopes
            )
            creds = flow.run_local_server(port=0)
            _save_token(creds)

    return creds

def _save_token(creds: Credentials) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # chmod 600
```

---

## 9. Tool Specifications

### Tool Registration — Mode-Gated

```python
# server.py
MODE = os.getenv("GWS_MODE", "full")

from .tools.read import register_read_tools
register_read_tools(mcp)                         # Always registered

if MODE == "full":
    from .tools.write import register_write_tools
    register_write_tools(mcp)                    # Hidden in readonly mode
```

> **Key decision:** In `readonly` mode, write tools are **not registered at all**.
> They are invisible to the agent — not disabled, not erroring. Clean context.

---

### READ Tools

#### `view_schedule`
```python
@mcp.tool(annotations={"readOnlyHint": True})
def view_schedule(
    time_min: str,                    # ISO 8601 with timezone
    time_max: str,                    # ISO 8601 with timezone
    calendar_id: str = "primary",
    max_results: int = 50,
) -> str:
    """List calendar events in a time range with color-coded type labels.

    Window is capped at GWS_MAX_WINDOW_DAYS to prevent bulk data exposure.
    Returns events formatted with emoji type labels derived from color IDs.

    Example output:
        🟢 [Focus]  | ID: abc | Team Standup    | 09:00 → 09:30
        🔴 [Urgent] | ID: def | Deadline Review | 14:00 → 15:00
        💚 [Social] | ID: ghi | Lunch w/ Priya  | 13:00 → 14:00
    """
```

#### `list_calendars`
```python
@mcp.tool(annotations={"readOnlyHint": True})
def list_calendars() -> str:
    """List all calendars accessible to the user.

    Returns calendar IDs needed for multi-calendar operations.
    Call once per session and reuse the IDs.
    """
```

#### `find_slots`
```python
@mcp.tool(annotations={"readOnlyHint": True})
def find_slots(
    time_min: str,
    time_max: str,
    duration_minutes: int,
    calendar_ids: list[str] = None,       # Defaults to ["primary"]
    invitee_emails: list[str] = None,     # Check their freebusy too
) -> str:
    """Find open time slots using the Google freebusy API.

    Checks availability for the user AND all invitees in one API call.
    Returns available windows (not raw busy blocks) — agent-ready output.

    Use this instead of view_schedule for scheduling tasks.
    One API call vs. parsing all events manually.

    Example output:
        Available slots on July 8:
        • 09:00 – 10:30 (90 min) — all 3 attendees free
        • 14:00 – 16:00 (120 min) — all 3 attendees free
    """
```

---

### WRITE Tools (registered only when GWS_MODE=full)

#### `create_event`
```python
@mcp.tool(annotations={"destructiveHint": False})
def create_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    location: str = "",
    attendee_emails: list[str] = None,
    color_id: str = None,                 # Google Calendar color ID (1–11)
    recurrence: list[str] = None,         # RRULE e.g. ["RRULE:FREQ=WEEKLY"]
    calendar_id: str = "primary",
    ignore_availability: bool = False,    # Explicit double-booking override
) -> str:
    """Create a new calendar event. Returns event ID and HTML link.

    Use ignore_availability=True only when the user explicitly requests
    overlapping/conflicting bookings (e.g., "book it even if I'm busy").
    """
```

#### `move_event`
```python
@mcp.tool(annotations={"destructiveHint": False})
def move_event(
    event_id: str,
    new_start_iso: str,
    new_end_iso: str,
    calendar_id: str = "primary",
) -> str:
    """Change the start and end time of an existing event by ID."""
```

#### `modify_event`
```python
@mcp.tool(annotations={"destructiveHint": False})
def modify_event(
    event_id: str,
    new_summary: str = None,
    new_description: str = None,
    new_location: str = None,
    new_color_id: str = None,
    add_attendees: list[str] = None,
    calendar_id: str = "primary",
) -> str:
    """Modify text/metadata fields of an event (uses PATCH — only updates provided fields).
    For time changes, use move_event instead.
    """
```

---

### 9a. `delete_event` — Full Design

**The core design principle:**
The tool itself fetches all event context via the Google API (zero extra LLM calls).
On `confirm=False` (default), it returns a rich preview card.
The agent shows the card, waits for user confirmation, then calls again with `confirm=True`.

**Why this is better than alternatives:**

| Approach | API calls | LLM tokens spent | Safety |
|---|---|---|---|
| Old: just delete | 1 | 0 | ❌ Irreversible, no review |
| Naive: agent calls view_schedule first | 2+ | High (parse event list) | ⚠️ Medium |
| **This: tool fetches internally** | 2 (get + list surrounding) | Near-zero | ✅ Strong |

**The preview card output:**
```
=== 🗑  DELETE PREVIEW — call with confirm=True to execute ===

📌  Title:      Q3 Planning Session
📅  Date:       Tuesday, 8 July 2026
🕐  Time:       10:00 AM → 12:00 PM IST  (2 hrs)
📍  Location:   Conf Room B / meet.google.com/xyz-abc-def
🔁  Recurrence: This is a recurring event — only this instance will be deleted

👥  Attendees (4):
    ✅ you@company.com        — Accepted  (organizer)
    ✅ priya@company.com      — Accepted
    ❓ rahul@company.com      — Pending
    ❌ maya@company.com       — Declined

📝  Description:
    Quarterly planning review. Bring OKR updates and blockers.

📎  Linked Documents (2):
    • Q3 OKR Tracker.gsheet
    • Planning Agenda.gdoc

⏰  Availability after deletion:
    Frees up:              10:00 AM – 12:00 PM (2 hrs)
    Next event:            "Lunch with Priya" at 1:00 PM
    Total contiguous free: 09:00 AM – 01:00 PM (4 hrs)

⚠️  Deletion will send cancellation notifications to 3 attendees.

>>> To confirm: delete_event(event_id="abc123", confirm=True)
```

**Full implementation:**
```python
@mcp.tool(annotations={"destructiveHint": True})
def delete_event(
    event_id: str,
    confirm: bool = False,
    calendar_id: str = "primary",
) -> str:
    """Delete a calendar event by its ID.

    ALWAYS call twice:
    1. delete_event(event_id=...) → returns preview card with full event context.
       Fetches title, time, attendees, description, linked docs, and what
       contiguous free time opens up after deletion. Zero extra tool calls.
    2. delete_event(event_id=..., confirm=True) → executes deletion + audit log.

    Never call with confirm=True without showing the preview to the user first.
    """
    service = get_service()

    # Always fetch event first — even on confirm=True (needed for audit log)
    try:
        event = service.events().get(
            calendarId=calendar_id, eventId=event_id
        ).execute()
    except Exception as e:
        return f"Error: Could not fetch event '{event_id}'. It may not exist.\n{e}"

    tz        = ZoneInfo(os.getenv("GWS_TIMEZONE", "UTC"))
    start     = _parse_dt(event.get("start", {}), tz)
    end       = _parse_dt(event.get("end", {}), tz)
    summary   = event.get("summary", "(No title)")
    location  = event.get("location", "")
    desc      = event.get("description", "").strip()
    recur     = event.get("recurrence", [])
    attachments = event.get("attachments", [])
    attendees   = event.get("attendees", [])

    if start and end:
        mins = int((end - start).total_seconds() / 60)
        hrs, m = divmod(mins, 60)
        duration  = f"{hrs}h {m}m" if m else f"{hrs}h"
        start_fmt = start.strftime("%-I:%M %p")
        end_fmt   = end.strftime("%-I:%M %p %Z")
        date_fmt  = start.strftime("%A, %-d %B %Y")

    lines = ["=== 🗑  DELETE PREVIEW — call with confirm=True to execute ===\n"]
    lines.append(f"📌  Title:      {summary}")
    if start:
        lines.append(f"📅  Date:       {date_fmt}")
        lines.append(f"🕐  Time:       {start_fmt} → {end_fmt}  ({duration})")
    if location:
        lines.append(f"📍  Location:   {location}")
    if recur:
        lines.append(f"🔁  Recurrence: This is a recurring event — only this instance will be deleted")

    if attendees:
        rsvp = {"accepted": "✅", "declined": "❌", "tentative": "🟡", "needsAction": "❓"}
        lines.append(f"\n👥  Attendees ({len(attendees)}):")
        for a in attendees:
            icon = rsvp.get(a.get("responseStatus", "needsAction"), "❓")
            org  = "  (organizer)" if a.get("organizer") else ""
            status = a.get("responseStatus", "needsAction").replace("needsAction", "Pending").title()
            lines.append(f"    {icon} {a.get('email','?'):<30} — {status}{org}")

    if desc:
        preview = desc[:200] + ("…" if len(desc) > 200 else "")
        lines.append(f"\n📝  Description:\n    {preview}")

    if attachments:
        lines.append(f"\n📎  Linked Documents ({len(attachments)}):")
        for att in attachments:
            lines.append(f"    • {att.get('title', att.get('fileUrl', 'Unknown'))}")

    # Fetch surrounding events to compute contiguous free block
    if start and end:
        try:
            window_start = (start - timedelta(hours=2)).isoformat()
            window_end   = (end   + timedelta(hours=2)).isoformat()
            surrounding  = service.events().list(
                calendarId=calendar_id, timeMin=window_start, timeMax=window_end,
                singleEvents=True, orderBy="startTime",
            ).execute().get("items", [])

            others = [e for e in surrounding if e.get("id") != event_id]
            before = [e for e in others if _parse_dt(e.get("end",   {}), tz) and _parse_dt(e.get("end",   {}), tz) <= start]
            after  = [e for e in others if _parse_dt(e.get("start", {}), tz) and _parse_dt(e.get("start", {}), tz) >= end]

            free_from = _parse_dt(before[-1].get("end",   {}), tz) if before else start - timedelta(hours=2)
            free_to   = _parse_dt(after[0].get("start",  {}), tz) if after  else end   + timedelta(hours=2)
            total_min = int((free_to - free_from).total_seconds() / 60)
            h, m2     = divmod(total_min, 60)
            total_str = f"{h}h {m2}m" if m2 else f"{h}h"

            lines.append(f"\n⏰  Availability after deletion:")
            lines.append(f"    Frees up:              {start_fmt} – {end_fmt} ({duration})")
            if after:
                nxt = after[0]
                lines.append(f"    Next event:            \"{nxt.get('summary','?')}\" at {_parse_dt(nxt.get('start',{}), tz).strftime('%-I:%M %p')}")
            lines.append(f"    Total contiguous free: {free_from.strftime('%-I:%M %p')} – {free_to.strftime('%-I:%M %p')} ({total_str})")
        except Exception:
            lines.append(f"\n⏰  Availability after deletion: {start_fmt} – {end_fmt} freed")

    notify_count = len([a for a in attendees if not a.get("self")])
    if notify_count:
        lines.append(f"\n⚠️   Deletion will send cancellation notifications to {notify_count} attendee(s).")

    lines.append(f"\n>>> To confirm: delete_event(event_id=\"{event_id}\", confirm=True)")

    if not confirm:
        return "\n".join(lines)

    # Execute deletion
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    _audit("delete_event", {
        "event_id":  event_id,
        "summary":   summary,
        "start":     start.isoformat() if start else None,
        "attendees": [a.get("email") for a in attendees],
    })

    return (
        f"✅ Deleted: \"{summary}\" on {date_fmt} ({start_fmt} – {end_fmt})\n"
        f"   Freed {duration} back on your calendar."
    )
```

---

## 10. Safety Harness (6 Layers)

| # | Layer | What It Prevents | Where Implemented |
|---|---|---|---|
| 1 | Token file `chmod 600` | Credential leak via world-readable file | `auth.py` → `_save_token()` + startup check |
| 2 | Read-only mode (OAuth + tool) | Write operations when user wants read-only | `config.py` scope sets + `server.py` registration |
| 3 | `delete_event` dry-run | Accidental irreversible event loss | `confirm=False` default, self-contained preview |
| 4 | Date range cap | Bulk private calendar data exposure | `GWS_MAX_WINDOW_DAYS` check in `view_schedule` |
| 5 | Rate limiter | Google API quota exhaustion in agent loops | `@rate_limited` decorator, 100ms token bucket |
| 6 | Audit log | Untracked agent mutations | `_audit()` called before every write operation |

### Audit Log Format (append-only JSON lines)
```jsonl
{"ts":"2026-07-08T10:30:00Z","action":"delete_event","event_id":"abc123","summary":"Standup","start":"2026-07-08T09:00:00+05:30","attendees":["priya@co.com"]}
{"ts":"2026-07-08T10:31:00Z","action":"create_event","summary":"Deep Work","start":"2026-07-09T10:00:00+05:30","end":"2026-07-09T12:00:00+05:30"}
{"ts":"2026-07-08T10:32:00Z","action":"move_event","event_id":"def456","new_start":"2026-07-09T14:00:00+05:30"}
```

### Rate Limiter Implementation
```python
# middleware/rate_limiter.py
import time
from functools import wraps

_last_call: float = 0.0
MIN_INTERVAL = 0.1  # 100ms = max 10 req/s

def rate_limited(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        global _last_call
        elapsed = time.monotonic() - _last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        _last_call = time.monotonic()
        return fn(*args, **kwargs)
    return wrapper
```

---

## 11. Agent Behavior Rules (`gws_agent_rules.md`)

Dropped into CWD via `gws-serve --init-rules`. No other MCP server ships this.

```markdown
# Google Workspace MCP — Agent Behavior Rules
# Place this in your agent config directory (e.g., AGENTS.md, .claude/rules.md)

## Scheduling Protocol
1. Before suggesting ANY meeting time, call `find_slots` for the target window.
   Never infer availability from context — always query it.
2. When a user says "sometime this week" or "find a time," call `find_slots`
   with the full week window and stated duration.
3. If invitees are mentioned, always pass their emails to `find_slots`.
4. Use `find_slots`, not `view_schedule`, for availability questions.
   `find_slots` is one API call; parsing `view_schedule` output wastes tokens.

## Delete Protocol (CRITICAL)
1. Always call `delete_event(event_id=..., confirm=False)` first.
   Show the full preview card to the user before proceeding.
2. Only call `delete_event(confirm=True)` if the user's response unambiguously
   confirms. "yes", "do it", "confirm", "delete it" → proceed.
   "hmm", "wait", "actually" → do not proceed.
3. Never call confirm=True in the same turn as the dry-run preview.

## Context Efficiency
1. Call `list_calendars` once per session, cache the IDs.
2. Default to 1-day windows for "what's on my calendar" — not multi-week.
3. `view_schedule` is for displaying events. `find_slots` is for scheduling.
   Do not use `view_schedule` as a substitute for `find_slots`.

## Color Coding — Event Priority Guide
Events in `view_schedule` output include color-coded type labels:
  🟢 Focus/Deep Work  — Do NOT schedule over without explicit user approval
  🔴 Urgent/Deadline  — Proactively flag these when planning the user's week
  💚 Social/Enjoyment — Lower priority, can be rescheduled if needed
  🩷 Health           — Non-negotiable, never suggest removing
  🟠 Admin            — Flexible, compressible, moveable

## Intentional Overrides
When user explicitly says "book it even if I'm busy" or "I need to be in both":
  → use create_event(..., ignore_availability=True)
  → confirm with user before executing
```

---

## 12. CLI Commands

### `gws-auth`
```
$ gws-auth

Initiates OAuth2 Desktop App flow.
Opens browser → receives redirect → saves token to XDG config dir.

Handles 7-day GCP Testing mode expiry with a clear error and instructions.
```

### `gws-serve`
```
$ gws-serve
  Starts the FastMCP stdio server (reads GWS_MODE from env).

$ gws-serve --init-rules
  Drops gws_agent_rules.md into the current working directory.

$ gws-serve --export-colors
  Writes colors.default.json to CWD for user customization.
  Edit and set GWS_COLOR_CONFIG=/path/to/custom.json to use it.
```

### `gws-purge`
```
$ gws-purge
  Prompts before deleting the entire XDG config directory.
  Shows exact path before asking for confirmation.

$ gws-purge --token-only
  Deletes only token.json, preserves credentials.json.
  Use when: refresh token revoked, need to re-authenticate.
```

---

## 13. Color System

### Google Calendar Color ID → Event Type Mapping

```json
{
  "color_map": {
    "1":  { "label": "Lavender",  "type": "personal",  "emoji": "💜" },
    "2":  { "label": "Sage",      "type": "social",    "emoji": "💚" },
    "3":  { "label": "Grape",     "type": "creative",  "emoji": "🟣" },
    "4":  { "label": "Flamingo",  "type": "health",    "emoji": "🩷" },
    "5":  { "label": "Banana",    "type": "reminder",  "emoji": "🟡" },
    "6":  { "label": "Tangerine", "type": "admin",     "emoji": "🟠" },
    "7":  { "label": "Peacock",   "type": "learning",  "emoji": "🔵" },
    "8":  { "label": "Blueberry", "type": "deep-work", "emoji": "🫐" },
    "9":  { "label": "Basil",     "type": "focus",     "emoji": "🟢" },
    "10": { "label": "Tomato",    "type": "urgent",    "emoji": "🔴" },
    "11": { "label": "Graphite",  "type": "blocked",   "emoji": "⬛" }
  },
  "default_create_color_id": "9"
}
```

- Missing/invalid config file → falls back to defaults silently
- Users export via `gws-serve --export-colors`, edit, point `GWS_COLOR_CONFIG` to it
- Color emoji and type appear in `view_schedule` output for quick visual scanning

---

## 14. Milestone Checklist

### Phase 1 — Core Foundation (Week 1)
- [ ] `pyproject.toml` with uv + hatchling, CLI entry points
- [ ] `config.py` — `platformdirs` paths, all env vars, color map loader
- [ ] `auth.py` — fixed token refresh, `_save_token()`, 7-day expiry error, chmod 600
- [ ] `cli.py` — `gws-auth`, `gws-purge`, `gws-serve` skeleton
- [ ] `tools/read.py` — `view_schedule` (date range cap, color output)
- [ ] `tools/read.py` — `list_calendars`
- [ ] `tools/read.py` — `find_slots` (freebusy API)

### Phase 2 — Write Tools + Safety (Week 2)
- [ ] `tools/write.py` — `create_event` (color_id, recurrence, attendees, ignore_availability)
- [ ] `tools/write.py` — `move_event`
- [ ] `tools/write.py` — `modify_event`
- [ ] `tools/write.py` — `delete_event` (full self-contained dry-run + confirm)
- [ ] `server.py` — mode-gated tool registration (GWS_MODE)
- [ ] `middleware/rate_limiter.py` — `@rate_limited` decorator
- [ ] `middleware/audit.py` — `_audit()` JSON log
- [ ] All `destructiveHint` / `readOnlyHint` annotations

### Phase 3 — Polish + Distribution (Week 3)
- [ ] `templates/gws_agent_rules.md` — `--init-rules` flag
- [ ] `templates/colors.default.json` — `--export-colors` flag
- [ ] `tests/` — conftest mocks, all tool tests, auth edge cases
- [ ] `.github/workflows/ci.yml` — ruff + mypy + pytest
- [ ] `README.md` — GCP setup guide, uvx one-liner, security notice, scope table
- [ ] `examples/` — claude_desktop_setup.md, antigravity_setup.md
- [ ] `uv publish` → PyPI
- [ ] Register on `mcp.directory`
- [ ] PR to `modelcontextprotocol/servers` registry

---

## 15. Open Questions

| # | Question | Options | Current Leaning |
|---|---|---|---|
| Q1 | `gws_agent_rules.md` — drop to CWD or prompt for path? | CWD / ask | CWD (mirrors AGENTS.md conventions) |
| Q2 | `find_slots` output — raw windows or suggested times? | Raw windows / opinionated | Raw windows (agent adds context) |
| Q3 | Recurrence support in v1 or v2? | RRULE passthrough / full parsing | v1 passthrough — no parsing needed |
| Q4 | `delete_event` confirm: same session or always new call? | Same turn / new call | New call — enforced by agent rules |
| Q5 | `gws-purge` — prompt or `--yes` flag? | Prompt / `--yes` | Prompt (destructive, be conservative) |
| Q6 | uv-only or also support pip? | uv-only / both | Both, uv is primary target |
| Q7 | Service Account auth in v1? | Yes / No | No — v2 enterprise feature |
| Q8 | Should audit log rotate? | No / size-based / date-based | Size-based (10MB) — simple |
