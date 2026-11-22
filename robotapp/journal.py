"""The write-ahead journal: the robot's memory of what it already pressed (PLAN §6.4, §6.7).

The rule the user cares about most: **never press Post/Share/Upload twice**. Before the tap the robot writes
`post_pressed` to disk; if anything goes wrong after that, the outcome is "unsure" and the robot *looks* for the
post instead of pressing again. The database enforces it too: one row per (job, upload, event), so a second
`post_pressed` returns False and the caller must not tap.

SQLite (WAL) in `data/robot.db`, which is git-ignored. `data/status.json` is written by the CLI for callers that
want a quick "what is the phone doing now" (§8.1).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .window import WIB

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id          TEXT PRIMARY KEY,
  brand       TEXT,
  kind        TEXT NOT NULL,
  state       TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  payload     TEXT
);
CREATE TABLE IF NOT EXISTS journal (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id      TEXT NOT NULL,
  upload_id   TEXT,
  platform    TEXT,
  event       TEXT NOT NULL,
  at          TEXT NOT NULL,
  detail      TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS journal_once ON journal(job_id, upload_id, event);
CREATE INDEX IF NOT EXISTS journal_job ON journal(job_id, id);
"""

# Events a post can go through, in order. Terminal ones are written once.
PRESSED = "post_pressed"
POSTED = "posted"
UNSURE = "unsure_after_post"
FAILED = "failed_before_post"


@dataclass
class Event:
    job_id: str
    upload_id: str | None
    platform: str | None
    event: str
    at: str
    detail: dict | None

    def as_dict(self) -> dict[str, object]:
        return {
            "job": self.job_id,
            "upload_id": self.upload_id,
            "platform": self.platform,
            "event": self.event,
            "at": self.at,
            "detail": self.detail or {},
        }


def _now() -> str:
    return datetime.now(WIB).isoformat(timespec="seconds")


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None)  # autocommit: a crash must not lose a press
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # -- jobs --------------------------------------------------------------------------------------
    def start_job(self, job_id: str, kind: str, brand: str | None = None, payload: dict | None = None) -> None:
        at = _now()
        self.db.execute(
            "INSERT OR IGNORE INTO jobs (id, brand, kind, state, created_at, updated_at, payload) VALUES (?,?,?,?,?,?,?)",
            (job_id, brand, kind, "running", at, at, json.dumps(payload or {}, ensure_ascii=False)),
        )

    def set_state(self, job_id: str, state: str) -> None:
        self.db.execute("UPDATE jobs SET state = ?, updated_at = ? WHERE id = ?", (state, _now(), job_id))

    def job(self, job_id: str) -> dict[str, object] | None:
        row = self.db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    # -- the journal -------------------------------------------------------------------------------
    def mark(
        self,
        job_id: str,
        event: str,
        upload_id: str | None = None,
        platform: str | None = None,
        detail: dict | None = None,
    ) -> bool:
        """Write one event. Returns False when it was already there (so `post_pressed` can never double-tap)."""
        try:
            self.db.execute(
                "INSERT INTO journal (job_id, upload_id, platform, event, at, detail) VALUES (?,?,?,?,?,?)",
                (job_id, upload_id, platform, event, _now(), json.dumps(detail or {}, ensure_ascii=False)),
            )
        except sqlite3.IntegrityError:
            return False
        return True

    def claim_press(self, job_id: str, upload_id: str | None, platform: str | None = None) -> tuple[bool, str | None]:
        """Ask permission to tap Post and write the record in one step. (True, None) or (False, why).

        The guard is **per upload, not per job**: one upload is one post, and ClipMaker starts a new job
        for every sitting. Until 2026-11-22 the unique index only stopped a second press inside one job,
        so the same row was pressed again by the next job (TikTok's Post: 07:52, 07:57, then 06:03 the
        next morning; Instagram's Share: four times). A press is now claimed for the upload forever;
        `release_press` is the one deliberate way back.
        """
        row = self.db.execute(
            "SELECT job_id, at FROM journal WHERE event = ? AND upload_id IS ? ORDER BY id LIMIT 1",
            (PRESSED, upload_id),
        ).fetchone()
        if row is not None:
            if row["job_id"] == job_id:
                return False, "Post was already pressed for this upload; not pressing again"
            return False, (
                f"Post was already pressed for this upload in job {row['job_id']} at {row['at']}; "
                "not pressing again — look for the post on the account instead"
            )
        if not self.mark(job_id, PRESSED, upload_id, platform):
            return False, "Post was already pressed for this upload; not pressing again"
        return True, None

    def release_press(self, upload_id: str, reason: str) -> int:
        """Undo a press claim — only for a human who has looked and seen that nothing was published.

        Keeps the old rows (they are the audit trail) but deletes the claim so the next job may press.
        Returns how many claim rows were removed.
        """
        rows = self.db.execute(
            "SELECT id FROM journal WHERE event = ? AND upload_id IS ?", (PRESSED, upload_id)
        ).fetchall()
        self.db.execute("DELETE FROM journal WHERE event = ? AND upload_id IS ?", (PRESSED, upload_id))
        for row in rows:
            self.mark(
                f"release-press-{row['id']}",
                "press_released",
                upload_id,
                detail={"reason": reason},
            )
        return len(rows)

    def has(self, job_id: str, event: str, upload_id: str | None = None) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM journal WHERE job_id = ? AND event = ? AND (upload_id IS ? OR upload_id = ?)",
            (job_id, event, upload_id, upload_id),
        ).fetchone()
        return row is not None

    def pressed(self, job_id: str, upload_id: str | None) -> bool:
        """The one question that decides whether the robot may tap Post: was it pressed already?"""
        return self.has(job_id, PRESSED, upload_id)

    def events(self, job_id: str) -> list[Event]:
        rows = self.db.execute("SELECT * FROM journal WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()
        return [
            Event(r["job_id"], r["upload_id"], r["platform"], r["event"], r["at"], json.loads(r["detail"] or "{}"))
            for r in rows
        ]

    def outcome(self, job_id: str, upload_id: str | None) -> str | None:
        for event in (UNSURE, POSTED, FAILED):
            if self.has(job_id, event, upload_id):
                return event
        return None


def write_status(path: Path, status: dict) -> None:
    """`data/status.json`: what the phone is doing now, for ClipMaker's Phone page (§8.1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"updated_at": _now(), **status}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
