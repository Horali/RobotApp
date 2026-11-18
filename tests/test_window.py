"""The 06:00-10:00 rule (PLAN §7.2, §9). The clock is injected, so these tests never depend on the real time."""

from datetime import datetime

import pytest

from robotapp.window import (
    WIB,
    OutsideWindow,
    WindowGuard,
    describe,
    in_window,
    next_window_start,
    post_allowed,
    seconds_left,
)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 18, hour, minute, tzinfo=WIB)


@pytest.mark.parametrize(
    "moment, inside",
    [
        (at(5, 59), False),
        (at(6, 0), True),
        (at(9, 59), True),
        (at(10, 0), False),
        (at(23, 30), False),
    ],
)
def test_in_window(moment: datetime, inside: bool) -> None:
    assert in_window(moment) is inside


def test_no_post_after_0955() -> None:
    assert post_allowed(at(9, 54)) is True
    assert post_allowed(at(9, 55)) is False
    assert post_allowed(at(6, 0)) is True
    assert post_allowed(at(5, 59)) is False


def test_guard_refuses_outside_and_names_the_reason(monkeypatch) -> None:
    monkeypatch.delenv("ROBOTAPP_BUILD_MODE", raising=False)  # a test never inherits the shell
    guard = WindowGuard(clock=lambda: at(3, 0))
    with pytest.raises(OutsideWindow) as caught:
        guard.check("read the screen")
    assert "06:00-10:00" in str(caught.value)
    assert "06:00" in describe(at(3, 0))


def test_guard_allows_inside_and_post_cutoff(monkeypatch) -> None:
    monkeypatch.delenv("ROBOTAPP_BUILD_MODE", raising=False)
    WindowGuard(clock=lambda: at(7, 0)).check("read the screen")
    WindowGuard(clock=lambda: at(7, 0)).check_post("press Post")
    with pytest.raises(OutsideWindow):
        WindowGuard(clock=lambda: at(9, 56)).check_post("press Post")


def test_build_mode_lets_the_guard_pass_outside(monkeypatch) -> None:
    """ROBOTAPP_BUILD_MODE=1 is the user's build-time allowance: the phone may be used at 3 AM."""
    monkeypatch.setenv("ROBOTAPP_BUILD_MODE", "1")
    WindowGuard(clock=lambda: at(3, 0)).check("read the screen")
    WindowGuard(clock=lambda: at(3, 0)).check_post("press Post")
    monkeypatch.setenv("ROBOTAPP_BUILD_MODE", "0")
    with pytest.raises(OutsideWindow):
        WindowGuard(clock=lambda: at(3, 0)).check("read the screen")


def test_seconds_left_and_next_start() -> None:
    assert seconds_left(at(9, 0)) == 3600
    assert seconds_left(at(11, 0)) == 0
    assert next_window_start(at(3, 0)) == at(6, 0)
    assert next_window_start(at(11, 0)) == datetime(2026, 11, 19, 6, 0, tzinfo=WIB)
