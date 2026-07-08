# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import json
import stat
import sys
from datetime import datetime, timezone
from google_workspace_mcp.config import AUDIT_LOG


def audit_log(action: str, payload: dict) -> None:
    """Write action and details to the append-only JSON audit log."""
    try:
        # Create structured log entry
        entry = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "action": action,
            **payload,
        }

        # Ensure target config/log directory exists
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

        # Write to log in append-only JSONL format
        log_line = json.dumps(entry) + "\n"
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(log_line)

        # Enforce secure permissions (chmod 600) on the log file
        try:
            if AUDIT_LOG.exists() and (AUDIT_LOG.stat().st_mode & 0o777) != 0o600:
                AUDIT_LOG.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    except Exception as e:
        # Prevent logging errors from crashing the main tool execution
        sys.stderr.write(f"Warning: Failed to write to audit log: {e}\n")
        sys.stderr.flush()
