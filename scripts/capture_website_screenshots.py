#!/usr/bin/env python3
"""Build AtlasDays and capture deterministic website screenshots from Simulator."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import re
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
    parser.add_argument(
        "--id-prefix",
        help='Restrict --all to ids starting with this, e.g. "help-". Keeps a Help Center '
             "run from recapturing the published marketing assets.",
    )
    parser.add_argument("--list", action="store_true", help="List capture states and exit.")
    parser.add_argument("--device", help="Override the manifest Simulator name.")
    parser.add_argument(
        "--locale",
        default="en",
        help="Interface language to capture in. Non-default locales write to a <code>/ "
             "directory under the asset root (assets/article-images/<code>/..., "
             "assets/home/<code>/...) so a translated page can show its own screens.",
    )
    parser.add_argument(
        "--appearance",
        default="dark",
        choices=("dark", "light"),
        help="Interface appearance to capture in. Light runs pass --light through to the "
             "app harness and write alongside the dark file with a -light suffix, so the "
             "site can serve a matching set per theme without a second manifest.",
    )
    parser.add_argument(
        "--residence",
        help="Override the home country a capture is shot from (two-letter code, or "
             "\"none\" to keep the harness default). Normally left unset: captures that "
             "care declare it themselves in the manifest.",
    )
    parser.add_argument("--app-repo", type=Path)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help="Keep the full-screen PNG per scenario here instead of a temp dir, so crops "
             "can be re-cut later without relaunching the Simulator.",
    )
    parser.add_argument(
        "--from-raw",
        type=Path,
        help="Re-cut targets from PNGs saved by --raw-dir. Touches no Simulator and no build, "
             "which is what makes tuning a crop rectangle cheap.",
    )
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


def select_captures(manifest: dict, args: argparse.Namespace, device_name: str) -> list[dict]:
    captures = manifest["captures"]
    # A capture without a `device` belongs to the manifest default, so an iPad
    # run picks up only the entries that actually name the iPad. Without this
    # every run would try to capture the other device's slots on the wrong one.
    other_device = [
        capture for capture in captures
        if not device_matches(capture.get("device", manifest["device"]["name"]), device_name)
        and (not args.id_prefix or str(capture["id"]).startswith(args.id_prefix))
    ]
    captures = [
        capture for capture in captures
        if device_matches(capture.get("device", manifest["device"]["name"]), device_name)
    ]
    if other_device:
        # Say what this run cannot reach. Silence here reads as "everything is
        # captured", which is how a whole locale's iPad slots stayed English
        # without anyone noticing.
        families = sorted({str(c.get("device", "")) for c in other_device})
        print(
            f"skipping {len(other_device)} capture(s) that belong to another device "
            f"({', '.join(families)}); rerun with --device to capture them"
        )
    if args.all:
        if args.id_prefix:
            captures = [c for c in captures if str(c["id"]).startswith(args.id_prefix)]
        return [capture for capture in captures if capture.get("status") == "ready"]
    requested = set(args.capture or [])
    return [
        capture
        for capture in captures
        if capture.get("id") in requested or capture.get("scenario") in requested
    ]


def known_scenarios(app_repo: Path) -> set[str]:
    """Scenario names the app actually understands.

    Parsed from the harness enum so the manifest cannot drift from it. This
    exists because an unrecognised name is silently ignored at launch: the app
    comes up with an empty in-memory store and none of the pinned defaults, and
    that empty screen gets published as though it were the real thing.
    """
    source = app_repo / "AtlasDays" / "App" / "WebsiteScreenshotHarness.swift"
    if not source.exists():
        return set()
    names: set[str] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("case "):
            continue
        # `case fullMap = "full-map"` or a bare `case timeline`
        match = re.match(r'case\s+`?(\w+)`?(?:\s*=\s*"([^"]+)")?', stripped)
        if match:
            names.add(match.group(2) or match.group(1))
    return names


def device_matches(wanted: str, actual: str) -> bool:
    """Match a manifest device against a booted Simulator name.

    Slots name a device family ("iPad Pro 13-inch") while Simulator names carry
    a generation ("iPad Pro 13-inch (M5)"). Matching on the family means the
    manifest does not need editing every time Apple ships new hardware.
    """
    return actual == wanted or actual.startswith(f"{wanted} (")


def group_by_scenario(captures: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group captures by scenario, preserving manifest order."""
    grouped: dict[str, list[dict]] = {}
    for capture in captures:
        grouped.setdefault(str(capture["scenario"]), []).append(capture)
    return list(grouped.items())


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
        # Deliberately signed. `CODE_SIGNING_ALLOWED=NO` strips the iCloud
        # container entitlement, and `CKContainer.default()` then raises an
        # Objective-C CKException that no Swift `catch` can see, so the app
        # dies the moment a capture opens Settings → iCloud Sync. A signed
        # simulator build is also simply closer to what ships.
        "build",
    ]
    print("+", " ".join(command))
    if not dry_run:
        subprocess.run(command, cwd=app_repo, env=env, check=True)
    return derived_data / "Build" / "Products" / "Debug-iphonesimulator" / "AtlasDays.app"


