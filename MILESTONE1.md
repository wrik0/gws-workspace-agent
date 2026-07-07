# Milestone 1: Implementation Strategy & Sequence

This document details the step-by-step roadmap to implement the Google Workspace MCP server foundation.

---

### Step 1: Authentication & Storage Foundation
* **Target Files:**
  * `src/google_workspace_mcp/config.py` (Completed basic version)
  * `src/google_workspace_mcp/auth.py`
* **Description:** Implement OAuth 2.0 credential loading, token auto-saving, 7-day token expiry handling, and profile-based token routing (`token_{GWS_PROFILE}.json`).

### Step 2: CLI Authentication Commands
* **Target Files:**
  * `src/google_workspace_mcp/cli.py`
* **Description:** Build `gws-auth` command to run the browser authentication loop and `gws-purge` to clean up credentials.

### Step 3: Base Read Tools & Server Lifecycle
* **Target Files:**
  * `src/google_workspace_mcp/server.py`
  * `src/google_workspace_mcp/tools/read.py`
* **Description:** Register read-only tools on the FastMCP instance, implement `list_calendars`, and build `view_schedule` with emoji-labeled calendar colors.

### Step 4: Availability slot finder
* **Target Files:**
  * `src/google_workspace_mcp/tools/read.py`
* **Description:** Implement `find_slots` utilizing the Google freebusy API, returning available blocks of time rather than raw events.

### Step 5: Middlewares & Logging
* **Target Files:**
  * `src/google_workspace_mcp/middleware/rate_limiter.py`
  * `src/google_workspace_mcp/middleware/audit.py`
* **Description:** Enforce API rate-limits and generate structured JSON append-only logs for all modification (write) tools.

### Step 6: Write Tools & Domain Whitelist Enforcer
* **Target Files:**
  * `src/google_workspace_mcp/tools/write.py`
* **Description:** Implement `create_event`, `move_event`, and `modify_event` with strict `GWS_ALLOWED_DOMAINS` boundary validations.

### Step 7: Advanced Write Tools & PII Filtering
* **Target Files:**
  * `src/google_workspace_mcp/tools/write.py`
  * `src/google_workspace_mcp/middleware/pii_scrubber.py`
  * `src/google_workspace_mcp/cli.py` (Export rules/colors commands)
* **Description:** Implement the two-turn preview/confirm flow for `delete_event`. Add the PII Scrubber decorator to mask sensitive descriptions and email domains.

### Step 8: Testing & CI/CD
* **Target Files:**
  * `tests/`
  * `.github/workflows/ci.yml`
* **Description:** Mock API client services and write verification tests for auth lifecycle, rate limits, PII filters, and tool endpoints.
