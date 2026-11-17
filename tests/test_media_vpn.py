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


def test_the_clip_lands_in_the_spaces_gallery_and_is_indexed(tmp_path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"fake video")
    phone = FakePhone(guard=fake_guard())
    remote = push_video(phone, clip, 11)
    assert remote.startswith("/storage/emulated/11/DCIM/Robot/robot-")
    assert remote.endswith(".mp4")
    assert phone.pushes == [(str(clip), remote)]
    assert any("MEDIA_SCANNER_SCAN_FILE" in command or "am broadcast" in command for command in phone.commands)


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
