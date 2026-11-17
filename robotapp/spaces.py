"""Spaces: one Android user per brand (PLAN §3, §4.2, §4.8).

A space is created fresh, never reused by another brand; deleting the user (not clearing app data) is what gives
the next brand new Android IDs. The owner user (0) is G2G's space and is never wiped, never gets a VPN, and is
always left on the home screen with no space open (§9).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .adb import AndroidUser, Phone

log = logging.getLogger("robotapp")

# Apps a US space gets (§4.2 step 5). G2G's owner user already has its own.
SPACE_PACKAGES = (
    "com.zhiliaoapp.musically",
    "com.instagram.android",
    "com.google.android.youtube",
    "io.nekohasekai.sfa",
    "com.android.chrome",  # the leak check needs a browser inside the space (§4.5)
)
# Media permissions granted up front; location and contacts are deliberately NOT granted (§4.2 step 6).
SPACE_PERMISSIONS = (
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
)


@dataclass
class Space:
    user_id: int
    name: str
    running: bool = False


class Spaces:
    def __init__(self, phone: Phone) -> None:
        self.phone = phone

    # -- reading -----------------------------------------------------------------------------------
    def list(self) -> list[AndroidUser]:
        return self.phone.users()

    def free_slots(self) -> int:
        return max(0, self.phone.max_users() - len(self.phone.users()))

    def owner_running(self) -> bool:
        return any(u.owner and u.running for u in self.phone.users())

    # -- creating ----------------------------------------------------------------------------------
    def create(self, name: str, packages: tuple[str, ...] = SPACE_PACKAGES) -> Space:
        """Create the user, skip its setup wizard, start it, and put the apps and permissions in place."""
        user_id = self.phone.create_user(name)
        # The setup wizard would block the first open; mark it done and disable the wizard for this user.
        self.phone.settings_put("secure", "user_setup_complete", "1", user_id)
        try:
            self.phone.shell(f"pm disable-user --user {user_id} com.google.android.setupwizard")
        except Exception:  # noqa: BLE001 - absent on some builds, and that is fine
            pass
        self.phone.start_user(user_id)
        self.configure(user_id)
        for package in packages:
            try:
                self.phone.install_existing(package, user_id)
            except Exception as exc:  # noqa: BLE001 - a missing app is reported, not fatal here
                log.warning("could not install %s into user %s: %s", package, user_id, exc)
        self.grant_media(user_id)
        return Space(user_id, name, True)

    def configure(self, user_id: int) -> None:
        """US-shaped settings: location off, English, a long screen timeout, no auto-rotate surprises."""
        self.phone.settings_put("secure", "location_mode", "0", user_id)
        self.phone.settings_put("system", "screen_off_timeout", "1800000", user_id)  # 30 min
        self.phone.settings_put("system", "accelerometer_rotation", "0", user_id)

    def grant_media(self, user_id: int, packages: tuple[str, ...] = SPACE_PACKAGES) -> None:
        for package in packages:
            for permission in SPACE_PERMISSIONS:
                try:
                    self.phone.grant(package, permission, user_id)
                except Exception:  # noqa: BLE001 - an app that does not declare it is not an error
                    pass
            # Notifications off, and the battery manager must not kill the proxy (§4.2 step 10).
            try:
                self.phone.appops(package, "POST_NOTIFICATION", "ignore", user_id)
            except Exception:  # noqa: BLE001
                pass
            try:
                self.phone.appops(package, "RUN_ANY_IN_BACKGROUND", "allow", user_id)
            except Exception:  # noqa: BLE001
                pass

    # -- running -----------------------------------------------------------------------------------
    def start(self, user_id: int) -> None:
        self.phone.start_user(user_id)

    def stop(self, user_id: int) -> None:
        self.phone.stop_user(user_id)

    def switch_to(self, user_id: int) -> None:
        self.phone.switch_user(user_id)

    def leave_owner_front(self) -> None:
        """The state the phone must be left in (§9): owner user in front, no space open."""
        self.phone.switch_user(0)

    # -- deleting ----------------------------------------------------------------------------------
    def delete(self, user_id: int) -> str:
        if user_id == 0:
            raise ValueError("the owner user is never deleted")
        return self.phone.remove_user(user_id)

    def wipe(self, user_id: int) -> None:
        """§4.8: stop it, remove the user. The next brand gets a fresh user with new Android IDs."""
        if user_id == 0:
            raise ValueError("the owner user is never wiped")
        try:
            self.phone.stop_user(user_id)
        except Exception:  # noqa: BLE001 - already stopped is fine
            pass
        self.phone.remove_user(user_id)
