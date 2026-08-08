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

## Adding or editing an article

1. Edit the fragment under `_site-src/content/<section>/`, or add a new one.
2. Register it in `_site-src/data/articles.json`, and add a route to `routes.json`.
3. Rebuild, in this order (each output feeds the next):

```bash
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
| `sync_help_screenshots.py` | Swaps a Help screenshot placeholder for a `<figure>` once its WebP lands. |
| `capture_website_screenshots.py` | Drives the iOS Simulator to capture Help Center screenshots (macOS only). |
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
