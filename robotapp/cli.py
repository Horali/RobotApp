"""The `robot` command (PLAN Â§8.1, Â§8.2).

One command, JSON events on stdout, human logs on stderr, so ClipMaker can start it and read lines. In step 1 it
is run by hand:

    python -m robotapp.cli doctor
    python -m robotapp.cli provision --space-name "US 1" --proxy-id <chameleon proxy id>
    python -m robotapp.cli login tiktok --user 11 --profile-id <id> --email <address>
    python -m robotapp.cli post tiktok --user 11 --video C:\\clips\\x.mp4 --caption "..." --hashtags "#x"

Every command that touches the phone takes the shared lock first and refuses outside 06:00-10:00 WIB.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from . import doctor, timezone
from .adb import AdbPhone
from .apk import ApkRejected, install as install_apk, install_bundle, verify as verify_apk
from .config import Settings
from .errors import NeedsCode, NeedsHuman, RobotError
from .fake import FakePhone, fake_guard
from .journal import Journal, write_status
from .log import setup
from .media import push_video, video_length
from .post.base import FAILED, PostResult, PostSpec, split_caption
from .post.tiktok import TIKTOK_ID, TIKTOK_US, TikTokPoster
from .secrets import Chameleon, ChameleonError
from .spaces import SPACE_PACKAGES, Spaces
from .ui import U2Screen
from .vpn import Proxy, always_on, build_config, import_profile, serve_once, vpn_state
from .window import LockHeld, OutsideWindow, PhoneLock, describe, in_window, seconds_left

log = logging.getLogger("robotapp")

EXIT_OK, EXIT_ERROR, EXIT_NEEDS, EXIT_OUTSIDE, EXIT_LOCKED = 0, 1, 2, 3, 4


def emit(event: dict) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def build(args: argparse.Namespace, settings: Settings):
    """The phone and the screen for this run: the real ones, or the fakes with `--fake`."""
    if args.fake:
        phone = FakePhone(guard=fake_guard())
        return phone, None
    return AdbPhone(settings.adb, settings.serial), None


def screen_for(phone, settings: Settings):
    if isinstance(phone, FakePhone):
        from .fake import FakeScreen

        return FakeScreen()
    return U2Screen.connect(settings.serial)


def require_window() -> None:
    if not in_window():
        raise OutsideWindow(
            f"it is {datetime.now().strftime('%H:%M')} WIB and the robot only works 06:00-10:00 ({describe()})"
        )


def enter_space(phone, user: int) -> None:
    """The screen only shows one user at a time: to read a space's screen, that space must be in front."""
    if phone.current_user() == user:
        return
    phone.switch_user(user)
    for _ in range(10):
        time.sleep(1.0)
        if phone.current_user() == user:
            time.sleep(2.0)  # let the launcher settle before uiautomator2 reads it
            return
    raise RobotError(f"could not switch the phone to user {user}")


def leave_space(phone) -> None:
    """Leave the phone the way other scripts expect it (§9): the owner user in front."""
    try:
        if phone.current_user() != 0:
            phone.switch_user(0)
            time.sleep(2.0)
    except Exception as exc:  # noqa: BLE001 - never mask the job's own result
        log.warning("could not switch back to the owner user: %s", exc)


# -- commands --------------------------------------------------------------------------------------
def cmd_doctor(args: argparse.Namespace, settings: Settings) -> int:
    phone, _ = build(args, settings)
    apps = doctor.OWNER_APPS if args.owner else doctor.SPACE_APPS
    report = doctor.check(phone, apps)
    if args.json:
        emit(report.as_dict())
    else:
        print(doctor.format_report(report))
    return EXIT_OK if report.ok else EXIT_ERROR


def cmd_window(args: argparse.Namespace, settings: Settings) -> int:
    body = {
        "now": datetime.now().isoformat(timespec="seconds"),
        "inside": in_window(),
        "describe": describe(),
        "seconds_left": round(seconds_left()),
    }
    emit(body) if args.json else print(f"{body['now']}  {body['describe']}")
    return EXIT_OK


def cmd_lock(args: argparse.Namespace, settings: Settings) -> int:
    lock = PhoneLock()
    if args.action == "status":
        info = lock.read()
        if info is None:
            print("free")
        else:
            print(f"held by {info.holder} (pid {info.pid}) since {info.since} until {info.until}")
        return EXIT_OK
    if args.action == "take":
        info = lock.acquire(wait_s=args.wait)
        print(f"taken until {info.until}")
        return EXIT_OK
    print("released" if lock.release() else "not ours to release")
    return EXIT_OK


