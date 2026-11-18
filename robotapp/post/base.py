"""What a post is, and what came of it (PLAN §8.2, §8.5).

The journal decides the outcome: an error before the press is `failed_before_post` (the post goes back to the
queue), an error after it is `unsure_after_post` (the robot looks for the post and reports its link; the Post
button is never pressed again).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

POSTED = "posted"
UNSURE = "unsure_after_post"
FAILED = "failed_before_post"


def split_caption(caption: str) -> tuple[str, list[str]]:
    """ClipMaker's own split (phone_posts.split_tags): the text, then the hashtags typed one by one."""
    tags = re.findall(r"#\w+", caption or "")
    return re.sub(r"[ \t]*#\w+", "", caption or "").strip(), tags


@dataclass
class PostSpec:
    upload_id: str
    platform: str
    video: Path
    length_s: float | None = None
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    title: str = ""  # YouTube
    sound: str | None = None  # "trending" | None
    sound_required: bool = False
    pinned_comment: str = ""  # YouTube
    media_uri: str | None = None  # content:// of the pushed clip, for a share intent

    @property
    def full_caption(self) -> str:
        tags = " ".join(t for t in self.hashtags if t)
        return " ".join(part for part in (self.caption.strip(), tags) if part)


@dataclass
class PostResult:
    upload_id: str
    platform: str
    outcome: str
    url: str | None = None
    handle: str | None = None
    reason: str | None = None
    engaged_s: float = 0.0
    sound: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome == POSTED

    def as_event(self) -> dict[str, object]:
        body: dict[str, object] = {
            "t": "done",
            "post": self.upload_id,
            "platform": self.platform,
            "outcome": self.outcome,
            "engaged_s": round(self.engaged_s, 1),
            "sound": self.sound,
        }
        if self.url:
            body["url"] = self.url
        if self.handle:
            body["handle"] = self.handle
        if self.reason:
            body["reason"] = self.reason
        return body
