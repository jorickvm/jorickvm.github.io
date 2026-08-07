#!/usr/bin/env python3
"""Rewrite the concise AtlasDays Help Center sources and structured metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "_site-src"
CONTENT = SOURCE / "content" / "help"
DATA = SOURCE / "data"
UPDATED_DISPLAY = "August 2, 2026"
UPDATED_ISO = "2026-08-02"
ARTICLES: list[dict[str, object]] = []


def add(
    slug: str,
    title: str,
    category: str,
    description: str,
    body: str,
    *,
    next_steps: list[tuple[str, str]],
    synonyms: list[str],
    shots: list[dict[str, str]],
) -> None:
    ARTICLES.append(
        {
            "slug": slug,
            "title": title,
            "category": category,
            "description": description,
            "body": body.strip(),
            "next": next_steps,
            "synonyms": synonyms,
            "shots": shots,
        }
    )


def shot(
    key: str,
    scenario: str,
    placement: str,
    alt: str,
    device: str = "iPhone 17 Pro Max",
    priority: str = "p1",
    crop: str = "control",
) -> dict[str, str]:
    """One deferred screenshot slot.

    ``placement`` names the exact anchor in the article body, because the
    published HTML carries only ``<!-- SCREENSHOT_DEFERRED: key | scenario -->``
    and the capture agent needs to know what the image sits under.

    ``priority`` is ``p0`` when the article does not make sense without the
    image and ``p1`` when it merely helps, so a partial capture session can
    stop at a coherent point. ``crop`` is ``control`` for a tight crop around
    the referenced button or row, ``screen`` when the whole screen matters.
    """
    return {
        "key": key,
        "scenario": scenario,
        "placement": placement,
        "alt": alt,
        "device": device,
        "priority": priority,
        "crop": crop,
    }


def image_relpath(slug: str, key: str) -> str:
    return f"assets/article-images/help/{slug}/{key}.webp"


def webp_dimensions(path: Path) -> tuple[int, int] | None:
    """Intrinsic size of a WebP, straight from its header.

    Only the two container shapes this project produces are handled: simple
    lossy (``VP8 ``) and the extended form cwebp writes for cropped output
    (``VP8X``). Anything else returns None and the tag simply omits the size.
    """
    try:
        data = path.read_bytes()[:32]
    except OSError:
        return None
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if chunk == b"VP8 ":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return width, height
    return None


# Phrases that should become a link to the article that explains them, longest
# first so "CSV Format Reference" wins over "CSV Import" when both could match
# the same spot. That order is match precedence only. Which links survive the
# budget is decided by link_score, never by where the phrase happens to appear:
# ranking by reading position once linked Photo Import and Flighty Import while
# dropping CSV Import from the sentence between them.
INLINE_LINK_TARGETS: list[tuple[str, str]] = [
    ("CSV Format Reference", "csv-format-reference"),
    ("AtlasDays Pro", "atlasdays-pro"),
    ("Delete or Reset", "delete-and-reset"),
    ("Smart Alerts", "smart-alerts"),
    ("Photo Import", "photo-import"),
    ("Flighty Import", "flighty-import"),
    ("CSV Import", "csv-import"),
    ("iCloud Sync", "icloud-sync-and-restore"),
    ("Auto-Detect", "auto-detect-trips"),
    ("Home Country", "getting-started"),
    ("Exact Dates", "history-and-import"),
    ("rolling window", "trackers-and-limits"),
    ("Schengen", "schengen-90-180"),
    ("Timeline", "timeline-and-calendar"),
    ("Dashboard", "dashboard-and-map"),
    ("Transit", "history-and-import"),
    ("widget", "widgets"),
    ("forecast", "plan-a-trip"),
    ("Spreadsheet", "export-and-reports"),
    ("export", "export-and-reports"),
    ("app icon", "appearance-and-personalization"),
    ("country name", "languages"),
    ("accent color", "appearance-and-personalization"),
]

# Ordinary vocabulary that happens to name an article. Linking one of these is
# a convenience. Linking a product name the reader may not have met yet is the
# reason inline linking exists, so those win when the budget binds.
AMBIENT_PHRASES = frozenset(
    {
        "rolling window",
        "Schengen",
        "Timeline",
        "Dashboard",
        "widget",
        "forecast",
        "export",
        "app icon",
        "country name",
        "accent color",
    }
)

SKIP_LINE_MARKERS = ("<h1", "<h2", "<h3", "{{shot:", "class=\"breadcrumb\"")


def link_budget(body: str) -> int:
    """A runaway guard, not a quota. One link per 25 words, floor 6, ceiling 10.

    Demand is already self-limiting: only the first mention of a target is ever
    linked, so an article cannot exceed the size of INLINE_LINK_TARGETS however
    long it gets. Measured across the Help Center, articles want two to seven
    links, so this binds on nothing today and exists to stop a future article
    from turning blue. Set it any tighter and it starts deleting links that are
    genuinely warranted, which is what a flat cap of 6 did to AtlasDays Pro.
    """
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    return max(6, min(10, words // 25))


def link_score(phrase: str, target: str, next_slugs: set[str]) -> float:
    """How much a link is warranted. Highest first when the budget binds."""
    score = 0.0
    if target in next_slugs:
        # The author already named this as where the reader goes next, which is
        # the only place in an article definition that states intent.
        score += 3
    if phrase not in AMBIENT_PHRASES:
        score += 2
    # Tie-break only: a longer phrase is a more deliberate mention. Held under 1
    # so it can never outrank either signal above.
    return score + len(phrase) / 100


def link_related(article: dict[str, object]) -> str:
    """Turn the first mention of another article's subject into a link.

    Candidates are collected across the whole article, ranked by how much each
    link is warranted, cut to the budget, and only then written back in reading
    order, so what survives does not depend on what happened to appear first.
    """
    slug = str(article["slug"])
    body = str(article["body"])
    next_slugs = {target for target, _ in article["next"]}
    # Targets already linked by hand in the prose. Without this the automatic
    # pass would add a second link to the same article a paragraph later.
    used: set[str] = set(re.findall(r'href="/help/([a-z0-9-]+)"', body))

    lines = body.split("\n")
    # (score, line index, start, end, target, matched text)
    candidates: list[tuple[float, int, int, int, str, str]] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        if any(marker in line for marker in SKIP_LINE_MARKERS) or "<a " in line:
            continue
        for phrase, target in INLINE_LINK_TARGETS:
            if target == slug or target in used or target in seen:
                continue
            # Whole words only, with an optional plural, so "export" never
            # matches inside "exported" and "widget" still catches "widgets".
            match = re.search(rf"\b{re.escape(phrase)}s?\b", line)
            if not match:
                continue
            # Never link inside a tag, only in visible text.
            if line.rfind("<", 0, match.start()) > line.rfind(">", 0, match.start()):
                continue
            seen.add(target)
            candidates.append(
                (
                    link_score(phrase, target, next_slugs),
                    index,
                    match.start(),
                    match.end(),
                    target,
                    match.group(0),
                )
            )

    winners = sorted(candidates, key=lambda item: -item[0])[: link_budget(body)]
    # Rewrite from the end backwards so an earlier match's offsets stay valid
    # after a later one on the same line has been replaced.
    for _, index, start, end, target, text in sorted(winners, key=lambda item: (-item[1], -item[2])):
        line = lines[index]
        lines[index] = line[:start] + f'<a href="/help/{target}">{text}</a>' + line[end:]
    return "\n".join(lines)


def wrap_content(article: dict[str, object]) -> str:
    """Render the body, resolving each screenshot slot.

    A slot becomes a real ``<figure>`` as soon as its WebP exists at
    ``assets/article-images/help/<slug>/<key>.webp``, and stays an HTML comment
    until then. Capturing a screenshot is therefore "save the file, rerun this
    script" with no hand-editing of generated HTML.
    """
    slug = str(article["slug"])
    body = link_related(article)
    for item in article["shots"]:
        key = str(item["key"])
        marker = "{{shot:" + key + "}}"
        relpath = image_relpath(slug, key)
        if (ROOT / relpath).exists():
            alt = str(item["alt"]).replace('"', "&quot;")
            # Intrinsic size is read off the file rather than assumed: control
            # crops are all different shapes, and without width/height the
            # browser reflows the article as each image arrives.
            size = webp_dimensions(ROOT / relpath)
            dimensions = f' width="{size[0]}" height="{size[1]}"' if size else ""
            # A landscape shot (the iPad captures) must not be squeezed into the
            # portrait-phone width cap, or it lands on a phone at a tenth of its
            # size and nothing in it can be read.
            landscape = " help-shot-landscape" if size and size[0] > size[1] else ""
            replacement = (
                f'<figure class="help-shot help-shot-{item["crop"]}{landscape}">'
                f'<img src="/{relpath}" alt="{alt}"{dimensions} loading="lazy" decoding="async" />'
                f"</figure>"
            )
        else:
            replacement = f"<!-- SCREENSHOT_DEFERRED: {key} | {item['scenario']} -->"
        body = body.replace(marker, replacement)
    unresolved = "{{shot:" in body
    if unresolved:
        raise SystemExit(f"Unresolved screenshot marker in {article['slug']}")
    return "\n".join(
        [
            '    <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">AtlasDays</a> / <a href="/help/">Help Center</a></nav>',
            "",
            f'    <h1>{article["title"]}</h1>',
            body,
            "",
        ]
    )


def record(article: dict[str, object], title_by_slug: dict[str, str]) -> dict[str, object]:
    slug = str(article["slug"])
    title = str(article["title"])
    description = str(article["description"])
    canonical = f"https://atlasdays.app/help/{slug}"
    path = f"help/{slug}.html"
    next_steps = [
        {
            "url": f"/help/{target}",
            "title": title_by_slug[target],
            "description": explanation,
        }
        for target, explanation in article["next"]
    ]
    return {
        "path": path,
        "section": "help",
        "category": article["category"],
        "title": f"{title} — AtlasDays Help Center",
        "meta": [
            {"name": "description", "content": description},
            {"property": "og:title", "content": f"{title} — AtlasDays Help Center"},
            {"property": "og:description", "content": description},
            {"property": "og:type", "content": "article"},
            {"property": "og:url", "content": canonical},
            {"name": "twitter:card", "content": "summary_large_image"},
            {"name": "twitter:title", "content": f"{title} — AtlasDays Help Center"},
            {"name": "twitter:description", "content": description},
            {"name": "apple-itunes-app", "content": "app-id=6760133544, app-argument=https://apps.apple.com/app/atlasdays-track-country-days/id6760133544"},
        ],
        "links": [{"rel": "canonical", "href": canonical}],
        "jsonld": [
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "AtlasDays", "item": "https://atlasdays.app"},
                        {"@type": "ListItem", "position": 2, "name": "Help Center", "item": "https://atlasdays.app/help/"},
                        {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": title,
                    "description": description,
                    "author": {"@type": "Organization", "name": "AtlasDays"},
                    "publisher": {"@type": "Organization", "name": "AtlasDays"},
                    "url": canonical,
                    "dateModified": UPDATED_ISO,
                },
                ensure_ascii=False,
                indent=2,
            ),
        ],
        "content": f"content/help/{slug}.html",
        "style_variants": ["help20260802"],
        "next_steps": next_steps,
        "search_synonyms": article["synonyms"],
        "screenshot_slots": article["shots"],
        "last_updated": UPDATED_DISPLAY,
    }


# ARTICLE_DEFINITIONS

add(
    "getting-started",
    "Getting Started",
    "trips-travel-days",
    "What AtlasDays does, how to fill your Timeline from photos and Auto-Detect instead of typing, and how to add your first tracker.",
    """
    <p class="article-answer">AtlasDays records which country you were in on which day, then counts those days against the limits that matter to you. Trips live in the Timeline, the Dashboard shows what they add up to, and a tracker watches one specific rule.</p>

    <h2>What AtlasDays is for</h2>
    <p>Questions with a consequence attached: how many Schengen 90/180 days are still available, whether you are approaching a 183-day residency threshold, how long you have really been out of your home country this year.</p>
    <p>AtlasDays keeps the record and counts the days. Interpreting an immigration or tax rule is still your responsibility.</p>

    <h2>Fill your Timeline without typing</h2>
    <p>Photos cover the past. Auto-Detect covers what comes next.</p>
    <p>Open <strong>Settings → Import → Photos</strong> and scan a date range. Photo Import reads geotagged photo metadata on the device and proposes trips for review, and nothing is saved until you confirm. Use CSV Import instead when your history is already in a spreadsheet or a booking record, or Flighty Import when your Flighty flight history covers most of it.</p>
    {{shot:import-hub}}
    <p>Then turn on <strong>Auto-Detect Trips</strong> so new travel arrives as a Timeline suggestion rather than a manual entry. It never saves a trip without your confirmation.</p>

    <h2>The Timeline holds the record</h2>
    <p>Every trip, in order, with the dates you gave it. Tap a trip to edit it, or tap <strong>+</strong> to add one by hand.</p>
    <p>Not every trip needs precise dates. Use Exact Dates for anything feeding a live limit, and year-only or unknown-date entries for older history you cannot place confidently. Forcing a guess into exact dates makes the record look more certain than it is.</p>
    {{shot:timeline}}

    <h2>The Dashboard shows what it adds up to</h2>
    <p>Days abroad, countries and continents visited, the world map, and your trackers. The period selector at the top switches between this year, a fiscal year, or a custom range, so the same record answers different questions.</p>
    {{shot:dashboard}}

    <div class="callout"><p><strong>Home Country only affects Days Abroad.</strong> Onboarding asks you to choose one, and it sets which country counts as home rather than abroad. Choose <strong>No fixed residence</strong> to count every recorded day instead. You can change it in Settings at any time.</p></div>

    <h2>Add your first tracker</h2>
    <p>A tracker is the reason to use AtlasDays rather than a travel diary. Open <strong>Trackers</strong>, tap <strong>+</strong>, and choose a preset such as Schengen 90/180 or a 183-day residency threshold. It then shows used days, remaining days, and how close you are.</p>
    {{shot:add-tracker}}
    <p>A tracker is only as good as the trips behind it. Treat its total as provisional while the relevant trips are still approximate.</p>

    <section class="if-needed">
      <h2>If the first totals look wrong</h2>
      <p>Check the selected Dashboard period, your Home Country setting, any open-ended trip still counting toward today, Transit trips, and whether the trips that matter use Exact Dates.</p>
    </section>
    """,
    next_steps=[
        ("photo-import", "Rebuild older history from your photo library."),
        ("create-a-tracker", "Set up the limit you actually need to watch."),
        ("day-counting", "See exactly which travel days count toward a total."),
    ],
    synonyms=["what is atlasdays", "first setup", "onboarding", "home country", "new user", "how does it work", "start here", "first steps", "set up"],
    shots=[
        shot("import-hub", "import", "End of the first paragraph of Fill your Timeline without typing", "Import screen listing Photos, Flighty, and CSV options", priority="p1", crop="control"),
        shot("timeline", "timeline", "End of The Timeline holds the record", "AtlasDays Timeline listing saved trips by country and date", priority="p0", crop="screen"),
        shot("dashboard", "dashboard", "End of The Dashboard shows what it adds up to", "AtlasDays Dashboard showing day totals, trackers, and the world map", priority="p0", crop="screen"),
        shot("add-tracker", "trackers", "End of the first paragraph of Add your first tracker", "Trackers screen with the Add Tracker button", priority="p1", crop="control"),
    ],
)

add(
    "timeline-and-calendar",
    "Add, Edit, or Delete a Trip",
    "trips-travel-days",
    "Use the AtlasDays Timeline or Calendar to add a trip, correct its details, or remove it from your travel history.",
    """
    <p class="article-answer">The Timeline is the source record behind the Dashboard, map, trackers, exports, and widgets. Edit the trip there when any of those views need different input.</p>

    <h2>Add a trip</h2>
    <ol>
      <li>Open <strong>Timeline</strong> and tap <strong>+</strong>.</li>
      <li>Select a country. For a US trip, add a state when you want state-level tracking.</li>
      <li>Choose the appropriate trip mode and enter its dates.</li>
      <li>Optionally add purposes or notes, then tap <strong>Save</strong>.</li>
    </ol>
    {{shot:timeline-list}}

    <h2>Edit a trip</h2>
    <p>Tap a trip in the Timeline list or its entry in Calendar view. Change the country, state, dates, purposes, notes, or Transit status, then save. Related totals refresh from the edited record.</p>
    {{shot:add-edit}}

    <h2>Delete a trip</h2>
    <p>Open the trip and choose <strong>Delete Trip</strong>, or use the delete action available from the Timeline row. After a Timeline deletion an <strong>Undo</strong> button appears at the bottom of the screen for a few seconds. Once it disappears the deletion stands, so restore the trip by adding it again.</p>

    <h2>Switch between List and Calendar</h2>
    <p><strong>List</strong> is fastest for reviewing trips chronologically. <strong>Calendar</strong> makes gaps, overlaps, and trips spanning weeks easier to see. Both views edit the same records.</p>
    {{shot:calendar}}

    <h2>United States stays</h2>
    <p>A United States trip without a state still contributes to country-level US totals. The Timeline row shows the state beneath the country name once you add one. Add the state when you need state-specific trackers or the US state breakdown.</p>

    <section class="if-needed">
      <h2>If a trip cannot be saved</h2>
      <p>Check that the end date is not before the start date and review any overlap warning. Approximate modes use years instead of exact calendar dates.</p>
    </section>
    """,
    next_steps=[
        ("day-counting", "See how edited dates change inclusive day totals."),
        ("history-and-import", "Choose the right precision when exact dates are unavailable."),
        ("dashboard-and-map", "See where saved trips appear across AtlasDays."),
    ],
    synonyms=["edit trip", "delete trip", "add stay", "calendar", "timeline", "us state breakdown", "remove trip", "undo", "change dates", "fix a trip", "wrong dates", "add trip"],
    shots=[
        shot("timeline-list", "timeline", "End of the Add a trip steps", "Timeline list containing past and ongoing trips", priority="p0", crop="screen"),
        shot("add-edit", "edit-trip", "End of the Edit a trip section", "Edit Trip sheet showing country and exact dates", priority="p0", crop="screen"),
        shot("calendar", "timeline-calendar", "End of the Switch between List and Calendar section", "Calendar view with trips spanning several dates", priority="p0", crop="screen"),
    ],
)

add(
    "day-counting",
    "How AtlasDays Counts Travel Days",
    "trips-travel-days",
    "Understand inclusive arrival and departure days, overlaps, ongoing trips, approximate records, and Transit in AtlasDays.",
    """
    <p class="article-answer">AtlasDays counts each calendar day from the arrival date through the departure date for Exact Dates trips. Both boundary days are included.</p>

    <h2>Exact Dates are inclusive</h2>
    <p>A trip from June 1 through June 3 contributes three days: June 1, June 2, and June 3. A same-day trip contributes one day.</p>
    {{shot:exact-dates}}

    <h2>Overlapping days are deduplicated</h2>
    <p>When multiple qualifying trips cover the same calendar day inside a tracker’s country set, that tracker counts the day once. Overlaps remain visible in the Timeline so you can decide whether the records themselves need correction.</p>

    <h2>Ongoing trips use today</h2>
    <p>An Exact Dates trip without an end date is ongoing. AtlasDays uses today as its effective end date, so its total can increase each day until you close the trip.</p>
    {{shot:ongoing}}

    <h2>Approximate trips do not create numeric days</h2>
    <p><strong>Year</strong> and <strong>Unknown</strong> preserve travel history without inventing dates. They can mark a place as visited, but they do not contribute to numeric day totals or rolling-window calculations.</p>
    {{shot:approximate}}

    <h2>Transit contributes zero days</h2>
    <p>Use <strong>Transit</strong> when you did not enter the country, such as an airside connection. The record stays in your history but contributes zero days and does not mark the country as visited.</p>
    {{shot:transit}}

    <h2>Home Country has a specific role</h2>
    <p>Your Home Country setting affects the Dashboard’s Days Abroad metric. It does not remove trips from a country tracker or change how an exact trip’s inclusive dates are calculated.</p>

    <div class="callout"><p><strong>AtlasDays is a record-keeping tool.</strong> A tracker counts the dates you entered. Official visa, tax, and residency rules decide which days legally qualify. The <a href="/learn/">Travel Rule Library</a> explains the common rules in plain language.</p></div>

    <section class="if-needed">
      <h2>If a total differs from your manual count</h2>
      <p>Compare the tracker’s places and window, then check for an ongoing trip, a Transit record, an approximate trip, or an overlap. Count the arrival and departure dates before comparing again.</p>
    </section>
    """,
    next_steps=[
        ("history-and-import", "Understand which trip modes can and cannot produce numeric days."),
        ("dashboard-and-map", "Relate trip records to Dashboard periods and map highlights."),
        ("trackers-and-limits", "See how tracker windows select from these counted days."),
    ],
    synonyms=["arrival day", "departure day", "inclusive dates", "overlap", "ongoing trip", "ground crossing", "midnight", "wrong count", "border crossing", "counted twice", "does the arrival day count"],
    shots=[
        shot("exact-dates", "add-trip", "In the Exact Dates are inclusive section", "Exact Dates trip showing start and end dates", priority="p0", crop="control"),
        shot("ongoing", "trip-editor-ongoing", "In the Ongoing trips use today section", "Exact Dates trip with no end date", priority="p1", crop="control"),
        shot("approximate", "trip-editor-year", "In the Approximate trips section", "Trip editor with Year precision selected", priority="p1", crop="control"),
        shot("transit", "trip-editor-transit", "In the Transit contributes zero days section", "Trip editor with Transit selected", priority="p1", crop="control"),
    ],
)

add(
    "history-and-import",
    "Understanding Trip Modes",
    "trips-travel-days",
    "Choose Exact Dates, Year, Unknown, Transit, or an ongoing trip without inventing precision in AtlasDays.",
    """
    <p class="article-answer">Use the most precise mode supported by your evidence. Exact Dates power day totals; approximate modes preserve history without pretending the dates are known.</p>

    <h2>Exact Dates</h2>
    <p>Choose <strong>Exact Dates</strong> when you know the arrival and departure dates. These trips contribute to Dashboard totals, tracker calculations, exports, and forecasts.</p>

    <h2>Ongoing</h2>
    <p>Leave the end date empty on an Exact Dates trip only when the stay is genuinely ongoing. AtlasDays counts through today until you add the departure date.</p>

    <h2>Year</h2>
    <p>Choose <strong>Year</strong> when you know the year but not the calendar dates. A year-only trip marks the place as visited but contributes no numeric days.</p>
    {{shot:mode-year}}

    <h2>Unknown</h2>
    <p>Choose <strong>Unknown</strong> when even the year is uncertain. This is useful for a country list or map, not for compliance calculations.</p>
    {{shot:mode-unknown}}

    <h2>Transit</h2>
    <p>Choose <strong>Transit</strong> when you did not enter the country. Transit contributes zero days and does not mark the country as visited.</p>
    {{shot:mode-transit}}

    <h2>All five modes in one place</h2>
    <p>The mode selector in the trip editor holds every option, so you can change a trip's precision later without recreating it.</p>
    {{shot:mode-selector}}

    <h2>Choose conservatively</h2>
    <p>Keep a half-remembered trip approximate for now, and switch it to Exact Dates once a passport stamp, booking, photo, or other record confirms the boundaries. An approximate trip that is honest about what you know is more useful than exact dates you had to guess.</p>

    <section class="if-needed">
      <h2>If an approximate trip is missing from a total</h2>
      <p>That is expected: Year and Unknown trips preserve visit history but do not create calendar days. Edit the trip to Exact Dates only when you can support those dates.</p>
    </section>
    """,
    next_steps=[
        ("day-counting", "Learn what each mode contributes to day calculations."),
        ("photo-import", "Use photo evidence to propose more precise trip boundaries."),
        ("csv-import", "Import a prepared history while preserving date precision."),
    ],
    synonyms=["exact dates", "year only", "unknown date", "open ended", "ongoing", "transit", "approximate trip", "approximate", "dont know the dates", "rough dates", "old trips"],
    shots=[
        shot("mode-year", "trip-editor-year", "In the Year section", "Trip editor with Year precision selected", priority="p1", crop="control"),
        shot("mode-unknown", "trip-editor-unknown", "In the Unknown section", "Trip editor with Unknown precision selected", priority="p1", crop="control"),
        shot("mode-transit", "trip-editor-transit", "In the Transit section", "Trip editor with Transit selected", priority="p1", crop="control"),
        shot("mode-selector", "add-trip", "End of the All five modes in one place section", "Trip mode selector showing Exact Dates, Year, Unknown, and Transit", priority="p0", crop="screen"),
    ],
)

add(
    "dashboard-and-map",
    "Understanding the Dashboard and Map",
    "trips-travel-days",
    "See how Dashboard periods, Home Country, trip precision, and visit rules shape AtlasDays totals and map highlights.",
    """
    <p class="article-answer">The Dashboard summarizes your Timeline for the selected period. The map answers where you have been; numeric cards answer how many qualifying days are recorded.</p>

    <h2>Start with the selected period</h2>
    <p>Use the period control at the top of the Dashboard before comparing a card with a trip or export. A calendar year, recent period, and all-time view can legitimately show different results.</p>
    {{shot:period-selector}}

    <h2>Days Abroad uses Home Country</h2>
    <p>With a Home Country selected, Days Abroad reflects exact recorded days outside that country. With <strong>No fixed residence</strong>, it reflects exact recorded travel days without subtracting one home country.</p>

    <h2>The map and totals answer different questions</h2>
    <p>A non-Transit trip can highlight a country as visited even when its mode is Year or Unknown. Those approximate trips do not create numeric day totals. Transit does neither.</p>
    {{shot:map-state}}

    <h2>United States detail</h2>
    <p>A country-level United States trip can highlight the US and contribute to US totals. State-level views require a state on the trip; an untagged US trip cannot be assigned to a state automatically.</p>

    <h2>Share cards follow the Dashboard</h2>
    <p>Review the period and visible result before sharing. You can choose the share-card appearance and language without changing the underlying trip record.</p>
    {{shot:share-cards}}

    <section class="if-needed">
      <h2>If a Dashboard card is surprising</h2>
      <p>Open the Timeline and inspect the period’s exact, approximate, ongoing, and Transit trips. Then verify Home Country and any missing US state tags.</p>
    </section>
    """,
    next_steps=[
        ("day-counting", "Review the inclusive and precision rules behind numeric cards."),
        ("trackers-and-limits", "Understand why a tracker may use a different window than the Dashboard."),
        ("timeline-and-calendar", "Correct the trip records feeding both views."),
    ],
    synonyms=["dashboard totals", "map highlights", "days abroad", "visited countries", "period selector", "share card", "map wrong", "country count", "map", "statistics"],
    shots=[
        shot("period-selector", "dashboard", "In the Start with the selected period section", "Dashboard period selector open", priority="p0", crop="control"),
        shot("map-state", "full-map", "In the map and totals section", "AtlasDays world map with visited countries highlighted", priority="p0", crop="screen"),
        shot("share-cards", "share-cards", "In the Share cards section", "Share preview showing AtlasDays Dashboard cards", priority="p1", crop="control"),
    ],
)

add(
    "create-a-tracker",
    "Create a Tracker",
    "trackers-limits",
    "Create an AtlasDays tracker from a preset or custom rule and check its places, window, and day limit.",
    """
    <p class="article-answer">Create a tracker after the relevant Exact Dates trips are in your Timeline, then verify the rule’s places, window, and limit before using its result.</p>

    <h2>Add a tracker</h2>
    <ol>
      <li>Open <strong>Trackers</strong> and tap <strong>+</strong>.</li>
      <li>Choose a category: <strong>Residence</strong>, <strong>Schengen</strong>, <strong>Visa &amp; Entry Limits</strong>, <strong>Travel Goal</strong>, <strong>US State</strong>, or <strong>Custom</strong>.</li>
      <li>Select a preset when one matches your need, or choose a custom setup.</li>
      <li>Review the name, countries or US states, time window, and limit.</li>
      <li>Save the tracker.</li>
    </ol>
    {{shot:category-picker}}
    <p>The category you pick decides which presets you are offered next.</p>
    {{shot:preset-picker}}

    <h2>Understand the window</h2>
    <ul>
      <li><strong>Rolling window</strong> looks back a set number of calendar days from the selected date.</li>
      <li><strong>Calendar year</strong> uses January 1 through December 31.</li>
      <li><strong>Per entry</strong> evaluates a continuous stay rather than adding unrelated visits.</li>
    </ul>

    <p>Tracking the Schengen 90/180 rule? <a href="/help/schengen-90-180">Follow the dedicated walkthrough</a> instead of building it by hand.</p>

    <h2>Review the places</h2>
    <p>A multi-country tracker counts qualifying exact days across its selected country set. A US state tracker needs state-tagged United States trips; country-only US records cannot feed a specific state.</p>
    {{shot:configured-editor}}

    <h2>Presets are starting configurations</h2>
    <p>A preset saves setup time. It does not change the rule you are actually subject to, so confirm it matches your nationality, permission, purpose, and current situation before relying on the number.</p>

    <div class="callout"><p><strong>Free AtlasDays includes one tracker.</strong> AtlasDays Pro adds unlimited trackers and Smart Alerts.</p></div>

    <section class="if-needed">
      <h2>If the new tracker has no days</h2>
      <p>Confirm that its places match your trips and that the relevant trips use Exact Dates rather than Year, Unknown, or Transit.</p>
    </section>
    """,
    next_steps=[
        ("schengen-90-180", "Set up the most common rule step by step."),
        ("trackers-and-limits", "Understand exactly how the saved configuration selects days."),
        ("smart-alerts", "Add threshold notifications to a configured tracker."),
    ],
    synonyms=[
        "add tracker", "new tracker", "preset", "schengen tracker", "residence tracker", "custom rule",
        "create counter", "day counter", "visa tracker", "tax residency tracker", "183 day",
        "esta", "us state tracker", "travel goal",
    ],
    shots=[
        shot("category-picker", "tracker-categories", "Directly after step 2, the category list", "Add Tracker category picker showing Residence, Schengen, Visa and Entry Limits, Travel Goal, US State, and Custom", priority="p0", crop="screen"),
        shot("preset-picker", "tracker-presets", "Directly after step 3, the preset list", "Tracker preset picker with available rules for the chosen category", priority="p0", crop="screen"),
        shot("configured-editor", "tracker-editor", "End of the Review the places section", "Configured tracker editor showing places, window, and limit", priority="p0", crop="screen"),
    ],
)

add(
    "schengen-90-180",
    "Track the Schengen 90/180 Rule",
    "trackers-limits",
    "Set up the Schengen 90/180 tracker in AtlasDays and read the days you have used and the days you have left.",
    """
    <p class="article-answer">Open <strong>Trackers</strong>, tap <strong>+</strong>, choose <strong>Schengen</strong>, and select the <strong>90/180 Short-Stay Rule</strong> preset. AtlasDays creates a tracker for the Schengen Area with a 90-day limit across a rolling 180-day window.</p>

    <h2>Set up the tracker</h2>
    <ol>
      <li>Open <strong>Trackers</strong> and tap <strong>+</strong>.</li>
      <li>Choose the <strong>Schengen</strong> category.</li>
      <li>Select <strong>90/180 Short-Stay Rule</strong>.</li>
      <li>Review the countries, the 90-day limit, and the 180-day window.</li>
      <li>Save the tracker.</li>
    </ol>
    {{shot:schengen-category}}
    <p>The Schengen category offers two presets. Pick the short-stay rule unless you hold a visa.</p>
    {{shot:schengen-preset}}

    <h2>Add the trips it needs</h2>
    <p>The tracker can only count trips already in your Timeline. Add every Schengen stay from the past 180 days using <strong>Exact Dates</strong>. Year and Unknown trips preserve history but contribute no days, so they cannot support a 90/180 answer.</p>
    {{shot:schengen-timeline}}

    <h2>Read the result</h2>
    <p>The tracker card shows days used against the 90-day limit. Open it for the detail chart, which shows how the count rose and when earlier days drop out of the window.</p>
    {{shot:schengen-detail}}

    <h2>The window moves every day</h2>
    <p>A rolling window always looks back 180 days from the date you are viewing. Days you spent in the Schengen Area gradually leave the window, so your total can fall without you editing anything. That is why a number checked last month is not the number that applies today.</p>

    <h2>Arrival and departure days both count</h2>
    <p>A stay from June 1 through June 3 uses three days. Airside connections recorded as <strong>Transit</strong> use none. This matches how the rule is normally applied at a border.</p>

    <h2>If you hold a visa instead</h2>
    <p>The <strong>Single-Entry Visa</strong> preset in the same category tracks one continuous stay against the days printed on your visa, rather than the 90/180 short-stay allowance.</p>

    <div class="callout"><p><strong>AtlasDays counts the dates you entered.</strong> The border authority decides which days qualify. Read <a href="/learn/schengen-90-180-rule">what 90 days in any 180-day period means</a> in the Travel Rule Library, and check your own permission before you travel.</p></div>

    <section class="if-needed">
      <h2>If the total looks wrong</h2>
      <p>Check that every Schengen stay in the last 180 days is recorded with Exact Dates, that no stay is still open-ended, and that the countries you visited are in the tracker. <a href="/learn/schengen-countries-list-90-180-rule">The Schengen country list</a> shows which places the rule covers.</p>
    </section>
    """,
    next_steps=[
        ("plan-a-trip", "Test a future Schengen stay against the same limit."),
        ("trackers-and-limits", "Understand exactly how the rolling window selects days."),
        ("smart-alerts", "Get notified before you approach 90 days."),
    ],
    synonyms=[
        "schengen", "90 180", "90/180", "schengen 90 180", "europe", "eu", "schengen area",
        "short stay", "how many days can i stay", "schengen calculator", "180 day window",
        "rolling window", "visa free", "days left in europe",
    ],
    shots=[
        shot("schengen-category", "tracker-categories", "Directly after step 2, on the Schengen category row", "Add Tracker category picker with the Schengen category", priority="p0", crop="control"),
        shot("schengen-preset", "tracker-presets-schengen", "Directly after step 3, the Schengen preset list", "Schengen preset list showing 90/180 Short-Stay Rule and Single-Entry Visa", priority="p0", crop="screen"),
        shot("schengen-timeline", "timeline", "End of the Add the trips it needs section", "Timeline list showing Schengen stays recorded with exact dates", priority="p1", crop="control"),
        shot("schengen-detail", "tracker-detail-schengen", "End of the Read the result section", "Schengen tracker detail showing days used against the 90-day limit", priority="p0", crop="screen"),
    ],
)

add(
    "plan-a-trip",
    "Check Whether a Planned Trip Fits",
    "trackers-limits",
    "Add a future trip in AtlasDays and use the tracker forecast to see whether it stays inside your limit.",
    """
    <p class="article-answer">Add the trip with its real future dates, then open the tracker that governs it. The forecast tells you whether those dates take you past the limit and on which date that happens.</p>

    <h2>Add the trip you are considering</h2>
    <ol>
      <li>Open <strong>Timeline</strong> and tap <strong>+</strong>.</li>
      <li>Choose the country, and a US state when you track states.</li>
      <li>Enter the planned arrival and departure dates using <strong>Exact Dates</strong>.</li>
      <li>Save the trip.</li>
    </ol>
    <p>A future trip does not change your current total. It is counted separately as planned travel until its dates arrive.</p>
    {{shot:plan-future-trip}}

    <h2>Read the forecast</h2>
    <p>Open the tracker that covers those countries. When planned travel would take you past a limit, AtlasDays names the date, for example <em>Based on your travel plans, you'll reach the limit on 14 Oct</em>. On a goal tracker, the same forecast tells you when you would reach your target instead.</p>

    <h2>Try a different set of dates</h2>
    <p>Edit the planned trip and save it again. The forecast recalculates immediately, so you can shorten the stay, move it later, or split it until the dates work.</p>
    {{shot:plan-chart}}

    <h2>What the forecast cannot do</h2>
    <p>Only Exact Dates contribute. A planned trip saved as Year or Unknown carries no dates to project. An ongoing trip with no end date is treated as continuing, so close it when you know you have left.</p>

    <h2>Remove a trip you decided against</h2>
    <p>Open the planned trip in Timeline and delete it. Nothing else has to be corrected, because a future trip never entered your historical totals.</p>

    <div class="callout"><p><strong>A forecast is arithmetic, not permission.</strong> It projects your own recorded dates forward. It does not confirm that a border authority will admit you.</p></div>

    <section class="if-needed">
      <h2>If no forecast appears</h2>
      <p>Confirm that the planned trip uses Exact Dates with both dates set, that its country is inside the tracker, and that the trip starts in the future rather than today.</p>
    </section>
    """,
    next_steps=[
        ("schengen-90-180", "Test planned travel against the 90/180 limit."),
        ("timeline-and-calendar", "Edit or remove the planned trip afterwards."),
        ("smart-alerts", "Be notified as the tracker approaches its limit."),
    ],
    synonyms=[
        "plan a trip", "future trip", "upcoming trip", "planned travel", "forecast", "projection",
        "can i travel", "will i exceed", "before i book", "trip planning", "what if",
        "days remaining", "book a flight",
    ],
    shots=[
        shot("plan-future-trip", "trip-editor-future", "Directly after the numbered steps", "Add Trip sheet with future exact dates entered", priority="p0", crop="screen"),
        shot("plan-chart", "tracker-detail", "End of the Try a different set of dates section", "Tracker detail chart including projected planned travel", priority="p0", crop="screen"),
    ],
)

add(
    "trackers-and-limits",
    "How Tracker Totals Are Calculated",
    "trackers-limits",
    "Understand how an AtlasDays tracker combines selected places, exact trip days, window type, and limit.",
    """
    <p class="article-answer">A tracker selects qualifying Exact Dates from its configured places, deduplicates overlapping calendar days, and applies its saved time window.</p>

    <h2>Four settings determine the result</h2>
    <ol>
      <li><strong>Places:</strong> only trips in the selected countries or US states qualify.</li>
      <li><strong>Window:</strong> rolling, calendar-year, and per-entry trackers examine different date ranges.</li>
      <li><strong>Limit:</strong> the threshold determines the tracker’s progress and status.</li>
      <li><strong>Trip precision:</strong> Exact Dates can count; Year, Unknown, and Transit contribute zero days.</li>
    </ol>

    <h2>Rolling windows move every day</h2>
    <p>A rolling tracker looks backward from its selected reference date. Older days leave the window while newer exact trip days enter it, so the total can change even when you do not edit a trip.</p>

    <h2>Calendar-year trackers reset by year</h2>
    <p>These trackers count qualifying days from January 1 through December 31 of the selected year. Switching years changes the records in scope.</p>

    <h2>Per-entry trackers evaluate continuity</h2>
    <p>A per-entry tracker focuses on a continuous stay within its places rather than combining unrelated visits into a single total.</p>

    <h2>Charts and forecasts</h2>
    <p>The detail chart explains how the count changes across time. Planned future Exact Dates can contribute to a forecast; approximate future trips cannot. <a href="/help/plan-a-trip">Checking whether a planned trip fits</a> covers the forecast in detail.</p>
    {{shot:detail-chart}}
    <p>The limit and window that shape that chart are set in the tracker editor.</p>
    {{shot:goal-window}}

    <section class="if-needed">
      <h2>Check which trips affect a tracker</h2>
      <p>Open its detail view, confirm the places and window, then compare those settings with Timeline. Pay special attention to ongoing trips, Transit, approximate dates, overlaps, and missing US state tags.</p>
    </section>
    """,
    next_steps=[
        ("day-counting", "Review inclusive dates, overlaps, and precision rules."),
        ("plan-a-trip", "Use the same rule to test travel you have not taken yet."),
        ("create-a-tracker", "Change the places, window, or limit behind the result."),
    ],
    synonyms=[
        "tracker total", "rolling window", "calendar year", "per entry", "per stay", "days remaining",
        "tracker count", "check trips", "90 180", "how many days left", "days used", "counting window",
        "tracker status", "tracker color",
    ],
    shots=[
        shot("detail-chart", "tracker-detail", "In the Charts and forecasts section", "Tracker detail chart across its active window", priority="p0", crop="screen"),
        shot("goal-window", "tracker-editor", "End of the Charts and forecasts section", "Tracker editor showing its limit and window controls", priority="p1", crop="control"),
    ],
)

add(
    "smart-alerts",
    "Smart Alerts",
    "trackers-limits",
    "Configure AtlasDays Smart Alerts for tracker thresholds and understand when notifications can appear.",
    """
    <p class="article-answer">Smart Alerts notify you when a tracker reaches configured milestones. They depend on the tracker’s saved rule, qualifying trips, and notification permission.</p>

    <h2>Turn on alerts</h2>
    <ol>
      <li>Open the tracker and choose its alert settings.</li>
      <li>Turn on <strong>Smart Alerts</strong>.</li>
      <li>Choose the thresholds and timing you want to be warned at.</li>
      <li>Allow notifications when iOS asks.</li>
    </ol>
    {{shot:alert-settings}}

    <h2>Alerts follow tracker calculations</h2>
    <p>If you edit a trip, change the tracker window, or close an ongoing trip, AtlasDays recalculates the tracker and schedules eligible alerts from the updated result.</p>

    <h2>Notification permission is separate</h2>
    <p>A tracker can have alerts configured while notifications are disabled in iOS. Open <strong>Settings → Notifications</strong> on the device if AtlasDays cannot deliver them.</p>

    <h2>Smart Alerts and Auto-Detect are different</h2>
    <p>Smart Alerts concern tracker thresholds. Auto-Detect notifications concern possible new border crossings. Each has its own purpose and settings.</p>

    <div class="callout"><p><strong>Smart Alerts require AtlasDays Pro.</strong> The tracker itself can still be reviewed without alerts.</p></div>

    <section class="if-needed">
      <h2>If an alert did not appear</h2>
      <p>Check AtlasDays notification permission, confirm Smart Alerts are on for the intended tracker, and verify that its current total actually crossed the configured milestone.</p>
    </section>
    """,
    next_steps=[
        ("trackers-and-limits", "Confirm the calculation that drives each milestone."),
        ("auto-detect-trips", "Configure separate notifications for possible new trips."),
        ("widgets", "Monitor the tracker without waiting for a notification."),
    ],
    synonyms=["notification", "threshold", "reminder", "alert not working", "milestone", "limit warning", "alert", "warning", "notify me"],
    shots=[
        shot("alert-settings", "tracker-alerts", "Directly after the steps, the full alert settings screen", "Smart Alert settings screen", priority="p0", crop="screen"),
    ],
)

add(
    "widgets",
    "Home Screen Widgets",
    "trackers-limits",
    "Add AtlasDays tracker and world-map widgets to the iPhone Home Screen and choose what each widget displays.",
    """
    <p class="article-answer">Add AtlasDays from the iOS widget gallery, choose a Tracker or World Map layout, then configure the placed widget when needed.</p>

    <h2>Add a widget</h2>
    <ol>
      <li>Long-press an empty area of the Home Screen until it enters editing mode.</li>
      <li>Tap <strong>+</strong> and search for <strong>AtlasDays</strong>.</li>
      <li>Choose Tracker or World Map, then swipe through the available sizes.</li>
      <li>Tap <strong>Add Widget</strong> and place it.</li>
    </ol>
    {{shot:widget-gallery}}

    <h2>Choose a tracker</h2>
    <p>Long-press a placed Tracker widget, choose <strong>Edit Widget</strong>, and select the tracker. Each widget remembers its own selection, so several trackers can appear together.</p>
    {{shot:widget-edit}}

    <h2>Understand refresh timing</h2>
    <p>AtlasDays writes a new widget snapshot when relevant data changes, and iOS decides when the Home Screen redraws it. Open AtlasDays once after installing it or after a large edit so the widget has current data to draw.</p>

    <h2>Free and Pro layouts</h2>
    <p>The small Tracker Status widget and all World Map sizes are available with the free app. Medium and large Tracker Trend layouts, including charts and forecasts, require AtlasDays Pro.</p>

    <section class="if-needed">
      <h2>If a widget is blank or stale</h2>
      <p>Open AtlasDays once, confirm the selected tracker still exists, and wait for iOS to refresh the widget. For a differing count, compare the widget’s tracker selection with the tracker inside the app.</p>
    </section>
    """,
    next_steps=[
        ("create-a-tracker", "Create the tracker a status widget should display."),
        ("trackers-and-limits", "Understand the count shown by the widget."),
        ("atlasdays-pro", "Compare free widgets with Pro Tracker Trend layouts."),
    ],
    synonyms=["widget blank", "widget stale", "home screen", "edit widget", "world map widget", "tracker widget", "widget not updating", "lock screen"],
    shots=[
        shot("widget-gallery", "widgets-gallery", "Directly after the numbered steps", "iOS widget gallery showing AtlasDays Tracker and World Map widgets", priority="p0", crop="screen"),
        shot("widget-edit", "widgets-edit", "In the Choose a tracker section, on Edit Widget", "Edit Widget sheet with the tracker picker", priority="p0", crop="control"),
    ],
)

add(
    "photo-import",
    "Photo Import",
    "import-export",
    "Use photo location metadata to suggest AtlasDays trips, then review dates, countries, duplicates, and overlaps before saving.",
    """
    <p class="article-answer">Photo Import scans location information in your photo library on the device, groups evidence into suggested trips, and lets you review everything before saving.</p>

    <h2>Start Photo Import</h2>
    <ol>
      <li>Open <strong>Settings → Import → Photos</strong>.</li>
      <li>Choose the date range and allow Photos access if requested.</li>
      <li>Start the scan and keep AtlasDays open while it examines the selected library.</li>
      <li>Review the proposed trips before saving.</li>
    </ol>
    {{shot:photo-setup}}

    <h2>What AtlasDays examines</h2>
    <p>AtlasDays uses photo timestamps and embedded location coordinates when available. The scan and country resolution happen on your device; the photos themselves are not uploaded to AtlasDays.</p>
    {{shot:photo-scan}}

    <h2>Review every proposal</h2>
    <p>Check the country or US state, start and end dates, and any duplicate or overlap warning. A photo’s location is evidence, not proof of the exact moment you crossed a border.</p>
    {{shot:photo-review}}

    <h2>Handle gaps conservatively</h2>
    <p>Photos without location information cannot support a suggestion. Long gaps between geotagged photos may also produce boundaries that need manual correction. Edit the saved trip in Timeline when better evidence is available.</p>

    <section class="if-needed">
      <h2>If no trips are found</h2>
      <p>Confirm AtlasDays can access the intended photos, choose a period containing geotagged images, and check that location was enabled when those photos were taken.</p>
    </section>
    """,
    next_steps=[
        ("history-and-import", "Choose an honest precision for suggestions with uncertain boundaries."),
        ("auto-detect-trips", "Detect future travel without rescanning old photos."),
        ("privacy-location-and-sync", "Review how Photos and location permissions are used."),
    ],
    synonyms=["scan photos", "photo location", "geotag", "no photos found", "duplicate import", "photo privacy", "photos", "photo library", "found nothing", "missed trips"],
    shots=[
        shot("photo-setup", "import-photos", "Directly after the numbered steps", "Photo Import setup with date-range options", priority="p0", crop="screen"),
        shot("photo-scan", "import-photos-scanning", "End of the What AtlasDays examines section", "Photo Import scan in progress", priority="p1", crop="control"),
        shot("photo-review", "import-photos-review", "In the Review every proposal section", "Photo Import review with proposed trips and warnings", priority="p0", crop="screen"),
    ],
)

add(
    "flighty-import",
    "Flighty Import",
    "import-export",
    "Import a Flighty CSV into AtlasDays and review the stays, transit days, and overnight travel inferred from its flights.",
    """
    <p class="article-answer">Export your flight history from Flighty as CSV, select it in AtlasDays, and review the proposed trips before saving.</p>

    <h2>Export from Flighty</h2>
    <p>Export your flight history from Flighty as CSV and save it somewhere the iOS Files picker can reach, such as iCloud Drive or On My iPhone.</p>

    <h2>Import into AtlasDays</h2>
    <ol>
      <li>Open <strong>Settings → Import → Flighty</strong>.</li>
      <li>Tap <strong>Select Flighty CSV</strong> and choose the exported file.</li>
      <li>Wait for AtlasDays to build its preview.</li>
      <li>Review the proposed stays, Transit records, overnight cases, duplicates, and overlaps.</li>
      <li>Save only the rows you want in Timeline.</li>
    </ol>
    {{shot:flighty-setup}}

    <h2>How flights become trips</h2>
    <p>Arrival and departure airports provide evidence for a stay, while connections may become Transit. Overnight and closely connected flights can require judgment, so compare the preview with your actual entry into each country.</p>
    {{shot:flighty-review}}

    <h2>Review US states</h2>
    <p>When airport information supports a US state, AtlasDays can propose it. Confirm the state before saving if you rely on state-specific tracking.</p>

    <section class="if-needed">
      <h2>If the file is rejected</h2>
      <p>Create a fresh Flighty CSV export and select that original file. A spreadsheet that has resaved or rearranged the export may no longer match Flighty’s format.</p>
    </section>
    """,
    next_steps=[
        ("history-and-import", "Review the modes assigned to inferred stays and connections."),
        ("photo-import", "Use a second on-device evidence source for older travel."),
        ("csv-import", "Import a manually prepared travel-history file instead."),
    ],
    synonyms=["import flights", "flighty csv", "airport transit", "overnight flight", "flight history"],
    shots=[
        shot("flighty-setup", "import-flighty", "Directly after the Import into AtlasDays steps", "Import from Flighty setup screen", priority="p0", crop="screen"),
        shot("flighty-review", "import-flighty-review", "End of the How flights become trips section", "Flighty Import preview with stays, transit, and warnings", priority="p0", crop="screen"),
    ],
)

add(
    "csv-import",
    "CSV Import",
    "import-export",
    "Import a prepared CSV travel history into AtlasDays and review valid rows, errors, duplicates, and overlaps before saving.",
    """
    <p class="article-answer">Prepare a header-based CSV, choose it under Settings → Import → CSV, and resolve the preview before saving any trips.</p>

    <h2>Import the file</h2>
    <ol>
      <li>Open <strong>Settings → Import → CSV</strong>.</li>
      <li>Use the example or format reference to prepare the file.</li>
      <li>Select the CSV from Files.</li>
      <li>Review valid rows, invalid rows, duplicates, and overlap warnings.</li>
      <li>Import the rows you accept.</li>
    </ol>
    {{shot:csv-setup}}

    <h2>Fix errors in the source file</h2>
    <p>The preview reports a row number and reason when it cannot resolve a country, state, date, or required header. Correct that row in the CSV and import the file again.</p>

    <h2>Warnings are review prompts</h2>
    <p>A duplicate can repeat a trip already in Timeline. An overlap can be legitimate or can represent two versions of the same stay. Check the dates and places rather than accepting every row automatically.</p>
    {{shot:csv-review}}

    <h2>Only saving changes your Timeline</h2>
    <p>Selecting a file and viewing the preview does not add trips. AtlasDays writes the accepted rows only after the final import action.</p>

    <section class="if-needed">
      <h2>If every row is invalid</h2>
      <p>Confirm the first row contains a <strong>Country</strong> header and check the exact date formats. See the CSV Format Reference for supported columns and examples.</p>
    </section>
    """,
    next_steps=[
        ("csv-format-reference", "Check supported headers, date formats, states, and examples."),
        ("history-and-import", "Understand how imported precision affects totals."),
        ("export-and-reports", "Create an AtlasDays CSV or spreadsheet from an existing record."),
    ],
    synonyms=["csv error", "row invalid", "spreadsheet import", "template", "duplicate", "overlap warning", "missing country column"],
    shots=[
        shot("csv-setup", "import-csv", "Directly after the numbered steps", "CSV Import setup and example-file controls", priority="p0", crop="screen"),
        shot("csv-review", "import-csv-review", "End of the Warnings are review prompts section", "CSV Import preview containing valid, invalid, duplicate, and overlap rows", priority="p0", crop="screen"),
    ],
)

add(
    "csv-format-reference",
    "CSV Format Reference",
    "import-export",
    "Reference the supported AtlasDays CSV headers, exact-date and year formats, US states, Transit, purposes, notes, and examples.",
    """
    <p class="article-answer">Only the <strong>Country</strong> column is required. AtlasDays finds supported columns by header name, so their order does not matter.</p>

    <h2>Recommended headers</h2>
    <p><code>Country,State,Start Date,End Date,Purpose,Notes</code></p>
    <ul>
      <li><strong>Country:</strong> English country name, ISO two-letter code, or a recognized common alias.</li>
      <li><strong>State:</strong> optional US state name, postal abbreviation, or ISO subdivision code such as <code>US-CA</code>.</li>
      <li><strong>Start Date / End Date:</strong> exact date, year, or empty according to the rules below.</li>
      <li><strong>Purpose:</strong> Tourism, Business, Medical, Transit, or Personal; multiple non-Transit purposes may be comma-separated.</li>
      <li><strong>Notes:</strong> optional text.</li>
    </ul>
    {{shot:csv-reference}}

    <h2>Date formats</h2>
    <h3>Exact Dates</h3>
    <p>Use <code>yyyy-mm-dd</code> in both date columns. Leave End Date empty only for an ongoing trip.</p>
    <h3>Year</h3>
    <p>Use a four-digit year in Start Date. End Date can hold a year, or stay empty to mean the same year. A range spanning several years becomes one year-only record per year.</p>
    <h3>Unknown</h3>
    <p>Leave both date cells empty. The country is preserved as a visit without numeric days.</p>

    <h2>US state rows</h2>
    <p>Use State only for a United States trip. If one US visit covered several states and you need state-level records, use one row per state. A plain US row is valid for country-level tracking.</p>

    <h2>Transit</h2>
    <p>Put <code>Transit</code> in Purpose when you did not enter the country. Transit is exclusive: do not combine it with Tourism, Business, or another purpose.</p>

    <h2>Example</h2>
    <pre><code>Country,State,Start Date,End Date,Purpose,Notes
