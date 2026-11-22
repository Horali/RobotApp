# Morning run — 2026-11-23, the throwaway's YouTube Short

State as of 2026-11-22 15:50 WIB: **only the YouTube row is still queued.** Instagram and TikTok are
live and marked posted in ClipMaker (links in `docs/report-2026-11-22.md`); quote their links again in
the report, but do not touch those rows or profiles.

- YouTube row: `038412461d60436faf123cac7bd58b0d`, channel **Horali Cript** (`UCl1ZpgCNfkIGhtf-Af3f5nQ`),
  posting **as is** — the user chose that on 2026-11-21. Clip: `twitch_2899844366_108_v5.mp4`, 48 s.
- Sitting file: **`data/robot-sit-youtube-1123.json`** (job `morning-youtube-1123`, user 11, deadline
  09:55 WIB, caption clean — the old file's caption was double-encoded mojibake, 175 MB of it).
- The YouTube Upload has **never been pressed** for this upload, so the press guard will allow exactly
  one press.

## The run

1. `robot doctor` — must be green, inside 06:00–10:00 WIB, battery < 42 °C.
2. First look at `data/status.json` and `data/robot.db` (`job`, `state`): if ClipMaker's own tick is
   already running a sitting, **wait for it** — two senders is the one thing the phone lock must not
   arbitrate twice.
3. Run it by hand, watching the JSON events:
   `C:\Users\child\PROJECTS\ClipMaker\.venv\Scripts\python.exe tools\phone_robot.py tick`
   or, with the row's sitting directly:
   `\.\.venv\Scripts\python.exe -m robotapp.cli --json sitting --file data\robot-sit-youtube-1123.json`
4. `posted` + `url` = done. `failed_before_post` = nothing was pressed, the row is back on the line:
   fix that screen and run again. `unsure_after_post` = **do not press again**; open the channel and
   look for the Short (see below).

## Expect this to break somewhere (its first real press)

- **The details screen** — the flow taps Next until "Add details"/"Upload Short" is up. If it lands on
  the AI creation page again ("Make me a chef…"), Back out and take "Create from gallery".
- **The upload wait** — the new rule needs YouTube's own "uploading/processing" words, or the feed on
  three reads in a row. A details screen still up after 25 s now says "the tap did not start an
  upload" instead of pretending. If that appears: look at the screen, fix the selector, and only then
  consider the press (the journal now blocks a second press on this upload for good — the way back is
  `Journal.release_press(upload_id, reason)` after a human has seen that nothing was published).
- **The link read** — You → Your videos → newest → "…" → Copy link. The "…" may be a different label
  on 21.46; the clipboard only counts with `youtube.com/shorts` or `youtu.be` in it.
- **The title** — this build exposes no title field, so the Short gets YouTube's default title. Known
  and accepted; do not spend the window on it.

## When the link is in hand

- `POST http://localhost:8765/api/phone-posted` with
  `{"upload_id":"038412461d60436faf123cac7bd58b0d","url":"<link>"}`.
- Then check the channel page from the laptop, the same way Instagram and TikTok were checked:
  `https://www.youtube.com/@HoraliCript/videos` in real headless Chrome with a real UA
  (`select-string 'watch\?v='` on the dump). That is the proof that survives a bad log line.
- Leave the phone in user 0, time zone Jakarta, lock released.

## Still open, for the user

- **Duplicates:** Instagram has two Reels of the same clip (`Df-8W5tKYqT` newest, `Df-5g6oK9uc` older)
  and TikTok two videos (`7710764478886907166` today, `7710422808341384478` from the 21st). Deleting
  the copies is the user's call; the robot does not delete posts.
- **Renaming the channel** to "vtubers Clips" — decided against on 2026-11-21 (post as "Horali Cript").
- **Logins** (Speed/Timmy) need the user awake for CAPTCHAs and a decision on Speed's Instagram
  identity (its Chameleon login is the user's own faizchess55@gmail.com). Not part of this run.