# The Simulator language a locale captures in. Kept beside the path rule
# because the two must agree: a Japanese screenshot written to the English
# path would silently replace the English one.
LOCALE_LAUNCH = {
    "en": ("(en-US)", "en_US"),
    "ja": ("(ja)", "ja_JP"),
    "nl": ("(nl)", "nl_NL"),
    "de": ("(de)", "de_DE"),
    "es": ("(es)", "es_ES"),
    "fr": ("(fr)", "fr_FR"),
    "ru": ("(ru)", "ru_RU"),
    "uk": ("(uk)", "uk_UA"),
    "tr": ("(tr)", "tr_TR"),
    # The website locale is `pt`, but the app ships Brazilian Portuguese only
    # (`InterfaceLocale.supportedAppLanguageCodes`), so the Simulator language
    # is pt-BR. Launching "(pt)" would fall back to English silently.
    "pt": ("(pt-BR)", "pt_BR"),
    "ko": ("(ko)", "ko_KR"),
    "zh-Hant": ("(zh-Hant)", "zh_TW"),
    "zh-Hans": ("(zh-Hans)", "zh_CN"),
}


# The residence a marketing capture is shot from, per language. This is not
# cosmetic: `TrackerCatalog.entries` demotes the Schengen presets below the
# curated visa rules when the home country is inside the Schengen area, on the
# grounds that a Schengen resident has no 90/180 limit of their own. So a
# Dutch or German reader should see the visa rules they would actually reach
# for, and an English, Japanese, Russian or Ukrainian reader should see
# Schengen leading, because that is the limit they are most likely counting.
#
# The rule is "the locale's own country". Spanish and French are the loose
# ends, since both are spoken well beyond their Schengen homelands; they follow
# the rule until there is a reason to split them by region.
LOCALE_RESIDENCE = {
    "en": "US",
    "ja": "JP",
    "ru": "RU",
    "uk": "UA",
    "nl": "NL",
    "de": "DE",
    "es": "ES",
    "fr": "FR",
    "tr": "TR",
    # `pt` is Brazilian Portuguese for a Brazilian reader, so the residence is
    # BR, not PT. A Brazilian is a visa-free third-country national who counts
    # Schengen; a Portuguese national is an EU citizen with no cap, and a PT
    # residence would demote the presets this locale exists to show.
    "pt": "BR",
    "ko": "KR",
    "zh-Hant": "TW",
    "zh-Hans": "CN",
}


def launch_locale_args(code: str) -> list[str]:
    if code not in LOCALE_LAUNCH:
        raise SystemExit(f"No Simulator language mapping for locale {code!r}")
    languages, locale = LOCALE_LAUNCH[code]
    return ["-AppleLanguages", languages, "-AppleLocale", locale]


