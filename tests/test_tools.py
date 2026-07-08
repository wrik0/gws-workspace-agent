# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from google_workspace_mcp.tools.read import register_read_tools
from google_workspace_mcp.tools.write import register_write_tools
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError


@pytest.fixture
def mock_mcp():
    return FastMCP("TestAgent")


@pytest.fixture
def mock_calendar_service():
    service = MagicMock()

    # Mock primary calendar retrieval (used to get user email)
    service.calendars().get().execute.return_value = {"id": "user@company.com"}

    # Mock list calendars
    service.calendarList().list().execute.return_value = {
        "items": [
            {
                "summary": "Primary",
                "id": "primary",
                "primary": True,
                "accessRole": "owner",
            },
            {"summary": "Work", "id": "work_cal_id", "accessRole": "writer"},
        ]
    }

    # Mock events list
    service.events().list().execute.return_value = {
        "items": [
            {
                "id": "event1",
                "summary": "Team Sync",
                "description": "Weekly alignment",
                "start": {"dateTime": "2026-07-08T09:00:00Z"},
                "end": {"dateTime": "2026-07-08T10:00:00Z"},
                "colorId": "8",
            }
        ]
    }

    # Mock freebusy query
    service.freebusy().query().execute.return_value = {
        "calendars": {
            "primary": {
                "busy": [
                    {"start": "2026-07-08T11:00:00Z", "end": "2026-07-08T12:00:00Z"}
                ]
            }
        }
    }

    # Mock events insert
    service.events().insert().execute.return_value = {
        "id": "new_event_123",
        "htmlLink": "https://calendar.google.com/event?id=new_event_123",
    }

    # Mock events get
    service.events().get().execute.return_value = {
        "id": "event1",
        "summary": "Team Sync",
        "start": {"dateTime": "2026-07-08T09:00:00Z"},
        "end": {"dateTime": "2026-07-08T10:00:00Z"},
        "attendees": [{"email": "colleague@company.com"}],
    }

    # Mock events patch
    service.events().patch().execute.return_value = {
        "id": "event1",
        "summary": "Updated Sync",
    }

    # Mock events delete
    service.events().delete().execute.return_value = {}

    return service


def run_tool(mcp, name, **kwargs) -> str:
    """Helper to run an MCP tool and return the resulting text string."""
    result = asyncio.run(mcp.call_tool(name, kwargs))
    if isinstance(result, tuple):
        content = result[0]
    else:
        content = result
    return "".join(c.text for c in content if hasattr(c, "text"))


# ==========================================
# 1. Read Tools Tests
# ==========================================
def test_list_calendars(mock_mcp, mock_calendar_service):
    register_read_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.read.load_credentials"),
        patch(
            "google_workspace_mcp.tools.read.build",
            return_value=mock_calendar_service,
        ),
    ):
        result = run_tool(mock_mcp, "list_calendars")
        assert "Accessible Calendars:" in result
        assert "- Primary [ID: primary] (Primary) — Role: owner" in result
        assert "- Work [ID: work_cal_id] — Role: writer" in result


def test_view_schedule(mock_mcp, mock_calendar_service):
    register_read_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.read.load_credentials"),
        patch(
            "google_workspace_mcp.tools.read.build",
            return_value=mock_calendar_service,
        ),
        patch("google_workspace_mcp.middleware.pii_scrubber.GWS_PII_MODE", "none"),
    ):
        result = run_tool(
            mock_mcp,
            "view_schedule",
            time_min="2026-07-08T00:00:00Z",
            time_max="2026-07-08T23:59:59Z",
        )
        assert "🫐 [Deep-work] | ID: event1 | Team Sync" in result
        assert "Description: Weekly alignment" in result


def test_view_schedule_max_days_exceeded(mock_mcp):
    register_read_tools(mock_mcp)

    result = run_tool(
        mock_mcp,
        "view_schedule",
        time_min="2026-07-08T00:00:00Z",
        time_max="2026-10-30T00:00:00Z",
    )
    assert "Error: Request window exceeds the maximum allowed limit" in result


