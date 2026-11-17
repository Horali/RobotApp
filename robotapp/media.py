"""Getting the clip into the space's gallery (PLAN §6.1).

The shell cannot list another user's storage while that user is stopped, so the space must be running. Then:
`adb push` into `/storage/emulated/N/DCIM/Robot/`, and ask the media scanner to index it. A fresh name and
today's time make it the newest video in the gallery, which is what the post flows pick.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .adb import Phone
from .window import WIB

ROBOT_FOLDER = "DCIM/Robot"


def media_store(user_id: int) -> str:
    return f"/storage/emulated/{user_id}"


def find_ffprobe() -> str | None:
    """ffprobe from PATH, from FFPROBE in the environment, or ClipMaker's Remotion copy (this laptop)."""
    import os

    for candidate in (os.environ.get("FFPROBE"), os.environ.get("ROBOTAPP_FFPROBE")):
        if candidate and Path(candidate).exists():
            return candidate
    found = shutil.which("ffprobe")
    if found:
        return found
    known = Path(r"C:\Users\child\PROJECTS\ClipMaker\renderer\node_modules\@remotion\compositor-win32-x64-msvc\ffprobe.exe")
    return str(known) if known.exists() else None


def video_length(path: Path) -> float | None:
    """Length in seconds, from ffprobe when it is on the laptop. None when unknown."""
    ffprobe = find_ffprobe()
    if not ffprobe:
        return None
    try:
        done = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True,
            timeout=30,
            check=True,
        )
        return float(json.loads(done.stdout.decode("utf-8"))["format"]["duration"])
    except (subprocess.SubprocessError, ValueError, KeyError):
        return None


def push_video(phone: Phone, local: Path, user_id: int, name: str | None = None) -> str:
    """Copy the clip into the space's gallery and index it. Returns the remote path."""
    if not local.exists():
        raise FileNotFoundError(f"clip not found: {local}")
    stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")
    remote_name = name or f"robot-{stamp}.mp4"
    remote_dir = f"{media_store(user_id)}/{ROBOT_FOLDER}"
    phone.shell(f"mkdir -p {remote_dir}")
    remote = f"{remote_dir}/{remote_name}"
    phone.push(local, remote)
    phone.scan_media(remote)
    return remote


def gallery_has(phone: Phone, user_id: int, remote: str) -> bool:
    """The media store's own view, not just the file: the post flow needs the gallery to see it."""
    try:
        out = phone.shell(
            "content query --user {u} --uri content://media/external/video/media "
            "--projection _display_name --where \"_data LIKE '%{n}%'\"".format(u=user_id, n=Path(remote).name)
        )
    except Exception:  # noqa: BLE001 - the query is a check, not a requirement
        return False
    return "Row:" in out
