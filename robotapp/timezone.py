"""The phone's time zone, and the two rules that keep the flips invisible (PLAN §4.6).

The zone is phone-wide. The robot switches it to New York for the US sittings and back to Jakarta right after,
twice a day, both inside the window. Before switching to New York it force-stops G2G's apps in the owner user,
so they never see the jump: a force-stopped app gets no broadcasts and no push until it is opened again.
"""

from __future__ import annotations

from .adb import Phone

JAKARTA = "Asia/Jakarta"
NEW_YORK = "America/New_York"
# G2G's apps in the owner user: they must not see the time zone jump (§4.6 step 2).
G2G_APPS = ("com.ss.android.ugc.trill", "com.google.android.youtube")


def disable_auto_detection(phone: Phone) -> None:
    """One-time setup (§4.1 step 5): the zone must stay where the robot puts it."""
    for command in (
        "cmd time_zone_detector set_auto_detection_enabled false",
        "cmd time_zone_detector set_geo_detection_enabled false",
    ):
        try:
            phone.shell(command)
        except Exception:  # noqa: BLE001 - older builds have no such command; the zone still changes
            pass


def set_zone(phone: Phone, zone: str) -> str:
    """Set and verify. Returns the zone the phone reports afterwards."""
    phone.set_timezone(zone)
    actual = phone.timezone()
    if actual != zone:
        raise RuntimeError(f"the time zone did not change: asked for {zone}, phone says {actual}")
    return actual


def freeze_g2g(phone: Phone) -> None:
    for package in G2G_APPS:
        try:
            phone.force_stop(package, user=0)
        except Exception:  # noqa: BLE001 - an app that is not running is already fine
            pass


def to_us(phone: Phone) -> str:
    freeze_g2g(phone)
    return set_zone(phone, NEW_YORK)


def to_jakarta(phone: Phone) -> str:
    return set_zone(phone, JAKARTA)
