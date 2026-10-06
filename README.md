# atlasdays.app

Marketing and support website for [AtlasDays](https://atlasdays.app), a private iPhone app for tracking trips, visa days, and residency thresholds.

Static HTML served straight from this repo by GitHub Pages. No framework, no bundler, and the Python tooling is standard library only, so there is nothing to install.

Accounts, DNS, analytics, automations, and where each credential lives are documented in the private `atlasdays-internal` repo, in `OPERATIONS.md`.

## Deploying has no build step. Authoring does.

This is the one thing to know before editing anything. Pages under `learn/` and `help/`, the hub pages, and every root page listed in `_site-src/data/pages.json` are **generated** by `scripts/build_site.py` from sources in `_site-src/`, and the rendered output is committed. Editing those files directly gets overwritten by the next build, and `build_site.py --check` fails when committed HTML no longer matches its sources.

All ten root pages are generated, `index.html`, `404.html`, and `support.html` included; they moved into `pages.json` when Dutch shipped, because a page that cannot be translated cannot be localized.

Genuinely hand-authored: the `app/*/index.html` alias stubs, the in-app link hop `app/open/index.html` (the app opens Learn articles through it so Cloudflare can tell in-app visits apart), the three legacy meta-refresh redirect stubs in `learn/` (`day-limits.html`, `how-to-use-atlasdays.html`, `icloud-sync-travel-tracking.html`), and the Shift pages (below). Merged Learn pages in `_site-src/data/redirects.json` generate redirect stubs for English and every locale; `build_site.py --check` covers them.

### The Shift folders

`shift/` and the `<code>/shift/` folders hold the privacy and support pages for Shift, a separate iOS app. They sit outside the build and deliberately do not use the AtlasDays design. Shift ships in more languages than this site, so some root folders (`it/`, `ka/`, `pt-PT/`, …) exist only for Shift.

`changelog.html` is shared with the AtlasDays app repo, which owns the release notes. `scripts/sync_changelog.py` replaces only the contents of `<div class="release-stack">`, so a release updates the cards and leaves this repo's header, footer, social metadata, and theme bootstrap intact.

## Sources

```
_site-src/
  content/{learn,help,hubs,pages}/   article fragments (the part inside <article>)
  data/                             the registries the build reads
  templates/                        page layout + header/footer partials
```

`_site-src/data/articles.json` is the single article registry. A page exists on the site because it has a record there; that record carries its title, metadata, JSON-LD, style variant, review tier, and, for jurisdiction pages, the `residency` object that puts it on the hub tables. Learn records also own their structured official-source URLs in `sources`, the explanatory `source_note`, and, where the fragment's factbox did not already name the law, `legal_basis`. The build turns those fields into a linked legal-basis row and a shared source/context panel; do not hand-author either component in a fragment. `routes.json` drives `sitemap.xml` and `llms.txt`. Nothing reaches a generated surface without going through these files.

## Languages

The site is generated one locale at a time from the same templates and the same English registry. Everything that differs between languages is data:

```
_site-src/data/locales.json        which locales exist, and how each formats a route, date, and title
_site-src/data/ui-strings.json     chrome copy (nav, footer, article furniture), keyed string-first
_site-src/data/articles.<code>.json  overlays, joined to articles.json, hubs.json and pages.json by `source`
_site-src/data/glossary.json       terminology snapshot, generated from the app repo
_site-src/content/<code>/…          translated fragments
```

The published locales and their coverage are declared in `_site-src/data/locales.json`. Each non-English locale routes under its own code. English stays unprefixed, so `en` is simply the locale whose `route_prefix` is empty. The privacy and terms pages are ordinary generated pages in every locale; a `?lang=<code>` query on the English page redirects to that locale's copy before paint, which is how the app's deep links reach them.

**A translation record supplies prose and nothing else.** Paths, canonicals, hreflang, JSON-LD, og tags, next-step URLs, and the rendered date are all derived from the English source record, and setting one of them in an overlay is a build error. That is deliberate: it means a translation cannot invent a URL or a JSON-LD graph in a language nobody here can proofread, and `validate_help_next_steps` keeps guarding the routes for free.

Official-source URLs are source-owned too. A localized `source_note` may translate the explanation and anchor text, but it refers to the English record's URLs with `{{source:0}}`, `{{source:1}}`, and so on. The legal-basis link, source panel, context disclaimer, and cluster-related navigation are template components, so one change propagates across every Learn article and every language on rebuild.

Templates and partials carry two marker forms, both resolved by `scripts/locales.py`:

```
{{t:nav.help}}   a chrome string, from ui-strings.json
{{r:/help/}}     an internal route, locale-prefixed only when that page exists in the locale
```

The `{{r:}}` fallback supports a draft locale while its coverage grows: a link uses the locale route only when that translated page exists. Adding a translation is a data change, not a code change.

A locale carries `status: draft | published`. A draft locale builds and previews locally but is marked `noindex` and excluded from the sitemap, hreflang, `llms.txt`, and the language switcher. That is how a new language is verified end to end before it becomes discoverable.

Each published locale gets its own `sitemap-<code>.xml`, with `sitemap.xml` as the sitemap index over them. The split buys nothing for ranking; it buys measurement, because Search Console reports discovery and indexing per submitted sitemap, so a locale that is not being indexed is a number rather than a hunch. `robots.txt` still points at `sitemap.xml`, so nothing needs resubmitting when a locale is added, and submitting the children individually in Search Console is what turns the per-locale reporting on. hreflang stays in the page head and is deliberately not repeated in the sitemap: two sources of truth for the same annotation is how a hreflang cluster gets discarded. Retiring a locale deletes its child file, and `--check` fails on a `sitemap-*.xml` that no locale claims.

A locale also carries `coverage`. Under `complete`, every English page must have an overlay and a missing one is an error rather than a silent gap. Pages the locale deliberately serves in English go in `untranslated` instead, which is a decision rather than a to-do: `check_translations.py` rejects an entry that names something which is not an English source, and rejects one that still has an overlay, so the list cannot drift out of step with what is actually translated. `changelog.html` is the standing example. Its release cards are authored in the AtlasDays repo and synced here on every release, so a translated changelog would pin a hash that each release invalidates, blocking the build until someone retranslated the new cards.

Adding the next language should be `locales.json` + a `ui-strings.json` column + an overlay registry + fragments. If it needs a change in `scripts/`, that is a bug in the machinery, not a missing feature.

### Translating

Interactive day-calendar messages live in the article fragment’s `<script type="application/json" data-cal-strings>` block. Translate its values and plural variants; preserve the keys and placeholders. The checks validate these messages alongside the visible prose. Dates and weekdays use the document language through `Intl`, while downloaded CSV headers, country names and notes remain English for the AtlasDays importer.

1. Refresh the terminology snapshot if the app repo has moved: `python3 scripts/sync_glossary.py`. It covers every non-English locale in `locales.json`.
2. Write `_site-src/content/<code>/<section>/<slug>.html`, keeping the English structure (see the checks below).
3. Add the overlay record to `_site-src/data/articles.<code>.json`, including a localized `source_note` when the English record has one, `source_hash`, `source_meta_hash`, and `jsonld_replacements` for any page whose JSON-LD carries prose. Keep the `{{source:n}}` markers unchanged; URLs never belong in the overlay.
4. Rebuild as usual. Localized routes need no `routes.json` row: `build_route_outputs.py` derives them from the overlay registries, so a published locale cannot leave a page out of the sitemap.

`scripts/check_translations.py` gates terminology against the app's own shipped strings, structural parity with the English source (heading, list, figure, and internal-link counts), Japanese typography, and translation staleness. `scripts/check_untranslated.py` separately catches multi-word English copy that survived inside a translated fragment. Both run before the build in CI.

**Staleness**: each overlay records the hash of the English fragment and metadata it was translated from. Editing English copy fails the build until the translation catches up. When the edit genuinely does not change meaning, add a `stale_ack` carrying the new hash, a reason, and an `expires` date; it warns until that date and errors after it.

**Screenshots**: `capture_website_screenshots.py --locale ja` captures in the app's Japanese interface and writes to `assets/article-images/ja/…`. `sync_help_screenshots.py` resolves per locale and falls back to the English file per slot, so a language can recapture gradually. iPad slots need their own run with `--device`.

**Terminology comes from the app, not from this repo.** `glossary.json` is a generated snapshot of the AtlasDays app's shipped translations and its accepted-terminology tables. A help article is a set of instructions about the app's screens: if it names a button differently from the app, the article is worse than useless, and that mismatch is invisible to anyone who cannot read the language.

## How Learn is put together

- **Rule articles appear as the app's preset cards** on the Learn index, the use-case pages and in related links: the flag, title, section and one-line rule come from the app. An article names its preset with `app_preset` in `articles.json`; `_site-src/data/app-catalog.json` is the committed snapshot of the app's catalogue, refreshed with `scripts/sync_app_catalog.py`. A rule the app has no preset for gets its own card in `_site-src/data/learn-cards.json`. An article with neither is left off the Learn index without an error.
- **Guides and calculators have their own pages,** `/learn/guides` and `/learn/calculators` (`_site-src/content/hubs/learn-guides.html`, `learn-calculators.html`, one per locale), and sit under them in the breadcrumb ("Travel Rules / Guides"), in the fragment and in the `BreadcrumbList`. A new guide goes on the guides page in every locale.
- **Related articles** at the foot of every Learn article are chosen by the build (`related_paths()` in `build_site.py`): the same country's other rules, the rule's calculator and guide, the topic overview, then the same kind of rule in nearby countries. Neighbours come from `_site-src/data/regions.json`; add a new country there.
- **"On this page"** (`render_toc()`) is a sidebar on wide screens on every Learn article, and an inline list on phones and tablets for long articles only.
- **Search** matches titles, descriptions and `search_synonyms`; put the abbreviations and form numbers people type (SPT, ILR, N-400) in the English record's `search_synonyms`, and every language inherits them.
- **Day calculators** are described in the private repo's `CALCULATORS_HANDOFF.md`.

## Adding or editing an article

1. Edit the fragment under `_site-src/content/<section>/`, or add a new one.
2. Register it in `_site-src/data/articles.json`, and add a route to `routes.json`. A rule article needs its card: `app_preset`, or an entry in `learn-cards.json` (see How Learn is put together). For Learn, put verified government URLs in `sources` and the prose that explains them in `source_note`; use `{{source:n}}` markers inside that note. A factbox must have a Legal basis row: use the row in the fragment, or set `legal_basis` and `legal_basis_source` for the build to add it.
3. Rebuild, in this order (each output feeds the next):

```bash
python3 scripts/check_translations.py          # terminology, structure, typography, staleness
python3 scripts/build_content_governance.py   # editorial + cluster records, review queue
python3 scripts/generate_social_cards.py      # generic OG image manifest
python3 scripts/build_residency_hub.py        # hub tables, if a residency page changed
python3 scripts/build_site.py                 # every generated page, sitemaps, and llms.txt
python3 scripts/build_search_index.py         # on-site search
```

A brand-new page crashes its first `build_site.py` with `FileNotFoundError`, because `llms.txt` is rendered from the pages already on disk. Seed the output path with `<title>x</title>`, then build twice.

4. Verify, and review the diff before committing:

```bash
python3 scripts/audit_site.py --strict-semantics --check-baseline _site-src/data/baseline.json
```

The audit is the main safety net: it checks canonicals, sitemap agreement, JSON-LD, internal links, social images, editorial coverage, and diffs every page against a committed baseline. For generated pages the baseline pins structure (route, indexability, title, description, canonical, H1) rather than body text, since `build_site.py --check` already guards the body; hand-authored pages are pinned in full. If a structural change is intentional, re-arm the baseline with `--write-baseline` and check that the diff lists only the pages you meant to touch.

## Analytics

Every generated page loads Cloudflare Web Analytics (cookieless, aggregate) through a small inline loader in the three page templates, between the `Cloudflare Web Analytics` comment markers. Opening any page with `?notrack` switches analytics off in that browser (a `localStorage` flag, never sent anywhere); `?notrack=off` switches it back on. It exists so the site owner's own visits are not counted. The app's in-app browser keeps its own storage and has no address bar, so the app adds `notrack=1` to every atlasdays.app link when its hidden analytics opt-out is on; the hand-authored `app/*/index.html` pages, including the in-app hop, honour it too. `assets/js/app-page-alias.js` strips everything between the markers from pages it renders, so an alias never counts twice.

## Local preview

```bash
python3 scripts/serve_site.py --port 8899
```

Serves the committed HTML with GitHub Pages' extensionless URLs, so links resolve the way they do in production.

## Scripts

| Script | Purpose |
|---|---|
| `build_site.py` | Renders articles, hubs, and root pages from `_site-src/`. `--check` fails on drift. |
| `check_app_learn_links.py` | Fails when an address the app opens (Learn slugs, `/app/open/`, the aliases, the legal pages) no longer exists. CI checks the committed snapshot `_site-src/data/app-links.json`; after the app changes a slug or link, refresh it with `--sync` (needs the app checkout) and commit it. |
| `build_route_outputs.py` | Generates the sitemap set (`sitemap.xml` index plus `sitemap-<code>.xml` per locale) and the `llms.txt` set (English at the root, `/<code>/llms.txt` per translation) from `routes.json`. |
| `build_content_governance.py` | Derives editorial records, content clusters, and the review queue from `articles.json`. |
| `build_residency_hub.py` | Fills the residency hub tables from the `residency` objects in `articles.json`. |
| `hub_collation.py` | Per-language alphabetical sort keys for the residency hub tables. |
| `build_search_index.py` | Builds `assets/search-index.json`. |
| `generate_social_cards.py` | Assigns the generic 1200x630 share image site-wide. |
| `sync_help_screenshots.py` | Swaps a Help screenshot placeholder for a `<figure>` once its WebP lands, in every locale. |
| `capture_website_screenshots.py` | Drives the iOS Simulator to capture Help Center screenshots (macOS only). `--locale` captures in another interface language. |
| `check_translations.py` | Gates translated pages on terminology, structural parity, typography, and staleness. |
| `check_untranslated.py` | Flags reader-facing English phrases left in translated fragments. |
| `sync_glossary.py` | Snapshots product terminology from the app repo into `glossary.json`. |
| `sync_app_catalog.py` | Snapshots the app's tracker catalogue (preset cards, per language) into `app-catalog.json`, from the app's `WebsiteCatalogExportTests` output. |
| `locales.py` | Shared locale registry, marker resolution, dates, and translation hashing. |
| `check_external_sources.py` | Weekly link check over the official sources articles cite. |
| `report_source_health.py` | Turns that report into the GitHub issue the weekly workflow maintains. |
| `sync_changelog.py` | Replaces release cards in the changelog source fragment; rebuild afterwards. |
| `audit_site.py` | The site auditor, and the shared HTML parser other scripts import. |
| `serve_site.py` | Local preview server. |

Every build script has a `--check` mode that verifies without writing. CI runs all of them.

## CI

`.github/workflows/site-audit.yml` runs the audit and every `--check` on pull requests and pushes to `main`. It runs entirely from the checkout, with no secrets.

The same workflow runs a weekly source monitor: it re-checks the official government sources the articles cite and maintains a single GitHub issue listing any that moved or died, closing it when they all resolve again. Sites that merely block CI runners (401/403/429) are recorded but never raise the issue.

Editorial process, brand and voice, and review notes live in a separate private repo and are git-ignored here by name. See [CLAUDE.md](CLAUDE.md) for the conventions agents follow in this repo.
