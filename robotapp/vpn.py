"""The proxy: sing-box (SFA) config, import, always-on and lockdown (PLAN §4.4, §4.2 steps 7-9).

The config sends every packet to the brand's SOCKS5 proxy, answers DNS through the proxy over TCP, blocks QUIC
(UDP) so apps fall back to TCP and WebRTC cannot leak, and uses IPv4 only with `strict_route`. The proxy
password is written into the config at this moment, served once to the phone over the home network, and the
file is deleted immediately after: it is never logged and never kept.

The JSON keys move between sing-box versions, so `build_config` takes the installed version and the caller
checks the result on the phone (`sing-box check` is not available there; a broken profile shows as "not
started", which the leak check catches).
"""

from __future__ import annotations

import http.server
import json
import secrets as py_secrets
import socket
import threading
import urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .adb import Phone
from .log import Secret

SFA_PACKAGE = "io.nekohasekai.sfa"
LAN_IP_HINT = "8.8.8.8"  # a UDP "connect" tells us the LAN address without sending a packet


@dataclass
class Proxy:
    host: str
    port: int
    username: str = ""
    password: Secret | None = None
    protocol: str = "socks5"


def build_config(proxy: Proxy, dns_server: str = "1.1.1.1") -> dict:
    """A strict, leak-free profile: all traffic through the proxy, DNS through it, QUIC blocked."""
    outbound: dict[str, object] = {
        "type": "socks",
        "tag": "proxy",
        "server": proxy.host,
        "server_port": int(proxy.port),
        "version": "5",
    }
    if proxy.username:
        outbound["username"] = proxy.username
    if proxy.password is not None:
        outbound["password"] = proxy.password.reveal()
    return {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [{"tag": "proxy-dns", "address": f"tcp://{dns_server}", "detour": "proxy"}],
            "final": "proxy-dns",
            "strategy": "ipv4_only",
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "address": ["172.19.0.1/30"],
                "mtu": 9000,
                "auto_route": True,
                "strict_route": True,
                "stack": "system",
            }
        ],
        "outbounds": [
            outbound,
            {"type": "block", "tag": "block"},
        ],
        "route": {
            "rules": [{"protocol": "quic", "outbound": "block"}],
            "final": "proxy",
            "auto_detect_interface": True,
        },
    }


def lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((LAN_IP_HINT, 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


@contextmanager
def serve_once(config: dict, seconds: float = 60.0):
    """Serve the config at a random one-time path on the home network, then stop and forget it."""
    token = py_secrets.token_urlsafe(18)
    body = json.dumps(config).encode("utf-8")
    served = {"done": False}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server naming
            if self.path != f"/{token}/config.json":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            served["done"] = True

        def log_message(self, *args) -> None:  # never log the request path: it holds the token
            return

    server = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://{lan_ip()}:{server.server_address[1]}/{token}/config.json"
        yield url, served
    finally:
        server.shutdown()
        server.server_close()


def import_link(url: str) -> str:
    """The deep link SFA understands for a remote profile (sing-box docs, clients/general)."""
    return "sing-box://import-remote-profile?url=" + urllib.parse.quote(url, safe="")


def import_profile(phone: Phone, url: str, user: int) -> None:
    link = import_link(url)
    phone.shell(f'am start --user {user} -a android.intent.action.VIEW -d "{link}"', timeout=30)


def always_on(phone: Phone, user: int, package: str = SFA_PACKAGE) -> dict[str, str]:
    """Always-on VPN + block connections without VPN, per user. The system may ignore a plain `settings put`;
    the caller verifies and falls back to the Settings screen (§4.2 step 9)."""
    phone.settings_put("secure", "always_on_vpn_app", package, user)
    phone.settings_put("secure", "always_on_vpn_lockdown", "1", user)
    return {
        "always_on_vpn_app": phone.settings_get("secure", "always_on_vpn_app", user).strip(),
        "always_on_vpn_lockdown": phone.settings_get("secure", "always_on_vpn_lockdown", user).strip(),
    }


def vpn_state(phone: Phone, user: int) -> dict[str, object]:
    """What the phone says about the VPN for that user: up, which app, and whether lockdown is on."""
    connectivity = phone.shell("dumpsys connectivity | grep -i -m4 vpn")
    app = phone.settings_get("secure", "always_on_vpn_app", user).strip()
    lockdown = phone.settings_get("secure", "always_on_vpn_lockdown", user).strip()
    return {
        "up": "VPN" in connectivity.upper(),
        "always_on_app": app,
        "lockdown": lockdown == "1",
        "detail": " ".join(connectivity.split())[:200],
    }
