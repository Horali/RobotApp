"""A tiny fake adb for test_reconnect.py: it answers from a state file, mutating it on connect.

Usage: python fake_adb.py <state.json> <adb args...>
"""

import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
args = sys.argv[2]


def main() -> int:
    state = json.loads(state_path.read_text())
    connected: list[str] = list(state.get("devices", []))

    if args == "devices":
        print("List of devices attached")
        for serial in connected:
            print(f"{serial}\tdevice")
        return 0

    if args == "mdns services":
        print(state.get("mdns", "List of discovered mdns services"))
        return 0

    if args == "start-server":
        return 0

    if "tcpip" in args.split() and "5555" in args.split():
        print("restarting in TCP mode port: 5555")
        return 0

    if args.startswith("connect "):
        target = args.split()[1]
        if state.get("connect", {}).get(target):
            if target not in connected:
                connected.append(target)
                state_path.write_text(json.dumps({**state, "devices": connected}), encoding="utf-8")
            print(f"connected to {target}")
            return 0
        print(f"cannot connect to {target}")
        return 1

    print("unknown command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
