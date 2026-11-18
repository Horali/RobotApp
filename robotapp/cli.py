"""The `robot` command (PLAN section 8.1, section 8.2).

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
from .media import find_media_uri, push_video, video_length
from .post.base import FAILED, PostResult, PostSpec, split_caption
from .post.tiktok import TIKTOK_ID, TIKTOK_US, TikTokPoster
from .secrets import Chameleon, ChameleonError
from .spaces import SPACE_PACKAGES, Spaces
from .ui import U2Screen
from .vpn import Proxy, always_on, build_config, import_profile, serve_once, vpn_state
from .window import (
    BUILD_MODE_ENV,
    LockHeld,
    OutsideWindow,
    PhoneLock,
    build_mode,
    describe,
    in_window,
    seconds_left,
)

log = logging.getLogger("robotapp")

EXIT_OK, EXIT_ERROR, EXIT_NEEDS, EXIT_OUTSIDE, EXIT_LOCKED = 0, 1, 2, 3, 4


def emit(event: dict) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def resolve_serial(settings: Settings, emit_event: bool = True) -> str:
    """The serial to talk to: the configured one, or whatever mDNS found after a reboot.

    Transport only (adb connect / mdns services), never a phone shell command, so this is the one
    part of a job that may run at 05:50: it wakes nothing on the phone. The cable fallback is
    pinned to the robot phone's USB serial, so another phone on the cable is never touched.
    """
    from .reconnect import Reconnector

    reconnector = Reconnector(settings.adb)
    if reconnector.state_of(settings.serial) == "device":
        return settings.serial
    serial = reconnector.reconnect(settings.serial, usb_serial=settings.usb_serial)
    if not serial:
        return settings.serial  # let the command itself report the phone as unreachable
    if serial != settings.serial and emit_event:
        emit({"t": "info", "name": "serial", "configured": settings.serial, "using": serial})
    return serial


def build(args: argparse.Namespace, settings: Settings):
    """The phone and the screen for this run: the real ones, or the fakes with `--fake`."""
    if args.fake:
        phone = FakePhone(guard=fake_guard())
        return phone, None
    serial = resolve_serial(settings, emit_event=not getattr(args, "json", False))
    return AdbPhone(settings.adb, serial), serial


def screen_for(phone, settings: Settings):
    """The screen for the phone we are actually talking to (`phone.serial` is the resolved one)."""
    if isinstance(phone, FakePhone):
        from .fake import FakeScreen

        return FakeScreen()
    return U2Screen.connect(phone.serial)


def require_window() -> None:
    if in_window():
        return
    if build_mode():
        log.warning(
            "BUILD MODE is on (%s=1): using the phone at %s, outside 06:00-10:00. "
            "Unset it before any other script shares this phone.",
            BUILD_MODE_ENV,
            datetime.now().strftime("%H:%M"),
        )
        return
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
    """Leave the phone the way other scripts expect it ( section 9): the owner user in front."""
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


def cmd_connect(args: argparse.Namespace, settings: Settings) -> int:
    """Find the phone again: the configured serial, mDNS (Wireless debugging), then the cable.

    Transport only (adb connect / mdns), never a shell command, so it is safe to run at 05:50:
    it wakes no app and changes nothing on the phone.
    """
    from .reconnect import Reconnector

    reconnector = Reconnector(settings.adb)
    serial = reconnector.reconnect(settings.serial, cable_fallback=not args.no_cable)
    if serial:
        emit({"t": "connected", "serial": serial, "state": reconnector.state_of(serial)})
        if args.json:
            pass
        else:
            print(f"connected: {serial}")
        return EXIT_OK
    services = reconnector.mdns_services()
    emit({"t": "offline", "configured": settings.serial, "mdns": [vars(s) for s in services]})
    print("the phone is not reachable; plug the USB cable in and run this again")
    return EXIT_ERROR


def cmd_lock(args: argparse.Namespace, settings: Settings) -> int:
    lock = PhoneLock(fallback=settings.data_dir / "phone.lock")
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
    """ section 4.1 / section 4.2: clean the phone, create one US space, put the apps and the VPN in, check for leaks."""
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
    existing = next((u for u in phone.users() if u.name == args.space_name), None)
    if existing is not None:
        # A re-run must not create a second space with the same name: reuse it and refresh what it holds.
        emit({"t": "info", "name": "space exists", "user": existing.id, "name": existing.name})
        space_user = existing.id
        spaces.start(space_user)
        spaces.configure(space_user)
        for package in SPACE_PACKAGES:
            try:
                phone.install_existing(package, space_user)
            except Exception as exc:  # noqa: BLE001
                log.warning("could not install %s into user %s: %s", package, space_user, exc)
        spaces.grant_media(space_user)
    else:
        created = spaces.create(args.space_name)
        space_user = created.user_id
        emit({"t": "info", "name": "space created", "user": space_user, "name": created.name})
    enter_space(phone, space_user)

    if args.proxy_id:
        screen = screen_for(phone, settings)
        setup_vpn(phone, screen, chameleon, settings, space_user, args.proxy_id, emit)
    else:
        screen = None

    if args.zone:
        emit({"t": "step", "name": "time zone"})
        emit({"t": "info", "name": "time zone", "zone": timezone.set_zone(phone, args.zone)})

    emit({"t": "step", "name": "leak check"})
    screen = screen or screen_for(phone, settings)
    from .leakcheck import check_us
    result = check_us(phone, screen, space_user, expected_ip=args.expected_ip, shots_dir=settings.shots_dir)
    emit({"t": "leakcheck", **result.as_dict()})
    emit({"t": "info", "name": "space ready", "user": space_user, "ok": result.ok})
    leave_space(phone)
    return EXIT_OK if result.ok or result.outcome == "dry_run" else EXIT_ERROR


def setup_vpn(phone, screen, chameleon, settings, user: int, proxy_id: str, emit, wait_s: float = 90.0) -> dict:
    """Write the sing-box profile from Chameleon's proxy, get it onto the phone, lock the space to it.

    Order matters: lockdown off first (it would block the download), then the import, then wait for the tunnel,
    then always-on + lockdown. Returns the VPN state the phone reports.
    """
    from .vpn import always_on, clear_lockdown, serve_once, sfa_import, vpn_state

    emit({"t": "step", "name": "vpn"})
    proxy_body = chameleon.proxy(proxy_id)
    proxy = Proxy(
        host=str(proxy_body.get("host")),
        port=int(proxy_body.get("port") or 0),
        username=str(proxy_body.get("username") or ""),
        password=proxy_body.get("password"),
        protocol=str(proxy_body.get("protocol") or "socks5"),
    )
    clear_lockdown(phone, user)
    config = build_config(proxy)
    phone_host = settings.serial.split(":")[0]
    with serve_once(config, phone_host=phone_host) as (url, served):
        try:
            sfa_import(phone, screen, url, user, emit)
        except RuntimeError as exc:
            emit({"t": "error", "reason": str(exc)})
            return {"up": False, "reason": str(exc)}
        for _ in range(20):
            if served["done"]:
                break
            time.sleep(1.0)
        emit({"t": "info", "name": "profile import", "fetched": served["done"], "url_host": url.split("/")[2]})
        if not served["done"]:
            return {"up": False, "reason": "the phone did not fetch the profile (SFA would not open the link?)"}

    state: dict = {}
    for _ in range(int(wait_s)):
        state = vpn_state(phone, user)
        if state["up"]:
            break
        if screen is not None and _ > 2:
            _tap_start_if_present(screen, emit)
        time.sleep(1.0)
    if not state.get("up"):
        emit({"t": "info", "name": "vpn not up", "detail": state.get("detail")})
        return state
    always_on(phone, user)
    state = vpn_state(phone, user)
    emit({"t": "info", "name": "vpn locked", **{k: state[k] for k in ("up", "always_on_app", "lockdown")}})
    return state


def _tap_start_if_present(screen, emit) -> None:
    """SFA's big button is the only tap the robot needs on this app; names differ between versions."""
    from .ui import find, find_exact

    elements = screen.elements()
    for label in ("Start", "Connect", "Turn on", "Start service"):
        button = find_exact(elements, label) or find(elements, label)
        if button is not None:
            screen.tap(button)
            emit({"t": "info", "name": "tapped", "label": label})
            return


