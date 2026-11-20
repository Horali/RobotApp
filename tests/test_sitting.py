"""The sitting contract (PLAN §8.2): what ClipMaker sends, and what the robot refuses."""

import pytest

from robotapp.errors import RobotError
from robotapp.sitting import Sitting

BODY = {
    "proto": 1,
    "job_id": "job-1",
    "brand": "G2GChannel Clips",
    "user": 0,
    "time_zone": "Asia/Jakarta",
    "posts": [
        {
            "upload_id": "u1",
            "platform": "tiktok",
            "video": "C:/clips/x.mp4",
            "length_s": 61.6,
            "caption": "a caption",
            "hashtags": ["#g2g", "#shorts"],
        }
    ],
    "engage_minutes": [3, 5],
    "must_finish_by": "2026-11-18T02:00:00Z",
}


def test_a_sitting_is_read_as_the_plan_describes() -> None:
    sitting = Sitting.from_json(BODY)
    assert sitting.job_id == "job-1"
    assert sitting.user == 0
    assert sitting.time_zone == "Asia/Jakarta"
    assert sitting.engage_minutes == (3.0, 5.0)
    assert sitting.must_finish_by is not None and sitting.must_finish_by.tzinfo is not None
    post = sitting.posts[0]
    assert post.upload_id == "u1"
    assert post.platform == "tiktok"
    assert post.length_s == 61.6
    assert post.hashtags == ["#g2g", "#shorts"]


def test_a_naive_deadline_is_read_as_wib() -> None:
    sitting = Sitting.from_json({**BODY, "must_finish_by": "2026-11-18T09:55:00"})
    assert sitting.must_finish_by is not None
    assert sitting.must_finish_by.utcoffset().total_seconds() == 7 * 3600


def test_another_protocol_version_is_refused() -> None:
    with pytest.raises(RobotError):
        Sitting.from_json({**BODY, "proto": 2})


def test_a_sitting_without_a_job_id_is_refused() -> None:
    with pytest.raises(RobotError):
        Sitting.from_json({**BODY, "job_id": ""})


def test_a_sitting_without_a_user_is_refused(tmp_path, capsys) -> None:
    """Never guess the space. On 2026-11-20 a sitting with no user ran in whichever user was in front
    - the owner user, the user's own Instagram - one step from posting there."""
    import argparse
    import json

    from robotapp.cli import EXIT_ERROR, cmd_sitting
    from robotapp.config import Settings

    body = {k: v for k, v in BODY.items() if k != "user"}
    path = tmp_path / "sitting.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    args = argparse.Namespace(file=str(path), dry_run=True, fake=True, json=False)
    settings = Settings(data_dir=tmp_path / "data")
    assert cmd_sitting(args, settings) == EXIT_ERROR
    out = capsys.readouterr().out
    assert "refusing to guess" in out
