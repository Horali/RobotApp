"""`start_app` must hand the device shell a component it cannot mangle.

YouTube's launcher activity is `com.google.android.youtube/.app.honeycomb.Shell$HomeActivity`. Unquoted,
the phone's shell expands `$HomeActivity` to nothing and `am start` answers "Activity class ... Shell does
not exist" - the app never opened, which is exactly how the first YouTube dry run failed (2026-11-21).
The fake phone has its own `start_app`, so these tests drive the real `AdbPhone` with a stub shell.
"""

from robotapp.adb import AdbPhone
from robotapp.fake import fake_guard


class StubPhone(AdbPhone):
    """The real `AdbPhone`, with its shell replaced by a recorder."""

    def __init__(self, resolve: str) -> None:
        super().__init__("adb", "stub:5555", guard=fake_guard())
        self.commands: list[str] = []
        self._resolve = resolve

    def shell(self, command: str, timeout: int = 60) -> str:
        self.guard.check("stub shell")
        self.commands.append(command)
        if "resolve-activity" in command:
            return "priority=0 preferredOrder=0 match=0x108000\n" + self._resolve
        return "Starting: Intent"


def test_a_component_with_a_dollar_sign_is_quoted_for_the_device_shell():
    phone = StubPhone("com.google.android.youtube/.app.honeycomb.Shell$HomeActivity")
    phone.start_app("com.google.android.youtube", 11)
    starts = [c for c in phone.commands if c.startswith("am start")]
    assert starts, phone.commands
    assert "'com.google.android.youtube/.app.honeycomb.Shell$HomeActivity'" in starts[-1]


def test_a_plain_component_is_still_started():
    phone = StubPhone("com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity")
    phone.start_app("com.zhiliaoapp.musically", 11)
    starts = [c for c in phone.commands if c.startswith("am start")]
    assert "com.ss.android.ugc.aweme.splash.SplashActivity" in starts[-1]
