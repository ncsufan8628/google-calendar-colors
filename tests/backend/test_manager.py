"""Tests for incremental cache refresh, recolors, and deletion."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2] / "custom_components" / "google_calendar_colors"
PACKAGE = "custom_components.google_calendar_colors"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules.setdefault(PACKAGE, package)


def load(name):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", ROOT / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("color")
api_stub = types.ModuleType(f"{PACKAGE}.api")


class GoogleSyncTokenExpired(Exception):
    pass


class GoogleApiError(Exception):
    pass


api_stub.GoogleCalendarApi = object
api_stub.GoogleApiError = GoogleApiError
api_stub.GoogleSyncTokenExpired = GoogleSyncTokenExpired
sys.modules[api_stub.__name__] = api_stub
manager_module = load("manager")


class FakeApi:
    def __init__(self):
        self.event_calls = []
        self.responses = []
        self.labels = [{"id": "work", "backgroundColor": "#123456"}]

    async def async_calendar(self, calendar_id):
        return {"labelProperties": {"eventLabels": self.labels}}

    async def async_colors(self):
        return {"event": {"2": {"background": "#00ff00"}}}

    async def async_calendar_list(self):
        return [{"id": "family", "backgroundColor": "#abcdef"}]

    async def async_events(self, calendar_id, start=None, end=None, sync_token=None):
        self.event_calls.append((start, end, sync_token))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def google_event(event_id="one", **values):
    return {
        "id": event_id,
        "iCalUID": f"{event_id}@example.com",
        "status": "confirmed",
        "start": {"dateTime": "2026-12-01T10:00:00Z"},
        "end": {"dateTime": "2026-12-01T11:00:00Z"},
        **values,
    }


@pytest.mark.asyncio
async def test_initial_then_incremental_recolor_and_delete():
    api = FakeApi()
    api.responses = [([google_event(eventLabelId="work")], "token-1")]
    manager = manager_module.ColorManager(api, "family", None, 0)
    initial = await manager.async_get("2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z")
    assert initial[0]["color"] == "#123456"
    assert api.event_calls[0][2] is None

    api.responses = [([google_event(colorId="2")], "token-2")]
    recolored = await manager.async_get("2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z")
    assert recolored[0]["color"] == "#00ff00"
    assert api.event_calls[1][2] == "token-1"

    api.responses = [([{"id": "one", "status": "cancelled"}], "token-3")]
    assert await manager.async_get("2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z") == []


@pytest.mark.asyncio
async def test_expired_sync_token_performs_full_resync():
    api = FakeApi()
    api.responses = [([google_event()], "old")]
    manager = manager_module.ColorManager(api, "family", None, 0)
    await manager.async_get("2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z")
    api.responses = [GoogleSyncTokenExpired(), ([google_event("new")], "new-token")]
    result = await manager.async_get("2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z")
    assert result[0]["uid"] == "new@example.com"
    assert api.event_calls[-1][:2] == (
        "2026-12-01T00:00:00Z",
        "2026-12-02T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_temporary_api_failure_serves_stale_cache():
    api = FakeApi()
    api.responses = [([google_event()], "token")]
    manager = manager_module.ColorManager(api, "family", None, 0)
    expected = await manager.async_get(
        "2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z"
    )
    api.responses = [GoogleApiError("rate limited")]
    actual = await manager.async_get(
        "2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z"
    )
    assert actual == expected


@pytest.mark.asyncio
async def test_new_and_recolored_label_is_discovered():
    api = FakeApi()
    api.responses = [([google_event(eventLabelId="work")], "one")]
    manager = manager_module.ColorManager(api, "family", None, 0)
    first = await manager.async_get(
        "2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z"
    )
    assert first[0]["color"] == "#123456"
    api.labels = [{"id": "work", "backgroundColor": "#654321"}]
    api.responses = [([google_event(eventLabelId="work")], "two")]
    second = await manager.async_get(
        "2026-12-01T00:00:00Z", "2026-12-02T00:00:00Z"
    )
    assert second[0]["color"] == "#654321"


def test_diagnostics_never_include_ids_tokens_or_content():
    manager = manager_module.ColorManager(FakeApi(), "private-id", "#ffffff", 300)
    payload = manager.diagnostics()
    rendered = repr(payload)
    assert "private-id" not in rendered
    assert "sync_token" not in rendered
    assert set(payload) == {
        "calendar_configured",
        "calendar_default_available",
        "label_count",
        "legacy_color_count",
        "range_cache_count",
        "cached_event_count",
        "incremental_sync_ranges",
        "refresh_interval",
    }


def test_websocket_security_contract_is_entity_scoped_and_authenticated():
    source = (ROOT / "websocket.py").read_text()
    assert "check_entity(entity_id, POLICY_READ)" in source
    assert 'f"{DOMAIN}/get_events"' in source
    assert 'hass.data[DOMAIN]["entities"].get(entity_id)' in source
    assert "requires_auth = False" not in source


def test_oauth_requests_use_home_assistant_refreshing_session():
    source = (ROOT / "api.py").read_text()
    assert "OAuth2Session" in source
    assert "self._oauth_session.async_request" in source
    assert "access_token" not in source


def test_oauth_config_flow_supports_reauthentication():
    source = (ROOT / "config_flow.py").read_text()
    assert "async def async_step_reauth(" in source
    assert "return await self.async_step_user()" in source
    assert "self.source == SOURCE_REAUTH" in source
    assert "self.async_update_reload_and_abort(" in source

