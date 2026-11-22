"""Getting the clip into a space's gallery (PLAN §6.1) and the sing-box profile (PLAN §4.4)."""

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from robotapp.fake import FakePhone, fake_guard
from robotapp.log import Secret
from robotapp.media import media_store, push_video, video_length
from robotapp.vpn import Proxy, build_config, import_link, serve_once


def test_the_owner_users_clip_is_pushed_and_indexed(tmp_path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"fake video")
    phone = FakePhone(guard=fake_guard())
    remote = push_video(phone, clip, 0)                     # G2G's owner user: a plain adb push
    assert remote.startswith("/storage/emulated/0/DCIM/Robot/robot-")
    assert remote.endswith(".mp4")
    assert phone.pushes == [(str(clip), remote)]
    assert any("MEDIA_SCANNER_SCAN_FILE" in command or "am broadcast" in command for command in phone.commands)


def test_a_secondary_users_clip_goes_in_through_that_spaces_browser(tmp_path, monkeypatch) -> None:
    """SELinux refuses `adb push` into another user's storage (“/storage/emulated/11: Permission
    denied”, measured 2026-11-20), so the space's own Chrome downloads the clip instead: the only
    writer that has that user's storage."""
    from robotapp import media as media_module

    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"fake video")
    phone = FakePhone(guard=fake_guard())

    class Serving:
        def __enter__(self):
            return "http://192.168.1.16:9999/clip.mp4"

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(media_module, "_serve_file", lambda *a, **k: Serving())
    monkeypatch.setattr("time.sleep", lambda s: None)
    seen = {"n": 0}

    def fake_uri(ph, user, remote):
        seen["n"] += 1
        return "content://media/external/video/media/7" if seen["n"] > 1 else None

    monkeypatch.setattr(media_module, "find_media_uri", fake_uri)
    remote = media_module.push_video(phone, clip, 11, name="clip.mp4")
    assert remote == "/storage/emulated/11/Download/clip.mp4"
    # the file is reached over device loopback (a LAN address would go through the space's VPN)
    assert any(c.startswith("reverse tcp:") for c in phone.commands)
    assert any("am start --user 11" in c and "http://127.0.0.1:" in c for c in phone.commands)
    assert phone.pushes == []                               # no adb push was attempted

    # the URL's port and the reverse port match: the browser reaches the laptop, not the LAN
    import re

    start = next(c for c in phone.commands if "am start --user 11" in c)
    url_port = re.search(r"127\.0\.0\.1:(\d+)", start).group(1)
    assert any(c == f"reverse tcp:{url_port} tcp:{url_port}" for c in phone.commands)


def test_a_missing_clip_is_an_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        push_video(FakePhone(guard=fake_guard()), tmp_path / "nope.mp4", 11)


def test_media_store_is_per_user() -> None:
    assert media_store(11) == "/storage/emulated/11"


