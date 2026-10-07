# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Minimal cron expression parser and matcher.

Supports the standard 5-field form::

    minute hour day-of-month month day-of-week

Each field accepts ``*``, lists (``1,15``), ranges (``9-17``), steps
(``*/15``, ``9-17/2``) and the usual numeric ranges:

- minute: 0-59
- hour: 0-23
- day of month: 1-31
- month: 1-12
- day of week: 0-6 (0 and 7 both mean Sunday)

Matching follows Vixie cron semantics: when both day-of-month and
day-of-week are restricted (neither is ``*``), a time matches if *either*
field matches; otherwise the restricted field must match.

This is deliberately dependency-free (no croniter) and fully unit-tested.
All times are naive UTC datetimes — the scheduler stores and compares
``next_run_at`` in UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_FIELD_RANGES = (
    (0, 59),  # minute
    (0, 23),  # hour
    (1, 31),  # day of month
    (1, 12),  # month
    (0, 7),  # day of week (7 normalized to 0)
)

_FIELD_NAMES = ("minute", "hour", "day of month", "month", "day of week")


class CronError(ValueError):
    """Raised when a cron expression cannot be parsed."""


def _parse_field(field: str, minimum: int, maximum: int, name: str) -> frozenset[int]:
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if not part:
            raise CronError(f"empty {name} field part in cron expression")
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            try:
                step = int(step_text)
            except ValueError:
                raise CronError(f"bad step {step_text!r} in {name} field") from None
            if step < 1:
                raise CronError(f"step must be >= 1 in {name} field")
        if part == "*" or part == "":
            start, end = minimum, maximum
        elif "-" in part:
            start_text, end_text = part.split("-", 1)
            try:
                start, end = int(start_text), int(end_text)
            except ValueError:
                raise CronError(f"bad range {part!r} in {name} field") from None
        else:
            try:
                start = end = int(part)
            except ValueError:
                raise CronError(f"bad value {part!r} in {name} field") from None
        if start < minimum or end > maximum or start > end:
            raise CronError(f"{name} value {part!r} out of range {minimum}-{maximum}")
        values.update(range(start, end + 1, step))
    return frozenset(values)


def parse_cron(expression: str) -> tuple[frozenset[int], ...]:
    """Parse a 5-field cron expression into sets of matching values.

    Raises :class:`CronError` on invalid input.
    """
    fields = expression.split()
    if len(fields) != 5:
        raise CronError(
            f"cron expression must have 5 fields, got {len(fields)}: {expression!r}"
        )
    parsed = []
    for field, (minimum, maximum), name in zip(
        fields, _FIELD_RANGES, _FIELD_NAMES, strict=True
    ):
        parsed.append(_parse_field(field, minimum, maximum, name))
    # Normalize day of week: 7 -> 0 (Sunday).
    dow = set(parsed[4])
    if 7 in dow:
        dow.discard(7)
        dow.add(0)
    parsed[4] = frozenset(dow)
    return tuple(parsed)  # type: ignore[return-value]


def matches(schedule: tuple[frozenset[int], ...], when: datetime) -> bool:
    """Return True if ``when`` matches the parsed cron schedule."""
    minute, hour, dom, month, dow = schedule
    if when.minute not in minute:
        return False
    if when.hour not in hour:
        return False
    if when.month not in month:
        return False
    dom_star = dom == frozenset(range(1, 32))
    dow_star = dow == frozenset(range(0, 7))
    dom_match = when.day in dom
    # Python: Monday=0..Sunday=6; cron: Sunday=0..Saturday=6.
    cron_dow = (when.weekday() + 1) % 7
    dow_match = cron_dow in dow
    if not dom_star and not dow_star:
        day_match = dom_match or dow_match
    elif not dom_star:
        day_match = dom_match
    elif not dow_star:
        day_match = dow_match
    else:
        day_match = True
    return day_match


def next_run(expression: str, after: datetime | None = None) -> datetime:
    """Compute the next datetime strictly after ``after`` matching the cron.

    Searches forward minute-by-minute up to ~366 days; raises
    :class:`CronError` if no match is found (e.g. February 30th).
    """
    schedule = parse_cron(expression)
    cursor = (after or datetime.now(UTC)).replace(
        second=0, microsecond=0, tzinfo=None
    ) + timedelta(minutes=1)
    limit = cursor + timedelta(days=366)
    while cursor <= limit:
        if matches(schedule, cursor):
            return cursor
        cursor += timedelta(minutes=1)
    raise CronError(f"no run time found within a year for {expression!r}")
