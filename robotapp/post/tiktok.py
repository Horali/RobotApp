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

# Play's "TikTok needs to download additional files to add features" sheet: the installed musically is the
# base APK, and Play wants the dynamic modules of its bundle. Measured 2026-11-20/21: it owns the screen
# after Create and again when the camera/editor assets are asked for.
PLAY_PACKAGE = "com.android.vending"
_PLAY_SHEET_WORDS = ("additional files", "download from play", "dismiss update dialog")


def _says_play_sheet(elements: list[Element]) -> bool:
    text = " ".join(((e.text or "") + " " + (e.desc or "")) for e in elements).lower()
    return any(word in text for word in _PLAY_SHEET_WORDS)


def _dismiss_control(elements: list[Element]) -> Element | None:
    """The sheet's own way out. Its label is "Dismiss update dialog" on this Play build, and on a fresh
    sheet the control is missing for the first seconds - so callers wait instead of reading once."""
    for element in elements:
        if not element.enabled:
            continue
        label = ((element.desc or "") + " " + (element.text or "")).lower()
        if "dismiss" in label:
            return element
    return None



def tiktok_package(user: int) -> str:
    """The TikTok build a space uses: G2G's trill in the owner user, the US build everywhere else."""
    return TIKTOK_ID if user == 0 else TIKTOK_US

HOME = Signature("tiktok home", any_of=("For You", "Following", "Inbox", "Profile"))
CAMERA = Signature("tiktok camera", any_of=("Upload", "Add sound", "Flip", "Record"))
GALLERY = Signature("tiktok gallery", any_of=("Videos", "Photos", "Select", "Next"))
EDITOR = Signature("tiktok editor", any_of=("Next", "Add sound", "Edit", "Sound"))
POST_SCREEN = Signature("tiktok post screen", any_of=("Add description", "Who can watch", "Post", "Describe your video"))
UPLOADED = Signature("tiktok uploaded", any_of=("Video uploaded", "Your video is being uploaded", "Uploading", "Posting"))
PROFILE = Signature("tiktok profile", any_of=("Edit profile", "Followers", "Following"))
SHARE_SHEET = Signature("tiktok share sheet", any_of=("Copy link", "Share to", "Save video", "Duet"))
SHARE_ON_TIKTOK = Signature("tiktok share from another app", any_of=("Share on TikTok", "Share to TikTok"))


