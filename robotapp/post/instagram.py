"""Instagram: one Reel, from the phone's own app (PLAN section 6.5).

The order is the plan's: open the app and check the account, + -> REEL -> the newest video (with a
length check) -> Next -> the caption -> Share. The journal is written *before* the Share tap; after
it nothing is ever pressed twice - a problem becomes "unsure" and the robot looks for the post.

Honest note: these signatures follow the plan's description of Instagram's screens. No Instagram
account exists on the robot phone yet, so they have not been checked against the real app; the
first real Instagram account provides the fixtures (tests/test_fixtures.py then guards them).
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path

from ..adb import Phone
from ..engage import engage
from ..journal import FAILED, POSTED, PRESSED, UNSURE, Journal
from ..ui import Element, Screen, ScreenTimeout, Signature, find, find_exact, wait_for
from ..window import WIB
from .base import PostResult, PostSpec

log = logging.getLogger("robotapp")

INSTAGRAM = "com.instagram.android"

# The feed's own tabs mark the feed; "Search" is on the nav bar of every screen (the scripted test
# caught the flow believing it was home while still on the profile).
HOME = Signature("instagram home", any_of=("For you", "Following"))
LOGIN = Signature("instagram login", any_of=("Log in", "Log in with Facebook", "Sign up"))
PROFILE = Signature("instagram profile", any_of=("Edit profile", "Followers", "Following", "Posts"))
REEL_CAMERA = Signature("instagram reel camera", any_of=("REEL", "POST", "Preview", "Gallery"))
GALLERY = Signature("instagram gallery", any_of=("Select", "Gallery", "Recents", "Next"))
EDITOR = Signature("instagram editor", any_of=("Next", "Edit", "Trim", "Audio"))
CAPTION = Signature("instagram caption", any_of=("Write a caption", "Add caption", "Caption", "Share"))
SHARED = Signature("instagram shared", any_of=("Your reel has been shared", "Reel shared", "shared", "Done"))
SHARE_SHEET = Signature("instagram share sheet", any_of=("Copy link", "Share to", "Copy", "Links"))
_EDITOR_OR_CAPTION = Signature("instagram editor or caption", any_of=("Next", "Edit", "Write a caption", "Share"))


class InstagramPoster:
    def __init__(
        self,
        phone: Phone,
        screen: Screen,
        journal: Journal,
        job_id: str,
        package: str = INSTAGRAM,
        user: int = 0,
        emit=None,
        shots_dir: Path | None = None,
    ) -> None:
        self.phone = phone
        self.screen = screen
        self.journal = journal
        self.job_id = job_id
        self.package = package
        self.user = user
        self.emit = emit or (lambda event: None)
        self.shots_dir = shots_dir
        self.handle: str | None = None
        self.sound_added = False

    # -- the whole post ----------------------------------------------------------------------------
    def post(self, spec: PostSpec, dry_run: bool = False) -> PostResult:
        result = PostResult(spec.upload_id, spec.platform, FAILED)
        try:
            self._step(1, "open app")
            self._open()
            self._step(2, "check account")
            self.handle = self._handle()
            result.handle = self.handle
            self._step(3, "create")
            self._open_reel_camera()
            wait_for(self.screen, REEL_CAMERA, 30)
            self._step(4, "pick video")
            self._open_gallery()
            wait_for(self.screen, GALLERY, 30)
            self._pick_video(spec)
            self._step(5, "editor")
            self._add_sound_if_asked(spec)
            # Some builds show an editor with a Next button; others land on the caption screen at once.
            elements = wait_for(self.screen, _EDITOR_OR_CAPTION, 60)
            if find_exact(elements, "Next") is not None:
                self._tap_exact("Next")
                wait_for(self.screen, CAPTION, 60)
            self._step(6, "caption")
            self._write_caption(spec)
        except Exception as exc:  # noqa: BLE001 - anything here is before the press
            result.reason = str(exc)
            self._shot("instagram-before-share")
            self.journal.mark(self.job_id, FAILED, spec.upload_id, spec.platform, {"reason": result.reason})
            log.warning("instagram: failed before Share: %s", exc)
            return result

        if dry_run:
            self._shot("instagram-dry-run")
            result.outcome = "dry_run"
            result.reason = "stopped before Share on purpose"
            log.info("instagram: dry run reached the caption screen; nothing was pressed")
            return result

        # From here on, never press Share twice.
        self._step(7, "press share")
        if not self.journal.mark(self.job_id, PRESSED, spec.upload_id, spec.platform):
            result.outcome = UNSURE
            result.reason = "Share was already pressed for this upload; not pressing again"
            log.warning("instagram: %s", result.reason)
            return result
        try:
            self._tap_exact("Share")
        except Exception as exc:  # noqa: BLE001
            result.outcome = UNSURE
            result.reason = f"could not confirm the Share tap: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("instagram-share-tap")
            return result

        try:
            self._step(8, "wait for shared")
            self._wait_shared()
            result.outcome = POSTED
        except Exception as exc:  # noqa: BLE001 - the post may well be out; look, don't repeat
            result.outcome = UNSURE
            result.reason = f"share pressed, not confirmed: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("instagram-shared")
            return result

        self._step(9, "read link")
        try:
            result.url = self._read_link()
        except Exception as exc:  # noqa: BLE001 - the post is out; the link can be asked for
            result.reason = f"posted, link not readable: {exc}"
            log.warning("instagram: %s", result.reason)
        result.sound = "trending" if self.sound_added else None
        self.journal.mark(self.job_id, POSTED, spec.upload_id, spec.platform, {"url": result.url})
        if not result.url:
            result.outcome = UNSURE
            result.reason = result.reason or "posted, link not readable"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})

        self._step(10, "engage")
        try:
            self._back_to_feed()
            result.engaged_s = engage(self.phone)
        except Exception as exc:  # noqa: BLE001 - engagement errors are ignored
            log.warning("instagram: engagement stopped early: %s", exc)
        return result

    # -- steps -------------------------------------------------------------------------------------
    def _add_sound_if_asked(self, spec: PostSpec) -> None:
        """Section 6.6: trending audio from the editor; if it fails, post without it."""
        if spec.sound != "trending":
            return
        from .. import sound

        added = sound.add_sound(self.screen, "instagram")
        self.sound_added = added
        if added:
            log.info("instagram: trending audio added")
            return
        if spec.sound_required:
            raise RuntimeError("trending audio is required but could not be added")
        log.warning("instagram: no audio could be added; posting without it")

    def _open(self) -> None:
        self.phone.force_stop(self.package, self.user)
        time.sleep(1.0)
        self.phone.start_app(self.package, self.user)
        time.sleep(6.0)
        deadline = time.monotonic() + 60
        stable = 0
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if LOGIN.matches(elements):
                raise RuntimeError("Instagram is logged out (a login must run before posting)")
            if HOME.matches(elements) and self._in_front():
                stable += 1
                if stable >= 2:
                    self._dismiss_popups(elements)
                    return
            else:
                stable = 0
                self._clear_dialog(elements)
            time.sleep(1.5)
        self._shot("instagram-open")
        raise ScreenTimeout("Instagram did not reach its home screen in 60 s")

    def _in_front(self) -> bool:
        try:
            package, _ = self.phone.fore_app()
        except Exception:  # noqa: BLE001
            return True
        if not package:
            return True
        return package == self.package

    def _clear_dialog(self, elements: list[Element]) -> bool:
        for label in ("Not now", "Skip", "Later", "Cancel", "Don't allow", "Dismiss"):
            button = find_exact(elements, label)
            if button is not None:
                self.screen.tap(button)
                time.sleep(1.0)
                return True
        return False

    def _dismiss_popups(self, elements: list[Element]) -> None:
        self._clear_dialog(elements)

    def _handle(self) -> str | None:
        """The @handle on the profile tab, so a wrong account is caught before anything is posted.

        Returns to the feed afterwards: the create button is on the feed's bottom bar, and a profile
        page also has tabs that match 'Reel' (the bug the scripted test caught).
        """
        try:
            if not self._tap_nav("Profile"):
                return None
            elements = wait_for(self.screen, PROFILE, 20)
        except ScreenTimeout:
            return None
        handle = next((e.text.strip() for e in elements if e.text.startswith("@")), None)
        self._back_to_feed()
        return handle

    def _tap_nav(self, label: str) -> bool:
        """Tap a bottom-bar item by its exact label (the bottom bar only, like TikTok's)."""
        width, height = self.screen.size()
        for element in self.screen.elements():
            if element.enabled and element.says(label) and element.bounds[1] >= height * 0.85:
                self.screen.tap(element)
                return True
        return False

    def _open_reel_camera(self) -> None:
        """Home first (a profile's own Reels tab also matches 'Reel'), then + and its REEL tab."""
        for _ in range(4):
            if HOME.matches(self.screen.elements()):
                break
            self.screen.press_back()
            time.sleep(1.0)
        width, height = self.screen.size()
        for element in self.screen.elements():
            if element.enabled and (element.says("Create") or element.desc.strip() == "Create a new post"
                                    or element.text.strip() == "+") and element.bounds[1] >= height * 0.85:
                self.screen.tap(element)
                time.sleep(2.0)
                reel = find_exact(self.screen.elements(), "REEL") or find(self.screen.elements(), "Reel")
                if reel is not None:
                    self.screen.tap(reel)
                    return
        raise RuntimeError("the create (+) button is not on the bottom bar")

    def _open_gallery(self) -> None:
        """The gallery button sits at the bottom left of the camera."""
        elements = self.screen.elements()
        for label in ("Gallery", "Recents", "All photos"):
            button = find_exact(elements, label) or find(elements, label)
            if button is not None:
                self.screen.tap(button)
                return
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.10), int(height * 0.72))

    def _pick_video(self, spec: PostSpec) -> None:
        elements = self.screen.elements()
        self._assert_length(elements, spec)
        # A tile, not a button: the gallery's "Select" is small and clickable too, a tile is big.
        width, height = self.screen.size()
        big = [e for e in elements if e.clickable and e.area >= (width * height) * 0.02 and e.bounds[1] > height * 0.1]
        if big:
            tile = min(big, key=lambda e: (e.bounds[1], e.bounds[0]))   # top-left is the newest
            self.screen.tap(tile)
        else:
            self.phone.tap(int(width * 0.17), int(height * 0.34))
        time.sleep(2.5)

    def _assert_length(self, elements: list[Element], spec: PostSpec) -> None:
        """The tile shows the clip's length; a different one means the wrong video."""
        if not spec.length_s:
            return
        for element in elements:
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", element.text.strip())
            if m:
                shown = int(m.group(1)) * 60 + int(m.group(2))
                if abs(shown - spec.length_s) > 2:
                    raise RuntimeError(f"the gallery shows a {shown}s video, the clip is {spec.length_s:.0f}s")
                return

    def _write_caption(self, spec: PostSpec) -> None:
        """Instagram links pasted hashtags (the plan's note), so the whole caption goes in one paste."""
        elements = self.screen.elements()
        field = (find(elements, "Write a caption") or find(elements, "Add caption")
                 or find(elements, "Caption"))
        if field is None:
            raise RuntimeError("the caption field is not on the share screen")
        self.screen.tap(field)
        time.sleep(0.8)
        wanted = spec.full_caption
        for attempt in (0, 1):
            try:
                self.screen.clear_field()
            except Exception:  # noqa: BLE001 - an empty field may refuse a clear
                pass
            self.screen.set_text(wanted)
            time.sleep(1.0)
            # Read it back: a half-written caption must not post. The field reports its tail while the
            # keyboard is up; the screen text is the fallback.
            flat_wanted = wanted.replace("\n", "").replace("\r", "").lower()
            head, tail = flat_wanted[:20], flat_wanted[-20:]
            actual = (self.screen.focused_text() or "").strip()
            page = " ".join(e.text for e in self.screen.elements()).replace("\n", "").lower()
            if (actual and (head in actual.lower() or tail in actual.lower())) \
                    or head in page or tail in page:
                return
            log.warning("instagram: the caption did not stick (attempt %d): %r", attempt + 1, actual[:60])
        self._shot("instagram-caption")
        raise RuntimeError("the caption could not be written into the share screen")

    def _wait_shared(self) -> None:
        """'Your reel has been shared', up to 5 minutes."""
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if SHARED.matches(elements) or HOME.matches(elements) or PROFILE.matches(elements):
                return
            time.sleep(2.0)
        raise RuntimeError("the share did not finish")

    def _read_link(self) -> str | None:
        """Profile -> Reels -> the newest -> ... -> Copy link, then read the clipboard."""
        if not self._tap_nav("Profile"):
            self._tap_desc("Profile")
        wait_for(self.screen, PROFILE, 20)
        time.sleep(1.5)
        reels = find(self.screen.elements(), "Reels")
        if reels is not None:
            self.screen.tap(reels)
            time.sleep(2.0)
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.16), int(height * 0.45))   # the newest Reel tile
        time.sleep(3.5)
        menu = find_exact(self.screen.elements(), "...") or find(self.screen.elements(), "More options")
        if menu is None:
            raise RuntimeError("the Reel's menu (...) is not on screen")
        self.screen.tap(menu)
        wait_for(self.screen, SHARE_SHEET, 20)
        link = find_exact(self.screen.elements(), "Copy link") or find(self.screen.elements(), "Copy link")
        if link is None:
            raise RuntimeError("'Copy link' is not in the share sheet")
        self.screen.tap(link)
        time.sleep(1.5)
        return self._clipboard()

    def _back_to_feed(self) -> None:
        for _ in range(4):
            if HOME.matches(self.screen.elements()):
                return
            self.screen.press_back()
            time.sleep(1.0)

    # -- small helpers -----------------------------------------------------------------------------
    def _tap_desc(self, desc: str, timeout_s: float = 20.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            button = find(self.screen.elements(), desc)
            if button is not None:
                self.screen.tap(button)
                return
            time.sleep(1.0)
        raise RuntimeError(f"'{desc}' is not on screen")

    def _tap_exact(self, label: str, timeout_s: float = 20.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            button = find_exact(self.screen.elements(), label)
            if button is not None:
                self.screen.tap(button)
                return
            time.sleep(1.0)
        raise RuntimeError(f"the '{label}' button is not on screen")

    def _clipboard(self) -> str | None:
        value = self.screen.clipboard()
        if value and "https://" in value and "instagram.com" in value:
            return value.strip()
        return None

    def _shot(self, name: str) -> None:
        if not self.shots_dir:
            return
        try:
            self.screen.screenshot(self.shots_dir / f"{name}-{datetime.now(WIB):%H%M%S}.png")
        except Exception:  # noqa: BLE001
            pass

    def _step(self, n: int, name: str) -> None:
        self.emit({"t": "step", "job": self.job_id, "n": n, "of": 10, "name": name})
        log.info("instagram step %d/10: %s", n, name)
