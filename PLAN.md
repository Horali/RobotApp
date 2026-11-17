# RobotApp: the phone robot (build plan)

Status: **plan only, nothing built.** First written 2026-11-17; updated 2026-11-18 with the user's answers to
§13, YouTube Shorts from the phone, and a new capacity plan. Ask the user before any code.

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
| Owner user (user 0) | G2GChannel Clips (Indonesian test brand) | TikTok `trill` (already there), YouTube | home Wi-Fi, **no proxy, no VPN, ever** | permanent |
| US space 1-3 (new users) | the US brands, one per space | TikTok US build `musically`, Instagram, YouTube | `us-ps-2-newyork` through a locked VPN | while the brand posts by phone |

Ruang Ganda (999) and the old "Brand" user (10) get deleted first, which leaves room for **exactly 3 US spaces**
(the phone allows 4 users including the owner).

**What it does each day:** up to **11 posts** with today's accounts (3 US brands × TikTok + Instagram + YouTube,
plus G2G's TikTok + YouTube). **12 if G2G gets an Instagram account** (it has none today). Timetable in §7.2.
**After your corrections, phone time is no longer the limit; the number of spaces (3) is.**

**What you still do:** about 10-15 minutes once (§4.1). Per new account: 0 HANDS, except a Telegram ping for a
CAPTCHA or an unusual check (~30 s), and possibly a few minutes the first time each brand's **Google** account
signs in on the phone (Google's checks are stricter, §5.6).

**Things to know (the honest part):**
1. **YouTube's ~0 views are more likely the channels and the clips than the laptop** (§8.7). Only 4 Shorts were
   ever posted, all 2-3 days old, from brand-new channels. Test before switching (§8.8).
2. **YouTube and TikTok on the phone for good means spaces stop recycling.** A US brand then holds its space
   forever → at most 3 US brands on this phone. Recycling only helps brands that leave the phone after 10 posts.
3. **G2G in your owner user needs two changes there:** the auto-clicker accessibility service off, and the owner's
   screen lock (PIN/pattern) removed, or the robot can't unlock the phone for G2G (§3.3).
4. **All US brands on one IP + one phone** is a real linking risk (§3.4).
5. **The robot can't read TikTok/Instagram passwords yet** (Chameleon keeps them in its main process). A small
   Chameleon change is needed (§5.1).
6. **Wi-Fi adb dies on every reboot.** Fix: Android's "Wireless debugging" + a tiny boot helper (§9).
7. The Warming Guide's DO NOT list says "Use bots, automation tools, or scheduling apps for first 10 posts". You
   accepted this risk; the plan still starts with a throwaway account.

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
lockdown on user 0** (it would also cut your own apps and adb). Re-checking the earlier concerns:

| Concern | Risk for G2G (opinion) | What to do |
|---|---|---|
| **Auto-clicker accessibility service** (`com.rise.automatic.autoclicker.clicker`) | **High.** Any app can list the enabled accessibility services (a public Android API); an auto-clicker next to TikTok is a classic bot signal | **Turn it off** (Settings → Accessibility → the auto-clicker → off), or uninstall it if you don't use it. HANDS 30 s, or AUTO with your OK |
| **Owner screen lock** (PIN/pattern is set) | Blocks the robot: G2G sessions need the owner user unlocked, and the robot must not hold your phone PIN | **Set the owner's screen lock to None or Swipe** (HANDS 1 min). Catch: anyone holding the phone opens your 17 Google accounts; the phone stays at home. It also makes Wi-Fi adb after a reboot simpler (§9) |
| 17 personal Google accounts, 3 Instagram logins | Low to medium. Since Android 8 an app can't list other apps' accounts without you picking them. But Google sees every account on a device: **G2G's Google/YouTube account will be linked to your personal ones** | Accept for a test brand. The robot never taps "Continue with Google"/one-tap offers in TikTok; it logs in with email + password |
| Your own TikTok in the same `trill` app (if you use one there) | Two accounts in one TikTok install = one device ID for both | The robot uses TikTok's account switcher and checks the handle before posting. Tell me if your personal TikTok is logged in there (§13) |
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

**Your decision:** only `us-ps-2-newyork` for now; all US brands share it.

**Linking risk (opinion):** one IP alone looks like a household. One IP **plus** one phone **plus** one Wi-Fi
behind it, for 3 brands × 3 platforms = 9 accounts, looks like one person running a network of accounts. If
one account gets banned for spam, platforms may look at accounts that share its IP and device (anti-detect
vendors call these "chain bans"; not verified). Separate Android users give each space its own app IDs, which
helps, but the IP and hardware stay shared.

**When a second IP becomes worth it (opinion):**
- when the **third US brand** joins (more than ~6 accounts on one IP);
- right away after **any** account on the IP is disabled or banned (move the healthy brands, never the flagged one);
- note: `us-ps-1-virginia` is already paid (auto-renew on, decisions.md 2026-11-10) and idle, so using it costs
  nothing extra. Rule stays: an account never changes IP, so a new IP is for a **new** brand.

Also: add G2G's missing email logins with Chameleon's **Edit** button in Show accounts; check Speed Instagram's
email has a Gmail profile.

---

## 4. Question 2: zero-touch setup

### 4.1 One-time phone setup

| # | Step | Who | Time |
|---|---|---|---|
| 1 | ~~SIM out~~ done (2026-11-18: `ABSENT,ABSENT`) | — | — |
| 2 | Owner user: turn off the auto-clicker accessibility service; set the screen lock to None/Swipe (§3.3) | HANDS | 2 min |
| 3 | **Wireless debugging** on and paired once: Developer options → Wireless debugging → on → "Always allow on this network" → "Pair device with pairing code"; the laptop runs `adb pair` with the code you read out | HANDS + AUTO | 2 min |
| 4 | Install RobotApp's tiny boot helper ("Keeper", our own app from this repo) in the owner and let it turn Wireless debugging back on after a reboot (`pm grant ... WRITE_SECURE_SETTINGS`) | AUTO | — |
| 5 | Automatic time zone off (`cmd time_zone_detector set_auto_detection_enabled false` and `set_geo_detection_enabled false`), so only the robot sets it (§4.6) | AUTO | — |
| 6 | Delete user 10 "Brand" and Ruang Ganda 999 (§3.1) | AUTO, maybe HANDS | 0-1 min |
| 7 | Proxy app sing-box "SFA" (§4.4) installed once: Play Store in the owner, or the official GitHub release APK | HANDS 1 min or AUTO (your OK to download) | — |
| 8 | Play Store (owner): auto-update off for TikTok, Instagram, YouTube. The robot updates on purpose once a week and re-tests its screens | HANDS | 1 min |
| 9 | XOS battery manager (Phone Master): let SFA and Keeper run in the background if XOS asks; the robot also adds them to Android's battery allow-list | AUTO, maybe HANDS | 0-2 min |
| 10 | TikTok US build `musically` onto the phone (§4.7) | AUTO (needs a US Google Play account or your OK for a download) | — |

Total HANDS: about 6-10 minutes, once.

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

Time per space (opinion): 3-5 minutes unattended, plus the Google sign-in (§5.6).

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
1. Switch only **twice a day**, not per sitting: New York just before the first US sitting (~03:25 your time),
   Jakarta right after the last US sitting (~07:45). G2G's evening sitting then needs no switch.
2. Before switching to New York: **force-stop G2G's TikTok and YouTube** in the owner (`am force-stop --user 0
   <pkg>`). A force-stopped app gets no broadcasts and no push until it is opened again, so it never sees New
   York. (YouTube is also your personal YouTube app; it just restarts when you open it.)
3. Never switch while a space app is open; check with `getprop persist.sys.timezone` and the clock after.
4. The network clock stays automatic (only the zone changes, the real time is always right).
5. If a sitting is retried late, the robot re-checks the zone before opening any space.

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
2. **A signed download** (e.g. APKMirror's bundle), only with your OK: the robot checks the signing certificate
   matches TikTok's before installing (`apksigner verify --print-certs`), installs with `adb install-multiple`.
   Catch: the installer then shows as adb, not Play (a small oddity; not known to matter).
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

G2G (owner): the same, inside `trill`'s account switcher if another TikTok account is already there.

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
(for an SMS code that reached your own phone). You solve it on the phone or in scrcpy (~30 s). No answer in 15 min
→ the job stops safely; nothing is retried until the next day. At night (the YouTube sittings, §7.2) nobody
answers, so a challenge there just waits for the morning.

### 5.5 Moving the brands' accounts onto the robot phone (every login is a new-device login)

**Fact (your answer):** you hand-post everything from your Samsung S25+. Every account was created in a Chameleon
browser. So **the Infinix is a new device for every account**, TikTok, Instagram and Google alike.

What keeps the risk down (opinion):
- **Only the device changes, never the IP:** each US space uses `us-ps-2-newyork`, the same IP the accounts'
  Chameleon profiles use; G2G uses the home Indonesian line, like its Chameleon profile.
- **Log in outside the posting window**, at a normal daytime hour for the account's country, **one day before**
  its first robot post; 3-5 min watch-only after login.
- **One new login per day**, at most. A week of watching after the first brand before the next.
- **After the robot takes an account, stop using it on the S25+** (log out there). One phone per account looks
  more normal than an account bouncing between two phones and two networks every evening. (Your S25+ likely
  posts through a different app/IP setup; mixing both is the bigger risk.)
- Never move an account inside a calm or after a fresh flag.

The safest order:
1. **Throwaway account** (a new US test brand, made in Chameleon on `us-ps-2-newyork`, warmed like the others).
   One week.
2. **Speed's TikTok**, then **Timmy's TikTok** (no flags, few posts so far).
3. **Instagrams** after their calm ends and their first Story is up (Timmy's calm ends ~2026-11-19; Speed's
   Instagram is a replacement account, keep it gentle).
4. **Google/YouTube** sign-ins last, one brand first, only for the YouTube test (§8.8).
5. **G2G** in the owner whenever you like: its IP country doesn't change, so it's the lowest-risk move.

### 5.6 Signing in the brand's Google account in a space (for YouTube)

Flow (AUTO): Settings → Passwords & accounts → Add account → Google (or YouTube → Sign in, which opens the same
Google screens) → email → Next → password → Next → possible checks → "I agree" to Google's terms → Google
services screen: **Backup off, Location off** → done. Then YouTube → avatar → check the **channel** is the
brand's (a Gmail can own several channels; pick by name).

Google's checks are stricter than TikTok's (opinion, from how Google treats new devices):
- **"Verify it's you"** with choices. The robot takes only "get a code at <the brand's Gmail>"-type options it can
  read. A code to a **recovery email or phone** it can't read → ping you (you read it on your own phone or inbox
  and reply with the code).
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

US brand, morning sitting: **Instagram first** (its window ends an hour earlier), then **TikTok**. Each post is
followed by its own 3-5 min of watch-mostly engagement in that app (the guide: "do not just post and close the
app"). YouTube has its own sitting outside that window (§7.2). G2G: TikTok, then YouTube, in its evening sitting.

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
- 24 h views: read **at the start of the brand's next-day sitting** (sittings run at the same time daily, a few
  minutes later each day, so ≥ 24 h has passed): profile → the post's tile ("▷ 1,234" / Reels play count) →
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

Rules used (your corrections, 2026-11-18):
- **No gap between a brand's own apps** in one sitting. **30 minutes between brands** (from one brand's last post to
  the next brand's first post).
- US TikTok + Instagram in the guide's window: TikTok 6-10 PM New York, Instagram 6-9 PM. Instagram first.
- **US YouTube outside that window.** Buffer's 2026 data of Shorts says the best slots are around **4 PM, 6 PM
  and 7 PM** ([Buffer](https://buffer.com/resources/best-time-to-post-on-youtube/?lang=en)); other sources disagree
  ([Tryordinal](https://www.tryordinal.com/blog/best-time-to-post-on-youtube-shorts): 12-3 PM and 7-10 PM). 6-7 PM
  is taken by TikTok/Instagram, so: **3:30-5:00 PM New York**.
- **G2G in an Indonesian evening window:** Indonesian guides agree most on **19:00-22:00 WIB** as prime time
  ([Dealls](https://dealls.com/pengembangan-karir/jadwal-fyp-tiktok),
  [timetopost](https://timetopost.co/best-time-to-post/tiktok/indonesia/)). Opinion: start at **19:30 WIB**.
- Durations (opinion, measured in step 1): open space + checks 2 min; one post 4-5 min + link 1 min; engage 4 min.

**Timetable, one winter day (your time, WIB; New York = WIB − 12 h):**

| WIB | New York | Phone does | Posts |
|---|---|---|---|
| 03:25 | 15:25 | time zone → New York; force-stop G2G's apps | |
| 03:30-03:43 | 15:30-15:43 | **US 1** sitting: YouTube (posted ~03:37), engage | 1 |
| 04:00-04:13 | 16:00-16:13 | **US 2**: YouTube (~04:07) | 1 |
| 04:30-04:43 | 16:30-16:43 | **US 3**: YouTube (~04:37) | 1 |
| 06:00-06:21 | 18:00-18:21 | **US 1**: yesterday's views → Instagram (~06:06) → engage → TikTok (~06:15) → engage | 2 |
| 06:39-07:00 | 18:39-19:00 | **US 2**: Instagram (~06:45) → TikTok (~06:54) | 2 |
| 07:18-07:39 | 19:18-19:39 | **US 3**: Instagram (~07:24) → TikTok (~07:33) | 2 |
| 07:45 | 19:45 | time zone → Jakarta | |
| 19:30-19:50 | 07:30-07:50 | **G2G** (owner): yesterday's views → TikTok (~19:36) → engage → YouTube (~19:46) → engage | 2 |
| | | **Total** | **11** (12 with a G2G Instagram) |

- Phone busy about **2 hours a day** (YouTube ~40 min, US evening ~65 min, G2G ~20 min); you do nothing unless
  pinged.
- In US summer time (March to early November) every US row moves **one hour earlier** in WIB.
- Slack: the TikTok/Instagram window could hold **2 more US brands** (Instagram's last start ~08:40 WIB), and the
  YouTube slot 2 more (15:00-17:30 NY). **So time is no longer the limit: spaces are (3 US).**
- If a sitting is late (a retry, a challenge), the next brand slides by the same amount; a post that would miss
  its window waits for tomorrow.
- YouTube sittings run while you sleep and during the night shift (the robot is light, no rendering). A
  challenge there waits until morning (§5.4).

**Do I agree with "no gap within a brand"? Yes (opinion), reasons:**
- The Targeting Guide's flag is "rapidly switch between accounts on same device": many accounts **on one
  platform** traded back and forth. Posting one clip to your own TikTok, Instagram and YouTube in one sitting is
  what every creator does, and each app has exactly one account in that space.
- The real gap that matters, between brands, stays.
- Small caveat: each post still gets its own 3-5 min of engagement in its app before the next app opens.

**Simpler alternative I'd consider (opinion):** put YouTube **inside** each brand's evening sitting (third, after
TikTok). 6-7 PM New York is one of Buffer's best Shorts slots too, each brand's space opens once a day instead of
twice, and 3 US brands still fit by ~08:10 WIB. Your version is fine; this one means fewer space switches and no
night sittings. Your call.

**Changes this needs in ClipMaker** (listed in §8.4): the 30-min gap per brand instead of per account
(`phone_posts.account_gap`), one sitting taking several due posts of one brand, per-brand windows (G2G Indonesian,
YouTube 3:30-5 PM New York).

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
| `phone_posts.py` | `account_gap` → **per brand** (no gap within a brand); new `due_for_brand()` (Instagram, TikTok, YouTube order); per-brand/per-platform windows (`in_window`: G2G 19:00-22:00 Asia/Jakarta; robot YouTube 15:30-17:30 New York); `check_link` accepts `youtube.com/shorts/<id>` / `youtu.be/<id>`; the first-post 24 h check (`verdict`) stays TikTok/Instagram only; `steps()` text for a YouTube hand post |
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

- **One US brand** (suggest **Timmy**: US IP, posts on all three platforms), **14 days**, one Short a day at the same
  time (~3:30 PM New York).
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
| Phone offline in a window | — | Laptop watchdog every minute; posts fall back (§8.5); one "phone offline" message per window |
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
| **1. One account, end to end** | Repo skeleton, `robot doctor`. Delete users 10 and 999; create **one** US space; `musically` onto the phone (§4.7); apps, permissions, time-zone switching, SFA + config, always-on + lockdown, leak check, **video into the space** (§6.1), uiautomator2 in a secondary user, login of the **throwaway** with its Gmail code (a hand-run code reader for now), **one TikTok post** from a plain CLI (no ClipMaker), link read, 3-5 min engagement. You watch in scrcpy; kill switch = turn the phone's Wi-Fi off | one real post on the throwaway, 0 HANDS except watching; timings measured | 2-3 sessions |
| 2. Wi-Fi adb survives reboots | Keeper, Wireless debugging pairing, mDNS reconnect, watchdog, cable fallback | phone rebooted → robot reconnects alone | 1 session |
| 3. Safety rails + fake phone | journal (never press Post twice), outcomes, screen signatures, FakePhone tests, password-leak test | tests green | 1 session |
| 4. ClipMaker wiring | §8.4 behind `CLIPMAKER_PHONE_ROBOT` (off) + per-brand opt-in; sittings, per-brand gap and windows; `needs` answered; Phone mode line | an opted-in brand's sitting posts by robot; any failure lands in Telegram as today | 1-2 sessions |
| 5. Instagram | §6.5 + login §5.3 | one Reel by the robot | 1-2 sessions |
| 6. YouTube | Google sign-in (§5.6), Shorts flow (§6.7), the "YouTube by phone" switch (§8.6), then **the 14-day test** (§8.8) | one Short by the robot; test running | 1-2 sessions + 2 weeks |
| 7. G2G in the owner | owner checks (§3.3), `trill` account switching, Indonesian window, no-VPN check | G2G's TikTok and YouTube posted by robot in its evening sitting | 1 session |
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
| **9 US accounts on one IP + one phone get linked** | medium | separate users; second IP at the 3rd US brand or after any ban (§3.4) |
| **Auto-clicker seen next to G2G's TikTok** | high if left on | turn it off (§3.3) |
| G2G's Google linked to your personal Google accounts | certain | accepted for a test brand |
| Daily time-zone flips seen by G2G's apps | low | flip twice a day, force-stop G2G's apps first (§4.6) |
| Google sign-in checks in spaces | likely once per brand | codes via you; one attempt per day |
| New-device logins (every account) | likely once per account | same IP as before; one per day; stop using the S25+ for robot accounts |
| `musically` can't come from Play (no US Play account) | medium | a signed download with your OK (§4.7) |
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
10. Proxies: only `us-ps-2-newyork` for now.
11. You hand-post from the S25+: every robot login is a new-device login.
12. New: YouTube Shorts from the phone, per brand; capacity rules of §7.2.

Still open:
1. **Owner user:** OK to turn off (or uninstall) the auto-clicker, and to set the owner's screen lock to None/Swipe?
2. **G2G's logins:** which Gmail owns G2G's YouTube channel and TikTok? (Chameleon has no email assigned to them.)
   Is your personal TikTok logged in to `trill` on this phone?
3. **G2G Instagram:** make one? (11 → 12 posts a day.)
4. **Brand Gmails' recovery email/phone:** where do Google's "verify it's you" codes go? (Decides how often you're
   pinged for Google sign-ins.)
5. **YouTube timing:** keep YouTube in its own 3:30-5 PM New York sitting (your choice), or fold it into the evening
   sitting (fewer switches, §7.2)?
6. **YouTube test brand:** Timmy?
7. **`us-ps-1-virginia`:** it's paid and idle; use it for the third US brand?
8. **Downloads:** if Play can't give `musically`, OK to download a signed copy (APKMirror) after a certificate check?
9. **After a robot takes an account:** OK to log it out of your S25+?

---

## 14. Repo layout (planned, nothing built)

```
RobotApp/
  PLAN.md               this file
  robotapp/             Python package (adb + uiautomator2)
    phone.py            the Phone interface (real over adb, FakePhone for tests)
    spaces.py           create / start / wipe users; owner-user rules
    timezone.py         switch + verify, force-stop rules
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
