"""`robot doctor`: is the phone ready for a sitting? (PLAN §8.2)

Read-only facts, gathered in one place: online, battery, heat, time zone, users and free spaces, app versions,
and the 06:00-10:00 window. The CLI prints them; a job calls `check()` first and refuses to start when a
blocking problem is found.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .adb import AdbError, AndroidUser, Battery, Phone
from .window import describe, in_window

# The apps a US space needs (§4.2). G2G's owner user has its own list (§3.3).
SPACE_APPS = {
    "com.zhiliaoapp.musically": "TikTok (US build)",
    "com.instagram.android": "Instagram",
    "com.google.android.youtube": "YouTube",
    "io.nekohasekai.sfa": "sing-box (SFA)",
}
OWNER_APPS = {
    "com.ss.android.ugc.trill": "TikTok (trill, G2G)",
    "com.google.android.youtube": "YouTube (G2G)",
}


@dataclass
class Report:
    online: bool = False
    model: str = ""
    android: str = ""
    sdk: str = ""
    battery: Battery | None = None
    timezone: str = ""
    users: list[AndroidUser] = field(default_factory=list)
    max_users: int = 0
    current_user: int = 0
    window: str = ""
    apps: dict[str, str | None] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def free_spaces(self) -> int:
        """Users the phone can still create: the limit includes the owner (§3.1)."""
        return max(0, self.max_users - len(self.users))

    @property
    def ok(self) -> bool:
        return self.online and not self.problems

    def as_dict(self) -> dict[str, object]:
        return {
            "online": self.online,
            "model": self.model,
            "android": self.android,
            "sdk": self.sdk,
            "battery": None if self.battery is None else {
                "level": self.battery.level,
                "temperature_c": self.battery.temperature_c,
                "ok": self.battery.ok,
            },
            "timezone": self.timezone,
            "users": [{"id": u.id, "name": u.name, "running": u.running} for u in self.users],
            "max_users": self.max_users,
            "current_user": self.current_user,
            "free_spaces": self.free_spaces,
            "window": self.window,
            "apps": self.apps,
            "problems": self.problems,
            "ok": self.ok,
        }


def check(phone: Phone, apps: dict[str, str] | None = None, moment=None) -> Report:
    """Gather the facts. Never raises for a missing phone: the report says what is wrong."""
    report = Report(window=describe(moment))
    report.online = phone.online()
    if not report.online:
        report.problems.append("the phone is not reachable over adb")
        return report

    try:
        report.model = phone.prop("ro.product.model")
        report.android = phone.prop("ro.build.version.release")
        report.sdk = phone.prop("ro.build.version.sdk")
        report.timezone = phone.timezone()
        report.battery = phone.battery()
        report.users = phone.users()
        report.max_users = phone.max_users()
        report.current_user = phone.current_user()
        for package in apps or SPACE_APPS:
            report.apps[package] = phone.package_version(package)
    except AdbError as exc:
        report.problems.append(f"adb error: {exc}")
        return report

    if report.battery and not report.battery.ok:
        report.problems.append(
            f"battery {report.battery.level} % / {report.battery.temperature_c:.1f} °C "
            "(needs 30 %+ and under 42 °C)"
        )
    if report.free_spaces == 0:
        report.problems.append("no free user slot (delete a space first)")
    if not any(u.owner for u in report.users):
        report.problems.append("the owner user (0) is missing")
    if not in_window(moment):
        report.problems.append(f"outside the work window ({describe(moment)})")
    return report


def format_report(report: Report) -> str:
    lines = [
        f"phone      {'online' if report.online else 'OFFLINE'}"
        + (f"  {report.model}, Android {report.android} (SDK {report.sdk})" if report.online else ""),
        f"window     {report.window}",
    ]
    if report.battery:
        lines.append(
            f"battery    {report.battery.level} %, {report.battery.temperature_c:.1f} °C "
            f"({'ok' if report.battery.ok else 'not ok'})"
        )
    if report.online:
        lines.append(f"time zone  {report.timezone}")
        lines.append(
            f"users      {len(report.users)} of {report.max_users} "
            f"({report.free_spaces} free): "
            + ", ".join(f"{u.id} {u.name}{'*' if u.running else ''}" for u in report.users)
        )
        lines.append(f"in front   user {report.current_user}")
        for package, version in report.apps.items():
            lines.append(f"app        {package} {version or 'NOT INSTALLED'}")
    if report.problems:
        lines.append("problems:")
        lines.extend(f"  - {p}" for p in report.problems)
    else:
        lines.append("all checks passed")
    return "\n".join(lines)
