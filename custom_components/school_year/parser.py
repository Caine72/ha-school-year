"""Parser for Skellefteå kommun grundskola school-year pages.

The parser intentionally avoids external dependencies. It is based on the
stable public page structure: term heading -> subsection heading -> date rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from typing import Any

from .const import (
    STATE_OUTSIDE_TERM,
    STATE_SCHOOL_CLOSED,
    STATE_SCHOOL_DAY,
    STATE_WEEKEND,
    SUPPORTED_PARSER,
    SUPPORTED_SCHOOL_FORM,
    SUPPORTED_SOURCE,
)

MONTHS: dict[str, int] = {
    "januari": 1,
    "februari": 2,
    "mars": 3,
    "april": 4,
    "maj": 5,
    "juni": 6,
    "juli": 7,
    "augusti": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}

TERM_RE = re.compile(r"^(Vårterminen|Höstterminen)\s+(\d{4})$", re.IGNORECASE)
DATE_UPDATED_RE = re.compile(r"Senast\s+uppdaterad:\s*([0-9]{1,2}\s+[A-Za-zÅÄÖåäö]+\s+[0-9]{4})")
DATE_START_RE = re.compile(
    r"(?<!\S)(?:"
    r"\d{1,2}/\d{1,2}\s*-\s*\d{1,2}/\d{1,2}"
    r"|\d{1,2}\s*-\s*\d{1,2}/\d{1,2}"
    r"|\d{1,2}\s*-\s*\d{1,2}\s+[A-Za-zÅÄÖåäö]+"
    r"|\d{1,2}\s+[A-Za-zÅÄÖåäö]+"
    r"|\d{1,2}/\d{1,2}"
    r")\b"
)

TARGET_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "a"}


@dataclass(frozen=True)
class SchoolEvent:
    """A normalized school-year event.

    The end date is inclusive in this integration's internal data model.
    Calendar entities convert it to an exclusive all-day end date.
    """

    uid: str
    name: str
    event_type: str
    start: date
    end: date
    school_closed: bool
    term: str | None
    raw: str
    inferred: bool = False

    @property
    def calendar_end(self) -> date:
        """Return the exclusive all-day end date used by CalendarEvent."""
        return self.end + timedelta(days=1)

    def is_active(self, day: date) -> bool:
        """Return true if this event is active on the given day."""
        return self.start <= day <= self.end

    def is_upcoming_or_active(self, day: date) -> bool:
        """Return true if this event has not fully passed."""
        return self.end >= day

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant attribute-safe dictionary."""
        return {
            "uid": self.uid,
            "name": self.name,
            "type": self.event_type,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "school_closed": self.school_closed,
            "term": self.term,
            "raw": self.raw,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class SchoolTerm:
    """A normalized school term."""

    name: str
    term_type: str
    year: int
    start: date | None = None
    end: date | None = None

    def contains(self, day: date) -> bool:
        """Return true if the day is inside this term."""
        if self.start is None or self.end is None:
            return False
        return self.start <= day <= self.end

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant attribute-safe dictionary."""
        return {
            "name": self.name,
            "type": self.term_type,
            "year": self.year,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
        }


@dataclass(frozen=True)
class SchoolDayStatus:
    """The evaluated status for a specific day."""

    state: str
    reason: str
    current_term: SchoolTerm | None
    active_events: tuple[SchoolEvent, ...]
    next_event: SchoolEvent | None

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant attribute-safe dictionary."""
        return {
            "state": self.state,
            "reason": self.reason,
            "current_term": self.current_term.name if self.current_term else None,
            "active_events": [event.as_dict() for event in self.active_events],
            "next_event": self.next_event.as_dict() if self.next_event else None,
        }


@dataclass(frozen=True)
class SchoolYearData:
    """Parsed school-year data."""

    source_url: str
    fetched_at: datetime
    source_updated: date | None
    terms: tuple[SchoolTerm, ...]
    events: tuple[SchoolEvent, ...]

    @property
    def closure_events(self) -> tuple[SchoolEvent, ...]:
        """Return all school-closed events."""
        return tuple(event for event in self.events if event.school_closed)

    def term_for_day(self, day: date) -> SchoolTerm | None:
        """Return the term containing the day, if any."""
        return next((term for term in self.terms if term.contains(day)), None)

    def active_events_for_day(
        self, day: date, *, closures_only: bool = False
    ) -> tuple[SchoolEvent, ...]:
        """Return events active on a given day."""
        events = self.closure_events if closures_only else self.events
        return tuple(event for event in events if event.is_active(day))

    def current_event_for_day(
        self, day: date, *, closures_only: bool = False
    ) -> SchoolEvent | None:
        """Return the first event active on a given day."""
        active = self.active_events_for_day(day, closures_only=closures_only)
        if not active:
            return None
        return sorted(active, key=lambda event: (event.start, event.end, event.name))[0]

    def next_event_for_day(self, day: date, *, closures_only: bool = False) -> SchoolEvent | None:
        """Return the current or next event relative to a day."""
        events = self.closure_events if closures_only else self.events
        upcoming = [event for event in events if event.is_upcoming_or_active(day)]
        if not upcoming:
            return None
        return sorted(upcoming, key=lambda event: (event.start, event.end, event.name))[0]

    def next_future_event_for_day(
        self, day: date, *, closures_only: bool = False
    ) -> SchoolEvent | None:
        """Return the next event that starts after the given day."""
        events = self.closure_events if closures_only else self.events
        upcoming = [event for event in events if event.start > day]
        if not upcoming:
            return None
        return sorted(upcoming, key=lambda event: (event.start, event.end, event.name))[0]

    def is_school_day(self, day: date) -> bool:
        """Return true if the given date is an actual school day."""
        return self.status_for_day(day).state == STATE_SCHOOL_DAY

    def next_school_day_on_or_after(
        self, day: date, *, max_days_ahead: int | None = None
    ) -> date | None:
        """Return the next school day on or after the given date.

        If max_days_ahead is provided, only dates up to that many days after the
        supplied date are considered. A value of 0 only checks the supplied date.
        """
        search_days = max_days_ahead if max_days_ahead is not None else 370
        for offset in range(search_days + 1):
            candidate = day + timedelta(days=offset)
            if self.is_school_day(candidate):
                return candidate
        return None

    def status_for_day(self, day: date) -> SchoolDayStatus:
        """Return school-day status for the given date."""
        active_closures = self.active_events_for_day(day, closures_only=True)
        next_closure = self.next_event_for_day(day, closures_only=True)
        current_term = self.term_for_day(day)

        if active_closures:
            return SchoolDayStatus(
                STATE_SCHOOL_CLOSED,
                "school closure event is active",
                current_term,
                active_closures,
                next_closure,
            )

        if current_term is None:
            return SchoolDayStatus(
                STATE_OUTSIDE_TERM,
                "date is outside known school terms",
                None,
                (),
                next_closure,
            )

        if day.weekday() >= 5:
            return SchoolDayStatus(
                STATE_WEEKEND,
                "date is a weekend",
                current_term,
                (),
                next_closure,
            )

        return SchoolDayStatus(
            STATE_SCHOOL_DAY,
            "date is a weekday inside a known term with no closure event",
            current_term,
            (),
            next_closure,
        )

    def as_attributes(self, day: date | None = None) -> dict[str, Any]:
        """Return a Home Assistant attribute-safe dictionary."""
        day = day or date.today()
        status = self.status_for_day(day)
        return {
            "source_url": self.source_url,
            "source_updated": self.source_updated.isoformat() if self.source_updated else None,
            "fetched_at": self.fetched_at.isoformat(),
            "source": SUPPORTED_SOURCE,
            "school_form": SUPPORTED_SCHOOL_FORM,
            "parser": SUPPORTED_PARSER,
            "status": status.state,
            "reason": status.reason,
            "current_term": status.current_term.name if status.current_term else None,
            "active_events": [event.as_dict() for event in status.active_events],
            "next_event": status.next_event.as_dict() if status.next_event else None,
            "terms": [term.as_dict() for term in self.terms],
            "events": [event.as_dict() for event in self.events],
        }


class _BlockTextExtractor(HTMLParser):
    """Extract readable text blocks while preserving page order."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self._current_tag: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Start capturing text for selected block tags."""
        if tag.lower() in TARGET_TAGS and self._current_tag is None:
            self._current_tag = tag.lower()
            self._current_text = []

    def handle_data(self, data: str) -> None:
        """Capture text inside the current block."""
        if self._current_tag is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finish current block."""
        if self._current_tag == tag.lower():
            text = _clean_text(" ".join(self._current_text))
            if text:
                self.blocks.append(text)
            self._current_tag = None
            self._current_text = []


def parse_school_year_html(
    html: str,
    source_url: str,
    *,
    include_inferred_breaks: bool = True,
    fetched_at: datetime | None = None,
) -> SchoolYearData:
    """Parse the school-year page into normalized data."""
    fetched_at = fetched_at or datetime.now().astimezone()
    blocks = _extract_blocks(html)
    full_text = _html_to_text(html)
    source_updated = _parse_source_updated(full_text)

    terms: list[SchoolTerm] = []
    events: list[SchoolEvent] = []

    current_term: SchoolTerm | None = None
    current_section: str | None = None

    for block in blocks:
        if _is_stop_heading(block):
            break

        term_match = TERM_RE.match(block)
        if term_match:
            term_type = term_match.group(1).lower()
            year = int(term_match.group(2))
            current_term = SchoolTerm(
                name=f"{term_match.group(1)} {year}",
                term_type="spring" if term_type.startswith("vår") else "autumn",
                year=year,
            )
            terms.append(current_term)
            current_section = None
            continue

        if current_term is None:
            continue

        normalized_section = _section_from_block(block)
        if normalized_section is not None:
            current_section = normalized_section
            continue

        if current_section is None or current_section == "download":
            continue

        rows = _split_closure_rows(block) if current_section == "closures" else [block]

        for row in rows:
            parsed_range = _parse_date_range(row, current_term.year)
            if parsed_range is None:
                continue

            start, end, match_end = parsed_range

            if current_section == "term_start":
                current_term = _replace_term(terms, current_term, start=start)
                events.append(
                    _build_event(
                        name="Skolstart",
                        event_type="term_start",
                        start=start,
                        end=end,
                        school_closed=False,
                        term=current_term.name,
                        raw=row,
                        inferred=False,
                    )
                )
                continue

            if current_section == "term_end":
                name = "Skolavslutning" if current_term.term_type == "spring" else "Terminsslut"
                current_term = _replace_term(terms, current_term, end=end)
                events.append(
                    _build_event(
                        name=name,
                        event_type="term_end",
                        start=start,
                        end=end,
                        school_closed=False,
                        term=current_term.name,
                        raw=row,
                        inferred=False,
                    )
                )
                continue

            if current_section == "closures":
                name = _extract_event_name(row, match_end)
                events.append(
                    _build_event(
                        name=name,
                        event_type=_event_type_from_name(name),
                        start=start,
                        end=end,
                        school_closed=True,
                        term=current_term.name,
                        raw=row,
                        inferred=False,
                    )
                )

    _validate_terms(terms)

    if include_inferred_breaks:
        events.extend(_infer_between_term_breaks(terms))

    terms_tuple = tuple(terms)
    events_tuple = tuple(sorted(events, key=lambda event: (event.start, event.end, event.name)))

    return SchoolYearData(
        source_url=source_url,
        fetched_at=fetched_at,
        source_updated=source_updated,
        terms=terms_tuple,
        events=events_tuple,
    )


def _validate_terms(terms: list[SchoolTerm]) -> None:
    """Reject partial or internally inconsistent parser results."""
    if not terms:
        raise ValueError("No school terms could be parsed from the source page")

    incomplete = [term.name for term in terms if term.start is None or term.end is None]
    if incomplete:
        raise ValueError(f"Incomplete school terms: {', '.join(incomplete)}")

    complete_terms = sorted(terms, key=lambda term: term.start or date.min)
    for term in complete_terms:
        if term.start is not None and term.end is not None and term.start > term.end:
            raise ValueError(f"School term starts after it ends: {term.name}")

    for previous, current in zip(complete_terms, complete_terms[1:], strict=False):
        if previous.end is not None and current.start is not None and current.start <= previous.end:
            raise ValueError(f"School terms overlap: {previous.name} and {current.name}")


def _extract_blocks(html: str) -> list[str]:
    """Extract ordered text blocks from HTML."""
    extractor = _BlockTextExtractor()
    extractor.feed(html)

    if len(extractor.blocks) >= 5:
        return extractor.blocks

    return [line for line in _html_to_text(html).splitlines() if line.strip()]


def _html_to_text(html: str) -> str:
    """Return a rough text version of an HTML document."""
    text = re.sub(r"(?is)<script.*?</script>", "\n", html)
    text = re.sub(r"(?is)<style.*?</style>", "\n", text)
    text = re.sub(r"(?i)</?(h[1-6]|p|li|br|div|section|article|main)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return "\n".join(_clean_text(line) for line in unescape(text).splitlines() if _clean_text(line))


def _clean_text(text: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _split_closure_rows(block: str) -> list[str]:
    """Split a closure block that contains several date rows.

    The official page usually exposes one date row per visual line, but some
    HTML variants can collapse several rows into one text block when parsed.
    This keeps parsing robust without requiring a full browser/DOM dependency.
    """
    cleaned = _clean_text(block)
    matches = list(DATE_START_RE.finditer(cleaned))
    if len(matches) <= 1:
        return [cleaned]

    rows: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        row = cleaned[start:end].strip()
        if row:
            rows.append(row)
    return rows or [cleaned]


def _is_stop_heading(block: str) -> bool:
    """Return true when the school-year content has ended."""
    lowered = block.lower()
    return lowered.startswith("ledighetsansökan") or lowered.startswith("detta gäller")


def _section_from_block(block: str) -> str | None:
    """Map Swedish page headings to internal section identifiers."""
    lowered = block.lower()
    if lowered == "skolstart":
        return "term_start"
    if lowered in {"skolavslutning", "terminsslut"}:
        return "term_end"
    if lowered == "lov och lediga dagar":
        return "closures"
    if lowered.startswith("ladda ner"):
        return "download"
    return None


def _replace_term(
    terms: list[SchoolTerm], term: SchoolTerm, *, start: date | None = None, end: date | None = None
) -> SchoolTerm:
    """Replace a term in the terms list with an updated copy."""
    updated = SchoolTerm(
        name=term.name,
        term_type=term.term_type,
        year=term.year,
        start=start if start is not None else term.start,
        end=end if end is not None else term.end,
    )
    terms[terms.index(term)] = updated
    return updated


def _parse_source_updated(text: str) -> date | None:
    """Parse the page's 'Senast uppdaterad' date."""
    match = DATE_UPDATED_RE.search(text)
    if not match:
        return None
    return _parse_swedish_date_with_year(match.group(1))


def _parse_swedish_date_with_year(value: str) -> date | None:
    """Parse '4 juni 2026'."""
    match = re.match(r"^(\d{1,2})\s+([A-Za-zÅÄÖåäö]+)\s+(\d{4})$", value.strip())
    if not match:
        return None
    day = int(match.group(1))
    month = MONTHS.get(match.group(2).lower())
    year = int(match.group(3))
    if month is None:
        return None
    return date(year, month, day)


def _parse_date_range(value: str, default_year: int) -> tuple[date, date, int] | None:
    """Parse the date formats used on the Skellefteå page.

    Returns start date, inclusive end date, and the end position of the matched
    date text so that the remaining text can be used as the event name.
    """
    value = _clean_text(value).lower().replace("–", "-").replace("—", "-")

    # 30/3-2/4
    match = re.match(r"^(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\b", value)
    if match:
        start = date(default_year, int(match.group(2)), int(match.group(1)))
        end = date(default_year, int(match.group(4)), int(match.group(3)))
        return start, end, match.end()

    # 26-30/10
    match = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\b", value)
    if match:
        start = date(default_year, int(match.group(3)), int(match.group(1)))
        end = date(default_year, int(match.group(3)), int(match.group(2)))
        return start, end, match.end()

    # 2-6 mars
    match = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\s+([a-zåäö]+)\b", value)
    if match:
        month = MONTHS.get(match.group(3))
        if month is None:
            return None
        start = date(default_year, month, int(match.group(1)))
        end = date(default_year, month, int(match.group(2)))
        return start, end, match.end()

    # 12 januari
    match = re.match(r"^(\d{1,2})\s+([a-zåäö]+)\b", value)
    if match:
        month = MONTHS.get(match.group(2))
        if month is None:
            return None
        parsed = date(default_year, month, int(match.group(1)))
        return parsed, parsed, match.end()

    # 7/5
    match = re.match(r"^(\d{1,2})/(\d{1,2})\b", value)
    if match:
        parsed = date(default_year, int(match.group(2)), int(match.group(1)))
        return parsed, parsed, match.end()

    return None


def _extract_event_name(raw: str, match_end: int) -> str:
    """Extract a human-readable event name from a date row."""
    paren_match = re.search(r"\(([^)]*)\)", raw)
    if paren_match:
        return _normalize_event_name(paren_match.group(1))

    remainder = raw[match_end:].strip(" /()-")
    if remainder:
        return _normalize_event_name(remainder)

    return "Ledig dag"


def _normalize_event_name(name: str) -> str:
    """Normalize event display names."""
    cleaned = _clean_text(name.strip(" /()-"))
    if cleaned.lower() == "k-dag":
        return "K-dag"
    if cleaned.lower() == "lovdag":
        return "Lovdag"
    return cleaned[:1].upper() + cleaned[1:]


def _event_type_from_name(name: str) -> str:
    """Return a stable event type from a Swedish event name."""
    lowered = name.lower()
    if "k-dag" in lowered:
        return "k_day"
    if "påsklov" in lowered:
        return "easter_break"
    if "sportlov" in lowered:
        return "winter_sports_break"
    if "läslov" in lowered or "höstlov" in lowered:
        return "autumn_break"
    if "lovdag" in lowered:
        return "holiday"
    if "jullov" in lowered:
        return "christmas_break"
    if "sommarlov" in lowered:
        return "summer_break"
    if "lov" in lowered:
        return "break"
    return "closure"


def _build_event(
    *,
    name: str,
    event_type: str,
    start: date,
    end: date,
    school_closed: bool,
    term: str | None,
    raw: str,
    inferred: bool,
) -> SchoolEvent:
    """Create an event with a stable UID."""
    uid = _slugify(f"{event_type}-{start.isoformat()}-{end.isoformat()}-{name}")
    return SchoolEvent(
        uid=uid,
        name=name,
        event_type=event_type,
        start=start,
        end=end,
        school_closed=school_closed,
        term=term,
        raw=raw,
        inferred=inferred,
    )


def _infer_between_term_breaks(terms: list[SchoolTerm]) -> list[SchoolEvent]:
    """Infer long breaks between adjacent known terms."""
    complete_terms = sorted(
        (term for term in terms if term.start is not None and term.end is not None),
        key=lambda term: term.start or date.min,
    )
    inferred: list[SchoolEvent] = []

    for previous, next_term in zip(complete_terms, complete_terms[1:], strict=False):
        if previous.end is None or next_term.start is None:
            continue

        start = previous.end + timedelta(days=1)
        end = next_term.start - timedelta(days=1)
        if start > end:
            continue

        if previous.term_type == "spring" and next_term.term_type == "autumn":
            name = "Sommarlov"
            event_type = "summer_break"
        elif previous.term_type == "autumn" and next_term.term_type == "spring":
            name = "Jullov"
            event_type = "christmas_break"
        else:
            name = "Lov mellan terminer"
            event_type = "between_terms_break"

        inferred.append(
            _build_event(
                name=name,
                event_type=event_type,
                start=start,
                end=end,
                school_closed=True,
                term=None,
                raw=f"Inferred between {previous.name} and {next_term.name}",
                inferred=True,
            )
        )

    return inferred


def _slugify(value: str) -> str:
    """Return a simple stable identifier."""
    value = value.lower()
    replacements = {"å": "a", "ä": "a", "ö": "o"}
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_") or "event"
