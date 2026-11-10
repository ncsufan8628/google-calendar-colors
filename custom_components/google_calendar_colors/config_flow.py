"""Config and options flows for Google Calendar Colors."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, override

import probatio
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_CALENDAR_ID,
    CONF_DIAGNOSTICS,
    CONF_ENTITY_ID,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    GOOGLE_API_BASE,
    MAX_REFRESH_INTERVAL,
    MIN_REFRESH_INTERVAL,
    OAUTH2_SCOPE,
)

_LOGGER = logging.getLogger(__name__)


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle Google OAuth and calendar/entity selection."""

    DOMAIN = DOMAIN

    def __init__(self) -> None:
        super().__init__()
        self._oauth_data: dict[str, Any] | None = None
        self._calendar_choices: list[dict[str, str]] = []

    @property
    @override
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    @override
    def extra_authorize_data(self) -> dict[str, str]:
        return {
            "scope": OAUTH2_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Restart OAuth for an existing config entry."""
        return await self.async_step_user()

    async def _async_load_calendars(self, access_token: str) -> list[dict[str, str]]:
        session = async_get_clientsession(self.hass)
        choices: list[dict[str, str]] = []
        page_token: str | None = None
        while True:
            params = {"minAccessRole": "reader", "maxResults": "250"}
            if page_token:
                params["pageToken"] = page_token
            response = await session.get(
                f"{GOOGLE_API_BASE}/users/me/calendarList",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status >= 400:
                response.release()
                raise ConnectionError("Unable to list Google calendars")
            payload = await response.json()
            for item in payload.get("items", []):
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    choices.append(
                        {
                            "value": item["id"],
                            "label": item.get("summaryOverride")
                            or item.get("summary")
                            or "Google calendar",
                            "backgroundColor": item.get("backgroundColor", ""),
                        }
                    )
            page_token = payload.get("nextPageToken")
            if not isinstance(page_token, str):
                return choices

    @override
    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Validate OAuth, then continue to calendar selection."""
        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
            return self.async_update_reload_and_abort(
                entry, data={**entry.data, **data}
            )
        try:
            self._calendar_choices = await self._async_load_calendars(
                data["token"]["access_token"]
            )
        except (ClientError, KeyError, ConnectionError, TimeoutError):
            return self.async_abort(reason="cannot_connect")
        if not self._calendar_choices:
            return self.async_abort(reason="no_calendars")
        self._oauth_data = data
        return await self.async_step_calendar()

    async def async_step_calendar(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the Google calendar and existing HA calendar entity."""
        if self._oauth_data is None or not self._calendar_choices:
            return self.async_abort(reason="oauth_error")
        if user_input is not None:
            calendar_id = user_input[CONF_CALENDAR_ID]
            if any(
                entry.data.get(CONF_ENTITY_ID) == user_input[CONF_ENTITY_ID]
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            ):
                return self.async_abort(reason="entity_already_configured")
            choice = next(
                item for item in self._calendar_choices if item["value"] == calendar_id
            )
            await self.async_set_unique_id(
                f"{calendar_id}:{user_input[CONF_ENTITY_ID]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{choice['label']} colors",
                data={
                    **self._oauth_data,
                    CONF_CALENDAR_ID: calendar_id,
                    CONF_ENTITY_ID: user_input[CONF_ENTITY_ID],
                    "calendar_default": choice.get("backgroundColor"),
                },
                options={
                    CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
                    CONF_DIAGNOSTICS: False,
                },
            )

        return self.async_show_form(
            step_id="calendar",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_CALENDAR_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": item["value"], "label": item["label"]}
                                for item in self._calendar_choices
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    probatio.Required(CONF_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(domain="calendar")
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Configure safe refresh and diagnostic behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_REFRESH_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_REFRESH_INTERVAL,
                            max=MAX_REFRESH_INTERVAL,
                            step=30,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="seconds",
                        )
                    ),
                    probatio.Required(
                        CONF_DIAGNOSTICS,
                        default=self.config_entry.options.get(CONF_DIAGNOSTICS, False),
                    ): bool,
                }
            ),
        )