def test_video_length_without_ffprobe_is_unknown(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("robotapp.media.shutil.which", lambda name: None)
    assert video_length(tmp_path / "x.mp4") is None


def test_an_http_proxy_becomes_an_http_outbound() -> None:
    config = build_config(Proxy("208.214.162.185", 50100, "user1", Secret("proxy-pass"), "http"))
    outbound = config["outbounds"][0]
    assert outbound["type"] == "http"
    assert outbound["server"] == "208.214.162.185"
    assert outbound["server_port"] == 50100
    assert outbound["username"] == "user1"
    assert outbound["password"] == "proxy-pass"  # the config must carry it: sing-box needs it
    assert config["route"]["final"] == "proxy"
    assert any(rule.get("protocol") == "quic" for rule in config["route"]["rules"])


def test_a_socks_proxy_becomes_a_socks_outbound() -> None:
    config = build_config(Proxy("1.2.3.4", 50101, "u", Secret("p"), "socks5"))
    assert config["outbounds"][0]["type"] == "socks"
    assert config["outbounds"][0]["version"] == "5"


def test_dns_rides_https_through_the_proxy_never_port_53() -> None:
    """Measured through the Virginia proxy on 2026-11-20: CONNECT to :443 answers 200, CONNECT to
    :53 answers 403 - the proxy blocks DNS on port 53. With the old tcp/53 DNS no hostname resolved
    (Google's account-add said "Something went wrong" while raw-IP pages still loaded), so the DNS
    must go over HTTPS on 443, through the proxy."""
    config = build_config(Proxy("208.214.162.185", 50100, "u", Secret("p"), "http"))
    (server,) = config["dns"]["servers"]
    assert server["type"] == "https"
    assert server["server_port"] == 443
    assert server["path"] == "/dns-query"
    assert server["detour"] == "proxy"          # never the home connection: that would leak DNS
    assert config["dns"]["final"] == "proxy-dns"
    assert all(s.get("server_port") != 53 for s in config["dns"]["servers"])


def test_a_dropped_adb_says_the_vpn_is_down_instead_of_crashing() -> None:
    """Seen 2026-11-20: `dumpsys` answered 'error: closed' mid-job and the whole command died. An
    unreadable phone must read as 'not up', which every caller already handles."""
    from robotapp.vpn import vpn_state

    class DroppedPhone:
        def shell(self, command: str, timeout: int = 60) -> str:
            raise RuntimeError("adb failed (1): error: closed")

        def settings_get(self, namespace: str, key: str, user: int) -> str:
            return ""

    state = vpn_state(DroppedPhone(), 11)
    assert state["up"] is False and "could not read" in str(state["detail"])


def test_the_import_confirmation_is_answered_before_the_profile_list_counts() -> None:
    """SFA asks "Are you sure to import remote profile <host>?" and the profile list behind that
    dialog stays readable. A plain "Profiles is on screen" check answered yes, left the dialog
    unanswered and the space got no tunnel (on the phone, 2026-11-20)."""
    from robotapp.ui import Element
    from robotapp.vpn import sfa_import

    def el(text: str) -> Element:
        return Element(text=text, bounds=(0, 1400, 1080, 1560), clickable=True)

    class ImportScreen:
        def __init__(self) -> None:
            self.dialog = True
            self.taps: list[str] = []

        def elements(self) -> list[Element]:
            rows = [Element(text="Profiles", bounds=(0, 100, 1080, 200))]   # behind the dialog
            if self.dialog:
                rows += [el("Are you sure to import remote profile 192.168.1.16:50877?"),
                         el("Cancel"), el("OK")]
            return rows

        def tap(self, element) -> None:
            self.taps.append(element.text or "")
            if (element.text or "") == "OK":
                self.dialog = False

    screen = ImportScreen()
    phone = FakePhone(guard=fake_guard())
    assert sfa_import(phone, screen, "http://192.168.1.16:50877/tok/config.json", 11) is True
    assert screen.taps, "the dialog was never answered"
    assert screen.taps[0] == "OK"


def test_the_import_link_encodes_the_url() -> None:
    link = import_link("http://192.168.1.5:8080/tok/config.json")
    assert link.startswith("sing-box://import-remote-profile?url=")
    assert ":" not in link.split("url=")[1]
    assert "%3A" in link


def test_the_config_is_served_once_at_a_random_path() -> None:
    config = {"log": {"level": "warn"}}
    with serve_once(config, seconds=5) as (url, served):
        body = json.loads(urllib.request.urlopen(url, timeout=5).read())
        assert body == config
        assert served["done"] is True
        base = url.rsplit("/", 2)[0]
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(base + "/config.json", timeout=5)
        assert caught.value.code == 404


def test_vpn_state_matches_only_the_requested_user() -> None:
    """User 10's connected tunnel must not make user 12 look connected (measured 2026-11-23)."""
    from robotapp.vpn import vpn_state

    connectivity = (
        "  4: VpnNetworkProvider:0\n"
        "  35: VpnNetworkProvider:10\n"
        "  34: VpnNetworkProvider:12\n"
        "  NetworkAgentInfo{network{153} ni{VPN CONNECTED extra: } "
        "Uids: <{1000000-1099999}> OwnerUid: 1010238 AdminUids: [1010238]}\n"
    )
    phone = FakePhone(guard=fake_guard())
    phone.expect(r"dumpsys connectivity", connectivity)
    phone.expect(r"settings get --user 10 secure always_on_vpn_app", "io.nekohasekai.sfa")
    phone.expect(r"settings get --user 10 secure always_on_vpn_lockdown", "1")
    phone.expect(r"settings get --user 12 secure always_on_vpn_app", "io.nekohasekai.sfa")
    phone.expect(r"settings get --user 12 secure always_on_vpn_lockdown", "1")
    phone.expect(r"settings get --user 11 secure always_on_vpn_app", "io.nekohasekai.sfa")
    phone.expect(r"settings get --user 11 secure always_on_vpn_lockdown", "1")

    assert vpn_state(phone, 10)["up"] is True
    assert vpn_state(phone, 12)["up"] is False
    assert vpn_state(phone, 11)["up"] is False


def test_vpn_state_still_accepts_output_without_uids() -> None:
    from robotapp.vpn import vpn_state

    phone = FakePhone(guard=fake_guard())
    phone.expect(r"dumpsys connectivity", "NetworkAgentInfo{ni{VPN CONNECTED}}")
    phone.expect(r"settings get --user 11 secure always_on_vpn_app", "io.nekohasekai.sfa")
    phone.expect(r"settings get --user 11 secure always_on_vpn_lockdown", "1")
    assert vpn_state(phone, 11)["up"] is True


def test_sfa_import_raises_on_error_dialog_instead_of_tapping_ok() -> None:
    from robotapp.ui import Element
    from robotapp.vpn import sfa_import

    def el(text: str) -> Element:
        return Element(text=text, bounds=(0, 1400, 1080, 1560), clickable=True)

    class ErrorScreen:
        def __init__(self) -> None:
            self.taps: list[str] = []

        def elements(self) -> list[Element]:
            return [el("Error"), el("connect: connection refused"), el("OK")]

        def tap(self, element) -> None:
            self.taps.append(element.text or "")

    screen = ErrorScreen()
    phone = FakePhone(guard=fake_guard())
    with pytest.raises(RuntimeError, match="import failed"):
        sfa_import(phone, screen, "http://127.0.0.1:50877/tok/config.json", 10)
    assert "OK" not in screen.taps


def test_setup_vpn_uses_adb_reverse_loopback_for_import(monkeypatch) -> None:
    from robotapp.cli import setup_vpn
    from robotapp.config import Settings
    from robotapp.fake import FakeScreen
    from robotapp.vpn import SFA_PACKAGE, vpn_state as real_vpn_state  # noqa: F401
    import robotapp.vpn as vpn_module

    phone = FakePhone(guard=fake_guard())
    imported_urls: list[str] = []

    class FakeChameleon:
        def proxy(self, proxy_id: str) -> dict:
            return {
                "host": "65.195.107.138",
                "port": 50100,
                "username": "u",
                "password": Secret("p"),
                "protocol": "http",
            }

    def fake_sfa_import(ph, scr, url, user, emit):
        imported_urls.append(url)
        urllib.request.urlopen(url, timeout=5).read()
        return True

    monkeypatch.setattr(vpn_module, "sfa_import", fake_sfa_import)
    monkeypatch.setattr(
        vpn_module,
        "vpn_state",
        lambda ph, u: {"up": True, "always_on_app": "io.nekohasekai.sfa", "lockdown": True, "detail": "ok"},
    )
    monkeypatch.setattr("time.sleep", lambda s: None)

    events: list[dict] = []
    state = setup_vpn(phone, FakeScreen(), FakeChameleon(), Settings(), 10, "proxy-1", events.append)
    assert state["up"] is True
    assert imported_urls and imported_urls[0].startswith("http://127.0.0.1:")
    assert any(c.startswith("reverse tcp:") for c in phone.commands)
    assert any("settings delete --user 10 secure always_on_vpn_app" in c for c in phone.commands)
    assert any(f"pm clear --user 10 {SFA_PACKAGE}" in c for c in phone.commands)
    assert phone.commands.count(f"am force-stop --user 10 {SFA_PACKAGE}") >= 2
    assert f"monkey -p {SFA_PACKAGE} --user 10 1" in phone.commands
    assert any(e.get("name") == "profile import" and e.get("fetched") is True and str(e.get("url_host", "")).startswith("127.0.0.1:") for e in events)


def test_tap_start_ignores_disconnected_vpn_notification() -> None:
    from robotapp.cli import _tap_start_if_present
    from robotapp.ui import Element

    class RecordingScreen:
        def __init__(self, elems: list[Element]) -> None:
            self._elems = elems
            self.taps: list[Element] = []

        def elements(self) -> list[Element]:
            return self._elems

        def tap(self, element: Element) -> None:
            self.taps.append(element)

    notif = Element(
        text="",
        desc="Android System notification: Disconnected from always-on VPN",
        bounds=(204, 30, 252, 78),
        enabled=True,
    )
    dash = Element(text="Dashboard", bounds=(0, 2200, 270, 2350), clickable=True)
    events: list[dict] = []
    screen1 = RecordingScreen([notif, dash])
    _tap_start_if_present(screen1, events.append)
    assert screen1.taps == [dash]
    assert events[-1].get("label") == "Dashboard"

    start_fab = Element(text="", desc="Start", bounds=(864, 1950, 1020, 2106), clickable=True)
    events2: list[dict] = []
    screen2 = RecordingScreen([notif, start_fab, dash])
    _tap_start_if_present(screen2, events2.append)
    assert screen2.taps == [start_fab]
    assert events2[-1].get("label") == "Start"

    enable_fab = Element(text="Enable", desc="", bounds=(864, 1950, 1020, 2106), clickable=True)
    events3: list[dict] = []
    screen3 = RecordingScreen([notif, enable_fab, dash])
    _tap_start_if_present(screen3, events3.append)
    assert screen3.taps == [enable_fab]
    assert events3[-1].get("label") == "Enable"