France,,2026-03-01,2026-03-05,Tourism,
United States,CA,2026-04-10,2026-04-15,Business,Conference
Japan,,2024,,Tourism,Dates not known
United Arab Emirates,,2026-05-01,2026-05-01,Transit,Airport connection</code></pre>

    <h2>Delimiter and quoting</h2>
    <p>AtlasDays recognizes comma, semicolon, and tab-delimited files from the header row. Quote fields that contain the delimiter or a line break according to normal CSV rules.</p>

    <section class="if-needed">
      <h2>If a value is not recognized</h2>
      <p>Use an ISO country code, an unambiguous English country name, ISO dates, and a standard US state name or code. Keep the original row number so it is easy to compare with the import preview.</p>
    </section>
    """,
    next_steps=[
        ("csv-import", "Return to the short import procedure and preview the corrected file."),
        ("export-and-reports", "Export an existing AtlasDays record in a reusable format."),
    ],
    synonyms=["csv columns", "csv headers", "date format", "iso date", "country code", "state code", "semicolon", "tab separated", "sample csv"],
    shots=[
        shot("csv-reference", "import-csv", "End of the Recommended headers section", "CSV Import example and template controls", priority="p1", crop="control"),
    ],
)

add(
    "export-and-reports",
    "Export and Reports",
    "import-export",
    "Export AtlasDays travel history as an AtlasDays CSV, configurable spreadsheet, or PDF report.",
    """
    <p class="article-answer">Open Settings → Export, choose the format that fits the purpose, configure its period and options, preview it, and share the finished file.</p>

    <h2>Choose an export</h2>
    <ul>
      <li><strong>AtlasDays CSV</strong> is designed for backup or moving trip data back into AtlasDays.</li>
      <li><strong>Spreadsheet</strong> creates a configurable Excel or CSV file for analysis and record keeping.</li>
      <li><strong>PDF</strong> creates a readable travel report for review or sharing.</li>
    </ul>
    {{shot:export-hub}}

    <h2>Configure the period and detail</h2>
    <p>Choose the date range, language, date format, and the columns or report options you want. Decide whether state, purpose, and notes belong in the file before you share it, because an export can carry more detail than the recipient needs.</p>
    {{shot:spreadsheet-config}}

    <h2>Preview before sharing</h2>
    <p>The preview shows what the export will contain. If a trip is missing or needs correction, return to Timeline, edit the source record, and create the export again.</p>
    {{shot:pdf-preview}}

    <h2>Exports do not change the app</h2>
    <p>Creating or sharing an export does not remove, mark, or alter trips. The exported file is a separate copy.</p>

    <div class="callout"><p><strong>CSV, Spreadsheet, and PDF export require AtlasDays Pro.</strong> Keep exported files secure because they may contain detailed travel history.</p></div>

    <section class="if-needed">
      <h2>If the file omits a trip</h2>
      <p>Check the export period and then inspect the trip in Timeline. Approximate trips may be represented differently from exact trips depending on the chosen format.</p>
    </section>
    """,
    next_steps=[
        ("icloud-sync-and-restore", "Understand how sync differs from keeping an export copy."),
        ("csv-import", "Bring a compatible travel-history CSV into AtlasDays."),
        ("atlasdays-pro", "Review the Pro features required for exports."),
    ],
    synonyms=["backup", "pdf", "excel", "xlsx", "csv export", "report", "share travel history", "visa application", "export", "spreadsheet", "download my data", "print"],
    shots=[
        shot("export-hub", "export", "End of the Choose an export section", "Export hub with AtlasDays CSV, Spreadsheet, and PDF options", priority="p0", crop="screen"),
        shot("spreadsheet-config", "export-spreadsheet", "End of the Configure the period and detail section", "Spreadsheet export configuration with format and date options", priority="p0", crop="screen"),
        shot("pdf-preview", "export-pdf", "In the Preview before sharing section", "PDF travel report preview", priority="p0", crop="screen"),
    ],
)

add(
    "privacy-location-and-sync",
    "Privacy and Permissions",
    "sync-privacy-data",
    "Understand AtlasDays local-first travel data, Photos and location access, notifications, analytics, and iCloud storage.",
    """
    <p class="article-answer">AtlasDays keeps travel history in the app’s data store. Photos are scanned on device, location access is optional, and iCloud Sync stores app data in your private iCloud account when enabled.</p>

    <h2>Travel history</h2>
    <p>Your trips, trackers, and notes are app data. With iCloud Sync off they remain on the device. With it on, CloudKit keeps supported records in your private iCloud account and synchronizes them across your devices.</p>

    <h2>Photos</h2>
    <p>Photo Import reads timestamps and embedded coordinates from the Photos library you permit. Country resolution happens on the device; AtlasDays does not upload the photos themselves.</p>

    <h2>Location</h2>
    <p>Auto-Detect Trips uses low-power location monitoring when you explicitly enable it and grant Always location access. It creates suggestions for review rather than silently writing completed trips.</p>

    <h2>Notifications</h2>
    <p>Notifications are used for enabled Auto-Detect events and Smart Alerts. You can disable the related feature in AtlasDays or change notification permission in iOS Settings.</p>

    <h2>Review or revoke access</h2>
    <p>Open iOS Settings for AtlasDays to change Photos, Location, and Notifications permission at any time. A permission only appears in that list once AtlasDays has asked for it, so a feature you have never opened will not be listed yet.</p>
    {{shot:privacy-permissions}}

    <h2>Usage statistics</h2>
    <p>AtlasDays sends anonymous usage statistics to an independent analytics provider in the European Union, so it can see how the app is used and where it can be better. There is no account and nothing that identifies you personally.</p>
    <p>These statistics cover actions taken in the app, your settings, basic device and app information, and your approximate country. Counts, such as how many trips you have, are sent as ranges rather than exact numbers. They never include your trips, dates, notes, photos, or coordinates.</p>
    <p>AtlasDays carries no advertising, uses no advertising identifier, and asks for no tracking permission. The <a href="/privacy">Privacy Policy</a> is the full statement.</p>
    {{shot:privacy-overview}}

    <section class="if-needed">
      <h2>If a feature stops working</h2>
      <p>Check the permission it depends on in iOS Settings. Photo Import needs Photos access, Auto-Detect needs Always location, and alerts need notifications. Each keeps working normally once access is allowed again.</p>
    </section>
    """,
    next_steps=[
        ("auto-detect-trips", "See exactly what location access enables."),
        ("photo-import", "Understand the on-device photo scan and review flow."),
        ("icloud-sync-and-restore", "Review private iCloud storage and device sync."),
    ],
    synonyms=["privacy", "location permission", "photos permission", "analytics", "usage statistics", "telemetry", "notification permission", "data storage", "private", "does it track me", "data collection", "tracking", "permissions", "opt out", "offline"],
    shots=[
        shot("privacy-overview", "privacy", "End of the Analytics section", "AtlasDays privacy overview showing data and permission summaries", priority="p0", crop="screen"),
        shot("privacy-permissions", "ios-settings-atlasdays", "End of the Review or revoke access section", "iOS Settings page for AtlasDays listing its Location, Photos, and other permissions", priority="p1", crop="control"),
    ],
)

add(
    "auto-detect-trips",
    "Auto-Detect Trips",
    "sync-privacy-data",
    "Enable AtlasDays Auto-Detect Trips, grant the required location access, and review border-crossing suggestions.",
    """
    <p class="article-answer">Auto-Detect uses low-power background location monitoring to notice possible new travel and add a suggestion to Timeline for your review.</p>

    <h2>Turn on Auto-Detect</h2>
    <ol>
      <li>Open <strong>Settings → Auto-Detect Trips</strong>.</li>
      <li>Turn on <strong>Auto-Detect Trips</strong>.</li>
      <li>Grant Always location access when iOS asks. The toggle remains off until background access is available.</li>
      <li>Optionally turn on notifications for new country detections.</li>
    </ol>
    {{shot:auto-detect-settings}}

    <h2>Review suggestions</h2>
    <p>A suggestion appears in Timeline as a card above your saved trips, showing the detected country and the dates AtlasDays inferred. It is evidence of movement, not a finished travel record. Open it, confirm the country or US state and the boundary dates, then accept, edit, or ignore it. Ignoring one does not stop you adding the trip by hand later.</p>

    <h2>Ignore places you do not want suggested</h2>
    <p>Add countries to the Ignore list when recurring border proximity produces suggestions you never need. Pro users can also ignore individual US states. Ignored places can still be added manually.</p>

    <h2>Auto-Detect is not continuous GPS recording</h2>
    <p>The feature uses low-power system location events rather than storing a detailed route. Detection timing depends on iOS, geography, connectivity, and the available boundary signal.</p>

    <section class="if-needed">
      <h2>If no suggestion appears</h2>
      <p>Check that Auto-Detect is on, Location is set to Always, the place is not ignored, and AtlasDays notifications are allowed if you expect a notification. You can always add the trip manually.</p>
    </section>
    """,
    next_steps=[
        ("timeline-and-calendar", "Review, edit, or replace a detection in Timeline."),
        ("privacy-location-and-sync", "Understand how location and notification permission are used."),
        ("smart-alerts", "Configure separate notifications for tracker thresholds."),
    ],
    synonyms=["automatic trip", "border crossing", "always location", "location notification", "detection missing", "ground crossing", "automatic tracking", "background location", "battery", "always allow", "detect trips", "location permission"],
    shots=[
        shot("auto-detect-settings", "auto-detect", "Directly after the numbered steps", "Auto-Detect Trips settings with location and notification controls", priority="p0", crop="screen"),
    ],
)

add(
    "icloud-sync-and-restore",
    "iCloud Sync and Restore",
    "sync-privacy-data",
    "Set up AtlasDays iCloud Sync, check its status, and understand new-device, reinstall, and missing-data behavior.",
    """
    <p class="article-answer">When iCloud Sync is enabled, AtlasDays stores trips and trackers in your private iCloud account and keeps them synchronized across devices using the same Apple Account.</p>

    <h2>Set up a new device</h2>
    <ol>
      <li>Sign in to the same Apple Account and make sure iCloud Drive is available.</li>
      <li>Install AtlasDays and open <strong>Settings → iCloud Sync</strong>.</li>
      <li>Confirm iCloud Sync is on and review the displayed status.</li>
      <li>Leave AtlasDays open briefly while records arrive.</li>
    </ol>
    {{shot:icloud-status}}

    <h2>After reinstalling AtlasDays</h2>
    <p>Trips and trackers held in iCloud come back once the app reconnects to its iCloud store, which can take a few minutes on first launch. Device-specific permissions, widget configuration, and some preferences have to be set again.</p>

    <h2>Understand the status</h2>
    <p>The iCloud Sync screen reports whether AtlasDays is checking, syncing, waiting, synced, not signed in, or using local storage. Enabling or disabling sync can require closing AtlasDays from the app switcher and reopening it.</p>

    <h2>If data appears missing</h2>
    <ol>
      <li>Do not reset or delete the app data while investigating.</li>
      <li>Confirm the Apple Account and iCloud availability.</li>
      <li>Check the iCloud Sync status and data count.</li>
      <li>Keep the app open on a stable connection and check again.</li>
      <li>Contact support before making destructive changes if another device still has the expected record.</li>
    </ol>

    <h2>Sync is not the same as an export</h2>
    <p>Sync keeps one evolving record across devices. An export is a separate file you control and can retain as a point-in-time copy.</p>

    <section class="if-needed">
      <h2>If the screen says AtlasDays is not syncing</h2>
      <p>Follow the status message first. Check Apple Account sign-in, available iCloud storage, network access, and whether the app requests a restart after changing the toggle.</p>
    </section>
    """,
    next_steps=[
        ("export-and-reports", "Keep a separate file copy of important travel records."),
        ("privacy-location-and-sync", "Review what private iCloud storage means for AtlasDays data."),
        ("delete-and-reset", "Understand destructive actions before removing local or synced records."),
    ],
    synonyms=["missing data", "new phone", "restore", "reinstall", "backup", "icloud status", "sync not working", "same apple account", "new iphone", "transfer to new device", "lost trips"],
    shots=[
        shot("icloud-status", "icloud-sync", "Directly after the Set up a new device steps", "iCloud Sync settings showing status, last activity, and data count", priority="p0", crop="screen"),
    ],
)

add(
    "delete-and-reset",
    "Delete Data or Start Over",
    "sync-privacy-data",
    "Delete selected AtlasDays data or reset the app after understanding what the action removes and whether iCloud is involved.",
    """
    <p class="article-answer">Use Settings → Delete or Reset only after choosing the narrowest action that fits. Export important records first when you may need them later.</p>

    <h2>Delete individual records first</h2>
    <p>For one trip, open it in Timeline and choose <strong>Delete Trip</strong>. For one tracker, open its settings and use the tracker delete action. This preserves the rest of the app.</p>

    <h2>Use Delete or Reset for larger changes</h2>
    <p>Open <strong>Settings → Delete or Reset</strong> to see the available trip, tracker, and full-reset actions. Read the confirmation carefully; each option lists what it removes.</p>
    {{shot:delete-actions}}

    <h2>Consider iCloud before confirming</h2>
    <p>With iCloud Sync enabled, deleting synced records can affect the shared record on your other devices. A full reset can also remove preferences and device setup that a normal trip deletion leaves alone.</p>
    {{shot:delete-confirmation}}

    <div class="callout"><p><strong>Deletion may be irreversible after the confirmation completes.</strong> An exported file is separate from the app and is not removed by resetting AtlasDays.</p></div>

    <section class="if-needed">
      <h2>If you are trying to fix sync</h2>
      <p>Do not reset first. Check iCloud status and contact support while a device still contains the expected data.</p>
    </section>
    """,
    next_steps=[
        ("icloud-sync-and-restore", "Check sync status before removing data during a recovery attempt."),
        ("export-and-reports", "Create a separate copy before a destructive action."),
        ("getting-started", "Set up AtlasDays again after an intentional reset."),
    ],
    synonyms=["reset app", "delete all", "erase data", "start over", "remove trips", "factory reset", "erase", "reset", "delete everything", "remove all data"],
    shots=[
        shot("delete-actions", "delete-reset", "In the Use Delete or Reset for larger changes section", "Delete or Reset screen listing available actions", priority="p0", crop="screen"),
        shot("delete-confirmation", "delete-reset-confirm", "Directly above the warning callout", "Destructive confirmation explaining what will be deleted", priority="p0", crop="control"),
    ],
)

add(
    "atlasdays-pro",
    "AtlasDays Pro",
    "settings-purchases",
    "Compare free AtlasDays with Pro features including unlimited trackers, Smart Alerts, exports, US states, and Tracker Trend widgets.",
    """
    <p class="article-answer">AtlasDays is usable for free with one tracker. Pro unlocks advanced monitoring, exports, state-level records, and richer tracker widgets.</p>

    <h2>Included for free</h2>
    <ul>
      <li>Trip history, Timeline, Calendar, Dashboard, and visited-country map</li>
      <li>One tracker</li>
      <li>Photo, CSV, and Flighty import review</li>
      <li>Small Tracker Status widget and all World Map widget sizes</li>
      <li>Optional iCloud Sync</li>
    </ul>

    <h2>Pro unlocks</h2>
    <ul>
      <li>Unlimited trackers and Smart Alerts</li>
      <li>US state tracking</li>
      <li>AtlasDays CSV, Spreadsheet, and PDF exports</li>
      <li>Medium and large Tracker Trend widgets with charts and forecasts</li>
      <li>Additional personalization options, listed in full on the upgrade screen</li>
    </ul>
    {{shot:pro-paywall}}
    <p>A Pro feature you have not unlocked shows the same upgrade route where you meet it.</p>
    {{shot:pro-locked}}

    <h2>Purchase and restore</h2>
    <p>Open the AtlasDays Pro screen from Settings or a locked feature. Complete the purchase through Apple. If you already purchased with the same Apple Account, use <strong>Restore Purchases</strong>.</p>

    <h2>If Pro is not recognized</h2>
    <p>Confirm the App Store Apple Account, check connectivity, reopen AtlasDays, and try Restore Purchases. Apple manages billing and the purchase record.</p>

    <section class="if-needed">
      <h2>Before purchasing</h2>
      <p>Use the current upgrade screen as the authoritative feature and price list, because availability and pricing can vary by storefront and change over time.</p>
    </section>
    """,
    next_steps=[
        ("create-a-tracker", "Use unlimited trackers for separate visa and residency questions."),
        ("export-and-reports", "Create the Pro export format that fits your purpose."),
        ("widgets", "Compare free widgets with Pro Tracker Trend layouts."),
    ],
    synonyms=["upgrade", "purchase", "restore purchase", "subscription", "lifetime", "price", "free version", "pro features", "cost", "how much", "cancel subscription", "manage subscription", "promo code", "redeem", "free trial", "free vs pro", "refund"],
    shots=[
        shot("pro-paywall", "pro-paywall", "End of the Pro unlocks list", "Current AtlasDays Pro upgrade screen with feature list", priority="p0", crop="screen"),
        shot("pro-locked", "pro-locked", "End of the Pro unlocks list, on a locked feature", "A locked Pro feature prompting an upgrade", priority="p1", crop="control"),
    ],
)

add(
    "languages",
    "Languages and Country Names",
    "settings-purchases",
    "Choose the AtlasDays interface language, country-name language, and language used for exports and share cards.",
    """
    <p class="article-answer">AtlasDays separates the app interface language from country names and from the language chosen when exporting or sharing.</p>

    <h2>Change the app language</h2>
    <ol>
      <li>Open <strong>Settings → Language</strong>.</li>
      <li>Choose the app interface language.</li>
      <li>Follow the restart instruction when shown so the interface reloads consistently.</li>
    </ol>
    {{shot:language-settings}}

    <h2>Choose country names separately</h2>
    <p>On the same screen, choose <strong>Country Names</strong>. It can follow the app language or use a different supported language, which is useful when you read the interface in one language but want country names in another.</p>
    {{shot:language-country}}

    <h2>Exports and share cards</h2>
    <p>Spreadsheet, PDF, and share-card screens can offer their own language choice. Changing that output language does not change the app interface.</p>

    <section class="if-needed">
      <h2>If some text has not changed</h2>
      <p>Close and reopen the relevant screen. For an interface-language change, follow the app’s restart prompt.</p>
    </section>
    """,
    next_steps=[
        ("export-and-reports", "Choose the language and date format of exported records."),
        ("appearance-and-personalization", "Adjust the visual presentation separately from language."),
    ],
    synonyms=["change language", "country names", "translation", "export language", "share card language", "language", "translate"],
    shots=[
        shot("language-settings", "settings-language", "End of the Change the app language steps", "Language settings showing interface and country-name choices", priority="p0", crop="screen"),
        shot("language-country", "settings-language-country-names", "In the Choose country names separately section", "Country Names language picker", priority="p0", crop="control"),
    ],
)

add(
    "appearance-and-personalization",
    "Appearance and Personalization",
    "settings-purchases",
    "Change the AtlasDays theme, accent color, background wash, and app icon without changing travel data or calculations.",
    """
    <p class="article-answer">Appearance settings change how AtlasDays looks. They do not change trips, counted days, tracker rules, or exports unless an export screen offers its own appearance option.</p>

    <h2>Choose a theme</h2>
    <p>Open <strong>Settings → Appearance</strong> and choose the available light, dark, or device-following behavior.</p>
    {{shot:appearance-settings}}

    <h2>Personalize AtlasDays</h2>
    <p>Use the personalization settings to select an accent color, background wash, and app icon. The map uses the chosen visual treatment while preserving the same highlighted places.</p>
    {{shot:appearance-icon}}

    <h2>Widgets follow their supported appearance</h2>
    <p>AtlasDays prepares widget map snapshots for light and dark appearances. iOS controls which version appears with the Home Screen environment.</p>

    <section class="if-needed">
      <h2>If an app icon does not update immediately</h2>
      <p>Return to the Home Screen and allow iOS a moment to refresh it. Reopen AtlasDays if the old icon remains.</p>
    </section>
    """,
    next_steps=[
        ("widgets", "See how AtlasDays content appears on the Home Screen."),
        ("languages", "Change interface and country-name language independently."),
    ],
    synonyms=["dark mode", "light mode", "theme", "accent color", "app icon", "background wash", "personalize"],
    shots=[
        shot("appearance-settings", "settings-appearance", "End of the Choose a theme section", "Appearance and personalization settings with theme and accent choices", priority="p0", crop="screen"),
        shot("appearance-icon", "settings-app-icon", "In the Personalize AtlasDays section, on the app icon picker", "App icon picker", priority="p1", crop="control"),
    ],
)

add(
    "ipad",
    "AtlasDays on iPad",
    "settings-purchases",
    "Use AtlasDays two-pane Timeline and Settings layouts and expanded Dashboard map on iPad.",
    """
    <p class="article-answer">AtlasDays uses the extra iPad space for side-by-side navigation and detail while keeping the same trips, trackers, and counting rules as iPhone.</p>

    <h2>Timeline</h2>
    <p>The Timeline can keep the trip list or calendar visible beside the selected trip’s detail. Selecting another trip updates the detail pane without replacing the whole screen.</p>
    {{shot:ipad-timeline}}

    <h2>Settings</h2>
    <p>Settings uses a sidebar and detail pane. Choose Import, Export, Appearance, Language, iCloud Sync, or another destination on the left and work in the right pane.</p>
    {{shot:ipad-settings}}

    <h2>Dashboard and map</h2>
    <p>The Dashboard uses the wider canvas for its cards and an expanded map. The selected period, visit rules, and day totals remain identical to iPhone.</p>
    {{shot:ipad-dashboard}}

    <h2>Sync between iPhone and iPad</h2>
    <p>Enable iCloud Sync on devices using the same Apple Account when you want supported trips and trackers to stay aligned.</p>

    <section class="if-needed">
      <h2>If a pane looks empty</h2>
      <p>Select a trip or Settings destination in the sidebar. Rotate the iPad or widen the window if Stage Manager has reduced the available width.</p>
    </section>
    """,
    next_steps=[
        ("timeline-and-calendar", "Learn the records shown in the iPad Timeline panes."),
        ("dashboard-and-map", "Understand the same Dashboard and map rules on a wider screen."),
        ("getting-started", "Set up the shared record before moving between devices."),
    ],
    synonyms=["tablet", "split view", "two pane", "sidebar", "stage manager", "ipad settings", "ipad", "large screen"],
    shots=[
        shot("ipad-timeline", "ipad-timeline", "In the Timeline section", "AtlasDays iPad Timeline with list and trip detail panes", "iPad Pro 13-inch", priority="p0", crop="screen"),
        shot("ipad-settings", "ipad-settings", "In the Settings section", "AtlasDays iPad Settings with sidebar and detail pane", "iPad Pro 13-inch", priority="p0", crop="screen"),
        shot("ipad-dashboard", "ipad-dashboard", "In the Dashboard and map section", "AtlasDays iPad Dashboard with expanded map", "iPad Pro 13-inch", priority="p1", crop="screen"),
    ],
)



def main() -> int:
    if len(ARTICLES) != 24:
        raise SystemExit(f"Expected 24 Help articles, found {len(ARTICLES)}")
    title_by_slug = {str(article["slug"]): str(article["title"]) for article in ARTICLES}
    if len(title_by_slug) != len(ARTICLES):
        raise SystemExit("Duplicate Help slug")
    for article in ARTICLES:
        for target, _ in article["next"]:
            if target not in title_by_slug:
                raise SystemExit(f"{article['slug']}: unknown next article {target}")
        CONTENT.mkdir(parents=True, exist_ok=True)
        (CONTENT / f"{article['slug']}.html").write_text(wrap_content(article), encoding="utf-8")

    article_path = DATA / "articles.json"
    payload = json.loads(article_path.read_text(encoding="utf-8"))
    non_help = [item for item in payload["articles"] if item.get("section") != "help"]
    help_records = [record(article, title_by_slug) for article in ARTICLES]
    payload["articles"] = help_records + non_help
    article_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    route_path = DATA / "routes.json"
    routes = json.loads(route_path.read_text(encoding="utf-8"))
    retained = [item for item in routes["routes"] if not str(item["path"]).startswith("help/")]
    help_routes = [
        {"path": "help/index.html", "canonical": "https://atlasdays.app/help/", "lastmod": UPDATED_ISO, "priority": "0.7", "indexable": True}
    ] + [
        {
            "path": f"help/{article['slug']}.html",
            "canonical": f"https://atlasdays.app/help/{article['slug']}",
            "lastmod": UPDATED_ISO,
            "priority": "0.7" if article["category"] != "settings-purchases" else "0.6",
            "indexable": True,
        }
        for article in ARTICLES
    ]
    insert_at = next((index for index, item in enumerate(retained) if str(item["path"]).startswith("learn/")), len(retained))
    routes["routes"] = retained[:insert_at] + help_routes + retained[insert_at:]
    route_path.write_text(json.dumps(routes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Help articles now use product screenshots exclusively. Keep the archived
    # generic assets until their final inventory is approved, but remove them
    # from the active illustration plan so audits do not expect inline markers.
    image_plan_path = ROOT / "article-image-plan.json"
    image_plan = json.loads(image_plan_path.read_text(encoding="utf-8"))
    image_plan["articles"] = {
        key: value
        for key, value in image_plan.get("articles", {}).items()
        if not key.startswith("help/")
    }
    image_plan_path.write_text(
        json.dumps(image_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Rebuilt {len(ARTICLES)} Help article sources and metadata records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
