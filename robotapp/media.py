"""Getting the clip into the space's gallery (PLAN §6.1).

The shell cannot list another user's storage while that user is stopped, so the space must be running. Then:
`adb push` into `/storage/emulated/N/DCIM/Robot/`, and ask the media scanner to index it. A fresh name and
today's time make it the newest video in the gallery, which is what the post flows pick.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
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
    """Copy the clip into the space's gallery and index it. Returns the remote path.

    The owner user is an ordinary `adb push`. **A secondary user is not**: SELinux lets the adb
    shell write `/storage/emulated/0` but refuses `/storage/emulated/11` ("Permission denied",
    measured 2026-11-20 - step 1 only ever pushed into user 0, so this never showed). The way in is
    the space's own browser: the laptop serves the file, Chrome in that user downloads it into that
    user's Downloads (its own storage), and the space's media store indexes it.
    """
    if not local.exists():
        raise FileNotFoundError(f"clip not found: {local}")
    stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")
    remote_name = name or f"robot-{stamp}.mp4"

    if user_id != 0:
        return _push_via_browser(phone, local, user_id, remote_name)

    remote_dir = f"{media_store(user_id)}/{ROBOT_FOLDER}"
    phone.shell(f"mkdir -p {remote_dir}")
    remote = f"{remote_dir}/{remote_name}"
    phone.push(local, remote)
    # `adb push` keeps the laptop file's date; the gallery sorts by date, so make it "just now".
    try:
        phone.shell(f"touch {remote}", timeout=15)
    except Exception:  # noqa: BLE001 - the name already carries today's time
        pass
    try:
        phone.scan_media(remote)
    except Exception:  # noqa: BLE001 - the push already indexes it on this phone; the broadcast can hang
        pass
    return remote


def _serve_file(path: Path, filename: str = "", seconds: float = 180.0, host_ip: str = ""):
    """Serve one file over HTTP with Content-Disposition: attachment, so Chrome saves it rather than plays it.

    ``filename`` is the name the browser saves it under - it must be the robot's name, because the
    media store is then searched by it (Chrome would otherwise keep the laptop's file name, and the
    robot looked for its own: the download worked and the lookup failed, 2026-11-20).
    """
    import contextlib
    import http.server
    import threading
    import urllib.parse

    saved_as = filename or path.name

    @contextlib.contextmanager
    def serve():
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server naming
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f'attachment; filename="{saved_as}"')
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args) -> None:  # never log paths
                pass

        server = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Handler)
        server.timeout = seconds
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host = host_ip or _lan_ip()
            yield f"http://{host}:{server.server_address[1]}/{urllib.parse.quote(saved_as)}"
        finally:
            server.shutdown()
            server.server_close()

    return serve()


def _lan_ip() -> str:
    """The laptop's address on the same network as the phone."""
    import socket

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.168.1.1", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        try:
            probe.close()
        except Exception:  # noqa: BLE001
            pass


def _push_via_browser(phone: Phone, local: Path, user_id: int, remote_name: str, wait_s: float = 120.0) -> str:
    """Chrome in the space downloads the clip, then the space's media store indexes it.

    The file is served on a laptop port and reached through `adb reverse` (device loopback). A LAN
    address would travel through the space's VPN, and the proxy cannot reach 192.168.x.x.
    """
    download = f"/storage/emulated/{user_id}/Download/{remote_name}"
    with _serve_file(local, filename=remote_name) as url:
        port = int(url.rsplit(":", 1)[1].split("/")[0])
        try:
            phone.reverse_port(port, port)
            url = f"http://127.0.0.1:{port}/{remote_name}"
        except Exception:  # noqa: BLE001 - a phone without reverse still tries the LAN address
            pass
        phone.shell(
            f"am start --user {user_id} -a android.intent.action.VIEW -d '{url}' -p com.android.chrome",
            timeout=30,
        )
        # Chrome writes the download itself; the media store picks it up (or a scan makes it)
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            if find_media_uri(phone, user_id, download):
                return download
            time.sleep(3.0)
            try:
                phone.shell(
                    f"am broadcast --user {user_id} -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
                    f"-d file://{download}",
                    timeout=15,
                )
            except Exception:  # noqa: BLE001 - the scan is a nudge, not a requirement
                pass
    raise FileNotFoundError(f"the clip never reached the space's Downloads: {download}")


def find_media_uri(phone: Phone, user_id: int, remote: str) -> str | None:
    """The MediaStore URI of a pushed clip, for a share intent.

    A `file://` URI is refused by apps targeting Android N+, so the robot hands TikTok a `content://` one.
    """
    name = Path(remote).name
    query = (
        f"content query --user {user_id} --uri content://media/external/video/media "
        f"--projection _id:_display_name --where \"_display_name='{name}'\""
    )
    try:
        out = phone.shell(query, timeout=30)
    except Exception:  # noqa: BLE001 - the caller falls back to the gallery path
        return None
    match = re.search(r"_id=(\d+)", out)
    return f"content://media/external/video/media/{match.group(1)}" if match else None


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
