# RobotApp: the phone robot (build plan)

Status: **building.** Plan finished 2026-11-18; P1 (the Chameleon route) is built, step 1 is in progress. See
**Progress** below.

## Progress

Last updated: 2026-11-22, 17:20 WIB. **The login blocker is the exit, not the accounts — measured.**
One attempt was spent on Speed's TikTok (`login-speed-tt6`, 17:05): the flow reached TikTok's login
screen, typed `horalixscripts3@gmail.com`, tapped Continue — and the button **spun forever**. In the
same space, Chrome to `www.tiktok.com` and to `1.1.1.1` gives **ERR_CONNECTION_REFUSED**; the tunnel is
up (always-on + lockdown), so the requests are being refused, not blocked by the app. The control: the
throwaway's space on the **same phone** (us-ps-1-**virginia**, 208.214.162.185) posted to TikTok at
06:04 today and its leak check was green at 05:22. **Both brand spaces point at us-ps-2-newyork**
(65.195.107.138) — the exit the 03:20 entry already recorded as unable to reach the platforms from the
phone. So the earlier "these are rate/risk refusals" was wrong, or at least premature: on this exit
nothing gets past the TCP handshake, which no amount of cooling fixes. The 02:16 swap of Speed's space
onto virginia **failed** (`data/vpn-swap-u10.jsonl`: "the phone did not fetch the profile") — that is a
robot-side bug, and the reason the space is still on newyork. Evidence and the vendor question are in
`docs/proxy-vendor-ticket-2026-11-22.md`; the lead decision (2026-11-22) is to file it with the vendor
rather than share the throwaway's exit. Also fixed today: a login that dies now closes its job
(`c401ec3`) instead of staying "running" — all 36 stale rows are closed.

Previous entry — 2026-11-22, 15:35 WIB. **The throwaway's Instagram and TikTok posts are live; YouTube is
the one left.** Proven from the laptop (real headless Chrome, no phone): `@vtubersclips90` has two
Reels (`Df-8W5tKYqT` newest, `Df-5g6oK9uc` duplicate), `@vtubersclips70` has `videoCount: 2` —
`7710764478886907166` = today 06:04:16 WIB, `7710422808341384478` = 2026-11-21 07:58:25 — and
`@HoraliCript` still has no videos. **Both "unsure" TikTok verdicts were wrong**: yesterday's 07:57
press did publish, 27 s later, and today's 06:03:58 press published in 18 s; the profile reads that
followed were misread (the "Drafts: 1" page was an older draft). So the robot's presses work; the
robot's *confirmation* did not. ClipMaker's Instagram and TikTok rows are now `posted` with those
links, which leaves **only the YouTube row queued** — the 06:00 tick can no longer repost either.

Three real bugs fixed with tests (**146 pass**): the press guard only covered one job, so a new
sitting could press the same upload again (TikTok's Post three times, Instagram's Share four times) —
`claim_press()` is now per upload across jobs, `release_press()` the deliberate way back; TikTok's
link read tapped the fixed (16 %, 40 %) point that lands on the Drafts row, so the tile is now found
on the screen and every tap must prove it opened a video page; TikTok's upload confirmation accepted
a stale hierarchy after 1.3 s, so it now needs the composer gone on three consecutive reads. Commits
`8a0a60f`, `5faab39`, `28d863c`; the full story is in `docs/report-2026-11-22.md`. **Tomorrow:
YouTube's first real press** (its poster has never posted — expect 1–2 selector fixes).

Previous entry — 2026-11-22, 03:20 WIB. **Correction to the 03:00 entry: UDP never explained the
logins — it has been dead in every config since Nov 18, including the day the logins worked.** The
Chameleon record has said `protocol: http` since at least its Nov 9 health check, so the Nov 18-19
outbound was HTTP too, with the same dead UDP — and the throwaway's TikTok login succeeded through it.
Measured tonight (user 10, one submit each): through the HTTP outbound the app answers "No internet
connection"; through a SOCKS5 outbound the answer becomes **"Please try again or log in with a
different method"** — TikTok's server responding, i.e. the login request completes and is *refused*.
What actually differs between Nov 19 (worked) and now (refused) is therefore NOT the tunnel: it is
the risk engine on the other side — a fresh device making its 5th-6th login attempt in three hours
through an ISP-range proxy exit, after the night's debugging retries. The honest conclusion: the
login refusals are rate/risk refusals, and further attempts tonight only deepen them. **Stop; one
attempt per account in the morning window.** Still true from tonight: newyork's exit cannot reach
the platforms from the phone's tunnel (even TCP; laptop through the same proxy is fine) so both brand
spaces stay on virginia; the clean-UDP rule (`52fd57f`) stays (it removed the tunnel's black-hole
errors); SOCKS5 UDP ASSOCIATE is refused by both gateways (measured, `0x07`) — a fact for the proxy
vendor, not the login blocker. Spaces: user 10 Speed (socks5 profile, virginia), user 12 Timmy
(virginia), user 11 throwaway (untouched, up + locked). The 06:00 posts are unaffected (existing
sessions, TCP works).

**23:00 update — the two real-brand spaces are BUILT and leak-green; their logins are refused, almost
certainly by the proxy.** `robot provision` made **user 10 "Speed Clips"** and **user 12 "Timmy Clips"**
(both `us-ps-2-newyork`, New York time, VPN up + locked, leak checks green after two real bugs were fixed:
Chrome's first-run screen blocks the first leak check, and SFA's imported profile does not start itself —
`vpn` and a hand-tap of Start are both needed; the spaces also had gesture navigation while the owner has
3-button, now all spaces are 3-button and a dry run confirmed the flows still pass). The logins all refused:
Speed's Instagram (a CAPTCHA the user could not solve in time, then three "unexpected error" refusals —
and note its Chameleon login identity is the user's own faizchess55@gmail.com), Speed's TikTok (the app
does not recognise horalixscripts3@gmail.com as a login — the account's real username is recorded nowhere),
and Speed's Google ("Something went wrong", twice, with DNS verified clean). The isolation evidence:
the SAME Google sign-in reached "Checking info" from the throwaway's Virginia space on the same phone
today. **Conclusion: us-ps-2-newyork is likely flagged for account sign-ins (Instagram and Google both
refuse it; posting and browsing work fine through it). Next step: a third proxy, or the user's own hand
on the phone, which is also the plan's answer to sign-in challenges.** TikTok needs the account's real
login name first. Fixes pushed tonight: musically's login landing is taken as a start screen (`0a616ec`),
and the flows' step timings from the evening are in the events.

**15:45 update — all three flows were walked to the pre-press point on the phone, by the robot.** After
fixing every known bug (140 tests green, commits `8d35379`…`acdce62`), three dry runs ran on the real phone
(build mode, nothing pressed):

| flow | dry run | reached |
|---|---|---|
| Instagram | `dry_run` | the caption/share screen of a Reel (create → picker with the newest clip preselected → editor → caption) |
| TikTok | `dry_run` | the post screen, caption written, handle **@vtubersclips70**, "Everyone can view" |
| YouTube | `dry_run` | the details screen with **Upload Short** on it, channel **Horali Cript**, 48 s clip |

**What is live:** Instagram has **2 Reels** on @vtubersclips90 — the first post worked, but the flow's
confirmation check missed the success and it posted a duplicate (one must be deleted). TikTok's Post was
pressed at 07:57 and never confirmed; YouTube has 0 videos.

**Bugs found and fixed today (all measured, each with a test where a test can hold it):** Instagram 456's
create goes straight to the post picker (no REEL tab) and its one-time sheets (OK / Continue) cover the
share screen; the share is the bottom Next then the "About Reels" Share; TikTok's gallery tile has no label,
the editor's Next needs a settle-and-retry, and Post sits under the keyboard; YouTube has no avatar in the
top bar (the channel name is a content-desc on the You tab), Create can open a Drafts/Create-video chooser
whose "Create from gallery" leads to the **AI creation page**, the first editor visit asks for consent
("I agree"), and its launcher component contains a `$` that the phone's shell ate (`am start` never ran);
Chrome can need the clip URL opened twice.

**Known warts:** YouTube's title row ("Add details") does not open its editor for uiautomator2, so the
Short goes out with YouTube's default title; TikTok's upload confirmation has never been seen; Instagram's
share confirmation is unreliable, so the verdict must come from the profile's post count.

**Done**
- **P1 — the Chameleon route. Done 2026-11-18.** `GET /v1/profiles/:id/platform-password?platform=tiktok|instagram`
  in Chameleon's daemon (commit `c1f6672`, repo `chameleon-browser`). It reads the encrypted
  `platform-passwords.json` that the main process writes and asks the main process to decrypt **one value per
  request** over the secrets channel it already has; nothing is cached, nothing is logged. Answers:
  `200 {profile_id, platform, password}`, `404` nothing saved for that profile+platform, `409` saved but the blob
  cannot be decrypted, `400` for `youtube` (that account signs in with its Gmail password). Same bearer token,
  host allow-list and no-browser-Origin rules as every other route.
  Tests: a unit test with a fake cipher, and 8 new checks in Chameleon's `npm run test:api` (real
  safeStorage, encrypted at rest, the 401/400/404 paths). That suite: 37 pass, 0 fail, exit 0.
  **Catch:** the Chameleon app that is running now still has the old code in memory. The route works after its
  next restart (close it and open it again). Nothing else needs it before the first real login.
- **Step 1's code. Done 2026-11-18** (commits `ec37460` … `bd9e5b5`): the `robotapp` package and the `robot`
  CLI — the 06:00-10:00 guard every phone call goes through, the shared phone lock, the write-ahead journal (Post
  is pressed once, enforced by the database), `doctor`, the Chameleon client (a password is fetched only when it
  is typed and cannot be printed), spaces, time-zone switching, sing-box config/import/always-on, the leak check,
  pushing a clip into a space's gallery, the TikTok login and post flows, engagement, and `robot sitting` (the
  §8.2 JSON contract, so ClipMaker can be written against it already). **56 tests pass** against
  `FakePhone`/`FakeScreen` — including a scripted walk of the whole post and login flows.
