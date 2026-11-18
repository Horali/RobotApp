"""The 06:00-10:00 WIB rule and the shared phone lock (PLAN §7.2, §9).

The user's firm rule: the robot touches the phone only between 06:00 and 10:00 Asia/Jakarta. Outside that the
phone belongs to their other scripts, so the robot sends no commands at all — not even a read. Everything that
talks to the phone goes through `Phone`, and `Phone` asks `WindowGuard` first, so the rule cannot be forgotten
in one code path.

The lock is a small file on the laptop (`%LOCALAPPDATA%\\PhoneLock\\phone.lock`) shared with those other
scripts: whoever holds it may drive the phone. The robot takes it at 06:00 and gives it back by 10:00. A lock
whose `until` has passed, or whose holder is gone, is stale and may be taken over.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    WIB = ZoneInfo("Asia/Jakarta")
except ZoneInfoNotFoundError:  # Windows has no tz database: `pip install tzdata` fixes it, this keeps it running
    WIB = dt_timezone(timedelta(hours=7), "WIB")  # Indonesia has no daylight saving
WINDOW_START = dtime(6, 0)
WINDOW_END = dtime(10, 0)
NO_POST_AFTER = dtime(9, 55)

# Build mode: while the robot is being built there is no other script on the phone, so the user allowed it to be
# used at any hour (2026-11-18). Off unless this variable is set, and every use is logged loudly.
BUILD_MODE_ENV = "ROBOTAPP_BUILD_MODE"
_build_warned = False


def build_mode() -> bool:
    return os.environ.get(BUILD_MODE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _warn_build_mode(action: str, moment: datetime) -> None:
    """Once per process: using the phone outside the window must never be silent."""
    global _build_warned
    if _build_warned:
        return
    _build_warned = True
    import logging

    logging.getLogger("robotapp").warning(
        "BUILD MODE (%s=1): %s at %s, outside the 06:00-10:00 window (%s). "
        "Unset it before any other script shares this phone.",
        BUILD_MODE_ENV,
        action,
        moment.strftime("%H:%M"),
        describe(moment),
    )


class OutsideWindow(RuntimeError):
    """Raised instead of touching the phone outside 06:00-10:00 WIB."""


class LockHeld(RuntimeError):
    """Raised when another program (or another robot job) holds the phone lock."""


def now_wib() -> datetime:
    return datetime.now(WIB)


def window_bounds(day: date | None = None) -> tuple[datetime, datetime]:
    """Today's window as two aware datetimes (start included, end excluded)."""
    day = day or now_wib().date()
    return (
        datetime.combine(day, WINDOW_START, WIB),
        datetime.combine(day, WINDOW_END, WIB),
    )


def in_window(moment: datetime | None = None) -> bool:
    moment = moment or now_wib()
    start, end = window_bounds(moment.date())
    return start <= moment < end


def post_allowed(moment: datetime | None = None) -> bool:
    """A Post/Share/Upload is never pressed after 09:55 (§7.2), nor outside the window."""
    moment = moment or now_wib()
    start, _ = window_bounds(moment.date())
    return start <= moment < datetime.combine(moment.date(), NO_POST_AFTER, WIB)


def seconds_left(moment: datetime | None = None) -> float:
    moment = moment or now_wib()
    _, end = window_bounds(moment.date())
    return max(0.0, (end - moment).total_seconds())


def describe(moment: datetime | None = None) -> str:
    moment = moment or now_wib()
    if in_window(moment):
        return f"inside the window, {seconds_left(moment) / 60:.0f} min left"
    start, end = window_bounds(moment.date())
    if moment < start:
        return f"before the window (opens {start:%H:%M} WIB, in {(start - moment).total_seconds() / 60:.0f} min)"
    return f"after the window (closed {end:%H:%M} WIB)"


