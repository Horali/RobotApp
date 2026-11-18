"""G2G's sittings in the owner user (PLAN section 3.3, step 7).

G2G is the one brand that lives in the owner user: Indonesian, no proxy (never a VPN on user 0),
its TikTok (trill) and YouTube already logged in by hand. The robot never logs G2G in - it only
posts. The owner user is shared with the user's own apps, so the sitting is wrapped:

  - the leak check is G2G's own (no VPN up, an Indonesian exit, Jakarta time, no SIM);
  - Do Not Disturb goes on during the sitting and back to the user's setting after;
  - the sitting happens on Jakarta time (the robot switches the zone back before it starts);
  - the owner user is left in front, no space open, as every other script expects.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import leakcheck, sitting as sitting_module
from .adb import Phone
from .journal import Journal
from .leakcheck import LeakResult
from .post.base import PostResult
from .sitting import Sitting
from .secrets import Chameleon
from .ui import Screen

log = logging.getLogger("robotapp")

DND_KEY = "zen_mode"
G2G_APPS = ("com.ss.android.ugc.trill", "com.google.android.youtube")


class G2GSitting:
    def __init__(self, phone: Phone, screen: Screen, journal: Journal, chameleon: Chameleon,
                 emit=None, shots_dir: Path | None = None) -> None:
        self.phone = phone
        self.screen = screen
        self.journal = journal
        self.chameleon = chameleon
        self.emit = emit or (lambda event: None)
        self.shots_dir = shots_dir

    def run(self, sitting: Sitting, dry_run: bool = False) -> tuple[LeakResult | None, list[PostResult]]:
        """One G2G sitting: check the owner user, then post, then put everything back.

        A failed check posts nothing: the sitting reports it and the posts wait.
        """
        self.emit({"t": "step", "job": sitting.job_id, "name": "g2g check"})
        before_dnd = self._dnd_on()

        leak: LeakResult | None = None
        results: list[PostResult] = []
        try:
            # G2G's own check: no VPN in the owner user, an Indonesian exit, Jakarta, no SIM.
            leak = leakcheck.check_g2g(self.phone, self.screen, self.shots_dir)
            self.emit({"t": "leakcheck", **leak.as_dict()})
            if not leak.ok:
                for spec in sitting.posts:
                    result = PostResult(spec.upload_id, spec.platform, "failed_before_post",
                                        reason="; ".join(leak.problems))
                    self.emit(result.as_event())
                    results.append(result)
                    self.journal.mark(sitting.job_id, "failed_before_post", spec.upload_id, spec.platform,
                                      {"reason": "g2g check failed"})
                return leak, results

            # The sitting itself is the shared one (TikTok -> YouTube, in the sitting's order).
            results = sitting_module.run(
                sitting, self.phone, self.screen, self.journal, self.chameleon, self.emit,
                shots_dir=self.shots_dir, dry_run=dry_run,
            )
            return leak, results
        finally:
            self._dnd_restore(before_dnd)
            # Leave the owner user in front with no app in the way.
            for package in G2G_APPS:
                try:
                    self.phone.force_stop(package, user=0)
                except Exception:  # noqa: BLE001
                    pass

    # -- Do Not Disturb --------------------------------------------------------------------------
    def _dnd_on(self) -> str:
        """DND on for the sitting; the previous value goes back after (the user's own setting)."""
        try:
            before = self.phone.settings_get("global", DND_KEY, 0).strip()
            self.phone.settings_put("global", DND_KEY, "1", 0)
            return before
        except Exception:  # noqa: BLE001 - a phone that refuses keeps its own way
            return ""

    def _dnd_restore(self, before: str) -> None:
        if not before:
            return
        try:
            self.phone.settings_put("global", DND_KEY, before or "0", 0)
        except Exception:  # noqa: BLE001
            pass
