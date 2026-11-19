"""The leak check must read a *fresh* trace page, never a cached one (found 2026-11-20).

Chrome kept showing a trace page from minutes earlier while the space's DNS was broken, so the
check read a believable ip=/loc= from a network that could not resolve anything. Two guards: a
cache-busting query on the URL, and the page's own `ts=` must be recent.
"""

import time

from robotapp.fake import FakeScreen, fake_guard
from robotapp.leakcheck import read_trace, trace_url
from robotapp.ui import Element

PAGE = (
    "fl=1167f8\nh=1.1.1.1\nip=208.214.162.185\nts={ts}\nvisit_scheme=https\n"
    "uag=Mozilla/5.0\ncolo=BOS\nloc=US\ntls=TLSv1.3\n"
)


class Phone:
    """Records the URLs opened; no adb."""

    def __init__(self):
        self.urls: list[str] = []

    def shell(self, command: str, timeout: int = 60) -> str:
        self.urls.append(command)
        return ""


def el(text: str) -> Element:
    return Element(text=text, bounds=(0, 0, 1080, 2000))


def test_the_url_is_unique_so_the_cache_cannot_answer() -> None:
    first, second = trace_url(1_700_000_000), trace_url(1_700_000_001)
    assert first != second
    assert first.startswith("https://1.1.1.1/cdn-cgi/trace?t=")


def test_a_fresh_page_is_read() -> None:
    phone = Phone()
    screen = FakeScreen([el(PAGE.format(ts=f"{time.time():.3f}"))])
    ip, loc, _ = read_trace(phone, screen, 11, timeout_s=2)
    assert (ip, loc) == ("208.214.162.185", "US")
    assert "?t=" in phone.urls[0]          # it asked for a live copy


def test_a_cached_page_is_not_an_answer() -> None:
    phone = Phone()
    old = time.time() - 3600                 # an hour old: the browser had it from before the network died
    screen = FakeScreen([el(PAGE.format(ts=f"{old:.3f}"))])
    ip, loc, text = read_trace(phone, screen, 11, timeout_s=2)
    assert (ip, loc) == (None, None)
    assert "ip=208.214.162.185" in text      # it read the page, and refused to trust it
