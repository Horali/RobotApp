"""Chameleon's login identity: the email assigned to a profile, so the caller never has to know it."""

import pytest

from robotapp.secrets import Chameleon


class FakeChameleon(Chameleon):
    """Answers /v1/email-accounts from a canned list; no network."""

    def __init__(self, accounts):
        super().__init__("http://fake", "token")
        self.accounts = accounts

    def _get(self, path):
        assert path == "/v1/email-accounts"
        return {"items": self.accounts}


def test_the_assigned_email_is_the_login_name() -> None:
    client = FakeChameleon([
        {"id": "e1", "address": "brand@gmail.com", "assignments": [
            {"brand_profile_id": "ig-profile", "platform": "instagram"}]},
    ])
    assert client.login_identity("ig-profile") == ("brand@gmail.com", "e1")


def test_a_profile_with_no_email_answers_none_none() -> None:
    client = FakeChameleon([
        {"id": "e1", "address": "brand@gmail.com", "assignments": [
            {"brand_profile_id": "tt-profile", "platform": "tiktok"}]},
    ])
    assert client.login_identity("ig-profile") == (None, None)


def test_a_platform_filter_can_still_fall_back_to_the_gmail_assignment() -> None:
    """One brand often uses one Gmail for all its accounts (the plan's 'one Gmail' case)."""
    client = FakeChameleon([
        {"id": "e1", "address": "brand@gmail.com", "assignments": [
            {"brand_profile_id": "ig-profile", "platform": "gmail"}]},
    ])
    assert client.login_identity("ig-profile", "instagram")[0] == "brand@gmail.com"
