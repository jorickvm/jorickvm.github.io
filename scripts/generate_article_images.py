#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from urllib import error, request

from article_image_lib import (
    CATALOG_PATH,
    OUTPUT_ROOT,
    SITE_ROOT,
    Article,
    SectionContext,
    collapse_whitespace,
    discover_articles,
    find_section_context,
    load_env_file,
    load_plan,
    select_article_keys,
)


IMAGE_API_URL = "https://api.openai.com/v1/images/generations"

BASE_STYLE = (
    "Use a premium travel-tech editorial illustration style that fits AtlasDays: dark charcoal and cool slate as the base, "
    "deep oceanic navy depth, cyan-blue route accents, pale ice-blue surfaces, and small restrained warm highlights for contrast. "
    "The image should feel premium, modern, mobile-first, and travel-oriented: calm but not sterile, precise but not academic, "
    "aspirational without becoming generic travel-advertising fluff. Favor layered depth, subtle glow, motion, route energy, "
    "and destination atmosphere over flat icon-pack graphics. Do not make it whimsical, photoreal stock-photo-like, or cartoonish."
)

GLOBAL_AVOID = (
    "Avoid readable text, letters, words, labels, titles, map labels, typographic elements, UI screenshots, "
    "government seals, watermarks, stock-photo cliches, passport-stamp collages, fake official forms, brand logos, "
    "or cluttered layouts. Avoid stiff textbook-diagram energy, generic corporate SaaS art, or dry flat iconography. "
    "If a counting concept is needed, represent it abstractly with bars, chips, rings, windows, "
    "or markers. Minimal numerals are acceptable only when they function as an abstract threshold symbol rather than readable UI text or copy."
)

SECTION_GUIDANCE = {
    "learn": (
        "This image supports an evergreen educational travel-rule article. It should feel authoritative, "
        "clear, and SEO-friendly, with one dominant idea that still reads well on a responsive web page while still feeling like part of a premium travel brand."
    ),
    "help": (
        "This image supports product documentation for AtlasDays, a private iPhone app for trip history, "
        "visa days, and residency tracking. It should feel product-adjacent without recreating a literal app screenshot, and should still carry some travel-product personality."
    ),
}

