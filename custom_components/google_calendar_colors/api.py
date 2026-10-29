"""Small authenticated Google Calendar API client."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import GOOGLE_API_BASE


class GoogleApiError(Exception):
    """Base Google API error."""

    def __init__(self, status: int, message: str = "Google Calendar API error") -> None:
        super().__init__(message)
        self.status = status


class GoogleSyncTokenExpired(GoogleApiError):
    """An incremental sync token is no longer valid."""


class GoogleCalendarApi:
    """Access only the read-only Calendar endpoints required by this integration."""

    def __init__(self, oauth_session: OAuth2Session) -> None:
        self._oauth_session = oauth_session

    async def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        response = await self._oauth_session.async_request(
            "get", f"{GOOGLE_API_BASE}{path}", params=params
        )
        if response.status == 401:
            response.release()
            self._oauth_session.config_entry.async_start_reauth_if_available(
                self._oauth_session.hass
            )
            raise GoogleApiError(401, "Google authorization expired")
        if response.status == 410:
            response.release()
            raise GoogleSyncTokenExpired(410, "Google sync token expired")
        if response.status >= 400:
            status = response.status
            response.release()
            raise GoogleApiError(status)
        payload = await response.json()
        if not isinstance(payload, dict):
            raise GoogleApiError(response.status, "Invalid Google API response")
        return payload

    async def async_calendar_list(self) -> list[dict[str, Any]]:
        """Return every readable calendar, following pagination."""
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {"minAccessRole": "reader", "maxResults": "250"}
            if page_token:
                params["pageToken"] = page_token
            payload = await self._get("/users/me/calendarList", params)
            items.extend(
                item for item in payload.get("items", []) if isinstance(item, dict)
            )
            page_token = payload.get("nextPageToken")
            if not isinstance(page_token, str):
                return items

    async def async_calendar(self, calendar_id: str) -> dict[str, Any]:
        """Get custom labels for a calendar."""
        return await self._get(f"/calendars/{quote(calendar_id, safe='')}")

    async def async_colors(self) -> dict[str, Any]:
        """Get Google's legacy event color palette."""
        return await self._get("/colors")

    async def async_events(
        self,
        calendar_id: str,
        start: str | None = None,
        end: str | None = None,
        sync_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Get a full or incremental event page set."""
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        next_sync_token: str | None = None
        while True:
            params = {
                "singleEvents": "true",
                "showDeleted": "true",
                "maxResults": "2500",
            }
            if sync_token:
                params["syncToken"] = sync_token
            elif start is not None and end is not None:
                params.update({"timeMin": start, "timeMax": end})
            if page_token:
                params["pageToken"] = page_token
            payload = await self._get(
                f"/calendars/{quote(calendar_id, safe='')}/events", params
            )
            items.extend(
                item for item in payload.get("items", []) if isinstance(item, dict)
            )
            page_token = payload.get("nextPageToken")
            token = payload.get("nextSyncToken")
            if isinstance(token, str):
                next_sync_token = token
            if not isinstance(page_token, str):
                return items, next_sync_token

