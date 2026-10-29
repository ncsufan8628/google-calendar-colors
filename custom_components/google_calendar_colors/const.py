"""Constants for Google Calendar Colors."""

from typing import Final

DOMAIN: Final = "google_calendar_colors"
CONF_CALENDAR_ID: Final = "calendar_id"
CONF_ENTITY_ID: Final = "entity_id"
CONF_REFRESH_INTERVAL: Final = "refresh_interval"
CONF_DIAGNOSTICS: Final = "diagnostics"
DEFAULT_REFRESH_INTERVAL: Final = 300
MIN_REFRESH_INTERVAL: Final = 60
MAX_REFRESH_INTERVAL: Final = 3600
GOOGLE_API_BASE: Final = "https://www.googleapis.com/calendar/v3"
OAUTH2_AUTHORIZE: Final = "https://accounts.google.com/o/oauth2/auth"
OAUTH2_TOKEN: Final = "https://oauth2.googleapis.com/token"
OAUTH2_SCOPE: Final = "https://www.googleapis.com/auth/calendar.readonly"
CARD_URL: Final = "/google_calendar_colors/week-planner-card.js"

