# Research: temporary, no-wipe root on the locked X6815D

Written: **2026-11-19** (research pass finished just after midnight WIB). By the builder, at the operator's
request.

**What this is:** research only. It informs a possible future decision and is **not** approval to root anything.
No exploit was run, nothing was flashed, no phone setting was changed. The only phone contact was **read-only
adb** (`getprop`, `uname`, `cat /proc/version`, `zcat /proc/config.gz`, `getenforce`) plus the GitHub/web research
below. Every "phone fact" in this file was read from the phone in this session, on 2026-11-18 ~23:52–00:10 WIB.

**Why this is a separate document:** [RESEARCH-ROOT.md](RESEARCH-ROOT.md) (2026-11-18) examined *Magisk-class*
root, which requires unlocking the bootloader — a full wipe. The operator will not wipe this phone
(data is kept), so that whole path is dead here. This file is only about **root without unlocking and without a
wipe**: an exploit that breaks into kernel/admin powers at runtime ("soft" or **ephemeral root**), surviving until
the next reboot, re-runnable afterwards. Cross-references instead of repeats: RESEARCH-ROOT.md for the
*should-we* analysis, [PLAN.md](PLAN.md) §2 for the phone's measured facts, §9 for the Wi-Fi-adb pain, §10 for
the "later, more than 3 brands" list.

**Rot warning:** exploit availability, affected-version ranges and tool support rot in weeks. The
"what to re-check" list at the end is part of the document.

---

## 0. The phone, verified from the metal (facts, this session's adb)

| What | Value (read tonight) |
|---|---|
| Model / device | Infinix X6815D (`Infinix-X6815D`), Zero 5G 2023 |
| SoC | **MT6877V/TZA** — MediaTek Dimensity 920 family (`ro.soc.model`, `ro.board.platform=mt6877`) |
| Kernel | **Linux 4.19.191+**, built 2023-07-14, clang 11.0.1 (`/proc/version`) — **not** 5.x, see the correction below |
| `uname -r` | `4.19.191+` |
| OS / patch | Android 13 (SDK 33), security patch **2023-06-05**, build `X6815D-H777BC-T-GL-230714V199` |
| Bootloader | `ro.boot.flash.locked=1`, `ro.boot.verifiedbootstate=green`, `ro.boot.vbmeta.device_state=locked`, veritymode `enforcing` |
| SELinux | `enforcing` |
| Kernel config (via `/proc/config.gz`, readable by the shell user!) | `CONFIG_IKCONFIG=y`, **`CONFIG_XFRM=y`, `CONFIG_INET_ESP=y`, `CONFIG_INET6_ESP=y`**, `CONFIG_MODULES=y`, `CONFIG_MODULE_UNLOAD=y`, `CONFIG_KPROBES=y`, `CONFIG_NAMESPACES=y`, `CONFIG_NET_NS=y`, `CONFIG_SECURITY_SELINUX=y`; **`CONFIG_USER_NS` is not set**, **`CONFIG_MODULE_SIG` is not set** (no module-signature enforcement), and no RXRPC option appears in the config at all |

**Correction to RESEARCH-ROOT.md (supersedes its kernel guess; that file is not edited per this ticket's
scope):** RESEARCH-ROOT.md §0/§4.3 assumed a "5.10/5.15-era" kernel. The metal says **4.19.191+** — a
2018-era branch that MediaTek/Infinix carried forward into their Android 13 build. Consequences already
re-derived below: DirtyPipe (needs 5.8–5.10.1) never applied; the famous nf_tables turnkey LPE
(CVE-2024-1086, kernels 5.14–6.6) does not apply. The Mali UAF (CVE-2023-4211, Valhall drivers, fixed only in
the 2023-10 bulletins — after our patch) **stays on the table**; the exact Mali driver revision on this phone
could not be read without root (`/proc/mali/version` is not exposed). RESEARCH-ROOT's *recommendation* is
untouched by the correction: root is not worth it for this use case.

