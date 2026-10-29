"""Tests for color resolution, identity payloads, and accessibility."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[2]
    / "custom_components"
    / "google_calendar_colors"
    / "color.py"
)
SPEC = spec_from_file_location("google_calendar_colors_color", MODULE_PATH)
assert SPEC and SPEC.loader
color = module_from_spec(SPEC)
SPEC.loader.exec_module(color)


def event(**values):
    base = {
        "id": "instance-id",
        "iCalUID": "stable@example.com",
        "status": "confirmed",
        "start": {"dateTime": "2026-11-01T01:30:00-04:00"},
        "end": {"dateTime": "2026-11-01T01:30:00-05:00"},
    }
    return {**base, **values}


def test_event_label_supersedes_legacy_and_default():
    assert color.resolve_event_color(
        event(eventLabelId="label", colorId="2"),
        {"label": "#ABCDEF"},
        {"2": "#00ff00"},
        "#ff0000",
    ) == ("#abcdef", "event_label")


def test_legacy_and_calendar_fallbacks():
    assert color.resolve_event_color(
        event(colorId="2"), {}, {"2": "#00ff00"}, "#ff0000"
    ) == ("#00ff00", "legacy_color")
    assert color.resolve_event_color(event(), {}, {}, "#ff0000") == (
        "#ff0000",
        "calendar_default",
    )


def test_missing_deleted_and_invalid_labels_fall_back_safely():
    for labels in ({}, {"removed": "javascript:alert(1)"}, {"removed": "#abcd"}):
        assert color.resolve_event_color(
            event(eventLabelId="removed"), labels, {}, "#112233"
        ) == ("#112233", "calendar_default")


def test_recurring_exception_identity_and_dst_are_preserved():
    result = color.metadata_for_event(
        event(
            recurringEventId="series",
            originalStartTime={"dateTime": "2026-11-01T01:30:00-04:00"},
            eventLabelId="label",
        ),
        {"label": "#101010"},
        {},
        None,
    )
    assert result == {
        "uid": "stable@example.com",
        "recurrence_id": "instance-id",
        "recurring_event_id": "series",
        "original_start": "2026-11-01T01:30:00-04:00",
        "start": "2026-11-01T01:30:00-04:00",
        "end": "2026-11-01T01:30:00-05:00",
        "color": "#101010",
        "text_color": "#ffffff",
        "source": "event_label",
    }


def test_all_day_and_multi_day_values_are_not_timezone_shifted():
    result = color.metadata_for_event(
        event(start={"date": "2026-12-24"}, end={"date": "2026-12-27"}),
        {},
        {},
        "#ffffff",
    )
    assert result["start"] == "2026-12-24"
    assert result["end"] == "2026-12-27"
    assert result["text_color"] == "#000000"


def test_cancelled_and_malformed_events_are_omitted():
    assert (
        color.metadata_for_event(event(status="cancelled"), {}, {}, "#123456")
        is None
    )
    assert color.metadata_for_event(event(start={}), {}, {}, "#123456") is None


def test_contrast_boundary_chooses_higher_wcag_ratio():
    assert color.contrast_color("#ffffff") == "#000000"
    assert color.contrast_color("#000000") == "#ffffff"
    assert color.contrast_color("#777777") == "#000000"
    assert color.contrast_color("invalid") == "#ffffff"


def test_identical_titles_and_start_times_do_not_enter_metadata_identity():
    first = color.metadata_for_event(
        event(id="one", iCalUID="one@example.com"), {}, {}, "#010203"
    )
    second = color.metadata_for_event(
        event(id="two", iCalUID="two@example.com"), {}, {}, "#010203"
    )
    assert first["uid"] != second["uid"]
    assert "summary" not in first

