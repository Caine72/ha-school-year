"""Tests for the School Year source parser and date calculations."""

from datetime import date, datetime

import pytest

from custom_components.school_year.const import (
    STATE_OUTSIDE_TERM,
    STATE_SCHOOL_CLOSED,
    STATE_SCHOOL_DAY,
    STATE_WEEKEND,
)
from custom_components.school_year.parser import parse_school_year_html

SOURCE_URL = "https://example.com/school-year"
FETCHED_AT = datetime.fromisoformat("2026-01-01T12:00:00+01:00")

COMPLETE_HTML = """
<html><body>
<h2>Vårterminen 2026</h2>
<h3>Skolstart</h3><p>12 januari</p>
<h3>Lov och lediga dagar</h3>
<p>2-6 mars (Sportlov)</p>
<p>30/3-2/4 (Påsklov) 7/5 (K-dag)</p>
<h3>Skolavslutning</h3><p>12 juni</p>
<h2>Höstterminen 2026</h2>
<h3>Skolstart</h3><p>20 augusti</p>
<h3>Lov och lediga dagar</h3><p>26-30/10 (Läslov)</p>
<h3>Terminsslut</h3><p>18 december</p>
<p>Senast uppdaterad: 4 juni 2026</p>
<h2>Ledighetsansökan</h2><p>1/1 should not be parsed</p>
</body></html>
"""


def test_parse_complete_schedule_and_infer_break() -> None:
    """A representative source page becomes normalized terms and closures."""
    data = parse_school_year_html(COMPLETE_HTML, SOURCE_URL, fetched_at=FETCHED_AT)

    assert len(data.terms) == 2
    assert data.terms[0].start == date(2026, 1, 12)
    assert data.terms[0].end == date(2026, 6, 12)
    assert data.source_updated == date(2026, 6, 4)

    events_by_type = {event.event_type: event for event in data.events}
    assert events_by_type["easter_break"].start == date(2026, 3, 30)
    assert events_by_type["easter_break"].end == date(2026, 4, 2)
    assert events_by_type["k_day"].start == date(2026, 5, 7)
    assert events_by_type["summer_break"].start == date(2026, 6, 13)
    assert events_by_type["summer_break"].end == date(2026, 8, 19)
    assert events_by_type["summer_break"].calendar_end == date(2026, 8, 20)


def test_status_and_next_school_day() -> None:
    """Weekdays, weekends, closures, and dates outside terms are distinguished."""
    data = parse_school_year_html(COMPLETE_HTML, SOURCE_URL, fetched_at=FETCHED_AT)

    assert data.status_for_day(date(2026, 2, 2)).state == STATE_SCHOOL_DAY
    assert data.status_for_day(date(2026, 2, 7)).state == STATE_WEEKEND
    assert data.status_for_day(date(2026, 3, 3)).state == STATE_SCHOOL_CLOSED
    assert data.status_for_day(date(2025, 12, 1)).state == STATE_OUTSIDE_TERM
    assert data.next_school_day_on_or_after(date(2026, 3, 6)) == date(2026, 3, 9)
    assert data.next_school_day_on_or_after(date(2026, 3, 6), max_days_ahead=2) is None


def test_inferred_breaks_can_be_disabled() -> None:
    """Only explicit source events remain when inference is disabled."""
    data = parse_school_year_html(
        COMPLETE_HTML,
        SOURCE_URL,
        include_inferred_breaks=False,
        fetched_at=FETCHED_AT,
    )

    assert all(not event.inferred for event in data.events)


@pytest.mark.parametrize(
    ("html", "message"),
    [
        ("<h2>Not a school term</h2>", "No school terms"),
        (
            "<h2>Vårterminen 2026</h2><h3>Skolstart</h3><p>12 januari</p>",
            "Incomplete school terms",
        ),
        (
            """
            <h2>Vårterminen 2026</h2>
            <h3>Skolstart</h3><p>12 juni</p>
            <h3>Skolavslutning</h3><p>12 januari</p>
            """,
            "starts after it ends",
        ),
    ],
)
def test_invalid_or_partial_source_is_rejected(html: str, message: str) -> None:
    """A structurally recognizable but unusable page does not replace cached data."""
    with pytest.raises(ValueError, match=message):
        parse_school_year_html(html, SOURCE_URL, fetched_at=FETCHED_AT)
