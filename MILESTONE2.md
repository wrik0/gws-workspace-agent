# Milestone 2: Corporate Account Isolation (Low-Hanging Fruits)

These four items define the low-impact features to isolate corporate accounts (like `ishanu@company-name.com`) within the v1 codebase architecture.

---

### 1. Profile-Based Storage Isolation
* **Target File:** `src/google_workspace_mcp/auth.py`
* **Description:** Allow personal and corporate profiles to coexist on the same system without sharing credentials.
* **Details:**
  * Add `GWS_PROFILE = os.getenv("GWS_PROFILE", "default")` to configuration.
  * Map `TOKEN_PATH` dynamically:
    ```python
    TOKEN_PATH = APP_DIR / f"token_{GWS_PROFILE}.json"
    ```

### 2. Lightweight PII / Description Scrubbing Middleware
* **Target File:** `src/google_workspace_mcp/middleware/pii_scrubber.py`
* **Description:** Filter out or anonymize private calendar summaries, descriptions, emails, and phone numbers before the agent's LLM can read them.
* **Details:**
  * Define `GWS_PII_MODE` env var (`none`, `redact`, `metadata_only`).
  * Implement `@scrub_pii` decorator to process returned strings.
  * Decorate `view_schedule` and `find_slots` in `tools/read.py`.

### 3. Invitee Domain Boundary Enforcer
* **Target File:** `src/google_workspace_mcp/tools/write.py`
* **Description:** Restrict the agent from inviting external domains to corporate events.
* **Details:**
  * Read `GWS_ALLOWED_DOMAINS` env var (comma-separated whitelist).
  * Validate all emails in `attendee_emails` parameter of `create_event` at runtime.
  * Raise a `ValueError` if an unauthorized domain is present.

### 4. GCP Internal OAuth Consent Screen Configuration
* **Target File:** Google Cloud Console Project Configuration (Non-Code)
* **Description:** Guarantee that the server can only authenticate corporate accounts.
* **Details:**
  * Configure the OAuth Consent Screen's **User type** to **Internal** inside the Google Cloud Console.
  * This blocks all external consumer accounts (e.g. standard `@gmail.com` addresses) from requesting tokens.
