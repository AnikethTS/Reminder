from datetime import datetime, timedelta

import pytest

from scheduler import (
    advance,
    describe_when,
    due_state,
    make_reminder,
    normalize_scheduled,
    parse_datetime,
    process_reminders,
)


NOW = datetime(2026, 3, 10, 15, 0, 0)
KW = {"check_interval": 30, "missed_hours": 24}


def _reminder(**overrides):
    base = {
        "id": "r1",
        "title": "Standup",
        "message": "",
        "datetime": datetime(2026, 3, 10, 15, 0, 0).isoformat(),
        "repeat": "none",
        "enabled": True,
    }
    base.update(overrides)
    return base


def test_make_reminder_strips_text_and_keeps_enabled_state():
    made = make_reminder(
        title="  Pay rent  ",
        message="  bank  ",
        when=datetime(2026, 4, 1, 9, 30),
        repeat="monthly",
        reminder_id="abc",
        enabled=False,
    )
    assert made["id"] == "abc"
    assert made["title"] == "Pay rent"
    assert made["message"] == "bank"
    assert made["enabled"] is False
    assert made["anchor_day"] == 1
    assert made["repeat"] == "monthly"


def test_weekdays_scheduled_on_saturday_move_to_monday():
    saturday = datetime(2026, 10, 24, 9, 0)
    assert saturday.weekday() == 5
    moved = normalize_scheduled(saturday, "weekdays")
    assert moved == datetime(2026, 10, 26, 9, 0)
    assert moved.weekday() == 0


@pytest.mark.parametrize("repeat", ["daily", "weekdays", "weekly", "monthly", "yearly"])
@pytest.mark.parametrize(
    "when",
    [
        datetime(2024, 2, 29, 8, 15),
        datetime(2025, 1, 31, 23, 59),
        datetime(2025, 12, 31, 0, 0),
        datetime(2026, 2, 28, 12, 0),
        datetime(2026, 3, 6, 9, 0),   # Friday
        datetime(2026, 3, 7, 9, 0),   # Saturday
    ],
)
def test_advance_always_moves_forward(repeat, when):
    nxt = advance(when, repeat, when.day)
    assert nxt > when


def test_monthly_anchor_survives_a_short_month():
    january = datetime(2026, 1, 31, 9, 0)
    february = advance(january, "monthly", 31)
    march = advance(february, "monthly", 31)
    assert february == datetime(2026, 2, 28, 9, 0)
    assert march == datetime(2026, 3, 31, 9, 0)


def test_yearly_leap_day_clamps_then_returns_on_the_next_leap_year():
    leap = datetime(2024, 2, 29, 7, 0)
    clamped = advance(leap, "yearly", 29)
    assert clamped == datetime(2025, 2, 28, 7, 0)
    restored = advance(datetime(2027, 2, 28, 7, 0), "yearly", 29)
    assert restored == datetime(2028, 2, 29, 7, 0)


def test_one_shot_due_now_fires_once_and_disables():
    reminders = [_reminder()]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert changed is True
    assert fired == reminders
    assert reminders[0]["enabled"] is False

    fired_again, changed_again = process_reminders(reminders, NOW, **KW)
    assert fired_again == []
    assert changed_again is False


def test_one_shot_outside_the_missed_window_stays_quiet():
    reminders = [_reminder(datetime=(NOW - timedelta(hours=30)).isoformat())]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert fired == []
    assert changed is False
    assert reminders[0]["enabled"] is True


def test_missed_one_shot_inside_the_window_fires():
    reminders = [_reminder(datetime=(NOW - timedelta(hours=3)).isoformat())]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert len(fired) == 1
    assert changed is True
    assert reminders[0]["enabled"] is False


def test_stuck_daily_reminder_catches_up_without_a_stale_alarm():
    # 9:00 each day, last stored three days ago. It is now 15:00, so today's
    # 9:00 is inside the missed window and tomorrow is the next slot.
    reminders = [_reminder(
        datetime=datetime(2026, 3, 7, 9, 0).isoformat(),
        repeat="daily",
    )]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert changed is True
    assert len(fired) == 1
    assert reminders[0]["datetime"] == datetime(2026, 3, 11, 9, 0).isoformat()
    assert reminders[0]["enabled"] is True


def test_old_weekly_occurrence_rolls_forward_without_firing():
    reminders = [_reminder(
        datetime=datetime(2026, 2, 1, 9, 0).isoformat(),
        repeat="weekly",
    )]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert fired == []
    assert changed is True
    nxt = datetime.fromisoformat(reminders[0]["datetime"])
    assert nxt > NOW
    assert nxt.weekday() == datetime(2026, 2, 1).weekday()


def test_january_31_monthly_does_not_crash_and_keeps_the_anchor():
    reminders = [_reminder(
        datetime=datetime(2026, 1, 31, 9, 0).isoformat(),
        repeat="monthly",
    )]
    fired, changed = process_reminders(reminders, datetime(2026, 4, 1, 12, 0), **KW)
    assert changed is True
    assert reminders[0]["anchor_day"] == 31
    assert reminders[0]["datetime"] == datetime(2026, 4, 30, 9, 0).isoformat()
    assert fired == []


def test_timezone_aware_values_are_ignored():
    aware = "2026-03-10T15:00:00+00:00"
    assert parse_datetime(aware) is None
    reminders = [_reminder(datetime=aware)]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert fired == []
    assert changed is False


def test_disabled_future_and_garbage_are_left_alone():
    reminders = [
        _reminder(id="off", enabled=False, datetime=(NOW - timedelta(minutes=1)).isoformat()),
        _reminder(id="later", datetime=(NOW + timedelta(hours=1)).isoformat()),
        _reminder(id="bad", datetime="not-a-date"),
        "nope",
    ]
    fired, changed = process_reminders(reminders, NOW, **KW)
    assert fired == []
    assert changed is False
    assert reminders[0]["enabled"] is False
    assert reminders[2]["datetime"] == "not-a-date"


def test_describe_when_and_due_state():
    assert describe_when(NOW - timedelta(minutes=1), NOW) == "Overdue"
    assert describe_when(NOW + timedelta(seconds=30), NOW) == "Now"
    assert describe_when(NOW + timedelta(minutes=1), NOW) == "In 1 min"
    assert describe_when(NOW + timedelta(minutes=12), NOW) == "In 12 mins"
    later_today = NOW.replace(hour=18, minute=5)
    assert describe_when(later_today, NOW) == "Today · 18:05"
    tomorrow = NOW + timedelta(days=1)
    assert describe_when(tomorrow, NOW) == f"Tomorrow · {tomorrow.strftime('%H:%M')}"
    next_week = NOW + timedelta(days=3)
    assert describe_when(next_week, NOW) == next_week.strftime("%a · %H:%M")
    far = NOW + timedelta(days=40)
    assert describe_when(far, NOW) == far.strftime("%b %d, %Y · %H:%M")

    soon = _reminder(datetime=(NOW + timedelta(minutes=20)).isoformat())
    late = _reminder(datetime=(NOW + timedelta(hours=5)).isoformat())
    overdue = _reminder(datetime=(NOW - timedelta(minutes=5)).isoformat())
    off = _reminder(enabled=False, datetime=(NOW - timedelta(minutes=5)).isoformat())
    assert due_state(soon, NOW) == "soon"
    assert due_state(late, NOW) == "later"
    assert due_state(overdue, NOW) == "overdue"
    assert due_state(off, NOW) == "disabled"
    assert due_state(_reminder(datetime="nope"), NOW) == "invalid"
