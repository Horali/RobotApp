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

## Still missing for the full plan

- **TikTok's US build (`musically`)**: not on the phone. The US space is ready except for it.
- **The throwaway account**: does not exist; the login path is built and unit-tested but has not run on a real
  account. Chameleon must be restarted once for the platform-password route.
- **Wi-Fi adb after a reboot**: step 2's Keeper app.
