"""Build keeper.apk by hand: javac -> d8 -> aapt2 -> apksigner.

No Gradle, no Android Studio project: the app is one manifest and one Java file, and the SDK's
own tools are enough to build it. The signing key lives in data/keeper/ (git-ignored), created on
the first run and reused after, so the update path works on the phone.

Usage:  .venv/Scripts/python.exe keeper/build.py
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KEEPER = REPO / "keeper"
BUILD = KEEPER / "build"
SDK = Path(r"C:\Users\child\AppData\Local\Android\Sdk")
BUILD_TOOLS = SDK / "build-tools" / "36.0.0"
PLATFORM_JAR = SDK / "platforms" / "android-35" / "android.jar"
KEYSTORE = REPO / "data" / "keeper" / "keeper.keystore"
KEY_PASS = "robotapp-keeper"
PACKAGE = "app.robotapp.keeper"
CLASSES = ["app/robotapp/keeper/KeeperReceiver.class", "app/robotapp/keeper/KeeperReceiver$r.class"]


def run(command: list[str], **kwargs) -> str:
    done = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if done.returncode != 0:
        raise SystemExit(f"failed: {' '.join(command)}\n{done.stdout}\n{done.stderr}")
    return done.stdout


def main() -> None:
    for path in (BUILD / "classes", BUILD / "dex"):
        for stale in path.rglob("*"):
            stale.unlink() if stale.is_file() else None
    (BUILD / "classes").mkdir(parents=True, exist_ok=True)
    (BUILD / "dex").mkdir(parents=True, exist_ok=True)

    run(
        [
            "javac",
            "-source", "8", "-target", "8",
            "-bootclasspath", str(PLATFORM_JAR),
            "-d", str(BUILD / "classes"),
            str(KEEPER / "src" / PACKAGE.replace(".", "/") / "KeeperReceiver.java"),
        ]
    )
    compiled = [str(p) for p in (BUILD / "classes").rglob("*.class")]
    run([str(BUILD_TOOLS / "d8.bat"), "--release", "--lib", str(PLATFORM_JAR), "--output", str(BUILD / "dex"), *compiled])

    unsigned = BUILD / "keeper-unsigned.apk"
    run(
        [
            str(BUILD_TOOLS / "aapt2.exe"), "link",
            "-I", str(PLATFORM_JAR),
            "--manifest", str(KEEPER / "AndroidManifest.xml"),
            "--min-sdk-version", "24",
            "--target-sdk-version", "33",
            "--version-code", "1",
            "--version-name", "1.0",
            "-o", str(unsigned),
        ]
    )
    with zipfile.ZipFile(unsigned, "a") as apk:
        apk.write(BUILD / "dex" / "classes.dex", "classes.dex", compress_type=zipfile.ZIP_DEFLATED)

    if not KEYSTORE.exists():
        KEYSTORE.parent.mkdir(parents=True, exist_ok=True)
        run(
            [
                "keytool", "-genkeypair",
                "-keystore", str(KEYSTORE),
                "-alias", "keeper",
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
                "-storepass", KEY_PASS, "-keypass", KEY_PASS,
                "-dname", "CN=RobotApp Keeper,O=RobotApp",
            ]
        )

    signed = BUILD / "keeper.apk"
    run(
        [
            str(BUILD_TOOLS / "apksigner.bat"), "sign",
            "--ks", str(KEYSTORE),
            "--ks-pass", f"pass:{KEY_PASS}",
            "--out", str(signed),
            str(unsigned),
        ]
    )
    print(run([str(BUILD_TOOLS / "apksigner.bat"), "verify", "--print-certs", str(signed)]))
    print("built:", signed, f"({signed.stat().st_size} bytes)")


if __name__ == "__main__":
    sys.exit(main())
