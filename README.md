# atlasdays.app

Marketing and support website for [AtlasDays](https://atlasdays.app), a private iPhone app for tracking trips, visa days, and residency thresholds.

Static HTML served straight from this repo by GitHub Pages. No framework, no bundler, and the Python tooling is standard library only, so there is nothing to install.

## Deploying has no build step. Authoring does.

This is the one thing to know before editing anything. Pages under `learn/` and `help/`, the hub pages, and `about|privacy|terms.html` are **generated** by `scripts/build_site.py` from sources in `_site-src/`, and the rendered output is committed. Editing those files directly gets overwritten by the next build, and `build_site.py --check` fails when committed HTML no longer matches its sources.

Genuinely hand-authored: `index.html`, `support.html`, `404.html`, the `app/*/index.html` alias stubs, and two redirect stubs in `learn/`.

`changelog.html` is shared with the AtlasDays app repo, which owns the release notes. `scripts/sync_changelog.py` replaces only the contents of `<div class="release-stack">`, so a release updates the cards and leaves this repo's header, footer, social metadata, and theme bootstrap intact.

## Sources

```
_site-src/
  content/{learn,help,hubs,pages}/   article fragments (the part inside <article>)
  data/                             the registries the build reads
  templates/                        page layout + header/footer partials
```

`_site-src/data/articles.json` is the single article registry. A page exists on the site because it has a record there; that record carries its title, metadata, JSON-LD, style variant, review tier, and, for jurisdiction pages, the `residency` object that puts it on the hub tables. `routes.json` drives `sitemap.xml` and `llms.txt`. Nothing reaches a generated surface without going through these files.

## Languages

The site is generated one locale at a time from the same templates and the same English registry. Everything that differs between languages is data:

```
_site-src/data/locales.json        which locales exist, and how each formats a route, date, and title
_site-src/data/ui-strings.json     chrome copy (nav, footer, article furniture), keyed string-first
_site-src/data/articles.ja.json    Japanese overlays, joined to articles.json by `source`
_site-src/data/glossary.json       terminology snapshot, generated from the app repo
_site-src/content/ja/…             translated fragments
```

Japanese Help Center pages are served at `/ja/help/…`. English stays unprefixed, so `en` is simply the locale whose `route_prefix` is empty.

**A translation record supplies prose and nothing else.** Paths, canonicals, hreflang, JSON-LD, og tags, next-step URLs, and the rendered date are all derived from the English source record, and setting one of them in an overlay is a build error. That is deliberate: it means a translation cannot invent a URL or a JSON-LD graph in a language nobody here can proofread, and `validate_help_next_steps` keeps guarding the routes for free.

Templates and partials carry two marker forms, both resolved by `scripts/locales.py`:

```
{{t:nav.help}}   a chrome string, from ui-strings.json
{{r:/help/}}     an internal route, locale-prefixed only when that page exists in the locale
```

The `{{r:}}` fallback is what makes partial coverage legal: a Japanese Help page links to the Japanese Help hub but to the English Travel Rules hub, because no Japanese one exists. Localising a single Learn article later is a data change, not a code change.

A locale carries `status: draft | published`. A draft locale builds and previews locally but is marked `noindex` and excluded from the sitemap, hreflang, `llms.txt`, and the language switcher. That is how a new language is verified end to end before it becomes discoverable.

A locale also carries `coverage`. Under `complete`, every English page must have an overlay and a missing one is an error rather than a silent gap. Pages the locale deliberately serves in English go in `untranslated` instead, which is a decision rather than a to-do: `check_translations.py` rejects an entry that names something which is not an English source, and rejects one that still has an overlay, so the list cannot drift out of step with what is actually translated. `changelog.html` is the standing example. Its release cards are authored in the AtlasDays repo and synced here on every release, so a translated changelog would pin a hash that each release invalidates, blocking the build until someone retranslated the new cards.

Adding the next language should be `locales.json` + a `ui-strings.json` column + an overlay registry + fragments. If it needs a change in `scripts/`, that is a bug in the machinery, not a missing feature.

### Translating

1. Refresh the terminology snapshot if the app repo has moved: `python3 scripts/sync_glossary.py`.
2. Write `_site-src/content/<code>/help/<slug>.html`, keeping the English structure (see the checks below).
3. Add the overlay record to `_site-src/data/articles.<code>.json`, including `source_hash` and `source_meta_hash`.
4. Add a `routes.json` row per page, and rebuild as usual.

`scripts/check_translations.py` gates all of it, and runs first in CI. It enforces terminology against the app's own shipped strings, structural parity with the English source (heading, list, figure, and internal-link counts), Japanese typography, and translation staleness.

**Staleness**: each overlay records the hash of the English fragment and metadata it was translated from. Editing English copy fails the build until the translation catches up. When the edit genuinely does not change meaning, add a `stale_ack` carrying the new hash, a reason, and an `expires` date; it warns until that date and errors after it.

**Screenshots**: `capture_website_screenshots.py --locale ja` captures in the app's Japanese interface and writes to `assets/article-images/ja/…`. `sync_help_screenshots.py` resolves per locale and falls back to the English file per slot, so a language can recapture gradually. iPad slots need their own run with `--device`.

**Terminology comes from the app, not from this repo.** `glossary.json` is a generated snapshot of the AtlasDays app's shipped translations and its accepted-terminology tables. A help article is a set of instructions about the app's screens: if it names a button differently from the app, the article is worse than useless, and that mismatch is invisible to anyone who cannot read the language.

## Adding or editing an article

1. Edit the fragment under `_site-src/content/<section>/`, or add a new one.
2. Register it in `_site-src/data/articles.json`, and add a route to `routes.json`.
3. Rebuild, in this order (each output feeds the next):

```bash
python3 scripts/check_translations.py          # terminology, structure, typography, staleness
python3 scripts/build_content_governance.py   # editorial + cluster records, review queue
python3 scripts/generate_social_cards.py      # OG images + manifest
python3 scripts/build_residency_hub.py        # hub tables, if a residency page changed
python3 scripts/build_site.py                 # renders every generated page
python3 scripts/build_search_index.py         # on-site search
```

4. Verify, and review the diff before committing:

```bash
python3 scripts/audit_site.py --strict-semantics --check-baseline _site-src/data/baseline.json
```

The audit is the main safety net: it checks canonicals, sitemap agreement, JSON-LD, internal links, social images, editorial coverage, and diffs every page against a committed baseline. If a change is intentional, re-arm the baseline with `--write-baseline` and check that the diff lists only the pages you meant to touch.

## Local preview

```bash
python3 scripts/serve_site.py --port 8899
```

Serves the committed HTML with GitHub Pages' extensionless URLs, so links resolve the way they do in production.

## Scripts

| Script | Purpose |
|---|---|
| `build_site.py` | Renders articles, hubs, and root pages from `_site-src/`. `--check` fails on drift. |
| `build_route_outputs.py` | Generates `sitemap.xml` and `llms.txt` from `routes.json`. |
| `build_content_governance.py` | Derives editorial records, content clusters, and the review queue from `articles.json`. |
| `build_residency_hub.py` | Fills the residency hub tables from the `residency` objects in `articles.json`. |
| `build_search_index.py` | Builds `assets/search-index.json`. |
| `generate_social_cards.py` | Renders the 1200x630 share images. |
| `sync_help_screenshots.py` | Swaps a Help screenshot placeholder for a `<figure>` once its WebP lands, in every locale. |
| `capture_website_screenshots.py` | Drives the iOS Simulator to capture Help Center screenshots (macOS only). `--locale` captures in another interface language. |
| `check_translations.py` | Gates translated pages on terminology, structural parity, typography, and staleness. |
| `sync_glossary.py` | Snapshots product terminology from the app repo into `glossary.json`. |
| `locales.py` | Shared locale registry, marker resolution, dates, and translation hashing. |
| `check_external_sources.py` | Weekly link check over the official sources articles cite. |
| `report_source_health.py` | Turns that report into the GitHub issue the weekly workflow maintains. |
| `sync_changelog.py` | Copies release cards from the app repo into `changelog.html`. |
| `audit_site.py` | The site auditor, and the shared HTML parser other scripts import. |
| `serve_site.py` | Local preview server. |

Every build script has a `--check` mode that verifies without writing. CI runs all of them.

## CI

`.github/workflows/site-audit.yml` runs the audit and every `--check` on pull requests and pushes to `main`. It runs entirely from the checkout, with no secrets.

The same workflow runs a weekly source monitor: it re-checks the official government sources the articles cite and maintains a single GitHub issue listing any that moved or died, closing it when they all resolve again. Sites that merely block CI runners (401/403/429) are recorded but never raise the issue.

Editorial process, brand and voice, and review notes live in a separate private repo and are git-ignored here by name. See [CLAUDE.md](CLAUDE.md) for the conventions agents follow in this repo.
