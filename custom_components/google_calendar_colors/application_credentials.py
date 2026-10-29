"""Application credentials support for Google Calendar Colors."""

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN

AUTHORIZATION_SERVER = AuthorizationServer(OAUTH2_AUTHORIZE, OAUTH2_TOKEN)


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return a standard Home Assistant local OAuth implementation."""
    return config_entry_oauth2_flow.LocalOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        credential.client_secret,
        AUTHORIZATION_SERVER.authorize_url,
        AUTHORIZATION_SERVER.token_url,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return Google Cloud setup links for the credentials dialog."""
    return {
        "oauth_consent_url": "https://console.cloud.google.com/apis/credentials/consent",
        "oauth_creds_url": "https://console.cloud.google.com/apis/credentials",
        "calendar_api_url": "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com",
    }