def cmd_provision(args: argparse.Namespace, settings: Settings) -> int:
    """Â§4.1 / Â§4.2: clean the phone, create one US space, put the apps and the VPN in, check for leaks."""
    phone, _ = build(args, settings)
    spaces = Spaces(phone)
    chameleon = Chameleon(settings.chameleon_url, settings.chameleon_token)

    emit({"t": "step", "name": "clean"})
    if args.clean:
        for package in ("com.rise.automatic.autoclicker.clicker",):
            try:
                phone.uninstall_for_user(package, 0)
                emit({"t": "info", "name": "uninstalled", "package": package})
            except Exception as exc:  # noqa: BLE001
                emit({"t": "info", "name": "not installed", "package": package, "detail": str(exc)})
        for user_id in args.delete_users:
            if user_id == 0:
                continue
            try:
                emit({"t": "info", "name": "user removed", "user": user_id, "detail": spaces.delete(user_id)})
            except Exception as exc:  # noqa: BLE001
                emit({"t": "info", "name": "user not removed", "user": user_id, "detail": str(exc)})
        timezone.disable_auto_detection(phone)

    if args.sfa_apk:
        emit({"t": "step", "name": "install sing-box"})
        sfa = Path(args.sfa_apk)
        if args.sfa_sha256:
            emit({"t": "info", "name": "apk certificate", "sha256": verify_apk(sfa, args.sfa_sha256)})
        install_apk(phone, sfa)

    if args.musically_apk:
        emit({"t": "step", "name": "install musically"})
        apk_path = Path(args.musically_apk)
        digest = verify_apk(apk_path, args.apk_sha256 or "")
        emit({"t": "info", "name": "apk certificate", "sha256": digest})
        if apk_path.suffix.lower() in (".apkm", ".xapk"):
            install_bundle(phone, apk_path, settings.data_dir / "tmp" / "apkm")
        else:
            install_apk(phone, apk_path)

    emit({"t": "step", "name": "create space"})
    space = spaces.create(args.space_name)
    emit({"t": "info", "name": "space created", "user": space.user_id, "name": space.name})
    enter_space(phone, space.user_id)

    if args.proxy_id:
        emit({"t": "step", "name": "vpn"})
        proxy_body = chameleon.proxy(args.proxy_id)
        proxy = Proxy(
            host=str(proxy_body.get("host")),
            port=int(proxy_body.get("port") or 0),
            username=str(proxy_body.get("username") or ""),
            password=proxy_body.get("password"),
            protocol=str(proxy_body.get("protocol") or "socks5"),
        )
        config = build_config(proxy)
        with serve_once(config) as (url, served):
            import_profile(phone, url, space.user_id)
            emit({"t": "info", "name": "profile import opened", "served": served["done"]})
        state = always_on(phone, space.user_id)
        emit({"t": "info", "name": "always-on", **state})

    emit({"t": "step", "name": "leak check"})
    screen = screen_for(phone, settings)
    from .leakcheck import check_us

    result = check_us(phone, screen, space.user_id, expected_ip=args.expected_ip, shots_dir=settings.shots_dir)
    emit({"t": "leakcheck", **result.as_dict()})
    emit({"t": "info", "name": "space ready", "user": space.user_id, "ok": result.ok})
    leave_space(phone)
    return EXIT_OK if result.ok else EXIT_ERROR


def cmd_login(args: argparse.Namespace, settings: Settings) -> int:
    phone, _ = build(args, settings)
    screen = screen_for(phone, settings)
    chameleon = Chameleon(settings.chameleon_url, settings.chameleon_token)
    journal = Journal(settings.db_path)
    job_id = args.job or f"login-{uuid.uuid4().hex[:8]}"
    journal.start_job(job_id, "login", payload={"user": args.user, "profile": args.profile_id})
    enter_space(phone, args.user)

    def code_provider() -> str:
        if args.code:
            return args.code
        emit({"t": "needs", "kind": "email_code", "platform": "tiktok"})
        print("Type the 6-digit code from the account's email and press Enter:", file=sys.stderr, flush=True)
        return sys.stdin.readline().strip()

    from .login.tiktok import TikTokLogin

    login = TikTokLogin(phone, screen, chameleon, emit=emit, shots_dir=settings.shots_dir, code_provider=code_provider)
    try:
        result = login.login(args.profile_id, args.email, args.package)
    except NeedsHuman as exc:
        emit(exc.as_event())
        journal.set_state(job_id, "needs_human")
        return EXIT_NEEDS
    except NeedsCode as exc:
        emit(exc.as_event())
        journal.set_state(job_id, "needs_code")
        return EXIT_NEEDS
    journal.set_state(job_id, "done" if result.logged_in else "failed")
    emit({"t": "done", "job": job_id, "handle": result.handle, "logged_in": result.logged_in})
    leave_space(phone)
    return EXIT_OK if result.logged_in else EXIT_ERROR


