"""Spaces: creating a user, putting the apps in, and never touching the owner (PLAN §3, §4.2, §4.8)."""

import pytest

from robotapp.fake import FakePhone, fake_guard
from robotapp.spaces import SPACE_PACKAGES, Spaces


def phone() -> FakePhone:
    return FakePhone(guard=fake_guard())


def test_free_slots_count_the_owner() -> None:
    spaces = Spaces(phone())
    assert spaces.free_slots() == 1  # 3 users on a phone that allows 4


def test_create_makes_a_user_and_installs_the_apps() -> None:
    p = phone()
    space = Spaces(p).create("US 1")
    assert space.user_id > 0
    assert any("US 1" in row for row in p.user_rows)
    commands = "\n".join(p.commands)
    assert "pm create-user" in commands
    assert f"settings --user {space.user_id} put secure user_setup_complete 1" in commands
    assert f"pm disable-user --user {space.user_id} com.google.android.setupwizard" in commands
    assert f"am start-user {space.user_id}" in commands
    for package in SPACE_PACKAGES:
        assert f"pm install-existing --user {space.user_id} {package}" in commands
    assert f"pm grant --user {space.user_id} com.zhiliaoapp.musically android.permission.READ_MEDIA_VIDEO" in commands
    # location and contacts are deliberately not granted (§4.2 step 6)
    assert "ACCESS_FINE_LOCATION" not in commands
    assert "READ_CONTACTS" not in commands


def test_the_owner_user_is_never_deleted_or_wiped() -> None:
    spaces = Spaces(phone())
    with pytest.raises(ValueError):
        spaces.delete(0)
    with pytest.raises(ValueError):
        spaces.wipe(0)


def test_wipe_stops_then_removes() -> None:
    p = phone()
    spaces = Spaces(p)
    spaces.wipe(10)
    assert "am stop-user -f 10" in p.commands
    assert "pm remove-user 10" in p.commands


def test_leave_owner_front_switches_to_user_zero() -> None:
    p = phone()
    p.current = 11
    Spaces(p).leave_owner_front()
    assert p.current == 0
