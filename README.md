# Google Calendar Colors for Week Planner

> [!IMPORTANT]
> This is a personal project provided as-is. No support, feature requests,
> compatibility guarantees, or maintenance commitments are offered.

Google Calendar Colors is a HACS-installable Home Assistant custom integration plus a
color-aware distribution of `week-planner-card`. It keeps the built-in Google Calendar
entities intact while allowing one calendar entry to opt into Google's per-event legacy
colors and custom labels:

```yaml
- entity: calendar.family_calendar
  name: Family
  inherit_event_colors: true
  filter: ${ FAMCAL }
```

No color/person map, title convention, extra calendar entity, or TouchKio-specific setup
is required. The example person, birthday, and holiday calendars retain their configured
colors. Family remains one entity and `${ FAMCAL }` is still evaluated before rendering.

## What this package preserves

The frontend is based on week-planner-card 1.14.1. Its calendar options, global filters,
per-calendar filters, similar-event combining, navigation, weather, descriptions,
locations, actions/dialogs, legend, past-event classes, compact mode, responsive columns,
and editor remain on their original code paths. `inherit_event_colors` adds one metadata
lookup and changes only the matched event's color variables.

For Family events it sets `--event-color`, upstream's existing `--border-color`, and
`--event-text-color`. Your existing rule continues to work unchanged:

```css
.event {
  color: #333333 !important;
  background-color: var(--border-color) !important;
}
```

The explicit `!important` text color continues to win over the accessible automatic text
choice. Past-event opacity/background rules and every unrelated style remain untouched.

## Requirements

- Home Assistant 2026.10.0 or newer
- HACS
- A Google Cloud OAuth client with the Google Calendar API enabled
- The existing built-in Google integration and `calendar.family_calendar`

The separate read-only OAuth connection is intentional. Home Assistant's standard event
model drops provider-specific color fields, while a custom integration has no supported
right to reuse another integration's private token or coordinator. See
[the architecture decision](docs/architecture.md).

## Install

1. In HACS, add this repository as a custom **Integration** repository, then install
   **Google Calendar Colors for Week Planner**.
2. Restart Home Assistant. This registers the integration, its authenticated WebSocket
   command, and `/google_calendar_colors/week-planner-card.js`.
3. In **Settings → Devices & services → Add integration**, select **Google Calendar
   Colors**. If prompted, add Google application credentials. In Google Cloud, enable the
   Calendar API, configure the consent screen, and add Home Assistant's displayed redirect
   URI to a Web application OAuth client.
4. Authorize the read-only Calendar scope. Select the shared **Family** Google calendar
   and match it to `calendar.family_calendar`.
5. In **Settings → Dashboards → Resources**, remove or disable the old
   `week-planner-card.js` resource and add this JavaScript module:

   ```text
   /google_calendar_colors/week-planner-card.js?v=1.0.0
   ```

   Do not load both distributions: both correctly register `custom:week-planner-card`.
6. Apply the single dashboard change below and reload the dashboard.

## Exact migration for the supplied dashboard

Change only these three lines inside the existing `custom:config-template-card` calendar
list:

```diff
                 - entity: calendar.family_calendar
                   name: Family
-                  color: '#4A90E2'
+                  inherit_event_colors: true
                   filter: ${ FAMCAL }
```

An anonymized equivalent of the supplied YAML with that functional change is in
[`examples/family-calendar-dashboard.yaml`](examples/family-calendar-dashboard.yaml).
The Family Bubble Card may keep its blue button background; it indicates visibility and
does not supply event colors.

## Color and refresh behavior

The exact Google six-digit hex value is selected in this order:

1. The event's custom `eventLabelId` color.
2. The event's legacy `colorId` color.
3. The selected Google calendar's current default color.
4. The calendar entry's configured `color`, if present.
5. week-planner-card's normal theme/inherit fallback.

Steps 1–3 run only when `inherit_event_colors: true`. Label definitions, the legacy
palette, and calendar default refresh automatically. Event ranges use Google incremental
sync; deletions, cancellations, recolors, recurring exceptions, and moved instances update
without a dashboard reload. The default metadata interval is five minutes and can be set
from 60 to 3600 seconds in integration options. The card's existing `updateInterval`
(default 60 seconds) determines when it next asks for metadata.

