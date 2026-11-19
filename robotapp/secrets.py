"""Chameleon (CustomBrowser) is where the accounts' secrets live. This is the only way the robot reads one.

Rules from the plan (§5.1): a secret is fetched **at the moment it is typed**, kept in memory, and dropped right
after. It never goes into the repo, a file, a log, an event, an exception or a screenshot. So every method here
returns a `Secret`, whose `str()` is `***`; only the typing code calls `.reveal()`.

Endpoints used:
  GET /v1/profiles/:id/platform-password?platform=tiktok|instagram   (built for this robot, PLAN §5.1)
  GET /v1/proxies/:id?include_secrets=true                            (proxy login for sing-box)
  GET /v1/email-accounts/:id/password                                 (Gmail password, for Google sign-in)
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .log import Secret


class ChameleonError(RuntimeError):
    pass


class NotSaved(ChameleonError):
    """The secret exists in Chameleon's world but was never saved: the user has to add it."""


class Chameleon:
    def __init__(self, base_url: str, token: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout

    def _get(self, path: str) -> dict:
        if not self._token:
            raise ChameleonError("CHAMELEON_TOKEN is not set in .env: the robot cannot read any secret")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            message = ""
            try:
                message = str(json.loads(body).get("error", ""))
            except ValueError:
                pass
            if exc.code == 404:
                raise NotSaved(message or f"not saved in Chameleon ({path})") from None
            raise ChameleonError(f"Chameleon answered {exc.code}: {message or 'no message'}") from None
        except urllib.error.URLError as exc:
            raise ChameleonError(f"Chameleon is not reachable at {self.base_url} ({exc.reason})") from None

    # -- what the robot needs ----------------------------------------------------------------------
    def platform_password(self, profile_id: str, platform: str) -> Secret:
        """TikTok or Instagram password of a brand profile. YouTube has none (it uses the Gmail one)."""
        body = self._get(f"/v1/profiles/{profile_id}/platform-password?platform={platform}")
        password = body.get("password")
        if not password:
            raise NotSaved(f"no {platform} password saved for profile {profile_id}")
        return Secret(str(password))

    def proxy(self, proxy_id: str) -> dict:
        """Proxy details including its login, for writing the sing-box config. The password is a Secret."""
        body = self._get(f"/v1/proxies/{proxy_id}?include_secrets=true")
        if body.get("password"):
            body["password"] = Secret(str(body["password"]))
        return body

    def email_password(self, account_id: str) -> Secret:
        body = self._get(f"/v1/email-accounts/{account_id}/password")
        password = body.get("password")
        if not password:
            raise NotSaved(f"no password saved for email account {account_id}")
        return Secret(str(password))

    def login_identity(self, profile_id: str, platform: str | None = None) -> tuple[str | None, str | None]:
        """(the email address, the email account id) assigned to a brand profile, or (None, None).

        This is the login name of an account: the email Chameleon links to the profile. The plan's
        callers pass Chameleon ids, not secrets; the robot looks the name up instead of asking.
        """
        items = self._get("/v1/email-accounts").get("items") or []
        for account in items:
            for assignment in account.get("assignments") or []:
                if assignment.get("brand_profile_id") != profile_id:
                    continue
                if platform and assignment.get("platform") not in (platform, "gmail", None):
                    continue
                return account.get("address"), account.get("id")
        return None, None

    def health(self) -> dict:
        return self._get("/v1/health")