def cmd_vpn(args: argparse.Namespace, settings: Settings) -> int:
    """(Re)build the VPN for one space: clear lockdown, import the profile, wait, then lock it down."""
    phone, _ = build(args, settings)
    enter_space(phone, args.user)
    screen = screen_for(phone, settings)
    chameleon = Chameleon(settings.chameleon_url, settings.chameleon_token)
    try:
        state = setup_vpn(phone, screen, chameleon, settings, args.user, args.proxy_id, emit)
    finally:
        leave_space(phone)
    emit({"t": "vpn", **state})
    return EXIT_OK if state.get("up") else EXIT_ERROR


def cmd_zone(args: argparse.Namespace, settings: Settings) -> int:
    phone, _ = build(args, settings)
    # Going to New York freezes G2G's apps first, so they never see the jump (PLAN Â§4.6).
    zone = timezone.to_us(phone) if args.zone == "newyork" else timezone.to_jakarta(phone)
    emit({"t": "info", "name": "time zone", "zone": zone})
    return EXIT_OK


def cmd_leak(args: argparse.Namespace, settings: Settings) -> int:
    """The leak check on its own: VPN up and locked, the exit in the US, the right zone, no SIM."""
    from .leakcheck import check_g2g, check_us
    from .vpn import always_on

    phone, _ = build(args, settings)
    enter_space(phone, args.user)
    screen = screen_for(phone, settings)
    try:
        if args.user == 0:
            result = check_g2g(phone, screen, settings.shots_dir)
        else:
            if not args.no_lock:
                state = always_on(phone, args.user)
                emit({"t": "info", "name": "always-on", **state})
            result = check_us(phone, screen, args.user, expected_ip=args.expected_ip or None, shots_dir=settings.shots_dir)
    finally:
        leave_space(phone)
    emit({"t": "leakcheck", **result.as_dict()})
    return EXIT_OK if result.ok or result.outcome == "dry_run" else EXIT_ERROR


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
    media_uri = find_media_uri(phone, args.user, remote)
    emit({"t": "info", "name": "video pushed", "remote": remote, "length_s": length, "media_uri": media_uri})

    caption_text = args.caption
    if args.caption_file:
        caption_text = Path(args.caption_file).read_text(encoding="utf-8")
    caption, tags = split_caption(caption_text)
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
        media_uri=media_uri,
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
    return EXIT_OK if result.ok or result.outcome == "dry_run" else EXIT_ERROR


