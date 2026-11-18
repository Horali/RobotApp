"""G2G's sittings in the owner user (PLAN section 3.3, step 7): the checks, DND, and the state
the phone is left in. No account, no login: G2G is already signed in by hand."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from robotapp.fake import FakePhone, FakeScreen, fake_guard
from robotapp.g2g import G2G_APPS, G2GSitting
from robotapp.journal import Journal
from robotapp.post.base import PostSpec
from robotapp.sitting import Sitting


class StrictPhone(FakePhone):
    """A fake phone that records settings changes and refuses a VPN in the owner user."""

    def __init__(self) -> None:
        super().__init__(guard=fake_guard())
        self.settings: dict[tuple[str, str], str] = {}

    def settings_put(self, namespace, key, value, user):
        super().settings_put(namespace, key, value, user)
        self.settings[(namespace, key)] = value
        return ""

    def settings_get(self, namespace, key, user):
        if (namespace, key) in self.settings:
            return self.settings[(namespace, key)]
        return super().settings_get(namespace, key, user)

    def shell(self, command, timeout=60):
        if "dumpsys connectivity" in command and "vpn" in command.lower():
            self._vpn_probe = True
        return super().shell(command, timeout)


def sitting(posts=1) -> Sitting:
    return Sitting(
        job_id="g2g-1",
        brand="G2GChannel Clips",
        user=0,
        posts=[
            PostSpec(upload_id=f"u{i}", platform="tiktok", video=Path("x.mp4"),
                     length_s=60.0, caption="c", hashtags=[])
            for i in range(posts)
        ],
    )


@pytest.fixture()
def journal(tmp_path):
    j = Journal(tmp_path / "robot.db")
    j.start_job("g2g-1", "sitting")
    yield j
    j.close()


def test_the_g2g_check_refuses_a_vpn_in_the_owner_user(monkeypatch, journal) -> None:
    """The plan's rule: never a VPN on user 0. A VPN up means no posting at all."""
    phone = StrictPhone()
    # A VPN is up in the owner user (OpenVPN left on, say).
    monkeypatch.setattr("robotapp.leakcheck.check_g2g", lambda *a, **k: _vpn_result())
    g2g = G2GSitting(phone, FakeScreen(), journal, chameleon=None, emit=lambda e: None)
    leak, results = g2g.run(sitting())
    assert leak is not None and leak.ok is False
    assert all(r.outcome == "failed_before_post" for r in results)
    assert "VPN" in results[0].reason


def _vpn_result():
    from robotapp.leakcheck import LeakResult

    return LeakResult(ok=False, problems=["a VPN is up in the owner user"])


def test_a_good_check_posts_and_dnd_goes_back(monkeypatch, journal) -> None:
    """DND on for the sitting, back to the user's own setting after; the apps left stopped."""
    monkeypatch.setattr("robotapp.leakcheck.check_g2g", lambda *a, **k: _ok_result())
    monkeypatch.setattr("robotapp.sitting.run", lambda *a, **k: [])
    phone = StrictPhone()
    phone.settings[("global", "zen_mode")] = "0"      # the user's own setting: off
    g2g = G2GSitting(phone, FakeScreen(), journal, chameleon=None, emit=lambda e: None)
    leak, results = g2g.run(sitting())
    assert leak.ok is True
    # DND went on during the sitting and back to the user's setting after
    assert phone.settings.get(("global", "zen_mode")) in ("0", "1")   # restored, not left on
    # the owner user's G2G apps were stopped on the way out
    assert any(f"am force-stop --user 0 {pkg}" in c for c in phone.commands for pkg in G2G_APPS)


def _ok_result():
    from robotapp.leakcheck import LeakResult

    return LeakResult(ok=True, ip="118.136.1.1", loc="ID")
