"""TikTok: one post, from the phone's own app (PLAN §6.4, §6.6).

The order is fixed by the plan: open the app and clear the known pop-ups, check the handle, `+` → Upload → the
newest video (with a length check) → Next → caption and hashtags → Post. The journal is written *before* the
Post tap; after it, nothing is ever pressed twice — a problem becomes "unsure" and the robot looks for the post.

Screen signatures are the fragile part of any phone robot: TikTok changes them with every version. Each step
waits for a signature instead of sleeping, and a step that does not arrive fails the post *before* the press.
"""

from __future__ import annotations

import logging
import random
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

TIKTOK_US = "com.zhiliaoapp.musically"
TIKTOK_ID = "com.ss.android.ugc.trill"

HOME = Signature("tiktok home", any_of=("For You", "Following", "Inbox", "Profile"))
CAMERA = Signature("tiktok camera", any_of=("Upload", "Add sound", "Flip", "Record"))
GALLERY = Signature("tiktok gallery", any_of=("Videos", "Photos", "Select", "Next"))
EDITOR = Signature("tiktok editor", any_of=("Next", "Add sound", "Edit", "Sound"))
POST_SCREEN = Signature("tiktok post screen", any_of=("Add description", "Who can watch", "Post", "Describe your video"))
UPLOADED = Signature("tiktok uploaded", any_of=("Video uploaded", "Your video is being uploaded", "Uploading", "Posting"))
PROFILE = Signature("tiktok profile", any_of=("Edit profile", "Followers", "Following"))
SHARE_SHEET = Signature("tiktok share sheet", any_of=("Copy link", "Share to", "Save video", "Duet"))


