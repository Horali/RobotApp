"""The phone, over adb.

One class talks to the real phone (`AdbPhone`); one stands in for it in tests (`FakePhone`, in fake.py). Both
implement `Phone`, and every phone method asks the `WindowGuard` first, so the 06:00-10:00 rule holds for every
caller — a job, the CLI, or a test that forgot to check.

adb output is kept short on purpose (§11: "keep adb output short"): helpers return what the caller needs, not
whole UI dumps.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .log import short
from .window import WindowGuard

ADB_TIMEOUT = 60


class AdbError(RuntimeError):
    """An adb command failed. The message carries the command and a short tail of its output."""

    def __init__(self, command: list[str], code: int, output: str) -> None:
        self.command = command
        self.code = code
        self.output = output
        super().__init__(f"adb failed ({code}): {' '.join(command[1:])} -> {short(output, 240)}")


@dataclass
class Battery:
    level: int
    temperature_c: float
    status: str

    @property
    def ok(self) -> bool:
        """PLAN §6.4 step 0: at least 30 % and below 42 °C before a sitting."""
        return self.level >= 30 and self.temperature_c < 42.0


@dataclass
class AndroidUser:
    id: int
    name: str
    running: bool

    @property
    def owner(self) -> bool:
        return self.id == 0


def parse_users(output: str) -> list[AndroidUser]:
    """`cmd user list` prints `UserInfo{<id>:<name>:<flags>} running`, one per line."""
    users: list[AndroidUser] = []
    for line in output.splitlines():
        match = re.search(r"UserInfo\{(\d+):([^:}]*):[^}]*\}(.*)$", line)
        if match:
            users.append(AndroidUser(int(match.group(1)), match.group(2).strip(), "running" in match.group(3)))
            continue
        match = re.match(r"\s*(\d+):\s*([^:]*):?\s*(running|not running)?\s*$", line)
        if match:
            users.append(AndroidUser(int(match.group(1)), match.group(2).strip(), match.group(3) == "running"))
    return users


class Phone(Protocol):
    serial: str

    def online(self) -> bool: ...
    def shell(self, command: str, timeout: int = ADB_TIMEOUT) -> str: ...
    def prop(self, name: str) -> str: ...
    def push(self, local: Path, remote: str) -> None: ...
    def pull(self, remote: str, local: Path) -> None: ...
    def reverse_port(self, device_port: int, host_port: int) -> str: ...
    def screencap(self, local: Path) -> None: ...
    def users(self) -> list[AndroidUser]: ...
    def battery(self) -> Battery: ...
    def current_user(self) -> int: ...
    def max_users(self) -> int: ...
    def timezone(self) -> str: ...
    def package_version(self, package: str) -> str | None: ...
    def packages(self, user: int) -> list[str]: ...


class AdbPhone:
    """The real phone. `serial` is `host:port` for Wi-Fi adb or a USB serial."""

    def __init__(self, adb: Path, serial: str, guard: WindowGuard | None = None) -> None:
        self.adb = Path(adb)
        self.serial = serial
        self.guard = guard or WindowGuard()

    # -- plumbing ----------------------------------------------------------------------------------
    def _run(self, args: list[str], timeout: int = ADB_TIMEOUT, binary_path: Path | None = None) -> str:
        command = [str(self.adb), "-s", self.serial, *args]
        if binary_path is not None:  # screencap: write the bytes straight to the file
            with binary_path.open("wb") as fh:
                done = subprocess.run(command, stdout=fh, stderr=subprocess.PIPE, timeout=timeout)
            if done.returncode != 0:
                raise AdbError(command, done.returncode, done.stderr.decode("utf-8", "replace"))
            return ""
        done = subprocess.run(command, capture_output=True, timeout=timeout)
        out = done.stdout.decode("utf-8", "replace")
        err = done.stderr.decode("utf-8", "replace")
        if done.returncode != 0:
            raise AdbError(command, done.returncode, (out + "\n" + err).strip())
        return out

    def online(self) -> bool:
        self.guard.check("check the phone")
        try:
            return self._run(["get-state"], timeout=20).strip() == "device"
        except (subprocess.TimeoutExpired, AdbError, FileNotFoundError):
            return False

    def shell(self, command: str, timeout: int = ADB_TIMEOUT) -> str:
        self.guard.check("run a shell command")
        return self._run(["shell", command], timeout=timeout)

    def prop(self, name: str) -> str:
        return self.shell(f"getprop {name}").strip()

    def push(self, local: Path, remote: str) -> None:
        self.guard.check("copy a file to the phone")
        self._run(["push", str(local), remote], timeout=300)

    def pull(self, remote: str, local: Path) -> None:
        self.guard.check("copy a file from the phone")
        local.parent.mkdir(parents=True, exist_ok=True)
        self._run(["pull", remote, str(local)], timeout=300)

    def reverse_port(self, device_port: int, host_port: int) -> str:
        """`adb reverse`: a port on the phone that reaches this laptop.

        The space's browser uses it to download a clip from the laptop. A LAN address would go
        through the space's VPN (the proxy cannot reach 192.168.x.x); device loopback does not.
        """
        self.guard.check("open a port back to the laptop")
        return self._run(["reverse", f"tcp:{device_port}", f"tcp:{host_port}"], timeout=30)

    def screencap(self, local: Path) -> None:
        self.guard.check("take a screenshot")
        local.parent.mkdir(parents=True, exist_ok=True)
        self._run(["exec-out", "screencap", "-p"], binary_path=local)

    # -- facts -------------------------------------------------------------------------------------
    def users(self) -> list[AndroidUser]:
        """`cmd user list` gives one line per user; the running ones are marked after the braces."""
        return parse_users(self.shell("cmd user list"))

    def battery(self) -> Battery:
        out = self.shell("dumpsys battery")
        level = re.search(r"level:\s*(\d+)", out)
        temp = re.search(r"temperature:\s*(\d+)", out)
        status = re.search(r"status:\s*(\d+)", out)
        if not level or not temp:
            raise AdbError(["dumpsys", "battery"], 1, out)
        return Battery(int(level.group(1)), int(temp.group(1)) / 10.0, status.group(1) if status else "?")

    def current_user(self) -> int:
        out = self.shell("am get-current-user").strip()
        return int(out) if out.isdigit() else 0

    def max_users(self) -> int:
        out = self.shell("pm get-max-users").strip()
        m = re.search(r"(\d+)", out)
        return int(m.group(1)) if m else 0

    def timezone(self) -> str:
        return self.prop("persist.sys.timezone")

    def fore_app(self) -> tuple[str, int]:
        """(package, Android user) of the app actually in front - from the display, not a cached value.

        `am get-current-user` answers what the phone *thinks*; this answers what is on the screen, which
        is what a tap hits. On 2026-11-19 the two disagreed and a read was blamed on the wrong account.

        `dumpsys window`'s mCurrentFocus is printed once per root task on this XOS build - a background
        user's window comes first and blamed the user's own Instagram while the space's TikTok was on
        screen (2026-11-19). `topResumedActivity` is one line and was proven right both ways on the
        phone (u11 musically in front; after `am switch-user 0`, u0)."""
        out = self.shell("dumpsys activity activities | grep -m1 topResumedActivity", timeout=20)
        # topResumedActivity=ActivityRecord{d7f682f u11 com.zhiliaoapp.musically/...SplashActivity} t1100032}
        m = re.search(r"u(\d+)\s+([\w.]+)/", out)
        return (m.group(2), int(m.group(1))) if m else ("", self.current_user())

    def package_version(self, package: str) -> str | None:
        """None when the app is not installed: `grep` finds nothing and adb exits 1, which is an answer too."""
        try:
            out = self.shell(f"dumpsys package {package} | grep -m1 versionName")
        except AdbError:
            return None
        m = re.search(r"versionName=(\S+)", out)
        return m.group(1) if m else None

    def packages(self, user: int) -> list[str]:
        out = self.shell(f"pm list packages --user {user}")
        return sorted(line.split(":", 1)[1].strip() for line in out.splitlines() if ":" in line)

    # -- actions -----------------------------------------------------------------------------------
    def create_user(self, name: str) -> int:
        self.guard.check("create a user")
        out = self.shell(f'pm create-user --user-type android.os.usertype.full.SECONDARY "{name}"')
        m = re.search(r"id (\d+)", out)
        if not m:
            raise AdbError(["pm", "create-user"], 1, out)
        return int(m.group(1))

    def remove_user(self, user_id: int) -> str:
        self.guard.check("remove a user")
        return self.shell(f"pm remove-user {user_id}").strip()

    def start_user(self, user_id: int) -> str:
        self.guard.check("start a user")
        return self.shell(f"am start-user {user_id}").strip()

    def stop_user(self, user_id: int) -> str:
        self.guard.check("stop a user")
        return self.shell(f"am stop-user -f {user_id}").strip()

    def switch_user(self, user_id: int) -> str:
        self.guard.check("switch the foreground user")
        return self.shell(f"am switch-user {user_id}").strip()

    def force_stop(self, package: str, user: int = 0) -> str:
        self.guard.check("force-stop an app")
        return self.shell(f"am force-stop --user {user} {package}").strip()

    def start_app(self, package: str, user: int = 0) -> str:
        """Launch an app in a user. `monkey` has no --user on this build, so resolve the activity and `am start`.

        The component is quoted: YouTube's is `com.google.android.youtube/.app.honeycomb.Shell$HomeActivity`,
        and this phone's shell expands `$HomeActivity` away, so `am start` answered "Activity class ...
        Shell does not exist" and the app never opened (measured 2026-11-21).
        """
        self.guard.check("open an app")
        out = self.shell(f"cmd package resolve-activity --brief --user {user} {package}", timeout=30)
        component = next((line.strip() for line in out.splitlines() if "/" in line and " " not in line.strip()), "")
        if not component:
            raise RuntimeError(f"{package} is not installed in user {user}")
        return self.shell(f"am start --user {user} -n '{component}'", timeout=30).strip()

    def install_existing(self, package: str, user: int) -> str:
        self.guard.check("install an app into a user")
        return self.shell(f"pm install-existing --user {user} {package}").strip()

    def install_apk(self, path: Path) -> str:
        self.guard.check("install an app")
        return self._run(["install", "-r", str(path)], timeout=600)

    def install_multiple(self, paths: list[Path]) -> str:
        self.guard.check("install an app")
        return self._run(["install-multiple", "-r", *[str(p) for p in paths]], timeout=900)

    def uninstall_for_user(self, package: str, user: int) -> str:
        self.guard.check("uninstall an app for a user")
        return self.shell(f"pm uninstall --user {user} {package}").strip()

    def grant(self, package: str, permission: str, user: int) -> str:
        self.guard.check("grant a permission")
        return self.shell(f"pm grant --user {user} {package} {permission}").strip()

    def appops(self, package: str, op: str, mode: str, user: int) -> str:
        self.guard.check("set an app-op")
        return self.shell(f"appops set --user {user} {package} {op} {mode}").strip()

    def settings_put(self, namespace: str, key: str, value: str, user: int) -> str:
        self.guard.check("change a setting")
        return self.shell(f"settings --user {user} put {namespace} {key} {value}").strip()

    def settings_get(self, namespace: str, key: str, user: int) -> str:
        return self.shell(f"settings --user {user} get {namespace} {key}").strip()

    def set_timezone(self, zone: str) -> str:
        self.guard.check("change the time zone")
        return self.shell(f"cmd alarm set-timezone {zone}").strip()

    def tap(self, x: int, y: int) -> None:
        self.guard.check("tap the screen")
        self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 300) -> None:
        self.guard.check("swipe the screen")
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {ms}")

    def scan_media(self, remote_path: str, timeout: int = 10) -> str:
        """Ask the media scanner to index a file. On some builds the broadcast never returns: short timeout."""
        self.guard.check("index a video")
        return self.shell(
            f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remote_path}", timeout=timeout
        ).strip()
