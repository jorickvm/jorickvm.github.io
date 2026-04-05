Landing page for [AtlasDays](https://atlasdays.app) — a private iPhone app for tracking trips, visa days, and residency thresholds.

## Website launch TODO

### Homepage assets

Current live homepage assets:

- `assets/home/home-hero-dashboard.webp`
- `assets/home/home-hero-tracker-detail.webp`
- `assets/home/home-proof-timeline.webp`
- `assets/home/home-proof-import-preview.webp`
- `assets/home/home-proof-privacy.webp`

Current share-metadata assets:

- `assets/home/home-hero-dashboard.png`
- `assets/home/home-proof-map-country.png`

Older homepage variants that are no longer referenced by the site live in `assets/obsolete/home/`.

## AI article images

The repo now includes a no-dependency generator for `Learn` and `Help` article images.

Setup:
1. Copy `.env.example` to `.env.local`
2. Paste your `OPENAI_API_KEY`
3. Edit `article-image-plan.json` if you want to move image placements or add slot notes

Defaults:
- `Learn`: 1 hero + 2 body images per article
- `Help`: 1 hero + 1 body image per article
- model: `gpt-image-1-mini`
- quality: `medium`
- output: `webp`
- size: `1536x1024`

Dry run:
```bash
python3 scripts/generate_article_images.py --section learn --limit 2 --dry-run --show-prompts
```

Sync placement markers into article HTML:
```bash
python3 scripts/sync_article_image_markers.py
```

Generate images:
```bash
python3 scripts/generate_article_images.py --section learn
python3 scripts/generate_article_images.py --section help
```

Insert generated images into article HTML:
```bash
python3 scripts/insert_article_images.py
```

Useful options:
- `--slug schengen-90-180-rule` to target one article
- `--limit 3` to test a few articles first
- `--force` to regenerate existing files
- `--show-prompts` to inspect the exact prompt text
- `--check` on `sync_article_image_markers.py` to verify markers without rewriting files
- `--captions` on `insert_article_images.py` to render visible captions
- `--strict` on `insert_article_images.py` to fail if any slot asset is missing

Output:
- placement plan lives in `article-image-plan.json`
- images land in `assets/article-images/<section>/<slug>/`
- the prompt + asset catalog is written to `assets/article-images/catalog.json`
- slot names are `hero`, `body-1`, and optionally `body-2`
- the catalog includes suggested placement, section anchors, intro context, and extracted section summaries
- markers in the HTML use `<!-- ARTICLE_IMAGE:hero -->`, `<!-- ARTICLE_IMAGE:body-1 -->`, etc.

## Future help articles: program-specific tracking guides

How to track specific residency/tax programs in the app. Each article would explain the rule and walk through setting up a tracker.

- **US Foreign Earned Income Exclusion (FEIE) / Bona Fide Residence** — 330/365 days outside the US (Physical Presence Test)
- **IRS Substantial Presence Test** — 183-day weighted formula across 3 years
- **UK Statutory Residence Test (SRT)** — automatic overseas/UK tests + sufficient ties
- **Portugal NHR / Malaysia MM2H / New Zealand** — rolling 365-day windows
- **Cyprus 60-day rule** — non-domiciled tax residency via 60 days presence

---

Context used for prompting:
- page `<title>`
- meta description
- on-page `<h1>`
- first real intro paragraph
- article `h2` sections and their first body paragraph
- explicit slot placements and optional notes from `article-image-plan.json`
