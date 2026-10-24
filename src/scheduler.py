"""Pure reminder scheduling. No GTK imports — this module is what CI tests."""

import calendar
import uuid
from datetime import datetime, timedelta


REPEAT_CHOICES = (
    ("none", "None"),
    ("daily", "Daily"),
    ("weekdays", "Weekdays"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("yearly", "Yearly"),
)
REPEAT_KEYS = {key for key, _label in REPEAT_CHOICES}
_ANCHORED = {"monthly", "yearly"}
# Enough steps to walk a daily reminder across two decades without spinning forever.
_MAX_STEPS = 366 * 20


def parse_datetime(value):
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value)
    except ValueError:
        return None
    # Aware values can't be compared with the local clock and would stall the tick.
    if when.tzinfo is not None:
        return None
    return when


def repeat_label(repeat):
    for key, label in REPEAT_CHOICES:
        if key == repeat:
            return label
    return "None"


def normalize_scheduled(when, repeat):
    """Weekday repeats never land on Saturday or Sunday."""
    if repeat == "weekdays" and when.weekday() >= 5:
        return when + timedelta(days=(7 - when.weekday()))
    return when


def make_reminder(*, title, message, when, repeat, reminder_id=None, enabled=True):
    repeat = repeat if repeat in REPEAT_KEYS else "none"
    anchor_day = when.day
    when = normalize_scheduled(when, repeat)
    reminder = {
        "id": reminder_id or str(uuid.uuid4()),
        "title": title.strip(),
        "message": message.strip(),
        "datetime": when.isoformat(),
        "repeat": repeat,
        "enabled": bool(enabled),
    }
    if repeat in _ANCHORED:
        reminder["anchor_day"] = anchor_day
    return reminder


def advance(when, repeat, anchor_day=None):
    """Return the occurrence after `when`. Unknown repeats stay put."""
    day = anchor_day or when.day
    if repeat == "daily":
        return when + timedelta(days=1)
    if repeat == "weekdays":
        nxt = when + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt
    if repeat == "weekly":
        return when + timedelta(weeks=1)
    if repeat == "monthly":
        return _add_months(when, 1, day)
    if repeat == "yearly":
        return _add_years(when, 1, day)
    return when


def describe_when(when, now):
    """Short label for a row: 'In 12 min', 'Today · 15:30', 'Overdue'."""
    if when <= now:
        return "Overdue"
    seconds = (when - now).total_seconds()
    if seconds < 60:
        return "Now"
    if seconds < 3600:
        minutes = int(seconds // 60)
        unit = "min" if minutes == 1 else "mins"
        return f"In {minutes} {unit}"
    if when.date() == now.date():
        return f"Today · {when.strftime('%H:%M')}"
    if when.date() == now.date() + timedelta(days=1):
        return f"Tomorrow · {when.strftime('%H:%M')}"
    if seconds < 7 * 86400:
        return when.strftime("%a · %H:%M")
    return when.strftime("%b %d, %Y · %H:%M")


def due_state(reminder, now, soon_minutes=60):
    if not reminder.get("enabled", True):
        return "disabled"
    when = parse_datetime(reminder.get("datetime"))
    if when is None:
        return "invalid"
    if when <= now:
        return "overdue"
    if (when - now).total_seconds() <= soon_minutes * 60:
        return "soon"
    return "later"


def process_reminders(reminders, now, *, check_interval, missed_hours):
    """Advance due reminders in place.

    Returns `(fired, changed)`. One-shot reminders are disabled after they
    fire. Repeating ones jump to the next future occurrence, so a daily
    reminder missed for several days does not stay stuck in the past.
    A reminder notifies when its latest occurrence is still inside the missed
    window (also covers waking from sleep). Older one-shots stay overdue
    without ringing again. Older repeats skip ahead quietly.
    """
    fired = []
    changed = False
    fire_within = max(check_interval + 5, missed_hours * 3600)

    for reminder in reminders:
        if not isinstance(reminder, dict) or not reminder.get("enabled", True):
            continue
        when = parse_datetime(reminder.get("datetime"))
        if when is None or when > now:
            continue

        repeat = reminder.get("repeat", "none")
        if repeat not in REPEAT_KEYS:
            repeat = "none"

        if repeat == "none":
            age = (now - when).total_seconds()
            if age < fire_within:
                reminder["enabled"] = False
                changed = True
                fired.append(reminder)
            continue

        anchor = _anchor_day(reminder, when)
        if reminder.get("anchor_day") != anchor and repeat in _ANCHORED:
            reminder["anchor_day"] = anchor
            changed = True

        last_due, upcoming = _walk(when, repeat, now, anchor)
        if upcoming != when:
            reminder["datetime"] = upcoming.isoformat()
            changed = True
        age = (now - last_due).total_seconds()
        if age < fire_within:
            fired.append(reminder)

    return fired, changed


def _anchor_day(reminder, when):
    for key in ("anchor_day", "month_day"):
        value = reminder.get(key)
        if isinstance(value, int) and 1 <= value <= 31:
            return value
    return when.day


def _walk(when, repeat, now, anchor_day):
    """Return `(last occurrence <= now, next occurrence > now)`."""
    last = when
    for _ in range(_MAX_STEPS):
        nxt = advance(last, repeat, anchor_day)
        if nxt <= last:
            return last, last
        if nxt > now:
            return last, nxt
        last = nxt
    nxt = advance(last, repeat, anchor_day)
    return last, nxt if nxt > last else last


def _add_months(when, months, day):
    index = when.month - 1 + months
    year = when.year + index // 12
    month = index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return when.replace(year=year, month=month, day=min(day, last_day))


def _add_years(when, years, day):
    year = when.year + years
    last_day = calendar.monthrange(year, when.month)[1]
    return when.replace(year=year, day=min(day, last_day))
