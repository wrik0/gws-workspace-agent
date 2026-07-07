import warnings
from google.oauth2.credentials import Credentials
from .config import TOKEN_PATH, CREDENTIALS_PATH, SCOPE_SETS

def load_credentials(mode: str = "full") -> Credentials:
    """Load credentials from the token path, refreshing if expired.
    
    If token is not found or invalid, initiates Local Web Server flow.
    """
    # Stub implementation
    raise NotImplementedError("auth.load_credentials is not yet implemented")

def _save_token(creds: Credentials) -> None:
    """Save credentials to disk with chmod 600 permissions."""
    # Stub implementation
    raise NotImplementedError("auth._save_token is not yet implemented")
