"""Secrets and the log filter (PLAN §5.1): a password cannot be printed, and Chameleon's answers are read right.

Fake values only. The HTTP server stands in for Chameleon's daemon.
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from robotapp.log import REDACTED, RedactingFilter, Secret, redact
from robotapp.secrets import Chameleon, ChameleonError, NotSaved

TOKEN = "test-token-not-a-real-one"
PASSWORD = "fake-TikTok-Pass-123!"


def test_a_secret_never_prints_itself() -> None:
    secret = Secret(PASSWORD)
    assert str(secret) == REDACTED
    assert repr(secret) == f"Secret({REDACTED})"
    assert f"{secret}" == REDACTED
    assert secret.reveal() == PASSWORD
    assert secret != PASSWORD  # comparing to the plain string is False, so an f-string cannot slip through


def test_the_log_filter_redacts_registered_values() -> None:
    Secret(PASSWORD)  # registers it
    assert redact(f"typing {PASSWORD} now") == f"typing {REDACTED} now"

    record = logging.LogRecord("robotapp", logging.INFO, __file__, 1, "pw=%s", (PASSWORD,), None)
    RedactingFilter().filter(record)
    assert PASSWORD not in record.getMessage()


def test_short_values_are_not_registered() -> None:
    Secret("abc")  # too short to redact safely
    assert redact("abc def") == "abc def"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_error(401)
            return
        if self.path.startswith("/v1/profiles/p1/platform-password"):
            body = {"profile_id": "p1", "platform": "tiktok", "password": PASSWORD}
        elif self.path.startswith("/v1/proxies/x1"):
            body = {"id": "x1", "host": "1.2.3.4", "port": 50101, "username": "u", "password": "proxy-pw"}
        else:
            self.send_error(404, "no platform password saved for this profile")
            return
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args) -> None:
        return


@pytest.fixture()
def chameleon():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield Chameleon(f"http://127.0.0.1:{server.server_address[1]}", TOKEN)
    finally:
        server.shutdown()
        server.server_close()


def test_platform_password_is_a_secret(chameleon: Chameleon) -> None:
    password = chameleon.platform_password("p1", "tiktok")
    assert isinstance(password, Secret)
    assert password.reveal() == PASSWORD
    assert str(password) == REDACTED


def test_a_missing_password_is_not_saved(chameleon: Chameleon) -> None:
    with pytest.raises(NotSaved):
        chameleon.platform_password("p2", "tiktok")


def test_a_proxy_password_is_a_secret(chameleon: Chameleon) -> None:
    proxy = chameleon.proxy("x1")
    assert proxy["host"] == "1.2.3.4"
    assert isinstance(proxy["password"], Secret)


def test_a_wrong_token_is_an_error() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        wrong = Chameleon(f"http://127.0.0.1:{server.server_address[1]}", "nope")
        with pytest.raises(ChameleonError):
            wrong.platform_password("p1", "tiktok")
    finally:
        server.shutdown()
        server.server_close()
