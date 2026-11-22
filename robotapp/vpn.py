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
import re
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
    """A strict, leak-free profile: all traffic through the proxy, DNS through it, QUIC blocked.

    The format is sing-box 1.14's (the version SFA ships): DNS servers carry `type`/`server`/`server_port`
    because the legacy `address` form is rejected, and a blocked protocol is a route action (`reject`) because
    the `block` outbound no longer exists. A config this robot writes must be accepted by the installed app:
    the first version of this function was refused with "legacy DNS server formats are deprecated".

    **DNS rides HTTPS (DoH, port 443), not port 53.** Measured through the Virginia proxy on 2026-11-20:
    `CONNECT example.com:443` answers `200`, `CONNECT www.google.com:443` answers `200`, but
    `CONNECT 1.1.1.1:53` and `CONNECT 8.8.8.8:53` answer **403 Forbidden** - the proxy blocks DNS on port 53.
    With the old `tcp/53` DNS every hostname failed to resolve while raw-IP pages still loaded, which looked
    like a broken app (Google's account-add said "Something went wrong") and would have broken every post.
    """
    if proxy.protocol.lower().startswith("socks"):
        outbound: dict[str, object] = {
            "type": "socks",
            "tag": "proxy",
            "server": proxy.host,
            "server_port": int(proxy.port),
            "version": "5",
        }
    else:
        outbound = {"type": "http", "tag": "proxy", "server": proxy.host, "server_port": int(proxy.port)}
    if proxy.username:
        outbound["username"] = proxy.username
    if proxy.password is not None:
        outbound["password"] = proxy.password.reveal()
    return {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [
                {
                    "type": "https",
                    "tag": "proxy-dns",
                    "server": dns_server,
                    "server_port": 443,
                    "path": "/dns-query",
                    "detour": "proxy",
                }
            ],
            "final": "proxy-dns",
            "strategy": "ipv4_only",
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "address": ["172.19.0.1/30"],
                "auto_route": True,
                "strict_route": True,
                "stack": "system",
            }
        ],
        "outbounds": [outbound],
        "route": {
            # Measured 2026-11-22: a `{"network": "udp", "action": "reject"}` rule - which looked like
            # the correct way to refuse UDP cleanly - BROKE the tunnel's TCP in one space (every page
            # ERR_CONNECTION_REFUSED until the rule was rolled back; SFA 1.14). The old quic rule never
            # matches (protocol rules need sniffing, which this config never enables), so UDP falls
            # through to the proxy outbound and fails with a logged error instead. That is the state
            # every proven flow has run under - keep it until the UDP question is understood.
            "rules": [{"protocol": "quic", "action": "reject"}],
            "final": "proxy",
            "auto_detect_interface": True,
        },
    }


