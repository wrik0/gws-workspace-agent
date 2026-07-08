# Copyright (c) 2026 Ishanu Chakraborty. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root for license information.
#
# WARNING: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

import re
import json
from functools import wraps
from google_workspace_mcp.config import GWS_PII_MODE, GWS_ALLOWED_DOMAINS, COLOR_CONFIG

PHONE_REGEX = re.compile(
    r"\+?\b(?:\d{1,4}[-.\s]?)?\(?\d{2,5}?\)?[-.\s]?\d{3,5}(?:[-.\s]?\d{3,5})?\b"
)
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")

DEFAULT_COLOR_MAP = {
    "1": {"label": "Lavender", "type": "personal", "emoji": "💜"},
    "2": {"label": "Sage", "type": "social", "emoji": "💚"},
    "3": {"label": "Grape", "type": "creative", "emoji": "🟣"},
    "4": {"label": "Flamingo", "type": "health", "emoji": "🩷"},
    "5": {"label": "Banana", "type": "reminder", "emoji": "🟡"},
    "6": {"label": "Tangerine", "type": "admin", "emoji": "🟠"},
    "7": {"label": "Peacock", "type": "learning", "emoji": "🔵"},
    "8": {"label": "Blueberry", "type": "deep-work", "emoji": "🫐"},
    "9": {"label": "Basil", "type": "focus", "emoji": "🟢"},
    "10": {"label": "Tomato", "type": "urgent", "emoji": "🔴"},
    "11": {"label": "Graphite", "type": "blocked", "emoji": "⬛"},
}


