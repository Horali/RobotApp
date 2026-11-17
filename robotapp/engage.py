"""Watching, not liking (PLAN §6.3, §6.4 step 12).

The guide's rule: after posting, do not just post and close the app. The robot watches 3-5 minutes with uneven
swipes, likes nothing, follows nobody and comments nowhere. Plain `input swipe` is used, so uiautomator2 is not
attached while the feed scrolls.
"""

from __future__ import annotations

import random
import time
from datetime import datetime

from .adb import Phone
from .window import WIB, in_window


def engage(phone: Phone, minutes: tuple[float, float] = (3.0, 5.0), stop_at: datetime | None = None) -> float:
    """Scroll the current feed for a random time in `minutes`. Returns the seconds actually spent."""
    target = random.uniform(*minutes) * 60.0
    started = time.monotonic()
    width, height = _size(phone)
    while time.monotonic() - started < target:
        now = datetime.now(WIB)
        if not in_window(now) or (stop_at and now >= stop_at):
            break  # the window is a hard stop, engagement included (§7.2)
        # A video is watched for 60-100 % of its length, then an uneven swipe.
        time.sleep(random.uniform(6.0, 18.0))
        x = width // 2 + random.randint(-40, 40)
        phone.swipe(x, int(height * 0.78), x + random.randint(-30, 30), int(height * 0.22), random.randint(180, 420))
        time.sleep(random.uniform(0.8, 2.4))
    return time.monotonic() - started


def _size(phone: Phone) -> tuple[int, int]:
    """Screen size from `wm size` (1080x2400 on this phone). Falls back to a common size."""
    try:
        out = phone.shell("wm size")
        part = out.strip().split(":")[-1].strip()
        width, height = part.lower().split("x")
        return int(width), int(height)
    except Exception:  # noqa: BLE001
        return 1080, 2400