def cmd_screen(args: argparse.Namespace, settings: Settings) -> int:
    """What is on the phone now: the texts uiautomator2 can see (short), and optionally a screenshot.

    This is the tool for writing and fixing a step's signature on a real app version ( section 6.2).
    """
    phone, _ = build(args, settings)
    if getattr(args, "user", None) is not None:
        enter_space(phone, args.user)
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
    if args.save_as:
        from .screens import save_screen

        # The phone is already in the right state (the user put the screen there); save it as-is.
        path = _save_fixture(args.save_as, screen)
        print(f"fixture: {path}")
    return EXIT_OK


def _save_fixture(name: str, screen) -> Path:
    """Write what the screen shows as a fixture the signature tests replay (read-only)."""
    import json as _json

    from robotapp.screens import FIXTURES

    elements = screen.elements()
    body = {
        "name": name,
        "size": list(screen.size()),
        "elements": [
            {
                "text": e.text,
                "desc": e.desc,
                "resource_id": e.resource_id,
                "bounds": list(e.bounds),
                "clickable": e.clickable,
                "enabled": e.enabled,
            }
            for e in elements
        ],
    }
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / f"{name}.json"
    path.write_text(_json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def cmd_sitting(args: argparse.Namespace, settings: Settings) -> int:
    """One brand's sitting, from the JSON contract in PLAN section 8.2 (a file, or stdin)."""
    from .sitting import Sitting, run as run_sitting

    body = json.loads(Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read())
    sitting = Sitting.from_json(body)
    phone, _ = build(args, settings)
    screen = screen_for(phone, settings)
    chameleon = Chameleon(settings.chameleon_url, settings.chameleon_token)
    journal = Journal(settings.db_path)
    if sitting.user is not None:
        enter_space(phone, sitting.user)
    try:
        results = run_sitting(
            sitting, phone, screen, journal, chameleon, emit, shots_dir=settings.shots_dir, dry_run=args.dry_run
        )
    finally:
        leave_space(phone)
    return EXIT_OK if all(r.ok for r in results) else EXIT_ERROR


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

    co = sub.add_parser("connect", help="find the phone after a reboot (mDNS, then the cable)")
    co.add_argument("--no-cable", action="store_true", help="do not try the USB cable fallback")
    co.set_defaults(func=cmd_connect)

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
    pr.add_argument("--zone", default="", help="switch the phone's time zone before the leak check, e.g. America/New_York")
    pr.set_defaults(func=cmd_provision)

    vp = sub.add_parser("vpn", help="(re)build one space's VPN: import the profile, wait, lock it down")
    vp.add_argument("--user", type=int, required=True)
    vp.add_argument("--proxy-id", required=True)
    vp.set_defaults(func=cmd_vpn)

    zn = sub.add_parser("zone", help="switch the phone's time zone")
    zn.add_argument("zone", choices=("jakarta", "newyork"))
    zn.set_defaults(func=cmd_zone)

    lk2 = sub.add_parser("leak", help="the leak check for one space (or the owner user)")
    lk2.add_argument("--user", type=int, default=0)
    lk2.add_argument("--expected-ip", default="")
    lk2.add_argument("--no-lock", action="store_true", help="do not set always-on + lockdown first")
    lk2.set_defaults(func=cmd_leak)

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
    po.add_argument("--caption-file", default="", help="read the caption from a UTF-8 file (newlines and emoji)")
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

    si = sub.add_parser("sitting", help="one brand's sitting (JSON from PLAN section 8.2)")
    si.add_argument("--file", default="", help="the sitting JSON; stdin when omitted")
    si.add_argument("--dry-run", action="store_true", help="walk every post up to its Post button, then stop")
    si.set_defaults(func=cmd_sitting)

    st = sub.add_parser("status", help="what happened to a job")
    st.add_argument("job")
    st.set_defaults(func=cmd_status)

    sc = sub.add_parser("screen", help="what is on the phone now (for fixing signatures)")
    sc.add_argument("--user", type=int, default=None, help="switch into this user first")
    sc.add_argument("--shot", action="store_true", help="also save a screenshot to data/shots/screen.png")
    sc.add_argument("--save-as", default="", help="also save the elements as a test fixture with this name")
    sc.add_argument("--limit", type=int, default=40)
    sc.set_defaults(func=cmd_screen)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = Settings.load()
    settings.ensure_dirs()
    setup(settings.logs_dir)

    if args.command in ("doctor", "provision", "login", "post", "screen", "sitting", "vpn", "zone", "leak"):
        try:
            require_window()
        except OutsideWindow as exc:
            log.error("%s", exc)
            emit({"t": "error", "reason": str(exc)})
            return EXIT_OUTSIDE

    lock = PhoneLock(fallback=settings.data_dir / "phone.lock")
    needs_lock = args.command in ("provision", "login", "post", "screen", "sitting", "vpn", "zone", "leak")
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