def lan_ip(phone_host: str = "") -> str:
    """The laptop's address on the phone's network.

    A laptop can have several (here: a Wi-Fi address and a hotspot adapter's 192.168.137.1). The phone can only
    reach the adapter that shares its subnet, so pick that one; fall back to the default route otherwise.
    """
    prefix = ".".join(phone_host.split(".")[:3]) + "." if phone_host.count(".") == 3 else ""
    try:
        addresses = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
    except OSError:
        addresses = []
    if prefix:
        for ip in addresses:
            if ip.startswith(prefix):
                return ip
    if addresses:
        return addresses[0]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((LAN_IP_HINT, 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


@contextmanager
def serve_once(config: dict, seconds: float = 60.0, phone_host: str = ""):
    """Serve the config at a random one-time path on the phone's network, then stop and forget it."""
    token = py_secrets.token_urlsafe(18)
    body = json.dumps(config).encode("utf-8")
    served = {"done": False}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - http.server naming
            if self.path != f"/{token}/config.json":
                self.send_error(404)
                return
            served["done"] = True  # the phone asked: the import link worked
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:  # never log the request path: it holds the token
            return

    server = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://{lan_ip(phone_host)}:{server.server_address[1]}/{token}/config.json"
        yield url, served
    finally:
        server.shutdown()
        server.server_close()


def import_link(url: str) -> str:
    """The deep link SFA understands for a remote profile (sing-box docs, clients/general)."""
    return "sing-box://import-remote-profile?url=" + urllib.parse.quote(url, safe="")


def import_profile(phone: Phone, url: str, user: int) -> None:
    link = import_link(url)
    phone.shell(
        f'am start --user {user} -a android.intent.action.VIEW -c android.intent.category.BROWSABLE '
        f'-d "{link}" -p {SFA_PACKAGE}',
        timeout=30,
    )


def sfa_import(phone: Phone, screen, url: str, user: int, emit=lambda event: None) -> bool:
    """Open the import link and walk SFA's screens: the confirm dialog, the update offer, the new profile.

    SFA 1.14 asks "Are you sure to import remote profile <host>?" before it fetches anything. The
    profile list behind that dialog stays readable to uiautomator2, so a plain "is Profiles on screen"
    check answered yes and left the dialog unanswered - the import never happened and the space had
    no tunnel (found on the phone, 2026-11-20). The dialog is answered first; "Profiles" only counts
    when no dialog is up. A config it refuses shows an "Error" dialog with the reason, surfaced verbatim.
    """
    import time

    from .ui import find, find_exact

    phone.force_stop(SFA_PACKAGE, user)
    time.sleep(1.0)
    import_profile(phone, url, user)
    seen: set[str] = set()
    for _ in range(40):
        time.sleep(1.0)
        elements = screen.elements()
        text = " ".join(e.text + " " + e.desc for e in elements)
        low = text.lower()
        if "decode config" in low or "parse config" in low:
            raise RuntimeError(f"sing-box refused the profile: {text.strip()[:300]}")

        # Android ANR or Infinix USB charging popups can cover SFA right after a user switch.
        if "isn't responding" in low:
            wait_btn = find_exact(elements, "Wait")
            if wait_btn is not None:
                screen.tap(wait_btn)
                time.sleep(1.5)
                continue
        usb_cancel = next(
            (e for e in elements if (e.text or "").startswith("Cancel(") or e.resource_id == "com.android.settings:id/btn_negative"),
            None,
        )
        if usb_cancel is not None:
            screen.tap(usb_cancel)
            time.sleep(1.0)
            continue

        # The remote-import confirmation, before anything else: its OK is the only way forward.
        if "are you sure to import" in low:
            button = find_exact(elements, "OK") or find(elements, "OK")
            if button is not None:
                if "import OK" not in seen:
                    emit({"t": "info", "name": "sfa", "tapped": "OK (import confirmation)"})
                    seen.add("import OK")
                screen.tap(button)
                time.sleep(1.5)
                continue

        # Surface SFA's own import errors instead of dismissing them with "OK".
        if any(word in low for word in ("error", "failed", "connection refused")) and find_exact(elements, "OK") is not None:
            raise RuntimeError(f"sing-box import failed: {text.strip()[:300]}")

        tapped = False
        for label in ("No, thanks", "Create", "Allow", "Done", "OK"):
            button = find_exact(elements, label) or find(elements, label)
            if button is not None:
                if label not in seen:
                    emit({"t": "info", "name": "sfa", "tapped": label})
                    seen.add(label)
                screen.tap(button)
                tapped = True
                break
        if tapped:
            continue
        if (
            find(elements, "Profiles") is not None
            or find(elements, "Dashboard") is not None
            or ("Create" in seen and find(elements, "Edit Profile") is not None)
        ):
            return True
    return False


def always_on(phone: Phone, user: int, package: str = SFA_PACKAGE) -> dict[str, str]:
    """Always-on VPN + block connections without VPN, per user. The system may ignore a plain `settings put`;
    the caller verifies and falls back to the Settings screen (§4.2 step 9)."""
    phone.settings_put("secure", "always_on_vpn_app", package, user)
    phone.settings_put("secure", "always_on_vpn_lockdown", "1", user)
    return {
        "always_on_vpn_app": phone.settings_get("secure", "always_on_vpn_app", user).strip(),
        "always_on_vpn_lockdown": phone.settings_get("secure", "always_on_vpn_lockdown", user).strip(),
    }


def clear_lockdown(phone: Phone, user: int) -> None:
    """Before importing a profile there must be no lockdown or active always-on app: either would
    keep or restart the old broken tunnel and block or swallow the new import."""
    try:
        phone.settings_put("secure", "always_on_vpn_lockdown", "0", user)
    except Exception:  # noqa: BLE001 - nothing to clear is fine
        pass
    try:
        phone.shell(f"settings delete --user {user} secure always_on_vpn_app")
    except Exception:  # noqa: BLE001 - nothing to clear is fine
        pass


def reset_sfa(phone: Phone, user: int) -> None:
    """Clear SFA's stored profiles and cached intents so only the newly imported profile exists."""
    try:
        phone.force_stop(SFA_PACKAGE, user)
    except Exception:  # noqa: BLE001 - best effort before clearing
        pass
    phone.shell(f"pm clear --user {user} {SFA_PACKAGE}")
    try:
        phone.appops(SFA_PACKAGE, "RUN_ANY_IN_BACKGROUND", "allow", user)
    except Exception:  # noqa: BLE001 - best effort
        pass


def _vpn_lines_for_user(connectivity: str, user: int) -> list[str]:
    """Filter `dumpsys connectivity` VPN lines to those belonging to `user`.

    Multiple Android spaces can hold separate VPN tunnels simultaneously; matching globally caused
    user 10's tunnel to mask user 12's disconnected VPN (`Service not started`).
    """
    uid_base = user * 100000
    matched: list[str] = []
    for line in connectivity.splitlines():
        if "VPN CONNECTED" not in line and "TRANSPORT_VPN" not in line:
            continue
        owner = re.search(r"OwnerUid:\s*(\d+)", line)
        if owner is not None:
            if int(owner.group(1)) // 100000 == user:
                matched.append(line.strip())
            continue
        uids = re.search(r"Uids:\s*<([^>]+)>", line)
        if uids is not None:
            ranges = re.findall(r"(\d+)-(\d+)", uids.group(1))
            if any(int(lo) <= uid_base <= int(hi) for lo, hi in ranges):
                matched.append(line.strip())
            continue
        # Minimal mock / older Android lines with no UID ownership still count as a match.
        matched.append(line.strip())
    return matched


def vpn_state(phone: Phone, user: int) -> dict[str, object]:
    """What the phone says about the VPN for that user: up, which app, and whether lockdown is on.

    A dropped adb connection ("error: closed", seen 2026-11-20) answers "not up" instead of raising:
    every caller treats a VPN it cannot see as down, and a crash there loses the whole job's report.
    """
    try:
        connectivity = phone.shell(
            "dumpsys connectivity | grep -i -E 'VPN CONNECTED|TRANSPORT_VPN|VpnNetworkProvider'"
        )
    except Exception as exc:  # noqa: BLE001 - an unreadable phone is not a working tunnel
        return {"up": False, "always_on_app": "", "lockdown": False, "detail": f"could not read it: {exc}"}
    matched = _vpn_lines_for_user(connectivity, user)
    up = bool(matched)
    try:
        app = phone.settings_get("secure", "always_on_vpn_app", user).strip()
        lockdown = phone.settings_get("secure", "always_on_vpn_lockdown", user).strip()
    except Exception as exc:  # noqa: BLE001
        return {"up": up, "always_on_app": "", "lockdown": False, "detail": f"settings unreadable: {exc}"}
    return {
        "up": up,
        "always_on_app": app,
        "lockdown": lockdown == "1",
        "detail": " ".join(" ".join((matched or [connectivity])[:2]).split())[:200],
    }