THEME_RULES = [
    {
        "keywords": ["schengen"],
        "focus": "a recognizable Europe map, a rolling travel window, and precise travel-day counting",
        "motifs": ["Europe outline", "calendar window", "route arcs", "day-count markers"],
        "alt_focus": "Europe, a rolling calendar window, and travel-day counting motifs",
    },
    {
        "keywords": ["uk eta", "standard visitor", "uk-standard", "uk-eta", "visitor visa", "visitor"],
        "focus": "UK entry rules, trip duration, repeated visits, and border-decision context",
        "motifs": ["United Kingdom silhouette", "entry gate motif", "trip duration bars", "calendar checkpoints"],
        "alt_focus": "UK travel-rule motifs, duration bars, and trip checkpoints",
    },
    {
        "keywords": ["substantial presence", "us substantial presence", "u.s. substantial presence"],
        "focus": "U.S. tax presence, multi-year weighted counting, and residency-day analysis",
        "motifs": ["US outline", "stacked year bands", "weighted count chips", "residency threshold markers"],
        "alt_focus": "U.S. tax-presence motifs, weighted year bands, and residency-threshold markers",
    },
    {
        "keywords": ["b1/b2", "us-b1-b2", "esta", "united states", "u.s.", " us "],
        "focus": "US visitor stays, entry and exit timing, and stay-limit planning",
        "motifs": ["US outline", "arrival and departure markers", "count chips", "calendar bars"],
        "alt_focus": "US travel-day planning motifs and arrival-departure markers",
    },
    {
        "keywords": ["183-day", "tax residency", "residency"],
        "focus": "threshold counting across a year, fiscal periods, and residency-day milestones",
        "motifs": ["year grid", "threshold bar", "calendar blocks", "country presence markers"],
        "alt_focus": "yearly threshold counting, calendar blocks, and residency-day markers",
    },
    {
        "keywords": ["travel history", "passport", "visa application", "visa applications", "prove time spent", "rebuild"],
        "focus": "reconstructing or organizing travel history from documents, timelines, and evidence",
        "motifs": ["document stack", "timeline ribbon", "ticket fragments", "map pins"],
        "alt_focus": "travel-history documents, timelines, and map-pin evidence",
    },
    {
        "keywords": ["country counting", "how many countries", "layover", "countries in the world"],
        "focus": "country lists, map segmentation, transit logic, and how different counting systems disagree",
        "motifs": ["globe fragments", "country tiles", "route nodes", "comparison bands"],
        "alt_focus": "globe fragments, country tiles, and route-node comparison motifs",
    },
    {
        "keywords": ["digital nomad"],
        "focus": "long-term travel planning across multiple countries with day limits and flexible movement",
        "motifs": ["world map pins", "calendar bands", "laptop silhouette", "route lines"],
        "alt_focus": "world map pins, day-limit bands, and long-term travel planning motifs",
    },
    {
        "keywords": ["privacy", "icloud", "sync", "location"],
        "focus": "private on-device travel data, optional sync, and controlled location use",
        "motifs": ["locked device", "cloud link", "shield shape", "location pin"],
        "alt_focus": "locked-device privacy, optional cloud sync, and location-pin motifs",
    },
    {
        "keywords": ["dashboard", "map"],
        "focus": "summaries, map-based travel history, and top-level insight from trip data",
        "motifs": ["world map", "summary cards", "country highlight halo", "stat chips"],
        "alt_focus": "world map, summary cards, and country-highlight motifs",
    },
    {
        "keywords": ["tracker", "limits", "track travel days", "how-to-track-travel-days", "visa days"],
        "focus": "counting rules, rolling windows, per-stay limits, and threshold awareness",
        "motifs": ["progress bars", "window frames", "count chips", "threshold markers"],
        "alt_focus": "counting-rule motifs, threshold markers, and window frames",
    },
    {
        "keywords": ["import", "csv", "exact dates", "month & year", "month and year", "history-and-import", "getting started", "how-to-use-atlasdays"],
        "focus": "trip records moving from messy inputs into a clean, structured timeline",
        "motifs": ["calendar fragments", "CSV-like rows", "timeline cards", "route dots"],
        "alt_focus": "calendar fragments, timeline cards, and structured travel-record motifs",
    },
]

DEFAULT_THEME = {
    "focus": "travel tracking, country presence, time windows, and organized movement across places",
    "motifs": ["map pins", "calendar frames", "route lines", "count markers"],
    "alt_focus": "travel tracking, calendar frames, and route-line motifs",
}

HERO_COMPOSITION = (
    "Create the main article cover image with one dominant subject and two or three supporting elements. "
    "It should feel like a proper top-of-page hero image that can sit under the page title."
)