**A quirk worth knowing (fact):** `/proc/config.gz` is world-readable on this phone. That is what made the
checks above possible without root — and it means any future feasibility question about this kernel can be
answered from `zcat /proc/config.gz` alone.

---

## Words, explained once

- **Ephemeral / soft root:** gaining kernel/admin powers by exploiting a bug at runtime, with **no change to any
  disk partition**. A reboot returns the phone to fully stock. "Re-run after each reboot is fine" (operator).
- **LPE (local privilege escalation):** the bug class. Needs code running on the phone — here, an app you
  install yourself.
- **Page cache:** the kernel's in-memory copy of files. A page-cache write primitive means "change what
  everyone sees when they read a file", even files you have no permission to write.
- **XFRM / ESP:** the kernel's IPsec packet-transform code (XFRM) and its encrypted-packet format (ESP). Built
  into our kernel (table above).
- **BROM / Preloader:** the MediaTek chip's boot ROM — code burned into the SoC that talks over USB before the
  phone even boots. Tools can reach it to dump or reflash partitions.
- **SLA / DAA:** Serial-Lock Authentication / Download-Agent Authentication — MediaTek's per-vendor
  *passwords* that newer SoCs demand before the boot ROM accepts a download agent. The old Kamakiri-style
  free-for-all died years before this chip.
- **AVB (Android Verified Boot):** the locked bootloader's signature chain. `verifiedbootstate=green` +
  `veritymode=enforcing` (table above) = any modified boot/kernel image is refused at boot.
- **KMI / vermagic:** a kernel module must be built against the same kernel build (version string + config) to
  load; Android GKI ships per-KMI module binaries.

---

## 1. Is no-wipe temporary root realistically possible on THIS phone?

**Honest answer: MAYBE — one candidate path, and it is not turnkey.**

The landscape on 2026-11-19, for a **locked, AVB-green, 4.19.191+, SELinux-enforcing** Android 13 phone:

- The thing that changed the game in 2026 is the **DirtyFrag** family (CVE-2026-43284, published May 2026):
  ephemeral root *from an app*, no unlock, no custom kernel, gone at reboot. It is real, maintained, and works
  on many current phones — **but every public build targets GKI kernels 5.10 and newer, and the phone's
  kernel here is 4.19**. (Sources: DFRoot/DirtyFrag READMEs and module list, §2.1.)
- **GhostLock / CVE-2026-43499:** same idea, different bug — supported-device list is 5.10 through 6.12, no 4.19
  anywhere in it. **No** for this phone as-is. (§2.2)
- **mtkclient / BROM:** not a root path at all — it is a dump/reflash path, gated by SLA/DAA on this chip
  generation, and flashing a *modified* image is refused by AVB anyway. **No** (and never was a root path).
  (§2.4)
- **Magisk / KernelSU / APatch without an exploit:** all need a patched boot image **flashed** → unlock → wipe.
  **No.** With a working ephemeral root, KernelSU can be *loaded at runtime* — that is exactly what the
  DirtyFrag/GhostLock apps do (their "SU manager" step). So "KernelSU without unlocking" is real **only as a
  payload of a working LPE**, not as its own path.

What the MAYBE depends on, exactly:

