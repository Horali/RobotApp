# RobotApp: the phone robot (build plan)

Status: **plan only, nothing built.** Written 2026-11-17. Ask the user before any code.

RobotApp is "Chameleon for phones": a small program on the laptop that drives the user's old Android phone over
adb. It owns the phone's **spaces** (one Android user per account-in-warmup), their proxies, their setup, the
logins and the posting. ClipMaker calls it, the way ClipMaker calls Chameleon (CustomBrowser) for browsers.

First job: post each new TikTok/Instagram account's **first 10 posts** from the phone app (the Account Warming
Guide's rule), with almost no hand work.

Builds on ClipMaker `docs/plans/PLAN-ANDROID-POSTING.md` (research, 2026-11-16). This file does not repeat its
platform-detection research; read §5 there for that.

How to read this plan:
- **Fact** = I checked it (adb output on 2026-11-17, code, or a linked source).
- **Opinion** = my judgement, not proven.
- **AUTO** = the laptop does it over adb. **HANDS** = you do it, with the taps and minutes.

---

## 0. The short answer

**Yes, the robot can do almost all of the setup, the logins and the posting by itself.** After one short
one-time setup (about 10-15 minutes of HANDS, §4.1), a new account needs **0 HANDS**, except a Telegram ping
when TikTok or Instagram shows a CAPTCHA or an unusual check (~30 s to solve).

But the phone check found **six things you need to know first** (all facts from adb, §2):

1. **A SIM card still looks inserted.** The phone reports SIM slot 1 as `LOADED`, operator country `id`
   (Indonesia). The plan assumes no SIM. Please check the tray (§13 Q1).
2. **"Ruang Ganda" (user 999) cannot be a space.** Android itself forbids it a VPN (`no_config_vpn`) and adb
   (`no_debugging_features`). So it can never be behind a US proxy or be driven by the robot.
3. **Only 2 spaces for sure, maybe 3.** The phone allows 4 users in total, and 3 exist (owner 0, Brand 10,
   Ruang Ganda 999). Android says "limit reached: false", so at least one more user fits. Whether Ruang Ganda
   counts toward the 4 decides between 2 and 3 robot spaces. Creating one user (step 1) answers it safely.
   **Opinion:** don't use the owner (user 0) as a space (§3.3).
4. **TikTok accounts can't leave the phone yet.** ClipMaker has no TikTok uploader on the laptop
   (`campaign_posts.SUPPORTED = ("youtube", "instagram")`), so every TikTok post stays a phone post forever. Space
   recycling then only works for Instagram. To recycle TikTok spaces too, ClipMaker needs a TikTok laptop
   uploader (a separate ClipMaker task, §7.4).
5. **The robot can't read TikTok/Instagram passwords yet.** Chameleon keeps them in its main window process only
   (`platform-passwords.json`, "no read path"), not in its daemon. A small Chameleon change is needed (§5.1).
6. **Wi-Fi adb dies on every reboot** (`service.adb.tcp.port=5555`, `persist.adb.tcp.port` empty). The fix is
   Android's newer "Wireless debugging" plus a tiny boot helper (§9).

**Opinion on risk:** unchanged from the earlier plan. The Warming Guide's DO NOT list says "Use bots, automation
tools, or scheduling apps for first 10 posts". The robot is an automation tool by that rule. Test it on a
throwaway account first (§11, step 1).

---

## 1. Words used here

