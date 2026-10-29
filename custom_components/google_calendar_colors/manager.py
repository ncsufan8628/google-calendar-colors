"""Efficient incremental event-color cache."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from .api import GoogleApiError, GoogleCalendarApi, GoogleSyncTokenExpired
from .color import metadata_for_event, valid_color


@dataclass
class RangeCache:
    """A bounded range and its Google incremental sync state."""

    events: dict[str, dict[str, Any]] = field(default_factory=dict)
    sync_token: str | None = None
    updated: float = 0.0


class ColorManager:
    """Coordinate label, palette, default, and event caches."""

    def __init__(
        self,
        api: GoogleCalendarApi,
        calendar_id: str,
        default_color: str | None,
        refresh_interval: int,
    ) -> None:
        self.api = api
        self.calendar_id = calendar_id
        self.calendar_default = valid_color(default_color)
        self.refresh_interval = refresh_interval
        self._ranges: OrderedDict[tuple[str, str], RangeCache] = OrderedDict()
        self._labels: dict[str, str] = {}
        self._legacy_colors: dict[str, str] = {}
        self._metadata_updated = 0.0
        self._lock = asyncio.Lock()

    async def _async_refresh_metadata(self, now: float) -> None:
        if now - self._metadata_updated < self.refresh_interval:
            return
        calendar, colors, calendar_list = await asyncio.gather(
            self.api.async_calendar(self.calendar_id),
            self.api.async_colors(),
            self.api.async_calendar_list(),
        )
        raw_labels = calendar.get("labelProperties", {}).get("eventLabels", [])
        self._labels = {
            item["id"]: color
            for item in raw_labels
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and (color := valid_color(item.get("backgroundColor")))
        }
        raw_legacy = colors.get("event", {})
        self._legacy_colors = {
            color_id: color
            for color_id, item in raw_legacy.items()
            if isinstance(item, dict)
            and (color := valid_color(item.get("background")))
        }
        for item in calendar_list:
            if item.get("id") == self.calendar_id:
                self.calendar_default = valid_color(item.get("backgroundColor"))
                break
        self._metadata_updated = now

    async def _async_refresh_range(
        self, key: tuple[str, str], cache: RangeCache, now: float
    ) -> None:
        if now - cache.updated < self.refresh_interval:
            return
        try:
            changes, sync_token = await self.api.async_events(
                self.calendar_id,
                sync_token=cache.sync_token,
                start=None if cache.sync_token else key[0],
                end=None if cache.sync_token else key[1],
            )
        except GoogleSyncTokenExpired:
            cache.events.clear()
            cache.sync_token = None
            changes, sync_token = await self.api.async_events(
                self.calendar_id, start=key[0], end=key[1]
            )
        for event in changes:
            event_id = event.get("id")
            if not isinstance(event_id, str):
                continue
            if event.get("status") == "cancelled":
                cache.events.pop(event_id, None)
            else:
                cache.events[event_id] = event
        if sync_token:
            cache.sync_token = sync_token
        cache.updated = now

    async def async_get(self, start: str, end: str) -> list[dict[str, Any]]:
        """Return safe event color metadata for the requested range."""
        key = (start, end)
        async with self._lock:
            now = time.monotonic()
            try:
                await self._async_refresh_metadata(now)
            except GoogleApiError:
                if self._metadata_updated == 0:
                    raise
                # Serve the last safe palette through temporary errors/rate limits.
                self._metadata_updated = now
            cache = self._ranges.setdefault(key, RangeCache())
            self._ranges.move_to_end(key)
            while len(self._ranges) > 8:
                self._ranges.popitem(last=False)
            try:
                await self._async_refresh_range(key, cache, now)
            except GoogleApiError:
                if cache.updated == 0:
                    raise
                # Preserve the last range and retry after the normal interval.
                cache.updated = now
            return [
                metadata
                for event in cache.events.values()
                if (
                    metadata := metadata_for_event(
                        event,
                        self._labels,
                        self._legacy_colors,
                        self.calendar_default,
                    )
                )
                is not None
            ]

    def diagnostics(self) -> dict[str, Any]:
        """Return counts and state only—never IDs or event content."""
        return {
            "calendar_configured": True,
            "calendar_default_available": self.calendar_default is not None,
            "label_count": len(self._labels),
            "legacy_color_count": len(self._legacy_colors),
            "range_cache_count": len(self._ranges),
            "cached_event_count": sum(
                len(item.events) for item in self._ranges.values()
            ),
            "incremental_sync_ranges": sum(
                item.sync_token is not None for item in self._ranges.values()
            ),
            "refresh_interval": self.refresh_interval,
        }
