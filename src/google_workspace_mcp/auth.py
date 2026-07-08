# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import stat
import warnings
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from .config import TOKEN_PATH, CREDENTIALS_PATH, SCOPE_SETS, GWS_MODE


def load_credentials(mode: str = None, interactive: bool = False) -> Credentials:
    """Load credentials from the token path, refreshing if expired.

    If token is not found, is invalid, or lacks sufficient scopes for the requested mode,
    initiates the Local Web Server flow to request the necessary permissions.
    """
    from .config import GWS_PROFILE

    req_mode = mode or GWS_MODE or "full"
    required_scopes = SCOPE_SETS[req_mode]

    # Security: warn if token file is world-readable
    if TOKEN_PATH.exists():
        perms = oct(TOKEN_PATH.stat().st_mode)[-3:]
        if perms not in ("600", "400"):
            warnings.warn(
                f"Token at {TOKEN_PATH} has insecure permissions {perms}. "
                "Running chmod 600 is recommended."
            )

    creds = None
    if TOKEN_PATH.exists():
        try:
            # Load the raw credentials to inspect what scopes were granted
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
            token_scopes = creds.scopes or []

            # Check if the existing token satisfies all requested scopes
            has_sufficient_scopes = all(s in token_scopes for s in required_scopes)

            if has_sufficient_scopes:
                # Reload with the required scopes set to ensure API helper is fully configured
                creds = Credentials.from_authorized_user_file(
                    str(TOKEN_PATH), required_scopes
                )
            else:
                # If we requested readonly but the token actually has full, we can downscale session-side safely
                if (
                    req_mode == "readonly"
                    and "https://www.googleapis.com/auth/calendar" in token_scopes
                ):
                    creds = Credentials.from_authorized_user_file(
                        str(TOKEN_PATH), SCOPE_SETS["readonly"]
                    )
                else:
                    # Token has insufficient scopes (e.g. cached readonly, but we want full write/delete access)
                    # Setting to None will force the OAuth local server setup flow to upgrade the token
                    creds = None
        except Exception as e:
            warnings.warn(f"Failed to load token file: {e}. Re-authenticating...")
            creds = None

    # Refresh or authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _save_token(creds)  # Persist refreshed token to disk
            except Exception as e:
                # Catch revoked tokens (common after 7 days in Google Cloud Testing mode)
                err_str = str(e).lower()
                if "revoked" in err_str or "invalid_grant" in err_str:
                    raise RuntimeError(
                        "Refresh token revoked or invalid.\n\n"
                        "If your GCP OAuth Consent Screen is in 'Testing' status, "
                        "Google automatically revokes user tokens after 7 days. Fix:\n"
                        "  1. Go to GCP Console -> OAuth consent screen -> click 'Publish App', OR\n"
                        "     ensure your email is listed as an OAuth Test User to reset the timer.\n"
                        "  2. Purge the old token by running: gws-purge --token-only\n"
                        "  3. Re-authenticate using: gws-auth"
                    ) from e
                raise
        else:
            if not interactive:
                reason = "Authentication token not found"
                if TOKEN_PATH.exists():
                    reason = (
                        "Authentication token has insufficient scopes or is invalid"
                    )
                raise RuntimeError(
                    f"{reason} at {TOKEN_PATH}.\n"
                    "Please run the interactive setup tool in your terminal to authenticate first:\n"
                    f"  gws-auth --profile {GWS_PROFILE}"
                )

            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Google Client secret credentials file not found at: {CREDENTIALS_PATH}\n"
                    "Please download the OAuth Client Secrets JSON from GCP Console "
                    "and place it there."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), required_scopes
            )
            creds = flow.run_local_server(port=0)
            _save_token(creds)

    return creds


def _save_token(creds: Credentials) -> None:
    """Save credentials to disk with strict chmod 600 permissions."""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    # Restrict permissions: owner read & write only (chmod 600)
    TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
