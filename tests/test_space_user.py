"""Every flow opens its app in the brand's space, not the owner user (found live, 2026-11-19).

The TikTok login started musically in user 0 while user 11 was in front: the login timed out on
the space's screen and the owner user got a stray TikTok. The posters and the Instagram login had
the same blind spot - only the Google login passed its user through. This pins the fix: every
open, force-stop and share intent names the space's user.
"""

from pathlib import Path

import pytest

from robotapp.fake import FakePhone, FakeScreen, fake_guard
from robotapp.journal import Journal
from robotapp.login.instagram import InstagramLogin
from robotapp.login.tiktok import TikTokLogin
from robotapp.post.base import PostSpec
from robotapp.post.instagram import InstagramPoster
from robotapp.post.tiktok import TikTokPoster
from robotapp.post.youtube import YouTubePoster
from robotapp.ui import Element, ScreenTimeout


def el(text: str) -> Element:
    return Element(text=text, bounds=(0, 300, 400, 400), clickable=False)


class NoChameleon:
    """Answers the one call a login makes before the test stops it."""

    def login_identity(self, profile_id, platform):
        return ("somebody@example.com", "e1")

    def platform_password(self, profile_id, platform):
        from robotapp.log import Secret

        return Secret("pw-not-used")


def boom(*args, **kwargs):
    raise ScreenTimeout("stopped on purpose")


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)


def started_in(phone: FakePhone, package: str, user: int) -> bool:
    return any(
        f"--user {user}" in command and package in command
        for command in phone.commands
        if command.startswith(("am force-stop", "monkey", "am start"))
    )


def test_the_tiktok_login_opens_the_space_build(monkeypatch) -> None:
    from robotapp.login import tiktok as login_module

    phone = FakePhone(guard=fake_guard())
    monkeypatch.setattr(login_module, "wait_for", boom)
    login = TikTokLogin(phone, FakeScreen([el("For You")]), NoChameleon(), user=11)
    with pytest.raises(ScreenTimeout):
        login.login("profile-1", "somebody@example.com", "com.zhiliaoapp.musically")
    assert started_in(phone, "com.zhiliaoapp.musically", 11)


def test_the_instagram_login_opens_the_space_build(monkeypatch) -> None:
    from robotapp.login import instagram as login_module

    class Onboard:
        def matches(self, elements):
            return True

    phone = FakePhone(guard=fake_guard())
    monkeypatch.setattr(login_module, "wait_for", boom)
    monkeypatch.setattr(login_module, "ONBOARD", Onboard())
    login = InstagramLogin(phone, FakeScreen([]), NoChameleon(), user=11)
    with pytest.raises(ScreenTimeout):
        login.login("profile-1", "somebody@example.com", "com.instagram.android")
    assert started_in(phone, "com.instagram.android", 11)


@pytest.mark.parametrize(
    "poster_cls, package, home_word",
    [
        (TikTokPoster, "com.zhiliaoapp.musically", "For You"),
        (InstagramPoster, "com.instagram.android", "For you"),
        (YouTubePoster, "com.google.android.youtube", "Shorts"),
    ],
)
def test_a_poster_opens_the_space_build(tmp_path, poster_cls, package, home_word) -> None:
    phone = FakePhone(guard=fake_guard())
    screen = FakeScreen([el(home_word)])
    poster = poster_cls(phone, screen, Journal(tmp_path / "j.db"), "job-1", package=package, user=11)
    poster._open()
    assert started_in(phone, package, 11)


def test_the_tiktok_share_intent_names_the_space(monkeypatch, tmp_path) -> None:
    from robotapp.post import tiktok as poster_module

    phone = FakePhone(guard=fake_guard())
    monkeypatch.setattr(poster_module, "wait_for", boom)
    poster = TikTokPoster(
        phone, FakeScreen([]), Journal(tmp_path / "j.db"), "job-1",
        package="com.zhiliaoapp.musically", user=11,
    )
    spec = PostSpec(
        upload_id="u1", platform="tiktok", video=Path("x.mp4"),
        caption="", hashtags=[], media_uri="content://media/external/video/media/9",
    )
    assert poster._share_video(spec) is False
    assert any(
        command.startswith("am start --user 11") and "SystemShareActivity" in command
        for command in phone.commands
    )
