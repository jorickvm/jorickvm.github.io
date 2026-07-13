# Residency / Visa Rule Articles — Authoring Guide

Guide for producing the `learn/` articles that document each visa / tax-residency rule
AtlasDays can track. One article per rule. Encyclopedia style: factual, skimmable, no filler.

**Reference implementation:** `learn/portugal-183-day-tax-residency.html`. Copy it and change
the marked pieces below. Do **not** hand-write a new file from scratch — the reference carries
the correct schema, meta, CSS, header, and CTA boilerplate.

---

## Hard rules (do not deviate)

1. **En-dashes, never em-dashes.** Use `–` (or a plain hyphen). No `—` anywhere. Verify with
   `grep -c '—' <file>` → must be `0`.
2. **Anchor every fact to the app's own preset wording** (tables below). The site and the app
   must never contradict each other on threshold / window / days-vs-nights.
3. **Every article links a VERIFIED official government source** to the page where the rule is
   actually written. Research it per article (see "Official source" step). Never guess a URL and
   never link only a homepage when a deep link to the rule exists. Legislative page or a
   plain-language government guide both fine; it must be a government domain and must be live.
4. **No fluff.** Cut "what this page explains" lists, repeated disclaimers, and hand-wringing.
   The audience is intelligent. One short "beyond the day count" note is enough for caveats.
5. **The AtlasDays section is the CTA** (logo + headline "AtlasDays tracks [X] automatically" +
   App Store button). It is the only CTA. Keep it truthful and name the actual app preset.

---

## Per-article checklist

1. `cp learn/portugal-183-day-tax-residency.html learn/<slug>.html`
2. Replace, throughout: slug, `<title>`, meta description + keywords, all OG/Twitter tags,
   canonical URL, all three JSON-LD blocks (Article headline/description/url/dates,
   FAQPage Q&As, BreadcrumbList name/item), `datePublished`/`dateModified` = today.
3. Flag: `<img class="title-flag" src="../assets/flags/<code>.png" ...>` — flags already exist in
   `assets/flags/` (country ISO code lowercased, e.g. `th.png`; US states `us-ny.png`).
4. H1, subtitle, TLDR, `.factbox` values, "The rule", "How to count it" + example,
   "Beyond the day count" — all from the data table for this rule.
5. **Official source line**: WebSearch for the government page, WebFetch to confirm it is live
   and states the rule, then link it with `rel="nofollow"`.
6. CTA: headline "AtlasDays tracks [Country]'s [rule] automatically", copy names the preset,
   button unchanged.
7. FAQ: 3 short Q&As mirroring the FAQPage schema.
8. Related: 3–4 links (keep `183-day-tax-residency-rule`, `what-counts-as-a-day-for-visa-purposes`,
   plus 1–2 relevant siblings).
9. Wire in (SEO): the per-country listing lives in the hub, not the Learn index topic card.
   - Add a one-line entry to `scripts/residency_data.json`, then run
     `python3 scripts/build_residency_hub.py` to regenerate the grid + table in
     `learn/tax-residency-by-country.html`. Do NOT hand-edit the grid/table regions.
   - Add a `<url>` block to `sitemap.xml` (priority `0.8`, lastmod today) and an entry under
     "Country Tax Residency Rules" in `llms.txt` (the script also prints the sitemap blocks).
   - Add a reciprocal related-link from at least one sibling article. Root-relative links only.
   - The Learn index topic card stays curated (concept articles + the hub card); do not add
     one card per country there.
10. Verify: `grep -c '—' learn/<slug>.html` = 0; flag path resolves; links present.

### Delegated / parallel production (multiple subagents at once)

Shared files (`learn/index.html`, `sitemap.xml`, `llms.txt`) MUST NOT be edited by parallel
agents — concurrent writes clobber each other. When fanning out:
- Each subagent writes ONLY its `learn/<slug>.html` and does step 5's source research.
- Each subagent returns: slug, H1, meta description, one-line card description, and the verified
  official source URL.
- The orchestrator does all shared-file wiring (step 9) centrally after agents return, and runs
  the verification sweep across every new file.

Window → prose mapping:
- `calendarYear` → "calendar year (1 January – 31 December)"
- `calendarYear` + fiscal start → "income/tax year (e.g. 1 July – 30 June)"
- `rollingDays` (365) → "any rolling 12-month period"

---

## Data: residence-preset countries (16)

`~/Projects/AtlasDays/AtlasDays/AtlasDays/Trackers/ResidencePresetSheet.swift` is the source of truth.
UK is already covered by `learn/uk-statutory-residence-test.html` — skip or cross-link, do not duplicate.

