"""`robot doctor` against the fake phone: the facts it reads, and the problems it names (PLAN §8.2)."""

from datetime import datetime

from robotapp.doctor import SPACE_APPS, check, format_report
from robotapp.fake import FakePhone, fake_guard
from robotapp.window import WIB


def phone() -> FakePhone:
    p = FakePhone(guard=fake_guard())
    p.expect(r"getprop ro.product.model", "Infinix X6815D")
    p.expect(r"getprop ro.build.version.release", "13")
    p.expect(r"getprop ro.build.version.sdk", "33")
    p.expect(r"getprop gsm.sim.state", "ABSENT,ABSENT")
    return p


def test_report_reads_the_phone() -> None:
    report = check(phone(), apps=SPACE_APPS, moment=datetime(2026, 11, 18, 9, 0, tzinfo=WIB))
    assert report.online is True
    assert report.model == "Infinix X6815D"
    assert report.android == "13"
    assert report.sdk == "33"
    assert report.battery is not None and report.battery.level == 85
    assert report.battery.temperature_c == 40.5
    assert report.max_users == 4
    assert len(report.users) == 3
    assert report.free_spaces == 1
    assert report.apps["com.zhiliaoapp.musically"] == "39.5.4"
    assert report.problems == []
    assert report.ok is True


def test_low_battery_and_heat_are_problems() -> None:
    p = phone()
    p.battery_level = 20
    p.battery_temp = 430
    report = check(p, moment=datetime(2026, 11, 18, 9, 0, tzinfo=WIB))
    assert any("battery" in problem for problem in report.problems)
    assert report.ok is False


def test_outside_the_window_is_a_problem() -> None:
    report = check(phone(), moment=datetime(2026, 11, 18, 3, 0, tzinfo=WIB))
    assert any("work window" in problem for problem in report.problems)


def test_no_free_slot_is_a_problem() -> None:
    p = phone()
    p.user_rows.append("\tUserInfo{11:US 1:10} ")
    report = check(p, moment=datetime(2026, 11, 18, 9, 0, tzinfo=WIB))
    assert report.free_spaces == 0
    assert any("free user slot" in problem for problem in report.problems)


def test_report_is_printable() -> None:
    text = format_report(check(phone(), moment=datetime(2026, 11, 18, 9, 0, tzinfo=WIB)))
    assert "Infinix X6815D" in text
    assert "users      3 of 4" in text
    assert "all checks passed" in text
