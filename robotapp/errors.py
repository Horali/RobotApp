"""The two things the robot cannot do alone (PLAN §5.4): a code from an inbox, and a human tap.

A job that hits one reports it as a `needs` event and waits. In step 1 the CLI asks on the terminal; from step 4
ClipMaker answers through its Telegram bot, so the same events carry the same fields.
"""

from __future__ import annotations


class RobotError(RuntimeError):
    """Something the robot cannot continue past, with a message meant for the log and the caller."""


class NeedsHuman(RobotError):
    """A CAPTCHA, a phone code, a selfie check: only the user can clear it."""

    def __init__(self, why: str, screenshot: str | None = None, wait_s: int = 900) -> None:
        self.why = why
        self.screenshot = screenshot
        self.wait_s = wait_s
        super().__init__(why)

    def as_event(self) -> dict[str, object]:
        body: dict[str, object] = {"t": "needs", "kind": "human", "why": self.why, "wait_s": self.wait_s}
        if self.screenshot:
            body["screenshot"] = self.screenshot
        return body


class NeedsCode(RobotError):
    """A 6-digit code sent to the account's email."""

    def __init__(self, platform: str, email_account_id: str | None = None, sender: str | None = None, since: str | None = None) -> None:
        self.platform = platform
        self.email_account_id = email_account_id
        self.sender = sender
        self.since = since
        super().__init__(f"a code is needed for {platform}")

    def as_event(self) -> dict[str, object]:
        return {
            "t": "needs",
            "kind": "email_code",
            "platform": self.platform,
            "email_account_id": self.email_account_id,
            "sender": self.sender,
            "since": self.since,
        }
