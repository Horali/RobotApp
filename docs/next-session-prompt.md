# Prompt for the next session (copy-paste into a new chat)

RobotApp project, continuing straight from `docs/handoff-2026-11-21.md` — **read that file first**, then
`PLAN.md` (Progress at the top) and `docs/step1-runbook.md`.

**What we're doing:** the throwaway brand **vtubers Clips** must post its first three posts **by the robot,
from the phone's own apps, all three: Instagram → TikTok → YouTube**. The profiles are graduated, the
campaign exists, and three rows are already queued in ClipMaker and due at 06:00 WIB:

- instagram `b988d8b5d5334c3ba81661b49ea75a66` (@vtubersclips90)
- tiktok `92a0c985d2314f6e92e36d6df272cf85` (@vtubersclips70)
- youtube `038412461d60436faf123cac7bd58b0d` (channel "Horali Cript", see the handoff)

**Start by:**
1. `robot doctor` — phone online (USB serial `0953925324001286` works on any network; Wi-Fi is
   `192.168.1.8:5555`), battery under 42 °C, inside 06:00–10:00 WIB.
2. Restart ClipMaker's app (its running process has old code), or run the sitting by hand:
   `.venv\Scripts\python.exe tools\phone_robot.py tick` in `C:\Users\child\PROJECTS\ClipMaker`.
3. Watch the JSON events. `posted` + url = done; `failed_before_post` = it stopped before pressing anything,
   the row is back on the line: fix that screen and run the tick again.

**Two known blockers, in this order:**
- **TikTok**: after the bottom bar's Create, Play's "TikTok needs to download additional files" sheet takes
  over (the installed musically is the base APK; Play wants the dynamic modules). Best fix: install the
  **bundle** variant of 47.9.1 from the same APKMirror listing in user 11 (same signer
  `9041803e…cf2ab5ba`, check it first), which removes the request — the TikTok login then has to be redone
  with a code to the Gmail (ask the user for the code; the robot has `--code-file` for that).
- **YouTube**: the channel exists but is named **"Horali Cript"** (account default, id
  `UCl1ZpgCNfkIGhtf-Af3f5nQ`). Ask the user: rename it to "vtubers Clips" (2 min on the laptop in Studio →
  Customization → Profile) or post as it is. The YouTube poster has never run on a real screen, so expect
  1–2 selector fixes on its first run, the same way Instagram and TikTok needed them.

**Rules that must hold:** phone only 06:00–10:00 WIB (`ROBOTAPP_BUILD_MODE=1` for build work outside it);
**never press Post twice** (the journal is the guard); **never post in user 0** — that is the user's own
accounts; **GTA 6 Clips is a real brand and is never a test subject**; the "shadowban pauses posting" change
was **reverted on purpose** — don't re-apply it; small Conventional Commits, push to main, no AI attribution,
`gh auth switch -h github.com -u Horali` first.

**Timing that matters:** Instagram's evening window closes at **09:00 WIB** (21:00 New York), TikTok's at
10:00 WIB. Start the sitting at 06:00–06:30 or Instagram waits another day. A clip download into the space
takes 2–4 minutes.

**How I want you to work:** one step at a time, each proven on the phone before the next; show me the
posted links as they come; keep output short; commit and update `PLAN.md` as soon as a step is green. If a
screen is unknown, stop there and fix the selector rather than hammering the app.
