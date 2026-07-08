# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import json
import time
from unittest.mock import patch

from google_workspace_mcp.middleware.rate_limiter import rate_limited
from google_workspace_mcp.middleware.pii_scrubber import (
    clean_text,
    format_event_time,
    scrub_pii,
)
from google_workspace_mcp.middleware.audit import audit_log


# ==========================================
# 1. Rate Limiter Tests
# ==========================================
def test_rate_limiter():
    calls = []

    @rate_limited
    def dummy_func():
        calls.append(time.monotonic())
        return "ok"

    # Call twice in quick succession
    dummy_func()
    dummy_func()

    assert len(calls) == 2
    # The elapsed time between calls must be at least 0.1s (100ms)
    elapsed = calls[1] - calls[0]
    assert elapsed >= 0.095  # allowing minor timer precision tolerance


# ==========================================
# 2. PII Scrubber Tests
# ==========================================
def test_clean_text():
    allowed_domains = ["company.com"]

    # Test phone numbers
    assert clean_text("Call me at +1-555-0199", allowed_domains) == "Call me at [PHONE]"

    # Test internal vs external emails
    assert (
        clean_text("Contact user@company.com", allowed_domains)
        == "Contact user@company.com"
    )
    assert (
        clean_text("Contact hacker@competitor.com", allowed_domains)
        == "Contact [EXTERNAL_EMAIL]"
    )

    # Test fallback user domain
    assert (
        clean_text("Contact user@mycompany.com", [], "mycompany.com")
        == "Contact user@mycompany.com"
    )
    assert (
        clean_text("Contact hacker@competitor.com", [], "mycompany.com")
        == "Contact [EXTERNAL_EMAIL]"
    )


def test_format_event_time():
    # Timed event, same day
    start_timed = {"dateTime": "2026-07-08T09:00:00Z"}
    end_timed = {"dateTime": "2026-07-08T10:00:00Z"}
    formatted = format_event_time(start_timed, end_timed)
    assert "2026-07-08 09:00" in formatted
    assert "10:00" in formatted

    # All-day event
    start_allday = {"date": "2026-07-08"}
    end_allday = {"date": "2026-07-09"}
    formatted_allday = format_event_time(start_allday, end_allday)
    assert "2026-07-08 [All Day]" == formatted_allday


def test_scrub_pii_decorator_none_mode():
    @scrub_pii
    def dummy_tool():
        return {
            "type": "schedule",
            "events": [
                {
                    "id": "1",
                    "summary": "Meeting with contact@competitor.com",
                    "description": "Call me at +1-555-0199",
                    "start": {"dateTime": "2026-07-08T09:00:00Z"},
                    "end": {"dateTime": "2026-07-08T10:00:00Z"},
                }
            ],
            "user_email": "user@company.com",
        }

    with patch("google_workspace_mcp.middleware.pii_scrubber.GWS_PII_MODE", "none"):
        result = dummy_tool()
        # In none mode, text should not be redacted
        assert "contact@competitor.com" in result
        assert "+1-555-0199" in result


def test_scrub_pii_decorator_redact_mode():
    @scrub_pii
    def dummy_tool():
        return {
            "type": "schedule",
            "events": [
                {
                    "id": "1",
                    "summary": "Meeting with contact@competitor.com",
                    "description": "Call me at +1-555-0199",
                    "start": {"dateTime": "2026-07-08T09:00:00Z"},
                    "end": {"dateTime": "2026-07-08T10:00:00Z"},
                    "attendees": [{"email": "external@competitor.com"}],
                }
            ],
            "user_email": "user@company.com",
        }

    with (
        patch("google_workspace_mcp.middleware.pii_scrubber.GWS_PII_MODE", "redact"),
        patch(
            "google_workspace_mcp.middleware.pii_scrubber.GWS_ALLOWED_DOMAINS",
            ["company.com"],
        ),
    ):
        result = dummy_tool()
        assert "[EXTERNAL_EMAIL]" in result
        assert "[PHONE]" in result
        assert "contact@competitor.com" not in result
        assert "+1-555-0199" not in result


def test_scrub_pii_decorator_metadata_only_mode():
    @scrub_pii
    def dummy_tool():
        return {
            "type": "schedule",
            "events": [
                {
                    "id": "1",
                    "summary": "Top Secret Strategy Meeting",
                    "description": "Planning confidential release",
                    "start": {"dateTime": "2026-07-08T09:00:00Z"},
                    "end": {"dateTime": "2026-07-08T10:00:00Z"},
                    "colorId": "9",  # Basil -> Focus
                }
            ],
            "user_email": "user@company.com",
        }

    with patch(
        "google_workspace_mcp.middleware.pii_scrubber.GWS_PII_MODE", "metadata_only"
    ):
        result = dummy_tool()
        assert "Top Secret Strategy Meeting" not in result
        assert "Planning confidential release" not in result
        assert "[Focus]" in result  # derived from colorId=9


# ==========================================
# 3. Audit Logger Tests
# ==========================================
def test_audit_logger(tmp_path):
    log_file = tmp_path / "audit.log"

    with patch("google_workspace_mcp.middleware.audit.AUDIT_LOG", log_file):
        payload = {"event_id": "abc123", "summary": "Sync"}
        audit_log("create_event", payload)

        assert log_file.exists()

        # Check file contents
        content = log_file.read_text(encoding="utf-8")
        entry = json.loads(content.strip())

        assert entry["action"] == "create_event"
        assert entry["event_id"] == "abc123"
        assert entry["summary"] == "Sync"
        assert "ts" in entry
