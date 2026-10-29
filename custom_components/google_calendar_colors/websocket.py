"""Authenticated frontend metadata API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import probatio
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN


@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/get_events",
        probatio.Required("entity_id"): cv.entity_id,
        probatio.Required("start"): cv.datetime,
        probatio.Required("end"): cv.datetime,
    }
)
@websocket_api.async_response
async def websocket_get_events(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return color metadata for a configured entity and range."""
    entity_id: str = msg["entity_id"]
    if not connection.user.permissions.check_entity(entity_id, POLICY_READ):
        raise Unauthorized(entity_id=entity_id)
    manager = hass.data[DOMAIN]["entities"].get(entity_id)
    if manager is None:
        connection.send_error(msg["id"], "not_configured", "Entity is not configured")
        return
    start: datetime = msg["start"]
    end: datetime = msg["end"]
    if start >= end:
        connection.send_error(msg["id"], "invalid_range", "Start must be before end")
        return
    try:
        events = await manager.async_get(start.isoformat(), end.isoformat())
    except Exception:  # Home Assistant reports details in integration logs only.
        connection.send_error(msg["id"], "unavailable", "Color metadata unavailable")
        return
    connection.send_result(msg["id"], {"events": events})


def async_register(hass: HomeAssistant) -> None:
    """Register the WebSocket command once."""
    websocket_api.async_register_command(hass, websocket_get_events)

