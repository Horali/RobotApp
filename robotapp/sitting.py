"""One brand's sitting: its due posts, in order (PLAN §6.3, §8.2).

A sitting is what ClipMaker asks for: one brand, its posts for today, in the order Instagram → TikTok → YouTube
(US brands) or TikTok → YouTube (G2G). Each post gets its own engagement; the brand's apps are not separated by a
gap, but two brands are (that gap is ClipMaker's job, not the robot's).

The JSON is the contract from §8.2. Step 1 runs TikTok only; the other platforms answer
`failed_before_post` with a clear reason until their steps are built.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .adb import Phone
from .errors import RobotError
from .journal import Journal
from .media import find_media_uri, push_video
from .post.base import FAILED, PostResult, PostSpec
from .post.instagram import INSTAGRAM as INSTAGRAM_PACKAGE, InstagramPoster
from .post.tiktok import TikTokPoster, tiktok_package
from .post.youtube import YOUTUBE as YOUTUBE_PACKAGE, YouTubePoster
from .secrets import Chameleon
from .ui import Screen
from .window import WIB, build_mode, post_allowed

log = logging.getLogger("robotapp")

PROTO = 1


@dataclass
class Sitting:
    job_id: str
    brand: str
    posts: list[PostSpec]
    user: int | None = None
    time_zone: str = "Asia/Jakarta"
    engage_minutes: tuple[float, float] = (3.0, 5.0)
    must_finish_by: datetime | None = None
    read_views: list[dict] = field(default_factory=list)

    @classmethod
    def from_json(cls, body: dict) -> "Sitting":
        if body.get("proto") != PROTO:
            raise RobotError(f"unknown protocol version: {body.get('proto')!r} (this robot speaks {PROTO})")
        job_id = str(body.get("job_id") or "").strip()
        if not job_id:
            raise RobotError("the sitting has no job_id")
        posts = []
        for row in body.get("posts") or []:
            posts.append(
                PostSpec(
                    upload_id=str(row.get("upload_id") or ""),
                    platform=str(row.get("platform") or ""),
                    video=Path(row.get("video") or ""),
                    length_s=float(row["length_s"]) if row.get("length_s") else None,
                    caption=str(row.get("caption") or ""),
                    hashtags=[str(t) for t in (row.get("hashtags") or [])],
                    title=str(row.get("title") or ""),
                    sound=row.get("sound"),
                    sound_required=bool(row.get("sound_required")),
                    pinned_comment=str(row.get("pinned_comment") or ""),
                )
            )
        window = tuple(body.get("engage_minutes") or (3, 5))
        finish = body.get("must_finish_by")
        deadline = datetime.fromisoformat(finish.replace("Z", "+00:00")) if finish else None
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=WIB)
        return cls(
            job_id=job_id,
            brand=str(body.get("brand") or ""),
            posts=posts,
            user=int(body["user"]) if body.get("user") is not None else None,
            time_zone=str(body.get("time_zone") or "Asia/Jakarta"),
            engage_minutes=(float(window[0]), float(window[1])),
            must_finish_by=deadline,
            read_views=list(body.get("read_views") or []),
        )


def run(
    sitting: Sitting,
    phone: Phone,
    screen: Screen,
    journal: Journal,
    chameleon: Chameleon,
    emit,
    shots_dir: Path | None = None,
    dry_run: bool = False,
) -> list[PostResult]:
    """Run the sitting. Returns one result per post, in order; emits a `done` event per post."""
    journal.start_job(sitting.job_id, "sitting", brand=sitting.brand, payload={"posts": len(sitting.posts)})
    results: list[PostResult] = []
    pushed: dict[str, str] = {}
    user = sitting.user if sitting.user is not None else _user_of(phone)

    for index, spec in enumerate(sitting.posts, start=1):
        emit({"t": "step", "job": sitting.job_id, "post": spec.upload_id, "n": index, "of": len(sitting.posts), "name": "start"})
        if not post_allowed() and not build_mode():
            result = PostResult(spec.upload_id, spec.platform, FAILED, reason="past 09:55 WIB: no post today")
            emit(result.as_event())
            results.append(result)
            continue
        if sitting.must_finish_by and datetime.now(WIB) >= sitting.must_finish_by:
            result = PostResult(spec.upload_id, spec.platform, FAILED, reason="the sitting's deadline has passed")
            emit(result.as_event())
            results.append(result)
            continue

        if spec.video and spec.video.exists() and str(spec.video) not in pushed:
            remote = pushed[str(spec.video)] = push_video(phone, spec.video, user)
            spec.media_uri = find_media_uri(phone, user, remote)
            emit({"t": "info", "name": "video pushed", "remote": remote, "media_uri": spec.media_uri})

        if spec.platform == "tiktok":
            package = tiktok_package(user)
            poster = TikTokPoster(
                phone, screen, journal, sitting.job_id, package=package, user=user, emit=emit, shots_dir=shots_dir
            )
        elif spec.platform == "instagram":
            poster = InstagramPoster(
                phone, screen, journal, sitting.job_id, package=INSTAGRAM_PACKAGE, user=user, emit=emit, shots_dir=shots_dir
            )
        elif spec.platform == "youtube":
            poster = YouTubePoster(
                phone, screen, journal, sitting.job_id, package=YOUTUBE_PACKAGE, user=user, emit=emit, shots_dir=shots_dir
            )
        else:
            result = PostResult(
                spec.upload_id,
                spec.platform,
                FAILED,
                reason=f"the {spec.platform} flow is not built yet",
            )
            emit(result.as_event())
            results.append(result)
            continue
        result = poster.post(spec, dry_run=dry_run)
        emit(result.as_event())
        results.append(result)

    journal.set_state(sitting.job_id, "done" if all(r.ok for r in results) else "finished_with_failures")
    return results


def _user_of(phone: Phone) -> int:
    try:
        return phone.current_user()
    except Exception:  # noqa: BLE001 - a phone that cannot answer is the owner's
        return 0
