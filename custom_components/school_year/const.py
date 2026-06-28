"""Constants for the School Year integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "school_year"

DEFAULT_URL = (
    "https://skelleftea.se/invanare/startsida/"
    "forskola-skola-och-utbildning/grundskola/"
    "lov-lasarstider-och-ledigheter"
)

DEFAULT_POLL_HOURS = 24
MIN_POLL_HOURS = 1
MAX_POLL_HOURS = 168
DEFAULT_SCHOOL_DAY_LOOKAHEAD_DAYS = 2
MIN_SCHOOL_DAY_LOOKAHEAD_DAYS = 0
MAX_SCHOOL_DAY_LOOKAHEAD_DAYS = 14
DEFAULT_UPDATE_INTERVAL = timedelta(hours=DEFAULT_POLL_HOURS)

SUPPORTED_SOURCE = "Skellefteå kommun"
SUPPORTED_SCHOOL_FORM = "Grundskola"
SUPPORTED_PARSER = "skelleftea_grundskola"

# User-facing config keys. These are intentionally readable because Home Assistant
# falls back to humanizing the raw key if a custom integration translation is not
# loaded by the frontend.
CONF_PAGE_CHECK_INTERVAL_HOURS = "page_check_interval_hours"
CONF_INCLUDE_INFERRED_LONG_BREAKS = "include_inferred_long_breaks"
CONF_SCHOOL_DAY_LOOKAHEAD_DAYS = "school_day_lookahead_days"
LEGACY_CONF_MENU_LOOKAHEAD_DAYS = "school_menu_lookahead_days"

# Legacy v0.1.0/v0.1.1 keys. Keep these for migration and fallback reads.
LEGACY_CONF_POLL_HOURS = "poll_hours"
LEGACY_CONF_INCLUDE_INFERRED_BREAKS = "include_inferred_breaks"

ATTR_SOURCE_URL = "source_url"
ATTR_SOURCE_UPDATED = "source_updated"
ATTR_FETCHED_AT = "fetched_at"
ATTR_CURRENT_TERM = "current_term"
ATTR_ACTIVE_EVENTS = "active_events"
ATTR_NEXT_EVENT = "next_event"
ATTR_TERMS = "terms"
ATTR_EVENTS = "events"
ATTR_STATUS = "status"
ATTR_REASON = "reason"

STATE_SCHOOL_DAY = "school_day"
STATE_WEEKEND = "weekend"
STATE_SCHOOL_CLOSED = "school_closed"
STATE_OUTSIDE_TERM = "outside_term"
STATE_UNKNOWN = "unknown"
