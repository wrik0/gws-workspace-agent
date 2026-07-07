# Google Workspace MCP — Agent Behavior Rules

## Scheduling Protocol
1. Before suggesting ANY meeting time, call `find_slots` for the target window.
   Never infer availability from context — always query it.
2. When a user says "sometime this week" or "find a time," call `find_slots`
   with the full week window and stated duration.
3. If invitees are mentioned, always pass their emails to `find_slots`.
4. Use `find_slots`, not `view_schedule`, for availability questions.
   `find_slots` is one API call; parsing `view_schedule` output wastes tokens.

## Delete Protocol (CRITICAL)
1. Always call `delete_event(event_id=..., confirm=False)` first.
   Show the full preview card to the user before proceeding.
2. Only call `delete_event(confirm=True)` if the user's response unambiguously
   confirms. "yes", "do it", "confirm", "delete it" → proceed.
   "hmm", "wait", "actually" → do not proceed.
3. Never call confirm=True in the same turn as the dry-run preview.

## Context Efficiency
1. Call `list_calendars` once per session, cache the IDs.
2. Default to 1-day windows for "what's on my calendar" — not multi-week.
3. `view_schedule` is for displaying events. `find_slots` is for scheduling.
   Do not use `view_schedule` as a substitute for `find_slots`.

## Color Coding — Event Priority Guide
Events in `view_schedule` output include color-coded type labels:
  🟢 Focus/Deep Work  — Do NOT schedule over without explicit user approval
  🔴 Urgent/Deadline  — Proactively flag these when planning the user's week
  💚 Social/Enjoyment — Lower priority, can be rescheduled if needed
  🩷 Health           — Non-negotiable, never suggest removing
  🟠 Admin            — Flexible, compressible, moveable

## Intentional Overrides
When user explicitly says "book it even if I'm busy" or "I need to be in both":
  → use create_event(..., ignore_availability=True)
  → confirm with user before executing
