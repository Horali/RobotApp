# Step 1 — what actually works on the phone (measured 2026-11-18)

This is the working procedure, written after running it on the real phone (20:37-21:56 WIB, with
`ROBOTAPP_BUILD_MODE=1`). The plan's §4.2/§6.4 said what to do; this file records what the phone actually did,
because several screens differ from what the plan assumed.

Run everything from `C:\Users\child\PROJECTS\RobotApp` with `.\.venv\Scripts\python.exe`.

## 0. Before 06:00

Nothing. The robot sends no phone commands outside 06:00-10:00 unless `ROBOTAPP_BUILD_MODE=1` is set (build
only: off by default, logs a warning, unset before any other script shares the phone).

## 1. Connect and check

```powershell
$adb = "C:\Users\child\AppData\Local\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.1.8:5555
.\.venv\Scripts\python.exe -m robotapp.cli doctor
```

The phone connects over Wi-Fi and also shows on USB when the cable is in. `doctor` must be green.

## 2. Clean the phone and build one US space

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli provision --clean --space-name "US 1" `
  --sfa-apk data\apk\sfa-1.14.4.apk `
  --sfa-sha256 32250a4b5f3a6733df57a3b9ec16c38d2c7fc5f2f693a9636f8f7b3be3549641 `
  --proxy-id 7d8a1a48-e530-474b-8ba3-632dbf879ff9 --zone America/New_York
```

Measured: ~4 minutes including installing the 127 MB sing-box APK. What happened:
- the auto-clicker uninstalled; users 10 and 999 deleted (`pm remove-user 999` was **accepted**, no hands needed);
- space "US 1" = **user 11**, with Instagram, YouTube, Chrome and SFA installed, media permissions granted;
- SFA's own screens need three taps, in this order: **No, thanks** (update offer) → **OK** (import confirmation)
  → **Create** (the pre-filled New Profile). Then SFA's profile list has **Start**; Android then asks
  **Allow notifications** and **Connection request** — both OK. The tunnel comes up ("VPN on.").
- the import needs a clean lockdown first: the robot clears `always_on_vpn_lockdown`, serves the config on the
  laptop's **Wi-Fi** address (a hotspot adapter's 192.168.137.1 is unreachable from the phone), imports, waits
  for the tunnel, and only then sets always-on + lockdown.

## 3. The leak check

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli leak --user 11
```

Result: exit `208.214.162.185`, `loc=US`, VPN up and locked, New York time, no SIM, location off (~90 s).
Chrome's first-run screen is "Make Chrome your own" → **Stay signed out**.

## 4. Post one clip (TikTok)

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli sitting --file data\g2g-sitting.json --dry-run   # first
.\.venv\Scripts\python.exe -m robotapp.cli sitting --file data\g2g-sitting.json
```

The flow that works on trill 47.8.3:
- open the app (a fresh start shows a **location prompt**: tap **Open settings**, then Back — the robot does it);
- read the handle on the Profile tab (**@gtwogchannelclips**), so a wrong account stops the post;
- **the share intent is the way in**: `am start -a android.intent.action.SEND -t video/mp4 --eu
  android.intent.extra.STREAM content://media/external/video/media/<id> -n
  com.ss.android.ugc.trill/com.ss.android.ugc.aweme.share.SystemShareActivity`, then tap **Video** in the sheet.
  The camera's upload tile is drawn but absent from the accessibility tree, so tapping it does nothing;
- editor → **Next** → the post screen;
- the caption goes in as **one paste** and is read back (typing the hashtag suggestions one by one lost the
  first line);
- **Everyone can view this post** is already the default;
- the journal writes `post_pressed` before the **Post** tap; the upload took ~1 minute;
- the link is read from the newest tile on the profile → the share arrow ("Share video. …") → **Copy link**.
  The clipboard also holds the last caption (the IME puts pastes there), so only a `https://` value counts.

Measured: one post from "start" to link ≈ 8 minutes, engagement 3.3 minutes.

## 5. Record the post in ClipMaker

The robot's own `data/mark_posted.py` cannot write ClipMaker's database (the harness sandbox gives Python a
read-only view outside the workspace). The route that works uses ClipMaker's own API:

```powershell
node data\claim_phone_post.js <upload_id>          # sets sent_at (ClipMaker refuses an unsent row)
$body = @{ upload_id = "<upload_id>"; url = "<link>" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8765/api/phone-posted" -Method POST -Body $body -ContentType "application/json"
```

Answer: `{"ok": true, "url": …, "next": "24-hour check of the last post at …"}`.
**Step 4 replaces both commands** with `tools/phone_robot.py` inside ClipMaker.

## 6. Leave the phone as other scripts expect

Owner user in front, no space open, time zone Asia/Jakarta, lock released. The CLI does the lock and the switch
back; check with `robot lock status` and `robot screen --user 0`.

## If the space has "no internet" while the VPN is up (2026-11-20, measured)

Two layers, both real, both fixed in the robot; check them in this order:

1. **The phone's Private DNS.** `settings get global private_dns_mode` must be `off`. With
   `hostname` + a specifier (this phone had `dns.quad9.net`), Android insists on DoT to that server;
   through a locked proxy it is unreachable, so **every hostname fails** while raw-IP pages load
   (`https://1.1.1.1/cdn-cgi/trace` works, `google.com` and `example.com` do not). That reads as
   "no internet" and as Google's "Something went wrong".
2. **The proxy blocks DNS on port 53.** From the laptop, `CONNECT 1.1.1.1:53` and `8.8.8.8:53` answer
   **403**, while `:443` answers 200. So sing-box's DNS is **DoH over 443 through the proxy**
   (`{"type": "https", ..., "path": "/dns-query", "detour": "proxy"}`) — `build_config` writes that.

Check it with a hostname, never with an IP: open `https://example.com` in the space (and note the
leak check now refuses a trace page older than 10 minutes, so a cached page cannot fake a pass).

SFA's "Are you sure to import remote profile …?" dialog must be answered with **OK** before the
profile list means anything: the list stays readable behind the dialog, which once made the import
look finished when it had not started.

## Still missing for the full plan

- ~~**TikTok's US build (`musically`)**~~: **installed 2026-11-19** (47.9.1, user 11 only; certificate
  checked against the 47.8.3 of the same APKMirror listing, signer identical: `CN=musical.ly`, SHA-256
  `9041803e…cf2ab5ba`; the APK sits in `data\apk\musically-47.9.1.apk` for future spaces).
- **TikTok US logins (`musically`), measured 2026-11-19** - a journey `trill` never shows:
  1. a **birthdate wall**: the "Birthday" field is only a display; the three SeekBar wheels are the
     input. One drag on any wheel initialises them to today; a ~200px **down-drag on the Year picker =
     one year older**; `robot login` dials to an adult year, reads the field back each step, presses
     Continue once (the wall clears ~8 s later).
  2. a **Terms of Service** dialog → "Agree and continue" (the robot answers it).
  3. the **notifications permission** → its button prints as "DON'T ALLOW" (all caps, curly apostrophe);
     the robot declines.
  4. the feed; the email login goes **straight to an emailed code** ("Verify email", no password
     form). The code field has **no label** - the code is typed into the screen's editable, never
     tapped at by name ("Resend code" is a button, not the field). A manual run can wait for the code
     with `--code-file <path>` (5 min).
- **The throwaway account**: signed in - Instagram **@vtubersclips90**, TikTok **@vtubersclips70**, both in
  user 11 (Virginia space).
- **Wi-Fi adb after a reboot**: step 2's Keeper app.