Black or white event text is selected using the larger WCAG 2 relative-luminance contrast
ratio. Dashboard CSS retains normal precedence. Google values are accepted only as strict
six-digit hex colors and cannot inject CSS. Event descriptions are rendered as text rather
than untrusted HTML.

## Privacy and security

- OAuth uses only `https://www.googleapis.com/auth/calendar.readonly`.
- Tokens are stored/refreshed by Home Assistant and are never logged.
- The metadata command requires an authenticated Home Assistant WebSocket and read
  permission for the configured calendar entity.
- The backend sends UID/recurrence/time identity, resolved colors, and color source only.
  It never sends titles, descriptions, locations, attendees, emails, label names, or the
  calendar ID through the companion API.
- In-memory caches contain Google event IDs, event time/identity/color fields, label maps,
  and sync tokens. They are discarded on restart and never persisted by this integration.
- Diagnostics contain counts and booleans only; normal logs never include calendar IDs or
  event content.

## Manual verification checklist

1. Install through HACS and restart Home Assistant.
2. Complete Google Calendar Colors UI setup and select the Family calendar plus
   `calendar.family_calendar`.
3. Replace the old card resource with the bundled resource.
4. Add only `inherit_event_colors: true` and remove only Family's `color` line.
5. Confirm Person One and Person Two still render `#ff7d69` and `#fdbf6f` respectively.
6. Confirm two differently colored Family events render with their exact Google colors.
7. Recolor a Family event, wait for both refresh intervals, and confirm it changes without
   reloading the dashboard.
8. Create/recolor a Google custom event label and confirm automatic discovery.
9. Create an uncolored event and confirm it uses the Google Family calendar default.
10. Toggle the Family Bubble Card and confirm every Family color hides/shows together.
11. Exercise Today/Tomorrow/Week/Biweek/Month/Bimonth, descriptions, locations, weather,
    past events, event details, Add Event, and responsive/compact layouts.
12. Verify light and dark themes plus TouchKio. No TouchKio configuration is needed.
13. Temporarily disable the integration and confirm normal events remain, using fallback
    styling rather than disappearing.
14. Remove the integration and restore the old card resource to verify clean rollback.

## Troubleshooting

**Events appear but have a fallback color.** Confirm the target entity selected in the
integration exactly matches the YAML entity, the bundled card resource is loaded, and the
calendar entry has the boolean `inherit_event_colors: true` (not a quoted string). Check
the browser console and integration diagnostics; neither exposes event content.

**OAuth says the app is not verified.** For a personal Google Cloud project in Testing,
add the Google account as a test user. Confirm the Calendar API is enabled and the redirect
URI exactly matches the URI Home Assistant shows.

**A recolor is delayed.** The upper bound is normally the metadata interval plus the card
`updateInterval`, and can be longer during Google rate limiting or an outage. A 60-second
metadata interval is the supported minimum.

**The browser reports the custom element is already defined.** Both the upstream and this
card resources are loaded. Keep only `/google_calendar_colors/week-planner-card.js`.

**A private shared event does not color-match.** Google may omit stable identity/details
for events the connected account cannot read. Grant appropriate calendar read access or
allow the safe fallback.

## Upgrade and removal

Upgrade through HACS, restart Home Assistant when backend files change, and bump the
resource query string to the release version to bypass browser caches. Config entry and
calendar entity IDs are stable across upgrades.

To remove, restore the upstream `week-planner-card.js` resource, remove
`inherit_event_colors: true` (optionally restore `color: '#4A90E2'`), delete the Google
Calendar Colors config entry, uninstall it in HACS, and restart. The built-in Google config,
entities, events, and automations are never modified.

## Development and release

See [`docs/development.md`](docs/development.md). CI runs backend tests and lint, frontend
tests and the production build, HACS structure validation, and HACS/brand validation.
Versioning follows SemVer; release tags use `vMAJOR.MINOR.PATCH`. The project is MIT
licensed, including the retained upstream card license.

## Honest limitations

- Supported public APIs require a second OAuth consent; the built-in Google token is not
  reused.
- This release targets current Home Assistant and week-planner-card 1.14.1 rather than
  promising compatibility with arbitrary future upstream internal changes.
- Metadata refresh is polling/incremental sync, not an instant Google push notification.
- Google/API outages and unreadable private-event identity cause safe fallback colors.
- The supplied dashboard was the only compatibility baseline tested; no claim is made for
  unrelated forks that changed week-planner-card's event model or custom-element name.

