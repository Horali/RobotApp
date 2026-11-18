"""The leak check before every sitting (PLAN §4.5).

US space: the VPN must be up and locked, and the exit address must be the proxy's, in the US. G2G: no VPN at
all, and an Indonesian address. Both: no SIM, the right time zone, location off.

The IP is read inside the space, because the laptop's own adb commands do not use the phone's VPN: Chrome opens
`https://1.1.1.1/cdn-cgi/trace`, which prints `ip=` and `loc=` as plain text.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .adb import Phone
from .ui import Element, Screen, Signature, find, wait_for
from .vpn import vpn_state

CHROME = "com.android.chrome"
TRACE_URL = "https://1.1.1.1/cdn-cgi/trace"
DNS_URL = "https://browserleaks.com/dns"
WEBRTC_URL = "https://browserleaks.com/webrtc"

CHROME_FIRST_RUN = Signature(
    "chrome first run",
    any_of=(
        "Accept & continue",
        "Use without an account",
        "No thanks",
        "Welcome to Chrome",
        "Make Chrome your own",
        "Stay signed out",
    ),
)
CHROME_INTRO_LABELS = ("Stay signed out", "Accept & continue", "Use without an account", "No thanks", "Got it", "Not now")


@dataclass
class LeakResult:
    ok: bool
    ip: str | None = None
    loc: str | None = None
    problems: list[str] = field(default_factory=list)
    detail: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "ip": self.ip, "loc": self.loc, "problems": self.problems, "detail": self.detail}


def open_url(phone: Phone, user: int, url: str) -> None:
    phone.shell(f'am start --user {user} -a android.intent.action.VIEW -d "{url}" -p {CHROME}', timeout=30)


def page_text(screen: Screen) -> str:
    return "\n".join(f"{e.text}\n{e.desc}" for e in screen.elements() if e.text or e.desc)


def dismiss_chrome_intro(screen: Screen, timeout_s: float = 6.0) -> int:
    """Chrome's first-run screens (§4.2 step 11): up to three taps. Returns how many were dismissed."""
    dismissed = 0
    for _ in range(3):
        try:
            elements = wait_for(screen, CHROME_FIRST_RUN, timeout_s=timeout_s)
        except Exception:  # noqa: BLE001 - no intro is the normal case after the first time
            return dismissed
        for label in CHROME_INTRO_LABELS:
            button = find(elements, label)
            if button is not None:
                screen.tap(button)
                dismissed += 1
                time.sleep(1.5)
                break
        else:
            return dismissed
    return dismissed


def read_trace(phone: Phone, screen: Screen, user: int, timeout_s: float = 30.0) -> tuple[str | None, str | None, str]:
    """Open the Cloudflare trace page and read `ip=` and `loc=`. Returns (ip, loc, raw text)."""
    open_url(phone, user, TRACE_URL)
    dismiss_chrome_intro(screen)
    deadline_text = ""
    for _ in range(int(timeout_s)):
        deadline_text = page_text(screen)
        ip = re.search(r"\bip=([0-9a-fA-F:.]+)", deadline_text)
        loc = re.search(r"\bloc=([A-Z]{2})\b", deadline_text)
        if ip and loc:
            return ip.group(1), loc.group(1), deadline_text
        time.sleep(1.0)
    return None, None, deadline_text


def check_us(
    phone: Phone,
    screen: Screen,
    user: int,
    expected_ip: str | None = None,
    expected_zone: str = "America/New_York",
    shots_dir: Path | None = None,
) -> LeakResult:
    result = LeakResult(ok=False)
    state = vpn_state(phone, user)
    result.detail["vpn"] = state
    if not state["up"]:
        result.problems.append("the VPN is not up")
    if not state["lockdown"]:
        result.problems.append("lockdown is off (a dead proxy would leak the home IP)")
    if state["always_on_app"] not in ("", "null", "io.nekohasekai.sfa"):
        result.problems.append(f"always-on VPN is another app: {state['always_on_app']}")

    ip, loc, raw = read_trace(phone, screen, user)
    result.ip, result.loc = ip, loc
    if ip is None or loc is None:
        result.problems.append("could not read the trace page")
        if shots_dir:
            screen.screenshot(shots_dir / "leakcheck-trace.png")
    else:
        if loc != "US":
            result.problems.append(f"the exit is {loc}, not US")
        if expected_ip and ip != expected_ip:
            result.problems.append(f"the exit IP changed: {ip} (expected {expected_ip})")

    zone = phone.timezone()
    result.detail["timezone"] = zone
    if zone != expected_zone:
        result.problems.append(f"time zone is {zone}, not {expected_zone}")
    sim = phone.prop("gsm.sim.state")
    result.detail["sim"] = sim
    if "ABSENT" not in sim:
        result.problems.append(f"a SIM is present: {sim}")
    location = phone.settings_get("secure", "location_mode", user).strip()
    result.detail["location_mode"] = location
    if location not in ("0", "null", ""):
        result.problems.append(f"location is on (mode {location})")

    result.ok = not result.problems
    return result


def check_g2g(phone: Phone, screen: Screen, shots_dir: Path | None = None) -> LeakResult:
    """G2G: no VPN anywhere in the owner user, an Indonesian exit, Jakarta time, no SIM."""
    result = LeakResult(ok=False)
    vpn = phone.shell("dumpsys connectivity | grep -i -m2 vpn")
    result.detail["vpn"] = " ".join(vpn.split())[:200]
    if "VPN" in vpn.upper():
        result.problems.append("a VPN is up in the owner user")

    ip, loc, _ = read_trace(phone, screen, 0)
    result.ip, result.loc = ip, loc
    if loc is None:
        result.problems.append("could not read the trace page")
        if shots_dir:
            screen.screenshot(shots_dir / "leakcheck-g2g.png")
    elif loc != "ID":
        result.problems.append(f"the exit is {loc}, not ID")

    zone = phone.timezone()
    result.detail["timezone"] = zone
    if zone != "Asia/Jakarta":
        result.problems.append(f"time zone is {zone}, not Asia/Jakarta")
    sim = phone.prop("gsm.sim.state")
    result.detail["sim"] = sim
    if "ABSENT" not in sim:
        result.problems.append(f"a SIM is present: {sim}")

    result.ok = not result.problems
    return result


def deep_checks(phone: Phone, screen: Screen, user: int, shots_dir: Path | None = None) -> dict[str, str]:
    """DNS and WebRTC pages, kept as text + screenshots for a human look (§4.5 steps 3-4, once a day)."""
    out: dict[str, str] = {}
    for name, url in (("dns", DNS_URL), ("webrtc", WEBRTC_URL)):
        open_url(phone, user, url)
        time.sleep(8)
        out[name] = page_text(screen)[:4000]
        if shots_dir:
            screen.screenshot(shots_dir / f"leakcheck-{name}.png")
    return out
