"""The write-ahead journal (PLAN §6.4): Post is pressed once, and the record survives a crash."""

from pathlib import Path

from robotapp.journal import FAILED, POSTED, PRESSED, UNSURE, Journal, write_status


def journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path / "robot.db")


def test_post_pressed_is_written_once(tmp_path) -> None:
    j = journal(tmp_path)
    j.start_job("job-1", "post")
    assert j.mark("job-1", PRESSED, "upload-1", "tiktok") is True
    assert j.mark("job-1", PRESSED, "upload-1", "tiktok") is False  # the second tap is refused
    assert j.pressed("job-1", "upload-1") is True
    assert j.pressed("job-1", "upload-2") is False
    j.close()


def test_the_record_survives_a_restart(tmp_path) -> None:
    path = tmp_path / "robot.db"
    first = Journal(path)
    first.start_job("job-1", "post")
    first.mark("job-1", PRESSED, "upload-1", "tiktok")
    first.close()

    again = Journal(path)
    assert again.pressed("job-1", "upload-1") is True
    assert again.mark("job-1", PRESSED, "upload-1", "tiktok") is False
    again.close()


def test_outcomes(tmp_path) -> None:
    j = journal(tmp_path)
    j.start_job("job-1", "post")
    j.mark("job-1", PRESSED, "upload-1")
    j.mark("job-1", UNSURE, "upload-1", detail={"reason": "upload not confirmed"})
    assert j.outcome("job-1", "upload-1") == UNSURE
    j.mark("job-1", POSTED, "upload-1", detail={"url": "https://tiktok.com/x"})
    assert j.outcome("job-1", "upload-1") == UNSURE  # unsure wins: the robot still looks for the post
    assert [e.event for e in j.events("job-1")] == [PRESSED, UNSURE, POSTED]
    j.close()


def test_failed_before_post_is_recorded(tmp_path) -> None:
    j = journal(tmp_path)
    j.start_job("job-1", "post")
    j.mark("job-1", FAILED, "upload-1", detail={"reason": "VPN down"})
    assert j.outcome("job-1", "upload-1") == FAILED
    assert j.pressed("job-1", "upload-1") is False
    j.close()


def test_status_file_is_written_atomically(tmp_path) -> None:
    path = tmp_path / "status.json"
    write_status(path, {"job": "post", "state": "running"})
    assert '"state": "running"' in path.read_text(encoding="utf-8")
    write_status(path, {"job": "post", "state": "idle"})
    assert '"state": "idle"' in path.read_text(encoding="utf-8")
    assert not path.with_suffix(".json.tmp").exists()
