from mcp.server.fastmcp import FastMCP

def register_read_tools(mcp: FastMCP) -> None:
    """Register all calendar read tools with the FastMCP instance."""
    
    @mcp.tool(annotations={"readOnlyHint": True})
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
        # Stub implementation
        return f"Stub: view_schedule from {time_min} to {time_max} for calendar {calendar_id}"

    @mcp.tool(annotations={"readOnlyHint": True})
    def list_calendars() -> str:
        """List all calendars accessible to the user.

        Returns calendar IDs needed for multi-calendar operations.
        Call once per session and reuse the IDs.
        """
        # Stub implementation
        return "Stub: list_calendars"

    @mcp.tool(annotations={"readOnlyHint": True})
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
        # Stub implementation
        return f"Stub: find_slots for duration {duration_minutes} minutes"