class WindowGuard:
    """The gate every phone command passes. `clock` is injectable so tests can move time.

    `allow_outside` overrides the window for a test; the build-mode switch is the environment variable, so a
    normal run can never be outside the window by accident.
    """

    def __init__(self, clock=now_wib, allow_outside: bool | None = None) -> None:
        self._clock = clock
        self._allow_outside = allow_outside

    def _outside_ok(self) -> bool:
        return self._allow_outside if self._allow_outside is not None else build_mode()

    def check(self, action: str = "touch the phone") -> None:
        moment = self._clock()
        if in_window(moment):
            return
        if self._outside_ok():
            _warn_build_mode(action, moment)
            return
        raise OutsideWindow(
            f"refusing to {action}: it is {moment:%H:%M} WIB, outside the 06:00-10:00 window "
            f"({describe(moment)}). The phone belongs to the other scripts until 06:00."
        )

    def check_post(self, action: str = "press Post") -> None:
        moment = self._clock()
        if post_allowed(moment):
            return
        if self._outside_ok():
            _warn_build_mode(action, moment)
            return
        raise OutsideWindow(
            f"refusing to {action} at {moment:%H:%M} WIB: no post after 09:55, and none outside 06:00-10:00."
        )


def default_lock_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "PhoneLock" / "phone.lock"


@dataclass
class LockInfo:
    holder: str
    pid: int
    since: str
    until: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # os.kill(pid, 0) would TERMINATE the process on Windows, so ask the kernel instead.
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class PhoneLock:
    """The laptop-wide lock file. `holder` is what other scripts see; `until` is when it goes stale."""

    def __init__(self, holder: str = "robotapp", path: Path | None = None) -> None:
        self.holder = holder
        self.path = path or default_lock_path()

    # -- reading -------------------------------------------------------------------------------------
    def read(self) -> LockInfo | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return LockInfo(str(raw["holder"]), int(raw["pid"]), str(raw["since"]), str(raw["until"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def is_stale(self, info: LockInfo | None) -> bool:
        if info is None:
            return True
        try:
            until = datetime.fromisoformat(info.until)
        except ValueError:
            return True
        if until.tzinfo is None:
            until = until.replace(tzinfo=WIB)
        return until <= now_wib() or (info.holder != self.holder and not _pid_alive(info.pid))

    # -- taking and giving back ----------------------------------------------------------------------
    def acquire(self, until: datetime | None = None, wait_s: float = 0.0) -> LockInfo:
        """Take the lock, waiting up to `wait_s` for another holder to finish. Raises LockHeld."""
        deadline = time.monotonic() + max(0.0, wait_s)
        while True:
            info = self._try_acquire(until)
            if info is not None:
                return info
            if time.monotonic() >= deadline:
                current = self.read()
                who = f"{current.holder} (pid {current.pid}, until {current.until})" if current else "another program"
                raise LockHeld(f"the phone is locked by {who}")
            time.sleep(0.5)

    def _try_acquire(self, until: datetime | None) -> LockInfo | None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # A lock taken after 10:00 must not be stale on the spot: allow at least half an hour from now.
        end = until or max(window_bounds()[1], now_wib() + timedelta(minutes=30))
        info = LockInfo(self.holder, os.getpid(), now_wib().isoformat(timespec="seconds"), end.isoformat(timespec="seconds"))
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            current = self.read()
            if not self.is_stale(current):
                return None
            # Stale: replace it in one step (write a temp file, then move it over the old one).
            tmp = self.path.parent / f"{self.path.name}.{os.getpid()}.tmp"
            tmp.write_text(info.to_json(), encoding="utf-8")
            os.replace(tmp, self.path)
            return info
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(info.to_json())
        return info

    def release(self) -> bool:
        """Give the lock back. Only the holder may release it; returns False when it was not ours."""
        current = self.read()
        if current is None:
            return False
        if current.holder != self.holder or current.pid != os.getpid():
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            return False
        return True

    def held_by_me(self) -> bool:
        current = self.read()
        return bool(current and current.holder == self.holder and current.pid == os.getpid())

    def __enter__(self) -> "PhoneLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def next_window_start(moment: datetime | None = None) -> datetime:
    """When the robot may next touch the phone (today's 06:00 if it has not passed, else tomorrow's)."""
    moment = moment or now_wib()
    start, _ = window_bounds(moment.date())
    return start if moment < start else start + timedelta(days=1)
