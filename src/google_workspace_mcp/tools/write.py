# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from google_workspace_mcp.auth import load_credentials
from google_workspace_mcp.config import GWS_MODE
from google_workspace_mcp.middleware.rate_limiter import rate_limited
from google_workspace_mcp.middleware.audit import audit_log


def _verify_domains(emails: list[str]) -> None:
    from google_workspace_mcp.config import GWS_ALLOWED_DOMAINS

    if not GWS_ALLOWED_DOMAINS or not emails:
        return
    for email in emails:
        email = email.strip().lower()
        if not email:
            continue
        if "@" not in email:
            raise ValueError(f"Invalid email address: '{email}'")
        domain = email.split("@")[-1]
        if domain not in GWS_ALLOWED_DOMAINS:
            raise ValueError(
                f"Security Block: Inviting external domain '{domain}' (email: '{email}') is not allowed.\n"
                f"Whitelisted domains: {', '.join(GWS_ALLOWED_DOMAINS)}"
            )


def register_write_tools(mcp: FastMCP) -> None:
    """Register all calendar write tools with the FastMCP instance."""

    # Safety check: enforce readonly mode at runtime if server starts up with full mode tool registry
    # but GWS_MODE is readonly.
    def _check_readonly_mode() -> None:
        if GWS_MODE == "readonly":
            raise PermissionError(
                "Write actions are disabled because the server is running in read-only mode."
            )

    @mcp.tool(annotations={"destructiveHint": False})
    @rate_limited
    def create_event(
        summary: str,
        start_iso: str,
        end_iso: str,
        description: str = "",
        location: str = "",
        attendee_emails: list[str] = None,
        color_id: str = None,
        recurrence: list[str] = None,
        calendar_id: str = "primary",
        ignore_availability: bool = False,
    ) -> str:
        """Create a new calendar event. Returns event ID and HTML link.

        Use ignore_availability=True only when the user explicitly requests
        overlapping/conflicting bookings.
        """
        _check_readonly_mode()

        # 1. Validate domains
        if attendee_emails:
            _verify_domains(attendee_emails)

        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)

            # 2. Check availability unless overridden
            if not ignore_availability:
                body = {
                    "timeMin": start_iso,
                    "timeMax": end_iso,
                    "items": [{"id": calendar_id}],
                }
                fb_result = service.freebusy().query(body=body).execute()
                busy = (
                    fb_result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
                )
                if busy:
                    conflicts = []
                    for b in busy:
                        conflicts.append(f"{b.get('start')} to {b.get('end')}")
                    raise ValueError(
                        f"Scheduling Conflict: You are busy during the requested window ({start_iso} to {end_iso}).\n"
                        f"Conflicts detected: {', '.join(conflicts)}.\n"
                        "To double-book anyway, set ignore_availability=True."
                    )

            # 3. Construct event body
            event_body = {
                "summary": summary,
                "description": description,
                "location": location,
                "start": {"dateTime": start_iso},
                "end": {"dateTime": end_iso},
            }

            if attendee_emails:
                event_body["attendees"] = [
                    {"email": email} for email in attendee_emails
                ]
            if color_id:
                event_body["colorId"] = str(color_id)
            if recurrence:
                event_body["recurrence"] = recurrence

            # 4. Insert event
            event = (
                service.events()
                .insert(calendarId=calendar_id, body=event_body)
                .execute()
            )

            # 5. Log write action to audit log
            audit_payload = {
                "summary": summary,
                "start": start_iso,
                "end": end_iso,
                "attendee_count": len(attendee_emails or []),
                "event_id": event.get("id"),
            }
            audit_log("create_event", audit_payload)

            return (
                f"[+] Successfully created event '{summary}' (ID: {event.get('id')}).\n"
                f"Link: {event.get('htmlLink')}"
            )

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            return f"Error creating event: {e}"

    @mcp.tool(annotations={"destructiveHint": False})
    @rate_limited
    def move_event(
        event_id: str,
        new_start_iso: str,
        new_end_iso: str,
        calendar_id: str = "primary",
    ) -> str:
        """Change the start and end time of an existing event by ID."""
        _check_readonly_mode()

        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)

            # 1. Fetch current event summary for logging
            curr_event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )
            summary = curr_event.get("summary", "Unnamed Event")

            # 2. Patch start/end times
            move_body = {
                "start": {"dateTime": new_start_iso},
                "end": {"dateTime": new_end_iso},
            }

            service.events().patch(
                calendarId=calendar_id, eventId=event_id, body=move_body
            ).execute()

            # 3. Log to audit log
            audit_payload = {
                "event_id": event_id,
                "summary": summary,
                "new_start": new_start_iso,
                "new_end": new_end_iso,
            }
            audit_log("move_event", audit_payload)

            return f"[+] Successfully moved event '{summary}' (ID: {event_id}) to {new_start_iso} → {new_end_iso}."

        except Exception as e:
            return f"Error moving event: {e}"

    @mcp.tool(annotations={"destructiveHint": False})
    @rate_limited
    def modify_event(
        event_id: str,
        new_summary: str = None,
        new_description: str = None,
        new_location: str = None,
        new_color_id: str = None,
        add_attendees: list[str] = None,
        calendar_id: str = "primary",
    ) -> str:
        """Modify text/metadata fields of an event using PATCH."""
        _check_readonly_mode()

        if add_attendees:
            _verify_domains(add_attendees)

        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)

            # 1. Fetch current event details
            curr_event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )

            # 2. Prepare PATCH body
            patch_body = {}
            if new_summary is not None:
                patch_body["summary"] = new_summary
            if new_description is not None:
                patch_body["description"] = new_description
            if new_location is not None:
                patch_body["location"] = new_location
            if new_color_id is not None:
                patch_body["colorId"] = str(new_color_id)

            # 3. Merge attendees
            if add_attendees:
                curr_attendees = curr_event.get("attendees", [])
                existing_emails = {
                    a.get("email").lower().strip()
                    for a in curr_attendees
                    if a.get("email")
                }

                new_attendees = list(curr_attendees)
                for email in add_attendees:
                    if email.lower().strip() not in existing_emails:
                        new_attendees.append({"email": email})

                patch_body["attendees"] = new_attendees

            if not patch_body:
                return "No changes specified."

            # 4. Patch event
            event = (
                service.events()
                .patch(calendarId=calendar_id, eventId=event_id, body=patch_body)
                .execute()
            )

            # 5. Log to audit log
            audit_payload = {
                "event_id": event_id,
                "summary": event.get("summary", "Unnamed Event"),
                "modified_fields": list(patch_body.keys()),
            }
            audit_log("modify_event", audit_payload)

            return f"[+] Successfully modified event '{event.get('summary')}' (ID: {event_id})."

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            return f"Error modifying event: {e}"

    @mcp.tool(annotations={"destructiveHint": True})
    @rate_limited
    def delete_event(
        event_id: str,
        confirm: bool = False,
        calendar_id: str = "primary",
    ) -> str:
        """Delete a calendar event by its ID.

        ALWAYS call twice:
        1. delete_event(confirm=False) -> Returns preview card.
        2. delete_event(confirm=True) -> Executes deletion.
        """
        _check_readonly_mode()

        try:
            creds = load_credentials()
            service = build("calendar", "v3", credentials=creds)

            # 1. Fetch current event details
            event = (
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            )
            summary = event.get("summary", "Unnamed Event")

            if not confirm:
                # Two-turn protocol: return preview card
                start = event.get("start", {})
                end = event.get("end", {})
                start_time = start.get("dateTime") or start.get("date")
                end_time = end.get("dateTime") or end.get("date")

                attendees = event.get("attendees", [])
                attendees_str = (
                    ", ".join([a.get("email") for a in attendees if a.get("email")])
                    if attendees
                    else "None"
                )

                preview_card = (
                    f"⚠️ PENDING CONFIRMATION: Are you sure you want to delete this event?\n"
                    f"========================================\n"
                    f" Event Summary:  {summary}\n"
                    f" Event ID:       {event_id}\n"
                    f" Time Window:    {start_time} → {end_time}\n"
                    f" Location:       {event.get('location', 'None')}\n"
                    f" Description:    {event.get('description', 'None')}\n"
                    f" Invitees:       {attendees_str}\n"
                    f"========================================\n"
                    f"Confirm deletion by running this tool again with confirm=True."
                )
                return preview_card

            # 2. Execute deletion
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

            # 3. Log to audit log
            audit_payload = {
                "event_id": event_id,
                "summary": summary,
            }
            audit_log("delete_event", audit_payload)

            return f"[+] Successfully deleted event '{summary}' (ID: {event_id})."

        except Exception as e:
            return f"Error deleting event: {e}"
