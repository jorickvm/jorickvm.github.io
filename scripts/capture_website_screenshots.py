#!/usr/bin/env python3
"""Build AtlasDays and capture deterministic website screenshots from Simulator."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_ROOT / "_site-src" / "data" / "screenshots.json"
DEVELOPER_DIR = Path("/Applications/Xcode.app/Contents/Developer")
BUNDLE_ID = "com.jorickvm.atlasdays"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="append", help="Capture id or scenario; repeat as needed.")
    parser.add_argument("--all", action="store_true", help="Capture every ready manifest entry.")
    parser.add_argument("--list", action="store_true", help="List capture states and exit.")
    parser.add_argument("--device", help="Override the manifest Simulator name.")
    parser.add_argument("--app-repo", type=Path)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run(
    command: list[str],
    *,
    env: dict[str, str],
    dry_run: bool = False,
    check: bool = True,
    echo_output: bool = True,
) -> str:
    print("+", " ".join(command))
    if dry_run:
        return ""
    result = subprocess.run(command, check=check, text=True, capture_output=True, env=env)
    if echo_output and result.stdout.strip():
        print(result.stdout.strip())
    return result.stdout


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def select_captures(manifest: dict, args: argparse.Namespace) -> list[dict]:
    captures = manifest["captures"]
    if args.all:
        return [capture for capture in captures if capture.get("status") == "ready"]
    requested = set(args.capture or [])
    return [
        capture
        for capture in captures
        if capture.get("id") in requested or capture.get("scenario") in requested
    ]


def simulator_lookup(env: dict[str, str], name: str) -> tuple[str, str]:
    raw = run(
        ["/usr/bin/xcrun", "simctl", "list", "devices", "available", "--json"],
        env=env,
        echo_output=False,
    )
    data = json.loads(raw)
    matches: list[dict] = []
    for devices in data.get("devices", {}).values():
        matches.extend(device for device in devices if device.get("name") == name)
    if not matches:
        raise SystemExit(f'No available Simulator named "{name}"')
    device = next((item for item in matches if item.get("state") == "Booted"), matches[0])
    return str(device["udid"]), str(device.get("state", "Shutdown"))


def build_app(app_repo: Path, udid: str, derived_data: Path, env: dict[str, str], dry_run: bool) -> Path:
    command = [
        str(DEVELOPER_DIR / "usr" / "bin" / "xcodebuild"),
        "-quiet",
        "-project", "AtlasDays.xcodeproj",
        "-scheme", "AtlasDays",
        "-configuration", "Debug",
        "-destination", f"platform=iOS Simulator,id={udid}",
        "-derivedDataPath", str(derived_data),
        "CODE_SIGNING_ALLOWED=NO",
        "build",
    ]
    print("+", " ".join(command))
    if not dry_run:
        subprocess.run(command, cwd=app_repo, env=env, check=True)
    return derived_data / "Build" / "Products" / "Debug-iphonesimulator" / "AtlasDays.app"


def write_target(raw_png: Path, target: Path, width: int, height: int, env: dict[str, str], dry_run: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".webp":
        run([
            shutil.which("cwebp") or "cwebp",
            "-quiet", "-q", "88", "-resize", str(width), str(height),
            str(raw_png), "-o", str(target),
        ], env=env, dry_run=dry_run)
        return
    if target.suffix.lower() == ".png":
        if dry_run:
            print(f"+ resize PNG {raw_png} -> {target} ({width}x{height})")
            return
        with tempfile.NamedTemporaryFile(suffix=".png") as resized:
            run(["/usr/bin/sips", "--resampleHeightWidth", str(height), str(width), str(raw_png), "--out", resized.name], env=env)
            shutil.copyfile(resized.name, target)
        return
    raise SystemExit(f"Unsupported screenshot target format: {target}")


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    if args.list:
        for capture in manifest["captures"]:
            print(f"{capture['status']:18} {capture['id']:28} {capture.get('scenario') or '-'}")
        return 0
    captures = select_captures(manifest, args)
    if not captures:
        raise SystemExit("Choose --all or at least one --capture id/scenario. Use --list to inspect options.")
    blocked = [capture["id"] for capture in captures if capture.get("status") != "ready"]
    if blocked:
        raise SystemExit(f"Capture entries are not ready: {', '.join(blocked)}")

    env = os.environ.copy()
    env["DEVELOPER_DIR"] = str(DEVELOPER_DIR)
    device_name = args.device or manifest["device"]["name"]
    app_repo = (args.app_repo or (SITE_ROOT.parent / "AtlasDays" / "AtlasDays")).resolve()
    derived_data = Path(tempfile.gettempdir()) / "AtlasDaysWebsiteScreenshots"
    if args.dry_run:
        udid, state = "SIMULATOR-UDID", "Shutdown"
    else:
        udid, state = simulator_lookup(env, device_name)
    if state != "Booted":
        run(["/usr/bin/xcrun", "simctl", "boot", udid], env=env, dry_run=args.dry_run)
    run(["/usr/bin/xcrun", "simctl", "bootstatus", udid, "-b"], env=env, dry_run=args.dry_run)

    app_path = derived_data / "Build" / "Products" / "Debug-iphonesimulator" / "AtlasDays.app"
    if not args.no_build:
        app_path = build_app(app_repo, udid, derived_data, env, args.dry_run)
    run(["/usr/bin/xcrun", "simctl", "install", udid, str(app_path)], env=env, dry_run=args.dry_run)

    width = int(manifest["device"]["target_width"])
    height = int(manifest["device"]["target_height"])
    captured_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    with tempfile.TemporaryDirectory() as temp_dir:
        for capture in captures:
            scenario = str(capture["scenario"])
            run(
                ["/usr/bin/xcrun", "simctl", "terminate", udid, BUNDLE_ID],
                env=env,
                dry_run=args.dry_run,
                check=False,
                echo_output=False,
            )
            run([
                "/usr/bin/xcrun", "simctl", "launch", "--terminate-running-process",
                udid, BUNDLE_ID, "--ui-testing", "--website-screenshot", scenario,
            ], env=env, dry_run=args.dry_run)
            if not args.dry_run:
                time.sleep(float(capture.get("settle_seconds", 4)))
            raw_png = Path(temp_dir) / f"{capture['id']}.png"
            run(["/usr/bin/xcrun", "simctl", "io", udid, "screenshot", str(raw_png)], env=env, dry_run=args.dry_run)
            for target_value in capture.get("targets", []):
                write_target(raw_png, SITE_ROOT / target_value, width, height, env, args.dry_run)
            if not args.dry_run:
                capture["last_captured_at"] = captured_at
                capture["captured_app_version"] = manifest["app_version"]
                capture["captured_device"] = device_name

    if not args.dry_run:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
