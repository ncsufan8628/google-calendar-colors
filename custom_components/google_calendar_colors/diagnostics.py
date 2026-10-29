"""Privacy-preserving diagnostics."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DIAGNOSTICS, CONF_ENTITY_ID, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return no identifiers, tokens, event details, or calendar content."""
    manager = hass.data[DOMAIN]["entries"].get(entry.entry_id)
    return {
        "integration": DOMAIN,
        "diagnostics_enabled": entry.options.get(CONF_DIAGNOSTICS, False),
        "target_entity_configured": bool(entry.data.get(CONF_ENTITY_ID)),
        "cache": manager.diagnostics() if manager is not None else None,
    }