1. **Whether 4.19.191's ESP receive path has the vulnerable in-place decrypt-into-page-cache behaviour**
   (CVE-2026-43284). Facts pointing yes: `CONFIG_XFRM=y`, `CONFIG_INET_ESP=y`, `CONFIG_INET6_ESP=y` (read
   tonight); Red Hat issued fixes for kernels as old as RHEL 8's 4.18 line
   ([Red Hat CVE entry](https://access.redhat.com/security/cve/cve-2026-43284)), so the buggy code is old enough
   to plausibly be in 4.19; and **no Infinix firmware for this phone can contain the fix**, because every known
   build (ours: 2023-07, the newer one below: 2023-09) predates the May-2026 disclosure. Fact pointing
   *unknown*: nobody has published a 4.19 test result, and the tool's own FAQ lists "accidental mitigation" as
   a real outcome on some kernels
   ([DFRoot README](https://github.com/diabl0w/DFRoot),
   [mitigation thread](https://github.com/V4bel/dirtyfrag/issues/23)).
2. **Whether the Android app-side entry works on XOS 13.** The chain enters through `IpSecManager` — a normal
   Android framework API any app can use — precisely because Android kernels like ours have **no
   `CONFIG_USER_NS`** (read tonight). That matches the tool's design (the "unprivileged XFRM socket method").
   Untested on this exact build: the app→framework→kernel flow on XOS.
3. **Whether a `dfroot.ko` module can be produced for 4.19.191+.** Good news read tonight: **module signature
   enforcement is OFF** (`CONFIG_MODULE_SIG` is not set) and `CONFIG_MODULES=y` — the stock kernel will load an
   unsigned, correctly-built module. Bad news: the eight prebuilt modules cover 5.10→6.18 GKI KMI only
   ([module directory](https://github.com/mitschud/DirtyFrag/tree/master/app/src/main/jni/ko)); a 4.19.191
   MediaTek build has to be built from the (GPL) module source against this kernel's exact build — the public
   kernel tree for this phone (§2.5) ships prebuilt binaries and headers from a *sibling firmware*, not full
   source. Feasible for someone who builds kernels; not a download.
4. **Whether the post-exploit steps behave on XOS.** The chain relies on the `crash_dump` SELinux domain
   bridging into `vendor_file`, and on `vendor_modprobe` being allowed to `insmod`. Those are AOSP-common
   mechanisms, but the tool's testing surface so far is Samsung One UI (the mitschud fork is Samsung-branded;
   upstream DFRoot is SU-manager-agnostic). **Unknown on XOS.**

Opinion: put together — a serious, still-unproven porting project for this exact phone, not an off-the-shelf
tap. The bug surface is plausibly present; the tooling is a KMI-mismatch away. "Maybe" is the honest word, and
it stays "maybe" until someone publishes a 4.19/MTK module and an XOS test.

---

## 2. Path by path

### 2.1 DirtyFrag / DFRoot — CVE-2026-43284 (the page-cache ESP bug)

**Fact base:** [diabl0w/DFRoot README](https://github.com/diabl0w/DFRoot) (upstream),
[mitschud/DirtyFrag README](https://github.com/mitschud/DirtyFrag) (Samsung-flavoured fork, read in full),
[Qualys write-up](https://blog.qualys.com/product-tech/vulnmgmt/detection-response/2026/05/09/dirty-frag-using-the-page-caches-as-an-attack-surface)
(LPE chain published 2026-05-07, combining CVE-2026-43284 xfrm-ESP and CVE-2026-43500 RxRPC),
[Red Hat CVE](https://access.redhat.com/security/cve/cve-2026-43284) (CVSS 7.8, local, low privileges,
low complexity), [Rapid7 module](https://www.rapid7.com/db/modules/exploit/linux/local/cve_2026_43284_dirty_frag/).

- **Family:** neither DirtyPipe nor Dirty Pagetable — a new page-cache corruption class via *shared socket
  fragments* in kernel networking code.
- **Mechanism (public description, no attack code):** the kernel decrypts AES-CBC ESP packets directly into the
  page cache of a file that is open for `splice()`. Crafting the ESP IV as
  `AES_ECB_DEC(key, current_content) XOR desired_content` lets the app overwrite any 16-byte-aligned block of a
  mapped shared library — no write permission needed. The Android chain targets `libc++.so`: shellcode patched
  into the kernel's page cache runs at the next privileged call, `insmod`s a kernel module, the module sets
  SELinux globally permissive and launches the SU daemon. Root achieved without touching any partition.
- **Preconditions:** ESP support in the kernel (**fact: present here**, §0); an app-side IPsec API path
  (standard `IpSecManager`); a kernel module matching the running kernel (**fact: module-signing off here,
  but no 4.19.191 module exists publicly**).
- **Bootloader:** **not needed** — that is the entire point; stock boot chain, AVB stays green.
- **Reboot:** root gone; re-run the app after reboot; the fork even ships a bootloop interlock and "reboot is
  the recovery path" design (README FAQ).
- **Brick/stability:** designed to fail soft (page-cache patches evaporate on reboot; the app disables its
  autorun after a failed run). One confirmed rough edge in the family: the RxRPC variant's public sample
  ([popsicle](https://github.com/x-spy/CVE-2026-43499-popsicle), the sibling CVE) notes apps crashing until
  reboot after a successful run — i.e. *working* runs can still leave the UI briefly unhealthy. For us the
  relevant variant is xfrm-ESP only (this kernel has no RxRPC, §0).
- **Patch status of this phone:** **unfixed** — no X6815D firmware can predate the 2026-05 disclosure; our
  build is from 2023-07. Whether 4.19's old code is *accidentally* immune is the open question (§1, item 1).

### 2.2 GhostLock — CVE-2026-43499 ("popsicle")

**Fact base:** [YuKongA/ghostlock-app README](https://github.com/YuKongA/ghostlock-app) +
[supported-devices list](https://github.com/YuKongA/ghostlock-app/blob/main/docs/kernel_profiles/SUPPORTED_DEVICES.md)
+ [MediaTek porting guide](https://github.com/YuKongA/ghostlock-app/blob/main/docs/kernel_profiles/MEDIATEK.md)
(read in full) + [x-spy/CVE-2026-43499-popsicle](https://github.com/x-spy/CVE-2026-43499-popsicle).

- **What it is:** a one-tap app that gains temporary root via CVE-2026-43499 and loads KernelSU-family
  managers. Support requires an **exact `uname -r` match** against per-kernel-build profiles.
- **The list today:** kernels from **5.10.236** (Sony) up to **6.12.x**, including recent Infinix phones
  (Note 50s / GT 30 on 6.1.145, GT 30 Pro on 6.1.157). **No 4.19 entry.** Our `4.19.191+` is not there, and the
  underlying PoC was verified on 6.12-era kernels.
- **MediaTek angle in GhostLock:** MTK devices need `kernel_phys_load`/`kernel_phys_offset` recovered from the
  stock `boot.img`/`vendor_boot.img` — obtainable from an OTA package or (with root) `/proc/iomem`. Archive.org
  hosts X6815D stock firmware ([archive entry](https://archive.org/details/infinix-zero-2023-x6815d-stock-rom-firmware)),
  so the *inputs* exist — but the exploit's target code path simply is not shipped for 4.19.
- **Verdict for this phone: NO today**; would need both a 4.19 vulnerability analysis of CVE-2026-43499 and a
  profile port. Unknown whether the 43499 bug even exists in 4.19.

### 2.3 Mali GPU UAF — CVE-2023-4211 (carried over from RESEARCH-ROOT.md §4.3)

Still the best-matched *pre-existing* kernel bug for this SoC: use-after-free in the Mali driver, fixed in the
2023-10-05 Android bulletin — **after** our 2023-06 patch; actively exploited in the wild in 2023
([Project Zero RCA](https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2023/CVE-2023-4211.html)).
The public artifact is a crash reproducer, not a weaponised LPE. **Unknown:** whether Infinix backported the
Mali fix early (driver revision unreadable without root). Compared with DirtyFrag this path is *harder* (write
your own exploit) and offers the same payoff (ephemeral root). It stays in the catalogue, not on the bench.

### 2.4 mtkclient / BROM / SLA-DAA — the MediaTek "bootrom" angle

**Fact base:** [bkerler/mtkclient](https://github.com/bkerler/mtkclient),
[mtkclient issue #199](https://github.com/bkerler/mtkclient/issues/199) (BROM reachable, SLA auth blocks on a
newer Dimensity),
[XDA MTK Auth Bypass thread](https://xdaforums.com/t/mod-dev-mediatek-mtk-auth-bypass-sla-daa-utility.4232377/)
(mt6877 reports mixed — worked, then "seems like they patched something?"),
[Chimera's supported-CPU page](https://chimeratool.com/docs/mtk-dimensity-cpu-summer-update-supported-models)
(paid vendor; claims SLA/DAA support incl. Dimensity 900/MT6877 — treat as vendor marketing of a paid service).

- The old free-for-all boot ROM holes (Kamakiri era) were closed on chip generations **before** MT6877. On this
  generation the BROM is reachable but demands **SLA/DAA vendor auth** before any download agent runs; the free
  reports are mixed and the reliable-sounding routes are paid tools of unverifiable provenance.
- Even granting full BROM write access: it does not give runtime root at all. It reads/writes **partitions**.
  Writing a *modified* boot/kernel image is then refused by AVB at boot (§0's green + enforcing facts) — i.e.
  the best you can do is reflash *stock signed* images. That makes BROM a **rescue/unbrick path**, not a root
  path, on a locked phone. Worth knowing as a safety net; useless for the goal.

### 2.5 The X6815D kernel tree on GitHub — what it actually is

**Fact base:** [whoisgabutuniverseshit/device_infinix_X6815D-kernel](https://github.com/whoisgabutuniverseshit/device_infinix_X6815D-kernel)
(read: repo page, branch `lineage-20`, commit messages; **archived Oct 2025**, 0 stars, 2 forks).

- It is a **custom-ROM device tree**, not a kernel source release: `kernel` (a prebuilt kernel image),
  `vendor-modules` (prebuilt), `dtb`/`dtbo.img`, and `kernel-headers` — taken from firmware
  **`X6815D-H777BC-S-GL-230919V275`** and rebranded from the CK9n sibling (same MT6877 platform). Its purpose
  is letting a LineageOS build *boot* with the stock kernel.
- So: **it does not enable building a patched kernel** (no full source), and — the deeper block — a patched
  kernel cannot be flashed on this phone anyway without unlocking (§4b). Its value to this research: (a) it
  proves a slightly newer firmware build (2023-09) exists for this model; (b) it shows kernel headers for the
  platform are floating around, which is one of the inputs a hypothetical `dfroot.ko` 4.19 build would need —
  with the caveat that headers from the `-S-230919` build may not byte-match our `-T-230714` kernel.

### 2.6 DirtyPipe and friends — ruled out by the kernel version (facts)

DirtyPipe (CVE-2022-0847) affects 5.8–5.10.1: **not 4.19**. The turnkey nf_tables LPE (CVE-2024-1086) targets
5.14–6.6 ([repo](https://github.com/Notselwyn/CVE-2024-1086)): **not 4.19**, and its generic form needs
`CONFIG_USER_NS`, which this kernel **does not build** (§0). Listed here so nobody re-walks these dead ends.

---

## 3. The MediaTek secure-boot angle, directly

- **Does this SoC have a known pre-boot hole that gives access without unlocking or wiping?** No public,
  working, *free* one. The BROM is reachable over USB, but MT6877-era SoCs enforce SLA/DAA before any flashing
  happens (§2.4 sources). This is MediaTek's post-2020 hardening, layered on top of the phone's own locked
  bootloader + AVB (§0). An "auth file" for a given brand circulates in paid/grey markets; provenance and
  cleanliness are exactly what you don't want to bet a phone you keep data on.
- **Opinion:** even if someone handed over a working auth bypass tomorrow, it still wouldn't be a *root*
  path (§2.4's second half). The MediaTek angle matters for unbricking, not for this goal.

---

## 4. The update question, both directions

**(a) Could updating ENABLE anything?**

- A newer firmware for this phone, if any OTA is even offered (the phone is ~4 years old; no evidence of an
  Android 14/XOS 14 build for X6815D was found — **Unknown**, and the best hint of *any* newer build is the
  2023-09 `230919V275` from the kernel tree, §2.5), would still ship the **same 4.19 vendor kernel**. KernelSU/
  APatch/Magisk GKI install paths would not open, because those need *flashing*, which needs *unlocking*,
  regardless of kernel version ([KernelSU installation doc](https://kernelsu.org/guide/installation); also
  RESEARCH-ROOT.md §4.2).
- **Updating enables nothing for no-wipe root.** The only enabler in this space is the LPE ecosystem adding a
  4.19/MTK profile, and that is independent of firmware updates.

**(b) Could updating CLOSE the exploits?**

- **It cannot close DirtyFrag:** no X6815D firmware can contain a fix for a bug disclosed in May 2026; every
  known build is from 2023. (If Infinix *miraculously* shipped a 2026-era update, it would — that is the one
  scenario to re-check.)
- It plausibly **would** close older bugs: a newer 2023 build with a newer security patch level could carry the
  Mali CVE-2023-4211 fix and other 2023-era kernel fixes. That closes the §2.3 path (which nobody was going to
  walk anyway) and hardens the phone generally.
- **Custom kernel side-load without unlocking: confirmed NO.** `verifiedbootstate=green` + `veritymode=enforcing`
  (read tonight, §0) mean the bootloader verifies every boot/kernel image against the vendor's signatures; a
  self-built kernel fails verification and the phone refuses it. All flashing paths route through unlock =
  wipe. This closes the last "update-to-custom-kernel" fantasy.

**Net (opinion): "update first" is neither help nor harm for temporary root.** It only removes old-bug options
and shifts offsets around. For RobotApp it changes nothing either way — and for the *stated goal* of this
research, **not updating keeps the bug surface** that a DirtyFrag port would need, while updating slightly
shrinks it.

---

## 5. If a no-wipe temporary root worked — what would it actually buy RobotApp?

Cross-referenced against RESEARCH-ROOT.md §3.6 ("what the plan already has without root"):

| Capability temp root would give | Value to RobotApp | Fragility |
|---|---|---|
| **Persistent-ish Wi-Fi adb** — with root each boot: re-enable the adb TCP port (`service.adb.tcp.port`) after every reboot | Real: kills PLAN §9's reboot pain without building the Keeper app | Low; but must re-run after every reboot (the plan's Wireless-debugging + Keeper route achieves the same with zero exploit risk) |
| **Raise the user limit (`fw.max_users`)** | The plan's true ceiling is 3 US spaces *plus* the window math (PLAN §7.2), and PLAN §10 already says a second phone beats more spaces; more users on one Infinix also deepens the one-device cluster (RESEARCH-ROOT §3.4) | Per-boot resetprop; **Unknown** whether XOS tolerates >4 users at all |
| **Per-space fingerprint spoofing** (Zygisk/LSPosed at runtime) | None that RESEARCH-ROOT didn't already reject: mismatch signals, injection traces, Widevine/sensors still honest (§3.2 of that doc) | Worst item on the menu |
| Play Integrity during ephemeral root | **Nuance:** the *boot chain stays stock and locked*, so hardware attestation still says locked+certified — the DEVICE label can plausibly still pass mid-session. But the exploit chain itself sets SELinux globally permissive and runs injected modules — exactly the "signs of attack / system compromise" wording of an empty verdict ([Play Integrity docs](https://developer.android.com/google/play/integrity/verdicts)) | Medium-high; and TikTok/Instagram root checks (RESEARCH-ROOT §2.2) still see the su/traces while rooted |
| The robot's actual jobs (post, read views, engage) | **Nothing needed.** uiautomator2 + adb + spaces + proxies already do all of it without root | — |

**Opinion:** the only line item with real pull is **Wi-Fi adb across reboots** — a convenience, not a
capability, and PLAN §9 already solves it safely. Everything else is either already owned without root or
already rejected in RESEARCH-ROOT. And an ephemeral root *adds* the daily ritual of "exploit the phone before
the 06:00 window starts" — a new failure mode (run fails → no Wi-Fi adb → the morning's posts fall back) in
exchange for nothing the plan lacks.

---

## 6. Verdict for this user's scale

**Not worth pursuing now. Wait, and only revisit if the tooling arrives.**

- The honest state (2026-11-19): the only credible no-wipe path is **a 4.19/MT6877 port of DirtyFrag that
  does not exist today**, by anyone. Nothing off-the-shelf works on this kernel.
- RobotApp's needs are fully covered without root (§5's last row); the one tempting convenience has a safer
  planned solution (Keeper, PLAN §9).
- The risk ledger for trying a port on THIS phone: it is the phone with the operator's kept data, the G2G
  brand lives in it, and the failure modes (failed exploit run, SELinux left permissive mid-session, a module
  that doesn't unload) land on a device the pipeline depends on. RESEARCH-ROOT's conclusion — a second cheap
  phone if capacity ever binds — dominates this path on every axis.
- **The single best next experiment, if the operator ever wants to test feasibility safely** (read-only,
  reversible, laptop-side; **not** running anything on the phone): a source-level check of whether the 4.19
  ESP receive path contains the vulnerable in-place decrypt behaviour — i.e. read the public upstream 4.19
  xfrm/ESP code next to the May-2026 fix commit, and the already-collected config facts (§0) settle the
  remaining preconditions. That is an evening of laptop work with zero phone risk, and it converts §1's
  "MAYBE" into a yes/no *before* anyone ever installs an APK. A second safe probe: watch the DFRoot/DirtyFrag
  and GhostLock repos for a 4.19 or MT6877 entry appearing (that's a re-check item, below).

---

## Capability vs risk table (the whole menu on THIS phone)

| Path | Needs | Unlock/wipe? | Survives reboot? | 2023-06 patch vulnerable? | Stability/brick risk | State for THIS phone |
|---|---|---|---|---|---|---|
| **DirtyFrag (CVE-2026-43284)** | ESP in kernel ✓ (fact), IpSecManager app path, a 4.19.191 `dfroot.ko` to be built, XOS-compatible SELinux path | **No / no wipe** | No — re-run per boot | **Yes** (fix postdates all known firmware); 4.19 applicability itself unverified | Designed fail-soft; untested here; RxRPC sibling's runs left apps crashing till reboot | **Maybe, with real porting** — no public 4.19/MTK build exists |
| **GhostLock (CVE-2026-43499)** | Exact `uname -r` profile | No / no wipe | No — re-run | Unknown for 4.19 | As above | **No** — supported list is 5.10–6.12 only |
| **Mali UAF (CVE-2023-4211)** | Full exploit development from a crash PoC | No / no wipe | No | **Likely yes** (fix 2023-10 > patch 2023-06); Infinix backport unknown | Kernel UAF = crash risk on the phone that carries the data | Catalogue only |
| **mtkclient / BROM** | SLA/DAA auth (paid/grey on MT6877) | Not root at all | n/a | n/a | BROM misuse can hard-brick | **No** — partition tool, not a root path; useful only as an unbrick net |
| **Magisk / KernelSU-LKM / APatch (installed)** | Flash patched boot/init_boot | **Yes → wipe** | Yes | n/a | Low once flashed | **Refused** (operator will not wipe) |
| **KernelSU loaded at runtime** | A working LPE above to carry it in | No | No | via the LPE | via the LPE | Only as DirtyFrag's payload, i.e. same "maybe" |

---

## What to re-check before trusting this document

Exploit details rot fast; this list is the refresh checklist, in order of how quickly each item decays:

1. **DFRoot / mitschud-DirtyFrag releases and issues** — the appearance of a 4.19- or MT6877-flavoured
   `dfroot.ko`, or any XOS/Infinix success report, flips §1 from MAYBE toward YES.
2. **GhostLock's SUPPORTED_DEVICES.md** — whether the list ever grows a 4.19 row (today it starts at 5.10).
3. **The 4.19 applicability question itself** — the upstream fix commit vs the 4.19 ESP receive path
   (laptop-side source reading; the safe experiment named in §6).
4. **Any 2026-era X6815D firmware** — if Infinix ever ships a new OTA, re-evaluate §4 (it would close DirtyFrag
   only if it is genuinely from after 2026-05).
5. **CVE-2026-43499's affected range** — if a public analysis shows the bug exists in pre-5.10 kernels,
   GhostLock moves from "No" to "porting maybe".
6. **The newer firmware's patch level** — if `230919V275` (or any other newer build) carries SPL ≥ 2023-10, the
   Mali CVE-2023-4211 assumption changes for updated phones (ours stays vulnerable as-is).

---

## Sources

Primary (repos' own code/docs, advisories, and this session's read-only adb):

- This phone's build/boot/config facts — read-only adb output, 2026-11-18 ~23:52–00:10 WIB (§0 table); command
  set: `getprop`, `cat /proc/version`, `uname -a/-r`, `getenforce`, `zcat /proc/config.gz`.
- DFRoot (upstream) — mechanism, chain, FAQ — <https://github.com/diabl0w/DFRoot>
- DirtyFrag (mitschud fork) — Samsung-flavoured build, module list, autorun/interlock docs —
  <https://github.com/mitschud/DirtyFrag>;
  prebuilt modules 5.10→6.18 —
  <https://github.com/mitschud/DirtyFrag/tree/master/app/src/main/jni/ko>
- CVE-2026-43284 — Red Hat CVE entry (affected subsystems, userns note, errata down to RHEL 8-era kernels) —
  <https://access.redhat.com/security/cve/cve-2026-43284>;
  Qualys "Dirty Frag" chain write-up (2026-05-07) —
  <https://blog.qualys.com/product-tech/vulnmgmt/detection-response/2026/05/09/dirty-frag-using-the-page-caches-as-an-attack-surface>;
  Rapid7 module — <https://www.rapid7.com/db/modules/exploit/linux/local/cve_2026_43284_dirty_frag/>
- GhostLock — app README, exact-`uname -r` supported devices (5.10–6.12), MediaTek porting guide —
  <https://github.com/YuKongA/ghostlock-app>
- CVE-2026-43499 popsicle PoC (verified on 6.12.x; run-stability caveat) —
  <https://github.com/x-spy/CVE-2026-43499-popsicle>
- CVE-2023-4211 Mali UAF — Project Zero in-the-wild RCA (fixed in 2023-10-05 SPL) —
  <https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2023/CVE-2023-4211.html>
- X6815D kernel device tree (prebuilt kernels/modules/headers, archived; reveals firmware 230919V275) —
  <https://github.com/whoisgabutuniverseshit/device_infinix_X6815D-kernel>
- KernelSU installation (flashing requirement, GKI-mode discontinuation) —
  <https://kernelsu.org/guide/installation>
- CVE-2024-1086 (kernel-range exclusion) — <https://github.com/Notselwyn/CVE-2024-1086>
- mtkclient and the SLA/auth reality — repo <https://github.com/bkerler/mtkclient>;
  issue #199 <https://github.com/bkerler/mtkclient/issues/199>;
  XDA auth-bypass thread <https://xdaforums.com/t/mod-dev-mediatek-mtk-auth-bypass-sla-daa-utility.4232377/>

Secondary / vendor-marketing (named as such):

- ChimeraTool's Dimensity CPU support list (paid tool claiming SLA/DAA for MT6877) —
  <https://chimeratool.com/docs/mtk-dimensity-cpu-summer-update-supported-models>
- Archive.org X6815D stock firmware mirror (hosting source, not vendor-authoritative) —
  <https://archive.org/details/infinix-zero-2023-x6815d-stock-rom-firmware>
- Android-14-for-Infinix status pages (FAQ-style, low authority; used only for "no evidence of an A14 OTA") —
  <https://electronics.alibaba.com/question/infinix-android-14-update-download,-eligibility-manual-install-guide>,
  <https://www.devicesfaq.com/en/update/infinix-zero-5g-2023>

Cross-linked, not repeated: [RESEARCH-ROOT.md](RESEARCH-ROOT.md) (should-we, detection surface, Play
Integrity), [PLAN.md](PLAN.md) §2 (phone facts), §9 (Wi-Fi adb / Keeper), §10 (the second-phone alternative).
