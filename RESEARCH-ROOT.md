# Research: would root ever be worth it for RobotApp?

Written: **2026-11-18**, late evening WIB. By the builder, at the operator's request.

**What this is:** research only, so a future decision can be made with facts. It is **not** approval to root
anything, and nothing here was run. No exploit was executed, no phone setting was touched for this document.

**Read-by date warning:** Play Integrity, app-side detection and kernel-exploit details go **stale fast** — Google
ships server-side changes with no notice, TikTok/Instagram update their apps every two weeks, and exploit code
rots with every patch. Anything in §2 and §4 should be re-checked before it is trusted for a real decision; treat
this file as a snapshot of 2026-11-18.

**The phone this is about (facts):** Infinix **X6815D** = Infinix Zero 5G 2023, MediaTek Dimensity-class SoC with
an **Arm Mali-G68 MC4** GPU (Valhall family)
([devicespecifications](https://www.devicespecifications.com/en/model/f7465bd3),
[GSMArena](https://www.gsmarena.com/infinix_zero_5g_2023-11976.php) — note the two disagree on Dimensity 920 vs
1080; the GPU is the part that matters here and both agree on it). Android 13, security patch **2023-06-05**,
bootloader **locked**, not rooted (PLAN.md §2, read from the phone by adb). No SIM. Four Android users total
including the owner; the plan uses one Android user ("space") per brand, a US proxy per brand via sing-box, and
human-like timing. Scale: **3–5 of the operator's own accounts now, up to ~10 later.** This is not a bot farm.

**How to read this file** (same convention as PLAN.md):

- **Fact** — checked against a linked source today.
- **Opinion** — my judgement.
- **Widely claimed** — repeated by many people, no primary source; treat as marketing or folklore until proven.
- **Unknown** — I could not verify it, and neither could the sources I found.

---

## Words, explained once

- **Root**: letting a program on the phone act as the administrator ("superuser"). Android blocks this by design;
  root is gained by modifying the boot process or by exploiting a bug.
- **Bootloader**: the tiny program that starts the phone and verifies the operating system before loading it.
  **Unlocking** it removes that verification so other software can be flashed. Unlocking **wipes the phone** on
  essentially all modern devices, and the phone remembers it was unlocked.
- **Magisk**: the standard rooting tool. It patches the boot image so it can change things without touching the
  system partition ("systemless"). Modules plug into it.
- **Zygisk**: a Magisk feature that injects code into every app as it starts, so modules can change app behaviour
  from inside. Useful, but injection is also a thing apps can detect.
- **LSPosed / Xposed**: a framework that runs modules which rewrite other apps' code at runtime (for example, to
  fake what an app reads about the device). LSPosed runs on top of Zygisk.
- **Play Integrity** (replacing SafetyNet): Google's server-side verdict about a device, served to any app that
  asks. Labels explained in §2.1.
- **Attestation**: cryptographic proof, anchored in the phone's hardware, that the software it runs is genuine.
  Hardware-backed attestation is what makes tampering hard to lie about on Android 13+.
- **Widevine**: Google's DRM system on every Android phone. It has levels; **L1** uses hardware protection and
  ships a per-device certificate (an identity signal). Known casualty of unlocking bootloaders (§3.2).
- **ANDROID_ID**: a per-user, per-app-signing-key random identifier Android generates — already different in each
  of our spaces ([Settings.Secure docs](https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID)).
- **LPE (local privilege escalation)**: a bug that lets a normal app break into kernel/admin powers without the
  owner flashing anything. "Soft root" via an LPE dies at reboot.
- **Space**: one Android user on the phone, one per brand (PLAN.md §1).

---

## 1. Do they ban for root?

### TikTok

- **Fact:** TikTok's Android app runs its own device-intelligence and anti-fraud stack, separate from anything
  Google provides. Reverse-engineering toolkits document the shape of it: a **`device_register`** call to TikTok's
  servers that submits a device identity (`device_id`, install id `iid`, `openudid`, `cdid`) and is signed with
  obfuscated headers ([tiktok-android-signing toolkit README](https://github.com/code-root/tiktok-android-signing-toolkit) —
  note: the author sells an automation product, so treat details as vendor-adjacent; the endpoint's existence and
  shape match other public captures).
- **Fact:** TikTok's own error codes (same source) include `1105` = CAPTCHA and `7` = rate limit "different device /
  proxy / timing". In other words: **TikTok's response to distrust is challenges and throttling, not an instant
  account kill.** That matches what the Warming-Guide flow in PLAN.md already expects (CAPTCHAs, code checks).
- **Fact:** I found **no published policy, statement, or credible write-up showing TikTok hard-blocks or bans an
  account merely because the device is rooted.**
- **Widely claimed (unverified):** rooted phones get "flagged faster", see more CAPTCHAs, get their content
  shadow-limited. Plausible — root is a cheap risk signal — but nobody outside TikTok has published evidence of
  *what* it costs.
- **Opinion:** for TikTok, root is best read as **one risk signal among many**, not a hard block. The signals that
  get accounts limited, per everything public, are behavioral and network-level first (§2.4).

### Instagram / Meta

- **Fact:** Meta's public help pages describe "checkpoint"-style locks (identity re-checks at login) as a response
  to *suspicious activity* generally
  ([Facebook help on feature blocks](https://www.facebook.com/help/116393198446749/?query=Checkpoint%20Block),
  [Instagram login errors](https://www.facebook.com/fb-answers/instagram-login-error-messages-explained/));
  neither page mentions root.
- **Widely claimed (unverified, vendor-flavoured):** anti-detect vendors (e.g. GPM Login's marketing:
  [checkpoint causes](https://gpmloginapp.com/en/blog/facebook-checkpoint-causes-how-to-fix)) say Meta's locks fire
  on **duplicate device fingerprints and shared IPs across accounts** — which is marketing for their product, but
  it aligns with what Meta's own pages say the system looks for: activity patterns, not the boot chain.
- **Fact (contrast):** apps that DO hard-block root exist — Microsoft Authenticator officially refuses to
  authenticate on rooted/jailbroken devices
  ([Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5959018/how-to-fix-a-rooted-authenticator-app)),
  and many banking apps do the same via Play Integrity. So hard root-blocking is a real pattern — I found no
  evidence Meta's consumer apps follow it.
- **Unknown:** whether Instagram's app even calls Play Integrity. No public statement either way.

**Bottom line (opinion):** for these two platforms, root by itself is not a documented ban trigger; it is at most a
distrust signal sitting next to much louder signals (IP, device fingerprint reuse, behaviour). The cost side — root
makes the phone look *tampered with* to any app that checks — is fully documented (§2, §4). That asymmetry drives
the recommendation at the end.

---

## 2. How they detect, concretely

### 2.1 Play Integrity (Google's verdict, served to any app that asks)

**Fact** ([Integrity verdicts, developer.android.com](https://developer.android.com/google/play/integrity/verdicts)):

| Label | Meaning |
|---|---|
| `MEETS_BASIC_INTEGRITY` | Passes minimal checks. **"The device bootloader can be locked or unlocked"** — rootable phones can still get this. On Android 13+ it only requires an attestation root of trust provided by Google. |
| `MEETS_DEVICE_INTEGRITY` | "Genuine and certified" device; on Android 13+ there is **hardware-backed proof that the bootloader is locked** and the OS is a certified manufacturer image. A rooted phone with unlocked bootloader fails this. |
| `MEETS_STRONG_INTEGRITY` | `MEETS_DEVICE` **plus** security updates for all partitions within the last year. **Our phone fails this today** on its 2023-06 patch, rooted or not. |
| (empty) | "Signs of attack (such as API hooking) or system compromise (such as being rooted)", or a non-passing emulator. |

Also in the same doc, two verdicts that matter to *this project, rooted or not*:

- **App Access Risk** (opt-in by the app): reports `KNOWN_/UNKNOWN_` `INSTALLED`, `CAPTURING`, `CONTROLLING`,
  `OVERLAYS` — running apps that can view the screen, control input, or draw overlays. uiautomator2's helper app
  is installed via adb, not Play: while it is attached, it would count as `UNKNOWN_CONTROLLING` to any app that
  opted in. **Opinion:** RobotApp already minimises this (uiautomator2 attached only while it must read the
  screen, §6.2 of PLAN.md), which is the right mitigation, root or no root.
- **Recent device activity** (opt-in): how many integrity tokens the device requested in the last hour — an
  anti-hyperactivity check aimed at farms and attackers.

**What a 2023-patch locked phone passes:** Fact: `MEETS_DEVICE_INTEGRITY` is earned simply by staying stock and
locked (which is the state today). `MEETS_STRONG` needs newer patches; we do not have them; almost no app requires
STRONG for social media. **Unknown:** whether TikTok/Instagram call Play Integrity at all, and if so which labels
they require — the labels only matter to an app that actually checks them.

### 2.2 Root / Magisk / Zygisk detection (what apps look for)

Everything in this subsection is **widely claimed, with strong mechanism-level agreement across sources** — the
individual checks are documented in open-source root-detection libraries and Magisk's own docs; no platform has
published which ones it uses.

- **`su` binary and known paths**: looking for superuser binaries in the usual places. Trivial to do, trivial for
  Magisk to hide (it renames/mounts over them).
- **Known package names**: package lists are readable by any app (`PackageManager`). Magisk manager, KernelSU
  manager, LSPosed, root-apps — all visible unless hidden (Magisk can randomise its own package name).
- **Mount/namespace oddness**: systemless root works by overlay-mounting files; apps can list mount points or
  probe files and spot overlays that stock Android would not have.
- **Zygisk injection**: every app process carries telltale traces (loaded libraries, patched symbols) while
  Zygisk is on. Detection tools look for these; Shamiko-class modules exist to erase them —
  **Fact** that Shamiko's stated purpose is hiding "Magisk root, Zygisk itself and Zygisk modules" while reading
  Magisk's DenyList, and that it conflicts with Magisk's own "Enforce DenyList" mode
  ([Shamiko README mirror](https://github.com/rushizgithub/shamiko),
  [Magisk↔Shamiko guide](https://github.com/mModule/guide_hma/blob/master/Magisk-Shamiko.md)).
- **Properties (props)**: system properties that betray root managers or unlocked state (`ro.boot.verifiedbootstate`,
  `ro.debuggable`, Magisk's resetprop tweaks). Magisk edits these; both sides know both sides know.
- **When it runs:** all of the above is cheap, so apps can run it at install, at login, and continuously. Cost per
  check is negligible; frequency is unknown per platform.

### 2.3 Device-identity signals (how an app knows "this is the same device" after Android 10)

**Fact:** since Android 10, apps **cannot read IMEI or the serial number** — they require the privileged
`READ_PRIVILEGED_PHONE_STATE` permission, granted only to system/preinstalled apps; Wi-Fi MACs are randomised by
default ([Android 10 privacy changes](https://developer.android.com/about/versions/10/privacy/changes)). So the
old "change your IMEI" story targets an identifier most modern apps never see. What apps use instead:

- **ANDROID_ID** — per-user, per-app-signing-key, resets on factory reset
  ([docs](https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID)).
  **Each of our spaces already gets a different one without root** (this is why PLAN.md §4.8 wipes users rather
  than clearing app data).
- **Advertising ID** — per-user, user-resettable; each space has its own.
- **`Build` fingerprint / model / hardware strings** — readable by any app, **shared across all users of the
  phone.** Same model, same build, same chipset in every space. Root's only pitch here is to *fake* them.
- **Widevine DRM ID** — a per-device hardware certificate (L1). Same on every user; changes or degrades with
  unlocked bootloaders (§3.2). Any app can request a DRM session and read the device ID from the certificate.
- **Sensor/GPU/media fingerprints** — clock skew, gyroscope noise, GPU renderer strings, camera quirks. All shared
  hardware across spaces. **Widely claimed** as a fingerprinting axis (vendor blogs push it hardest);
  mechanism is sound, weight unknown.
- **Boot/kernel signals** — verified-boot state, kernel version/patch level. Readable in part without root; fully
  trustworthy only via hardware attestation (§2.1).

**Opinion:** the plan's honest weakness is the *shared-hardware* group — one real phone means one real
fingerprint, whatever the user count. Root could fake per-space builds, but faking build strings while the
sensors, GPU and Widevine all still say "Infinix X6815D" creates a *mismatch* signal that stock phones never emit.
Mismatches are what sophisticated anti-fraud looks for; a consistent boring phone is the better cover story.

### 2.4 Network and behaviour — the signals that actually bite

- **Fact (from the plan's own sources):** PLAN.md §3.4 records the linking risk as **one IP + one phone** for two
  brands; the Targeting Guide flag quoted in §7.2 is "rapidly switch between accounts on same device".
- **Opinion, consistent with everything above:** shared IPs (especially datacenter IPs), duplicate content across
  accounts, posting cadence that no human keeps, and same-moment activity across accounts are all *observable and
  provable* from the server side. Root changes **none** of them. This is why the plan spends its effort on one
  brand per space, per-brand proxies, watch-mostly engagement and 30-minute brand gaps.
- **Fact:** the operator's accounts use **residential US proxies from Proxy-Seller**, per-brand, consistent with
  their browser profiles' IPs (PLAN.md §3.4, §5.5). That is the strongest anti-linking measure this project owns,
  and it needs no root.

---

## 3. What root actually changes — honestly

### 3.1 IMEI change

- **Fact:** modern apps can't read IMEI anyway (§2.3). Changing it buys ~nothing against TikTok/Instagram.
- **Fact (Indonesia):** the IMEI-control system is real law: devices are blocked from cellular networks unless
  their IMEI is registered
  ([Permenkominfo No. 1/2020](https://peraturan.bpk.go.id/Details/169165/permenkominfo-no-1-tahun-2020),
  [Bea Cukai IMEI registration](https://www.beacukai.go.id/imei)). A faked IMEI would be an unregistered IMEI:
  the phone would fail the national IMEI database. This phone has **no SIM** (PLAN.md §2), so nothing would break
  in practice — but tampering with IMEI in an IMEI-controlled country is a legal exposure with zero upside here.
  **Verdict: pointless and legally dirty. Off the list.**

### 3.2 Per-space device fingerprint spoofing (model, build.prop, Android ID, DRM ID via Xposed/LSPosed/Zygisk)

- **What it would do:** give each space a fake model/fingerprint so TikTok sees "a Pixel 7 in space 11, a Galaxy
  S23 in space 12". LSPosed modules of this kind exist and are **widely claimed** to work.
- **Honest cost:** (a) every platform that matters runs machine-learning over *consistency*: a "Pixel 7" whose
  Widevine certificate says Infinix, whose GPU renderer string says Mali-G68, whose sensor noise matches the other
  spaces exactly, is a **walking mismatch**. Anti-fraud vendors sell "consistency checking" as a feature; treat as
  marketing but the mechanism is obvious. (b) Zygisk/LSPosed injection is itself a detection surface (§2.2). (c)
  It needs maintenance per app version. **Opinion: highest-fragility, lowest-probability-of-helping item in the
  whole root menu.**
- **Related fact:** unlocking the bootloader — a prerequisite for Magisk-class root — commonly drops **Widevine L1
  to L3** (widely reported across devices; e.g. XDA threads on L1→L3 after unlock:
  [one](https://xdaforums.com/t/root-widevine-l1-for-neflix.4181651/), [two](https://xdaforums.com/t/fix-widevine-l3-to-l1-on-netflix-app.4731380/)).
  That changes an identity-bearing property of the phone itself, for *every* space including G2G's owner user.

### 3.3 Hiding root (Magisk DenyList, Shamiko, Zygisk)

- **Fact:** the tools exist and are maintained (§2.2). **Fact:** the author of the most-used Play Integrity
  spoofer **quit**, citing "Google is increasingly putting up more obstacles"
  ([XDA, Play Integrity Fix thread](https://xdaforums.com/t/module-play-integrity-fix.4607985/)); the ecosystem now
  runs on community forks (PlayIntegrityFork, PIF-Inject) that chase Google's server-side changes
  ([fork landscape](https://magiskguide.com/modules/play-integrity-fix/)). A fork's own docs say it: the module
  "is not made to hide root, nor to avoid detections in other apps"
  ([KernelSU module page](https://modules.kernelsu.org/en/modules/playintegrityfix/)).
- **Opinion:** this is a treadmill with maintenance every time Google or the apps move, and the reward is getting
  back to *roughly where an unrooted phone already is*. For a 3–5 account personal setup, the treadmill buys
  nothing the plan doesn't already have clean.

### 3.4 Raising the Android user limit (`fw.max_users`) for more spaces

- **Fact:** the phone allows 4 users including the owner (PLAN.md §2, `pm get-max-users`).
- **Widely claimed, unverified on this build:** on rooted phones the framework's user limit can be raised by
  editing the relevant system property/config; whether XOS tolerates it, whether `pm` and storage behave, is
  **unknown**. Even if it worked: each new brand still shares the one phone's hardware fingerprint and the two
  paid IPs (PLAN.md §3.4) — the linking math doesn't improve, only the user count does. **Opinion:** a second real
  phone (PLAN.md §10) beats 6 spaces on one rooted Infinix on every axis that matters (hardware identity, heat,
  uptime, legality, effort).

### 3.5 Persistent Wi-Fi adb

- **Fact (plan, §9):** the pain is real (adb over Wi-Fi dies at reboot) but the planned fix is **Wireless
  debugging + a tiny boot helper ("Keeper") with a one-time `pm grant`** — no root in it. Root would make this
  trivial (`service.adb.tcp.port` persistent), but it's a solved problem without it.

### 3.6 What the plan already gets WITHOUT root (the important row)

| Need | Already have without root |
|---|---|
| Different ANDROID_ID per brand | Yes — separate Android users (§2.3 fact) |
| Separate app data, accounts, galleries | Yes — spaces |
| Per-brand network identity | Yes — per-brand SOCKS5/HTTP proxies in sing-box with lockdown (§4.4–4.5) |
| Screen automation | Yes — adb + uiautomator2 (§6.2) |
| Consistent, boring device story | Yes — a stock locked phone; nothing to hide |
| Survive reboot adb | Planned without root — Keeper (§9) |

**Opinion:** root's only *new* capability for this project is fingerprint spoofing per space — §3.2 showed that's
the most fragile, most likely-to-backfire one.

---

## 4. Can it be bypassed — and how fragile

### 4.1 Play Integrity on a rooted X6815D in 2026

- **Fact:** with an unlocked bootloader, `MEETS_DEVICE_INTEGRITY` is gone by definition (hardware-backed proof of
  a locked bootloader, §2.1). Only `MEETS_BASIC` is realistically attainable, via fingerprint-spoofing forks
  (§3.3). Whether any given app cares is unknown (§2.1).
- **Fact:** the spoofing ecosystem is fork-maintained and in permanent chase (§3.3). Banking-grade apps are
  exactly the ones that keep up; social apps are unknown. **Opinion:** expect breaks measured in weeks-to-months,
  and expect each break to be invisible until something stops working.

### 4.2 Does rooting *this* phone require unlocking the bootloader?

- **Fact:** Magisk and KernelSU's normal install paths patch the boot/`init_boot` image and flash it — the
  [KernelSU installation doc](https://kernelsu.org/guide/installation) is explicit: back up your boot image,
  flashing may cause data loss, and `fastboot flash` is the mechanism (KernelSU LKM still patches and flashes; the
  old "here's a ready boot.img" GKI mode was discontinued in v3.0). A locked bootloader refuses `fastboot flash`.
  So: **permanent root on this phone ⇒ bootloader unlock ⇒ full wipe + permanent unlock flag + Widevine L1 loss
  risk (§3.2). No no-wipe persistent path exists.**
- **Infinix unlock availability for this model: Unknown.** Many Infinix/XOS models have no official unlock
  channel, which pushes people to unofficial tools of unverified provenance — a worse idea than everything else
  on this page.

### 4.3 Temporary "soft root" via a kernel exploit (the §10 idea, examined)

- **Fact:** the phone's GPU is a Mali Valhall part (§0), and the Mali driver had a use-after-free
  (**CVE-2023-4211**) affecting Valhall drivers r19p0–r42p0, fixed only in the **2023-10-05** Android bulletin —
  **after** this phone's 2023-06-05 patch. It was actively exploited in the wild
  ([Project Zero root-cause analysis](https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2023/CVE-2023-4211.html);
  CISA listed it in October 2023, per the same page). So the *bug* is almost certainly present on this phone —
  **caveat, Unknown:** Infinix may have backported the Mali fix out-of-cycle; the phone's exact Mali driver
  revision has not been read.
- **Fact:** the same Project Zero page publishes a **reproducer** (crash PoC), not a weaponised LPE; the in-the-wild
  exploit sample was not public. Building a full Android LPE from the PoC is non-trivial exploit development.
- **Fact:** the famous turnkey nf_tables LPE (**CVE-2024-1086**, patched Feb 2024 — after this phone's patch)
  targets kernels **v5.14–v6.6** with unprivileged user namespaces and deliberately crashes the kernel after use
  ([Notselwyn's exploit repo](https://github.com/Notselwyn/CVE-2024-1086)). Android 13 devices of this class ship
  5.10/5.15 kernels and Android restricts unprivileged user namespaces — **Unknown** whether any variant of this
  chain applies here; assume not without verification.
- **Opinion, flagged as such:** soft root on this phone is *plausible* (Mali UAF) but **not turnkey**, dies at
  every reboot, and every capability in §3 that matters needs the *persistent* path anyway — which is the
  bootloader-unlock path with all its costs. PLAN.md §10 already called this "run exploit code from the internet
  on a phone you use; may crash or brick; lost on reboot" — this pass agrees.

---

## 5. The realistic threat model for THIS user

What the platforms actually see from this project, rooted or not:

- 3–5 accounts, each posting **real, human-watchable clips** the operator made, on a schedule a hobbyist could
  keep, with watch-time engagement per sitting.
- Each account on a **residential US proxy, alone per brand**, that it has used since creation (§2.4 fact).
- A **stock, locked, certified Android 13 phone** — the exact device class every anti-fraud system whitelists by
  default (`MEETS_DEVICE_INTEGRITY` out of the box, §2.1).
- The one real shared-hardware cluster: Speed+Timmy on one IP+phone (already accepted, §3.4 of PLAN).

Now swap in the rooted version of the same phone: unlocked flag visible to attestation, Zygisk/LSPosed injection
traces, spoofed-but-inconsistent fingerprints, Widevine possibly degraded, and a weekly maintenance treadmill to
keep DenyList/Shamiko/PIF ahead of app updates — all to *hide* what the unrooted phone never shows. Every root
capability in §3 makes the device look **more** like the thing anti-fraud profiles for, not less.

**Opinion:** root would move the needle only if (a) the farm grew past what one honest phone can carry (>
3 US brands), **and** (b) per-brand hardware separation was proven to be the binding constraint (accounts falling
over *because* of device clustering, not content or IP), **and** (c) a second phone was impossible. All three at
once is the only world where root pays, and even there the cleaner answer is the second phone.

---

## 6. If root ever happened anyway — the least-risky integration (trade-offs only, no build)

Recorded so a future decision has a starting sketch. Not approval, not a plan.

- **What to spoof per space: nothing, if possible.** Keep build/model/props stock; the *least* modification that
  achieves a goal beats the most. If per-space identities were ever needed, spoof *coherently or not at all* —
  model, props and behaviour must agree (§3.2's mismatch point), and accept that Widevine/sensors still tell the
  truth.
- **What to leave real:** bootloader-state reporting (can't be faked at the hardware anyway on 13+), per-user
  ANDROID_ID (already separate), the owner user (G2G) untouched by any module — a module that breaks user 0 breaks
  the operator's own phone.
- **Verify before trusting a space:** a Play Integrity check per space before its first login/post (an integrity
  probe app or a test call), recorded in `robot doctor` output; a space that stops passing gets benched, not
  posted from.
- **Kill-switch/rollback:** the original boot image kept on the laptop; Magisk/KernelSU's own "restore stock
  image" path (KernelSU documents its backup/restore flow, §4.2 source); the decision pre-made that a broken
  space means *fall back to the laptop path for that brand*, not heroics.
- **Detecting "we've been flagged" early:** the plan's existing signals (24 h views, first-post checks,
  CAPTCHA/needs ping rates) are exactly the right tripwires; root adds one more — any PIF/DenyList break counts as
  a red morning, pause posting until it's green again.
- **Opinion on order if it ever happened:** a *second stock phone* first (it solves capacity without any of the
  above), soft root never, Magisk-class root only on a *dedicated* third phone that never touches the owner user.

---

## 7. Recommendation

**Never, at this scale. Root later only in the narrow case: more than 3 US brands, device-clustering proven as the
binding constraint, and a second phone ruled out. Until then, the strongest move is the one already planned: keep
the phone stock and locked, one brand per space, per-brand residential proxies, human-like timing, and buy a second
cheap real phone when the spaces run out (PLAN.md §10 — the ~Rp 2.5 juta buys hardware identity separation, which
root cannot).**

### The capability table

| Root capability | Benefit for this project | Risk / fragility | Already handled without root? |
|---|---|---|---|
| IMEI change | ~zero (apps can't read it; §3.1) | Legal exposure under Indonesia's IMEI control; unregistered IMEI | N/A — no SIM, no benefit |
| Per-space fingerprint spoofing (build/model/ID) | Marginal (hides shared hardware) | High: mismatch signals, injection detection, per-app-version maintenance, Widevine L1 loss risk (§3.2) | Partly: ANDROID_ID + ad ID already per-space; hardware stays shared (accepted) |
| Hide root (DenyList/Shamiko/PIF) | Gets back to *unrooted* | Treadmill; fork-maintained; author of main tool quit (§3.3) | Yes — nothing to hide today |
| Raise user limit (`fw.max_users`) | More spaces on one phone | Unknown on XOS; doesn't fix IP/hardware linking (§3.4) | 3 spaces fit today (§3.1 PLAN) |
| Persistent Wi-Fi adb | Convenience | Trivial with root, but already solved: Keeper + Wireless debugging (§3.5) | Yes — planned, no root |
| Soft root via LPE | Nothing persistent | Crash/brick risk, dies at reboot, non-turnkey (§4.3) | — |
| Anything Magisk-class | The above | Bootloader unlock: full wipe, permanent flag, attestation loss (§4.2) | — |

---

## Sources

Primary (docs, advisories, exploit write-ups):

- Play Integrity verdicts, Android Developers — <https://developer.android.com/google/play/integrity/verdicts>
- Android 10 privacy changes (IMEI/serial restrictions) — <https://developer.android.com/about/versions/10/privacy/changes>
- `Settings.Secure.ANDROID_ID` (per-user, per-signing-key) — <https://developer.android.com/reference/android/provider/Settings.Secure#ANDROID_ID>
- Project Zero, CVE-2023-4211 Mali UAF root-cause analysis (in-the-wild; fixed in 2023-10-05 SPL) —
  <https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2023/CVE-2023-4211.html>
- Notselwyn, CVE-2024-1086 nf_tables LPE (kernels v5.14–v6.6, Feb 2024 patch, deliberate crash) —
  <https://github.com/Notselwyn/CVE-2024-1086>
- KernelSU installation guide (LKM patch+flash, GKI mode discontinued, backup/restore) —
  <https://kernelsu.org/guide/installation>
- Magisk developer guides (modules, Zygisk, boot scripts) — <https://topjohnwu.github.io/Magisk/guides.html>
- Project's own measured phone facts — PLAN.md §2 (adb, read-only, 2026-11-17/18)
- Infinix Zero 5G 2023 (X6815D) specs, Mali-G68 MC4 —
  <https://www.devicespecifications.com/en/model/f7465bd3>, <https://www.gsmarena.com/infinix_zero_5g_2023-11976.php>
- Indonesia IMEI control: Permenkominfo 1/2020 — <https://peraturan.bpk.go.id/Details/169165/permenkominfo-no-1-tahun-2020>;
  Bea Cukai IMEI registration — <https://www.beacukai.go.id/imei>

Secondary (named as such; vendors/marketing where applicable):

- TikTok Android signing/device-registration toolkit (vendor product; documents `device_register`, IDs, error
  codes) — <https://github.com/code-root/tiktok-android-signing-toolkit>
- Play Integrity Fix: original author's discontinuation note — <https://xdaforums.com/t/module-play-integrity-fix.4607985/>;
  fork landscape — <https://magiskguide.com/modules/play-integrity-fix/>;
  module's own scope disclaimer — <https://modules.kernelsu.org/en/modules/playintegrityfix/>
- Shamiko (hide root/Zygisk; DenyList enforcement conflict) — <https://github.com/rushizgithub/shamiko>,
  <https://github.com/mModule/guide_hma/blob/master/Magisk-Shamiko.md>
- Widevine L1→L3 after bootloader unlock (user reports, XDA) —
  <https://xdaforums.com/t/root-widevine-l1-for-neflix.4181651/>,
  <https://xdaforums.com/t/fix-widevine-l3-to-l1-on-netflix-app.4731380/>
- Microsoft Authenticator root hard-block (contrast case, official) —
  <https://learn.microsoft.com/en-us/answers/questions/5959018/how-to-fix-a-rooted-authenticator-app>
- Meta help pages on blocks/login errors —
  <https://www.facebook.com/help/116393198446749/?query=Checkpoint%20Block>,
  <https://www.facebook.com/fb-answers/instagram-login-error-messages-explained/>
- GPM Login on Facebook checkpoints (anti-detect vendor; marketing — read as such) —
  <https://gpmloginapp.com/en/blog/facebook-checkpoint-causes-how-to-fix>
