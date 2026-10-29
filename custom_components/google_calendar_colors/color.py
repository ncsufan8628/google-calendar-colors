"""Pure color and event identity helpers."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def valid_color(value: object) -> str | None:
    """Return a normalized safe CSS hex color, or None."""
    if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
        return None
    return value.lower()


def contrast_color(background: str) -> str:
    """Choose black or white using WCAG relative luminance contrast."""
    color = valid_color(background)
    if color is None:
        return "#ffffff"
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    white_contrast = 1.05 / (luminance + 0.05)
    black_contrast = (luminance + 0.05) / 0.05
    return "#ffffff" if white_contrast >= black_contrast else "#000000"


def resolve_event_color(
    event: dict[str, Any],
    labels: dict[str, str],
    legacy_colors: dict[str, str],
    calendar_default: str | None,
) -> tuple[str | None, str]:
    """Resolve an event color using Google's precedence."""
    label_id = event.get("eventLabelId")
    if isinstance(label_id, str) and (color := valid_color(labels.get(label_id))):
        return color, "event_label"
    color_id = event.get("colorId")
    if isinstance(color_id, str) and (
        color := valid_color(legacy_colors.get(color_id))
    ):
        return color, "legacy_color"
    return valid_color(calendar_default), "calendar_default"


def api_time(value: object) -> str | None:
    """Extract an RFC3339 datetime or all-day date from a Google value."""
    if not isinstance(value, dict):
        return None
    result = value.get("dateTime") or value.get("date")
    return result if isinstance(result, str) else None


def metadata_for_event(
    event: dict[str, Any],
    labels: dict[str, str],
    legacy_colors: dict[str, str],
    calendar_default: str | None,
) -> dict[str, Any] | None:
    """Build the privacy-minimized frontend metadata for one event."""
    if event.get("status") == "cancelled":
        return None
    color, source = resolve_event_color(
        event, labels, legacy_colors, calendar_default
    )
    if color is None:
        return None
    start = api_time(event.get("start"))
    end = api_time(event.get("end"))
    if start is None or end is None:
        return None
    original_start = api_time(event.get("originalStartTime"))
    return {
        "uid": event.get("iCalUID"),
        "recurrence_id": event.get("id") if event.get("recurringEventId") else None,
        "recurring_event_id": event.get("recurringEventId"),
        "original_start": original_start,
        "start": start,
        "end": end,
        "color": color,
        "text_color": contrast_color(color),
        "source": source,
    }


def parse_time(value: str) -> date | datetime:
    """Parse an ISO date or datetime for range validation tests and cache keys."""
    if "T" not in value:
        return date.fromisoformat(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

