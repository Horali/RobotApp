"""Finding the phone again after a reboot (PLAN section 9, step 2).

Old-style TCP adb (`adb tcpip 5555`) dies on every reboot: the port setting is not persistent.
Wireless debugging (the Android 11+ kind) is what survives, because Keeper turns it back on at
boot — but its port is random, so the laptop finds it by mDNS:

    adb mdns services
    adb-0953925324001286-5g4Eab   _adb-tls-connect._tcp   192.168.1.8:46841

This module is transport only: it runs `adb connect` and `adb mdns services`, never a shell
command, so it is safe to run while the phone belongs to other scripts.

Order: the configured serial first (works unless the phone rebooted), then mDNS, then the cable
fallback (`adb tcpip 5555` from a USB-connected phone).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

CONNECT_SERVICE = "_adb-tls-connect._tcp"


@dataclass
class Service:
    name: str
    kind: str
    address: str


def parse_mdns(output: str) -> list[Service]:
    """`adb mdns services` prints a header line, then `name\\tkind\\taddress` rows."""
    services: list[Service] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split("\t") if part.strip()]
        if len(parts) == 3 and "." in parts[2] and ":" in parts[2]:
            services.append(Service(parts[0], parts[1], parts[2]))
    return services


class Reconnector:
    def __init__(self, adb_path, timeout: float = 20.0) -> None:
        self.adb_path = str(adb_path)
        self.timeout = timeout

    def _adb(self, *args: str, timeout: float | None = None) -> tuple[int, str]:
        try:
            done = subprocess.run(
                [self.adb_path, *args], capture_output=True, text=True,
                timeout=timeout or self.timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, "timed out"
        return done.returncode, (done.stdout + done.stderr).strip()

    # -- the pieces --------------------------------------------------------------------------------
    def state_of(self, serial: str) -> str:
        """'device', 'offline', 'unauthorized' or '' (not listed)."""
        code, out = self._adb("devices")
        if code != 0:
            return ""
        for line in out.splitlines()[1:]:
            if not line.strip() or line.startswith("List of"):
                continue
            parts = line.split()
            if parts and parts[0] == serial:
                return parts[1] if len(parts) > 1 else ""
        return ""

    def connect(self, serial: str) -> bool:
        """`adb connect`, with a short timeout: a stale Wi-Fi address must not hang the whole job."""
        code, out = self._adb("connect", serial, timeout=5.0)
        if code != 0 or "cannot connect" in out.lower() or "failed" in out.lower() or "timed out" in out.lower():
            return False
        return self.state_of(serial) == "device"

    def mdns_services(self) -> list[Service]:
        code, out = self._adb("mdns", "services")
        return parse_mdns(out) if code == 0 else []

    def ensure_server(self) -> None:
        """`adb mdns` answers nothing until the local mdns daemon is up; a plain command wakes it."""
        self._adb("start-server")

    def tcpip_from_cable(self, configured_serial: str, usb_serial: str = "") -> bool:
        """The cable fallback (PLAN section 9): a USB-connected phone can be told `tcpip 5555`.

        `usb_serial` pins it to the robot phone: without it, a *different* phone on the cable
        (the user's S25+) would be switched to TCP mode by mistake.
        """
        code, out = self._adb("devices")
        if code != 0:
            return False
        usb = [
            line.split()[0]
            for line in out.splitlines()[1:]
            if line.strip()
            and not line.startswith("List of")
            and ":" not in line.split()[0]
            and (not usb_serial or line.split()[0] == usb_serial)
        ]
        if not usb:
            return False
        code, out = self._adb("-s", usb[0], "tcpip", "5555")
        return code == 0

    # -- the whole thing ---------------------------------------------------------------------------
    def find_phone(self, configured_serial: str) -> list[str]:
        """All the ways the phone can be reached, tried in order. Returns the connected serials.

        Never raises for an unreachable phone: an empty list is the answer "the phone is not
        reachable, plug the cable in".
        """
        connected: list[str] = []
        if self.state_of(configured_serial) == "device":
            connected.append(configured_serial)
            return connected
        if self.connect(configured_serial):
            connected.append(configured_serial)

        self.ensure_server()
        for service in self.mdns_services():
            if service.kind != CONNECT_SERVICE:
                continue
            if service.address in connected:
                continue
            if self.connect(service.address):
                connected.append(service.address)
        return connected

    def reconnect(self, configured_serial: str, cable_fallback: bool = True, usb_serial: str = "") -> str:
        """One serial, or an empty string. Tries everything, including the cable.

        The robot phone on USB comes first when it is there: the cable works whatever network this
        laptop is on, and a Wi-Fi address from the *home* network would otherwise hang for seconds.
        """
        if usb_serial and self.state_of(usb_serial) == "device":
            return usb_serial
        connected = self.find_phone(configured_serial)
        if connected:
            return connected[0]
        if cable_fallback and self.tcpip_from_cable(configured_serial, usb_serial=usb_serial):
            if self.connect(configured_serial):
                return configured_serial
        return ""
