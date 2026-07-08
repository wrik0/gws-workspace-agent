# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

from datetime import datetime, timedelta
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP
from google_workspace_mcp.auth import load_credentials
from google_workspace_mcp.config import GWS_MAX_WINDOW_DAYS
from google_workspace_mcp.middleware.pii_scrubber import scrub_pii

# User email cache to avoid repeated primary calendar fetches
_user_email_cache = {}


def get_user_email(service) -> str:
    if "email" not in _user_email_cache:
        try:
            cal = service.calendars().get(calendarId="primary").execute()
            _user_email_cache["email"] = cal.get("id")
        except Exception:
            _user_email_cache["email"] = "primary"
    return _user_email_cache["email"]


def register_read_tools(mcp: FastMCP) -> None:
    """Register all calendar read tools with the FastMCP instance."""

    @mcp.tool(annotations={"readOnlyHint": True})
    @scrub_pii
    def view_schedule(
        time_min: str,
        time_max: str,
        calendar_id: str = "primary",
        max_results: int = 50,
    ) -> str:
        """List calendar events in a time range with color-coded type labels.

        Window is capped at GWS_MAX_WINDOW_DAYS to prevent bulk data exposure.
        Returns events formatted with emoji type labels derived from color IDs.
        """
        try:
            dt_min = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
            dt_max = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
        except ValueError as e:
            return f"Error parsing time parameters: {e}. Ensure they are in valid ISO 8601 format."

        if (dt_max - dt_min).days > GWS_MAX_WINDOW_DAYS:
            return f"Error: Request window exceeds the maximum allowed limit of {GWS_MAX_WINDOW_DAYS} days."

        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)
            user_email = get_user_email(service)

            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            return {
                "type": "schedule",
                "events": events,
                "user_email": user_email,
            }
        except Exception as e:
            return f"Error viewing schedule: {e}"

    @mcp.tool(annotations={"readOnlyHint": True})
    def list_calendars() -> str:
        """List all calendars accessible to the user.

        Returns calendar IDs needed for multi-calendar operations.
        Call once per session and reuse the IDs.
        """
        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)

            calendar_list = service.calendarList().list().execute()
            items = calendar_list.get("items", [])

            if not items:
                return "No calendars found."

            lines = ["Accessible Calendars:"]
            for item in items:
                summary = item.get("summary", "Unnamed Calendar")
                cal_id = item.get("id")
                primary = " (Primary)" if item.get("primary") else ""
                access_role = item.get("accessRole", "unknown")
                lines.append(
                    f"- {summary} [ID: {cal_id}]{primary} — Role: {access_role}"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"Error listing calendars: {e}"

    @mcp.tool(annotations={"readOnlyHint": True})
    @scrub_pii
    def find_slots(
        time_min: str,
        time_max: str,
        duration_minutes: int,
        calendar_ids: list[str] = None,
        invitee_emails: list[str] = None,
    ) -> str:
        """Find open time slots using the Google freebusy API.

        Checks availability for the user AND all invitees in one API call.
        Returns available windows (not raw busy blocks) — agent-ready output.
        """
        try:
            dt_min = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
            dt_max = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
        except ValueError as e:
            return f"Error parsing time parameters: {e}. Ensure they are in valid ISO 8601 format."

        c_ids = calendar_ids or ["primary"]
        i_emails = invitee_emails or []
        all_ids = list(set(c_ids + i_emails))

        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)
            user_email = get_user_email(service)

            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cid} for cid in all_ids],
            }

            fb_result = service.freebusy().query(body=body).execute()
            calendars_fb = fb_result.get("calendars", {})

            busy_intervals = []
            for _, fb_info in calendars_fb.items():
                busy_list = fb_info.get("busy", [])
                for b in busy_list:
                    try:
                        b_start = datetime.fromisoformat(
                            b["start"].replace("Z", "+00:00")
                        )
                        b_end = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
                        busy_intervals.append((b_start, b_end))
                    except Exception:
                        pass

            # Sort and merge busy intervals
            sorted_intervals = sorted(busy_intervals, key=lambda x: x[0])
            merged_busy = []
            if sorted_intervals:
                merged_busy = [sorted_intervals[0]]
                for current in sorted_intervals[1:]:
                    prev_start, prev_end = merged_busy[-1]
                    curr_start, curr_end = current
                    if curr_start <= prev_end:
                        merged_busy[-1] = (prev_start, max(prev_end, curr_end))
                    else:
                        merged_busy.append(current)

            # Find free gaps
            free_slots = []
            current_start = dt_min
            duration_delta = timedelta(minutes=duration_minutes)

            for busy_start, busy_end in merged_busy:
                # Clip busy intervals to the search window
                busy_start = max(busy_start, dt_min)
                busy_end = min(busy_end, dt_max)

                if busy_start > current_start:
                    if (busy_start - current_start) >= duration_delta:
                        free_slots.append((current_start, busy_start))
                current_start = max(current_start, busy_end)

            if dt_max > current_start:
                if (dt_max - current_start) >= duration_delta:
                    free_slots.append((current_start, dt_max))

            return {
                "type": "slots",
                "slots": free_slots,
                "time_min": time_min,
                "time_max": time_max,
                "duration_minutes": duration_minutes,
                "attendees_count": len(all_ids),
                "user_email": user_email,
            }
        except Exception as e:
            return f"Error finding slots: {e}"
