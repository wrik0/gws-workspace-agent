from mcp.server.fastmcp import FastMCP

def register_write_tools(mcp: FastMCP) -> None:
    """Register all calendar write tools with the FastMCP instance."""

    @mcp.tool(annotations={"destructiveHint": False})
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
        # Stub implementation
        return f"Stub: create_event '{summary}' on {start_iso}"

    @mcp.tool(annotations={"destructiveHint": False})
    def move_event(
        event_id: str,
        new_start_iso: str,
        new_end_iso: str,
        calendar_id: str = "primary",
    ) -> str:
        """Change the start and end time of an existing event by ID."""
        # Stub implementation
        return f"Stub: move_event {event_id} to {new_start_iso}"

    @mcp.tool(annotations={"destructiveHint": False})
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
        # Stub implementation
        return f"Stub: modify_event {event_id}"

    @mcp.tool(annotations={"destructiveHint": True})
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
        # Stub implementation
        return f"Stub: delete_event {event_id} (confirm={confirm})"
