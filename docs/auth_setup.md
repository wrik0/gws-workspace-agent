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