| Code | Country | Threshold | Window | Notes / app ruleDescription anchor |
|------|---------|-----------|--------|-------------------------------------|
| PT | Portugal | > 183 (nights) | rolling 12-mo | DONE. + habitual-residence test |
| AU | Australia | > half | income year (Jul 1–Jun 30) | "one of its tax residence tests"; also domicile/resides tests |
| CA | Canada | ≥ 183 | calendar year | "deemed tax resident"; also residential-ties test |
| CO | Colombia | > 183 | rolling 12-mo | "any 365-day period" |
| EE | Estonia | ≥ 183 | rolling 12-mo | "any 12-month period" |
| GE | Georgia | ≥ 183 | rolling 12-mo | "any 12-month period" |
| GR | Greece | > 183 | rolling 12-mo | "any 12-month period" |
| IE | Ireland | ≥ 183 | tax year (= calendar) | also 280-day-over-2-years test (mention) |
| MT | Malta | > 183 | calendar year | |
| MU | Mauritius | ≥ 183 | income year (Jul 1–Jun 30) | + separate aggregate-day test |
| NZ | New Zealand | > 183 | rolling 12-mo | resident from first day; + permanent-place-of-abode |
| RO | Romania | > 183 | rolling 12-mo | "any 12-month period" |
| SG | Singapore | ≥ 183 | calendar year | |
| TH | Thailand | ≥ 180 | calendar year | note: 180 not 183 |
| AE | UAE | ≥ 183 | rolling 12-mo | + 90-day test for certain residents (mention) |
| GB | United Kingdom | ≥ 183 (midnights) | tax year (Apr 6–Apr 5) | COVERED by SRT article |

## Data: US-state residence presets (21)

`~/Projects/AtlasDays/AtlasDays/AtlasDays/Trackers/StatePresetSheet.swift`. Flags: `us-xx.png`.
**Reference article:** `learn/new-york-tax-residency.html` (statutory-resident pattern). Slug convention:
`<state>-tax-residency` (put the day number in the title/H1, not the slug, since thresholds vary).
Georgia the US state uses `georgia-us-tax-residency` to avoid clashing with the country.

Two structural types, and the article must use the right one:
- **statutory** = resident if 183+ days (varies) AND a permanent place of abode maintained for
  substantially all year, even if domiciled elsewhere. Both conditions required. Mirror NY.
- **presumption** = no hard statutory-resident line; the day count creates a REBUTTABLE
  presumption of residency (CA/AZ/ID/HI). Frame it as a presumption, not an automatic rule, and
  replace the "Also required" factbox row with a "Presumption" note.

STATUS: all 21 state articles are DONE and wired. The US-state hub lives at
`learn/us-state-tax-residency.html`, driven by the `us_states` array in `residency_data.json`
via the same `build_residency_hub.py`. Adding a state = new article + one JSON entry + run script
+ sitemap/llms. Verify each state against its Department of Revenue / Taxation source.

| State | Slug | Threshold | Window | Type / note |
|-------|------|-----------|--------|-------------|
| New York | new-york-tax-residency | > 183 (184+) | calendar | statutory + abode — DONE |
| New Jersey | new-jersey-tax-residency | > 183 (184+) | calendar | statutory + abode |
| Connecticut | connecticut-tax-residency | > 183 (184+) | calendar | statutory + abode |
| California | california-tax-residency | > 270 | calendar | presumption (rebuttable); no fixed line |
| Maryland | maryland-tax-residency | ≥ 183 | calendar | statutory + abode (place >6 months) |
| Massachusetts | massachusetts-tax-residency | > 183 (184+) | calendar | statutory + abode |
| Minnesota | minnesota-tax-residency | ≥ 183 | calendar | statutory + abode |
| Nebraska | nebraska-tax-residency | ≥ 183 | calendar | statutory + abode |
| North Dakota | north-dakota-tax-residency | > 210 (7-month) | calendar | statutory + permanent home |
| Ohio | ohio-tax-residency | > 212 nights | calendar | counts overnights ("contact periods") |
| Virginia | virginia-tax-residency | > 183 (184+) | calendar | actual resident + abode |
| Maine | maine-tax-residency | > 183 (184+) | calendar | statutory + abode (safe harbor) |
| Rhode Island | rhode-island-tax-residency | > 183 (184+) | calendar | statutory + abode |
| Vermont | vermont-tax-residency | > 183 (184+) | calendar | statutory + abode |
| Colorado | colorado-tax-residency | > 183 (184+) | calendar | statutory + abode (>6 months) |
| Pennsylvania | pennsylvania-tax-residency | > 183 (184+) | calendar | statutory + abode |
| Idaho | idaho-tax-residency | > 270 | calendar | present >270 days -> resident |
| Hawaii | hawaii-tax-residency | > 200 | calendar | presumption (rebuttable) |
| Oregon | oregon-tax-residency | > 200 | calendar | abode + >200 days |
| Arizona | arizona-tax-residency | > 270 | calendar | presumption (rebuttable) |
| Georgia (US state) | georgia-us-tax-residency | > 183 | rolling 12-mo | present 183+ days; disambiguate from country |

## Data: visa / entry presets (3 uncovered)

`~/Projects/AtlasDays/AtlasDays/AtlasDays/Trackers/EntryPresetSheets.swift`. These are entry
limits, not tax residency, so drop the tax-residency framing; keep TLDR + factbox + official
source + CTA. Schengen is already well covered — cross-link it.

| Rule | Limit | Window | Note |
|------|-------|--------|------|
| US ESTA / Visa Waiver | 90 days | per visit | closer to existing us-b1-b2 content |
| Türkiye short stay | 90 days | rolling 180-mo | rolling window like Schengen |
| Schengen single-entry visa | per visa | one continuous stay | days printed on the visa |

---

## Flag regeneration (if ever needed)

Flags are converted from the app's vector PDFs:
```
SRC="$HOME/Projects/AtlasDays/AtlasDays/AtlasDays/Assets.xcassets/Flags"
sips -s format png --resampleWidth 240 "$SRC/<CODE>.imageset/<CODE>.pdf" --out assets/flags/<code>.png
```
