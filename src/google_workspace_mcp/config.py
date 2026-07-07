import os
from pathlib import Path
from platformdirs import user_config_dir

# Application directory (XDG compliant)
APP_DIR = Path(user_config_dir("google-workspace-mcp", "gws"))

# Environment-based overrides and default configuration
GWS_MODE = os.getenv("GWS_MODE", "full").lower()  # "full" or "readonly"
GWS_TIMEZONE = os.getenv("GWS_TIMEZONE", "UTC")
GWS_MAX_WINDOW_DAYS = int(os.getenv("GWS_MAX_WINDOW_DAYS", "90"))
GWS_PROFILE = os.getenv("GWS_PROFILE", "default")
GWS_PII_MODE = os.getenv("GWS_PII_MODE", "none").lower()  # "none", "redact", "metadata_only"

# Parse comma-separated allowed domains
GWS_ALLOWED_DOMAINS = [
    d.strip().lower() 
    for d in os.getenv("GWS_ALLOWED_DOMAINS", "").split(",") 
    if d.strip()
]

# File Path Configuration with environment overrides
TOKEN_PATH = Path(
    os.getenv("GWS_TOKEN_PATH") or (APP_DIR / f"token_{GWS_PROFILE}.json")
)
CREDENTIALS_PATH = Path(
    os.getenv("GWS_CREDENTIALS_PATH") or (APP_DIR / "credentials.json")
)
COLOR_CONFIG = Path(
    os.getenv("GWS_COLOR_CONFIG") or (APP_DIR / "colors.json")
)
AUDIT_LOG = Path(
    os.getenv("GWS_AUDIT_LOG") or (APP_DIR / "audit.log")
)

# Google OAuth scopes
SCOPE_SETS = {
    "full": ["https://www.googleapis.com/auth/calendar"],
    "readonly": ["https://www.googleapis.com/auth/calendar.readonly"],
}
