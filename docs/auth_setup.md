# Google Workspace MCP — Authentication Setup Guide

This guide walks you through setting up Google Calendar API authentication for the `google-workspace-mcp` server.

---

## 1. Google Cloud Console Configuration

To access Google Calendar, you must create a project and download OAuth 2.0 client credentials from the Google Cloud Console.

### Step A: Create a GCP Project & Enable API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `Workspace MCP Server`).
3. Search for the **Google Calendar API** and click **Enable**.

### Step B: Configure the OAuth Consent Screen
1. Navigate to **APIs & Services** > **OAuth consent screen**.
2. Choose **User Type**:
   * **Internal**: Recommended if your organization uses Google Workspace. This restricts access exclusively to accounts within your domain.
   * **External**: Choose this if you are using a personal `@gmail.com` account.
3. Complete the app details (App name, support email, developer contact details).
4. **Scopes (Optional)**: You can leave scopes blank during consent screen setup, as the MCP server requests `calendar` or `calendar.readonly` scopes dynamically at login.
5. **Test Users**:
   * If your app is **External** and in **Testing** status, you **MUST** add your target email (e.g., `user@company-name.com`) to the **Test Users** list. Otherwise, Google will block authentication.

### Step C: Create OAuth Client ID Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. Set **Application type** to **Desktop app**.
4. Name the credential (e.g., `Workspace MCP Desktop`) and click **Create**.
5. Click **Download JSON** on the created credential. This file is your client secrets file. Rename it to `credentials.json`.

---

## 2. Configuration & Paths

By default, the server reads and saves files in standard, platform-specific XDG-compliant config directories using `platformdirs`.

### Default Credentials File Location
Save your downloaded `credentials.json` file to the standard user configuration path:
* **Linux:** `~/.config/google-workspace-mcp/credentials.json`
* **macOS:** `~/Library/Application Support/google-workspace-mcp/credentials.json`
* **Windows:** `%APPDATA%\gws\google-workspace-mcp\credentials.json`

### Environment Variable Override: `GWS_CREDENTIALS_PATH`
If you prefer not to use the default paths, or want to load the credentials from a custom directory, define the `GWS_CREDENTIALS_PATH` environment variable:

```bash
export GWS_CREDENTIALS_PATH="/absolute/path/to/your/custom_credentials.json"
```

Once defined, the MCP server will bypass the platform directory and read the secrets directly from your designated path.

---

## 3. Storage Security (Permissions)

To protect your OAuth tokens, the server enforces strict file permissions:
* Refreshed token JSON files (`token_{GWS_PROFILE}.json`) are written with `chmod 600` permissions (owner read/write only).
* If the server detects that the token file has insecure permissions (e.g., world-readable `chmod 644`), it will issue a warning in the console.

---

## 4. The 7-Day Testing Expiry Exception

If your GCP OAuth Consent Screen is in the default **Testing** status, Google automatically revokes refresh tokens after **7 days**. 

### How to Diagnose
If the token expires or is revoked, you will receive a runtime error:
`RuntimeError: Refresh token revoked or invalid.`

### How to Fix
1. **Option A (Permanent)**: Go to GCP Console -> OAuth consent screen -> click **Publish App** to move the app status to production. (This removes the 7-day token limit).
2. **Option B (Temporary)**: Go to GCP Console -> OAuth consent screen -> add or re-save your email in the **Test Users** list to reset the 7-day timer.
3. Purge the old expired token:
   ```bash
   gws-purge --token-only
   ```
4. Re-authenticate:
   ```bash
   gws-auth
   ```

---

## 5. Multi-Profile & Multi-Account Configurations

The server natively supports multi-tenant and multi-account configurations (e.g., separating personal `@gmail.com` and work `@company-name.com` accounts). You can manage them using the `--profile` command-line flag or `GWS_PROFILE` environment variable.

### Option A: Shared Google Cloud Project (Default)
In this configuration, both profiles share the same client credentials (`credentials.json`) but keep their login tokens separate.

1. **Authorize the Personal Profile**:
   ```bash
   gws-auth --profile personal
   ```
2. **Authorize the Work Profile**:
   ```bash
   gws-auth --profile work
   ```
3. **Configure the Client (`claude_desktop_config.json`)**:
   ```json
   {
     "mcpServers": {
       "google-workspace-personal": {
         "command": "~/.local/bin/gws-serve",
         "args": ["--profile", "personal", "--readonly", "--pii-mode", "redact"]
       },
       "google-workspace-work": {
         "command": "~/.local/bin/gws-serve",
         "args": ["--profile", "work", "--readonly", "--pii-mode", "redact"]
       }
     }
   }
   ```

### Option B: Isolated Google Cloud Projects (Advanced)
If you need to keep profiles strictly isolated across different Google Cloud Console projects (e.g., your personal sandbox project and your enterprise GCP tenant project), you can use different client credentials files:

1. **Save Credentials Separately**:
   Save your client secrets files as:
   * `~/.config/google-workspace-mcp/credentials_personal.json`
   * `~/.config/google-workspace-mcp/credentials_work.json`

2. **Authenticate Each Profile**:
   Set the `GWS_CREDENTIALS_PATH` env variable when authorizing each profile:
   ```bash
   GWS_CREDENTIALS_PATH=~/.config/google-workspace-mcp/credentials_personal.json gws-auth --profile personal
   GWS_CREDENTIALS_PATH=~/.config/google-workspace-mcp/credentials_work.json gws-auth --profile work
   ```

3. **Configure the Client (`claude_desktop_config.json`)**:
   Specify the credentials path for each server instance using the `"env"` block:
   ```json
   {
     "mcpServers": {
       "google-workspace-personal": {
         "command": "~/.local/bin/gws-serve",
         "args": ["--profile", "personal", "--readonly", "--pii-mode", "redact"],
         "env": {
           "GWS_CREDENTIALS_PATH": "/home/username/.config/google-workspace-mcp/credentials_personal.json"
         }
       },
       "google-workspace-work": {
         "command": "~/.local/bin/gws-serve",
         "args": ["--profile", "work", "--readonly", "--pii-mode", "redact"],
         "env": {
           "GWS_CREDENTIALS_PATH": "/home/username/.config/google-workspace-mcp/credentials_work.json"
         }
       }
     }
   }
   ```
