"""A phone that answers from a script, so most of the robot can be tested without the real one.

`FakePhone` speaks the same interface as `AdbPhone`. A test registers the answers it wants
(`phone.expect(r"getprop ro.product.model", "Infinix X6815D")`) and then asserts on `phone.commands`.
The guard is real, so a test that runs outside 06:00-10:00 WIB fails the same way the robot would.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .adb import Battery, AndroidUser, parse_users
from .window import WIB, WindowGuard


class FakePhone:
    def __init__(self, guard: WindowGuard | None = None) -> None:
        self.serial = "fake:5555"
        self.guard = guard or WindowGuard()
        self.commands: list[str] = []
        self.pushes: list[tuple[str, str]] = []
        self.shots: list[Path] = []
        self.responses: list[tuple[re.Pattern[str], str]] = []
        self.default = ""
        # A small, believable phone: the owner plus one old secondary user to delete.
        self.user_rows = [
            "Users:",
            "\tUserInfo{0:Owner:13} running",
            "\tUserInfo{10:Brand:10} ",
            "\tUserInfo{999:Ruang Ganda:410} ",
        ]
        self.max_user_count = 4
        self.battery_level = 85
        self.battery_temp = 405  # 40.5 °C, as measured on the real phone
        self.zone = "Asia/Jakarta"
        self.current = 0
        self.versions = {"com.zhiliaoapp.musically": "39.5.4", "com.ss.android.ugc.trill": "47.8.3"}

    # -- fixture helpers ---------------------------------------------------------------------------
    def expect(self, pattern: str, output: str) -> "FakePhone":
        self.responses.append((re.compile(pattern), output))
        return self

    def _answer(self, command: str) -> str:
        for pattern, output in self.responses:
            if pattern.search(command):
                return output
        return self.default

    # -- the Phone interface -----------------------------------------------------------------------
    def online(self) -> bool:
        self.guard.check("check the phone")
        self.commands.append("get-state")
        return True

    def shell(self, command: str, timeout: int = 60) -> str:
        self.guard.check("run a shell command")
        self.commands.append(command)
        if command.startswith("cmd user list"):
            return "\n".join(self.user_rows)
        if command.startswith("pm get-max-users"):
            return f"Maximum supported users: {self.max_user_count}"
        if command.startswith("dumpsys battery"):
            return f"Current Battery Service state:\n  level: {self.battery_level}\n  temperature: {self.battery_temp}\n  status: 2"
        if command.startswith("am get-current-user"):
            return str(self.current)
        if command.startswith("cmd alarm set-timezone"):
            self.zone = command.split()[-1]
            return ""
        if command.startswith("getprop persist.sys.timezone"):
            return self.zone
        if command.startswith("pm list packages"):
            user = int(command.split("--user")[-1].strip())
            return "\n".join(f"package:{p}" for p in self.versions) if user else ""
        if command.startswith("dumpsys package"):
            package = command.split()[2]
            version = self.versions.get(package)
            return f"versionName={version}" if version else ""
        if command.startswith("pm create-user"):
            name = command.split('"')[1]
            ids = [int(m.group(1)) for row in self.user_rows if (m := re.search(r"\{(\d+):", row))]
            new_id = (max(ids) if ids else 0) + 1
            self.user_rows.append(f"\tUserInfo{{{new_id}:{name}:10}} ")
            return f"Success: created user id {new_id}"
        return self._answer(command)

    def prop(self, name: str) -> str:
        if name == "persist.sys.timezone":
            return self.shell("getprop persist.sys.timezone")
        return self.shell(f"getprop {name}").strip()

    def push(self, local: Path, remote: str) -> None:
        self.guard.check("copy a file to the phone")
        self.pushes.append((str(local), remote))

    def pull(self, remote: str, local: Path) -> None:
        self.guard.check("copy a file from the phone")
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(b"fake")

    def screencap(self, local: Path) -> None:
        self.guard.check("take a screenshot")
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(b"\x89PNG fake")
        self.shots.append(local)

    def users(self) -> list[AndroidUser]:
        return parse_users(self.shell("cmd user list"))

    def battery(self) -> Battery:
        out = self.shell("dumpsys battery")
        level = re.search(r"level:\s*(\d+)", out)
        temp = re.search(r"temperature:\s*(\d+)", out)
        status = re.search(r"status:\s*(\d+)", out)
        assert level and temp
        return Battery(int(level.group(1)), int(temp.group(1)) / 10.0, status.group(1) if status else "?")

    def current_user(self) -> int:
        return int(self.shell("am get-current-user"))

    def max_users(self) -> int:
        m = re.search(r"(\d+)", self.shell("pm get-max-users"))
        return int(m.group(1)) if m else 0

    def timezone(self) -> str:
        return self.zone

    def package_version(self, package: str) -> str | None:
        return self.versions.get(package)

    def packages(self, user: int) -> list[str]:
        return sorted(line.split(":", 1)[1] for line in self.shell(f"pm list packages --user {user}").splitlines() if ":" in line)

    # -- actions (recorded; the state changes where it matters) --------------------------------------
    def create_user(self, name: str) -> int:
        out = self.shell(f'pm create-user --user-type android.os.usertype.full.SECONDARY "{name}"')
        return int(re.search(r"id (\d+)", out).group(1))  # type: ignore[union-attr]

    def remove_user(self, user_id: int) -> str:
        self.guard.check("remove a user")
        self.commands.append(f"pm remove-user {user_id}")
        self.user_rows = [r for r in self.user_rows if f"{{{user_id}:" not in r]
        return "Success: removed user"

    def start_user(self, user_id: int) -> str:
        self.guard.check("start a user")
        self.commands.append(f"am start-user {user_id}")
        return "Success: user started"

    def stop_user(self, user_id: int) -> str:
        self.guard.check("stop a user")
        self.commands.append(f"am stop-user -f {user_id}")
        return "Success: user stopped"

    def switch_user(self, user_id: int) -> str:
        self.guard.check("switch the foreground user")
        self.commands.append(f"am switch-user {user_id}")
        self.current = user_id
        return "Success: switched"

    def force_stop(self, package: str, user: int = 0) -> str:
        self.guard.check("force-stop an app")
        self.commands.append(f"am force-stop --user {user} {package}")
        return ""

    def start_app(self, package: str, user: int = 0) -> str:
        self.guard.check("open an app")
        self.commands.append(f"monkey -p {package} --user {user} 1")
        return "Events injected: 1"

    def install_existing(self, package: str, user: int) -> str:
        self.guard.check("install an app into a user")
        self.commands.append(f"pm install-existing --user {user} {package}")
        return "Package installed for user"

    def install_apk(self, path: Path) -> str:
        self.guard.check("install an app")
        self.commands.append(f"install -r {path}")
        return "Success"

    def install_multiple(self, paths: list[Path]) -> str:
        self.guard.check("install an app")
        self.commands.append("install-multiple " + " ".join(str(p) for p in paths))
        return "Success"

    def uninstall_for_user(self, package: str, user: int) -> str:
        self.guard.check("uninstall an app for a user")
        self.commands.append(f"pm uninstall --user {user} {package}")
        return "Success"

    def grant(self, package: str, permission: str, user: int) -> str:
        self.guard.check("grant a permission")
        self.commands.append(f"pm grant --user {user} {package} {permission}")
        return ""

    def appops(self, package: str, op: str, mode: str, user: int) -> str:
        self.guard.check("set an app-op")
        self.commands.append(f"appops set --user {user} {package} {op} {mode}")
        return ""

    def settings_put(self, namespace: str, key: str, value: str, user: int) -> str:
        self.guard.check("change a setting")
        self.commands.append(f"settings --user {user} put {namespace} {key} {value}")
        return ""

    def settings_get(self, namespace: str, key: str, user: int) -> str:
        self.commands.append(f"settings --user {user} get {namespace} {key}")
        return self._answer(f"settings --user {user} get {namespace} {key}")

    def set_timezone(self, zone: str) -> str:
        self.guard.check("change the time zone")
        self.zone = zone
        self.commands.append(f"cmd alarm set-timezone {zone}")
        return ""

    def tap(self, x: int, y: int) -> None:
        self.guard.check("tap the screen")
        self.commands.append(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 300) -> None:
        self.guard.check("swipe the screen")
        self.commands.append(f"input swipe {x1} {y1} {x2} {y2} {ms}")

    def scan_media(self, remote_path: str) -> str:
        self.guard.check("index a video")
        self.commands.append(f"am broadcast -d file://{remote_path}")
        return "Broadcast completed: result=0"


def fake_guard(moment: datetime | None = None) -> WindowGuard:
    """A guard frozen at a time inside the window (09:00 WIB by default), for tests and FakePhone runs."""
    fixed = moment or datetime(2026, 11, 18, 9, 0, tzinfo=WIB)
    return WindowGuard(clock=lambda: fixed)


class FakeScreen:
    """A screen whose contents a test sets by hand. Records taps, typing and screenshots."""

    def __init__(self, elements: list | None = None, clipboard: str | None = None) -> None:
        from .ui import Element

        self.current: list[Element] = elements or []
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.shots: list[Path] = []
        self._clipboard = clipboard
        self._size = (1080, 2400)

    def show(self, elements: list) -> "FakeScreen":
        self.current = elements
        return self

    def elements(self) -> list:
        return self.current

    def tap(self, element) -> None:
        self.taps.append(element.text or element.desc)

    def long_press(self, element) -> None:
        self.taps.append(f"long:{element.text or element.desc}")

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.typed.append(text)

    def type_secret(self, secret) -> None:
        self.typed.append(secret.reveal())

    def set_text(self, text: str) -> None:
        self.typed.append(text)

    def clear_field(self) -> None:
        self.typed.clear()

    def press_back(self) -> None:
        self.taps.append("back")

    def swipe_up(self) -> None:
        self.taps.append("swipe")

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG fake")
        self.shots.append(path)

    def size(self) -> tuple[int, int]:
        return self._size

    def clipboard(self) -> str | None:
        return self._clipboard

    def focused_text(self) -> str | None:
        return self.typed[-1] if self.typed else None
