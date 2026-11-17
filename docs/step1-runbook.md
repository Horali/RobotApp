# Step 1 runbook — the real phone, inside 06:00-10:00 WIB

Everything runs from `C:\Users\child\PROJECTS\RobotApp` with `.\.venv\Scripts\python.exe`.
The robot refuses to touch the phone outside the window; `robot window` says where you stand.

## 0. Before 06:00

Nothing. The robot sends no phone commands before 06:00 (the guard is in every adb call).

## 1. Is the phone there? (06:00)

```powershell
$adb = "C:\Users\child\AppData\Local\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.1.8:5555
& $adb devices
.\.venv\Scripts\python.exe -m robotapp.cli doctor
```

- `device` and a green doctor → continue.
- `cannot connect` → the phone rebooted and Wi-Fi adb is gone: plug the USB cable, `& $adb tcpip 5555`,
  then `& $adb connect 192.168.1.8:5555`. (Step 2's Keeper app fixes this for good.)

## 2. Clean the phone and build one US space

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli provision `
  --clean `
  --space-name "US 1" `
  --sfa-apk data\apk\sfa-1.14.4.apk `
  --sfa-sha256 32250a4b5f3a6733df57a3b9ec16c38d2c7fc5f2f693a9636f8f7b3be3549641 `
  --proxy-id 7d8a1a48-e530-474b-8ba3-632dbf879ff9
```

What it does, in order: uninstall the auto-clicker from the owner user; delete users 10 and 999; turn automatic
time zone detection off; install SFA (certificate checked); create "US 1" (or reuse it on a re-run); install the
apps that already exist on the phone; grant the media permissions (never location or contacts); write the
sing-box profile from the Virginia proxy and open its import link; set always-on + lockdown; switch into the
space; run the leak check.

Watch for:
- `pm remove-user 999` may be refused → HANDS: Settings → Ruang Ganda / Dual apps → remove.
- The leak check needs the SFA profile imported **and started**. If `vpn.up` is false, open SFA in the space and
  press its start button once (HANDS, 10 s), then re-run the leak check with `robot screen`/`doctor`.
- `--expected-ip` can be filled after the first good reading, so later runs notice a changed exit.

## 3. Prove uiautomator2 in the space

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli screen --shot --limit 25
```

It prints what uiautomator2 sees in the space. The first connect installs its two helper APKs (30-60 s).

## 4. The real post: G2G's queued TikTok clip (owner user)

The sitting JSON is already built from ClipMaker's queue row (`data/g2g-sitting.json`, clip length 61.6 s):

```powershell
.\.venv\Scripts\python.exe -m robotapp.cli sitting --file data\g2g-sitting.json --dry-run   # first, if unsure
.\.venv\Scripts\python.exe -m robotapp.cli sitting --file data\g2g-sitting.json
```

- The dry run walks the whole flow and stops at the Post button.
- The robot writes `post_pressed` to `data/robot.db` **before** the tap; if anything goes wrong after it, the
  outcome is `unsure_after_post` and the Post button is not touched again.
- Then: the link is read, 3-5 min of watch-only engagement, and the phone goes back to the owner user.

## 5. Record the post in ClipMaker

```powershell
.\.venv\Scripts\python.exe data\mark_posted.py ad6b19b920214d55a312eeb7b0ca1587 "<the link>"
```

(Step 4 replaces this with ClipMaker's own `tools/phone_robot.py`.)

## 6. Leave the phone as other scripts expect

Owner user in front, no space open, time zone Asia/Jakarta, lock released — the CLI does the lock and the switch
back by itself.

## Notes

- TikTok's US build (`musically`) is not on the phone yet: the US space is ready except for it.
- The first real login (any brand) also needs Chameleon restarted, so the platform-password route exists.
- `data/apk/sfa-1.14.4.apk` is git-ignored; download it again from F-Droid (`io.nekohasekai.sfa_746.apk`) if the
  folder is gone.
