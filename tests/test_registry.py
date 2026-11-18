"""The lifecycle (PLAN sections 7.1, 7.3; step 9): brands wait for a space, graduate, release, reuse."""

from pathlib import Path

import pytest

from robotapp.registry import Registry


def registry(tmp_path: Path) -> Registry:
    return Registry(tmp_path / "robot.db")


def test_a_home_brand_is_ready_at_once_in_the_owner_user(tmp_path) -> None:
    """G2G: no proxy, owner user, always ready, never wiped."""
    reg = registry(tmp_path)
    brand = reg.add_brand("g2g", "G2GChannel Clips", {"home": "ID"})
    assert brand.state == "ready" and brand.space_user == 0 and brand.home is True
    assert reg.spaces()[0]["user_id"] == 0
    with pytest.raises(ValueError):
        reg.release("g2g")          # the owner user is never released
    reg.close()


def test_a_us_brand_waits_then_gets_a_space(tmp_path) -> None:
    reg = registry(tmp_path)
    brand = reg.add_brand("vtuber", "vtuber Clips", {"proxy": "7d8a1a48"})
    assert brand.state == "waiting" and brand.space_user is None
    assert reg.next_waiting().brand_id == "vtuber"
    reg.add_brand("later", "Later Clips", {"proxy": "x"})
    assert reg.next_waiting().brand_id == "vtuber"       # first come, first served

    reg.assign("vtuber", 11, "US 1")
    assert reg.brand("vtuber").state == "assigned"
    reg.mark_ready("vtuber")
    assert reg.brand("vtuber").state == "ready"
    assert {s["user_id"]: s["state"] for s in reg.spaces()}[11] == "ready"
    reg.close()


def test_free_slots_count_the_owner_and_the_spaces_in_use(tmp_path) -> None:
    reg = registry(tmp_path)
    reg.add_brand("g2g", "G2G", {"home": "ID"})            # owner user
    reg.add_brand("a", "A", {"proxy": "x"})
    reg.assign("a", 11, "US 1")
    # 4 users allowed, the owner is one, space 11 is one: two still free
    assert reg.free_slots(4) == 2
    reg.assign("a", 12, "US 2")
    reg.close()


def test_releasing_a_brand_frees_its_space_for_the_next_one(tmp_path) -> None:
    """Step 9's 'done when': a graduated brand frees its space alone."""
    reg = registry(tmp_path)
    reg.add_brand("a", "A", {"proxy": "x"})
    reg.assign("a", 11, "US 1")
    reg.mark_ready("a")
    user = reg.release("a")
    assert user == 11
    assert reg.brand("a").state == "released" and reg.brand("a").space_user is None
    assert {s["user_id"]: s["state"] for s in reg.spaces()}[11] == "wiping"
    reg.space_wiped(11)                                     # after pm remove-user
    assert not reg.spaces()
    assert reg.free_slots(4) == 3                            # owner + nothing else
    reg.close()


def test_a_released_brand_can_come_back_with_a_new_space(tmp_path) -> None:
    reg = registry(tmp_path)
    reg.add_brand("a", "A", {"proxy": "x"})
    reg.assign("a", 11, "US 1")
    reg.release("a")
    reg.space_wiped(11)
    reg.add_brand("b", "B", {"proxy": "y"})
    reg.assign("b", 11, "US 1")                              # the same slot, a new brand
    assert reg.brand("b").space_user == 11
    assert reg.brand("a").state == "released"
    reg.close()
