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
CREATE_SHEET = Signature("youtube create sheet", any_of=("Create a Short", "Upload a video", "Go live"))
# Measured 2026-11-21 (YouTube 21.46): Create opens the Shorts camera directly - there is no sheet -
# and the only way to a clip is the labelled "Import video from photo library" tile.
SHORTS_CAMERA = Signature("youtube shorts camera", any_of=("Import video from photo library", "Record button",
                                                          "Close camera"))
GALLERY = Signature("youtube gallery", any_of=("Create from gallery", "Recents", "Next", "Create video"))
EDITOR = Signature("youtube editor", any_of=("Swipe up to edit", "More tools", "Exit editor", "Next"))
DETAILS = Signature("youtube details", any_of=("Add details", "Caption your Short", "Upload Short", "Save draft"))
VISIBILITY = Signature("youtube visibility", any_of=("Public", "Private", "Unlisted", "Save"))
UPLOADED = Signature("youtube uploaded", any_of=("Upload complete", "Short posted", "processing", "uploaded", "Done"))
SHARE_SHEET = Signature("share sheet", any_of=("Copy link", "Share to", "Copy", "Links"))
PROFILE = Signature("youtube you", any_of=("View channel", "Your videos", "Switch account", "Your channel"))
_NEXT_OR_DETAILS = Signature("youtube editor or details", any_of=("Next", "Add details", "Upload Short"))
# The Create tab sometimes opens the Shorts camera and sometimes the picker itself (measured
# 2026-11-21: the same tap did both within an hour), so either one is a valid way in.
_CAMERA_OR_PICKER = Signature(
    "youtube camera or picker",
    any_of=("Import video from photo library", "Record button", "Close camera",
            "Create from gallery", "Recents", "Create video"),
)


