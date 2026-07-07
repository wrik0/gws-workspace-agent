import time
from functools import wraps

def rate_limited(fn):
    """Decorator to enforce a minimum interval between tool invocations."""
    # Stub implementation
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper
