# Copy-paste prompt for a new session (RobotApp, step 10)

Paste everything below into a fresh session. It assumes the same machine and repos.

---

You are continuing the **RobotApp** project: a laptop program (Python + adb + uiautomator2) that drives an old
Android phone to post a clip channel's videos from the phone's own apps. Planning is done and most of it is
built. Work step by step; every step must work on its own before the next.

## Read first, in this order

1. `C:\Users\child\PROJECTS\RobotApp\PLAN.md` — source of truth. Start with the **Progress** section at the top
   (it holds the current state, exactly what is left, and the next commands), then §8.2 (the sitting JSON),
   §13 (all the user's answers).
2. `C:\Users\child\PROJECTS\RobotApp\docs\step1-runbook.md` — what the real phone actually does (measured), and
   the screens that differ from the plan.
3. `C:\Users\child\PROJECTS\ClipMaker\CLAUDE.md` — the main app this plugs into, and the user's working rules.

## The projects

- **RobotApp** (`C:\Users\child\PROJECTS\RobotApp`, GitHub `Horali/RobotApp`): the robot. Python package
  `robotapp/`, CLI `python -m robotapp.cli`, venv `.venv`, tests `pytest` (**107 green**).
- **ClipMaker** (`C:\Users\child\PROJECTS\ClipMaker`, `Horali/ClipMaker`): owns the posting queue
  (`phone_posts.py`); step 4's adapter `tools/phone_robot.py` is built and **off** (`CLIPMAKER_PHONE_ROBOT=0`,
  per-brand opt-in in `data/phone_robot.json`, currently `{}`).
- **Chameleon / CustomBrowser** (`C:\Users\child\PROJECTS\CustomBrowser`, `Horali/chameleon-browser`): stores the
  accounts' secrets. P1 (the platform-password route the robot needs) is **done and live** (the app was
  restarted 2026-11-19).

## The phone

Infinix X6815D, Android 13, the user's **second** phone. SIM removed.
- Home Wi-Fi: `192.168.1.8:5555` (only when laptop and phone are on the home network; lost on reboot — the
  robot finds it again by mDNS, and `sfa`/Wireless-debugging persist on this build).
- USB serial: `0953925324001286` — **works on any network**; `robot` tries it first, so when the user is away
  from home, ask them to plug the cable in.
- run `python -m robotapp.cli connect` then `doctor` before anything else; `doctor` needs the window or build mode.

Spaces (Android users):
- **user 0** = the owner: **G2GChannel Clips** (Indonesian test brand, `trill` + YouTube already signed in by
  hand; **no proxy, no VPN ever**) **and the user's own apps** (their personal Instagram is "Faiz" — leave it
  alone).
- **user 11** = **"US 1"**, the US test space: Virginia proxy (`us-ps-1-virginia`), sing-box imported, always-on
  + lockdown, Chrome/Instagram/YouTube/SFA installed, **Instagram signed in as @vtubersclips90** (leak check:
  exit `208.214.162.185`, `loc=US`).
- **`musically` (TikTok US build) is NOT installed** — US TikTok posts are blocked until it is (APKMirror, then
  `adb install`, with the certificate checked; the user approved the download).

## Firm rules

- **The robot touches the phone only 06:00-10:00 WIB.** Outside it sends no commands. During the build the user
  gave standing permission: `ROBOTAPP_BUILD_MODE=1` bypasses the window (off by default, logs a loud warning).
  Use it only while there is no other script on the phone.
- **Never press Post/Share/Upload twice.** The write-ahead journal (`data/robot.db`) records `post_pressed`
  before the tap; after it an error becomes `unsure_after_post` and the robot looks for the link instead.
- **Secrets never in the repo, logs, screenshots, commits or chat.** The robot fetches a password from Chameleon
  at the moment it types it (`Secret` wrapper; a leak test greps the channels).
- **GTA 6 Clips is a REAL brand — never use it for testing.** The throwaway is **vtubers Clips** (Virginia).
- **Ask the user only for things needing their hands** (phone taps, SMS/email codes) **or money/downloads.**
  Otherwise decide, and write it into `PLAN.md` §13.2 marked "decided by builder".
- Git: small commits, push to `main`; Conventional Commits, lowercase imperative; **no AI attribution**;
  commit only your own files (`git commit -- <paths>`); run `gh auth switch -h github.com -u Horali` first.
  Never commit `data/`, `.env`, screenshots, APKs.

## What is built (all tested, all pushed)

