"""Finding the phone again after a reboot (PLAN section 9, step 2), against a fake adb.

The fake adb is a small script that answers `devices`, `connect` and `mdns services` from a state
file, so the ordering (configured serial, then mDNS, then the cable fallback) is tested without a
phone — the same way FakePhone tests everything else.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from robotapp.reconnect import Reconnector, parse_mdns


SERVICES_OUTPUT = (
    "List of discovered mdns services\n"
    "adb-0953925324001286-5g4Eab\t_adb-tls-connect._tcp\t192.168.1.8:46841\n"
    "adb-tls-pairing._tcp\t_adb-tls-pairing._tcp\t192.168.1.8:46839\n"
)


def test_mdns_rows_are_parsed_and_filtered() -> None:
    services = parse_mdns(SERVICES_OUTPUT)
    assert len(services) == 2
    connect = [s for s in services if s.kind == "_adb-tls-connect._tcp"]
    assert connect and connect[0].address == "192.168.1.8:46841"


def test_mdns_noise_is_ignored() -> None:
    assert parse_mdns("List of discovered mdns services\n\nsome garbage\n") == []
    assert parse_mdns("") == []


class FakeAdb:
    """A tiny adb: the state (which serials are connected) lives in a JSON file."""

    def __init__(self, path: Path, state: dict) -> None:
        self.path = path
        self.path.write_text(json.dumps(state), encoding="utf-8")
        self.calls: list[str] = []

    def script(self) -> str:
        return str(Path(__file__).parent / "fake_adb.py")


@pytest.fixture()
def fake_adb(tmp_path):
    def make(state: dict) -> tuple[FakeAdb, Reconnector]:
        fake = FakeAdb(tmp_path / "state.json", state)
        reconnector = Reconnector(tmp_path / "adb.exe")
        original_run = subprocess.run

        def patched(*args, **kwargs):
            fake.calls.append(" ".join(args))
            done = original_run(
                [sys.executable, fake.script(), str(fake.path), " ".join(args)],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return done.returncode, (done.stdout + done.stderr).strip()

        reconnector._adb = patched
        return fake, reconnector

    return make


def test_the_configured_serial_wins(fake_adb) -> None:
    fake, r = fake_adb({"devices": ["192.168.1.8:5555"]})
    assert r.reconnect("192.168.1.8:5555") == "192.168.1.8:5555"
    assert "connect" not in " ".join(fake.calls)  # already there: no connect attempt at all


def test_mdns_finds_the_phone_after_a_reboot(fake_adb) -> None:
    # The old TCP port is gone; Wireless debugging is on a new random port.
    fake, r = fake_adb(
        {
            "devices": [],
            "connect": {"192.168.1.8:5555": False, "192.168.1.8:46841": True},
            "mdns": SERVICES_OUTPUT,
        }
    )
    assert r.reconnect("192.168.1.8:5555") == "192.168.1.8:46841"
    calls = " ".join(fake.calls)
    assert "mdns services" in calls  # it looked before giving up


def test_no_phone_and_no_cable_is_an_empty_answer(fake_adb) -> None:
    fake, r = fake_adb({"devices": [], "connect": {}, "mdns": "List of discovered mdns services\n"})
    assert r.reconnect("192.168.1.8:5555") == ""


def test_the_cable_fallback_sets_tcpip(fake_adb) -> None:
    fake, r = fake_adb(
        {
            "devices": ["0953925324001286"],  # the phone on USB, Wi-Fi adb gone (rebooted)
            "connect": {"192.168.1.8:5555": False, "192.168.1.8:5555-after-tcpip": True},
            "mdns": "List of discovered mdns services\n",
        }
    )
    # The TCP port comes back on the same address; the fake flips it on after `tcpip 5555` runs.
    calls: list[str] = []
    original = r._adb

    def patched(*args, **kwargs):
        calls.append(" ".join(args))
        code, out = original(*args)
        if "tcpip 5555" in calls[-1]:
            state = json.loads(fake.path.read_text())
            state["connect"]["192.168.1.8:5555"] = True  # the port is open again after tcpip
            fake.path.write_text(json.dumps(state), encoding="utf-8")
        return code, out

    r._adb = patched
    assert r.reconnect("192.168.1.8:5555") == "192.168.1.8:5555"
    assert any("tcpip 5555" in call for call in calls)
