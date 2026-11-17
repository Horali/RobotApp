"""The shared phone lock (PLAN §9): one holder at a time, stale locks are taken over, only the holder releases."""

import json
import os
from datetime import datetime, timedelta

import pytest

from robotapp.window import WIB, LockHeld, PhoneLock


def lock_at(tmp_path, holder: str = "robotapp") -> PhoneLock:
    return PhoneLock(holder=holder, path=tmp_path / "phone.lock")


def test_take_and_release(tmp_path) -> None:
    lock = lock_at(tmp_path)
    assert lock.read() is None
    info = lock.acquire()
    assert info.holder == "robotapp"
    assert lock.held_by_me()
    assert lock.release() is True
    assert lock.read() is None


def test_a_second_holder_is_refused(tmp_path) -> None:
    first = lock_at(tmp_path, "robotapp")
    first.acquire()
    second = lock_at(tmp_path, "other-script")
    with pytest.raises(LockHeld) as caught:
        second.acquire(wait_s=0.1)
    assert "robotapp" in str(caught.value)


def test_only_the_holder_releases(tmp_path) -> None:
    holder = lock_at(tmp_path, "robotapp")
    holder.acquire()
    stranger = lock_at(tmp_path, "other-script")
    assert stranger.release() is False
    assert holder.read() is not None


def test_a_stale_lock_is_taken_over(tmp_path) -> None:
    path = tmp_path / "phone.lock"
    past = (datetime.now(WIB) - timedelta(minutes=5)).isoformat(timespec="seconds")
    path.write_text(
        json.dumps({"holder": "gone", "pid": os.getpid() + 999999, "since": past, "until": past}),
        encoding="utf-8",
    )
    info = lock_at(tmp_path).acquire()
    assert info.holder == "robotapp"


def test_a_live_holder_is_not_taken_over(tmp_path) -> None:
    path = tmp_path / "phone.lock"
    future = (datetime.now(WIB) + timedelta(hours=1)).isoformat(timespec="seconds")
    path.write_text(
        json.dumps({"holder": "busy", "pid": os.getpid(), "since": "2026-11-18T06:00:00", "until": future}),
        encoding="utf-8",
    )
    with pytest.raises(LockHeld):
        lock_at(tmp_path).acquire(wait_s=0.1)