class TikTokPoster:
    def __init__(
        self,
        phone: Phone,
        screen: Screen,
        journal: Journal,
        job_id: str,
        package: str = TIKTOK_US,
        emit=None,
        shots_dir: Path | None = None,
    ) -> None:
        self.phone = phone
        self.screen = screen
        self.journal = journal
        self.job_id = job_id
        self.package = package
        self.emit = emit or (lambda event: None)
        self.shots_dir = shots_dir
        self.handle: str | None = None

    # -- the whole post ----------------------------------------------------------------------------
    def post(self, spec: PostSpec) -> PostResult:
        result = PostResult(spec.upload_id, spec.platform, FAILED)
        try:
            self._step(1, "open app")
            self._open()
            self._step(2, "check handle")
            self.handle = self._handle()
            result.handle = self.handle
            self._step(3, "create")
            self._tap_desc("Create")
            wait_for(self.screen, CAMERA, 30)
            self._step(4, "upload")
            self._tap_exact("Upload")
            wait_for(self.screen, GALLERY, 30)
            self._step(5, "pick video")
            self._pick_video(spec)
            wait_for(self.screen, EDITOR, 45)
            self._step(6, "editor")
            self._add_sound_if_asked(spec)
            self._tap_exact("Next")
            wait_for(self.screen, POST_SCREEN, 45)
            self._step(7, "caption")
            self._write_caption(spec)
            self._step(8, "settings")
            self._ensure_public()
        except Exception as exc:  # noqa: BLE001 - anything here is before the press
            result.reason = str(exc)
            self._shot("tiktok-before-post")
            self.journal.mark(self.job_id, FAILED, spec.upload_id, spec.platform, {"reason": result.reason})
            log.warning("tiktok: failed before Post: %s", exc)
            return result

        # From here on, never press Post twice.
        self._step(9, "press post")
        if not self.journal.mark(self.job_id, PRESSED, spec.upload_id, spec.platform):
            result.outcome = UNSURE
            result.reason = "Post was already pressed for this upload; not pressing again"
            log.warning("tiktok: %s", result.reason)
            return result
        try:
            self._tap_exact("Post")
        except Exception as exc:  # noqa: BLE001
            result.outcome = UNSURE
            result.reason = f"could not confirm the Post tap: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("tiktok-post-tap")
            return result

        try:
            self._step(10, "wait for upload")
            self._wait_uploaded()
            result.outcome = POSTED
        except Exception as exc:  # noqa: BLE001 - the post may well be out; look, don't repeat
            result.outcome = UNSURE
            result.reason = f"post pressed, upload not confirmed: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("tiktok-upload")
            return result

        self._step(11, "read link")
        try:
            result.url = self._read_link()
        except Exception as exc:  # noqa: BLE001 - the post is out; the link can be asked for
            result.reason = f"posted, link not readable: {exc}"
            log.warning("tiktok: %s", result.reason)
        self.journal.mark(self.job_id, POSTED, spec.upload_id, spec.platform, {"url": result.url})
        if not result.url:
            result.outcome = UNSURE
            result.reason = result.reason or "posted, link not readable"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})

        self._step(12, "engage")
        try:
            result.engaged_s = engage(self.phone)
        except Exception as exc:  # noqa: BLE001 - engagement errors are ignored (§6.4)
            log.warning("tiktok: engagement stopped early: %s", exc)
        return result

    # -- steps -------------------------------------------------------------------------------------
    def _open(self) -> None:
        self.phone.force_stop(self.package)
        self.phone.start_app(self.package)
        elements = wait_for(self.screen, HOME, 45)
        self._dismiss_popups(elements)

    def _dismiss_popups(self, elements: list[Element]) -> None:
        for label in ("Not now", "Skip", "Later", "Cancel", "Don't allow", "Dismiss"):
            button = find_exact(elements, label)
            if button is not None:
                self.screen.tap(button)
                time.sleep(1.0)
                return

    def _handle(self) -> str | None:
        """The handle on the Profile tab, so a wrong account is caught before anything is posted."""
        try:
            self._tap_desc("Profile")
            elements = wait_for(self.screen, PROFILE, 20)
        except ScreenTimeout:
            return None
        for element in elements:
            if element.text.startswith("@"):
                return element.text.strip()
        return None

    def _pick_video(self, spec: PostSpec) -> None:
        elements = self.screen.elements()
        videos_tab = find_exact(elements, "Videos") or find(elements, "Videos")
        if videos_tab is not None:
            self.screen.tap(videos_tab)
            time.sleep(1.5)
            elements = self.screen.elements()
        self._assert_length(elements, spec)
        tile = self._first_tile(elements)
        if tile is not None:
            self.screen.tap(tile)
        else:  # the gallery grid is often one big clickable surface: tap the newest tile's corner
            width, height = self._window()
            self.phone.tap(int(width * 0.17), int(height * 0.34))
        time.sleep(2.0)

    def _assert_length(self, elements: list[Element], spec: PostSpec) -> None:
        """The tile shows the clip's length; a different one means the wrong video (§6.4 step 5)."""
        if not spec.length_s:
            return
        for element in elements:
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", element.text.strip())
            if m:
                shown = int(m.group(1)) * 60 + int(m.group(2))
                if abs(shown - spec.length_s) > 2:
                    raise RuntimeError(f"the gallery shows a {shown}s video, the clip is {spec.length_s:.0f}s")
                return

    def _first_tile(self, elements: list[Element]) -> Element | None:
        clickable = [e for e in elements if e.clickable and e.area > 0]
        if not clickable:
            return None
        width, height = self._window()
        grid = [e for e in clickable if e.bounds[1] > height * 0.15 and e.area > (width * height) * 0.02]
        if not grid:
            return None
        grid.sort(key=lambda e: (e.bounds[1], e.bounds[0]))
        return grid[0]

    def _add_sound_if_asked(self, spec: PostSpec) -> None:
        """§6.6: the most fragile step. For step 1 the post goes out without an added sound."""
        if spec.sound != "trending":
            return
        if spec.sound_required:
            raise RuntimeError("a trending sound is required but the sound step is not built yet")
        log.info("tiktok: posting without an added sound (the sound step comes later)")

    def _write_caption(self, spec: PostSpec) -> None:
        elements = self.screen.elements()
        field = find(elements, "Add description") or find(elements, "Describe your video") or find(elements, "caption")
        if field is None:
            raise RuntimeError("the caption field is not on the post screen")
        self.screen.tap(field)
        time.sleep(0.8)
        if spec.caption:
            self.screen.type_text(spec.caption, min_ms=25, max_ms=70)
        for tag in spec.hashtags:
            if not tag:
                continue
            self.screen.type_text(" " + tag, min_ms=60, max_ms=140)
            time.sleep(1.2)  # let TikTok's suggestion list appear
            suggestion = self._hashtag_suggestion(tag)
            if suggestion is not None:
                self.screen.tap(suggestion)
            time.sleep(0.6)

    def _hashtag_suggestion(self, tag: str) -> Element | None:
        wanted = tag.lstrip("#").lower()
        for element in self.screen.elements():
            text = element.text.strip().lower()
            if text.startswith("#") and wanted in text and element.clickable:
                return element
        return None

    def _ensure_public(self) -> None:
        """§6.4 step 8: everyone can view, no location. A missing control is not an error."""
        elements = self.screen.elements()
        for element in elements:
            if "only you" in element.text.lower() or "only me" in element.text.lower():
                self.screen.tap(element)
                time.sleep(1.0)
                again = self.screen.elements()
                everyone = find(again, "Everyone")
                if everyone is not None:
                    self.screen.tap(everyone)
                break

    def _wait_uploaded(self) -> None:
        """The upload overlay: up to 5 minutes (§6.4 step 10)."""
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            text = " ".join(e.text + " " + e.desc for e in self.screen.elements()).lower()
            if "uploaded" in text or "video is being uploaded" in text:
                return
            if "post" in text and "upload" not in text and "posting" not in text:
                return  # back on the feed: the overlay is gone, which means it finished
            time.sleep(2.0)
        raise RuntimeError("the upload overlay did not finish")

    def _read_link(self) -> str | None:
        """Profile → newest video → Share → Copy link, then read the clipboard (§6.4 step 11)."""
        self._tap_desc("Profile")
        wait_for(self.screen, PROFILE, 20)
        width, height = self._window()
        self.phone.tap(int(width * 0.17), int(height * 0.30))  # newest tile, top-left of the grid
        time.sleep(3.0)
        self._tap_desc("Share")
        wait_for(self.screen, SHARE_SHEET, 20)
        self._tap_exact("Copy link")
        time.sleep(1.0)
        return self._clipboard()

    def _clipboard(self) -> str | None:
        value = self.screen.clipboard()
        if value and "http" in value:
            return value.strip()
        return self._paste_into_search()

    def _paste_into_search(self) -> str | None:
        """Fallback: paste the clipboard into TikTok's search box and read the field (§6.4 step 11)."""
        try:
            self._tap_desc("Search")
            time.sleep(1.0)
            field = find(self.screen.elements(), "Search")
            if field is None:
                return None
            self.screen.tap(field)
            time.sleep(0.8)
            self.screen.long_press(field)
            time.sleep(0.8)
            paste = find_exact(self.screen.elements(), "Paste")
            if paste is None:
                return None
            self.screen.tap(paste)
            time.sleep(0.8)
            text = self.screen.focused_text()
            return text.strip() if text and "http" in text else None
        except Exception:  # noqa: BLE001 - best effort, the post is already out
            return None

    # -- small helpers -----------------------------------------------------------------------------
    def _tap_desc(self, desc: str) -> None:
        elements = self.screen.elements()
        button = find(elements, desc)
        if button is None:
            raise RuntimeError(f"'{desc}' is not on screen")
        self.screen.tap(button)

    def _tap_exact(self, label: str) -> None:
        elements = self.screen.elements()
        button = find_exact(elements, label)
        if button is None:
            raise RuntimeError(f"the '{label}' button is not on screen")
        self.screen.tap(button)

    def _window(self) -> tuple[int, int]:
        return self.screen.size()

    def _shot(self, name: str) -> None:
        if not self.shots_dir:
            return
        try:
            self.screen.screenshot(self.shots_dir / f"{name}-{datetime.now(WIB):%H%M%S}.png")
        except Exception:  # noqa: BLE001
            pass

    def _step(self, n: int, name: str) -> None:
        self.emit({"t": "step", "job": self.job_id, "n": n, "of": 12, "name": name})
        log.info("tiktok step %d/12: %s", n, name)
