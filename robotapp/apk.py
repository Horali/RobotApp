"""Installing TikTok's US build safely (PLAN §4.7).

Play Store is the first choice, but the owner's Play account is Indonesian and offers `trill`, so a signed
download is the fallback the user approved. Before anything is installed the robot checks the signing
certificate with `apksigner` and refuses on any mismatch: a re-signed APK is exactly what we must not install.
Nothing from this module runs without an expected certificate digest.
"""

from __future__ import annotations

import os
import re
import subprocess
import zipfile
from pathlib import Path

from .adb import Phone

SDK_CANDIDATES = (
    Path(os.environ.get("ANDROID_HOME", r"C:\Users\child\AppData\Local\Android\Sdk")),
    Path(os.environ.get("ANDROID_SDK_ROOT", r"C:\Users\child\AppData\Local\Android\Sdk")),
)


class ApkRejected(RuntimeError):
    pass


def find_apksigner() -> Path | None:
    for sdk in SDK_CANDIDATES:
        build_tools = sdk / "build-tools"
        if not build_tools.exists():
            continue
        versions = sorted((p for p in build_tools.iterdir() if p.is_dir()), reverse=True)
        for version in versions:
            candidate = version / ("apksigner.bat" if os.name == "nt" else "apksigner")
            if candidate.exists():
                return candidate
    return None


def certificate_sha256(apk: Path) -> str:
    """The signer's certificate digest, lowercase hex without colons."""
    signer = find_apksigner()
    if signer is None:
        raise ApkRejected("apksigner is not installed (Android SDK build-tools), so the APK cannot be checked")
    done = subprocess.run(
        [str(signer), "verify", "--print-certs", str(apk)], capture_output=True, text=True, timeout=120
    )
    if done.returncode != 0:
        raise ApkRejected(f"apksigner rejected {apk.name}: {(done.stdout + done.stderr).strip()[:300]}")
    match = re.search(r"certificate SHA-256 digest:\s*([0-9a-fA-F]+)", done.stdout)
    if not match:
        raise ApkRejected(f"no certificate digest in apksigner's output for {apk.name}")
    return match.group(1).lower()


def verify(apk: Path, expected_sha256: str) -> str:
    """Refuse to install unless the signer matches the expected digest (PLAN §4.7 step 2)."""
    expected = re.sub(r"[^0-9a-fA-F]", "", expected_sha256).lower()
    if len(expected) != 64:
        raise ApkRejected("an expected certificate SHA-256 (64 hex characters) is required before installing")
    actual = certificate_sha256(apk)
    if actual != expected:
        raise ApkRejected(f"certificate mismatch: {actual} != {expected} (nothing installed)")
    return actual


def install(phone: Phone, apk: Path) -> str:
    return phone.install_apk(apk)


def install_bundle(phone: Phone, bundle: Path, work_dir: Path) -> str:
    """An .apkm/.xapk is a zip of split APKs: install them together, base first."""
    work_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".apk")]
        if not names:
            raise ApkRejected(f"{bundle.name} has no .apk inside")
        for name in names:
            archive.extract(name, work_dir)
    parts = sorted((work_dir / n for n in names), key=lambda p: (0 if "base" in p.name.lower() else 1, p.name))
    return phone.install_multiple(parts)
