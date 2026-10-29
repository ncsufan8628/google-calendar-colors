"""Google Calendar Colors integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .api import GoogleCalendarApi
from .const import (
    CARD_URL,
    CONF_CALENDAR_ID,
    CONF_ENTITY_ID,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)
from .manager import ColorManager
from .websocket import async_register


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the shared API and serve the bundled card."""
    hass.data.setdefault(DOMAIN, {"entries": {}, "entities": {}})
    async_register(hass)
    card_path = Path(__file__).parent / "www" / "week-planner-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one selected Google calendar."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(
        hass, entry, implementation
    )
    await oauth_session.async_ensure_token_valid()
    manager = ColorManager(
        GoogleCalendarApi(oauth_session),
        entry.data[CONF_CALENDAR_ID],
        entry.data.get("calendar_default"),
        int(entry.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)),
    )
    hass.data[DOMAIN]["entries"][entry.entry_id] = manager
    hass.data[DOMAIN]["entities"][entry.data[CONF_ENTITY_ID]] = manager
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload without modifying the built-in Google integration or its entities."""
    hass.data[DOMAIN]["entries"].pop(entry.entry_id, None)
    hass.data[DOMAIN]["entities"].pop(entry.data[CONF_ENTITY_ID], None)
    return True