class YouTubePoster:
    def __init__(
        self,
        phone: Phone,
        screen: Screen,
        journal: Journal,
        job_id: str,
        package: str = YOUTUBE,
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
            elements = wait_for(self.screen, _CAMERA_OR_PICKER, 30)
            self._clear_draft_picker()
            self._step(4, "pick video")
            if not GALLERY.matches(self.screen.elements()):
                self._open_gallery()
            wait_for(self.screen, GALLERY, 30)
            self._pick_video(spec)
            self._step(5, "next")
            # Picker -> editor -> details: this build shows a Next on each, and the first Shorts
            # editor visit asks for consent ("I agree" / "No thanks") before the editor appears
            # (measured 2026-11-21). Tap Next until the details screen is up.
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                elements = self.screen.elements()
                if DETAILS.matches(elements):
                    break
                agree = find_exact(elements, "I agree")
                if agree is not None:
                    self.screen.tap(agree)
                    time.sleep(3.0)
                    continue
                button = find_exact(elements, "Next")
                if button is not None:
                    self.screen.tap(button)
                    time.sleep(3.0)
                    continue
                time.sleep(1.5)
            wait_for(self.screen, DETAILS, 60)
            self._step(6, "title")
            self._write_title(spec)
            self._step(7, "visibility")
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
        self._step(8, "press upload")
        may_press, why_not = self.journal.claim_press(self.job_id, spec.upload_id, spec.platform)
        if not may_press:
            result.outcome = UNSURE
            result.reason = why_not
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
            self._step(9, "wait for upload")
            self._wait_uploaded()
            result.outcome = POSTED
        except Exception as exc:  # noqa: BLE001 - the Short may well be out; look, don't repeat
            result.outcome = UNSURE
            result.reason = f"upload pressed, not confirmed: {exc}"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})
            self._shot("youtube-upload")
            return result

        self._step(10, "read link")
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

        self._step(11, "pinned comment")
        if spec.pinned_comment:
            try:
                self._pin_comment(spec)
            except Exception as exc:  # noqa: BLE001 - the laptop pins it today when the robot cannot
                log.warning("youtube: pinning the comment failed (%s); pin it by hand as today", exc)
        self._step(12, "engage")
        try:
            self._back_to_feed()
            result.engaged_s = engage(self.phone)
        except Exception as exc:  # noqa: BLE001 - engagement errors are ignored
            log.warning("youtube: engagement stopped early: %s", exc)
        return result

    # -- steps -------------------------------------------------------------------------------------
    def _open(self) -> None:
        self.phone.force_stop(self.package, self.user)
        time.sleep(1.0)
        self.phone.start_app(self.package, self.user)
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
        """The signed-in channel's own name, read from the You tab.

        Measured 2026-11-21 (YouTube 21.46): the home top bar has **no account avatar** any more - only
        the logo, Notifications and Search - so the old avatar check failed on a signed-in app. The You
        tab shows the channel name right under "View channel".
        """
        self._open_you()
        elements = self.screen.elements()
        height = self.screen.size()[1]
        skipped = {"view channel", "get premium", "accounts", "notifications", "search", "settings", "you"}
        name = None
        # The You tab lists "View channel" and then the channel's own name right after it, which is the
        # only reliable way to tell the two apart from the menu items.
        seen_marker = False
        for element in elements:
            text = (element.text or "").strip()
            label = text or (element.desc or "").strip()
            if not label:
                continue
            if not seen_marker:
                if label.lower() == "view channel":
                    seen_marker = True
                continue
            if label.lower() in skipped or "@" in label:
                continue
            if element.bounds[1] < 100 or element.bounds[1] > height * 0.60:
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}(\s*[AP]M)?", label):   # the status bar's clock
                continue
            if 2 <= len(label) <= 40:
                name = label          # on this build the channel's name is a content-desc, not a text
                break
        # Back to the feed by tapping the bottom Home tab: Back here would leave the app.
        for element in elements:
            if (element.desc or element.text or "").strip() == "Home" and element.bounds[1] > height * 0.85:
                self.screen.tap(element)
                time.sleep(2.0)
                break
        else:
            self._back_to_feed()
        if name is None:
            raise RuntimeError("YouTube shows no account name (not signed in?)")
        return name

    @staticmethod
    def _account_name(elements: list[Element]) -> str | None:
        for element in elements:
            if element.text.strip() and "@" in element.text:
                return element.text.split("@")[0].strip()
        return None

    def _open_create(self) -> None:
        """The Create tab in the bottom bar; on this build it opens the Shorts camera directly."""
        deadline = time.monotonic() + 20
        create = None
        while time.monotonic() < deadline and create is None:
            elements = self.screen.elements()
            height = self.screen.size()[1]
            create = next(
                (
                    e for e in elements
                    if e.enabled and e.bounds[1] > height * 0.85
                    and "create" in ((e.desc or "") + " " + (e.text or "")).lower()
                ),
                None,
            )
            if create is None:
                time.sleep(1.5)
        if create is None:
            width, height = self.screen.size()
            self.phone.tap(int(width * 0.625), int(height * 0.96))
            time.sleep(3.0)
            return
        self.screen.tap(create)
        time.sleep(3.0)
        # This build's Create can open a chooser with two big tabs - "Drafts" and "Create video" -
        # and the gallery grid underneath it. "Create video" on this build leads to the AI creation
        # screen, while the grid is already the picker (measured 2026-11-21), so it is tapped only when
        # no clip is on screen.
        elements = self.screen.elements()
        has_clips = any((e.desc or e.text or "").strip().lower().endswith(".mp4") for e in elements)
        chooser = find_exact(elements, "Create video") or find_exact(elements, "Create a Short")
        if chooser is not None and not has_clips:
            self.screen.tap(chooser)
            time.sleep(3.0)
        # A "Back / Continue" prompt can sit between Create and the picker (measured 2026-11-21).
        for _ in range(3):
            elements = self.screen.elements()
            cont = find_exact(elements, "Continue")
            if cont is None:
                break
            self.screen.tap(cont)
            time.sleep(3.0)

    def _clear_draft_picker(self) -> None:
        """Leave the draft list that an interrupted run can leave behind; it blocks a new Short.

        Measured 2026-11-21: after a stopped run, Create can land on the drafts ("Edited 50 minutes
        ago") instead of the camera, and every later step then waits for a screen that never comes.
        """
        for _ in range(3):
            elements = self.screen.elements()
            close = find_exact(elements, "Close draft picker") or find(elements, "Close draft picker")
            if close is None:
                return
            self.screen.tap(close)
            time.sleep(2.0)

    def _open_gallery(self) -> None:
        """The camera's import tile (this build labels it "Import video from photo library")."""
        elements = self.screen.elements()
        for label in ("Import video from photo library", "Import", "Gallery", "Upload", "Recents", "Pick"):
            button = find_exact(elements, label) or find(elements, label)
            if button is not None:
                self.screen.tap(button)
                return
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.10), int(height * 0.73))

    def _pick_video(self, spec: PostSpec) -> None:
        # The tiles are the gallery itself; "Create from gallery" in that header leads to YouTube's AI
        # creation page (measured 2026-11-21), so it must not be tapped.
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
        """The plan's step 4: the trimmer may default shorter; the shown length must be the clip's.

        Kept for a build that opens a trimmer; this one goes from the picker to the editor without one,
        and the length was already checked on the picker's own tile.
        """
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            self._assert_length(elements, spec)
            done = find_exact(elements, "Done")
            if done is not None:
                self.screen.tap(done)
                time.sleep(1.5)
                return
            time.sleep(1.0)

    def _write_title(self, spec: PostSpec) -> None:
        """The Short's title = ClipMaker's title, when the build exposes a title field at all.

        Measured 2026-11-21 twice: tapping the row ("Add details") changes the screen but no text field
        appears, and then clear_text / set_text / hide_keyboard each block for about a minute - the step
        cost 142 s of a 190 s run for nothing. So the title is typed only when the screen actually shows
        a title field ("Add a title", "Describe your Short"); otherwise it is skipped in a second and
        YouTube's default title stands (it can be edited on the video afterwards).
        """
        wanted = (spec.title or spec.full_caption).strip()[:100]
        elements = self.screen.elements()
        hint = any(
            needle in ((e.text or "") + " " + (e.desc or "")).lower()
            for e in elements
            for needle in ("add a title", "describe your short", "title that describes")
        )
        row = find(elements, "Add details") or find(elements, "Title") or find(elements, "Caption your Short")
        if not hint or row is None:
            log.warning("youtube: this build exposes no title field; YouTube's default title is used")
            return
        self.screen.tap(row)
        time.sleep(1.5)
        edited = False
        for _ in range(2):
            try:
                self.screen.clear_field()
            except Exception:  # noqa: BLE001 - an empty field may refuse a clear
                pass
            self.screen.set_text(wanted)
            time.sleep(0.8)
            actual = (self.screen.focused_text() or "").strip()
            if actual and (actual[:20].lower() in wanted.lower() or wanted[:20].lower() in actual.lower()):
                edited = True
                break
        if edited:
            self.screen.hide_keyboard()
            done = find_exact(self.screen.elements(), "Done") or find_exact(self.screen.elements(), "Save")
            if done is not None:
                self.screen.tap(done)
                time.sleep(1.5)
        else:
            log.warning("youtube: the title did not stick; YouTube's default title is used")

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
        """The bottom bar's "You" tab (exact label in the bottom bar).

        A substring match is wrong here: the top-left logo's description is "YouTube", which contains
        "You", and tapping it opens Search (measured 2026-11-21).
        """
        height = self.screen.size()[1]
        for element in self.screen.elements():
            label = (element.desc or element.text or "").strip()
            if label == "You" and element.bounds[1] > height * 0.85:
                self.screen.tap(element)
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
        # ms = how long the *previous* step took, so a slow screen is visible in every run.
        now = time.monotonic()
        spent = int((now - getattr(self, "_last_step_at", now)) * 1000)
        self._last_step_at = now
        self.emit({"t": "step", "job": self.job_id, "n": n, "of": 12, "name": name, "ms": spent})
        log.info("youtube step %d/12: %s (%.1fs since the last step)", n, name, spent / 1000.0)