| Word | Meaning |
|---|---|
| space | One Android user on the phone (like a separate person on a shared tablet). Holds one brand's TikTok + Instagram while they warm up. Own apps, own data, own VPN. |
| account | One platform account (e.g. Timmy's TikTok). A brand has up to two accounts in a space. |
| proxy app | An app that turns the brand's Proxy-Seller US proxy into an Android VPN for that space. |
| lockdown | Android's "Always-on VPN" + "Block connections without VPN": if the proxy app dies, the space has no internet at all instead of leaking the home IP. |
| graduate | An account has made its first 10 posts; it moves to laptop posting. |
| caller | The program that asks RobotApp to do things: ClipMaker now, maybe AIShorts later. |
| job | One robot task: set up a space, log in, make one post, read views, wipe a space. |

---

## 2. What I checked on the phone (facts, read-only adb, 2026-11-17)

Phone reached over Wi-Fi at 192.168.1.8:5555. Only read-only commands were run.

| Check | Command | Result |
|---|---|---|
| Model / build | `getprop` | Infinix X6815D, Android 13 (SDK 33), patch 2023-06-05, XOS 13.0.0, arm64 |
| Bootloader | `ro.boot.flash.locked`, `verifiedbootstate` | locked, green (not rooted) |
| SIM | `gsm.sim.state`, `gsm.operator.iso-country` | `LOADED,ABSENT` and `id,` → **slot 1 has a working SIM** |
| User limit | `pm get-max-users`, `dumpsys user` | 4, "**limit reached: false**" |
| Running users | `pm get-max-running-users`, `dumpsys activity users` | 2; now running: 0 and 999 |
| Users | `cmd user list -v` | 0 Owner (current); 10 "Brand" (full secondary); 999 "Ruang Ganda" (`profile.DUAL`, a profile of user 0) |
| User 999 rules | `dumpsys user` | restrictions `no_sms`, **`no_config_vpn`, `no_debugging_features`**; `pm list packages --user 999` → "Shell does not have permission to access user 999" |
| User 10 rules | `dumpsys user` | `no_sms`, `no_outgoing_calls`, `no_record_audio` (normal for a secondary user in the background) |
| User 10 contents | `pm list packages -3 -i --user 10`, `dumpsys account` | **Not empty:** TikTok and Instagram installed there today (01:19 / 01:35) through the Play Store, and 1 account signed in (a Google one, judging by the Play installs) |
| User 10 settings | `settings --user 10 get ...` | setup complete = 1, location off, screen timeout 30 s, no screen lock, no accessibility service |
| User 0 | `dumpsys account` (counted types only, no names read), `settings get secure enabled_accessibility_services`, `cmd lock_settings` | 17 Google accounts, 3 Instagram logins, an **auto-clicker accessibility service is on**, and a screen lock (PIN/pattern) is set |
| TikTok package | `pm list packages` | `com.ss.android.ugc.trill` 47.8.3 (TikTok's build for Asian markets, from the Indonesian Play Store), not `com.zhiliaoapp.musically` (the US/global build) |
| Instagram | `dumpsys package` | `com.instagram.android` 455.0.0.51.72 (a factory-installed stub, updated by Play) |
| Proxy/VPN apps | `pm list packages` | only OpenVPN Connect in user 0; no SOCKS-to-VPN app yet |
| Always-on VPN | `settings --user N get secure always_on_vpn_app` | not set in users 0 and 10 |
| Time zone / language | `persist.sys.timezone`, `persist.sys.locale` | Asia/Jakarta (automatic), en-US |
| adb | `settings get global adb_wifi_enabled`, props | old-style TCP mode on port 5555 (lost on reboot); "Wireless debugging" off |
| Stay awake | `settings get global stay_on_while_plugged_in` | 7 (on for any charger); screen timeout user 0 = 30 min |
| Power / heat | `dumpsys battery` | USB powered, 85 %, health good, **40.5 °C** |
| Memory / storage | `/proc/meminfo`, `df` | 7.7 GB RAM (2.3 GB available now), 87 GB free |
| Other users' files | `ls /storage/emulated/10` | Permission denied while user 10 is stopped (matters for copying videos in, §6.1) |

Not checked (needs a change on the phone, so it waits for step 1): creating a user, installing apps, VPN, typing.

---

## 3. Question 1: spaces

### 3.1 How many spaces the phone really allows

- **Fact:** max 4 users; 3 exist; Android says the limit is not reached; secondary users have no per-type cap
  (`mMaxAllowed: -1`).
- **Opinion (from how Android's code counts):** profiles like Ruang Ganda usually count toward the 4. Then the
  phone allows **one more user** (id 11): spaces = Brand (10) + one new = **2 spaces**. If Ruang Ganda doesn't
  count: 3 spaces.
- **Safe test (step 1):** create one user, then read `dumpsys user` again. "limit reached: true" means Ruang
  Ganda counts. No second creation attempt is needed.
- **Fact:** only 2 users can run at once. The owner always runs, so **only one space can be open at a time**. That
  fits the "one account at a time" rule anyway. Opening a space may stop Ruang Ganda in the background (to check in
  step 1; your dual apps restart when you open them).

### 3.2 Ruang Ganda (999): no

It cannot have its own VPN and cannot be driven over adb (facts above). Its traffic would leave on your home
Indonesian IP. **It can't be a space, ever, without root.** The only way to gain its slot is to delete it, which
deletes the dual apps in it (your call, §13 Q3).

### 3.3 The owner (user 0) as a space: possible, not recommended

| | Owner (user 0) | A new user |
|---|---|---|
| VPN + lockdown | **Fact:** possible. **Opinion:** lockdown in user 0 would also cut your own apps on this phone off the internet when the proxy app dies, and could cut adb over Wi-Fi (adb runs as a user-0 program). | Only that space's apps are affected. |
| What the apps can see | Your 17 Google accounts, 3 Instagram logins, WhatsApp, Facebook apps, and the **auto-clicker accessibility service** (TikTok can see accessibility services in its own user). | A clean, empty user. |
| Identity | Indonesian personal phone behind a US IP. | Nothing personal. |
| Can be wiped for reuse | No (your data). | Yes (delete and recreate). |

**Opinion:** if you need a third space and Ruang Ganda counts, deleting Ruang Ganda is better than using the owner.

### 3.4 The brand -> account -> proxy map (read-only from ClipMaker's `warmup.db` and Chameleon's database)

| Brand | Accounts on TikTok / Instagram (posted so far) | Proxy | Email login in Chameleon |
|---|---|---|---|
| G2GChannel Clips | TikTok (1 posted, 1 phone post queued); no Instagram | **none** (home Indonesian IP) | **no email account assigned to the TikTok profile** |
| Speed Expedia Clips | TikTok (1); Instagram (0, warming) | `us-ps-2-newyork` | TikTok: Gmail with a linked Gmail profile. Instagram: two emails assigned, **one has no Gmail profile linked** (codes can't be read from it) |
| Timmy Clips | TikTok (2); Instagram (0, warming, in its 7-day calm) | `us-ps-2-newyork` | one Gmail for all three, Gmail profile linked |
| (unused) | — | `us-ps-1-virginia` is **not used by any brand** | — |

Facts: Speed and Timmy share one IP (allowed by the 2026-11-10 rule: "two accounts may share an IP"). Handles are
empty in `warmup_profiles.account_handle` for all accounts, so the robot must read the handle after login and
report it back.

What to fix (opinions):
- **G2G needs a US proxy before it can have a space.** A space without a proxy would post from Indonesia. The free
  IP is `us-ps-1-virginia`. Catch: G2G's TikTok was made on the Indonesian IP, so moving it to the US *and* to a new
  device at once is the riskiest move of all (§5.4). Option: keep G2G hand-posted, or give G2G a fresh account
  born on the US IP.
- **Speed and Timmy on the robot:** two spaces, same IP, same phone, 30+ minutes apart. Same as your hand posting
  today. Acceptable.
- **New brands: one IP per brand.** About $3/month each (decisions.md, 2026-11-10). Not a new phone.
- Add the missing logins with Chameleon's new **Edit** button in Show accounts (G2G's TikTok email; check Speed
  Instagram's email has a Gmail profile).

---

## 4. Question 2: zero-touch setup

### 4.1 One-time phone setup (before the first space)

| # | Step | Who | Time |
|---|---|---|---|
| 1 | Take out the SIM if one is in (§2) | HANDS | 1 min |
| 2 | Turn on **Wireless debugging** and pair the laptop once: Settings → System → Developer options → Wireless debugging → on → "Always allow on this network" → "Pair device with pairing code"; the laptop runs `adb pair` with the code you read out | HANDS + AUTO | 2 min |
| 3 | Install RobotApp's tiny boot helper ("Keeper", our own app, built from this repo) in the owner user and give it the right to turn Wireless debugging back on after a reboot (`pm grant ... WRITE_SECURE_SETTINGS`) | AUTO | — |
| 4 | Phone time zone America/New_York, automatic time zone off (`cmd time_zone_detector set_auto_detection_enabled false`, `cmd alarm set-timezone America/New_York`). **Fact:** the time zone is phone-wide, so your owner user's clock shows New York time too | AUTO (your OK) | — |
| 5 | Install the proxy app (sing-box "SFA", §4.4) once in the owner user: from the Play Store, or the robot installs the official GitHub release APK | HANDS 1 min or AUTO (your OK to download) | — |
| 6 | Play Store (owner user): turn off auto-update for TikTok and Instagram. **Fact:** an app is one shared install for all users, so updating it in the owner updates every space. The robot then updates on purpose, once a week, and re-tests its screens | HANDS | 1 min |
| 7 | XOS battery manager (Phone Master): allow SFA and Keeper to run in the background, if XOS asks. The robot also adds them to Android's battery allow-list (`cmd deviceidle whitelist +<pkg>`) | AUTO, maybe HANDS | 0-2 min |
| 8 | Decide what happens to user 10 "Brand" (it has a Google account and Play-installed apps): **opinion:** delete it and let the robot build every space the same way | AUTO (your OK) | — |
| 9 | Decide TikTok's package: keep `trill` (Asia build) or switch every space to `musically` (US build) (§12) | your decision | — |

Total HANDS: about 5-10 minutes, once.

### 4.2 Per new space: all AUTO

Each step is a plain adb command; the robot checks the result before the next.

| # | Step | How (adb) | Check |
|---|---|---|---|
| 1 | Create the user | `pm create-user --user-type android.os.usertype.full.SECONDARY "Space B"` | "Success: created user id N" |
| 2 | Skip its setup wizard | `settings --user N put secure user_setup_complete 1`; `pm disable-user --user N com.google.android.setupwizard` | first open lands on the home screen |
| 3 | Start it in the background | `am start-user N` | `dumpsys activity users`: RUNNING_UNLOCKED |
| 4 | US settings | location off (`settings --user N put secure location_mode 0`); language en-US (already the phone's); screen timeout 30 min | read back |
| 5 | Apps, no Play Store sign-in | `pm install-existing --user N <tiktok pkg>`, `com.instagram.android`, `io.nekohasekai.sfa` | `pm list packages --user N` |
| 6 | Permissions up front (no pop-ups later) | `pm grant --user N <pkg> android.permission.READ_MEDIA_VIDEO` (+ images, camera, mic for TikTok/Instagram). Location and contacts **not** granted. Notifications left off | `dumpsys package` |
| 7 | VPN consent pre-granted | `appops set --user N io.nekohasekai.sfa ACTIVATE_VPN allow`. Fallback: the robot taps OK on Android's "Connection request" dialog | **unverified**, step 1 |
| 8 | Proxy config in | §4.4 | SFA shows the profile |
| 9 | Always-on + lockdown | `settings --user N put secure always_on_vpn_app io.nekohasekai.sfa` and `always_on_vpn_lockdown 1`, then restart the user. Fallback: the robot opens Settings → Network → VPN → gear in that space and flips both switches | `settings --user N get ...` and the VPN shows in `dumpsys connectivity` for that user |
| 10 | Battery | SFA allowed to run in the background (`appops set --user N <pkg> RUN_ANY_IN_BACKGROUND allow`) | — |
| 11 | Chrome first run (needed for the leak check) | the robot taps "Accept & continue", "Use without an account", "No thanks" | Chrome opens a page |
| 12 | Leak check | §4.5 | must pass, or the space is marked broken |

**Facts behind it:** `pm create-user`, `install-existing`, `set-user-restriction` exist on this phone (`pm help`).
Always-on VPN settings are stored per user (AOSP source, [e/OS mirror of the framework](https://gitlab.e.foundation/e/os/android_frameworks_base/-/commit/17e6183b85ba3038acb935aaa01415058b2e6ddd)),
but one AOSP commit says only the system can change them, so **a plain `settings put` may be ignored on this build**.
That is why every step has a UI fallback. The VPN consent app-op exists ("activate a VPN connection without user
intervention", [bayton.org on vpndialogs](https://sysapps.bayton.org/packages/com.android.vpndialogs)); that
`appops set` skips the dialog on this phone is **not verified**. Someone reports `pm grant ... CONTROL_VPN` does
not work and fell back to tapping the dialog
([Stack Overflow copy](https://kaweah.freedombox.rocks/kiwix/stackoverflow.com_en_all_2023-11/questions/67980851/grant-android-vpn-permission-via-command-line-using-adb)).

Time per space (opinion): 3-5 minutes, unattended.

### 4.3 Why no Play Store account in a space

- The apps come from the owner's existing install (`install-existing`), so no Google account is needed.
- **Opinion:** Play Store stays enabled (apps may ask Google's Play Integrity check, which goes through the Play
  Store app); it just has nobody signed in. Whether Play Integrity works with no account signed in: **not
  known**, watch for errors in step 1.

### 4.4 The proxy app: sing-box (SFA)

Requirements: SOCKS5 with a login, DNS through the proxy, UDP/QUIC carried or blocked, config pushed by the
laptop, no clicking through menus by hand.

| App | SOCKS5 + login | DNS through proxy | UDP/QUIC control | Config by laptop | Notes |
|---|---|---|---|---|---|
| **sing-box for Android (SFA)** | yes (`socks` outbound has `username`/`password`) | yes, exact rules | yes, exact rules | JSON file; import by link `sing-box://import-remote-profile?url=...` ([docs](https://sing-box.sagernet.org/clients/general/)) | open source (SagerNet), [official Android client](https://sing-box.sagernet.org/clients/android/) |
| NekoBox | yes | yes | some | URL/clipboard import | built on sing-box; check if still maintained before using |
| Super Proxy | yes | unclear | unclear | by hand | closed source, simple |
| OpenVPN Connect (already on the phone) | no | — | — | — | needs an OpenVPN server; Proxy-Seller sells HTTP/SOCKS5 |

**Opinion: SFA.** The robot writes the whole config, so DNS and UDP are exactly what we say:

- all traffic of the space → the brand's Proxy-Seller IP, SOCKS5 port 50101 with the login;
- DNS answered through the proxy over TCP (no DNS leaves the home line);
- **UDP blocked** (TikTok/Instagram fall back from QUIC to normal TCP; WebRTC can't leak). Proxy-Seller's SOCKS5
  UDP support is unknown, so blocking is the safe default;
- IPv4 only (no IPv6 leaks around the tunnel); `strict_route` on.

The exact JSON keys changed between sing-box versions (1.11 / 1.12), so the build session writes it for the
installed version and checks it with `sing-box check` on the laptop first.

**How the config gets in (AUTO):** the laptop serves the file **once**, at a random one-time address on the home
network, for 60 seconds; the robot opens `sing-box://import-remote-profile?url=...` in the space and taps Import.
The file holds the proxy password, so it is deleted from the laptop right after, and never logged. Fallback: the
robot types the values into SFA's own "New profile" screen.

Proxy logins come from Chameleon: `GET /v1/proxies/:id?include_secrets=true` (daemon, bearer token). **Fact:** the
route exists (`app/src/daemon/api.ts`).

### 4.5 Leak check before every session (AUTO, ~30-45 s)

The laptop's own adb commands don't go through the space's VPN, so the check must run **inside** the space:

1. **VPN up and locked:** `dumpsys connectivity` shows a VPN network owned by SFA in user N; lockdown setting = 1.
2. **IP:** Chrome in the space opens `https://1.1.1.1/cdn-cgi/trace`; the robot reads `ip=` (must equal the
   brand's proxy IP) and `loc=US`.
3. **DNS:** Chrome opens a DNS leak page (e.g. browserleaks.com/dns); every resolver must be in the US, none
   Indonesian.
4. **WebRTC:** browserleaks.com/webrtc must show no public IP other than the proxy (with UDP blocked it should show
   none).
5. **Phone:** no SIM (`gsm.sim.state` all ABSENT), time zone America/New_York, location off in the space.

Any failure → no posting; the post goes back to Telegram with the reason. The full DNS/WebRTC pages run at setup
and once a day; every session runs at least 1, 2 and 5. **Opinion.**

### 4.6 Wiping a space for reuse (AUTO, ~3-5 min)

1. Log out of TikTok and Instagram inside the app (looks like a normal person leaving a device).
2. `pm remove-user N` (deletes every file of that space).
3. Create a fresh user (§4.2) for the next account.

**Why delete instead of "clear data":** **Fact:** Android's ID that an app sees is unique per app-signing key,
**user** and device ([ANDROID_ID](https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID)).
Clearing an app's data keeps the same user, so the next account would get the old account's ID. A new user gives
a new ID.

---

## 5. Question 3: automatic login

### 5.1 Where the logins come from (and the one gap)

| Secret | Where it lives (fact) | How RobotApp gets it |
|---|---|---|
| Gmail password | Chameleon daemon, encrypted | `GET /v1/email-accounts/:id/password` (bearer token) |
| Proxy login | Chameleon daemon | `GET /v1/proxies/:id?include_secrets=true` |
| TikTok / Instagram password | `ChameleonData/platform-passwords.json`, encrypted with Electron safeStorage (Windows DPAPI), **readable only by Chameleon's main process** ("there is no read path to the renderer or the logs") | **None today.** Needs a small Chameleon change: a bearer-token route like `GET /v1/profiles/:id/platform-password?platform=tiktok` (or moving that store into the daemon). To be built by the Chameleon session; RobotApp step 1 waits for it |
| 6-digit email code | the brand's Gmail inbox | ClipMaker's `email_flow/mail_reader.py` (reads Gmail through the Gmail account's own Chameleon profile, no IMAP); see §8.3 |

**Fact:** ClipMaker's `onboard_maker.py` doesn't read passwords itself: the Electron app hands them over in an
environment variable and an identity file it deletes after reading.

**Opinion:** RobotApp should not decrypt Chameleon's file itself (it would copy Chameleon's crypto and break when
Chameleon changes). Ask Chameleon.

**Safety rules for passwords (all built in, opinion → requirements):**
- Fetched at the moment of typing, kept in memory only, dropped right after. Never in the repo, files, logs, job
  files, events, exceptions or screenshots (a screenshot is never taken while a password field is focused).
- Typed through uiautomator2's connection, not `adb shell input text <password>` (that would put the password on
  a command line).
- The bearer token for Chameleon lives in RobotApp's git-ignored `.env` (or Windows Credential Manager).
- Tests use fake passwords. Claude (the assistant) never types a password; only the robot program does, at run
  time.

### 5.2 TikTok login, screen by screen (AUTO unless marked)

Typing at human speed: 90-260 ms between characters, small random pauses. **One** login attempt per account per day;
never a loop.

1. Open TikTok in the space. First-run screens: interests → **Skip**; swipe-up tutorial → swipe; notification
   permission → **Don't allow**.
2. **Profile** tab → **Log in** → "Use phone / email / username" → tab **Email / Username**.
3. Type the email (or username) → Continue → type the password → **Log in**.
4. Possible screens:
   - "Verify it's you" with a code sent to email → the robot asks for the code (§8.3), types it.
   - "Save login info?" / "Sync contacts" / notifications → **Not now / Don't allow**.
   - **Challenge → stop and ping** (§5.3).
5. Check: the Profile tab shows a handle; the robot reports it (ClipMaker has empty handles today).
6. Scroll the For You feed for 3-5 minutes, watch-only (a new device that only logs in and leaves looks odd).

### 5.3 Instagram login

1. Open Instagram → **Log in** (or "I already have an account").
2. Type username/email → password → **Log in**.
3. Possible screens:
   - "Check your email" / "Enter the 6-digit code" → code from Gmail, typed.
   - "We detected an unusual login attempt" → only the **"send code to email"** option is taken automatically.
   - "Save your login info?" → **Not now**; notifications, contacts, add phone → **Skip / Not now**.
4. Check the profile shows the expected account; scroll Reels/feed 3-5 minutes, watch-only.

### 5.4 What counts as a challenge (the robot stops and pings you)

| The robot handles it | The robot stops, pings Telegram, waits |
|---|---|
| 6-digit code to the brand's email | any CAPTCHA (slider, puzzle, rotate, "Confirm you're human") |
| "Save login", notifications, contacts, interests, tutorials | phone/SMS code (no SIM: you can't receive it anyway) |
| "Not now" offers | selfie / video / ID check |
| | "incorrect password" (the saved password is wrong: fix it in Chameleon) |
| | "too many attempts", "suspicious activity", account disabled/suspended |
| | any screen the robot doesn't recognise for 60 s |

The ping: a Telegram message with a screenshot and two buttons, **Done** and **Give up**. You solve it on the phone
(or in scrcpy on the laptop) and press Done (~30 s). No answer in 15 minutes → the job stops safely; nothing is
retried until the next day.

### 5.5 Moving the brands' existing accounts in (a "new device" login)

**Facts:** every current account was created in a Chameleon browser (`onboard_maker`), so the phone is a new
device for all of them. The rule "never change an account's IP" stays: each space uses the same proxy as that
account's Chameleon profile, so **only the device changes, not the IP**.

**Opinion, risk:** a new-device login often brings an email code (handled) and sometimes a CAPTCHA or a selfie
check (ping). Doing it right is a one-time cost per account. The safest order:

1. **A throwaway account** (new brand, born on a US IP in Chameleon, warmed like the others). Proves the robot.
2. **The account with the least to lose and no flags**, logged in **outside** the posting window at a normal US
   daytime hour, one day before its first robot post; 3-5 min watch-only after login.
3. One account per day, with a week of watching before the next brand.
4. **Never move an account inside a calm** (Timmy's Instagram is in its 7-day calm until about 2026-11-19), or
   one that was recently flagged.
5. **G2G's TikTok last, or never:** it changes country *and* device. Opinion: keep it hand-posted or replace it.

---

## 6. Question 4: posting

### 6.1 Getting the video into the space's gallery (step 1 must prove one)

**Fact:** the shell can't list user 10's storage while it is stopped. Three ways, tried in this order in step 1:

1. Space running → `adb push clip.mp4 /storage/emulated/N/DCIM/Robot/` → ask the media scanner to index it.
2. `adb push` to `/data/local/tmp/`, then `content insert --user N --uri content://media/external/video/media`
   (with `relative_path` and a "pending" flag), `content write` to fill it, then clear "pending".
3. Last resort: a share intent into the app.

The file gets a fresh name and today's time, so it is the newest video.

### 6.2 How the robot finds buttons

- uiautomator2 reads the screen as a tree of elements with **resource-id**, **text** and **description**.
- TikTok's resource-ids are scrambled and change with versions (e.g. `...:id/lxd`), so the robot looks for
  **text/description first** ("Post", "Next", "Upload", "Add sound"), then a resource-id learned for this app
  version, then a picture-match on a screenshot.
- Each screen has a **signature** (a few texts that must be there). Every step waits for the next signature (up
  to 30-60 s; a slow phone is fine), never a fixed sleep.
- Taps land on a random point inside the button; short random waits between steps.
- **uiautomator2 is attached only while it must read the screen.** The 3-5 minute scroll uses plain
  `input swipe` taps, so nothing extra is "watching" the app most of the time. **Opinion** (from the earlier plan:
  a reading tool may show apps "an accessibility client is active").
- **Unverified (step 1, test #1):** that uiautomator2 can read the screen of a secondary user. Fallback: plain
  screenshots + text recognition on the laptop, and `input tap` (taps work for whatever is on screen).

### 6.3 TikTok post flow

| # | Screen | What the robot does | Found by | On failure |
|---|---|---|---|---|
| 0 | — | Preflight: phone online, battery ≥ 30 %, temp < 42 °C, space opened, leak check passed, app version known | adb | hand back (before Post) |
| 1 | Home feed | Open TikTok; close pop-ups from a known list | "For You"/"Following" tabs | restart app once, then hand back |
| 2 | Create | Tap **+** | desc "Create" / centre bottom button | hand back |
| 3 | Camera | Tap **Upload** | text/desc "Upload" | hand back |
| 4 | Gallery | **Videos** tab → first tile. **Check its length label equals the clip's length** (wrong video = never posted) | tile with duration | hand back |
| 5 | Editor | **Next** (or the sound step, §6.6) | "Next" | hand back |
| 6 | Post screen | Paste the caption text (pasting is what you do by hand too; ClipMaker's Telegram tells you to copy it), then **type** each hashtag and pick it from TikTok's list (`phone_posts.split_tags`; pasted TikTok tags don't link) | hint "Add description" | hand back |
| 7 | Post screen | Check "Everyone can view"; location: none | text | hand back |
| 8 | Post screen | **Write "Post pressed" to the job journal on disk, then tap Post once** | "Post" | from here: never tap Post again |
| 9 | Feed/profile | Wait for "posted" (progress gone, up to 5 min) | progress overlay | "unsure" (see below) |
| 10 | Profile | Open the newest video → Share → **Copy link**; read it by pasting into TikTok's own search box and reading that field | Share sheet | fallback: ClipMaker reads the newest post URL from the account's Chameleon browser; last: Telegram asks you for the link only |
| 11 | Feed | Engage 3-5 min (configurable): watch most videos 60-100 %, uneven swipes, sometimes re-watch; **likes off by default** (watch-mostly), no follows, no comments | `input swipe` | ignore errors |
| 12 | — | Home, close the space, report | — | — |

Every step logs one line (`data/logs/<date>.log`, no secrets) and takes a screenshot only on failure
(`data/shots/`, git-ignored: they show account names).

**Never press Post twice:**
- Before the tap the journal says `post_pressed=true` (written to disk first).
- If anything goes wrong after that, the outcome is **"unsure"**. The robot then *looks* (newest post on the
  profile, same length, made after the press time) and reports its link if found. If it can't tell, ClipMaker asks
  you only for the link. The post is never handed to you as "please post this", so it can't be posted twice.

### 6.4 Instagram Reel flow

1. Open Instagram → home (signature "Home"/"Reels").
2. **+** (desc "New post"/"Create") → bottom tab **REEL**.
3. Gallery → newest video, **length check** → **Next**.
4. Editor: sound step (§6.6) → **Next**.
5. "Write a caption…" → paste the caption (Instagram links pasted hashtags; ClipMaker already keeps 5).
6. Journal "Share pressed" → **Share** once.
7. Wait for "Your reel has been shared".
8. Profile → Reels tab → newest → **⋯ / Share → Copy link** → read it the same way (paste into the search box).
9. Engage 3-5 min, watch-mostly. Instagram is the stricter one for engagement (your 2026-11-12 checkpoints came
   from follows/likes), so likes stay off.

**Before the first Reel** (Warming Guide): profile photo, bio, and at least one Story. The robot checks the profile
and, at first, asks you on Telegram if one is missing. Posting the Story automatically (a still from the clip) is
a later step.

### 6.5 The link and the 24-hour views

- The link goes back to ClipMaker, which runs `phone_posts.mark_posted` (same checks as a pasted link: right
  platform, right account).
- **24 h views:** a short "views" job (2-3 min, any hour, not only the posting window): open the profile, read the
  view count on the post's tile (TikTok "▷ 1,234", Instagram Reels tab play count), scroll 1-2 minutes, leave.
  ClipMaker runs `phone_posts.set_views`. The robot never guesses: an unreadable number → you are asked on
  Telegram, as today.

### 6.6 The trending-sound step

The guide: TikTok "a sound trending in the last 7 days"; Instagram "trending audio from the Reels tab".

- TikTok editor → **Add sound** → the list's trending/suggested section → pick one of the top few (random) →
  **Volume**: original sound high, added sound ~5-10 %.
- Instagram editor → **Audio** → **Trending** (↗) → pick → mix volume the same way.
- **Opinion:** this is the most fragile step (lists change daily, search screens differ by version). If it fails,
  the robot posts **without** an added sound and says so in its report, unless you set `sound_required: true`
  (then it hands the post back before pressing Post). Built after the plain post works (step 6).

---

## 7. The space lifecycle and the real ceiling

### 7.1 Lifecycle

```
account states:  waiting ──> assigned(space) ──> logging_in ──> ready ──> posting(1..10) ──> graduated ──> released
                    │                │                │
                    └── needs_you ◄──┴── challenge ◄──┘     blocked (wrong password, disabled): stays out of the queue

space states:    free ──> building ──> ready(brand) ──> wiping ──> free
                                │
                                └──> broken (leak check or setup failed: you're told, nothing posts from it)
```

- **Queue:** ClipMaker adds a brand (its TikTok + Instagram accounts) when you opt the brand in. RobotApp keeps the
  queue in its own `data/robot.db`.
- **Assign:** when a space is free, the oldest waiting brand gets it. Setup + login run **outside** the posting
  window (opinion: US daytime, 12-5 PM New York = 00:00-05:00 your time; the robot is light, it can run beside the
  night shift).
- **Graduate:** ClipMaker decides: the account has 10 posted rows and its next post would be automatic
  (`campaign_posts.post_mode` → `auto`), and the 10th post's 24 h views are in. A space is released when **both**
  of its accounts graduated.
- **Wipe and reuse:** §4.6, then the next waiting brand.

### 7.2 Phone time per evening (opinion, to be measured in step 1)

| Part of one post | Minutes |
|---|---|
| Wake phone, open the space, VPN up | 1 |
| Leak check | 0.5-1 |
| Copy the video in | 0.5 |
| Open app → upload → sound → caption → Post | 3-5 |
| Upload finishes, link read | 1-2 |
| Engage | 3-5 |
| Leave, close the space | 0.5 |
| **Total** | **~10-15** |

ClipMaker already waits **30 minutes** after a post before the next account's post goes out (`ACCOUNT_GAP`,
2026-11-16). So posts are ~35-40 minutes apart.

The window: TikTok 6-10 PM New York (4 h), Instagram 6-9 PM (3 h) = **06:00-10:00 your time** (05:00-09:00 in US
summer time, March to early November).

**Ceiling: about 6-7 posts per evening on one phone** (fewer if many are Instagram, which must fit in 3 hours).

| Spaces | Accounts warming at once (TT + IG each) | Posts per evening needed | Fits? |
|---|---|---|---|
| 2 | 4 | 4 | yes, ~2.5 h |
| 3 | 6 | 6 | just; Instagram ones first |

An account needs at least 10 posting days (1 post per day), realistically ~11-14 days with the 24-hour views waits.
So one space turns over about **twice a month**: 2 spaces ≈ 4 brands/month, 3 spaces ≈ 6 brands/month,
**only if TikTok can graduate** (next point).

### 7.3 The TikTok catch (fact + options)

**Fact:** `campaign_posts.SUPPORTED` has no TikTok, so `post_mode` keeps TikTok on `phone` after 10 posts too
(decisions.md 2026-11-10: "TikTok has no uploader yet, so it stays on the phone until one exists").

Options:
- **A (recommended, opinion):** ClipMaker gets a TikTok laptop uploader (TikTok has a web upload page; ClipMaker
  would drive it in the account's Chameleon browser, like YouTube/Instagram today). Then adding `"tiktok"` to
  `SUPPORTED` is enough. A separate ClipMaker task, not RobotApp.
- **B:** TikTok accounts keep their space forever → at most 2-3 brands on the robot, ever.
- **C:** Spaces hold TikTok only long-term and Instagram cycles in the remaining one. Breaks "one brand per space".

### 7.4 Who else could use RobotApp later (opinion)

- **AIShorts** (`..\AIShorts`): its fully AI-made Shorts need the same "first 10 from the phone" for new TikTok and
  Instagram accounts. It would call the same CLI (§8.2) with its own accounts.
- A "phone warmup" job: the same spaces could do light scroll-only sessions in the days before an account's first
  post, so the phone isn't brand new on post day.

---

## 8. Question 5: ClipMaker integration and the API

### 8.1 Shape (opinion): a CLI that speaks JSON, like `onboard_maker`

RobotApp is a Python package with one command, `robot`. ClipMaker starts it as a background process and reads
JSON lines from it, the same pattern ClipMaker already uses with the Electron app (`email_flow/stdio_protocol.py`).
Why not a server: one phone, one job at a time, no extra service to keep alive. A lock file stops two jobs.

RobotApp keeps its own state (`data/robot.db`: spaces, accounts, jobs, journal) and a `data/status.json` that
says what the phone is doing right now.

### 8.2 Commands

| Command | Input | Output |
|---|---|---|
| `robot doctor` | — | phone online?, battery, temp, users used/max, free spaces, app versions |
| `robot accounts add` | JSON: brand key, brand name, `chameleon_proxy_id`, accounts `[{platform, profile_id, email_account_id, handle?}]` | queued |
| `robot accounts list` | — | each brand: state, space, handle(s) |
| `robot setup-next` | — | events; takes the next waiting brand into a free space, sets it up, logs in |
| `robot post` | job JSON (below) | events, then one `done` |
| `robot views` | profile id + post URL | events, then `done` with views |
| `robot release` | brand key | logs out, wipes the space |
| `robot status` | job id | the final result of a job (after ClipMaker restarted mid-job) |

**No secrets ever cross this API.** Callers pass Chameleon ids; RobotApp fetches the secrets itself, at the moment
of typing (§5.1).

Post job:
```json
{"proto": 1, "job_id": "<upload id>", "profile_id": "...", "platform": "tiktok",
 "video": "C:/.../out/x.mp4", "length_s": 41.2,
 "caption": "Timmy's squad feeds him to the zombies", "hashtags": ["#timmy", "#zombies"],
 "sound": "trending", "sound_required": false, "engage_minutes": [3, 5],
 "must_finish_by": "2026-11-18T03:00:00Z"}
```

Events (one JSON object per line on stdout):
```json
{"t": "step", "job": "...", "n": 4, "of": 12, "name": "pick_video"}
{"t": "needs", "job": "...", "kind": "email_code", "platform": "tiktok", "email_account_id": "...", "sender": "tiktok", "since": "<ISO>"}
{"t": "needs", "job": "...", "kind": "human", "why": "TikTok shows a slider CAPTCHA", "screenshot": "data/shots/...png", "wait_s": 900}
{"t": "done", "job": "...", "outcome": "posted", "url": "https://www.tiktok.com/@.../video/...", "handle": "...", "sound": "name or null", "engaged_s": 242}
{"t": "done", "job": "...", "outcome": "failed_before_post", "reason": "VPN down", "screenshot": "..."}
{"t": "done", "job": "...", "outcome": "unsure_after_post", "reason": "link not readable"}
```
Answers (one JSON line on stdin): `{"t": "answer", "kind": "email_code", "code": "123456"}`,
`{"t": "answer", "kind": "human", "done": true}`, `{"t": "abort"}`.

If stdin closes (ClipMaker restarted): before Post → stop cleanly as `failed_before_post`; after Post → finish
reading the link, write the result; ClipMaker picks it up with `robot status`.

### 8.3 Who does what for codes and pings

- **Email codes:** ClipMaker answers `needs: email_code` with its existing `GmailInboxReader` (the same
  `open_gmail` path `onboard_maker.py` uses: start the Gmail profile in Chameleon, search `from:tiktok`, take the
  newest code). One Gmail reader in one place.
- **Human pings:** ClipMaker sends them with its existing Telegram bot (`tools/approve.py`; "don't add a second
  bot"), with Done / Give up buttons, and passes the tap back.
- AIShorts would answer the same two `needs` with its own code (or reuse ClipMaker's helpers).

### 8.4 ClipMaker changes (other sessions own these files; agree first)

| Where | Change |
|---|---|
| new `tools/phone_robot.py` | the adapter: `eligible(row)`, `start(row)` (spawns `robot post`), event loop in a thread, answers `needs`, maps `done` to ClipMaker |
| `tools/approve.py` `phone_tick` | one branch before `send_phone_post`: if `CLIPMAKER_PHONE_ROBOT=1`, the brand is opted in, RobotApp says its account is `ready`, `robot doctor` is OK and no robot job is running → `phone_posts.claim(row)` → start the robot job. Otherwise → Telegram exactly as today |
| outcomes | `posted` → `phone_posts.mark_posted(url)` (Content Rewards submit follows as today). `failed_before_post` → `phone_posts.unclaim` and the normal Telegram post with the reason ("robot: VPN down"). `unsure_after_post` → row stays claimed; Telegram asks only for the link |
| views | `phone_posts.views_due` rows of robot accounts → `robot views` → `set_views` |
| graduation | after `set_views`, if the account reached 10 and `post_mode` is now `auto` → `robot release` (when both accounts of the brand are done) |
| Phone mode (`tools/phone_mode.py` `snapshot`) and `phone_posts.why_waiting` | one line: "the robot is posting this now (step 4 of 12)", read from RobotApp's `status.json` |
| config | `.env`: `CLIPMAKER_PHONE_ROBOT=0` (default off), `ROBOTAPP_DIR=C:\Users\child\PROJECTS\RobotApp`; per-brand opt-in in `data/phone_robot.json` (`{"brands": {"<brand id>": true}}`), so no database migration is needed |
| handles | the robot reports each handle after login; ClipMaker stores it (`warmup_profiles.account_handle` is empty today; whoever owns `warmup_db.py` decides how) |

Hand posting stays exactly as it is: same queue, same one-post-at-a-time slot, same Telegram text. A brand that
isn't opted in never touches the robot.

### 8.5 Tests with a fake phone

- **RobotApp:** a `FakePhone` with the same interface as the real one: it returns saved screen dumps (XML) per
  screen, records taps and typed text, and can be told to fail at any step. Scenarios: happy path; CAPTCHA →
  `needs: human`; crash after Post → `unsure_after_post` (and no second Post tap); wrong video length → fails before
  Post; VPN down → fails before Post; link unreadable; stdin closed mid-job; a password never appears in logs or
  events (a test greps every output for the fake password).
- **ClipMaker:** a stub `robot` script that prints scripted events. `phone_tick` routes an opted-in post to it and
  a non-opted one to the (faked) Telegram; each outcome maps to the right `phone_posts` call. Runs inside
  `tests/run_offline.py`. No real phone, no real Telegram.

---

## 9. Question 6: Wi-Fi adb that survives

| Problem | Fact | Plan |
|---|---|---|
| Reboot loses adb over Wi-Fi | `service.adb.tcp.port=5555` is not persistent; setting the persistent one needs root | Use Android 11+ **Wireless debugging** (TLS, paired once, §4.1). The **Keeper** helper turns it on at boot (`adb_wifi_enabled=1`, allowed by a one-time `pm grant ... WRITE_SECURE_SETTINGS`). The laptop finds the phone by mDNS (`adb mdns services`), whatever its port. **Unverified:** that XOS lets this work; a Shizuku release claims the same trick works without root ([release note](https://newreleases.io/project/github/thedjchi/Shizuku/release/v13.6.0.r1117-thedjchi)), the official Shizuku manual says non-root needs a manual start after each reboot ([manual](https://shizuku.rikka.app/guide/setup/)) |
| Your screen lock after a reboot | Fact: user 0 has a PIN/pattern; until it's entered once after a reboot, normal apps don't start | Keeper is built to run before unlock ("direct boot"). If XOS doesn't connect Wi-Fi before unlock: **HANDS** once per reboot, unlock the phone (10 s). Reboots are rare (no updates) |
| IP address changes | home router hands out addresses | mDNS finds it anyway; optional HANDS: reserve 192.168.1.8 for the phone in the router (5 min, once) |
| A VPN blocking the laptop | Opinion: a space's lockdown only covers that space's apps; adb belongs to the owner user, so it's unaffected. **Never put lockdown on user 0** | step 1 checks adb stays up with a space's lockdown on |
| Phone asleep / XOS kills helpers | stay-awake is on (7); Keeper and SFA on the battery allow-list | `robot doctor` before every job |
| Cable is flaky | — | Cable is only a fallback: when a USB phone shows up, the laptop re-enables Wi-Fi debugging from it (`adb -d tcpip 5555`) and goes back to Wi-Fi |
| Phone offline in the window | — | Laptop watchdog every minute; posts simply go to Telegram (hand posting); one "phone offline" message per evening, not one per post |
| Heat | 40.5 °C while charging with the screen on | The robot turns the screen off between jobs, pauses at > 43 °C. Opinion: charge only around the window if you ever get a smart plug |

---

## 10. Question 7: later, for 10+ accounts (trade-offs only)

| Option | Gains | Costs / risks (opinion) |
|---|---|---|
| **Temporary root via a kernel exploit** (the phone's patch is 2023-06; public exploits for that age exist for some chips) | could set the persistent adb port, read/patch app data, more users | running exploit code from the internet on a phone you use; may crash or brick; lost on reboot; root is something apps look for. Not worth it now |
| **ID spoofing** (fake model, serial, Android ID) | each space looks like a different phone | needs root or hooking (Xposed/LSPosed) — the same "hook" family you ruled out; platforms look for it; a broken spoof is worse than a real phone |
| **Raise the user limit** (`fw.max_users`) | more spaces | needs root (system property) |
| **More phones** (you said no buying now) | each phone = 2-4 more spaces + another evening "lane" + truly separate hardware | money; a new budget phone ~Rp 2.5 juta, less used (earlier plan §6) |
| **Cloud phones** (GeeLark, DuoPlus, VMOS) | many "phones" | monthly cost; data-centre phones are a known farm pattern (earlier plan §6) |

**Opinion:** if the robot works and you want more, a second cheap real phone is the cleanest step.

---

## 11. Question 8: build steps (each one useful on its own)

Prerequisites outside RobotApp (other sessions):
- **P1. Chameleon:** a bearer-token route for the platform password (§5.1). Small, ~1 session. Without it the robot
  can't log in.
- **P2. Your answers** in §13.
- P3 (only for TikTok recycling): ClipMaker TikTok laptop uploader (§7.3). Big, separate.

| Step | What | Done when | Effort (guess) |
|---|---|---|---|
| **1. One account, end to end** | Repo skeleton, `robot doctor`, Keeper not yet. Create **one** space (learns the real user limit), apps, permissions, time zone, SFA + config, always-on + lockdown (both ways), leak check, **video into the space** (§6.1), uiautomator2 in a secondary user, login of the **throwaway** account with its code from Gmail (a temporary hand-run code reader), **one TikTok post** with a plain CLI (no ClipMaker), link read, 3 min engagement. You watch in scrcpy; kill switch = turn Wi-Fi off on the phone | one real post on the throwaway, 0 HANDS except watching; timings measured | 2-3 sessions |
| 2. Wi-Fi adb survives reboots | Keeper app, Wireless debugging pairing, mDNS reconnect, watchdog, cable fallback | phone rebooted → robot reconnects alone | 1 session |
| 3. Safety rails + fake phone | journal ("never press Post twice"), outcomes, screen signatures, FakePhone tests, password-leak test | test suite green | 1 session |
| 4. ClipMaker wiring | §8.4 behind `CLIPMAKER_PHONE_ROBOT` (off by default) + per-brand opt-in; `needs` answered (Gmail code, Telegram ping); Phone mode status line | an opted-in post goes out by robot; any failure lands in Telegram as today | 1-2 sessions |
| 5. Instagram | §6.4 + login §5.3 | one Reel by the robot | 1-2 sessions |
| 6. Sound + views + engagement polish | §6.5, §6.6 | 24 h views read; trending sound added (or cleanly skipped) | 1-2 sessions |
| 7. Space lifecycle | queue, assign, setup-next, graduate, wipe, reuse (§7.1) | a graduated brand frees its space and the next brand moves in alone | 1-2 sessions |
| 8. Move real accounts in | one per day, safest first (§5.5) | each account posting by robot for a week, clean | your time: a look per day |

Total: about 9-13 build sessions, one at a time (they touch the same files). Each should be a **fresh session**
with this file as its brief.

---

## 12. Risks

| Risk | Likelihood (opinion) | What we do |
|---|---|---|
| **The Warming Guide forbids it.** Its DO NOT list: "Use bots, automation tools, or scheduling apps for first 10 posts" | certain, by its letter | your decision; throwaway first; the robot keeps what platforms can see (a real app on a real phone) |
| Platform detects automation → shadowban/ban | unknown, moderate | human-like timing, watch-mostly, uiautomator2 only attached when needed, best accounts last |
| **A SIM still in the phone** tells TikTok "Indonesia" | certain if the check is right | take it out; the leak check refuses to post while a SIM is loaded |
| Wrong IP for an account | low | lockdown per space; leak check every session; stop on mismatch |
| All accounts on one phone get linked (same hardware) | some | separate users (separate Android IDs); same as hand posting today; never move a flagged account in |
| TikTok `trill` (Asia build) on a US account looks odd | unknown | your decision (§13 Q6); switching means getting the US build (Play in a US region, or a signed APK) |
| New-device login challenges | likely once per account | email code automatic; the rest pings you; one attempt per day |
| App update changes a screen | high over months | auto-update off; weekly planned update + a dry run up to (not including) Post |
| Double post | very low | journal before Post, look-don't-repeat |
| Robot posts the wrong video | very low | length check on the gallery tile |
| Phone offline / rebooted | medium | Keeper + watchdog; posts fall back to Telegram |
| Password leaks into logs/screenshots | low | fetched at typing time only; redaction; a test greps all output |
| TikTok never graduates → spaces stay full | certain until P3 | build the TikTok laptop uploader, or accept 2-3 brands |
| Battery heat/swelling | low but real | screen off between jobs; pause above 43 °C; look at the phone now and then |
| Your own phone use: the owner's clock shows New York time | certain | it's your second phone; say if that's a problem |

---

## 13. Open questions for you

1. **SIM:** the phone reports a working SIM in slot 1 (Indonesian). Is one still in? (Take it out before step 1.)
2. **Do you accept the "it's still an automation tool" catch** for a throwaway test? (Yes → step 1.)
3. **Ruang Ganda:** keep it (→ probably 2 spaces) or delete it (→ 3 spaces; its dual apps are deleted)?
4. **User 10 "Brand":** it now has a Google account and TikTok/Instagram from the Play Store. Delete it and let the
   robot build a clean space (recommended), or keep it?
5. **G2G:** give it the free `us-ps-1-virginia` IP (new device + new country at once), keep it hand-posted, or make
   a fresh G2G account on the US IP?
6. **TikTok package:** keep `trill` (what's installed) or switch spaces to the US build `musically`?
7. **TikTok recycling:** start a ClipMaker task for a TikTok laptop uploader (needed to free TikTok spaces)?
8. **Time zone:** OK to set the whole phone to New York time?
9. **Engagement length:** 3-5 minutes after each post as briefed (the earlier plan said ~10)? Likes off?
10. **Proxies for new brands:** OK to buy one Proxy-Seller IP per new brand (~$3/month each)?
11. Which phone do you hand-post from today? (User 0 on this phone has 3 Instagram logins; if brand accounts are
    already logged in here, the "new device" step is smaller for them.)

---

## 14. Repo layout (planned, nothing built)

```
RobotApp/
  PLAN.md               this file
  robotapp/             Python package (adb + uiautomator2)
    phone.py            the Phone interface (real over adb, FakePhone for tests)
    spaces.py           create / start / wipe users
    vpn.py              sing-box config, import, always-on, lockdown
    leakcheck.py
    secrets.py          Chameleon daemon client (bearer token; secrets in memory only)
    login/              tiktok.py, instagram.py
    post/               tiktok.py, instagram.py, sound.py
    engage.py
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
  `campaign_posts.py`, `email_flow/mail_reader.py`, `onboard_maker.py`, `docs/decisions.md`,
  `docs/handoff-phone-posts.md`, `data/warmup.db` (read-only).
- CustomBrowser: `app/src/main/my-accounts.ts`, `app/src/main/platform-passwords.ts`, `app/src/main/secret-vault.ts`,
  `app/src/main/data-dir.ts`, `app/src/daemon/api.ts`, `~/ChameleonData/custombrowser.db` (read-only).
- Android: [ANDROID_ID is per app-signing key, user and device](https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID);
  [VPN guide (one VPN per user, consent dialog)](https://developer.android.com/develop/connectivity/vpn);
  [Always-on VPN per user (Google help)](https://support.google.com/work/android/answer/9213914);
  [AOSP multi-user testing (`pm create-user`)](https://source.android.com/docs/devices/admin/multi-user-testing);
  [always-on settings stored per user (framework commit)](https://gitlab.e.foundation/e/os/android_frameworks_base/-/commit/17e6183b85ba3038acb935aaa01415058b2e6ddd);
  [VPN dialogs / ACTIVATE_VPN app-op](https://sysapps.bayton.org/packages/com.android.vpndialogs);
  [`pm grant CONTROL_VPN` doesn't work (Stack Overflow copy)](https://kaweah.freedombox.rocks/kiwix/stackoverflow.com_en_all_2023-11/questions/67980851/grant-android-vpn-permission-via-command-line-using-adb).
- sing-box: [Android client](https://sing-box.sagernet.org/clients/android/);
  [import-remote-profile link](https://sing-box.sagernet.org/clients/general/).
- Shizuku: [official manual](https://shizuku.rikka.app/guide/setup/);
  [non-root start-on-boot fork release](https://newreleases.io/project/github/thedjchi/Shizuku/release/v13.6.0.r1117-thedjchi).
- uiautomator2: [github.com/openatx/uiautomator2](https://github.com/openatx/uiautomator2).
- Phone facts: adb read-only output, 2026-11-17 (§2).