def resolve_residence(group: list[dict], code: str, override: str | None) -> str | None:
    """The residence to pin for one launch, or None to leave the app's default.

    Declared per capture rather than per run so a later recapture cannot lose
    the intent: a manifest entry asking for ``auto`` gets the language's own
    country whoever runs it, and every other capture keeps the harness default.
    """
    if override:
        return None if override == "none" else override
    wanted = {c.get("residence") for c in group if c.get("residence")}
    if not wanted:
        return None
    if len(wanted) > 1:
        raise SystemExit(
            f"captures sharing one scenario disagree about residence: {sorted(wanted)}"
        )
    value = wanted.pop()
    if value != "auto":
        return value
    if code not in LOCALE_RESIDENCE:
        raise SystemExit(f"No residence mapping for locale {code!r}")
    return LOCALE_RESIDENCE[code]


# Asset families that have a per-locale directory. A capture whose target
# falls outside these writes to the same path in every language, which is only
# correct for images with no text in them.
LOCALE_ASSET_ROOTS = ("assets/article-images/", "assets/home/")


def output_path(relpath: str, code: str, appearance: str = "dark") -> Path:
    """Where a capture lands.

    Non-default locales get their own directory. Light-appearance runs instead
    get a ``-light`` suffix on the filename, staying beside the dark file: the
    site picks between the two with a CSS rule keyed on the theme attribute, so
    the pair has to be siblings, and a directory split would put every
    reference in the markup one level out of step with the other theme.
    """
    if appearance == "light":
        relpath = re.sub(r"(\.[^./]+)$", r"-light\1", relpath)
    if code == "en":
        return SITE_ROOT / relpath
    for root in LOCALE_ASSET_ROOTS:
        if relpath.startswith(root):
            return SITE_ROOT / f"{root}{code}/{relpath[len(root):]}"
    raise SystemExit(
        f"{relpath!r} has no per-locale path, so capturing it as {code!r} would "
        f"overwrite the English file. Add its asset root to LOCALE_ASSET_ROOTS, "
        f"or narrow the run with --capture/--id-prefix."
    )


def manual_source(capture: dict, code: str, appearance: str) -> Path | None:
    """The archived PNG a hand-captured entry is cut from, or None if absent.

    Manual entries (the Home Screen widget gallery, the iOS Settings page) are
    photographed outside the app, so a language or an appearance is a different
    PNG rather than a different launch. Their filenames follow the same shape
    the outputs do: ``widgets-gallery.png`` is English dark, ``.de`` marks the
    language, ``-light`` the appearance.

    Returns None when that file does not exist, and the caller skips the entry.
    Skipping is the honest answer: publishing English pixels under a German
    filename is worse than the English fallback the page already falls back to.
    """
    relpath = capture["source"]
    stem, dot, ext = relpath.rpartition(".")
    if code != "en":
        stem = f"{stem}.{code}"
    if appearance == "light":
        stem = f"{stem}-light"
    source = SITE_ROOT / f"{stem}{dot}{ext}"
    return source if source.exists() else None


def normalize_targets(capture: dict) -> list[dict]:
    """Accept both target spellings.

    Marketing captures list plain path strings and want the whole screen. Help
    Center slots need a rectangle out of that same screen, so they use
    ``{"path": ..., "crop": [x, y, w, h]}``. Several slots crop the same
    capture differently, which is why cropping belongs here and not in a
    second launch.
    """
    normalized = []
    for target in capture.get("targets", []):
        if isinstance(target, str):
            normalized.append({"path": target, "crop": None})
        else:
            normalized.append({"path": target["path"], "crop": target.get("crop")})
    return normalized