Steps 1-9 of §11: the window guard, the shared phone lock, the journal, `doctor`, the Chameleon client, spaces,
time-zone switching, sing-box import/always-on, the leak check, video push (+ `content://` for share intents),
TikTok/Instagram/YouTube post flows, the TikTok/Instagram/Google login flows, engagement, the trending-sound
step, `views` reading, the brand/space lifecycle (`robot brand`, `setup-next`, `release`), and ClipMaker's
`tools/phone_robot.py` behind its switch. Real screen fixtures (TikTok feed/profile/editor, Instagram
home/profile) are replayed by `tests/test_fixtures.py`.

## What is left (in this order)

1. **First real Instagram post, end to end** for vtubers Clips: needs a `mode='phone'` row for its Instagram
   profile (`499b269e-a0d8-4ce6-8f1a-eb3de59fa8aa`) in ClipMaker's queue (there is none yet — the brand is new).
   Then the robot posts it from user 11, reads the link, and ClipMaker marks it (its own
   `POST http://localhost:8765/api/phone-posted`). Keep an eye on the journal.
2. **`musically`**: download + certificate check + install; then the throwaway's TikTok login
   (`6e1be5de-9641-45ad-be1d-6d0eb779b4a4`) and its first TikTok post.
3. **The 14-day YouTube test** (Timmy, §8.8): needs Timmy's Google sign-in on the phone
   (`robot login youtube ...` — actually the Google flow is `robotapp/login/google.py`, run from the CLI's login
   path for youtube). Google may ask for a code; the robot stops with `NeedsHuman` and the user answers.
4. Then the real brands, **one login per day** (§5.5's order, safest first).

## Commands you will actually use

```powershell
cd C:\Users\child\PROJECTS\RobotApp
.\.venv\Scripts\python.exe -m robotapp.cli connect            # find the phone (USB first, then mDNS)
.\.venv\Scripts\python.exe -m robotapp.cli doctor             # battery, heat, users, apps, window
.\.venv\Scripts\python.exe -m robotapp.cli screen --user 11   # prints package + user in front, then the labels
.\.venv\Scripts\python.exe -m robotapp.cli zone newyork|jakarta
.\.venv\Scripts\python.exe -m robotapp.cli leak --user 11     # exit IP must be 208.214.162.185, loc US
.\.venv\Scripts\python.exe -m robotapp.cli login instagram --user 11 --profile-id <id>   # email comes from Chameleon
.\.venv\Scripts\python.exe -m robotapp.cli sitting --file data\g2g-sitting.json [--dry-run]
.\.venv\Scripts\python.exe -m robotapp.cli post tiktok|instagram|youtube --user N --video <path> ...
.\.venv\Scripts\python.exe -m robotapp.cli views --upload-id <id> --platform instagram --user 11
.\.venv\Scripts\python.exe -m pytest tests -q                  # 107 tests, no phone needed
```

## Gotchas learned the hard way (do not re-learn them)

- **Typing:** in a fresh space uiautomator2's IME is *not* enabled, so `send_keys` types nothing. Everything goes
  through the field's own `setText`; Instagram's form has **two** EditTexts (username 0, password 1) and an
  un-indexed selector is refused. A login must never submit an empty form (it checks and refuses).
- **Whose app is in front:** `am get-current-user` answers what the phone thinks; read `mCurrentFocus` instead
  (`robot screen` does). Never assume which Android user a tap landed in — that caused a false alarm on
  2026-11-19.
- **The phone's keyboard (Facemoji)** puts its own terms dialog over the app until answered ("Agree And
  Continue"); Instagram also shows its own terms once per install.
- **Instagram's device confirmation** ("approve on another device" / an SMS code to +…71) is the user's: the
  robot stops with `NeedsHuman`. Nothing is submitted twice.
- **TikTok's camera upload tile is invisible to the accessibility tree** — the share intent is the route
  (`SystemShareActivity`, then tap "Video").
- **Python cannot write outside the repo** under this harness's sandbox: to mark a ClipMaker row, use its HTTP
  API, and claim `sent_at` first via `node data\claim_phone_post.js <upload_id>` (step 4 removes the need).
- **adb connect to a stale Wi-Fi address** now gives up in 5 s; the USB serial is tried first.

## How to work

Keep responses short (the previous session ran out of context): run tests with `-q` and show only the last
lines, don't dump whole UI trees (use `robot screen --limit 12`), and commit + push as soon as a step is green.
After each step update the **Progress** section at the top of `PLAN.md` (done / next / what the user must do).
Explain things in plain English; show results (a screenshot, the post link), not just descriptions.