def test_find_slots(mock_mcp, mock_calendar_service):
    register_read_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.read.load_credentials"),
        patch(
            "google_workspace_mcp.tools.read.build",
            return_value=mock_calendar_service,
        ),
        patch("google_workspace_mcp.middleware.pii_scrubber.GWS_PII_MODE", "none"),
    ):
        # We query a window from 10:00 to 13:00. The user is busy 11:00-12:00.
        # Duration is 60 minutes.
        # This should find slots: 10:00-11:00 and 12:00-13:00.
        result = run_tool(
            mock_mcp,
            "find_slots",
            time_min="2026-07-08T10:00:00Z",
            time_max="2026-07-08T13:00:00Z",
            duration_minutes=60,
        )
        assert "Available slots on July 08, 2026:" in result
        assert "• 10:00 – 11:00 (60 min)" in result
        assert "• 12:00 – 13:00 (60 min)" in result


# ==========================================
# 2. Write Tools Tests
# ==========================================
def test_create_event_whitelist_block(mock_mcp):
    register_write_tools(mock_mcp)

    with patch("google_workspace_mcp.config.GWS_ALLOWED_DOMAINS", ["company.com"]):
        # Inviting external email should raise a ValueError due to domain check
        with pytest.raises(ToolError) as excinfo:
            run_tool(
                mock_mcp,
                "create_event",
                summary="Sync",
                start_iso="2026-07-08T10:00:00Z",
                end_iso="2026-07-08T11:00:00Z",
                attendee_emails=["external@competitor.com"],
            )
        assert "Security Block" in str(excinfo.value)


def test_create_event_double_booking_block(mock_mcp, mock_calendar_service):
    register_write_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.write.load_credentials"),
        patch(
            "google_workspace_mcp.tools.write.build",
            return_value=mock_calendar_service,
        ),
    ):
        # User is busy 11:00-12:00. Creating event during this time should fail
        with pytest.raises(ToolError) as excinfo:
            run_tool(
                mock_mcp,
                "create_event",
                summary="Overlapping meeting",
                start_iso="2026-07-08T11:00:00Z",
                end_iso="2026-07-08T12:00:00Z",
                ignore_availability=False,
            )
        assert "Scheduling Conflict" in str(excinfo.value)

        # Setting ignore_availability=True should bypass the check and succeed
        result = run_tool(
            mock_mcp,
            "create_event",
            summary="Overlapping meeting",
            start_iso="2026-07-08T11:00:00Z",
            end_iso="2026-07-08T12:00:00Z",
            ignore_availability=True,
        )
        assert "[+] Successfully created event" in result


def test_move_event(mock_mcp, mock_calendar_service):
    register_write_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.write.load_credentials"),
        patch(
            "google_workspace_mcp.tools.write.build",
            return_value=mock_calendar_service,
        ),
        patch("google_workspace_mcp.tools.write.audit_log"),
    ):
        result = run_tool(
            mock_mcp,
            "move_event",
            event_id="event1",
            new_start_iso="2026-07-08T15:00:00Z",
            new_end_iso="2026-07-08T16:00:00Z",
        )
        assert "[+] Successfully moved event" in result


def test_modify_event(mock_mcp, mock_calendar_service):
    register_write_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.write.load_credentials"),
        patch(
            "google_workspace_mcp.tools.write.build",
            return_value=mock_calendar_service,
        ),
        patch("google_workspace_mcp.tools.write.audit_log"),
        patch("google_workspace_mcp.config.GWS_ALLOWED_DOMAINS", ["company.com"]),
    ):
        result = run_tool(
            mock_mcp,
            "modify_event",
            event_id="event1",
            new_summary="Updated Sync Summary",
            add_attendees=["partner@company.com"],
        )
        assert "[+] Successfully modified event" in result


def test_delete_event_flow(mock_mcp, mock_calendar_service):
    register_write_tools(mock_mcp)

    with (
        patch("google_workspace_mcp.tools.write.load_credentials"),
        patch(
            "google_workspace_mcp.tools.write.build",
            return_value=mock_calendar_service,
        ),
        patch("google_workspace_mcp.tools.write.audit_log"),
    ):
        # First turn: confirm=False -> Returns preview card
        preview = run_tool(mock_mcp, "delete_event", event_id="event1", confirm=False)
        assert "⚠️ PENDING CONFIRMATION" in preview
        assert "Event Summary:  Team Sync" in preview

        # Second turn: confirm=True -> Returns deletion confirmation
        success = run_tool(mock_mcp, "delete_event", event_id="event1", confirm=True)
        assert "[+] Successfully deleted event 'Team Sync'" in success