def write_target(
    raw_png: Path,
    target: Path,
    width: int,
    height: int,
    crop: list[int] | None,
    env: dict[str, str],
    dry_run: bool,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".webp":
        command = [shutil.which("cwebp") or "cwebp", "-quiet", "-q", "88"]
        if crop:
            # cwebp crops before it resizes, and a cropped control keeps its
            # native pixels: resizing it to the full device frame would stretch
            # a 400pt-tall strip over 2868px.
            command += ["-crop", *(str(int(v)) for v in crop)]
        elif should_resize(raw_png, width, height, env):
            command += ["-resize", str(width), str(height)]
        command += [str(raw_png), "-o", str(target)]
        run(command, env=env, dry_run=dry_run)
        return
    if target.suffix.lower() == ".png":
        if crop:
            raise SystemExit(f"Cropping is only implemented for WebP targets: {target}")
        if dry_run:
            print(f"+ resize PNG {raw_png} -> {target} ({width}x{height})")
            return
        with tempfile.NamedTemporaryFile(suffix=".png") as resized:
            run(["/usr/bin/sips", "--resampleHeightWidth", str(height), str(width), str(raw_png), "--out", resized.name], env=env)
            shutil.copyfile(resized.name, target)
        return
    raise SystemExit(f"Unsupported screenshot target format: {target}")


def raw_dimensions(raw_png: Path, env: dict[str, str]) -> tuple[int, int] | None:
    output = run(
        ["/usr/bin/sips", "-g", "pixelWidth", "-g", "pixelHeight", str(raw_png)],
        env=env, check=False, echo_output=False,
    )
    dimensions = {}
    for line in output.splitlines():
        key, _, value = line.strip().partition(":")
        if key in ("pixelWidth", "pixelHeight") and value.strip().isdigit():
            dimensions[key] = int(value.strip())
    if len(dimensions) != 2:
        return None
    return dimensions["pixelWidth"], dimensions["pixelHeight"]


def should_resize(raw_png: Path, width: int, height: int, env: dict[str, str]) -> bool:
    """Only resize a capture that shares the target's aspect ratio.

    The manifest carries one target size, sized for the iPhone. An iPad
    landscape capture forced into it comes out squashed into portrait, so a
    capture whose shape does not match keeps its own pixels.
    """
    raw = raw_dimensions(raw_png, env)
    if raw is None:
        return False
    if abs((raw[0] / raw[1]) - (width / height)) >= 0.01:
        return False
    # Downscale only. A hand-captured shot from a smaller phone shares the same
    # aspect, and stretching it up to the Pro Max frame invents pixels for no
    # gain: the page scales the image anyway.
    return raw[0] > width


def rotate_to_landscape(raw_png: Path, env: dict[str, str], dry_run: bool) -> None:
    """Turn a landscape capture the right way up, if it needs it.

    The app rotates fine once the Simulator itself is rotated. What the
    screenshot looks like afterwards depends on the runtime, and it changed
    under us: `simctl io screenshot` used to always write the framebuffer in
    the device's native portrait, so landscape content arrived on its side and
    needed 90 degrees clockwise. On iOS 26.5 it writes the rotated orientation
    directly, and the same unconditional rotation turns a correct landscape
    capture into a broken portrait one (2026-09-02: it published three Japanese
    iPad screenshots at 2064x2752 against English's 2752x2064).

    So decide from the pixels rather than from the runtime: rotate only a raw
    that is still taller than it is wide. That is correct under both
    behaviours, and stays correct if a later runtime reverts.
    """
    dimensions = raw_dimensions(raw_png, env)
    if dimensions is None:
        # Unreadable dimensions: rotate as before rather than silently skipping,
        # since the old behaviour is the one that produced the shipped set.
        if dry_run:
            print(f"+ rotate {raw_png} 90 degrees clockwise (dimensions unknown)")
            return
        run(["/usr/bin/sips", "--rotate", "90", str(raw_png)], env=env, echo_output=False)
        return
    width, height = dimensions
    if width >= height:
        print(f"+ {raw_png} is already landscape ({width}x{height}), not rotating")
        return
    if dry_run:
        print(f"+ rotate {raw_png} 90 degrees clockwise ({width}x{height})")
        return
    run(["/usr/bin/sips", "--rotate", "90", str(raw_png)], env=env, echo_output=False)


def capture_settled(
    udid: str,
    raw_png: Path,
    settle_seconds: float,
    env: dict[str, str],
    dry_run: bool,
    max_extra: float = 20.0,
    exact: bool = False,
) -> None:
    """Screenshot once the screen stops changing.

    A fixed sleep is a guess, and a wrong guess photographs the launch splash,
    which is how several slots quietly shipped a black screen with a logo on it.
    This waits the scenario's settle time, then keeps re-shooting every two
    seconds until two consecutive frames are byte-identical.

    Deliberately capped: a scenario captured mid-animation (the photo scan) never
    produces two identical frames, and for those the cap is the answer.
    """
    if dry_run:
        print(f"+ screenshot {raw_png} once settled (>= {settle_seconds}s)")
        return
    time.sleep(settle_seconds)
    shot = ["/usr/bin/xcrun", "simctl", "io", udid, "screenshot", str(raw_png)]
    run(shot, env=env, echo_output=False)
    if exact:
        # Some states are deliberately temporary. The undo toast lives about
        # four seconds, so waiting for the screen to stop changing is waiting
        # for the very thing being photographed to disappear.
        return
    previous = raw_png.read_bytes()
    waited = 0.0
    while waited < max_extra:
        time.sleep(2.0)
        waited += 2.0
        run(shot, env=env, echo_output=False)
        current = raw_png.read_bytes()
        if current == previous:
            return
        previous = current
    print(f"note: {raw_png.stem} never settled; captured after {settle_seconds + waited:.0f}s")


def set_status_bar(udid: str, env: dict[str, str], dry_run: bool) -> None:
    """Pin every capture to the same status bar.

    `discharging` matters: `charged` and `charging` both draw a charging
    indicator, which is an instant tell that a screenshot was staged.
    """
    run([
        "/usr/bin/xcrun", "simctl", "status_bar", udid, "override",
        "--time", "9:41",
        "--wifiBars", "3",
        "--cellularBars", "4",
        "--batteryLevel", "100",
        "--batteryState", "discharging",
    ], env=env, dry_run=dry_run, check=False, echo_output=False)


def clear_status_bar(udid: str, env: dict[str, str], dry_run: bool) -> None:
    run(
        ["/usr/bin/xcrun", "simctl", "status_bar", udid, "clear"],
        env=env, dry_run=dry_run, check=False, echo_output=False,
    )


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    if args.list:
        for capture in manifest["captures"]:
            print(f"{capture['status']:18} {capture['id']:28} {capture.get('scenario') or '-'}")
        return 0
    device_name = args.device or manifest["device"]["name"]
    captures = select_captures(manifest, args, device_name)
    if not captures:
        raise SystemExit(
            f'No ready captures for "{device_name}". Choose --all or a --capture id/scenario, '
            "and check --device against the manifest. Use --list to inspect options."
        )
    blocked = [capture["id"] for capture in captures if capture.get("status") != "ready"]
    if blocked and not args.raw_dir:
        raise SystemExit(f"Capture entries are not ready: {', '.join(blocked)}")
    if blocked:
        # With --raw-dir the point is to collect full screens to measure crops
        # against, so a not-yet-ready entry still gets its screenshot taken. It
        # just does not publish anything until its rectangle exists.
        print(f"note: {len(blocked)} entries are not ready; capturing raws only for those")

    env = os.environ.copy()
    env["DEVELOPER_DIR"] = str(DEVELOPER_DIR)
    width = int(manifest["device"]["target_width"])
    height = int(manifest["device"]["target_height"])

    # Entries with a `source` are captured by hand, outside the app: the iOS
    # Settings page and the Home Screen widget surfaces. They are cut from the
    # archived PNG rather than launched, and never reach the Simulator.
    manual = [c for c in captures if c.get("source")]
    captures = [c for c in captures if not c.get("source")]
    skipped = []
    for capture in list(manual):
        source = manual_source(capture, args.locale, args.appearance)
        if source is None:
            if args.locale == "en" and args.appearance == "dark":
                raise SystemExit(
                    f'Manual source missing for {capture["id"]}: '
                    f'{SITE_ROOT / capture["source"]}'
                )
            manual.remove(capture)
            skipped.append(capture["id"])
            continue
        for target in normalize_targets(capture):
            write_target(
                source, output_path(target["path"], args.locale, args.appearance),
                width, height, target["crop"], env, args.dry_run,
            )
    if manual:
        print(f"cut {len(manual)} manual capture(s) from archived sources")
    if skipped:
        print(
            f"skipping {len(skipped)} manual capture(s) with no "
            f"{args.locale}/{args.appearance} source: {', '.join(skipped)}"
        )

    if args.from_raw:
        recut = 0
        for scenario, group in group_by_scenario(captures):
            raw_png = args.from_raw / f"{scenario}.png"
            if not raw_png.exists():
                print(f"! no raw capture for {scenario}, skipping")
                continue
            for capture in group:
                for target in normalize_targets(capture):
                    write_target(
                        raw_png, output_path(target["path"], args.locale, args.appearance),
                        width, height, target["crop"], env, args.dry_run,
                    )
                    recut += 1
        print(f"re-cut {recut} targets from {args.from_raw}")
        return 0
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

    captured_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    # An unrecognised scenario is not a no-op: the app launches with an empty
    # store and no pinned defaults, and that blank screen publishes silently.
    valid = known_scenarios(app_repo)
    unknown = sorted({str(c["scenario"]) for c in captures} - valid) if valid else []
    if unknown:
        raise SystemExit(
            "These scenarios are not in WebsiteScreenshotScenario, so the app would "
            f"launch unseeded and publish a blank screen: {', '.join(unknown)}"
        )

    set_status_bar(udid, env, args.dry_run)
    if args.raw_dir:
        args.raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_root = args.raw_dir or Path(temp_dir)
            # One launch per scenario, not per capture. Slots that share a
            # scenario are different crops of the same screen, so relaunching
            # for each would be slower and could drift between shots.
            for scenario, group in group_by_scenario(captures):
                run(
                    ["/usr/bin/xcrun", "simctl", "terminate", udid, BUNDLE_ID],
                    env=env,
                    dry_run=args.dry_run,
                    check=False,
                    echo_output=False,
                )
                launch = [
                    "/usr/bin/xcrun", "simctl", "launch", "--terminate-running-process",
                    udid, BUNDLE_ID,
                    "--ui-testing", "--website-screenshot", scenario,
                    *launch_locale_args(args.locale),
                ]
                if any(capture.get("landscape") for capture in group):
                    launch.insert(-4, "--landscape")
                if args.appearance == "light":
                    launch.append("--light")
                residence = resolve_residence(group, args.locale, args.residence)
                if residence:
                    launch += ["--residence", residence]
                run(launch, env=env, dry_run=args.dry_run)
                raw_png = raw_root / f"{scenario}.png"
                capture_settled(
                    udid,
                    raw_png,
                    max(float(c.get("settle_seconds", 4)) for c in group),
                    env,
                    args.dry_run,
                    exact=any(c.get("settle_exact") for c in group),
                )
                if any(capture.get("landscape") for capture in group):
                    rotate_to_landscape(raw_png, env, args.dry_run)
                for capture in group:
                    if capture.get("status") != "ready":
                        continue
                    for target in normalize_targets(capture):
                        write_target(
                            raw_png, output_path(target["path"], args.locale, args.appearance),
                            width, height, target["crop"], env, args.dry_run,
                        )
                    if not args.dry_run:
                        # Provenance is a timestamp and a device, deliberately
                        # not an app version: the site never refers to
                        # AtlasDays by version number, in copy or in metadata.
                        #
                        # Light runs write their own key. They leave the dark
                        # files untouched, so stamping the shared one would
                        # claim a dark capture that never happened and hide a
                        # genuinely stale screenshot behind a fresh date.
                        if args.appearance == "light":
                            capture["last_captured_light_at"] = captured_at
                        else:
                            capture["last_captured_at"] = captured_at
                            capture["captured_device"] = device_name
    finally:
        # Always clear, including after a failed capture: a left-over override
        # silently stages every later screenshot taken on this simulator.
        clear_status_bar(udid, env, args.dry_run)

    if not args.dry_run:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