class TikTokPoster:
    def __init__(
        self,
        phone: Phone,
        screen: Screen,
        journal: Journal,
        job_id: str,
        package: str = TIKTOK_US,
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
        self._play_dismissals = 0

    # -- the whole post ----------------------------------------------------------------------------
    def post(self, spec: PostSpec, dry_run: bool = False) -> PostResult:
        result = PostResult(spec.upload_id, spec.platform, FAILED)
        try:
            self._step(1, "open app")
            self._open()
            self._step(2, "check handle")
            self.handle = self._handle()
            result.handle = self.handle
            self._step(3, "pick video")
            self._open_editor(spec)
            self._wait_past_play(EDITOR, 60)
            self._step(4, "editor")
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

        if dry_run:
            # Everything up to the press, nothing pressed: what an app update's dry run uses (§12).
            self._shot("tiktok-dry-run")
            result.outcome = "dry_run"
            result.reason = "stopped before Post on purpose"
            log.info("tiktok: dry run reached the post screen; nothing was pressed")
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
        result.sound = "trending" if self.sound_added else None
        self.journal.mark(self.job_id, POSTED, spec.upload_id, spec.platform, {"url": result.url})
        if not result.url:
            result.outcome = UNSURE
            result.reason = result.reason or "posted, link not readable"
            self.journal.mark(self.job_id, UNSURE, spec.upload_id, spec.platform, {"reason": result.reason})

        self._step(12, "engage")
        try:
            self._back_to_feed()
            result.engaged_s = engage(self.phone)
        except Exception as exc:  # noqa: BLE001 - engagement errors are ignored (§6.4)
            log.warning("tiktok: engagement stopped early: %s", exc)
        return result

    def _back_to_feed(self) -> None:
        """Engagement happens on the feed, not on the video page the link was read from."""
        for _ in range(3):
            if HOME.matches(self.screen.elements()):
                return
            self.screen.press_back()
            time.sleep(1.0)

    # -- steps -------------------------------------------------------------------------------------
    def _open(self) -> None:
        self.phone.force_stop(self.package, self.user)
        time.sleep(1.0)
        self.phone.start_app(self.package, self.user)
        time.sleep(6.0)  # TikTok's splash lasts several seconds; reading before that gives a stale screen
        stable = 0
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            # Play can throw its "TikTok needs to download additional files" sheet over the app
            # (measured 2026-11-20: it covered the screen for the whole 60 s wait). Dismiss it - and
            # then leave Play, because the sheet's activity belongs to Play, which stays in front
            # while TikTok waits behind it (measured 2026-11-21: the whole 90 s went on Play).
            if self._handle_play_sheet(elements):
                self._back_to_tiktok()
                stable = 0
                continue
            if not self._in_front():
                # Something else owns the screen (usually Play's own UI after its sheet).
                self._back_to_tiktok()
                stable = 0
                time.sleep(1.5)
                continue
            if HOME.matches(elements):
                stable += 1
                if stable >= 2:
                    self._dismiss_popups(elements)
                    return
            else:
                stable = 0
                self._clear_dialog(elements)
            time.sleep(1.5)
        self._shot("tiktok-open")
        raise ScreenTimeout("TikTok did not reach its home screen in 90 s")

    def _back_to_tiktok(self) -> None:
        """Bring TikTok back in front of whatever took the screen (Play, a system sheet).

        One Back closes the other app's top screen (Play's acquisition dialog or its account sheet);
        only if that is not enough is the app started again, which brings TikTok's task forward instead
        of waiting for it. Measured 2026-11-21: with Play left in front, TikTok never got the screen and
        the post stopped before anything was pressed.
        """
        if self._leave_play():
            return
        self.phone.start_app(self.package, self.user)
        time.sleep(3.0)

    def _leave_play(self) -> bool:
        """Press Back once when another app owns the screen; True when TikTok is in front afterwards.

        Safe in the middle of a post (the editor, the caption): it never restarts the app, so a
        dismissed Play sheet returns to the same screen instead of the feed.
        """
        try:
            package, _ = self.phone.fore_app()
        except Exception:  # noqa: BLE001 - a phone that cannot say is not a reason to press Back
            return True
        if not package or package == self.package:
            return True
        self.screen.press_back()
        time.sleep(1.5)
        try:
            package, _ = self.phone.fore_app()
        except Exception:  # noqa: BLE001
            return True
        return not package or package == self.package

    def _in_front(self) -> bool:
        """Guard against a stale hierarchy: the app actually resumed must be TikTok's."""
        try:
            package, _ = self.phone.fore_app()
        except Exception:  # noqa: BLE001 - if the phone cannot say, trust the screen text
            return True
        if not package:  # a phone (or a fake) that does not answer is not a reason to fail
            return True
        return package == self.package

    def _clear_dialog(self, elements: list[Element]) -> bool:
        """TikTok's own prompts, and Android's. Returns True when something was dismissed.

        The location prompt ("Allow precise location") only offers Allow / Open settings: the robot opens the
        app's settings page and comes back, which keeps location off and the app usable.
        """
        text = " ".join(e.text for e in elements)
        if "Allow precise location" in text:
            button = find_exact(elements, "Open settings")
            if button is not None:
                self.screen.tap(button)
                time.sleep(2.0)
                self.screen.press_back()
                return True
        for label in ("Not now", "Skip", "Later", "Cancel", "Don't allow", "Dismiss", "Agree and continue"):
            button = find_exact(elements, label)
            if button is not None:
                self.screen.tap(button)
                return True
        return False

    def _dismiss_popups(self, elements: list[Element]) -> None:
        for label in ("Not now", "Skip", "Later", "Cancel", "Don't allow", "Dismiss", "Agree and continue"):
            button = find_exact(elements, label)
            if button is not None:
                self.screen.tap(button)
                time.sleep(1.0)
                return

    def _handle(self) -> str | None:
        """The handle on the Profile tab, so a wrong account is caught before anything is posted."""
        try:
            self._tap_nav("Profile")
            elements = wait_for(self.screen, PROFILE, 20)
        except ScreenTimeout:
            return None
        for element in elements:
            if element.text.startswith("@"):
                return element.text.strip()
        return None

    def _tap_nav(self, label: str) -> bool:
        """Tap a bottom-bar item by its exact label.

        A substring search is wrong here: the feed's overlay says "Officialicarus profile", and tapping that
        opens the video author's profile instead of your own (which is how step 2 went wrong the first time).
        """
        width, height = self.screen.size()
        for element in self.screen.elements():
            if element.enabled and element.says(label) and element.bounds[1] >= height * 0.85:
                self.screen.tap(element)
                return True
        return False

    def _open_editor(self, spec: PostSpec) -> None:
        """Get the clip into TikTok's editor.

        The share intent is the reliable route on this build (trill 47.8.3): the camera's upload tile is drawn
        but not exposed to the accessibility tree, so `input tap` on it does nothing. The share sheet shows the
        clip with its own Video button and lands in the same editor. The camera route stays as the fallback for
        a build where the share activity is missing.
        """
        if spec.media_uri and self._share_video(spec):
            return
        # The share route can leave its own sheet (or a Play sheet) on screen, and the camera route
        # then looked for the bottom bar inside it and failed (measured 2026-11-20). Back out until
        # the bottom bar's own Create is there; only if that never happens, restart the app once.
        self._step(3, "create")
        for _ in range(6):
            elements = self.screen.elements()
            if self._handle_play_sheet(elements):
                self._back_to_tiktok()   # Play keeps its own app in front after the sheet
                continue
            if self._tap_nav("Create"):
                break
            self.screen.press_back()
            time.sleep(1.5)
        else:
            self.phone.force_stop(self.package, self.user)
            time.sleep(1.0)
            self.phone.start_app(self.package, self.user)
            time.sleep(12.0)
            for _ in range(20):
                elements = self.screen.elements()
                if self._handle_play_sheet(elements):
                    self._back_to_tiktok()
                    continue
                if self._tap_nav("Create"):
                    break
                time.sleep(1.5)
            else:
                self._tap_desc("Create")
        wait_for(self.screen, CAMERA, 30)
        self._open_gallery()
        self._wait_past_play(GALLERY, 30)
        self._pick_video(spec)

    def _wait_past_play(self, signature: Signature, timeout_s: float) -> None:
        """Wait for `signature`, dismissing Play's 'TikTok needs additional files' sheet whenever it appears.

        The sheet came back mid-flow on 2026-11-20 and covered the editor for the whole 60 s wait;
        the tap that dismisses it is the only way forward (the app is installed from the APK, so Play
        keeps offering the extra modules).
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if self._handle_play_sheet(elements):
                self._leave_play()      # Back only: never restart TikTok mid-post
                continue
            if signature.matches(elements):
                return
            time.sleep(1.5)
        raise ScreenTimeout(f"waited {timeout_s:.0f}s for '{signature.name}'")

    def _handle_play_sheet(self, elements: list[Element]) -> bool:
        """Dismiss Play's "needs additional files" sheet when it owns the screen; True when it was there.

        Two things this build showed: the sheet's dismiss control is missing while it animates in (so
        wait for it rather than reading once), and its label is text, not a description. When it keeps
        coming back, the app needs what the base APK does not have - stop before anything is pressed and
        say which fix that is, instead of burning the whole post on it.
        """
        if not _says_play_sheet(elements):
            try:
                package, _ = self.phone.fore_app()
            except Exception:  # noqa: BLE001 - a phone that cannot say is not a reason to raise here
                package = ""
            if package != PLAY_PACKAGE:
                return False
        deadline = time.monotonic() + 12.0
        button = _dismiss_control(elements)
        while button is None and time.monotonic() < deadline:
            time.sleep(1.5)
            button = _dismiss_control(self.screen.elements())
        if button is None:
            raise RuntimeError("Play's 'additional files' sheet is up but its Dismiss button never appeared")
        self.screen.tap(button)
        time.sleep(2.0)
        self._play_dismissals += 1
        if self._play_dismissals >= 4:
            raise RuntimeError(
                "Play's 'additional files' sheet keeps covering TikTok (4 times): the installed app is the "
                "base APK and has no dynamic modules - install the BUNDLE variant of 47.9.1 (same signer "
                "9041803e...cf2ab5ba) in this space, then log in again"
            )
        return True

    def _share_video(self, spec: PostSpec) -> bool:
        """Send the clip to TikTok's share activity; tap its Video button. False when that path is not there."""
        user = self.user
        self.phone.force_stop(self.package)
        time.sleep(0.5)
        self.phone.shell(
            f'am start --user {user} -a android.intent.action.SEND -t video/mp4 '
            f"--eu android.intent.extra.STREAM {spec.media_uri} "
            f"-n {self.package}/com.ss.android.ugc.aweme.share.SystemShareActivity",
            timeout=30,
        )
        try:
            elements = wait_for(self.screen, SHARE_ON_TIKTOK, 25)
        except ScreenTimeout:
            log.warning("tiktok: the share sheet did not appear; trying the camera's gallery")
            return False
        button = find_exact(elements, "Video") or find(elements, "Video")
        if button is None:
            return False
        self.screen.tap(button)
        return True

    def _open_gallery(self) -> None:
        """The camera's gallery entry: usually an 'Upload' label, else the square at the bottom left."""
        elements = self.screen.elements()
        for label in ("Upload", "Gallery", "Uploads"):
            button = find_exact(elements, label) or find(elements, label)
            if button is not None:
                self.screen.tap(button)
                return
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.10), int(height * 0.72))

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
        """Section 6.6: try a trending sound; if it fails, post without one (unless it is required)."""
        if spec.sound != "trending":
            return
        from .. import sound

        added = sound.add_sound(self.screen, "tiktok")
        self.sound_added = added
        if added:
            log.info("tiktok: a trending sound was added")
            return
        if spec.sound_required:
            raise RuntimeError("a trending sound is required but could not be added")
        log.warning("tiktok: no sound could be added; posting without one")

    def _write_caption(self, spec: PostSpec) -> None:
        """One paste of the whole caption, then read it back.

        Typing the hashtags one by one and picking TikTok's suggestions looked realistic but went wrong here:
        the field ended up missing its first line. A single set_text is exact, keeps the line breaks and the
        emoji, and is what a paste does anyway. The field is read back, so a half-written caption cannot post.
        """
        elements = self.screen.elements()
        field = (
            find(elements, "Add description")
            or find(elements, "Describe your video")
            or find(elements, "caption")
            or find(elements, "description")
        )
        if field is None:
            raise RuntimeError("the caption field is not on the post screen")
        self.screen.tap(field)
        time.sleep(0.8)
        wanted = spec.full_caption
        flat_wanted = wanted.replace("\n", "").replace("\r", "").lower()
        head, tail = flat_wanted[:20], flat_wanted[-20:]
        for attempt in (0, 1):
            try:
                self.screen.clear_field()
            except Exception:  # noqa: BLE001 - an empty field may refuse a clear
                pass
            self.screen.set_text(wanted)
            time.sleep(1.0)
            actual = (self.screen.focused_text() or "").strip()
            flat_actual = actual.replace("\n", "").replace("\r", "").lower()
            # The box scrolls to the end while the keyboard is up, so only its tail may be readable.
            if actual and (head in flat_actual or tail in flat_actual):
                return
            if not actual:
                # Some fields report no text while focused; the screen's own text is the fallback check.
                page = " ".join(e.text for e in self.screen.elements()).replace("\n", "").lower()
                if head in page or tail in page:
                    return
            log.warning("tiktok: the caption did not stick (attempt %d): %r", attempt + 1, actual[:60])
        raise RuntimeError("the caption could not be written into the post screen")

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
        """The upload overlay: up to 5 minutes (§6.4 step 10). Done when the feed is back."""
        deadline = time.monotonic() + 300
        saw_overlay = False
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            text = " ".join(e.text + " " + e.desc for e in elements).lower()
            if any(word in text for word in ("uploading", "uploaded", "posting", "processing")):
                saw_overlay = True
            elif HOME.matches(elements) or PROFILE.matches(elements):
                return  # back on the feed: the overlay finished (or never had time to show)
            time.sleep(2.0)
        raise RuntimeError("the upload overlay did not finish")

    def _read_link(self) -> str | None:
        """Profile → newest video → Share → Copy link, then read the clipboard (§6.4 step 11).

        Measured on trill 47.8.3: the profile's first tile sits at about (16 %, 40 %) of the screen; the share
        arrow carries the description "Share video. N shares"; the share sheet's "Copy link" is the first entry.
        """
        if not self._tap_nav("Profile"):
            self._tap_desc("Profile")
        wait_for(self.screen, PROFILE, 20)
        time.sleep(1.5)
        width, height = self.screen.size()
        self.phone.tap(int(width * 0.16), int(height * 0.40))  # newest tile, top-left of the grid
        time.sleep(3.5)
        if not self._tap_share():
            self._shot("tiktok-share")
            raise RuntimeError("the Share button is not on the video")
        wait_for(self.screen, SHARE_SHEET, 20)
        for attempt in range(3):
            button = find(self.screen.elements(), "Copy link")
            if button is not None:
                self.screen.tap(button)
                break
            time.sleep(1.0)
        else:
            raise RuntimeError("'Copy link' is not in the share sheet")
        time.sleep(1.5)
        return self._clipboard()

    def _tap_share(self) -> bool:
        """The share arrow on a video: its label is "Share video. 1,338 shares", so match on the prefix."""
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for element in self.screen.elements():
                label = (element.desc or element.text or "").strip().lower()
                if label == "share" or label.startswith("share video"):
                    self.screen.tap(element)
                    return True
            time.sleep(1.0)
        return False

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
        """Wait for a button before tapping it: TikTok's screens animate in, and a single read is too early."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            button = find_exact(self.screen.elements(), label)
            if button is not None:
                self.screen.tap(button)
                return
            time.sleep(1.0)
        raise RuntimeError(f"the '{label}' button is not on screen")

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
