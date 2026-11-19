"""Reading a post's view count from the phone (PLAN section 6.8).

The 24-hour views come from the account's own profile: every phone app shows the play count on
each post's tile. The robot reads the newest tile's number in the brand's next morning sitting,
right before that app's new post, so the reading is about 23 h 50 min old - which ClipMaker counts
as the 24-hour one from 23 h 30 min on (the user's answer, 2026-11-18).

No taps that post anything: the profile is opened, the number is read, the profile is left.
"""

from __future__ import annotations

import logging
import re
import time

from .adb import Phone
from .post.tiktok import tiktok_package
from .ui import Element, Screen, Signature, wait_for

log = logging.getLogger("robotapp")

PROFILE = {
    "tiktok": Signature("tiktok profile", any_of=("Edit profile", "Followers", "Following")),
    "instagram": Signature("instagram profile", any_of=("Edit profile", "Followers", "Following", "Posts")),
}


def parse_count(text: str) -> int | None:
    """'1,234' -> 1234; '1.2K' -> 1200; '3.4M' -> 3400000; '▶ 812' -> 812; anything else -> None."""
    text = (text or "").strip().replace("\u00a0", " ").replace(",", "")
    text = re.sub(r"^[\u25b6\u25b7\u25ba\u25b8\u25b2\u25bc\s]+", "", text)   # the play triangle the tiles show
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KkMm]?)", text)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).upper()
    if unit == "K":
        value *= 1_000
    elif unit == "M":
        value *= 1_000_000
    return int(round(value))


def _numbers_on_tiles(elements: list[Element], screen_height: int) -> list[int]:
    """The play counts under the profile grid: numbers in the lower part of the screen, top-left first."""
    found: list[tuple[int, int, int]] = []
    for element in elements:
        text = (element.text or element.desc or "").strip()
        if not text:
            continue
        # A tile's counter is either "▶ 1,234" in one label or a bare number next to the icon.
        count = parse_count(text)
        if count is None:
            continue
        x1, y1, x2, y2 = element.bounds
        if y1 < screen_height * 0.30:      # the header's follower counts live up there
            continue
        found.append((y1, x1, count))
    found.sort()
    return [count for _, _, count in found]


def read_views(phone: Phone, screen: Screen, platform: str, user: int) -> int | None:
    """Open the app's own profile and read the newest post's play count. None when it cannot be read."""
    package = {
        "tiktok": tiktok_package(user),        # trill in the owner user, the US build in a space
        "instagram": "com.instagram.android",
    }.get(platform)
    if package is None:
        return None
    phone.start_app(package, user)
    time.sleep(6.0)
    height = screen.size()[1]
    # The profile tab: exact label, bottom bar only (a video's author is a trap here, as TikTok taught us).
    for element in screen.elements():
        if element.enabled and element.says("Profile") and element.bounds[1] >= height * 0.85:
            screen.tap(element)
            break
    signature = PROFILE.get(platform)
    if signature is None:
        return None
    try:
        wait_for(screen, signature, 25)
    except Exception:  # noqa: BLE001 - the profile did not open (logged out, an update): the caller asks
        return None
    time.sleep(1.5)
    counts = _numbers_on_tiles(screen.elements(), height)
    return counts[0] if counts else None