def load_color_map() -> dict:
    if COLOR_CONFIG.exists():
        try:
            with open(COLOR_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("color_map", DEFAULT_COLOR_MAP)
        except Exception:
            pass
    return DEFAULT_COLOR_MAP


def clean_text(text: str, allowed_domains: list[str], user_domain: str = None) -> str:
    if not text:
        return ""

    # Redact phone numbers
    text = PHONE_REGEX.sub("[PHONE]", text)

    # Redact external emails
    def email_repl(match):
        email = match.group(0)
        domain = match.group(1).lower()

        is_internal = False
        if allowed_domains:
            if domain in allowed_domains:
                is_internal = True
        else:
            if user_domain and domain == user_domain.lower():
                is_internal = True
            elif domain in ("gmail.com", "googlemail.com"):
                is_internal = True

        if is_internal:
            return email
        return "[EXTERNAL_EMAIL]"

    return EMAIL_REGEX.sub(email_repl, text)


def format_event_time(start: dict, end: dict) -> str:
    from datetime import datetime

    if "date" in start:
        return f"{start.get('date')} [All Day]"

    start_dt_str = start.get("dateTime")
    end_dt_str = end.get("dateTime")

    if not start_dt_str or not end_dt_str:
        return "Unknown Time"

    try:
        s_dt = datetime.fromisoformat(start_dt_str.replace("Z", "+00:00"))
        e_dt = datetime.fromisoformat(end_dt_str.replace("Z", "+00:00"))

        if s_dt.date() == e_dt.date():
            return f"{s_dt.strftime('%Y-%m-%d %H:%M')} → {e_dt.strftime('%H:%M')}"
        else:
            return (
                f"{s_dt.strftime('%Y-%m-%d %H:%M')} → {e_dt.strftime('%Y-%m-%d %H:%M')}"
            )
    except Exception:
        return f"{start_dt_str} → {end_dt_str}"


def format_result(raw_result: dict) -> str:
    res_type = raw_result.get("type")
    color_map = load_color_map()

    if res_type == "schedule":
        events = raw_result.get("events", [])
        if not events:
            return "No events found."

        lines = []
        for ev in events:
            color_id = ev.get("colorId")
            color_info = (
                color_map.get(str(color_id))
                if color_id
                else {"emoji": "📅", "type": "event"}
            )
            emoji = color_info.get("emoji", "📅")
            type_label = color_info.get("type", "event").capitalize()

            type_str = f"[{type_label}]"
            time_str = format_event_time(ev.get("start", {}), ev.get("end", {}))

            line = f"{emoji} {type_str:<9} | ID: {ev.get('id')} | {ev.get('summary')} | {time_str}"

            desc = ev.get("description", "")
            if desc:
                line += f"\n  Description: {desc}"

            lines.append(line)
        return "\n".join(lines)

    elif res_type == "slots":
        lines = [f"Available slots ({raw_result['duration_minutes']} min duration):"]
        slots = raw_result.get("slots", [])
        if not slots:
            return "No available slots found in the specified range."

        slots_by_day = {}
        for start_dt, end_dt in slots:
            day_str = start_dt.strftime("%B %d, %Y")
            slots_by_day.setdefault(day_str, []).append((start_dt, end_dt))

        for day, day_slots in slots_by_day.items():
            lines.append(f"Available slots on {day}:")
            for s_dt, e_dt in day_slots:
                dur = int((e_dt - s_dt).total_seconds() / 60)
                time_range = f"{s_dt.strftime('%H:%M')} – {e_dt.strftime('%H:%M')}"
                lines.append(
                    f"  • {time_range} ({dur} min) — all {raw_result['attendees_count']} attendees free"
                )

        return "\n".join(lines)

    return str(raw_result)


def scrub_pii(fn):
    """Decorator to redact or mask private calendar information based on mode."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        raw_result = fn(*args, **kwargs)

        if not isinstance(raw_result, dict):
            return raw_result

        mode = GWS_PII_MODE or "none"
        if mode == "none":
            return format_result(raw_result)

        # Determine user domain
        user_email = raw_result.get("user_email") or ""
        user_domain = user_email.split("@")[-1] if "@" in user_email else None

        res_type = raw_result.get("type")

        if res_type == "schedule":
            events = raw_result.get("events", [])
            color_map = load_color_map()

            scrubbed_events = []
            for ev in events:
                scrubbed_ev = ev.copy()

                # Get event type for metadata-only fallback
                color_id = ev.get("colorId")
                color_info = (
                    color_map.get(str(color_id)) if color_id else {"type": "event"}
                )
                color_type = color_info.get("type", "event").capitalize()

                if mode == "metadata_only":
                    scrubbed_ev["summary"] = f"[{color_type}]"
                    scrubbed_ev["description"] = ""
                    scrubbed_ev["attendees"] = []
                else:  # mode == "redact"
                    scrubbed_ev["summary"] = clean_text(
                        ev.get("summary", ""), GWS_ALLOWED_DOMAINS, user_domain
                    )
                    scrubbed_ev["description"] = clean_text(
                        ev.get("description", ""), GWS_ALLOWED_DOMAINS, user_domain
                    )

                    # Redact attendees
                    if "attendees" in ev:
                        scrubbed_atts = []
                        for att in ev["attendees"]:
                            email = att.get("email", "")
                            if email:
                                domain = email.split("@")[-1].lower()
                                is_internal = False
                                if GWS_ALLOWED_DOMAINS:
                                    if domain in GWS_ALLOWED_DOMAINS:
                                        is_internal = True
                                else:
                                    if user_domain and domain == user_domain.lower():
                                        is_internal = True
                                    elif domain in ("gmail.com", "googlemail.com"):
                                        is_internal = True

                                if not is_internal:
                                    att_copy = att.copy()
                                    att_copy["email"] = "[EXTERNAL_EMAIL]"
                                    if "displayName" in att_copy:
                                        att_copy["displayName"] = clean_text(
                                            att_copy["displayName"],
                                            GWS_ALLOWED_DOMAINS,
                                            user_domain,
                                        )
                                    scrubbed_atts.append(att_copy)
                                else:
                                    scrubbed_atts.append(att)
                            else:
                                scrubbed_atts.append(att)
                        scrubbed_ev["attendees"] = scrubbed_atts

                scrubbed_events.append(scrubbed_ev)

            raw_result["events"] = scrubbed_events

        # Call format_result on the scrubbed data structure
        return format_result(raw_result)

    return wrapper