def cmd_post(args: argparse.Namespace, settings: Settings) -> int:
    phone, _ = build(args, settings)
    screen = screen_for(phone, settings)
    journal = Journal(settings.db_path)
    job_id = args.job or f"post-{uuid.uuid4().hex[:8]}"
    journal.start_job(job_id, "post", payload={"user": args.user, "video": str(args.video)})
    enter_space(phone, args.user)

    if args.leakcheck:
        from .leakcheck import check_g2g, check_us

        if args.user == 0:
            leak = check_g2g(phone, screen, settings.shots_dir)
        else:
            leak = check_us(phone, screen, args.user, expected_ip=args.expected_ip, shots_dir=settings.shots_dir)
        emit({"t": "leakcheck", **leak.as_dict()})
        if not leak.ok:
            emit({"t": "done", "post": args.upload_id, "outcome": FAILED, "reason": "leak check failed"})
            return EXIT_ERROR

    length = args.length or video_length(args.video)
    remote = push_video(phone, args.video, args.user)
    emit({"t": "info", "name": "video pushed", "remote": remote, "length_s": length})

    caption, tags = split_caption(args.caption)
    if args.hashtags:
        tags = [t.strip() for t in args.hashtags.split(",") if t.strip()]
    package = args.package or (TIKTOK_ID if args.user == 0 else TIKTOK_US)
    spec = PostSpec(
        upload_id=args.upload_id,
        platform="tiktok",
        video=args.video,
        length_s=length,
        caption=caption,
        hashtags=tags,
        sound=args.sound,
        sound_required=args.sound_required,
    )
    poster = TikTokPoster(phone, screen, journal, job_id, package=package, emit=emit, shots_dir=settings.shots_dir)
    try:
        result = poster.post(spec, dry_run=args.dry_run)
    except NeedsHuman as exc:
        emit(exc.as_event())
        journal.set_state(job_id, "needs_human")
        return EXIT_NEEDS
    journal.set_state(job_id, "done" if result.ok else result.outcome)
    emit(result.as_event())
    leave_space(phone)
    return EXIT_OK if result.ok else EXIT_ERROR


def cmd_screen(args: argparse.Namespace, settings: Settings) -> int:
    """What is on the phone now: the texts uiautomator2 can see (short), and optionally a screenshot.

    This is the tool for writing and fixing a step's signature on a real app version (§6.2).
    """
    phone, _ = build(args, settings)
    screen = screen_for(phone, settings)
    elements = screen.elements()
    rows = [
        {"text": e.text, "desc": e.desc, "id": e.resource_id, "bounds": list(e.bounds), "clickable": e.clickable}
        for e in elements
        if e.text or e.desc or e.clickable
    ]
    if args.json:
        emit({"t": "screen", "count": len(rows), "elements": rows[: args.limit]})
    else:
        for row in rows[: args.limit]:
            label = row["text"] or row["desc"]
            print(f"{label!r:45.45}  id={row['id'][-40:]:40.40}  {row['bounds']}")
    if args.shot:
        path = settings.shots_dir / "screen.png"
        screen.screenshot(path)
        print(f"screenshot: {path}")
    return EXIT_OK


def cmd_status(args: argparse.Namespace, settings: Settings) -> int:
    journal = Journal(settings.db_path)
    job = journal.job(args.job) if args.job else None
    if job is None:
        emit({"t": "error", "reason": "no such job"})
        return EXIT_ERROR
    emit({"t": "job", **job, "events": [e.as_dict() for e in journal.events(args.job)]})
    return EXIT_OK