- **STEP 1 RAN ON THE PHONE AND WORKED. 2026-11-18, 20:37-21:56 WIB** (the user allowed the phone outside the
  window while building: `ROBOTAPP_BUILD_MODE=1`, off by default, logged loudly). What was proven, in order:
  - the auto-clicker uninstalled; **users 10 ("Brand") and 999 ("Ruang Ganda") deleted** — `pm remove-user 999`
    was *not* refused;
  - **one US space = user 11** ("US 1"), with Instagram, YouTube, Chrome and sing-box installed, media
    permissions granted, location/contacts never;
  - **sing-box (SFA 1.14.4) imported the profile** written from the Virginia proxy and **the tunnel came up**;
    always-on + lockdown set;
  - **the leak check passed**: exit IP `208.214.162.185`, `loc=US`, VPN locked, New York time, no SIM, location
    off (~90 s including Chrome's first run);
  - **uiautomator2 reads and taps a secondary user's screen** — yes, the "unverified" item of §6.2; it needed
    `am switch-user` first (a space's UI only exists while that user is in front);
  - **G2G's queued TikTok clip was posted by the robot** from `trill` in the owner user: handle read
    (`@gtwogchannelclips`), caption written and read back, Post pressed **once** (journal), upload confirmed,
    **link `https://vt.tiktok.com/ZSp7oooX8/`**, 3.3 min of watch-only engagement;
  - **the post is in ClipMaker as posted**: `/api/phone-posted` answered `{"ok": true, "url": …}` and scheduled
    the 24 h check. (The row needed `sent_at` first, set with `data/claim_phone_post.js`; step 4 does that in
    ClipMaker's own code.)
  - Measured: connect + doctor ~1 min; clean + space + apps + SFA + VPN ~4 min; leak check ~1.5 min; one post
    from "start" to link ~8 min (including the upload wait); engagement 3.3 min. Well inside 06:00-10:00.

**Fixed on the way (all committed):** SFA 1.14 rejects the old DNS/`block` formats (new config); SFA needs its
update offer dismissed, its "Create" tapped and its profile started; the laptop's hotspot address was served
instead of its Wi-Fi address; `monkey --user` does not exist (resolve the activity instead); the camera's upload
tile is drawn but absent from the accessibility tree, so the **share intent** is the route (tap "Video" → the same
editor); a substring tap on "Profile" opened the *video author's* profile (now an exact bottom-bar tap); the
caption goes in one paste and is read back; TikTok's location prompt is cleared via "Open settings" + Back.

**Next**
- **Step 2 — DONE 2026-11-18, 22:32 WIB** ("phone rebooted → robot reconnects alone"):
  - **The laptop half is the real fix:** `robot connect` (and `resolve_serial`, which every command now runs)
    finds the phone by **mDNS** (`_adb-tls-connect._tcp`, a new random port after every reboot), connects with
    the already-authorized adb key, and falls back to `adb tcpip 5555` over the cable — pinned to the robot
    phone's USB serial (`PHONE_USB_SERIAL`), so another phone on the cable is never touched.
  - **Proven twice by reboots** (ports 46841 → 45307 → 36459): reboot → ~2 min → `robot connect` connects →
    `doctor` green.
  - **Honest finding: this XOS/Android 13 build persists `adb_wifi_enabled=1` across reboots by itself.**
    A control test with Keeper disabled came back with Wireless debugging on. The plan's fear (§9) does not
    hold on this firmware; **Keeper (built, installed, granted) is insurance, not the mechanism** — an 8.6 KB
    receiver that re-sets the flag at boot in case an OEM update reverts to AOSP behaviour.
  - Built `keeper.apk` by hand (javac → d8 → aapt2 → apksigner, no Gradle; `keeper/build.py`), installed in
    the owner user, `WRITE_SECURE_SETTINGS` granted, battery-allowlisted. 6 reconnect tests (fake adb binary),
    63 tests green.
- **Step 3 — DONE 2026-11-18, 22:45 WIB** (safety rails + fake phone; "tests green"):
  - already in from step 1: the write-ahead journal (never press Post twice, enforced by the database), the
    outcome types (`posted` / `failed_before_post` / `unsure_after_post`), screen signatures, FakePhone +
    FakeScreen tests, and the scripted whole-flow tests;
  - **the password-leak test:** a real login flow runs with a known fake password, then every output channel is
    grepped — the journal database, the WAL, the log file, the events, the exception text. The password appears
    in exactly one place: the typed characters (it was used, once);
  - **signature fixtures:** three real screen dumps saved from the phone (feed, profile, editor; `robot screen
    --save-as`, saved by `data/capture_fixtures.py`) and replayed by tests. When TikTok updates and a screen
    changes, the fixture test says so on the laptop before the phone ever runs the flow again;
  - **70 tests green.**
- **Step 4 — DONE 2026-11-19, 00:25 WIB** (ClipMaker wiring; "an opted-in brand's sitting posts by robot; any
  failure lands in Telegram as today"):
  - **`tools/phone_robot.py`**: one brand's due rows become one sitting (Instagram → TikTok → YouTube), the
    real RobotApp runs as a subprocess (`robot sitting`), and each `done` event marks its row through
    `phone_posts.mark_posted` — the same checks a pasted link goes through. A failure before Post **unclaims
    the row**, so Telegram sends it as today; anything the robot cannot answer stops it safely before it
    presses anything (stdin closes: no answer can follow).
  - **The switch is double**: `CLIPMAKER_PHONE_ROBOT=1` in `.env` (off by default) **plus** per-brand opt-in in
    `data/phone_robot.json` (`{"brands": {"<id>": {"robot": true, "youtube_by_phone": false}}}`). A brand not
    opted in, the robot missing, or its `robot doctor` unhappy → Telegram exactly as today. `approve.phone_tick`
    tries the robot first; a robot error can never stop the Telegram path.
  - **The §8.4 ClipMaker changes are all in**: the 30-min gap is **per brand** (a brand's own apps post back to
    back in one sitting); a home brand's rows ride the robot's 06:00-10:00 WIB window instead of the New York
    evening; a robot views reading counts from **23 h 30 min** (Telegram keeps the full 24 h);
    `check_link` accepts `youtube.com/shorts/<id>` / `youtu.be/<id>`; `post_mode` makes YouTube `phone` **only**
    for a brand with `youtube_by_phone` on; the hand-post steps text covers YouTube; the Phone page shows
    "🤖 the robot is posting this now (step N of 12)" from `status.json`.
  - **Tests: 31 pass** across `test_phone_posts`, `test_phone_robot`, `test_phone_robot_line`, `test_phone_mode`,
    `test_campaign_posts` — including an **integration test that runs the real RobotApp subprocess in `--fake`
    mode** through the whole pipe (its window guard refused at 00:12 WIB, exit 3, and the row came back
    unclaimed for Telegram — exactly the safety property). One existing test was updated to the new per-brand
    rule, which is what §8.4 ordered.
- **Step 5 (Instagram) — code DONE 2026-11-19, 01:10 WIB** ("one Reel by the robot" still needs a real account):
  - the Reel flow (`post/instagram.py`) and the login (`login/instagram.py`), both walked on a scripted screen
    (6 tests). The scripted walk caught three real bugs before any phone saw them: the home signature matched
    "Search" (on every screen's nav bar), a profile's own "Reels" tab matched "Reel", and a double Next tap.
  - `sitting` posts Instagram now (TikTok and Instagram both built); `robot post/login instagram` work.
  - **Honest note:** the signatures follow the plan's description of Instagram's screens. No Instagram account
    exists on the robot phone, so they are unchecked against the real app — the first real Instagram account
    (the throwaway) provides the fixtures, and `tests/test_fixtures.py` guards them after that.
- **Step 6 (YouTube) — code DONE 2026-11-19, 02:20 WIB** ("one Short by the robot" needs a real sitting):
  - the Shorts flow (`post/youtube.py`): open, check the avatar is the brand's channel, **+** → Create a
    Short → the newest video (length check, **the trimmer keeps the full length**) → the title (ClipMaker's,
    ≤ 100 chars) → Public + not made for kids → **Upload Short** (journal first, never twice) → the link →
    the pinned comment when the campaign asks → engagement;
  - the Google sign-in (`login/google.py`): Settings → Add account → Google, the Gmail password fetched only
    while typed, Backup off on the services screen, the account read back from YouTube's avatar. **A code to
    the brand's own Gmail is automatic; any other destination stops with NeedsHuman** (the plan's honest rule
    about Google's unknown recovery), and every "couldn't sign you in" stops for 24 h, never a loop;
  - 6 scripted tests; the scripted walk caught a double-Next and an avatar check that read the wrong sheet.
  - **Honest note:** like Instagram, the signatures are the plan's description until the first real YouTube
    sitting (Timmy's 14-day test, §8.8) provides the fixtures.
  - What is left of step 6: the 14-day test itself (needs Timmy's Google sign-in on the phone + `musically`
    is not on the phone yet, though YouTube does not need it).
- **Step 7 (G2G's YouTube) — code DONE 2026-11-19, 02:50 WIB**: a G2G sitting is wrapped
  (`g2g.py`): its own leak check first (a VPN up in the owner user means nothing posts), **Do Not Disturb on
  for the sitting and back to the user's setting after**, the owner apps stopped on the way out. 2 tests.
- **Step 8 (sound + views) — code DONE 2026-11-19, 03:00 WIB**:
  - `sound.py`: the trending-sound step for TikTok and Instagram, and it never lies — `False` means nothing was
    added, so the post goes out without a sound unless the caller said it is required (then it stops before the
    press). The added sound is dropped under the clip's own audio.
  - `views.py` + `robot views`: the newest tile's play count from the account's own profile (1,234 / 1.2K /
    3.4M, and the play triangle the tiles show). An unreadable number answers `None`, so ClipMaker asks the
    user as today. 6 tests.
- **Step 9 (lifecycle) — code DONE 2026-11-19, 03:08 WIB**: `data/robot.db` holds the registry (brands ↔
  spaces, states of §7.1). A home brand is ready at once in the owner user and never wiped; a US brand waits,
  takes a free space, and `robot release` puts its space to wiping, frees the slot after `pm remove-user` — so
  **a graduated brand frees its space alone** (step 9's acceptance). `robot brand add/list`, `robot
  setup-next`, `robot release`. 5 tests. **102 tests green.**
- **STEP 10 STARTED — the first real login ran. 2026-11-19, 11:26-11:40 WIB.** The throwaway is
  **vtubers Clips** (user, 2026-11-19; `us-ps-1-virginia`), and its **Instagram account is now signed in on the
  robot phone**, in the Virginia space (user 11):
  - handle read from the app: **@vtubersclips90** ("vtubers Clips", 0 posts, 0 followers);
  - the leak check before it: exit `208.214.162.185`, `loc=US`, VPN locked — the login went through the Virginia
    proxy, as §5.5 requires ("only the device changes, never the IP");
  - Instagram asked for a confirmation (approve on another device / an SMS code to +…71) — the plan's §5.4
    case. The robot stopped and reported it; **the user took the code** and the login completed;
  - the real screens are now fixtures: `instagram-home`, `instagram-profile`, and the signature test replays
    them, so the Instagram signatures are no longer guesses.
  - **Four bugs the fake phone could not have found, all fixed** (commit `f0d0999`): the IME is not enabled in
    a fresh space (so `send_keys` typed nothing and the first attempt submitted an empty form — now everything
    goes through the field's own setText, the password one character at a time); Instagram's form has two
    EditTexts, so an un-indexed selector is refused (username 0, password 1); tapping the field's hint does not
    focus it; and the phone's keyboard (Facemoji) puts its own terms dialog over the app until answered.
  - also fixed: `adb connect` to a stale Wi-Fi address now gives up in 5 s instead of hanging 20, the robot
    phone's USB serial is used first when the laptop is on another network, and a login never submits an empty
    form.
- **Open verification — DONE 2026-11-19, 12:34 WIB.** Read per user: **user 0 = "Faiz"** (the user's own
  account, 101 followers, untouched), **user 11 = "vtubers Clips"** (the throwaway, 0 posts). The login landed
  in the US space as intended; the earlier alarm ("on my main account") was a misread of a foreground window,
  now impossible to repeat: `robot screen` prints the package and user from `mCurrentFocus`.
- **STEP 10's TikTok HALF IS DONE. 2026-11-19, 12:43-16:22 WIB** (the user allowed the phone outside the
  window for this build, `ROBOTAPP_BUILD_MODE=1` per command; **@vtubersclips70 is signed in**):
  - **`musically` 47.9.1 (TikTok US) is on the phone**, in user 11 only. APKMirror's APK download
    (485,014,178 bytes, size exact), certificate checked per §4.7: apksigner on 47.9.1 **and on 47.8.3
    from the same listing** - the same signer both times (`CN=musical.ly, O=musical.ly Inc., Shanghai`,
    SHA-256 `9041803e…cf2ab5ba`). Installed through the built provision path (it re-verifies the
    digest itself), then `pm uninstall --user 0` so the owner user keeps only G2G's `trill`. The
    throwaway's **TikTok login is DONE: @vtubersclips70** in the Virginia space - the emailed code was
    taken by the user on the phone (the plan's one-hand rule). The robot's code path is built and
    unit-tested for the next login; what ran robotically was everything up to the code screen.
  - **musically's login journey, measured** (trill never showed any of it - G2G was logged in by hand):
    a birthdate wall whose three SeekBar **wheels** are the real input (the "Birthday" field only
    displays; typing leaves Continue disabled; one drag initialises the wheels to today, a 200px
    down-drag on the year wheel = one year older; the flow dials to an adult year, reads the field
    back, presses Continue once and waits for the wall to clear); then a **Terms of Service dialog**
    ("Agree and continue"); then the notifications permission (**"DON'T ALLOW"** - all caps and a curly
    apostrophe, so `says()` normalises U+2019); then the feed. The email login goes **straight to an
    emailed code ("Verify email"), no password form** - the code field carries no label (only
    "Resend code" does), so the code is typed into the screen's editable, never tapped at by name.
  - **Eight real bugs fixed on the way** (commits `fade624`…`34ea49d`, 107 → **123 tests green**):
    1. **the flows opened their app in the owner user, not the space** - `TikTokLogin`, `InstagramLogin`
       and all three posters called `start_app` with its default `user=0`. This one bug explains the
       morning Instagram login's ten crashed runs, the TikTok login opening musically in user 0, and
       the stray TikTok in the owner's launcher. All flows now take and pass their space's user.
    2. **`dumpsys window` prints one `mCurrentFocus` line per root** - with the user's own Instagram
       open in user 0, its stale line came first and `robot screen` blamed the wrong account. The one
       unique, proven source is `dumpsys activity activities`' **`topResumedActivity`**; `fore_app`
       and every `_in_front` guard now read it.
    3. a failed leak check crashed `provision` (`LeakResult` has no `outcome` - it hid on every green
       run).
    4. `views` read TikTok view counts from `trill` regardless of the space.
    5. a TikTok login without `--package` had no default (now trill for user 0, musically otherwise).
    6. the login's "Profile" tap was a substring match and opened a video author's page on the feed
       (the trap the post flow had already fixed) - now an exact bottom-bar tap, like `views`.
    7. `robot screen` died on emoji in a cp1252 console (it prints backslash-escaped ASCII now).
    8. `sitting` still refused Instagram/YouTube posts with "not built yet" - a stale guard left over
       from step 1, removed.
  - `robot login` accepts **`--code-file`**: a manual run in the background polls a file for the
    6-digit code (5 min), so the user can type the code into a file while the run sits on the code
    screen.
- **The first posts are QUEUED. 2026-11-19, 16:58 WIB** (the user chose "force it now" over waiting out
  the Nov 22 warmup lock): the throwaway's Instagram and TikTok profiles are graduated by hand (no
  warmup days - a throwaway; backup `data/backups/warmup-before-throwaway-force-20261119-1657.db`),
  a "robot test" campaign carries them (source `other`, platforms instagram+tiktok, no Content
  Rewards link so nothing auto-submits), and **two `mode='phone'` rows went through ClipMaker's own
  `queue_post` gates**: instagram `b988d8b5…`, tiktok `cd9c25ea…` - the clip is a house (Loud Lobby)
  one, "Kai crashes a real-life Mario Kart in Tokyo" (`renderer\out\twitch_2907224886_204_v2.mp4`,
  56 s, no paid-campaign ties). **The robot path is switched on for the throwaway only**
  (`CLIPMAKER_PHONE_ROBOT=1` in ClipMaker's `.env` + `data/phone_robot.json`; every other brand keeps
  Telegram). Read-only simulation at Fri 06:30 WIB: the gate says go and one sitting posts Instagram
  then TikTok. **The user's one action: restart ClipMaker's app before tomorrow's window** (the
  running app still has the old flag in memory), and leave the phone on Wi-Fi overnight. If the app
  is not restarted, the tick sends the posts to Telegram as hand posts instead - the rows only leave
  the queue from 06:00 WIB, so any restart tonight is in time.
- **The YouTube leg — the night it turned out the space had no DNS (2026-11-20, 02:40-04:25 WIB).**
  The user asked for the throwaway's YouTube post too. The Google sign-in failed with "Something went
  wrong. Please go back and try again" — from Settings *and* from the YouTube app's own Accounts → Add
  account, so never the route. Three real faults, all found and fixed (commits `332805a`, `4e08840`,
  `64c172c`, `592d76b`, `6b0ae7a`, `80a5458`, `00d132a`, `4515b0d`):
  1. **The phone's own Private DNS** was strict (`private_dns_mode=hostname`, `dns.quad9.net`) — DoT on
     port 853, unreachable through the locked Virginia proxy, so **no hostname resolved anywhere**
     while raw-IP pages still loaded. Turned off (`settings put global private_dns_mode off`). The owner
     user now uses the router's plain DNS; the user should know.
  2. **The robot's sing-box profile sent DNS as `tcp :53` through the proxy**, and that proxy answers
     **403 Forbidden** to `CONNECT 1.1.1.1:53` (200 on `:443`) — measured from the laptop. `build_config`
     now uses **DNS over HTTPS on 443 through the proxy**; verified on the phone (example.com and
     google.com load). Test.
  3. **The leak check could lie**: it read whatever Chrome showed, and a *cached* trace page passed
     while the network was dead. It now asks for a unique URL (cache-busting `?t=`) and requires the
     page's own `ts=` to be recent. 3 tests.
  Also fixed on the way: SFA's remote-import confirmation was never answered (the profile list behind
  it counted as success — now the dialog is answered first, with a test); `vpn_state` died on a dropped
  adb ("error: closed" — now reads as "not up", with a test); `robot login youtube` had no CLI branch
  (wired to `GoogleLogin`); Google's Next was tapped blind (now it waits, verifies the page moved,
  closes the keyboard only when it is really open, and retries); and the Gmail password went to field
  **index 1** (Instagram's habit) while Google's page has **one** field — it typed nothing and Google
  answered "Enter a password" (now index 0, plus a check that the field is not empty).
  **Result: the throwaway's Google account IS signed in on the phone** (`logged_in: true`, handle
  `horalixscripts7`). Its YouTube account had **no channel**, so YouTube's "Create a channel" made one
  and it took the account's default name **"Horali Cript"** / handle `@HoraliCript`. Renaming needs
  YouTube Studio's settings, which will not load in the phone's mobile Chrome ("Oops, something went
  wrong"); **Chrome's "Desktop site" mode does render Studio** (menu → Desktop site), and the channel
  id is **`UCl1ZpgCNfkIGhtf-Af3f5nQ`**, so
  `https://studio.youtube.com/channel/UCl1ZpgCNfkIGhtf-Af3f5nQ/editing/details` is the direct page —
  but its Profile form does not expose its fields to uiautomator2, so the rename is a **2-minute job
  for the user on the laptop** (Studio → Customization → Profile, or Settings → Channel → Basic info).
  **The YouTube row was pulled from tomorrow's queue**: the throwaway must not publish under the
  user's own name. Once renamed, the row goes straight back in (the profile is graduated, the
  campaign already lists youtube, `youtube_by_phone` is on).
- **Tomorrow's sitting is the proven pair only:** Instagram `b988d8b5…` then TikTok `92a0c985…`, both
  06:00 WIB, both the Mario Kart clip. Phone left as other scripts expect at 04:25: owner user, Jakarta
  time, no space open, VPN up + locked (leak check green: `208.214.162.185`, US, no SIM, location off).
  Battery 76 % but **44.4 °C** (doctor's limit 42 °C) — it cools with the screen off; check before the
  window.
- **The robot switch itself was broken (found at 04:30, ClipMaker commit `899c6da`).** Nothing loads
  `.env` into the app's process environment, and `phone_robot.on()` read only `os.environ` — so with
  `CLIPMAKER_PHONE_ROBOT=1` in the file the running app still answered "off" and would have sent the
  posts to Telegram. It now reads the environment first and `.env` fresh after (2 tests). **The app
  must still be restarted once** (its running process has the old module in memory); after that the
  flag works with no shell environment.
- **THE FIRST MORNING DIDN'T POST — but it found the real blockers. 2026-11-20, 07:00-09:40 WIB.**
  Nothing had run by 07:03: the app's tick was alive but its **in-memory code predated the switch fix**,
  so the robot branch still read as off. Running that same tick from the command line exposed, one at a
  time, everything that had never been exercised (all fixed, each with a test):
  1. **The sitting did not name its space** (`_sitting_json` never sent `"user"`), so RobotApp posted
     in whichever user was in front — **the owner user, the user's own Instagram**. It was stopped after
     "open app" (the journal has zero events: nothing was pressed). Now ClipMaker sends the brand's
     `user` from `data/phone_robot.json`, and **RobotApp refuses a sitting with no user** (fail closed).
  2. **A clip cannot be pushed into a secondary user's storage**: SELinux refuses
     `mkdir /storage/emulated/11/...` from the adb shell (step 1 only ever pushed into user 0). The
     space's own Chrome now downloads it over **`adb reverse`** (a LAN address travels through the VPN
     and the proxy cannot reach 192.168.x.x), served under the robot's name (Chrome otherwise keeps the
     laptop's name and the lookup misses), and the space's media store indexes it —
     `content://media/external/video/media/42` was reached that way.
  3. **Instagram 456 has no "+" in the bottom bar**: the create action is the top-left button
     (desc "Create"). Worse, **the profile page matched the old HOME signature** (it shows "0
     following"), so the flow never left the profile and never found the button — "Following" is gone
     from the signature now.
  4. **musically throws Play's "TikTok needs to download additional files" sheet** over the app and
     re-throws it mid-flow (the app is APK-installed, so Play keeps offering the extra modules). The
     flows dismiss it wherever it appears.
  End state: the **clip lands in the space**, the apps open, **the right accounts are read**
  (@vtubersclips70 on TikTok, "vtubers Clips" on Instagram), Instagram's create button is found, and
  every unknown screen stops the flow **before any press**. **Still blocking the post:** TikTok's
  camera → gallery picker step (the share intent did not land in the editor on musically and the camera
  entry's labels are still unknown — the last runs stopped there), and Instagram's own run never
  happened because its evening window closed at 21:00 New York (09:00 WIB) during those fixes.
- **Both rows stay queued for tomorrow** (Instagram `b988d8b5…`, TikTok `92a0c985…`), unclaimed.
  Instagram has the best chance: its window opens at 06:00 WIB and both its blockers are fixed. TikTok
  needs the camera-step work, done live with the space in front (about 10 minutes). **Restart the app**
  so it runs today's code.
- **The YouTube row is queued too (2026-11-21, 03:55 WIB): `03841246…`**, on the Herobrine clip (the
  other two share the Mario Kart clip). The user was explicit that **YouTube is in scope now, not a later
  test**. Its channel is still "Horali Cript" / `@HoraliCript` (id `UCl1ZpgCNfkIGhtf-Af3f5nQ`) — the rename
  is a 2-minute laptop job in Studio → Customization → Profile; the poster itself has never run for real,
  so expect 1-2 selector fixes on its first run.
- **The TikTok blocker, precisely:** after the bottom bar's Create, Play takes the screen with "TikTok
  needs to download additional files" (the installed `musically` 47.9.1 is the **base APK**; Play wants the
  dynamic modules). Dismissing it once restores the feed, but it returns when the camera/editor assets are
  asked for. The real fix is the **bundle** variant of the same release from the same listing (same signer
  `9041803e…cf2ab5ba`), installed in user 11 — which needs a fresh TikTok login (a code to the Gmail; the
  robot has `--code-file` for that).
- **Handoff for the next session: [`docs/handoff-2026-11-21.md`](docs/handoff-2026-11-21.md)**, with the
  copy-paste prompt [`docs/next-session-prompt.md`](docs/next-session-prompt.md).
- **What is left:** the first fully automatic sitting, the TikTok camera step, the YouTube channel
  rename + its row, the 24 h views reading, the 14-day YouTube test (Timmy's Google sign-in), then the
  real brands one login per day (§5.5's order). The throwaway's handles: Instagram
  **@vtubersclips90**, TikTok **@vtubersclips70**, YouTube channel **"Horali Cript"** (to rename).

  - **step 10 (move the real accounts in)** — the robot's side is built; it is one login per day, safest first
    (§5.5), and **the first real login is the next thing to run**: the throwaway is now **"vtuber Clips"**
    (user said so 2026-11-19), on `us-ps-1-virginia`, its accounts already signed in in Chameleon. Its
    Instagram login on the phone has **not** been attempted yet, on purpose: §5.5 puts new-device logins inside
    the 06:00-10:00 window, and the build session was at 02:00-03:00. Nothing was touched.
  - **TikTok's US build (`musically`)**: **DONE 2026-11-19** - 47.9.1 installed in user 11, certificate
    checked against the 47.8.3 of the same listing; the throwaway's TikTok is signed in (@vtubersclips70).
  - **The 14-day YouTube test needs Timmy's Google sign-in** (a separate, checked-by-hand job, §5.6).
  - **The first posts need queueable rows in ClipMaker** (see the honest list above).
- **For the next session, in order:** (1) **tomorrow 06:00-10:00 WIB the first automatic sitting
  should run by itself** (restart ClipMaker's app first - see above); check the phone the next
  morning: two `posted` rows with links, or a Telegram fallback with the reason. Then the 24 h views
  reading rides the next sitting. (2) The 14-day YouTube test needs Timmy's Google sign-in (§5.6).
  (3) The real brands, one login per day; the musically login flow is proven up to the code screen -
  the next login exercises the robot's own code entry (`--code-file`).


**What you must do**
- Nothing right now. When Chameleon is restarted, the platform-password route is live for the first login.
- The G2G post is live: https://vt.tiktok.com/ZSp7oooX8/ (ClipMaker already has it).


**Firm rule (user, 2026-11-18): the robot touches the phone only from 06:00 to 10:00 your time (WIB).** Every
robot job runs inside it: posting, engagement, views, setup, logins, wipes, app updates. Outside it the phone
belongs to your other scripts; the robot sends no commands at all (§7.2, §9).

RobotApp is "Chameleon for phones": a small program on the laptop that drives the user's old Android phone over
adb. It owns the phone's **spaces** (one Android user per brand), their proxies, their setup, the logins and the
posting. ClipMaker calls it, the way ClipMaker calls Chameleon (CustomBrowser) for browsers.

Jobs:
- post each new TikTok/Instagram account's **first 10 posts** from the phone app (the Account Warming Guide's rule);
- post **YouTube Shorts from the YouTube app**, per brand, as a test first (§6.7, §8.6);
- TikTok stays on the phone after 10 posts until ClipMaker has a TikTok laptop uploader (a later ClipMaker task).

Builds on ClipMaker `docs/plans/PLAN-ANDROID-POSTING.md` (research, 2026-11-16). This file doesn't repeat its
platform-detection research; read §5 there for that.

How to read this plan:
- **Fact** = I checked it (adb output on 2026-11-17/18, code, or a linked source).
- **Opinion** = my judgement, not proven.
- **AUTO** = the laptop does it over adb. **HANDS** = you do it, with the taps and minutes.

---

## 0. The short answer

**Layout (your decisions, 2026-11-18):**

| Where on the phone | Brand | Apps | Network | Lifetime |
|---|---|---|---|---|
| Owner user (user 0) | G2GChannel Clips (Indonesian test brand) | TikTok `trill` and YouTube, **already logged in by hand**: the robot only posts | home Wi-Fi, **no proxy, no VPN, ever** | permanent |
| US space 1-3 (new users) | the US brands, one per space | TikTok US build `musically`, Instagram, YouTube | `us-ps-2-newyork` through a locked VPN | while the brand posts by phone |

Ruang Ganda (999) and the old "Brand" user (10) get deleted first, which leaves room for **exactly 3 US spaces**
(the phone allows 4 users including the owner).

**What it does each day, all between 06:00 and 10:00 WIB:** one sitting per US brand (Instagram → TikTok →
YouTube), then G2G (TikTok → YouTube). With a third US brand that is **11 posts a day**; with today's brands
(Speed, Timmy, G2G) it is **8**. Timetable in §7.2: done by about 09:00 in winter and in summer, leaving
09:00-10:00 for retries, setup and logins.
**Two limits now:** the 4-hour window (it fits 3 US brands, just, in US summer time) and the 3 US spaces.

**What you still do:** about 10 minutes once (§4.1). Per new account: 0 HANDS, except a Telegram ping for a
CAPTCHA or an unusual check (~30 s), and possibly a few minutes the first time each brand's **Google** account
signs in on the phone (Google's checks are stricter, and nobody knows yet where its codes go, §5.6). Pings
always come between 06:00 and 10:00, when you're up.

**Things to know (the honest part):**
1. **YouTube's ~0 views are more likely the channels and the clips than the laptop** (§8.7). Only 4 Shorts were
   ever posted, all 2-3 days old, from brand-new channels. Test with Timmy first (§8.8).
2. **YouTube and TikTok on the phone for good means spaces stop recycling.** A US brand then holds its space
   forever → at most 3 US brands on this phone. Recycling only helps brands that leave the phone after 10 posts.
3. **G2G's posts move to the Indonesian morning** (~08:40-09:00 WIB) because of the 06:00-10:00 rule. Indonesian
   guides rate 19:00-22:00 higher; mornings are listed too, but as weaker slots (§7.2).
4. **US summer time is tight:** the third US brand's Instagram then has about 10 minutes to spare before the
   Instagram window closes (08:00 WIB in summer). A late morning means that one Instagram waits for tomorrow (§7.2).
5. **Speed and Timmy share one IP + one phone** (a linking risk, §3.4); the third US brand gets the second IP.
6. **The robot can't read TikTok/Instagram passwords yet** (Chameleon keeps them in its main process). A small
   Chameleon change is needed (§5.1).
7. **Wi-Fi adb dies on every reboot.** Fix: Android's "Wireless debugging" + a tiny boot helper (§9).
8. The Warming Guide's DO NOT list says "Use bots, automation tools, or scheduling apps for first 10 posts". You
   accepted this risk; the plan still starts with a throwaway account.
9. **The robot and your other scripts share one phone.** The robot needs the phone left in a known state at 06:00
   (owner user in front, no VPN in the owner, no space open). A shared lock is planned (§9).

---

## 1. Words used here

| Word | Meaning |
|---|---|
| space | One Android user on the phone (like a separate person on a shared tablet). Holds one brand's apps. Own data, own VPN. G2G's "space" is the owner user. |
| sitting | One visit to a space: open it, post to one or more apps, engage, close it. |
| proxy app | An app that turns the brand's Proxy-Seller US proxy into an Android VPN for that space. |
| lockdown | Android's "Always-on VPN" + "Block connections without VPN": if the proxy app dies, the space has no internet at all instead of leaking the home IP. US spaces only. |
| graduate | An account has made its first 10 posts and moves to laptop posting (today only Instagram can). |
| caller | The program that asks RobotApp to do things: ClipMaker now, maybe AIShorts later. |
| job | One robot task: set up a space, log in, make one sitting, read views, wipe a space. |

---

## 2. What I checked on the phone (facts, read-only adb)

Phone reached over Wi-Fi at 192.168.1.8:5555. Only read-only commands were run.

| Check | Command | Result |
|---|---|---|
| Model / build | `getprop` | Infinix X6815D, Android 13 (SDK 33), patch 2023-06-05, XOS 13.0.0, arm64 |
| Bootloader | `ro.boot.flash.locked`, `verifiedbootstate` | locked, green (not rooted) |
| SIM | `gsm.sim.state` | 2026-11-17: `LOADED,ABSENT`; **2026-11-18: `ABSENT,ABSENT`** (removed, as you said) |
| User limit | `pm get-max-users`, `dumpsys user` | 4 (owner included), "limit reached: false" |
| Running users | `pm get-max-running-users` | 2 (the owner + one other) |
| Users | `cmd user list -v` | 0 Owner; 10 "Brand" (full secondary); 999 "Ruang Ganda" (`profile.DUAL`, a profile of user 0) |
| User 999 rules | `dumpsys user` | **`no_config_vpn`, `no_debugging_features`**; adb is refused access to it |
| User 10 contents | `pm list packages -3 -i --user 10`, `dumpsys account` | TikTok (`trill`) and Instagram from the Play Store, 1 account signed in |
| Owner user | `dumpsys account` (account types counted, no names read), `settings get secure enabled_accessibility_services`, `cmd lock_settings` | 17 Google accounts, 3 Instagram logins, the **auto-clicker `com.rise.automatic.autoclicker.clicker` is on as an accessibility service**, a screen lock is set |
| Owner apps | `pm list packages --user 0` | TikTok `com.ss.android.ugc.trill` 47.8.3, YouTube 21.45.90, YouTube Music, Instagram, OpenVPN Connect, Chrome |
| TikTok US build | `pm list packages` | `com.zhiliaoapp.musically` is **not** on the phone |
| Always-on VPN | `settings --user N get secure always_on_vpn_app` | not set anywhere |
| Time zone / language | `persist.sys.timezone`, `persist.sys.locale` | Asia/Jakarta (automatic), en-US |
| adb | props, `settings get global adb_wifi_enabled` | old-style TCP mode on 5555 (lost on reboot); "Wireless debugging" off |
| Stay awake | `settings get global stay_on_while_plugged_in` | 7 (on with any charger) |
| Power / heat | `dumpsys battery` | USB powered, 85 %, good health, 40.5 °C |
| Memory / storage | `/proc/meminfo`, `df` | 7.7 GB RAM (2.3 GB free at the time), 87 GB free storage |
| Other users' files | `ls /storage/emulated/10` | Permission denied while user 10 is stopped (matters for copying videos in, §6.1) |

Not checked (needs a change on the phone, so it waits for step 1): creating/deleting users, installing apps, VPN,
time-zone switching, typing.

---

## 3. Question 1: spaces

### 3.1 How many spaces

- **Fact:** the phone allows 4 users **including the owner**.
- After deleting Ruang Ganda (999) and Brand (10): owner + **3 new US spaces** = 4. That is the hard ceiling
  without root, whether or not Ruang Ganda used to count.
- **Fact:** only 2 users can run at once (owner + one space), so only one US space is open at a time. That fits
  "one brand at a time".
- **Deleting them (AUTO, step 1):** `pm remove-user 10` and `pm remove-user 999`. adb may be refused for 999
  (it already refuses to list it); then **HANDS** (1 min): Settings → Ruang Ganda / Dual apps → remove the dual
  apps / turn it off. **Fact-check before deleting:** the dual space had 0 accounts signed in; whatever dual apps
  are in it are lost.

### 3.2 Ruang Ganda (999)

Can't be a space (no VPN, no adb, facts above). Deleted on your word.

### 3.3 G2G in the owner user: what to switch off

G2G stays Indonesian with no proxy, so the owner user (home Wi-Fi, Indonesia) matches it. **Rule: never a VPN or
lockdown on user 0** (it would also cut your own apps and adb). **G2G's TikTok and YouTube are already logged in by
hand in the owner user (your answer, 2026-11-18): the robot never logs G2G in, it only posts.** Your personal
TikTok is not on this phone, so `trill` holds only G2G. Re-checking the earlier concerns:

| Concern | Risk for G2G (opinion) | What to do (your answers) |
|---|---|---|
| **Auto-clicker accessibility service** (`com.rise.automatic.autoclicker.clicker`) | **High.** Any app can list the enabled accessibility services (a public Android API); an auto-clicker next to TikTok is a classic bot signal | **Uninstall it** (you said yes): `pm uninstall --user 0 com.rise.automatic.autoclicker.clicker`, AUTO in step 1, then check `enabled_accessibility_services` is empty |
| **Owner screen lock** (PIN/pattern is set) | Blocks the robot: G2G sittings need the owner user unlocked, and the robot must not hold your phone PIN | **Set it to None** (you said yes). HANDS 1 min: Settings → Security → Screen lock → None (asks your PIN once). Catch: anyone holding the phone opens your 17 Google accounts; the phone stays at home. It also makes Wi-Fi adb after a reboot simpler (§9) |
| 17 personal Google accounts, 3 Instagram logins | Since Android 8 an app can't list other apps' accounts without you picking them. Google sees every account on a device, so **G2G's Google/YouTube account is already linked to your personal ones** (you logged it in by hand) | Accepted for a test brand. The robot never taps "Continue with Google"/one-tap offers |
| Which YouTube account is active | The owner's YouTube app has many Google accounts | Each G2G sitting checks the avatar shows **G2G's channel** and switches to it if not; it leaves it on G2G afterwards (your phone's YouTube is rarely used; say if you want it switched back) |
| Which TikTok account is active | Only G2G is in `trill` | The robot checks the handle before posting; anything else → no post, ping |
| Notifications from your apps during a G2G sitting | A WhatsApp pop-up can cover a button | Do Not Disturb on during G2G sittings, back to your setting after (AUTO) |
| OpenVPN Connect in the owner | A VPN left on would move G2G off Indonesia | The robot checks no VPN is up before a G2G sitting; if one is, no posting |
| Location | Indonesia = true for G2G, no conflict | Still deny TikTok/YouTube location permission (the guide says location off) |
| Play Store auto-updates | Updating TikTok/YouTube/Instagram here updates every space (one shared install per app) | Auto-update off for those apps (HANDS 1 min, §4.1) |

G2G is permanent in user 0: no wipe, no recycling.

### 3.4 Brands, accounts and the one proxy

Facts (read-only from ClipMaker's `warmup.db` and Chameleon's database):

| Brand | Accounts | Network | Email login in Chameleon |
|---|---|---|---|
| G2GChannel Clips | TikTok (1 posted, 1 phone post queued), YouTube (2 Shorts); **no Instagram** | none (Indonesia) | **no email account assigned** to its TikTok or YouTube profile |
| Speed Expedia Clips | TikTok (1), Instagram (0, warming), YouTube (1 Short) | `us-ps-2-newyork` | Gmail with a linked Gmail profile; Instagram has a second email **without** a Gmail profile (its codes can't be read) |
| Timmy Clips | TikTok (2), Instagram (0, in its calm until ~2026-11-19), YouTube (1 Short) | `us-ps-2-newyork` | one Gmail for all three, Gmail profile linked |
| (none) | — | `us-ps-1-virginia` is bought but **unused** | — |

**Your decision (2026-11-18):** Speed and Timmy stay on `us-ps-2-newyork`. The **third US brand** (none exists
yet) gets `us-ps-1-virginia`, already paid and idle (auto-renew on, decisions.md 2026-11-10), so no extra cost.

**Linking risk (opinion):** one IP alone looks like a household. One IP **plus** one phone **plus** one Wi-Fi
behind it, for Speed and Timmy's 6 accounts, looks more like one person running several brands. If one account
gets banned for spam, platforms may look at accounts that share its IP and device (anti-detect vendors call
these "chain bans"; not verified). Separate Android users give each space its own app IDs, which helps, but the
IP and hardware stay shared. The third brand on its own IP keeps that cluster from growing.

**When another IP becomes worth it (opinion):** for every further new brand; and right away if **any** account on
`us-ps-2-newyork` is disabled or banned (new brands then go elsewhere; an existing account never changes IP).

Also: check Speed Instagram's email has a Gmail profile (its codes can't be read otherwise). G2G's missing email
logins in Chameleon no longer block the robot (it never logs G2G in), but are worth adding for the record.

---

## 4. Question 2: zero-touch setup

### 4.1 One-time phone setup

| # | Step | Who | Time |
|---|---|---|---|
| 1 | ~~SIM out~~ done (2026-11-18: `ABSENT,ABSENT`) | — | — |
| 2 | Owner user: set the screen lock to **None** (§3.3); the robot uninstalls the auto-clicker | HANDS + AUTO | 1 min |
| 3 | **Wireless debugging** on and paired once: Developer options → Wireless debugging → on → "Always allow on this network" → "Pair device with pairing code"; the laptop runs `adb pair` with the code you read out | HANDS + AUTO | 2 min |
| 4 | Install RobotApp's tiny boot helper ("Keeper", our own app from this repo) in the owner and let it turn Wireless debugging back on after a reboot (`pm grant ... WRITE_SECURE_SETTINGS`) | AUTO | — |
| 5 | Automatic time zone off (`cmd time_zone_detector set_auto_detection_enabled false` and `set_geo_detection_enabled false`), so only the robot sets it (§4.6) | AUTO | — |
| 6 | Delete user 10 "Brand" and Ruang Ganda 999 (§3.1) | AUTO, maybe HANDS | 0-1 min |
| 7 | Proxy app sing-box "SFA" (§4.4) installed once: Play Store in the owner, or the official GitHub release APK | HANDS 1 min or AUTO (your OK to download) | — |
| 8 | Play Store (owner): auto-update off for TikTok, Instagram, YouTube. The robot updates on purpose once a week and re-tests its screens | HANDS | 1 min |
| 9 | XOS battery manager (Phone Master): let SFA and Keeper run in the background if XOS asks; the robot also adds them to Android's battery allow-list | AUTO, maybe HANDS | 0-2 min |
| 10 | TikTok US build `musically` onto the phone (§4.7) | AUTO (Play first; a signed download is OK'd by you) | — |

Total HANDS: about 5-8 minutes, once. The AUTO parts run inside 06:00-10:00, in the free time after the
sittings (09:00-10:00) or on a day with no posts.

### 4.2 Per new US space: all AUTO

| # | Step | How (adb) | Check |
|---|---|---|---|
| 1 | Create the user | `pm create-user --user-type android.os.usertype.full.SECONDARY "US 1"` | "Success: created user id N" |
| 2 | Skip its setup wizard | `settings --user N put secure user_setup_complete 1`; `pm disable-user --user N com.google.android.setupwizard` | first open lands on the home screen |
| 3 | Start it in the background | `am start-user N` | `dumpsys activity users`: RUNNING_UNLOCKED |
| 4 | US settings | location off; language en-US (already the phone's); screen timeout 30 min | read back |
| 5 | Apps | `pm install-existing --user N com.zhiliaoapp.musically`, `com.instagram.android`, `com.google.android.youtube`, `io.nekohasekai.sfa` | `pm list packages --user N` |
| 6 | Permissions up front | `pm grant --user N <pkg> android.permission.READ_MEDIA_VIDEO` (+ images, camera, mic). Location and contacts **not** granted; notifications off | `dumpsys package` |
| 7 | VPN consent | `appops set --user N io.nekohasekai.sfa ACTIVATE_VPN allow`; fallback: the robot taps OK on Android's "Connection request" dialog | **unverified**, step 1 |
| 8 | Proxy config in | §4.4 | SFA shows the profile |
| 9 | Always-on + lockdown | `settings --user N put secure always_on_vpn_app io.nekohasekai.sfa`, `always_on_vpn_lockdown 1`, restart the user; fallback: the robot flips both switches in Settings → Network → VPN in that space | `dumpsys connectivity` shows the VPN for user N |
| 10 | Battery | `appops set --user N io.nekohasekai.sfa RUN_ANY_IN_BACKGROUND allow` | — |
| 11 | Chrome first run (for the leak check) | the robot taps "Accept & continue", "Use without an account", "No thanks" | Chrome opens a page |
| 12 | Leak check | §4.5 | must pass, or the space is marked broken |
| 13 | The brand's Google account (for YouTube) | §5.6 | YouTube shows the brand's channel |

**Facts behind it:** `pm create-user`, `install-existing`, `remove-user` exist on this phone (`pm help`). Always-on
VPN settings are stored per user (AOSP source, [e/OS mirror of the framework](https://gitlab.e.foundation/e/os/android_frameworks_base/-/commit/17e6183b85ba3038acb935aaa01415058b2e6ddd)),
but one AOSP commit says only the system may change them, so **a plain `settings put` may be ignored**; hence the
UI fallbacks. The VPN consent app-op exists ([bayton.org on vpndialogs](https://sysapps.bayton.org/packages/com.android.vpndialogs));
that `appops set` skips the dialog here is **not verified** ([someone's `pm grant` attempt failed](https://kaweah.freedombox.rocks/kiwix/stackoverflow.com_en_all_2023-11/questions/67980851/grant-android-vpn-permission-via-command-line-using-adb)).

Time per space (opinion): 3-5 minutes unattended, plus the Google sign-in (§5.6). Runs in the 09:00-10:00 free
slot, or in a sitting slot on a day that brand has nothing to post.

### 4.3 Google accounts in spaces (changed: YouTube needs one)

The earlier rule was "no Google account in a space". **YouTube changes that:** the YouTube app posts as a Google
account that lives on the device, so each US space gets **exactly one Google account: the brand's own Gmail**.

What that means (opinions):
- **No new link between a brand's accounts:** its TikTok, Instagram and YouTube already use the same Gmail
  (Timmy uses one Gmail for all three).
- **A phone with a Google account looks more normal** than one without.
- **Play Store is now signed in** in that space: auto-update **off** there too (the robot sets it in Play's
  settings), or it would update the apps for every space.
- **Backup to Google Drive off, Location history off, Chrome sync declined** (the robot answers those screens).
- No personal account ever goes into a US space.

### 4.4 The proxy app: sing-box (SFA)

Requirements: SOCKS5 with a login, DNS through the proxy, UDP/QUIC controlled, config pushed by the laptop.

| App | SOCKS5 + login | DNS through proxy | UDP/QUIC control | Config by laptop | Notes |
|---|---|---|---|---|---|
| **sing-box for Android (SFA)** | yes | yes, exact rules | yes, exact rules | JSON; import link `sing-box://import-remote-profile?url=...` ([docs](https://sing-box.sagernet.org/clients/general/)) | open source (SagerNet), [official Android client](https://sing-box.sagernet.org/clients/android/) |
| NekoBox | yes | yes | some | URL/clipboard import | built on sing-box; check if still maintained |
| Super Proxy | yes | unclear | unclear | by hand | closed source |
| OpenVPN Connect (already on the phone) | no | — | — | — | needs an OpenVPN server; Proxy-Seller sells HTTP/SOCKS5 |

**Opinion: SFA.** The robot writes the whole config: all traffic → `us-ps-2-newyork` SOCKS5 port 50101 with the
login; DNS answered through the proxy over TCP; **UDP blocked** (apps fall back from QUIC to TCP, WebRTC can't
leak; Proxy-Seller's SOCKS5 UDP support is unknown); IPv4 only; `strict_route`. The JSON keys differ between
sing-box versions, so the build session writes it for the installed version and checks it with `sing-box check`.

**How the config gets in (AUTO):** the laptop serves the file once, at a random one-time address on the home
network, for 60 s; the robot opens `sing-box://import-remote-profile?url=...` in the space and taps Import. The
file (it holds the proxy password) is deleted right after, never logged. Fallback: the robot types the values
into SFA's "New profile" screen. Proxy logins come from Chameleon (`GET /v1/proxies/:id?include_secrets=true`).

### 4.5 Leak check before every sitting (AUTO, ~30-45 s)

**US spaces** (the check runs inside the space, because the laptop's own adb commands don't use its VPN):
1. VPN up and locked: `dumpsys connectivity` shows SFA's VPN for user N; lockdown = 1.
2. IP: Chrome opens `https://1.1.1.1/cdn-cgi/trace` → `ip=` must be the proxy's IP, `loc=US`.
3. DNS: a DNS leak page (e.g. browserleaks.com/dns): every resolver in the US.
4. WebRTC: browserleaks.com/webrtc shows no IP but the proxy's (with UDP blocked: none).
5. Phone: no SIM, time zone America/New_York, location off.

**G2G (owner):** no VPN up; `loc=ID`; time zone Asia/Jakarta; no SIM.

Any failure → no posting; the post goes back as described in §8.4. Steps 3-4 run fully at setup and once a day;
every sitting runs at least 1, 2 and 5. **Opinion.**

### 4.6 Switching the phone's time zone per sitting (your decision)

**Fact:** the time zone is phone-wide (one setting for all users). `cmd alarm set-timezone <zone>` sets it (seen in
`cmd alarm help` on this phone); automatic detection must be off or it switches back.

**Does switching often look odd? (opinion)**
- **US spaces: no.** Their apps only run while their space is open, and the robot sets New York **before** opening
  the space. They never see Jakarta.
- **G2G's apps in the owner user: maybe.** The owner user always runs, so G2G's TikTok and YouTube could be awake
  in the background when the zone flips to New York and see a phone that "jumps" 12 hours daily without
  travelling. Real people almost never do that. No public evidence that TikTok punishes it, but it's an avoidable
  odd signal.
- Your own apps (Gmail, WhatsApp) see the flips too; harmless, but the phone's clock shows New York time part of
  the day.

**How to do it safely:**
1. Switch only **twice a day**, both inside the window: New York at **06:00** (the robot's first command of the
   day), Jakarta right after the last US sitting (~08:20). G2G's sitting comes after that switch. The phone shows
   New York time only 06:00-08:20; the rest of the day it is on Jakarta time for you and your other scripts.
   (Your timetable said 05:55; the firm 06:00-10:00 rule wins, and the switch takes a second, so it's the first
   step at 06:00.)
2. Before switching to New York: **force-stop G2G's TikTok and YouTube** in the owner (`am force-stop --user 0
   <pkg>`). A force-stopped app gets no broadcasts and no push until it is opened again, so it never sees New
   York. (YouTube is also your personal YouTube app; it just restarts when you open it.)
3. Never switch while a space app is open; check with `getprop persist.sys.timezone` and the clock after.
4. The network clock stays automatic (only the zone changes, the real time is always right).
5. A leftover US job after 08:20 (a retry in 09:00-10:00) switches to New York again first, and back to Jakarta
   right after; G2G's apps are force-stopped again before.
6. If the robot crashes mid-morning, its 10:00 clean-up (§9) still puts the zone back to Jakarta.

### 4.7 Getting TikTok's US build (`musically`) onto the phone

**Fact:** the phone has only `com.ss.android.ugc.trill` (TikTok's Asian build, from the Indonesian Play Store). US
users have `com.zhiliaoapp.musically`. Both can be installed side by side (different package names). G2G keeps
`trill`.

Options, in order (opinion):
1. **Play Store in a US space, signed in with a brand Gmail whose Play country is US**, behind the US proxy:
   search "TikTok" → if Play offers `com.zhiliaoapp.musically`, install it there. Then `pm install-existing --user M
   com.zhiliaoapp.musically` puts it in the other US spaces. Installed by Play, like on any US phone.
   **Unknown:** each brand Gmail's Play country (set when the account first used Play; Gmails made on the
   Indonesian IP are probably "Indonesia" and will get `trill`). Step 1 checks.
2. **A signed download, if Play won't offer it (you said OK, 2026-11-18):** APKMirror's listing for
   `com.zhiliaoapp.musically`, uploaded by TikTok's developer account. Before installing, the robot checks
   (`apksigner verify --print-certs`) that the signing certificate matches the one APKMirror shows for that app
   **and** the one in an older version of the same listing (same signer over time = not a re-signed copy). Any
   mismatch → stop, nothing installed. Installs with `adb install-multiple`. Catch: the installer then shows as
   adb, not Play (a small oddity; not known to matter). The download lands in its own folder outside the repo.
3. Never: a modded or "lite" build.

### 4.8 Wiping a US space for reuse (AUTO, ~3-5 min)

Only for brands that leave the phone (§7.3). Log out in each app → remove the Google account → `pm remove-user N`
→ create a fresh user (§4.2). Deleting the user (not just clearing app data) gives the next brand new Android IDs
([ANDROID_ID is per app-signing key, user and device](https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID)).

---

## 5. Question 3: automatic login

### 5.1 Where the logins come from (and the gap)

| Secret | Where it lives (fact) | How RobotApp gets it |
|---|---|---|
| Gmail password | Chameleon daemon, encrypted | `GET /v1/email-accounts/:id/password` (bearer token) |
| Proxy login | Chameleon daemon | `GET /v1/proxies/:id?include_secrets=true` |
| TikTok / Instagram password | `ChameleonData/platform-passwords.json`, Electron safeStorage (Windows DPAPI), **readable only by Chameleon's main process** | **None today.** Needs a small Chameleon change: a bearer-token route like `GET /v1/profiles/:id/platform-password?platform=tiktok`, or moving that store into the daemon. Built by the Chameleon session; step 1 waits for it |
| 6-digit email code | the brand's Gmail inbox | ClipMaker's `email_flow/mail_reader.py` (§8.3) |

**Fact:** ClipMaker's `onboard_maker.py` doesn't read passwords itself; the Electron app hands them over.
**Opinion:** RobotApp must not decrypt Chameleon's file itself. Ask Chameleon.

**Password rules (requirements):** fetched at the moment of typing, in memory only, dropped right after. Never in
the repo, files, logs, events, exceptions or screenshots (no screenshot while a password field is focused). Typed
through uiautomator2's connection, never `adb shell input text <password>` (that puts it on a command line).
Chameleon's bearer token sits in RobotApp's git-ignored `.env`. Tests use fake passwords. Claude never types a
password; only the robot program does, at run time.

### 5.2 TikTok login

Human-speed typing: 90-260 ms between characters, small random pauses. **One login attempt per account per day.**

1. Open TikTok in the space. First-run screens: interests → **Skip**; swipe tutorial → swipe; notifications →
   **Don't allow**.
2. **Profile** → **Log in** → "Use phone / email / username" → **Email / Username**.
3. Email/username → Continue → password → **Log in**.
4. "Verify it's you" code to email → code from Gmail (§8.3), typed. "Save login info?" / contacts / notifications
   → **Not now / Don't allow**. Anything in §5.4's right column → stop and ping.
5. Read the handle on the Profile tab and report it (ClipMaker's handles are empty today).
6. Scroll For You 3-5 min, watch-only.

G2G: **no login, ever** (already logged in by hand in the owner user). If G2G's TikTok or YouTube is ever found
logged out, the robot doesn't log it back in: it pings you and skips G2G that day.

### 5.3 Instagram login

1. Open Instagram → **Log in**.
2. Username/email → password → **Log in**.
3. "Check your email" / 6-digit code → from Gmail. "Unusual login attempt" → only **send code to email** is taken
   automatically. "Save your login info?", notifications, contacts, add phone → **Not now / Skip**.
4. Check the profile; scroll 3-5 min, watch-only.

### 5.4 What counts as a challenge

| The robot handles it | The robot stops, pings Telegram, waits |
|---|---|
| 6-digit code to the brand's email | any CAPTCHA (slider, puzzle, rotate, "Confirm you're human") |
| "Save login", notifications, contacts, interests, tutorials, "Not now" offers | phone/SMS code, "tap Yes on your other device" |
| Google: "Not now" on passkey / recovery / backup offers | selfie / video / ID check |
| | "incorrect password" (fix it in Chameleon) |
| | "too many attempts", "suspicious activity", disabled/suspended |
| | any screen it doesn't recognise for 60 s |

The ping: Telegram, screenshot, two buttons **Done** / **Give up**, and a code can be typed back as a reply
(for an SMS code that reached your own phone). You solve it on the phone or in scrcpy (~30 s). Pings only happen
06:00-10:00, so you're up. No answer in 15 min, or 10:00 comes → the job stops safely; nothing is retried until
the next day.

### 5.5 Moving the brands' accounts onto the robot phone (every login is a new-device login)

**Fact (your answer):** you hand-post everything from your Samsung S25+. Every account was created in a Chameleon
browser. So **the Infinix is a new device for every account**, TikTok, Instagram and Google alike.

What keeps the risk down (opinion):
- **Only the device changes, never the IP:** each US space uses its brand's proxy, the same IP the accounts'
  Chameleon profiles use.
- **Log in inside the 06:00-10:00 window, on a day before the account's first robot post** (in the 09:00-10:00
  free slot, = 21:00-22:00 New York in winter, 22:00-23:00 in summer: a normal evening hour for a US user), then
  3-5 min watch-only. Never in the same sitting as a post.
- **One new login per day**, at most. A week of watching after the first brand before the next.
- **Once the robot has an account (first robot post done), you log it out of your S25+** (your yes, 2026-11-18;
  HANDS ~1 min per account, Telegram reminds you). One phone per account looks more normal than an account
  bouncing between two phones and two networks every day.
- Never move an account inside a calm or after a fresh flag.

The safest order:
1. **Throwaway account** (a new US test brand, made in Chameleon, warmed like the others). One week. **Opinion:**
   put it on `us-ps-1-virginia`, not on Speed and Timmy's IP, so a flag on the throwaway can't touch them. Catch:
   if the throwaway gets flagged, the third real brand should not get that IP either. Afterwards its space is
   wiped, which tests recycling too.
2. **Speed's TikTok**, then **Timmy's TikTok** (no flags, few posts so far).
3. **Instagrams** after their calm ends and their first Story is up (Timmy's calm ends ~2026-11-19; Speed's
   Instagram is a replacement account, keep it gentle).
4. **Google/YouTube** sign-ins last: **Timmy first**, for the YouTube test (§8.8).
5. **G2G:** nothing to move; it's already logged in on this phone. It can start as soon as the owner-user changes
   (§3.3) are done.

### 5.6 Signing in the brand's Google account in a space (for YouTube)

Flow (AUTO): Settings → Passwords & accounts → Add account → Google (or YouTube → Sign in, which opens the same
Google screens) → email → Next → password → Next → possible checks → "I agree" to Google's terms → Google
services screen: **Backup off, Location off** → done. Then YouTube → avatar → check the **channel** is the
brand's (a Gmail can own several channels; pick by name).

Google's checks are stricter than TikTok's (opinion, from how Google treats new devices):
- **Where Google's codes go is unknown** (your answer: not sure what recovery the brand Gmails have). So plan for
  a ping every time Google asks: the robot screenshots Google's "Verify it's you" page, which **shows the masked
  destination** (e.g. "a code to j•••@gmail.com" or "•• 12"), and sends it to you on Telegram with the choices
  listed. You pick one with a button; if a code arrives somewhere you can read, you reply with it. If none of the
  choices reach you, you press Give up and that brand's Google sign-in waits (YouTube stays on the laptop).
- The robot itself only takes choices it can finish alone: a code to the brand's own Gmail (read by ClipMaker's
  Gmail reader).
- **"Tap Yes on your phone"** → only if the Gmail is signed in on an Android phone somewhere; it isn't, so this
  should not appear.
- **"Couldn't sign you in / try again later"** → stop; try again in 24 h+, never in a loop.
- **Location jump:** a Gmail made on the Indonesian IP signing in from New York is more likely to be checked.
  (The brand Gmails were made on different IPs; some without a proxy.)
- Budget: 0-5 min HANDS per brand, once.

---

## 6. Question 4: posting

### 6.1 Getting the video into the space's gallery (step 1 must prove one)

**Fact:** the shell can't list user 10's storage while it is stopped. Three ways, tried in this order:
1. Space running → `adb push clip.mp4 /storage/emulated/N/DCIM/Robot/` → ask the media scanner to index it.
2. `adb push` to `/data/local/tmp/`, then `content insert --user N --uri content://media/external/video/media`
   (with `relative_path` and a "pending" flag), `content write` to fill it, then clear "pending".
3. Last resort: a share intent into the app.

Fresh name and today's time, so it's the newest video. One copy per sitting serves all three apps.

### 6.2 How the robot finds buttons

- uiautomator2 reads the screen as elements with **resource-id**, **text** and **description**.
- TikTok's resource-ids are scrambled and change per version, so: **text/description first** ("Post", "Next",
  "Upload"), then a resource-id learned for this app version, then a picture-match on a screenshot.
- Each screen has a **signature** (a few texts that must be there). Every step waits for the next signature (up to
  30-60 s), never a fixed sleep.
- Taps land on a random point inside the button; short random waits between steps.
- **uiautomator2 is attached only while it must read the screen;** the engagement scroll uses plain `input swipe`.
- **Unverified (step 1, test #1):** uiautomator2 reading a secondary user's screen. Fallback: screenshots + text
  recognition on the laptop, and `input tap`.

### 6.3 The order inside one sitting (your correction)

One sitting per brand per day, all inside 06:00-10:00 WIB (your answers, 2026-11-18):
- **US brand:** **Instagram** (its window ends an hour earlier) → **TikTok** → **YouTube**.
- **G2G (owner user):** **TikTok** → **YouTube**.

Each post is followed by its own 3-5 min of watch-mostly engagement in that app, likes off (the guide: "do not
just post and close the app"). One copy of the video serves all the brand's apps.

### 6.4 TikTok post flow

| # | Screen | What the robot does | Found by | On failure |
|---|---|---|---|---|
| 0 | — | Preflight: phone online, battery ≥ 30 %, temp < 42 °C, time zone right, space open, leak check passed, app version known | adb | hand back (before Post) |
| 1 | Home feed | Open TikTok; close known pop-ups | "For You"/"Following" | restart app once, then hand back |
| 2 | — | Check the handle is the brand's (account switcher in G2G's `trill`) | Profile tab | hand back |
| 3 | Create | **+** | desc "Create" | hand back |
| 4 | Camera | **Upload** | "Upload" | hand back |
| 5 | Gallery | **Videos** → first tile; **its length must equal the clip's** | duration label | hand back |
| 6 | Editor | sound step (§6.6) → **Next** | "Next" | hand back |
| 7 | Post screen | paste the caption text, then **type** each hashtag and pick it from TikTok's list (`phone_posts.split_tags`) | "Add description" | hand back |
| 8 | Post screen | "Everyone can view"; no location | text | hand back |
| 9 | Post screen | **Write "Post pressed" to the job journal on disk, then tap Post once** | "Post" | from here: never tap Post again |
| 10 | Feed/profile | wait for "posted" (up to 5 min) | progress overlay | "unsure" |
| 11 | Profile | newest video → Share → **Copy link**; read it by pasting into TikTok's search box and reading that field | Share sheet | fallback: ClipMaker reads the newest post from the account's Chameleon browser; last: Telegram asks you for the link only |
| 12 | Feed | engage 3-5 min: watch most videos 60-100 %, uneven swipes, **likes off**, no follows, no comments | `input swipe` | ignore errors |

One log line per step (`data/logs/<date>.log`, no secrets); screenshots only on failure (`data/shots/`,
git-ignored).

**Never press Post twice:** the journal says `post_pressed=true` before the tap. Anything going wrong after that
gives **"unsure"**; the robot then *looks* for the post (newest on the profile, same length, made after the press)
and reports its link. If it can't tell, you're asked only for the link.

### 6.5 Instagram Reel flow

1. Open Instagram → home; check the account.
2. **+** → **REEL** → gallery → newest video, **length check** → **Next**.
3. Sound step (§6.6) → **Next**.
4. "Write a caption…" → paste the caption (Instagram links pasted hashtags; ClipMaker keeps 5).
5. Journal "Share pressed" → **Share** once → wait for "Your reel has been shared".
6. Profile → Reels → newest → Share → **Copy link** → read it (paste into the search box).
7. Engage 3-5 min, watch-mostly, likes off.

Before the first Reel (Warming Guide): profile photo, bio, at least one Story. The robot checks and, at first, asks
you on Telegram if one is missing.

### 6.6 The trending-sound step (TikTok, Instagram)

The guide: TikTok "a sound trending in the last 7 days"; Instagram "trending audio from the Reels tab".
- TikTok editor → **Add sound** → trending/suggested → one of the top few (random) → **Volume**: original high,
  added ~5-10 %.
- Instagram → **Audio** → **Trending** → pick → same mix.
- **Opinion:** the most fragile step. If it fails, post **without** an added sound and say so, unless
  `sound_required: true` (then hand back before Post). Built after the plain post works.

### 6.7 YouTube Shorts flow (new)

YouTube 21.45.90 is on the phone (owner); `install-existing` puts it in each US space.

| # | Screen | What the robot does | Found by | On failure |
|---|---|---|---|---|
| 0 | — | preflight as TikTok | adb | fall back (§8.6) |
| 1 | Home | open YouTube; avatar → check it's the brand's **channel**; switch if needed | avatar, channel name | fall back |
| 2 | Create | **+** (desc "Create") → **Create a Short** | sheet texts | fall back |
| 3 | Shorts camera | gallery button (bottom left) → newest video, **length check** | "Add" / thumbnail | fall back |
| 4 | Trim | **keep the full length** (the trimmer may default shorter); check the shown length equals the clip's → **Done** | length label | fall back |
| 5 | Editor | sound: **off by default for the test** (§8.8: change one thing at a time). Later option: **Add sound** from YouTube's library, low volume | "Add sound" | skip sound |
| 6 | Editor | **Next** | "Next" | fall back |
| 7 | Details | "Caption your Short" = ClipMaker's title (≤ 100 characters, the same title the laptop would use) | field hint | fall back |
| 8 | Details | **Visibility: Public**; **Audience: "No, it's not made for kids"** (the laptop uploader sets the same, `uploader.py`) | texts | fall back |
| 9 | Details | journal "Upload pressed" → **Upload Short** once | "Upload Short" | from here: never again |
| 10 | — | wait for upload + "processing" | progress | "unsure" |
| 11 | You → Your videos | newest Short → ⋮ → Share → **Copy link** (`https://youtube.com/shorts/<id>`); read it the same way | Share sheet | fallback: the channel's public feed `youtube.com/feeds/videos.xml?channel_id=...` read from the laptop gives the newest video, no login needed |
| 12 | Short | **pinned comment** when the campaign asks for one (G2G's does): comments → type → post → ⋮ → **Pin** | texts | note "pin it by hand" (as the laptop does today) |
| 13 | Shorts feed | engage 3-5 min, watch-mostly, likes off | `input swipe` | ignore |

**24 h views for YouTube** come from the laptop, not the phone: the public video page or the YouTube Data API
(statistics) with ClipMaker's existing Google API key, if it has one. No phone sitting needed.

### 6.8 The link and the 24-hour views (TikTok, Instagram)

- Link → ClipMaker `phone_posts.mark_posted` (same checks as a pasted link).
- 24 h views: read in the brand's next-day sitting, **right before that app's post** (so ~24 h after
  yesterday's; see the 23 h 30 min note in §7.2): profile → the post's tile ("▷ 1,234" / Reels play count) →
  ClipMaker `phone_posts.set_views` → the guide's first-post check decides whether today's post goes out. No extra
  sitting. An unreadable number → Telegram asks you, as today.

---

## 7. Spaces over time and the real ceiling

### 7.1 Lifecycle

```
brand states:   waiting ──> assigned(space) ──> logging_in ──> ready ──> posting ──> graduated ──> released
                   │                │                │
                   └── needs_you ◄──┴── challenge ◄──┘     blocked (wrong password, disabled): out of the queue

space states:   free ──> building ──> ready(brand) ──> wiping ──> free
                               └──> broken (leak check or setup failed: you're told, nothing posts from it)
```

G2G in the owner: always `ready`, never wiped.

### 7.2 One day on the phone (your capacity rules)

Rules used (your decisions, 2026-11-18):
- **The robot works only 06:00-10:00 WIB.** No night or evening sittings.
- **No gap between a brand's own apps** in one sitting. **30 minutes between brands** (from one brand's last post to
  the next brand's first post).
- US Instagram must be inside 6-9 PM New York, US TikTok inside 6-10 PM New York (Targeting Guide). YouTube has no
  window rule; inside the sitting it lands around 6:30-8:10 PM New York, which Buffer's 2026 Shorts data counts
  among the best slots (**6 PM and 7 PM**, [Buffer](https://buffer.com/resources/best-time-to-post-on-youtube/?lang=en)).
- G2G goes last, after the time zone is back on Jakarta.
- Durations (opinion, measured in step 1): open space + checks 2 min; read yesterday's views 2 min; each post
  ~5 min + link 1 min; engagement 4 min (3-5).

So one US sitting takes ~36 min, with its posts at about +9 (Instagram), +19 (TikTok), +29 (YouTube) minutes. The
30-min gap then starts the next brand ~50 min after the previous one.

**Timetable, one day (your time, WIB). Winter: New York = WIB − 12 h. Summer (March to early November):
New York = WIB − 11 h.**

| WIB | New York (winter / summer) | Phone does | Posts |
|---|---|---|---|
| 06:00 | 18:00 / 19:00 | time zone → New York; force-stop G2G's TikTok and YouTube | |
| 06:00-06:36 | 18:00 / 19:00 | **US 1**: open space, leak check, yesterday's views → Instagram (~06:09) → engage → TikTok (~06:19) → engage → YouTube (~06:29) → engage | 3 |
| 06:50-07:26 | 18:50 / 19:50 | **US 2**: Instagram (~06:59) → TikTok (~07:09) → YouTube (~07:19) | 3 |
| 07:40-08:16 | 19:40 / 20:40 | **US 3**: Instagram (~07:49) → TikTok (~07:59) → YouTube (~08:09) | 3 |
| 08:16 | — | time zone → Jakarta | |
| 08:31-08:55 | — | **G2G** (owner user): yesterday's views → TikTok (~08:39) → engage → YouTube (~08:49) → engage | 2 |
| 08:55-10:00 | — | **free slot:** retries, late posts, setup, logins, wipes, weekly app updates | |
| 10:00 | — | hard stop; the phone is yours/your scripts' | |
| | | **Total** | **11** (8 with today's brands: Speed, Timmy, G2G) |

**Does it fit?**
- **Winter: yes, easily.** US 3's Instagram (~07:49 WIB = 7:49 PM New York) has ~70 min to spare before Instagram's
  9 PM close; its TikTok ~2 h before 10 PM.
- **Summer: yes, but tight for one post.** The Instagram window is then 05:00-08:00 WIB, and the robot can't start
  before 06:00. US 3's Instagram (~07:49) has **~10 minutes** to spare. TikTok's window ends 09:00 WIB, fine.
  If the morning runs more than ~10 min late (a challenge, a slow upload), US 3's Instagram waits for tomorrow
  (its TikTok and YouTube still go). To soften it (opinion): put last the brand whose Instagram has graduated or
  has nothing due, and keep the brand order fixed (it also keeps each brand's posting time steady).
- **Why not your ~07:00 and ~08:00 starts:** the 30-min gap counts from one brand's **last** post to the next
  brand's **first** post, so sittings can start ~50 min apart. Starting US 3 at 08:00 would put its Instagram at
  ~08:09: fine in winter, **past the 08:00 Instagram close in summer**. The plan uses the earliest allowed start.
- **G2G's time moves to ~08:40 WIB** (an Indonesian morning). Indonesian guides rate **19:00-22:00 WIB** highest
  ([Dealls](https://dealls.com/pengembangan-karir/jadwal-fyp-tiktok),
  [timetopost](https://timetopost.co/best-time-to-post/tiktok/indonesia/)); mornings appear on some lists as
  weaker slots. Fine for a test brand; the cost of the 06:00-10:00 rule.
- **Phone busy** ~06:00-08:55 (about 3 h); ~65 min free for leftovers. **Two limits now:** the window (3 US
  brands in summer) and the spaces (3 US).
- Anything that misses its platform's window or 10:00 waits for tomorrow. A Post is never pressed after 09:55;
  engagement is cut short at 10:00 if needed.

**The "yesterday's views first" catch (and fix):** with sittings at the same time every day, yesterday's post is
~23 h 50 min old when today's sitting starts, a few minutes short of the guide's 24 h, and ClipMaker only asks
for views after 24 h (`phone_posts.CHECK_AFTER`). It matters only while an account is in the guide's first-post
check (until it reaches 200+ views on a warmup post). Fix (opinion): the robot reads each app's views **right
before that app's post** (so ~24 h), and ClipMaker accepts a robot reading from **23 h 30 min** on. The guide's
"wait 24 hours" is about letting views come in; ten minutes don't change that. Cleared accounts' views are read
whenever convenient (the free slot).

**Setup, logins and wipes** (your rule): in the 08:55-10:00 free slot, or in a brand's sitting slot on a day it
has nothing to post. A new account's first login happens on a day **before** its first robot post, never in the
same sitting.

**Do I agree with "no gap within a brand"? Yes (opinion), reasons:**
- The Targeting Guide's flag is "rapidly switch between accounts on same device": many accounts **on one
  platform** traded back and forth. Posting one clip to your own Instagram, TikTok and YouTube in one sitting is
  what every creator does, and each app has exactly one account in that space.
- The gap that matters, between brands, stays.
- Each post still gets its own 3-5 min of engagement in its app before the next app opens.

**Changes this needs in ClipMaker** (listed in §8.4): the 30-min gap per brand instead of per account
(`phone_posts.account_gap`), one sitting taking a brand's due posts (Instagram, TikTok, YouTube), the robot's
06:00-10:00 WIB window, G2G's window = 06:00-10:00 WIB, and the 23 h 30 min views reading.

### 7.3 Recycling, honestly

**Fact:** `campaign_posts.SUPPORTED = ("youtube", "instagram")`; TikTok stays a phone post forever until ClipMaker
has a TikTok uploader (your decision: later). And if YouTube moves to the phone for good, YouTube never leaves it.

So a US brand that posts TikTok or YouTube by phone **keeps its space for as long as it posts**. With 3 US spaces,
that means **3 US brands on this phone, total**, until:
- ClipMaker gets a TikTok laptop uploader **and** YouTube goes back to (or stays on) the laptop, so a brand can
  graduate after 10 TikTok/Instagram posts; or
- a second phone (§10).

Recycling (§4.8) is still built, for brands that do graduate, but it isn't the capacity engine it looked like.

### 7.4 Who else could use RobotApp later (opinion)

- **AIShorts** (`..\AIShorts`): its new TikTok/Instagram accounts need the same "first 10 from the phone". It would
  call the same CLI (§8.2), but it competes for the same 3 spaces.
- A "phone warmup" job: scroll-only sittings in the days before an account's first post.

---

## 8. Question 5: ClipMaker integration and the API

### 8.1 Shape (opinion): a CLI that speaks JSON, like `onboard_maker`

RobotApp is a Python package with one command, `robot`. ClipMaker starts it as a background process and reads JSON
lines from it (the pattern ClipMaker already uses with Electron, `email_flow/stdio_protocol.py`). No server: one
phone, one job at a time; a lock file stops two jobs. RobotApp keeps its own state (`data/robot.db`: spaces,
brands, jobs, journal) and a `data/status.json` with what the phone is doing now.

### 8.2 Commands

| Command | Input | Output |
|---|---|---|
| `robot doctor` | — | phone online?, battery, temp, time zone, users used/max, free spaces, app versions |
| `robot brands add` | JSON: brand key, name, `network` (`"proxy": <chameleon proxy id>` or `"home": "ID"`), `space` (`"new"` or `"owner"`), accounts `[{platform, profile_id, email_account_id, handle?}]` | queued |
| `robot brands list` | — | each brand: state, space, handles |
| `robot setup-next` | — | events; next waiting brand → free space → setup → logins |
| `robot sitting` | sitting JSON (below) | events, then one `done` per post |
| `robot views` | profile id + post URL | events, then `done` with views |
| `robot release` | brand key | log out, wipe the space |
| `robot status` | job id | final result of a job (after ClipMaker restarted mid-job) |

**No secrets cross this API.** Callers pass Chameleon ids; RobotApp fetches secrets itself at typing time.

Sitting job (one brand, its due posts in order):
```json
{"proto": 1, "job_id": "...", "brand": "<brand id>", "time_zone": "America/New_York",
 "work_window": "06:00-10:00 Asia/Jakarta", "no_post_after": "09:55",
 "read_views": [{"upload_id": "...", "platform": "instagram", "url": "https://..."}],
 "posts": [
   {"upload_id": "...", "platform": "instagram", "video": "C:/.../x.mp4", "length_s": 41.2,
    "caption": "...", "hashtags": ["#timmy"], "sound": "trending", "sound_required": false},
   {"upload_id": "...", "platform": "tiktok", "video": "C:/.../x.mp4", "length_s": 41.2,
    "caption": "...", "hashtags": ["#timmy", "#zombies"], "sound": "trending"}],
 "engage_minutes": [3, 5], "must_finish_by": "2026-11-18T02:00:00Z"}
```
A YouTube post adds `"title"` and `"pinned_comment"`.

Events (one JSON object per line):
```json
{"t": "step", "job": "...", "post": "<upload id>", "n": 4, "of": 12, "name": "pick_video"}
{"t": "views", "upload_id": "...", "views": 1234}
{"t": "needs", "kind": "email_code", "platform": "tiktok", "email_account_id": "...", "sender": "tiktok", "since": "<ISO>"}
{"t": "needs", "kind": "human", "why": "TikTok shows a slider CAPTCHA", "screenshot": "data/shots/...png", "wait_s": 900}
{"t": "done", "post": "<upload id>", "outcome": "posted", "url": "https://...", "handle": "...", "sound": null, "engaged_s": 242}
{"t": "done", "post": "<upload id>", "outcome": "failed_before_post", "reason": "VPN down"}
{"t": "done", "post": "<upload id>", "outcome": "unsure_after_post", "reason": "link not readable"}
```
Answers on stdin: `{"t": "answer", "kind": "email_code", "code": "123456"}`, `{"t": "answer", "kind": "human",
"done": true}` (or `"code": "..."` for a code you read on your own phone), `{"t": "abort"}`.

If stdin closes (ClipMaker restarted): before a Post press → stop cleanly; after → finish reading the link, write
the result; ClipMaker picks it up with `robot status`.

### 8.3 Codes and pings

- **Email codes:** ClipMaker answers `needs: email_code` with its existing `GmailInboxReader` (the same
  `open_gmail` path `onboard_maker.py` uses). One Gmail reader, in one place.
- **Human pings:** ClipMaker's existing Telegram bot (`tools/approve.py`; "don't add a second bot"), Done / Give up
  buttons, typed codes passed back.

### 8.4 ClipMaker changes (other sessions own these files; agree first)

| File | Change |
|---|---|
| new `tools/phone_robot.py` | the adapter: builds a sitting from a brand's due posts, spawns `robot sitting`, event loop in a thread, answers `needs`, maps each `done` |
| `tools/approve.py` (`phone_tick`, `send_phone_post`) | robot branch before Telegram: `CLIPMAKER_PHONE_ROBOT=1` + brand opted in + RobotApp says `ready` + `robot doctor` OK → claim the brand's due rows → start the sitting. Otherwise Telegram as today. `send_phone_post` learns YouTube (title + description) for the hand-post fallback |
| `phone_posts.py` | `account_gap` → **per brand** (no gap within a brand); new `due_for_brand()` (Instagram, TikTok, YouTube order); robot sittings only 06:00-10:00 Asia/Jakarta; G2G's window = 06:00-10:00 Asia/Jakarta; robot YouTube rides in the brand's sitting (no own window); a robot views reading counts from 23 h 30 min (`CHECK_AFTER`); hand posts via Telegram keep today's windows; `check_link` accepts `youtube.com/shorts/<id>` / `youtu.be/<id>`; the first-post 24 h check (`verdict`) stays TikTok/Instagram only; `steps()` text for a YouTube hand post |
| `campaign_posts.py` | `post_mode`: YouTube → `phone` for brands with "YouTube by phone" on (`PHONE_PLATFORMS` gets YouTube only through that switch); everything else unchanged |
| `bridge/uploads.py` | **no change needed:** the upload worker only takes `mode = 'auto'` rows (`campaign_posts.queued`), and `phone_to_submit` already submits any posted phone row to Content Rewards. To check: YouTube's pinned comment is then the robot's job |
| `tools/phone_mode.py` + the Phone page in `web/src` | YouTube rows and "the robot is posting this now (step 4 of 12)" from RobotApp's `status.json` |
| config | `.env`: `CLIPMAKER_PHONE_ROBOT=0` (default off), `ROBOTAPP_DIR`. `data/phone_robot.json`: `{"brands": {"<brand id>": {"robot": true, "youtube_by_phone": false, "window": "default"}}}`; a file, so no database migration |
| handles | robot reports each handle after login; ClipMaker stores it (the `warmup_db.py` owner decides how) |
| tests | `tests/test_phone_posts.py`, `tests/test_campaign_posts.py`: per-brand gap, windows, YouTube links, the switch on/off |

**Owners to ask:** the clipper session (`warmup_db.py`, `bridge/*`), the phone-mode session (`phone_mode.py`,
the Phone page). Hand posting stays exactly as it is for every brand not opted in.

### 8.5 Outcomes

| Outcome | TikTok / Instagram | YouTube |
|---|---|---|
| `posted` | `mark_posted(url)` → Content Rewards submit as today | same |
| `failed_before_post` | `unclaim` → normal Telegram post with the reason | see §8.6 |
| `unsure_after_post` | row stays claimed; Telegram asks only for the link | same; the laptop also checks the channel's public feed |

### 8.6 "YouTube by phone robot", per brand

- Off for every brand by default. When on, that brand's **new** YouTube campaign posts become `mode = 'phone'` and
  wait for the robot's YouTube sitting; the laptop uploader never sees them. Brands with it off keep today's
  laptop path untouched.
- If the robot fails before pressing Upload: **during the test**, the post moves to the next day's robot sitting
  (so the test isn't mixed); after the test, a setting decides: back to the laptop (`mode = 'auto'`) or Telegram.
- Rows already queued keep the mode they were queued with.

### 8.7 Are the ~0 YouTube views the laptop's fault? (honest answer)

**Facts (`warmup.db`, 2026-11-18):** only **4 YouTube Shorts** were ever posted: G2G two (2026-11-15 23:04 and
23:07 UTC, 3 minutes apart), Speed one and Timmy one (2026-11-16). All are 2-3 days old, from channels a few days
old. No 24 h views were recorded for any of them. They went through YouTube Studio's web page in each account's
own Chameleon browser (`uploader.py`), set public and "not made for kids". For comparison, Timmy's first TikTok
had 139 views in 24 h.

**Opinion: the channels and the content are the more likely cause, not the laptop:**
- **Too few, too new:** 4 Shorts on days-old channels say almost nothing. New channels' first Shorts often get
  close to nothing while YouTube decides who to show them to.
- **Crowded content:** IShowSpeed / Timmy / G2G moments are clipped by many channels; the same moment uploaded
  dozens of times competes with itself.
- **Two Shorts 3 minutes apart** on a brand-new G2G channel.
- **No public evidence** that YouTube gives less reach to web uploads. Guides only say a desktop upload must be
  vertical/square and up to 3 minutes to count as a Short ([postsyncer](https://postsyncer.com/blog/how-to-post-youtube-shorts));
  the `youtube.com/shorts/...` links show these were recognised as Shorts.
- What the phone **could** change: the app's Shorts editor can attach a library sound (an extra way to be found),
  and maybe how YouTube scores the upload. Possible, unproven.

**Check first, it's free (HANDS, 5 min in YouTube Studio for each Short):** Visibility public; "Restrictions:
None"; no copyright claim; Analytics → **"Shown in feed"**. If it was never shown in the Shorts feed, YouTube
isn't testing it at all (an eligibility problem, e.g. a claim or "reused content"). If it was shown but swiped
away, it's the clip and its first seconds.

### 8.8 The YouTube test (before switching all brands)

- **Timmy** (your choice), **14 days**, one Short a day at the same time: the YouTube slot of Timmy's sitting
  (~06:30 WIB, 6:30 PM New York in winter). On laptop days ClipMaker holds Timmy's YouTube row until that same
  time, then lets the laptop uploader post it, so both methods post at the same hour.
- **Alternate days:** phone, laptop, phone, laptop… (7 each). Comparing "before vs after" would mix up the method
  with the channel simply getting older; alternating keeps both the same age.
- **Change one thing only:** same titles, same kind of clips (pick which clip goes to which day by coin flip), **no
  added sound on the phone** for the test.
- **Measure:** views at 24 h and 72 h (laptop, from the public page/API), plus "Shown in feed" from Studio.
- **Decide:** if the phone's median is at least **2×** the laptop's and wins at least 5 of the 7 pairs, switch more
  brands. Otherwise keep the laptop and work on the clips/channels instead.
- **Cost:** the robot needs a working YouTube flow and Timmy's Google sign-in on the phone first (build step 6).

---

## 9. Question 6: Wi-Fi adb that survives

| Problem | Fact | Plan |
|---|---|---|
| Reboot loses adb over Wi-Fi | `service.adb.tcp.port=5555` isn't persistent; the persistent one needs root | Android 11+ **Wireless debugging** (paired once, §4.1). **Keeper** turns it on at boot (`adb_wifi_enabled=1`, allowed by a one-time `pm grant ... WRITE_SECURE_SETTINGS`); the laptop finds the phone by mDNS (`adb mdns services`). **Unverified on XOS.** A Shizuku release claims the same trick works without root ([release note](https://newreleases.io/project/github/thedjchi/Shizuku/release/v13.6.0.r1117-thedjchi)); the official Shizuku manual says non-root needs a manual start after each reboot ([manual](https://shizuku.rikka.app/guide/setup/)) |
| Owner screen lock | Fact: a PIN/pattern is set now | Removed for G2G anyway (§3.3), so Keeper runs right after a reboot |
| IP address changes | home router | mDNS finds it; optional HANDS: reserve 192.168.1.8 in the router (5 min) |
| A VPN blocking the laptop | Opinion: a US space's lockdown covers only that space's apps; adb belongs to the owner, which **never** gets a VPN | step 1 checks adb stays up with a space's lockdown on |
| Phone asleep / XOS kills helpers | stay-awake is on (7); Keeper and SFA on the battery allow-list | `robot doctor` before every job |
| Flaky cable | — | Cable only as a fallback: when a USB phone appears, the laptop re-enables Wi-Fi debugging from it (`adb -d tcpip 5555`) |
| Phone offline in the window | — | From 05:50 the laptop only *checks* the connection (no phone commands); at 06:00 it reconnects if needed. Offline → posts fall back (§8.5); one "phone offline" message per morning |
| Sharing the phone with your other scripts | Your rule: the phone is theirs outside 06:00-10:00 | A shared lock file on the laptop (e.g. `%LOCALAPPDATA%\PhoneLock\phone.lock`, holder + until-time): RobotApp takes it at 06:00 and gives it back by 10:00; your scripts should take it too and leave it free in the window. At 06:00 the robot checks the phone is in a known state (owner user in front, no space running, no VPN in the owner) and, if not, waits up to 5 min, then pings you rather than closing someone else's work |
| A job runs past 10:00 | Firm rule | No Post pressed after 09:55; at 10:00 the robot finishes reading a link if a post is already out, stops engagement, closes the space, puts the time zone back to Jakarta, turns Do Not Disturb off, releases the lock. Unfinished posts wait for tomorrow |
| Heat | 40.5 °C charging with the screen on | screen off between sittings; pause above 43 °C; sittings are spread over the day |

---

## 10. Question 7: later, for more than 3 US brands (trade-offs only)

| Option | Gains | Costs / risks (opinion) |
|---|---|---|
| **A second phone** (you said no buying now) | 3 more US spaces, separate hardware (less linking), a second lane | money; a new budget phone ~Rp 2.5 juta, less used (earlier plan §6). **The cleanest step when you need it** |
| **Temporary root via a kernel exploit** (patch 2023-06) | persistent adb port, more users (`fw.max_users`), deeper control | running exploit code from the internet on a phone you use; may crash or brick; lost on reboot; root is something apps look for |
| **ID spoofing** (fake model, serial, Android ID) | each space looks like another phone | needs root or hooking (Xposed/LSPosed), the family you ruled out; a broken spoof is worse than a real phone |
| **Cloud phones** (GeeLark, DuoPlus, VMOS) | many "phones" | monthly cost; data-centre phones are a known farm pattern |
| **Recycling** (§4.8) | free | only works for brands that leave the phone (§7.3) |

---

## 11. Question 8: build steps (each one useful on its own)

Prerequisites outside RobotApp:
- **P1. Chameleon:** a bearer-token route for the platform password (§5.1). ~1 session. Without it no login.
- **P2.** Your HANDS from §4.1 (about 10 minutes) and the answers in §13.
- Later, separate: ClipMaker TikTok laptop uploader (your decision: later).

| Step | What | Done when | Effort (guess) |
|---|---|---|---|
| **1. One account, end to end** | Repo skeleton, `robot doctor`, the **06:00-10:00 guard** (refuses to touch the phone outside it) and the shared phone lock. Uninstall the auto-clicker; delete users 10 and 999; create **one** US space; `musically` onto the phone (§4.7); apps, permissions, time-zone switching, SFA + config, always-on + lockdown, leak check, **video into the space** (§6.1), uiautomator2 in a secondary user, login of the **throwaway** with its Gmail code (a hand-run code reader for now), **one TikTok post** from a plain CLI (no ClipMaker), link read, 3-5 min engagement. You watch in scrcpy; kill switch = turn the phone's Wi-Fi off | one real post on the throwaway, 0 HANDS except watching; timings measured | 2-3 sessions |
| 2. Wi-Fi adb survives reboots | Keeper, Wireless debugging pairing, mDNS reconnect, watchdog, cable fallback | phone rebooted → robot reconnects alone | 1 session |
| 3. Safety rails + fake phone | journal (never press Post twice), outcomes, screen signatures, FakePhone tests, password-leak test | tests green | 1 session |
| 4. ClipMaker wiring | §8.4 behind `CLIPMAKER_PHONE_ROBOT` (off) + per-brand opt-in; sittings, per-brand gap and windows; `needs` answered; Phone mode line | an opted-in brand's sitting posts by robot; any failure lands in Telegram as today | 1-2 sessions |
| 5. Instagram | §6.5 + login §5.3 | one Reel by the robot | 1-2 sessions |
| 6. YouTube | Google sign-in (§5.6), Shorts flow (§6.7), the "YouTube by phone" switch (§8.6), then **the 14-day test** (§8.8) | one Short by the robot; test running | 1-2 sessions + 2 weeks |
| 7. G2G in the owner | owner checks (§3.3), handle/channel check (no login), no-VPN check, Do Not Disturb, sitting after the switch back to Jakarta | G2G's TikTok and YouTube posted by robot at ~08:40 WIB | 1 session (can come early: no login needed) |
| 8. Sound + views + engagement polish | §6.6, §6.8 | 24 h views read in sittings; trending sound added (or cleanly skipped) | 1-2 sessions |
| 9. Lifecycle | queue, assign, setup-next, graduate, wipe, reuse (§7.1) | a graduated brand frees its space alone | 1 session |
| 10. Move real accounts in | one per day, safest first (§5.5) | each account clean for a week on the robot | your time: a look per day |

Total: about 11-15 build sessions, one at a time (they touch the same files). Each in a **fresh session** with
this file as its brief.

---

## 12. Risks

| Risk | Likelihood (opinion) | What we do |
|---|---|---|
| The Warming Guide forbids automation for the first 10 posts | certain, by its letter | you accepted; throwaway first |
| Platform detects automation → shadowban/ban | unknown, moderate | human-like timing, watch-mostly, likes off, uiautomator2 attached only when needed |
| **Speed and Timmy (6 accounts) on one IP + one phone get linked** | medium | separate users; the 3rd US brand on `us-ps-1-virginia`; new brands on new IPs (§3.4) |
| **Auto-clicker seen next to G2G's TikTok** | gone once uninstalled | uninstall in step 1 (§3.3) |
| **US summer time: the 3rd brand's Instagram misses 08:00 WIB** | some mornings | earliest starts, fixed order, a graduated/idle Instagram goes last; else it waits a day (§7.2) |
| G2G posts in a weaker Indonesian morning slot | certain | accepted (06:00-10:00 rule) |
| The robot and your other scripts collide on the phone | low with the lock | shared lock file + known-state check at 06:00 (§9) |
| G2G's Google linked to your personal Google accounts | certain | accepted for a test brand |
| Daily time-zone flips seen by G2G's apps | low | flip twice a day, force-stop G2G's apps first (§4.6) |
| Google sign-in checks in spaces | likely once per brand | where codes go is unknown: you're pinged with the masked destination; one attempt per day; YouTube stays on the laptop for that brand if it fails (§5.6) |
| New-device logins (every account) | likely once per account | same IP as before; one per day; stop using the S25+ for robot accounts |
| `musically` can't come from Play (no US Play account) | medium | a signed download, certificate checked (you OK'd it, §4.7) |
| YouTube by phone doesn't beat the laptop | likely (opinion) | the 14-day test decides before switching brands (§8.8) |
| Spaces never free up (TikTok/YouTube stay on the phone) | certain until ClipMaker changes | 3 US brands max on this phone; second phone later |
| App update changes a screen | high over months | auto-update off everywhere; weekly planned update + a dry run up to (not including) Post |
| Double post | very low | journal before Post; look, don't repeat |
| Wrong video posted | very low | length check on the gallery tile and the YouTube trimmer |
| Phone offline / rebooted | medium | Keeper + watchdog; posts fall back |
| Password leaks into logs/screenshots | low | fetched at typing time only; redaction; a test greps all output |
| Owner phone unlocked (no PIN) | certain after §3.3 | phone stays at home; your choice |
| Battery heat/swelling | low but real | screen off between sittings; pause above 43 °C |

---

## 13. Your answers (2026-11-18) and what's still open

Answered:
1. SIM: removed (confirmed by adb: `ABSENT,ABSENT`).
2. Automation risk: accepted; throwaway first.
3. Ruang Ganda: delete.
4. User 10: delete; the robot rebuilds spaces.
5. G2G: Indonesian test brand, no proxy, in the owner user with `trill`, permanent, never a VPN on user 0.
6. TikTok: US brands use `musically`; G2G keeps `trill`.
7. TikTok laptop uploader: later, a separate ClipMaker task.
8. Time zone: switched by the robot (Jakarta for G2G, New York for US brands).
9. Engagement: 3-5 min after each post, watch-mostly, likes off.
10. Proxies: Speed and Timmy on `us-ps-2-newyork`; the third US brand (when made) on `us-ps-1-virginia`.
11. You hand-post from the S25+: every robot login is a new-device login.
12. YouTube Shorts from the phone, per brand, inside each brand's sitting (Instagram → TikTok → YouTube).

Second round (2026-11-18):
- **Firm rule:** the robot works only 06:00-10:00 WIB; every job inside it (§7.2, §9).
- Owner user: uninstall the auto-clicker; screen lock → None.
- G2G's TikTok and YouTube are already logged in by hand in the owner user: the robot never logs G2G in. Your
  personal TikTok is not on this phone.
- G2G Instagram: not now (so 11 posts a day with a third US brand, 8 today).
- Brand Gmails' recovery: unknown → plan for pinging you (§5.6).
- YouTube test brand: Timmy.
- `us-ps-1-virginia`: for the third US brand.
- Downloads: a signed `musically` is OK after the certificate check, if Play won't offer it.
- Robot accounts get logged out of your S25+ once the robot has them.

Still open (small, none blocks step 1):
1. **Throwaway's IP:** `us-ps-1-virginia` (keeps a flag away from Speed/Timmy, but then the third brand may need
   a new IP if the throwaway gets flagged), or `us-ps-2-newyork`? (§5.5; my pick: Virginia.)
2. **The 23 h 30 min views reading** for robot sittings (§7.2): OK?
3. **Your other scripts:** can they take/leave the shared phone lock (§9)? What do they leave on screen at 06:00?
4. **G2G's YouTube app:** leave it on G2G's channel after posting, or switch back to your account?

*(All four are answered now — see §13.1. The list stays as the record of what was asked.)*

### 13.1 Answers to those four (user, 2026-11-18, third round)

1. **Throwaway IP: `us-ps-1-virginia`. Yes.** The throwaway (and its one space) uses Virginia, not Speed/Timmy's
   New York IP.
2. **The 23 h 30 min views reading: yes.** A views reading at **23 h 30 min** counts as the 24 h reading for the
   guide's first-post check.
3. **Shared phone lock: yes, use it.** No other script uses the phone today. Any future script must take the lock
   and leave the owner user on the home screen with no space open.
4. **G2G's YouTube app stays on G2G's channel** after posting; the robot does not switch it back.

### 13.2 Decided by the builder (no user question needed)

- **2026-11-19, HARD RULE (user, after a near-miss): "GTA 6 Clips Clips" is a REAL brand, never the
  throwaway.** It appeared in ClipMaker (new, warming, both passwords saved in Chameleon) and the builder
  wrongly assumed it was the test brand. **No account, login or post of GTA 6 Clips may ever be used to test
  the robot.** Only read-only database looks were made before the correction; nothing was touched.
- **No throwaway account exists yet** (§5.5's throwaway would be a brand-new test brand made in Chameleon).
  The first real login waits until the user names or creates one. Until then the robot tests only against the
  FakePhone/fixtures, and any real post is a queued row of a brand the user has approved for it.
- **2026-11-18, P1:** the platform-password route lives in the **daemon** and reads the file the main process
  already writes, instead of moving the store into the daemon. Smallest change, one storage format, and the
  daemon already has a decrypt channel to the main process. Route name and query as in §5.1.
- **2026-11-18, P1:** `platform=youtube` is refused (400) rather than silently answered with the Gmail password:
  two different secrets behind one name would be a trap for the caller.
- **2026-11-18, step 1: the first real post is G2G's queued TikTok clip, not a throwaway.** No throwaway account
  exists yet: a brand-new TikTok account is a ClipMaker/Chameleon sign-up job, not something RobotApp can make.
  G2G's `trill` is already logged in by hand in the owner user, and a TikTok clip has been queued for it since
  2026-11-15 (`ad6b19b9…`, "He bets on a fight and picks the wrong guy"). Posting that one proves the whole
  pipeline on a post that is waiting anyway, with no new-account risk. The throwaway login path is built and
  unit-tested; its first real run happens when an account exists. **User approved this on 2026-11-18.**
- **2026-11-18, step 1: the two APKs are downloaded from official sources.** sing-box (SFA) 1.14.4 from F-Droid
  (`io.nekohasekai.sfa_746.apk`, built and signed by the developer; certificate SHA-256
  `32250a4b…3549641`, recorded in the runbook), and TikTok's US build from APKMirror only after `apksigner`
  shows the expected signer. **User approved both on 2026-11-18.**
- **2026-11-18, step 1: the proxies in Chameleon are HTTP, not SOCKS5.** Both Proxy-Seller records are
  `protocol: http, port: 50100` (the plan assumed SOCKS5 on 50101), so the sing-box config builds an `http`
  outbound for them and a `socks` one only if a record says so.
- **2026-11-18, step 1: the running Chameleon app predates the new route.** It answers 404 for
  `/v1/profiles/:id/platform-password` until it is restarted. No login is needed before that restart; the G2G
  post needs no password at all.



---

## 14. Repo layout (planned, nothing built)

```
RobotApp/
  PLAN.md               this file
  robotapp/             Python package (adb + uiautomator2)
    phone.py            the Phone interface (real over adb, FakePhone for tests)
    spaces.py           create / start / wipe users; owner-user rules
    timezone.py         switch + verify, force-stop rules
    window.py           the 06:00-10:00 WIB guard, the shared phone lock, the 10:00 clean-up
    vpn.py              sing-box config, import, always-on, lockdown
    leakcheck.py
    secrets.py          Chameleon daemon client (secrets in memory only)
    login/              tiktok.py, instagram.py, google.py
    post/               tiktok.py, instagram.py, youtube.py, sound.py
    engage.py
    sitting.py          one brand's posts in order
    journal.py          write-ahead "Post pressed" record
    screens/            screen signatures per app version
    cli.py              the `robot` command and its JSON protocol
  keeper/               the tiny Android boot helper (Kotlin)
  tests/                FakePhone fixtures (saved screen dumps)
  data/                 git-ignored: robot.db, status.json, logs, screenshots, journal
```

---

## Sources

- ClipMaker: `docs/plans/PLAN-ANDROID-POSTING.md`, `phone_posts.py`, `tools/approve.py`, `tools/phone_mode.py`,
  `campaign_posts.py`, `bridge/uploads.py`, `uploader.py`, `tools/upload.py`, `email_flow/mail_reader.py`,
  `onboard_maker.py`, `docs/decisions.md`, `docs/handoff-phone-posts.md`, `data/warmup.db` (read-only).
- CustomBrowser: `app/src/main/my-accounts.ts`, `app/src/main/platform-passwords.ts`, `app/src/main/secret-vault.ts`,
  `app/src/main/data-dir.ts`, `app/src/daemon/api.ts`, `~/ChameleonData/custombrowser.db` (read-only).
- Android: [ANDROID_ID](https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID);
  [VPN guide](https://developer.android.com/develop/connectivity/vpn);
  [Always-on VPN per user](https://support.google.com/work/android/answer/9213914);
  [AOSP multi-user testing](https://source.android.com/docs/devices/admin/multi-user-testing);
  [always-on settings per user (framework commit)](https://gitlab.e.foundation/e/os/android_frameworks_base/-/commit/17e6183b85ba3038acb935aaa01415058b2e6ddd);
  [VPN dialogs / ACTIVATE_VPN](https://sysapps.bayton.org/packages/com.android.vpndialogs);
  [`pm grant CONTROL_VPN` doesn't work](https://kaweah.freedombox.rocks/kiwix/stackoverflow.com_en_all_2023-11/questions/67980851/grant-android-vpn-permission-via-command-line-using-adb).
- sing-box: [Android client](https://sing-box.sagernet.org/clients/android/);
  [import-remote-profile link](https://sing-box.sagernet.org/clients/general/).
- Shizuku: [manual](https://shizuku.rikka.app/guide/setup/);
  [non-root start-on-boot fork](https://newreleases.io/project/github/thedjchi/Shizuku/release/v13.6.0.r1117-thedjchi).
- Posting hours: [Buffer, Shorts (2026 update)](https://buffer.com/resources/best-time-to-post-on-youtube/?lang=en);
  [Tryordinal, Shorts](https://www.tryordinal.com/blog/best-time-to-post-on-youtube-shorts);
  [Dealls, TikTok Indonesia](https://dealls.com/pengembangan-karir/jadwal-fyp-tiktok);
  [timetopost, TikTok Indonesia](https://timetopost.co/best-time-to-post/tiktok/indonesia/).
- YouTube upload method: [postsyncer guide](https://postsyncer.com/blog/how-to-post-youtube-shorts) (no official
  YouTube statement found either way).
- uiautomator2: [github.com/openatx/uiautomator2](https://github.com/openatx/uiautomator2).
- Phone facts: adb read-only output, 2026-11-17 and 2026-11-18 (§2).
