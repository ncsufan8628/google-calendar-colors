# ADR 0001: Companion OAuth integration and compatible card fork

Status: accepted, 2026-10-29.

## Context

Home Assistant Core's current Google integration converts `gcal_sync.model.Event`
objects to the standard `CalendarEvent` dataclass. The conversion deliberately exposes
calendar-neutral fields (`uid`, `recurrence_id`, times, summary, description, location,
RRULE, and status); it does not expose Google's `colorId` or `eventLabelId`. The calendar
REST/WebSocket transport serializes that standard model. Current week-planner-card 1.14.1
requests `/api/calendars/<entity>` and assigns one configured color per calendar.

Core therefore has no supported extension point through which a custom integration can
add provider-only fields to the existing `calendar.family_calendar` response. Accessing
the built-in Google integration's private coordinator or token storage would couple this
package to undocumented internals and violate the token boundary.

## Decision

Ship one HACS integration repository containing two cooperating artifacts:

1. A custom integration with its own Google read-only OAuth connection. It selects one
   Google calendar and matches it to one existing Home Assistant calendar entity. An
   authenticated Home Assistant WebSocket command returns only event identity and color
   metadata for authorized users of that entity.
2. A maintained patch of upstream week-planner-card. All upstream configuration and
   rendering paths remain in place. Only entries explicitly setting
   `inherit_event_colors: true` query the companion command and replace that event's
   existing `--border-color`. It also sets `--event-color` and a contrast variable.

The card waits for both normal events and their metadata before rendering each refresh,
avoiding a visible recolor/layout shift. A metadata failure leaves normal events usable
and applies the documented fallback. The existing polling cycle refreshes colors without
a dashboard reload.

## Identity and matching

The backend sends no title, description, location, attendee, email, or calendar ID. The
primary key is `iCalUID` plus the Google instance ID exposed by Home Assistant as
`recurrence_id`. A secondary `iCalUID` plus exact provider start value handles versions
where an instance ID is absent. The instance ID and `originalStartTime` remain in the
metadata to distinguish recurring exceptions. Matching never uses a title.

All-day dates stay date strings and are not timezone-shifted. Timed values keep their
RFC3339 offsets, including the two distinct offsets during a daylight-saving fold.
Moved recurring exceptions retain their stable instance ID, so a changed start does not
break the primary match. Identical titles and identical start times remain distinct by
UID/instance ID.

## Color resolution and cache

Resolution order is custom `eventLabelId`, legacy `colorId`, Google calendar-list default,
configured card `color`, then week-planner-card's normal `inherit` fallback. Google label
definitions (`Calendars.get`), legacy colors (`Colors.get`), and the CalendarList default
are refreshed on the configured interval. Event ranges have bounded in-memory caches and
use Google's `nextSyncToken`; HTTP 410 discards only the expired range and performs a full
sync. Cancelled/deleted items remove cached events. At most eight viewed ranges are kept.

Every Google color must match `#[0-9a-fA-F]{6}` in both backend and frontend. Custom label
names are neither needed nor sent. Deleted/missing/invalid labels fall through safely.

## Authentication, authorization, and privacy

The OAuth scope is `calendar.readonly`. Home Assistant's application-credentials and
OAuth2Session helpers store and refresh tokens; this code never reads the built-in
integration's tokens and never logs tokens. The metadata command uses Home Assistant's
authenticated WebSocket connection and enforces `POLICY_READ` on the selected entity.

Memory holds provider IDs, sync tokens, label maps, and the requested event ranges. These
are not persisted by this integration. Diagnostics expose counts and boolean state only.
Normal logging contains no calendar IDs or event content. The browser receives the same
event identities already present in Home Assistant plus resolved colors.

## Accessibility

Google backgrounds use exact six-digit hex values. Text is black or white according to
the larger WCAG 2 relative-luminance contrast ratio. The card places that choice in
`--event-text-color`; a dashboard rule such as `color: #333 !important` retains precedence.
Theme changes do not affect the supplied Google color, and all unrelated theme/layout
variables remain upstream behavior.

## Alternatives rejected

- Monkey-patching Core or replacing `google`: unsafe upgrades and entity/automation risk.
- Reading the built-in config entry/coordinator: private internals and silent token access.
- One virtual calendar per color: changes identity, filtering, actions, and automations.
- Title parsing or manual maps: violates Google-as-source-of-truth.
- An unauthenticated HTTP metadata endpoint: unnecessary exposure of calendar metadata.
- A second HACS repository: adds installation/version skew without a technical benefit.

## Consequences and limitations

One additional Google OAuth consent is unavoidable with supported public APIs. The Google
Calendar API must be enabled for that OAuth client. This package intentionally does not
write event labels. Color freshness is bounded by the larger of the card update interval
and integration metadata interval (minimum 60 seconds), subject to Google availability
and rate limits. During an outage, normal events still render using configured/upstream
fallback colors. Private events whose stable identity is withheld by Google may not match.

