# HANDOFF — RobotApp

RobotApp drives a real Android phone (Infinix X6815D, Android 13) over adb + uiautomator2. It
posts clips through the phone's own Instagram / TikTok / YouTube apps (no web APIs) and reads
back post links. ClipMaker owns the schedule and hands RobotApp a JSON "sitting" job.
Repo: github.com/Horali/RobotApp, branch `main`.

## Entry points
- `.\.venv\Scripts\python.exe -m robotapp.cli <cmd>` (add `--fake` to run against the fake phone).
- Sandboxed harness: venv python can hit `0xC0000142`; run base Python 3.12 with `PYTHONPATH` set
  to the repo + `.venv\Lib\site-packages`, and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.
- Read `PLAN.md` first (Progress section = current state), then the task file.

## Hard rules
- Post only 06:00–10:00 WIB. `ROBOTAPP_BUILD_MODE=1` only for build/inspection, never posting.
- Never press Post/Share/Upload twice (journal enforces one claim per upload).
- Never touch User 0. Brand work in Users 10/11/12. Leave phone on User 0, Asia/Jakarta, lock=free.
- Never solve CAPTCHAs: pause (NeedsHuman) and let Queen Hora type on the phone.
- GTA 6 Clips (`a71775cde9e44208b00c71b2be00fdce`) is off-limits.
- Git: account Horali, Conventional Commits, no AI attribution, never commit data/ .env media .venv.

## Current state (2026-11-24)
- Goal 1 done: `vtubers Clips` (User 11) is 3/3 live (IG, TT, YT).
- Goal 2 in progress: 2/6 brand logins done (Speed YT, Timmy YT). Remaining: Speed IG (needs
  CAPTCHA), Timmy IG (spins on Log in), Speed TT + Timmy TT (spin on Continue; Google already
  signed in to Android OS — try "Continue with Google").
- No queued uploads in ClipMaker, no running jobs in RobotApp. Phone was asleep/disconnected at handoff.

## Linked projects
- ClipMaker (`../ClipMaker`, API http://localhost:8765) runs RobotApp as a subprocess and owns the
  schedule. It has a `--fake` mode for tests. It reads RobotApp `data/status.json` — keep that contract.
- Chameleon (`C:\Users\child\PROJECTS\CustomBrowser\app`, API http://127.0.0.1:38100) stores proxies
  and credentials. Unset `ELECTRON_RUN_AS_NODE` before launching Electron.

## Active tasks
(none yet — add one line per task with its task file path, e.g. `handoffs/<slug>.md`)

## Where to look
- `PLAN.md` — source of truth (Progress section first).
- `README.md` — commands, layout, tests.
- Old handoffs (kept for history, read newest first):
  - `docs/handoff-2026-11-24.md`
  - `docs/handoff-2026-11-23.md`
  - `docs/handoff-2026-11-21.md`
  - `docs/handoff-prompt.md`
  - `docs/proxy-udp-handoff-prompt.md`
