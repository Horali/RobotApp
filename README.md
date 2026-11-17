# RobotApp

The phone robot: a small program on the laptop that drives an old Android phone over adb to post a clip
channel's videos from the phone's own TikTok / Instagram / YouTube apps. ClipMaker owns the posting queue and
calls this; it also runs on its own from the command line.

The full plan, every decision and the current progress live in **[PLAN.md](PLAN.md)**. Read that first.

## The one rule that shapes everything

**The robot touches the phone only between 06:00 and 10:00 WIB.** Outside that the phone belongs to other
scripts, so the robot sends no commands at all. Every phone call goes through `robotapp/window.py`, which
refuses outside the window; a Post is never pressed after 09:55.

The phone is also shared through a lock file (`%LOCALAPPDATA%\PhoneLock\phone.lock`): whoever holds it may
drive the phone. The robot takes it at the start of a job and gives it back at the end.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env      # then fill in CHAMELEON_TOKEN
```

`.env` is git-ignored. It holds Chameleon's bearer token; no password ever goes into it, or into the repo.

The phone must be reachable over adb (`adb devices` shows `192.168.1.8:5555`). Wi-Fi adb is lost on every
reboot until step 2 adds the Keeper app.

## Commands

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli window            # inside 06:00-10:00 WIB?
.\.venv\Scripts\python.exe -m robotapp.cli lock status       # who holds the phone
.\.venv\Scripts\python.exe -m robotapp.cli doctor            # battery, heat, users, free spaces, apps
.\.venv\Scripts\python.exe -m robotapp.cli provision --space-name "US 1" --proxy-id <id> --clean
.\.venv\Scripts\python.exe -m robotapp.cli login tiktok --user 11 --profile-id <id> --email <address>
.\.venv\Scripts\python.exe -m robotapp.cli post tiktok --user 11 --video C:\clips\x.mp4 --caption "..." --hashtags "#tag"
.\.venv\Scripts\python.exe -m robotapp.cli status <job id>
```

Events are JSON lines on stdout (`step`, `needs`, `done`, `error`); human logs go to stderr and to
`data/logs/<date>.log`. `data/` is git-ignored: it holds `robot.db` (the write-ahead journal), screenshots and
logs. Add `--fake` to run a command against the fake phone instead of adb.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The tests use `FakePhone` and `FakeScreen` (in `robotapp/fake.py`), so they need no phone and no network. They
cover the time window, the phone lock, the journal's "never press Post twice", `doctor`, and the secret handling
(a password cannot be printed).

## Layout

```
robotapp/
  adb.py        the phone over adb (AdbPhone) and the shared parsers
  fake.py       FakePhone / FakeScreen for tests
  window.py     the 06:00-10:00 guard and the shared phone lock
  journal.py    the write-ahead journal (data/robot.db) and data/status.json
  doctor.py     `robot doctor`
  secrets.py    the Chameleon client: a password is fetched only when it is typed
  log.py        logging that redacts secrets
  spaces.py     create / start / wipe Android users
  timezone.py   New York / Jakarta switching, G2G's apps frozen first
  vpn.py        sing-box config, import, always-on + lockdown
  leakcheck.py  the VPN / IP / DNS / time-zone checks before a sitting
  media.py      pushing the clip into a space's gallery
  ui.py         reading the screen and tapping it (uiautomator2)
  login/tiktok.py, post/tiktok.py, engage.py
  cli.py        the `robot` command
```