# -- wiring ----------------------------------------------------------------------------------------
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="robot", description="The phone robot (see PLAN.md)")
    p.add_argument("--fake", action="store_true", help="use the fake phone instead of adb")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("doctor", help="is the phone ready?")
    d.add_argument("--owner", action="store_true", help="check G2G's apps in the owner user")
    d.set_defaults(func=cmd_doctor)

    w = sub.add_parser("window", help="is the robot inside 06:00-10:00 WIB?")
    w.set_defaults(func=cmd_window)

    lk = sub.add_parser("lock", help="the shared phone lock")
    lk.add_argument("action", choices=("status", "take", "release"))
    lk.add_argument("--wait", type=float, default=0.0)
    lk.set_defaults(func=cmd_lock)

    pr = sub.add_parser("provision", help="clean the phone and build one US space")
    pr.add_argument("--space-name", default="US 1")
    pr.add_argument("--proxy-id", default="")
    pr.add_argument("--clean", action="store_true", help="uninstall the auto-clicker and delete the old users")
    pr.add_argument("--delete-users", type=int, nargs="*", default=[10, 999])
    pr.add_argument("--musically-apk", default="")
    pr.add_argument("--apk-sha256", default="")
    pr.add_argument("--sfa-apk", default="", help="sing-box APK to install once (F-Droid, developer-signed)")
    pr.add_argument("--sfa-sha256", default="")
    pr.add_argument("--expected-ip", default="")
    pr.set_defaults(func=cmd_provision)

    lo = sub.add_parser("login", help="sign an account in")
    lo.add_argument("platform", choices=("tiktok",))
    lo.add_argument("--user", type=int, required=True)
    lo.add_argument("--profile-id", required=True)
    lo.add_argument("--email", required=True)
    lo.add_argument("--package", default=TIKTOK_US)
    lo.add_argument("--code", default="")
    lo.add_argument("--job", default="")
    lo.set_defaults(func=cmd_login)

    po = sub.add_parser("post", help="post one clip")
    po.add_argument("platform", choices=("tiktok",))
    po.add_argument("--user", type=int, required=True)
    po.add_argument("--video", type=Path, required=True)
    po.add_argument("--caption", default="")
    po.add_argument("--hashtags", default="")
    po.add_argument("--length", type=float, default=0.0)
    po.add_argument("--sound", default=None)
    po.add_argument("--sound-required", action="store_true")
    po.add_argument("--package", default="", help="default: trill for user 0, musically otherwise")
    po.add_argument("--upload-id", default="local-test")
    po.add_argument("--expected-ip", default="")
    po.add_argument("--no-leakcheck", dest="leakcheck", action="store_false")
    po.add_argument("--dry-run", action="store_true", help="walk the flow up to the Post button, then stop")
    po.add_argument("--job", default="")
    po.set_defaults(func=cmd_post, leakcheck=True)

    st = sub.add_parser("status", help="what happened to a job")
    st.add_argument("job")
    st.set_defaults(func=cmd_status)

    sc = sub.add_parser("screen", help="what is on the phone now (for fixing signatures)")
    sc.add_argument("--shot", action="store_true", help="also save a screenshot to data/shots/screen.png")
    sc.add_argument("--limit", type=int, default=40)
    sc.set_defaults(func=cmd_screen)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = Settings.load()
    settings.ensure_dirs()
    setup(settings.logs_dir)

    if args.command in ("doctor", "provision", "login", "post", "screen"):
        try:
            require_window()
        except OutsideWindow as exc:
            log.error("%s", exc)
            emit({"t": "error", "reason": str(exc)})
            return EXIT_OUTSIDE

    lock = PhoneLock()
    needs_lock = args.command in ("provision", "login", "post", "screen")
    if needs_lock:
        try:
            lock.acquire(wait_s=60)
        except LockHeld as exc:
            log.error("%s", exc)
            emit({"t": "error", "reason": str(exc)})
            return EXIT_LOCKED
        write_status(settings.data_dir / "status.json", {"job": args.command, "state": "running", "pid": None})

    try:
        return int(args.func(args, settings))
    except (RobotError, ChameleonError, ApkRejected) as exc:
        log.error("%s", exc)
        emit({"t": "error", "reason": str(exc)})
        return EXIT_ERROR
    except OutsideWindow as exc:
        log.error("%s", exc)
        emit({"t": "error", "reason": str(exc)})
        return EXIT_OUTSIDE
    except Exception as exc:  # noqa: BLE001 - the CLI is the top level: report, never traceback at the user
        log.exception("unexpected error")
        emit({"t": "error", "reason": f"{type(exc).__name__}: {exc}"})
        return EXIT_ERROR
    finally:
        if needs_lock:
            lock.release()
            write_status(settings.data_dir / "status.json", {"job": args.command, "state": "idle"})


if __name__ == "__main__":
    raise SystemExit(main())
