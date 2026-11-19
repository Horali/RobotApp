"""YouTube: one Short, from the phone's own app (PLAN section 6.7).

The order is the plan's: open YouTube, check the avatar is the brand's channel, + -> Create a
Short -> the newest video (length check, keep the full length) -> Next -> the caption (= the
title) -> Visibility Public, Audience not made for kids -> Upload Short. The journal is written
*before* the Upload tap; after it nothing is ever pressed twice.

Honest note: like Instagram's, these signatures follow the plan's description of YouTube's
screens. The first real YouTube sitting (Timmy, section 8.8's test) provides the fixtures.
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

YOUTUBE = "com.google.android.youtube"

HOME = Signature("youtube home", any_of=("Home", "Shorts", "Subscriptions", "You"))
CREATE_SHEET = Signature("youtube create sheet", any_of=("Create a Short", "Create", "Upload a video", "Go live"))
SHORTS_CAMERA = Signature("youtube shorts camera", any_of=("Add sound", "Record", "Upload", "Gallery"))
GALLERY = Signature("youtube gallery", any_of=("Recents", "Gallery", "Next", "Done"))
TRIM = Signature("youtube trim", any_of=("Done", "Next", "trim", "Preview"))
DETAILS = Signature("youtube details", any_of=("Title", "Caption", "Describe your Short", "Shorts"))
VISIBILITY = Signature("youtube visibility", any_of=("Public", "Private", "Unlisted", "Save"))
UPLOADED = Signature("youtube uploaded", any_of=("Upload complete", "Short posted", "processing", "uploaded", "Done"))
SHARE_SHEET = Signature("share sheet", any_of=("Copy link", "Share to", "Copy", "Links"))
PROFILE = Signature("youtube you", any_of=("View channel", "Your videos", "Switch account", "Your channel"))
_NEXT_OR_DETAILS = Signature("youtube editor or details", any_of=("Next", "Title", "Describe your Short", "Upload Short"))


class YouTubePoster:
    def __init__(
        self,
        phone: Phone,
        screen: Screen,
        journal: Journal,
        job_id: str,
        package: str = YOUTUBE,
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
        self.channel: str | None = None

    # -- the whole post ----------------------------------------------------------------------------
    def post(self, spec: PostSpec, dry_run: bool = False) -> PostResult:
        result = PostResult(spec.upload_id, spec.platform, FAILED)
        try:
            self._step(1, "open app")
            self._open()
            self._step(2, "check channel")
            self.channel = self._check_channel()
            result.handle = self.channel
            self._step(3, "create")
            self._open_create()
            wait_for(self.screen, SHORTS_CAMERA, 30)
            self._step(4, "pick video")
            self._open_gallery()
            wait_for(self.screen, GALLERY, 30)
            self._pick_video(spec)
            self._step(5, "trim")
            self._keep_full_length(spec)
            self._step(6, "next")
            # Some builds show an editor with a Next between the trim and the details; some don't.
            elements = wait_for(self.screen, _NEXT_OR_DETAILS, 60)
            if find_exact(elements, "Next") is not None:
                self._tap_exact("Next")
                wait_for(self.screen, DETAILS, 60)
            self._step(7, "title")
            self._write_title(spec)
            self._step(8, "visibility")
            self._set_visibility()
        except Exception as exc:  # noqa: BLE001 - anything here is before the press
            result.reason = str(exc)
            self._shot("youtube-before-upload")
            self.journal.mark(self.job_id, FAILED, spec.upload_id, spec.platform, {"reason": result.reason})
            log.warning("youtube: failed before Upload: %s", exc)
            return result

        if dry_run:
            self._shot("youtube-dry-run")
            result.outcome = "dry_run"
            result.reason = "stopped before Upload on purpose"
            log.info("youtube: dry run reached the details screen; nothing was pressed")
            return result

        # From here on, never press Upload twice.
        self._step(9, "press upload")
        if not self.journal.mark(self.job_id, PRESSED, spec.upload_id, spec.platform):
            result.outcome = UNSURE
            result.reason = "Upload was already pressed for this upload; not pressing again"
            log.warning("youtube: %s", result.reason)
            return result
        try:
            self._tap_exact("Upload Short")
        except Exception as exc:  # noqa: BLE001
            result.outcome = UNSURE
            result.reason = f"could not confirm the Upload tap: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("youtube-upload-tap")
            return result

        try:
            self._step(10, "wait for upload")
            self._wait_uploaded()
            result.outcome = POSTED
        except Exception as exc:  # noqa: BLE001 - the Short may well be out; look, don't repeat
            result.outcome = UNSURE
            result.reason = f"upload pressed, not confirmed: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("youtube-upload")
            return result

        self._step(11, "read link")
        try:
            result.url = self._read_link()
        except Exception as exc:  # noqa: BLE001 - the Short is out; the link can be asked for
            result.reason = f"posted, link not readable: {exc}"
            log.warning("youtube: %s", result.reason)
        self.journal.mark(self.job_id, POSTED, spec.upload_id, spec.platform, {"url": result.url})
        if not result.url:
            result.outcome = UNSURE
            result.reason = result.reason or "posted, link not readable"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})

        self._step(12, "pinned comment")
        if spec.pinned_comment:
            try:
                self._pin_comment(spec)
            except Exception as exc:  # noqa: BLE001 - the laptop pins it today when the robot cannot
                log.warning("youtube: pinning the comment failed (%s); pin it by hand as today", exc)
        self._step(13, "engage")
        try:
            self._back_to_feed()
            result.engaged_s = engage(self.phone)
        except Exception as exc:  # noqa: BLE001 - engagement errors are ignored
            log.warning("youtube: engagement stopped early: %s", exc)
        return result

    # -- steps -------------------------------------------------------------------------------------
    def _open(self) -> None:
        self.phone.force_stop(self.package)
        time.sleep(1.0)
        self.phone.start_app(self.package)
        time.sleep(8.0)
        deadline = time.monotonic() + 60
        stable = 0
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if HOME.matches(elements) and self._in_front():
                stable += 1
                if stable >= 2:
                    return
            else:
                stable = 0
                self._clear_dialog(elements)
            time.sleep(1.5)
        self._shot("youtube-open")
        raise ScreenTimeout("YouTube did not reach its home screen in 60 s")

    def _in_front(self) -> bool:
        try:
            package, _ = self.phone.fore_app()
        except Exception:  # noqa: BLE001
            return True
        if not package:
            return True
        return package == self.package

    def _clear_dialog(self, elements: list[Element]) -> bool:
        for label in ("Not now", "Skip", "Later", "Cancel", "Don't allow", "Dismiss", "No thanks"):
            button = find_exact(elements, label)
            if button is not None:
                self.screen.tap(button)
                time.sleep(1.0)
                return True
        return False

    def _check_channel(self) -> str | None:
        """The avatar -> the account sheet: the signed-in account's name must be the brand's."""
        elements = self.screen.elements()
        avatar = next((e for e in elements if "Account" in (e.desc or "")), None)
        if avatar is None:
            # Not signed in at all: no account avatar on the home screen.
            raise RuntimeError("YouTube shows no account avatar (not signed in?)")
        self.screen.tap(avatar)
        time.sleep(2.5)
        name = self._account_name(self.screen.elements())
        if name is None:
            # The account sheet may hide behind a second tap on the avatar's sheet.
            avatar2 = next((e for e in self.screen.elements() if "Account" in (e.desc or "")), None)
            if avatar2 is not None:
                self.screen.tap(avatar2)
                time.sleep(2.0)
            name = self._account_name(self.screen.elements())
        # Back to the feed.
        self.screen.press_back()
        time.sleep(1.0)
        return name

    @staticmethod
    def _account_name(elements: list[Element]) -> str | None:
        for element in elements:
            if element.text.strip() and "@" in element.text:
                return element.text.split("@")[0].strip()
        for element in elements:
            text = element.text.strip()
            if text and 2 <= len(text) <= 40 and text.replace(" ", "").isalpha():
                continue
        return None

    def _open_create(self) -> None:
        """The + in the middle of the bottom bar, then 'Create a Short' in the sheet."""
        elements = self.screen.elements()
        create = next((e for e in elements if e.enabled and ("Create" in (e.desc or "") or e.text.strip() == "+"
                                                            or "Create a video" in (e.desc or ""))), None)
        if create is None:
            raise RuntimeError("the create (+) button is not on YouTube's bottom bar")
        self.screen.tap(create)
        wait_for(self.screen, CREATE_SHEET, 30)
        short = find(self.screen.elements(), "Create a Short") or find(self.screen.elements(), "Short")
        if short is None:
            raise RuntimeError("'Create a Short' is not in the create sheet")
        self.screen.tap(short)

    def _open_gallery(self) -> None:
        """The shorts camera's gallery entry, bottom left."""
        elements = self.screen.elements()
        for label in ("Gallery", "Upload", "Recents", "Pick"):
            button = find_exact(elements, label) or find(elements, label)
            if button is not None:
                self.screen.tap(button)
                return
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.10), int(height * 0.72))

    def _pick_video(self, spec: PostSpec) -> None:
        elements = self.screen.elements()
        self._assert_length(elements, spec)
        width, height = self.screen.size()
        big = [e for e in elements if e.clickable and e.area >= (width * height) * 0.02 and e.bounds[1] > height * 0.1]
        if big:
            tile = min(big, key=lambda e: (e.bounds[1], e.bounds[0]))
            self.screen.tap(tile)
        else:
            self.phone.tap(int(width * 0.17), int(height * 0.34))
        time.sleep(2.5)

    def _assert_length(self, elements: list[Element], spec: PostSpec) -> None:
        if not spec.length_s:
            return
        for element in elements:
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", element.text.strip())
            if m:
                shown = int(m.group(1)) * 60 + int(m.group(2))
                if abs(shown - spec.length_s) > 2:
                    raise RuntimeError(f"the gallery shows a {shown}s video, the clip is {spec.length_s:.0f}s")
                return

    def _keep_full_length(self, spec: PostSpec) -> None:
        """The plan's step 4: the trimmer may default shorter; the shown length must be the clip's."""
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if TRIM.matches(elements):
                self._assert_length(elements, spec)
                done = find_exact(elements, "Done") or find(elements, "Done")
                if done is not None:
                    self.screen.tap(done)
                    time.sleep(1.5)
                    return
            time.sleep(1.0)

    def _write_title(self, spec: PostSpec) -> None:
        """The Short's title = ClipMaker's title (the same one the laptop would use)."""
        wanted = (spec.title or spec.full_caption).strip()[:100]
        elements = self.screen.elements()
        field = (find(elements, "Title") or find(elements, "Describe your Short")
                 or find(elements, "Caption"))
        if field is None:
            raise RuntimeError("the title field is not on the details screen")
        self.screen.tap(field)
        time.sleep(0.8)
        for attempt in (0, 1):
            try:
                self.screen.clear_field()
            except Exception:  # noqa: BLE001
                pass
            self.screen.set_text(wanted)
            time.sleep(1.0)
            actual = (self.screen.focused_text() or "").strip()
            if actual and actual[:20].lower() in wanted.lower():
                return
            log.warning("youtube: the title did not stick (attempt %d): %r", attempt + 1, actual[:50])
        raise RuntimeError("the title could not be written into the details screen")

    def _set_visibility(self) -> None:
        """Public, and 'No, it's not made for kids' (the same as the laptop uploader)."""
        elements = self.screen.elements()
        public = find_exact(elements, "Public") or find(self.screen.elements(), "Public")
        if public is None:
            # Some builds show the choices only after tapping the visibility row.
            row = find(elements, "Visibility") or find(elements, "Private")
            if row is not None:
                self.screen.tap(row)
                time.sleep(1.5)
                elements = self.screen.elements()
                public = find_exact(elements, "Public") or find(elements, "Public")
        if public is not None:
            self.screen.tap(public)
            time.sleep(1.0)
        elements = self.screen.elements()
        kids = find(elements, "No, it's not made for kids") or find(elements, "not made for kids") \
            or find(elements, "No, it's Not made for kids")
        if kids is not None:
            self.screen.tap(kids)
            time.sleep(1.0)

    def _wait_uploaded(self) -> None:
        """Upload + processing, up to 5 minutes; done when the feed is back."""
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if UPLOADED.matches(elements) or HOME.matches(elements):
                return
            time.sleep(2.0)
        raise RuntimeError("the upload did not finish")

    def _read_link(self) -> str | None:
        """You -> Your videos -> the newest -> ... -> Copy link. The clipboard only counts with
        youtube.com/shorts or youtu.be in it."""
        self._open_you()
        videos = find(self.screen.elements(), "Your videos")
        if videos is not None:
            self.screen.tap(videos)
            time.sleep(3.0)
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.5), int(height * 0.30))   # the newest video row
        time.sleep(3.5)
        menu = find(self.screen.elements(), "...") or find(self.screen.elements(), "More options")
        if menu is None:
            raise RuntimeError("the video's menu (...) is not on screen")
        self.screen.tap(menu)
        wait_for(self.screen, SHARE_SHEET, 20)
        link = find_exact(self.screen.elements(), "Copy link")
        if link is None:
            raise RuntimeError("'Copy link' is not in the share sheet")
        self.screen.tap(link)
        time.sleep(1.5)
        value = self.screen.clipboard()
        if value and ("youtube.com/shorts" in value or "youtu.be" in value):
            return value.strip()
        return None

    def _open_you(self) -> None:
        elements = self.screen.elements()
        you = next((e for e in elements if e.enabled and (e.text.strip() == "You" or "You" in (e.desc or ""))), None)
        if you is not None:
            self.screen.tap(you)
            time.sleep(2.5)
            return
        raise RuntimeError("the 'You' tab is not on the bottom bar")

    def _pin_comment(self, spec: PostSpec) -> None:
        """Comments -> type -> post -> ... -> Pin (the plan's step 12)."""
        comments = find(self.screen.elements(), "Comments") or find(self.screen.elements(), "comments")
        if comments is None:
            raise RuntimeError("the comments button is not on screen")
        self.screen.tap(comments)
        time.sleep(2.0)
        field = find(self.screen.elements(), "Add a comment") or find(self.screen.elements(), "comment")
        if field is None:
            raise RuntimeError("the comment field is not on screen")
        self.screen.tap(field)
        time.sleep(0.8)
        self.screen.set_text(spec.pinned_comment)
        post = find_exact(self.screen.elements(), "Post") or find(self.screen.elements(), "Post")
        if post is None:
            raise RuntimeError("the comment's Post button is not on screen")
        self.screen.tap(post)
        time.sleep(2.5)
        menu = find(self.screen.elements(), "...") or find(self.screen.elements(), "More options")
        if menu is not None:
            self.screen.tap(menu)
            time.sleep(1.5)
            pin = find(self.screen.elements(), "Pin")
            if pin is not None:
                self.screen.tap(pin)

    def _back_to_feed(self) -> None:
        for _ in range(4):
            if HOME.matches(self.screen.elements()):
                return
            self.screen.press_back()
            time.sleep(1.0)

    # -- small helpers -----------------------------------------------------------------------------
    def _tap_exact(self, label: str, timeout_s: float = 20.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            button = find_exact(self.screen.elements(), label)
            if button is not None:
                self.screen.tap(button)
                return
            time.sleep(1.0)
        raise RuntimeError(f"the '{label}' button is not on screen")

    def _shot(self, name: str) -> None:
        if not self.shots_dir:
            return
        try:
            self.screen.screenshot(self.shots_dir / f"{name}-{datetime.now(WIB):%H%M%S}.png")
        except Exception:  # noqa: BLE001
            pass

    def _step(self, n: int, name: str) -> None:
        self.emit({"t": "step", "job": self.job_id, "n": n, "of": 13, "name": name})
        log.info("youtube step %d/13: %s", n, name)