BODY_COMPOSITION = {
    "learn": (
        "Create a supporting body image tied to one specific section of the article. It should visualize the section's idea clearly, "
        "feel more focused than the hero, and still match the same AtlasDays editorial system."
    ),
    "help": (
        "Create a supporting body image tied to one specific section of the help article. It should clarify the feature concept or workflow "
        "from that section without turning into a literal app screenshot."
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate branded Help/Learn article images for atlasdays.app using the OpenAI Image API."
    )
    parser.add_argument("--section", choices=("all", "learn", "help"), default="all")
    parser.add_argument("--slug")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model")
    parser.add_argument("--quality", choices=("low", "medium", "high", "auto"))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show-prompts", action="store_true")
    return parser.parse_args()


def env_str(name: str, default: str) -> str:
    raw = os.environ.get(name, "").strip()
    return raw or default


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def load_settings(args: argparse.Namespace | None = None) -> dict[str, Any]:
    fmt = env_str("ATLASDAYS_IMAGE_FORMAT", "webp").lower()
    if fmt not in {"png", "jpeg", "webp"}:
        fmt = "webp"
    background = env_str("ATLASDAYS_IMAGE_BACKGROUND", "opaque").lower()
    if background not in {"opaque", "transparent", "auto"}:
        background = "opaque"
    model = args.model.strip() if args and args.model else env_str("ATLASDAYS_IMAGE_MODEL", "gpt-image-1-mini")
    quality = args.quality.strip() if args and args.quality else env_str("ATLASDAYS_IMAGE_QUALITY", "medium")
    return {
        "model": model,
        "quality": quality,
        "size": env_str("ATLASDAYS_IMAGE_SIZE", "1536x1024"),
        "output_format": fmt,
        "output_compression": clamp(env_int("ATLASDAYS_IMAGE_COMPRESSION", 72), 0, 100),
        "background": background,
        "moderation": env_str("ATLASDAYS_IMAGE_MODERATION", "auto"),
    }


def ensure_api_key(dry_run: bool) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key or dry_run:
        return api_key
    raise SystemExit(
        "OPENAI_API_KEY is missing. Copy .env.example to .env.local and paste your key there."
    )


def shorten_text(value: str, limit: int = 240) -> str:
    if len(value) <= limit:
        return value
    trimmed = value[: limit - 1].rsplit(" ", 1)[0].rstrip(",.;: ")
    return f"{trimmed}…"


def sanitize_for_image_prompt(value: str) -> str:
    return collapse_whitespace(value)


def pick_body_visual_mode(context: SectionContext, slot_id: str) -> str:
    haystack = f"{context.heading} {context.summary}".lower()
    if any(term in haystack for term in ["template", "document", "evidence", "records", "passport", "export", "copyable", "source"]):
        return "documents" if slot_id == "body-1" else "workflow"
    if any(term in haystack for term in ["common", "pitfalls", "mistakes", "tripped", "refusal", "problems", "edge", "overstay"]):
        return "scenarios"
    if any(term in haystack for term in ["how", "rolling", "workflow", "works", "check", "count", "import", "sync"]):
        return "workflow" if slot_id == "body-1" else "comparison"
    if any(term in haystack for term in ["countries", "destinations", "map", "schengen", "uk", "us", "europe"]):
        return "map-detail" if slot_id == "body-1" else "comparison"
    if any(term in haystack for term in ["preset", "tracker", "types", "options", "difference", "versus", "vs "]):
        return "cards"
    if any(term in haystack for term in ["timeline", "history", "travel history", "day counting", "year", "window"]):
        return "timeline" if slot_id == "body-1" else "comparison"
    return "focused-explainer" if slot_id == "body-1" else "comparison"


def body_mode_instruction(mode: str, slot_id: str) -> str:
    instructions = {
        "workflow": "Use a directional step-by-step composition with a clear sequence or movement through a system. Prioritize flow, transitions, and causal structure over a cover-style overview.",
        "comparison": "Use a clear side-by-side or two-to-three-panel comparison layout. Show contrasting states, outcomes, or categories rather than one single hero object.",
        "documents": "Use a tidy records-and-evidence composition: papers, cards, tickets, passports, notes, tables, or timelines arranged in a clean organized stack.",
        "scenarios": "Use two or three compact scenario vignettes or edge-case panels, making the differences between cases immediately legible.",
        "map-detail": "Use a tighter geographic composition than the hero, focusing on route logic, country relationships, or region-specific movement rather than a generic full-page map overview.",
        "cards": "Use grouped cards, tiles, or option clusters that make different tracker types, categories, or choices feel distinct and structured.",
        "timeline": "Use a timeline or calendar-based composition with one clear axis of time, windows, milestones, or period blocks.",
        "focused-explainer": "Use one tight explanatory composition centered on a single mechanism from the section, not a broad overview.",
    }
    distinctness = (
        "This body image must feel clearly different from the article hero and other body images. "
        "Do not reuse the same centered overview layout, same map scale, or same dominant object from the hero."
    )
    if slot_id == "body-2":
        distinctness += " Give this slot a noticeably different visual grammar from body-1 as well."
    return f"{instructions[mode]} {distinctness}"


def format_section_detail_points(context: SectionContext) -> str:
    if not context.detail_points:
        return ""
    trimmed = [
        shorten_text(sanitize_for_image_prompt(point), limit=150)
        for point in context.detail_points[:3]
    ]
    return " | ".join(trimmed)


def body_scene_brief(article: Article, context: SectionContext, slot_id: str) -> list[str]:
    haystack = " ".join(
        [
            article.slug,
            article.title,
            context.heading,
            context.summary,
            *context.detail_points,
        ]
    ).lower()
    if any(term in haystack for term in ["common scenarios", "mistakes", "pitfalls", "two different questions", "why the number varies", "difference", "versus", " vs ", "eta vs", "compare"]):
        lines = [
            "Section-specific scene: use two or three clearly separated comparison panels with different travel cases or rule outcomes.",
            "Each panel should have a distinct route pattern or count state so the contrasts are immediately visible.",
            "Do not use one centered hero object. The main idea is contrast between cases, not overview.",
            "Translate the section detail cues into separate panels when possible instead of blending everything into one generalized scene.",
        ]
        if any(term in haystack for term in ["multiple short trips", "window boundary", "non-schengen", "ireland", "weekend trips", "edge case"]):
            lines.append(
                "A strong composition is three panels showing accumulation across short trips, a boundary-straddling trip, and a nearby route or country that does not count the same way."
            )
        return lines
    if "rolling window" in haystack or "rolling" in haystack:
        return [
            "Section-specific scene: show a horizontal timeline or calendar strip with a visibly sliding 180-day frame, where earlier days fall out on one side as the current date advances.",
            "Use Europe only as a small supporting cue or inset. The main subject should be the moving time window itself, not a full hero map.",
            "Make cause and effect obvious: a moving boundary, counted days inside it, and freed-up days outside it.",
        ]
    if any(term in haystack for term in ["what to gather", "template", "travel history", "passport", "evidence", "documents", "records", "spreadsheet", "copyable", "export", "import", "csv"]):
        return [
            "Section-specific scene: build an organized document-and-record workflow with travel records, date fragments, cards, tickets, and tidy structured rows moving into one clean system.",
            "Favor table fragments, timeline strips, and grouped evidence over a geographic overview.",
            "Let the image feel practical and methodical rather than scenic.",
        ]
    if any(term in haystack for term in ["exact dates", "month & year", "month and year", "year only", "dates unknown", "unknown date"]):
        return [
            "Section-specific scene: compare precise date blocks against fuzzier month-or-year blocks, making the precision difference visually obvious.",
            "Use paired cards or stacked time bands to show exact versus approximate trip memory.",
            "The key idea is precision level, not map coverage.",
        ]
    if any(term in haystack for term in ["countries count", "countries", "country", "schengen member", "popular destinations", "united nations", "europe"]):
        return [
            "Section-specific scene: focus on geography, grouping, or country relationships rather than generic counting.",
            "Use a tighter regional map, segmented country clusters, or a highlighted membership view instead of the broad hero overview.",
            "Make the geographic distinction the core message.",
        ]
    if any(term in haystack for term in ["entry and exit", "day count", "both entry and exit", "arrive", "leave"]):
        return [
            "Section-specific scene: use a calendar strip or trip bar where arrival and departure endpoints are both visibly included in the count.",
            "Show inclusion versus exclusion through highlighted edge markers, not through UI text.",
            "Prioritize counting logic at the trip boundaries.",
        ]
    if any(term in haystack for term in ["icloud", "sync", "privacy", "local", "device", "location"]):
        return [
            "Section-specific scene: show a private local device as the anchor, with optional sync or location signals as secondary controlled paths.",
            "The mood should be secure and calm, never surveillance-like.",
            "Favor locks, device halos, and optional dotted connections over map drama.",
        ]
    if any(term in haystack for term in ["dashboard", "map", "summary", "overview"]):
        return [
            "Section-specific scene: use a top-level overview composition with clustered summary cards and a map highlight, but keep it more analytical and cropped than the hero.",
            "Make the relationship between summary signals and places clear.",
            "Avoid reusing the same central subject scale as the hero.",
        ]
    if any(term in haystack for term in ["preset", "tracker", "options", "types", "choose the right"]):
        return [
            "Section-specific scene: use grouped cards or tiles representing different tracker types or rule models.",
            "Make the categories feel distinct through different shapes, bars, or icons, not through text.",
            "This should read as a structured choice system rather than a map or generic cover illustration.",
        ]
    if any(term in haystack for term in ["overstay", "consequences", "ban", "refusal", "strict enforcement"]):
        return [
            "Section-specific scene: show a consequence chain or warning-state progression using route interruption, blocked checkpoints, or escalating markers.",
            "The composition should feel cautionary and procedural, not dramatic or cinematic.",
            "Avoid repeating the hero's neutral overview composition.",
        ]
    if slot_id == "body-2":
        return [
            "Section-specific scene: make this second body image more diagrammatic or comparative than body-1.",
            "Favor multiple compartments, stages, or alternative outcomes over a single hero object.",
            "This slot should feel like a different explanatory tool, not a remix of the hero.",
        ]
    return [
        "Section-specific scene: focus tightly on the mechanism described in the target section rather than the whole article.",
        "Use a cropped analytical composition with one clear idea and one secondary supporting motif.",
        "Avoid repeating the hero's overview framing.",
    ]


def pick_theme(article: Article) -> dict[str, Any]:
    haystack = f"{article.slug} {article.title} {article.description} {article.headline}".lower()
    for rule in THEME_RULES:
        if any(keyword in haystack for keyword in rule["keywords"]):
            return rule
    return DEFAULT_THEME


def build_common_prompt_lines(
    article: Article,
    theme: dict[str, Any],
    article_notes: str,
    global_notes: str,
) -> list[str]:
    lines = [
        "Create a 3:2 website illustration for atlasdays.app.",
        SECTION_GUIDANCE[article.section],
        BASE_STYLE,
        f"Topic concept: {theme['focus']}.",
        f"Supporting context: {sanitize_for_image_prompt(article.description)}",
        "This artwork will appear beneath an existing webpage title and subtitle, so the image itself must not contain any heading, subtitle, sentence, or label. Minimal threshold numerals are acceptable, but avoid poster-style copy or UI-like text.",
        "Do not make the image look like a poster, slide, infographic header, or book cover.",
        "Use a dark neutral background that separates cleanly from both the light and dark website themes. Blue should appear as an accent, not as a full flat background.",
        f"Visual focus: {theme['focus']}.",
        f"Helpful motifs: {', '.join(theme['motifs'])}.",
        "The image should feel like it belongs to a product people are excited to use for travel, not just a neutral reference article.",
        "Bring in some sense of journey, movement, place, or destination atmosphere while staying clean and legible on the page.",
        "When the image uses paper, cards, tables, or document-like surfaces, tint them with pale ice-blue, mist blue, or cool blue-gray rather than stark pure white so they integrate better with light mode.",
        "Avoid large flat white blocks. Keep highlights soft, slightly cool, and premium.",
        "Keep the image subtly connected to AtlasDays by using travel-tracking-adjacent motifs such as route lines, day-count chips, tidy cards, world highlights, or private-device context, but do not show a literal app screenshot.",
        GLOBAL_AVOID,
    ]
    if article.intro:
        lines.append(f'Intro context: "{shorten_text(sanitize_for_image_prompt(article.intro))}"')
    if global_notes:
        lines.append(f"Additional global art direction: {collapse_whitespace(global_notes)}")
    if article_notes:
        lines.append(f"Additional article-specific notes: {collapse_whitespace(article_notes)}")
    return lines


def build_prompt(
    article: Article,
    theme: dict[str, Any],
    slot: dict[str, Any],
    article_notes: str,
    global_notes: str,
    context: SectionContext | None,
    sibling_signatures: list[str],
) -> str:
    lines = build_common_prompt_lines(article, theme, article_notes, global_notes)
    if slot["id"] == "hero":
        lines.append("Slot role: top-of-article hero image.")
        lines.append(f"Composition goal: {HERO_COMPOSITION}")
    else:
        lines.append(f'Slot role: supporting body image for marker "{slot["marker"]}".')
        lines.append(f"Composition goal: {BODY_COMPOSITION[article.section]}")
    if context is not None:
        if slot["id"] != "hero":
            slot_mode = collapse_whitespace(str(slot.get("body_mode", "")))
            if slot_mode in {"workflow", "comparison", "documents", "scenarios", "map-detail", "cards", "timeline", "focused-explainer"}:
                mode = slot_mode
            else:
                mode = pick_body_visual_mode(context, slot["id"])
            lines.append(f"Body image mode: {mode}.")
            lines.append(body_mode_instruction(mode, slot["id"]))
            lines.append("For this slot, the section-level brief should override the generic article overview whenever they compete.")
            if slot.get("scene_brief"):
                lines.append(f"Explicit scene brief: {collapse_whitespace(str(slot['scene_brief']))}")
            else:
                lines.extend(body_scene_brief(article, context, slot["id"]))
        elif slot.get("scene_brief"):
            lines.append(f"Explicit scene brief: {collapse_whitespace(str(slot['scene_brief']))}")
        lines.append(f'Section heading to visualize: "{context.heading}"')
        if context.summary:
            lines.append(f'Section summary: "{shorten_text(sanitize_for_image_prompt(context.summary))}"')
        detail_points = format_section_detail_points(context)
        if detail_points:
            lines.append(f"Section detail cues: {detail_points}")
        lines.append("This image is intended to appear inside the article body near that section, so focus on that idea rather than the whole article.")
    elif slot.get("scene_brief"):
        lines.append(f"Explicit scene brief: {collapse_whitespace(str(slot['scene_brief']))}")
    if slot.get("visual_kind"):
        lines.append(f"Preferred visual kind: {collapse_whitespace(str(slot['visual_kind']))}")
    if sibling_signatures:
        lines.append(f"Differentiate clearly from these sibling slots: {' | '.join(sibling_signatures)}")
    if slot.get("must_include"):
        includes = slot["must_include"]
        if isinstance(includes, list):
            include_text = ", ".join(collapse_whitespace(str(item)) for item in includes)
        else:
            include_text = collapse_whitespace(str(includes))
        lines.append(f"Must include these visual cues: {include_text}")
    if slot.get("must_avoid"):
        avoids = slot["must_avoid"]
        if isinstance(avoids, list):
            avoid_text = ", ".join(collapse_whitespace(str(item)) for item in avoids)
        else:
            avoid_text = collapse_whitespace(str(avoids))
        lines.append(f"Extra slot-specific avoidances: {avoid_text}")
    if slot.get("notes"):
        lines.append(f"Additional notes for this slot: {collapse_whitespace(str(slot['notes']))}")
    return "\n".join(lines)


def build_alt_text(article: Article, theme: dict[str, Any], slot_id: str, context: SectionContext | None) -> str:
    if slot_id == "hero":
        if context is not None:
            return f"Hero illustration for {article.title}, focused on {context.heading.lower()} in the AtlasDays visual style."
        return f"Hero illustration for {article.title}, showing {theme['alt_focus']} in the AtlasDays visual style."
    if context is not None:
        return f"Supporting illustration for {article.title}, focused on {context.heading.lower()} in the AtlasDays visual style."
    return f"Supporting illustration for {article.title} in the AtlasDays visual style."


def build_caption(article: Article, theme: dict[str, Any], slot_id: str, context: SectionContext | None) -> str:
    motif = theme["motifs"][0].lower()
    if slot_id == "hero":
        if context is not None:
            return f'AtlasDays hero illustration for "{context.heading}", using {motif} as a visual anchor.'
        return f"AtlasDays hero illustration for {article.title}, using {motif} as a visual anchor."
    if context is not None:
        return f'AtlasDays supporting illustration for "{context.heading}", using {motif} as a visual anchor.'
    return f"AtlasDays supporting illustration for {article.title}, using {motif} as a visual anchor."


def build_generation_plan(
    plan_data: dict[str, Any],
    article_lookup: dict[str, Article],
    selected_keys: list[str],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    global_notes = str(plan_data.get("global_notes", ""))
    for key in selected_keys:
        article = article_lookup.get(key)
        if article is None:
            raise SystemExit(f"Plan references missing article: {key}")
        article_plan = plan_data["articles"][key]
        if article_plan.get("skip"):
            continue
        theme = pick_theme(article)
        article_notes = str(article_plan.get("notes", ""))
        slots = article_plan.get("slots", [])
        if not isinstance(slots, list) or not slots:
            raise SystemExit(f"No slots configured for {key} in article-image-plan.json")
        for slot in slots:
            if not isinstance(slot, dict) or "id" not in slot or "marker" not in slot:
                raise SystemExit(f"Invalid slot config for {key}: {slot}")
            context = None
            anchor_heading = article.headline
            slot_anchor_heading = str(slot.get("anchor_heading", "")).strip()
            sibling_signatures = []
            for other in slots:
                if other is slot:
                    continue
                other_label = str(other.get("id", "slot"))
                descriptor = (
                    other.get("visual_kind")
                    or other.get("scene_brief")
                    or other.get("anchor_heading")
                    or other.get("marker")
                    or "supporting scene"
                )
                sibling_signatures.append(
                    f'{other_label}: {shorten_text(collapse_whitespace(str(descriptor)), limit=120)}'
                )
            if slot["id"] != "hero":
                anchor_heading = slot_anchor_heading
                if not anchor_heading:
                    raise SystemExit(f'Missing "anchor_heading" for {key} slot {slot["id"]}')
                context = find_section_context(article, anchor_heading)
            elif slot_anchor_heading:
                anchor_heading = slot_anchor_heading
                context = find_section_context(article, anchor_heading)
            relative_path = (
                Path("assets")
                / "article-images"
                / article.section
                / article.slug
                / f'{slot["id"]}.{settings["output_format"]}'
            )
            plan.append(
                {
                    "article": article,
                    "slot_id": slot["id"],
                    "marker": slot["marker"],
                    "placement": slot["placement"],
                    "anchor_heading": anchor_heading,
                    "context_summary": context.summary if context else article.intro,
                    "theme": theme,
                    "prompt": build_prompt(
                        article,
                        theme,
                        slot,
                        article_notes,
                        global_notes,
                        context,
                        sibling_signatures,
                    ),
                    "alt": build_alt_text(article, theme, slot["id"], context),
                    "caption": build_caption(article, theme, slot["id"], context),
                    "relative_path": relative_path,
                    "absolute_path": SITE_ROOT / relative_path,
                }
            )
    return plan


def load_existing_catalog() -> dict[str, dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return {}
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for article in data.get("articles", []):
        for image in article.get("images", []):
            path = image.get("path")
            if isinstance(path, str):
                lookup[path] = image
    return lookup


def write_catalog(
    plan: list[dict[str, Any]],
    plan_data: dict[str, Any],
    settings: dict[str, Any],
    prior_lookup: dict[str, dict[str, Any]],
) -> None:
    by_article: dict[str, dict[str, Any]] = {}
    for entry in plan:
        article: Article = entry["article"]
        article_record = by_article.setdefault(
            article.key,
            {
                "section": article.section,
                "slug": article.slug,
                "title": article.title,
                "headline": article.headline,
                "description": article.description,
                "intro": article.intro,
                "source": str(article.source_path.relative_to(SITE_ROOT)),
                "canonical": article.canonical,
                "plan_notes": plan_data["articles"][article.key].get("notes", ""),
                "section_contexts": [
                    {
                        "heading": context.heading,
                        "summary": context.summary,
                        "detail_points": context.detail_points,
                    }
                    for context in article.section_contexts
                ],
                "images": [],
            },
        )
        path_key = entry["relative_path"].as_posix()
        previous = prior_lookup.get(path_key, {})
        image_record = {
            "slot": entry["slot_id"],
            "marker": entry["marker"],
            "path": path_key,
            "url": f"/{path_key}",
            "alt": entry["alt"],
            "caption": entry["caption"],
            "theme_focus": entry["theme"]["focus"],
            "placement": entry["placement"],
            "anchor_heading": entry["anchor_heading"],
            "context_summary": entry["context_summary"],
            "prompt": entry["prompt"],
            "exists": entry["absolute_path"].exists(),
        }
        for field in ("generated_at", "revised_prompt", "usage", "bytes"):
            if field in previous:
                image_record[field] = previous[field]
        if entry["absolute_path"].exists():
            image_record["bytes"] = entry["absolute_path"].stat().st_size
        article_record["images"].append(image_record)

    catalog = {
        "generated_by": "scripts/generate_article_images.py",
        "plan_source": "article-image-plan.json",
        "settings": settings,
        "articles": [by_article[key] for key in sorted(by_article)],
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def update_catalog_entry(
    prior_lookup: dict[str, dict[str, Any]],
    path: Path,
    revised_prompt: str | None,
    usage: dict[str, Any] | None,
    byte_count: int,
) -> None:
    record = prior_lookup.setdefault(path.as_posix(), {})
    record["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    if revised_prompt:
        record["revised_prompt"] = revised_prompt
    if usage:
        record["usage"] = usage
    record["bytes"] = byte_count


def print_plan(plan: list[dict[str, Any]], show_prompts: bool) -> None:
    if not plan:
        print("No matching articles found.")
        return
    current = None
    for entry in plan:
        article: Article = entry["article"]
        if article.key != current:
            current = article.key
            print(f"\n[{article.section}] {article.slug}")
            print(f"  Title: {article.title}")
        label = "top of article" if entry["slot_id"] == "hero" else f'after "{entry["anchor_heading"]}"'
        print(f'  - {entry["slot_id"]}: {entry["relative_path"].as_posix()} ({label})')
        if show_prompts:
            print("    Prompt:")
            for line in entry["prompt"].splitlines():
                print(f"      {line}")


def call_openai_image_api(api_key: str, prompt: str, settings: dict[str, Any]) -> tuple[bytes, str | None, dict[str, Any] | None]:
    payload: dict[str, Any] = {
        "model": settings["model"],
        "prompt": prompt,
        "n": 1,
        "size": settings["size"],
        "quality": settings["quality"],
        "background": settings["background"],
        "moderation": settings["moderation"],
    }
    if settings["output_format"] != "png":
        payload["output_format"] = settings["output_format"]
        payload["output_compression"] = settings["output_compression"]
    else:
        payload["output_format"] = "png"

    req = request.Request(
        IMAGE_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as response:
            parsed = json.loads(response.read())
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI image generation failed with HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise SystemExit(f"OpenAI image generation failed: {exc}") from exc

    images = parsed.get("data") or []
    if not images:
        raise SystemExit(f"OpenAI returned no images: {parsed}")
    image = images[0]
    encoded = image.get("b64_json")
    if not encoded:
        raise SystemExit(f"OpenAI returned an image object without b64_json: {parsed}")
    return base64.b64decode(encoded), image.get("revised_prompt"), parsed.get("usage")


def main() -> int:
    args = parse_args()
    load_env_file()
    settings = load_settings(args)
    api_key = ensure_api_key(args.dry_run)
    plan_data = load_plan()
    selected_keys = select_article_keys(plan_data, args.section, args.slug, args.limit)
    if not selected_keys:
        print("No matching articles found.")
        return 0
    article_lookup = discover_articles(set(selected_keys))
    generation_plan = build_generation_plan(plan_data, article_lookup, selected_keys, settings)
    prior_lookup = load_existing_catalog()
    print_plan(generation_plan, args.show_prompts)
    if not args.dry_run:
        for entry in generation_plan:
            target: Path = entry["absolute_path"]
            if target.exists() and not args.force:
                print(f"Skipping existing {entry['relative_path'].as_posix()}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            print(f"Generating {entry['relative_path'].as_posix()}")
            image_bytes, revised_prompt, usage = call_openai_image_api(api_key, entry["prompt"], settings)
            target.write_bytes(image_bytes)
            update_catalog_entry(prior_lookup, entry["relative_path"], revised_prompt, usage, len(image_bytes))
    write_catalog(generation_plan, plan_data, settings, prior_lookup)
    print(f"\nCatalog written to {CATALOG_PATH.relative_to(SITE_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
