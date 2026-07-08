# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import time
from functools import wraps

_last_call: float = 0.0
MIN_INTERVAL = 0.1  # 100ms = max 10 req/s


def rate_limited(fn):
    """Decorator to enforce a minimum interval between tool invocations."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        global _last_call
        elapsed = time.monotonic() - _last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        _last_call = time.monotonic()
        return fn(*args, **kwargs)

    return wrapper
