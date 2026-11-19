"""Provision's exit path: a failed leak check is a clean error exit, not a crash.

Found live 2026-11-19: the real install of musically left the phone on Jakarta time, the leak
check said so, and `cmd_provision` crashed on `result.outcome` — an attribute `LeakResult` never
had (copied from the post paths, whose `PostResult` does). The crash hid on every green run.
"""

import argparse

from robotapp.cli import EXIT_ERROR, cmd_provision
from robotapp.config import Settings
from robotapp.fake import FakePhone
from robotapp.leakcheck import LeakResult


def test_failed_leak_check_is_an_error_not_a_crash(monkeypatch, tmp_path) -> None:
    from robotapp import leakcheck

    def failing_check_us(*args, **kwargs) -> LeakResult:
        return LeakResult(ok=False, problems=["time zone is Asia/Jakarta, not America/New_York"])

    monkeypatch.setattr(leakcheck, "check_us", failing_check_us)
    args = argparse.Namespace(
        fake=True,
        clean=False,
        delete_users=[10, 999],
        space_name="US 1",
        musically_apk="",
        apk_sha256="",
        sfa_apk="",
        sfa_sha256="",
        proxy_id="",
        zone="",
        expected_ip="",
    )
    settings = Settings(data_dir=tmp_path)
    assert cmd_provision(args, settings) == EXIT_ERROR      # reported, not crashed
