"""Brands and spaces over time (PLAN sections 7.1, 7.3; step 9).

RobotApp keeps its own small registry in `data/robot.db` (git-ignored), separate from ClipMaker's
queue: which brand lives in which Android user, and what state each is in.

    brand states:   waiting -> assigned -> logging_in -> ready -> posting -> graduated -> released
    space states:   free -> building -> ready(brand) -> wiping -> free
    G2G in the owner user: always ready, never wiped.

The robot is the only writer, so the registry is a plain SQLite file: no server, no lock beyond the
phone lock the jobs already take.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .window import WIB

SCHEMA = """
CREATE TABLE IF NOT EXISTS spaces (
  user_id    INTEGER PRIMARY KEY,
  name       TEXT,
  state      TEXT NOT NULL,              -- free | building | ready | wiping | broken
  brand_id   TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS brands (
  brand_id   TEXT PRIMARY KEY,
  name       TEXT,
  network    TEXT,                       -- {"proxy": "<chameleon id>"} or {"home": "ID"}
  space_user INTEGER,
  state      TEXT NOT NULL,              -- waiting | assigned | logging_in | ready | posting | graduated | released | blocked
  accounts   TEXT,                       -- [{"platform", "profile_id", "email_account_id", "handle"}]
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

COUNTED_USERS = (0,)  # the owner user is G2G's space and is never a "free" slot to hand out
MAX_USERS_DEFAULT = 4


def _now() -> str:
    return datetime.now(WIB).isoformat(timespec="seconds")


@dataclass
class Brand:
    brand_id: str
    name: str
    network: dict
    space_user: int | None
    state: str
    accounts: list[dict]

    @property
    def home(self) -> bool:
        """A brand with no proxy: G2G, in Indonesia, in the owner user."""
        return bool(self.network.get("home"))


class Registry:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # -- brands ------------------------------------------------------------------------------------
    def add_brand(self, brand_id: str, name: str, network: dict, accounts: list[dict] | None = None) -> Brand:
        """A new brand waits for a space; G2G (a home brand) is ready at once, in the owner user."""
        now = _now()
        home = bool(network.get("home"))
        space = 0 if home else None
        state = "ready" if home else "waiting"
        self.db.execute(
            "INSERT INTO brands (brand_id, name, network, space_user, state, accounts, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(brand_id) DO UPDATE SET "
            "name=excluded.name, network=excluded.network, accounts=excluded.accounts, updated_at=excluded.updated_at",
            (brand_id, name, json.dumps(network), space, state, json.dumps(accounts or []), now, now),
        )
        if home:
            self._space(0, "owner", "ready", brand_id)
        return self.brand(brand_id)  # type: ignore[return-value]

    def brand(self, brand_id: str) -> Brand | None:
        row = self.db.execute("SELECT * FROM brands WHERE brand_id = ?", (brand_id,)).fetchone()
        return Brand(row["brand_id"], row["name"], json.loads(row["network"] or "{}"),
                     row["space_user"], row["state"], json.loads(row["accounts"] or "[]")) if row else None

    def brands(self) -> list[Brand]:
        return [Brand(r["brand_id"], r["name"], json.loads(r["network"] or "{}"), r["space_user"],
                      r["state"], json.loads(r["accounts"] or "[]"))
                for r in self.db.execute("SELECT * FROM brands ORDER BY created_at")]

    def set_brand_state(self, brand_id: str, state: str) -> None:
        self.db.execute("UPDATE brands SET state = ?, updated_at = ? WHERE brand_id = ?", (state, _now(), brand_id))

    # -- spaces ------------------------------------------------------------------------------------
    def _space(self, user_id: int, name: str, state: str, brand_id: str | None) -> None:
        self.db.execute(
            "INSERT INTO spaces (user_id, name, state, brand_id, updated_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, state=excluded.state, "
            "brand_id=excluded.brand_id, updated_at=excluded.updated_at",
            (user_id, name, state, brand_id, _now()),
        )

    def spaces(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM spaces ORDER BY user_id")]

    def free_slots(self, max_users: int = MAX_USERS_DEFAULT) -> int:
        """Android users still available: the limit counts the owner, and a space in use is not free."""
        used = 1 + len([r for r in self.db.execute("SELECT user_id FROM spaces")
                        if r["user_id"] not in COUNTED_USERS])
        return max(0, max_users - used)

    def assign(self, brand_id: str, user_id: int, name: str = "") -> Brand:
        """Put a waiting brand into a space (the caller creates the Android user first)."""
        self._space(user_id, name or f"space {user_id}", "building", brand_id)
        self.db.execute("UPDATE brands SET space_user = ?, state = 'assigned', updated_at = ? WHERE brand_id = ?",
                        (user_id, _now(), brand_id))
        return self.brand(brand_id)  # type: ignore[return-value]

    def mark_ready(self, brand_id: str) -> None:
        brand = self.brand(brand_id)
        if brand and brand.space_user is not None:
            self._space(brand.space_user, "", "ready", brand_id)
        self.set_brand_state(brand_id, "ready")

    def release(self, brand_id: str) -> int | None:
        """A brand leaves the phone: its space goes to `wiping` and the caller wipes it.

        The owner user is never released: G2G is permanent (section 3.3).
        """
        brand = self.brand(brand_id)
        if brand is None or brand.space_user is None:
            return None
        if brand.space_user == 0:
            raise ValueError("the owner user is G2G's space and is never released")
        self._space(brand.space_user, "", "wiping", None)
        self.db.execute("UPDATE brands SET space_user = NULL, state = 'released', updated_at = ? WHERE brand_id = ?",
                        (_now(), brand_id))
        return brand.space_user

    def space_wiped(self, user_id: int) -> None:
        """After `pm remove-user`: the slot is free again."""
        self.db.execute("DELETE FROM spaces WHERE user_id = ?", (user_id,))

    def next_waiting(self) -> Brand | None:
        row = self.db.execute("SELECT brand_id FROM brands WHERE state = 'waiting' ORDER BY created_at LIMIT 1").fetchone()
        return self.brand(row["brand_id"]) if row else None
