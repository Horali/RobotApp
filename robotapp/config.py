"""Settings and paths.

Everything comes from the environment, with a `.env` file next to the repo root as a convenience. The `.env`
holds secrets (Chameleon's bearer token), so it is git-ignored and never printed: `Settings.describe()` lists
the names it found and nothing else.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ADB = Path(r"C:\Users\child\AppData\Local\Android\Sdk\platform-tools\adb.exe")
DEFAULT_SERIAL = "192.168.1.8:5555"
DEFAULT_CHAMELEON = "http://127.0.0.1:38100"


def load_dotenv(path: Path) -> dict[str, str]:
    """A tiny `.env` reader: `KEY=value` lines, `#` comments, optional quotes. No dependency, no surprises."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


@dataclass
class Settings:
    adb: Path = DEFAULT_ADB
    serial: str = DEFAULT_SERIAL
    usb_serial: str = ""  # the robot phone's USB serial, so the cable fallback never touches another phone
    chameleon_url: str = DEFAULT_CHAMELEON
    chameleon_token: str = ""
    data_dir: Path = field(default_factory=lambda: REPO_ROOT / "data")
    # The robot's own clock: the 06:00-10:00 WIB rule (PLAN §7.2, §9). Not configurable on purpose.
    window_start: str = "06:00"
    window_end: str = "10:00"
    no_post_after: str = "09:55"

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        env_file = env_file or (REPO_ROOT / ".env")
        file_values = load_dotenv(env_file)

        def get(name: str, default: str | None = None) -> str | None:
            return os.environ.get(name, file_values.get(name, default))

        data = get("ROBOTAPP_DATA")
        return cls(
            adb=Path(get("ADB_PATH") or DEFAULT_ADB),
            serial=get("PHONE_SERIAL") or DEFAULT_SERIAL,
            usb_serial=get("PHONE_USB_SERIAL") or "",
            chameleon_url=(get("CHAMELEON_API_URL") or DEFAULT_CHAMELEON).rstrip("/"),
            chameleon_token=get("CHAMELEON_TOKEN") or "",
            data_dir=Path(data) if data else REPO_ROOT / "data",
        )

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def shots_dir(self) -> Path:
        return self.data_dir / "shots"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "robot.db"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.logs_dir, self.shots_dir):
            path.mkdir(parents=True, exist_ok=True)

    def describe(self) -> dict[str, object]:
        """What the robot is configured with, without any secret: safe to print and to log."""
        return {
            "adb": str(self.adb),
            "serial": self.serial,
            "chameleon_url": self.chameleon_url,
            "chameleon_token": "set" if self.chameleon_token else "missing",
            "data_dir": str(self.data_dir),
            "window": f"{self.window_start}-{self.window_end} Asia/Jakarta",
        }
