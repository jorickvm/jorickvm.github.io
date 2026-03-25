Landing page for [AtlasDays](https://atlasdays.app) — a private iPhone app for tracking trips, visa days, and residency thresholds.

## Website launch TODO

### Homepage screenshot checklist

The homepage is now wired to these portrait iPhone screenshots.

1. `Hero primary`
   File target: `assets/home-hero-dashboard.png`
   Needed state: dashboard overview with tracker cards, top stats, and the mini map visible in the same shot.

2. `Hero secondary`
   File target: `assets/home-hero-tracker-detail.png`
   Needed state: one tracker detail view with used days, remaining days, and a clear forward-looking insight.

3. `Proof timeline`
   File target: `assets/home-proof-timeline.png`
   Needed state: timeline/history with realistic trips, visible day badges, and enough variety to show the app is not a toy dataset.

4. `Proof map`
   File target: `assets/home-proof-map-country.png`
   Needed state: full map with visited countries highlighted and a country detail sheet open.

5. `Proof tracker presets`
   File target: `assets/home-proof-tracker-presets.png`
   Needed state: preset picker showing `Residence`, `Schengen`, `Visa Limit`, and `Travel Goal`.

6. `Proof trip modes`
   File target: `assets/home-proof-trip-modes.png`
   Needed state: trip form showing the difference between `Exact Dates` and `Month & Year`.
   Bonus: include `Dates Unknown` if it still reads clearly in one capture.

7. `Proof import`
   File target: `assets/home-proof-import.png`
   Needed state: CSV import or import-preview flow with mapped columns.
   Bonus: include the AI helper if it looks polished enough for public marketing.

8. `Proof privacy`
   File target: `assets/home-proof-privacy.png`
   Needed state: privacy/location onboarding or permission flow that clearly reinforces on-device processing and optional iCloud sync.

### Notes

- The hero supports theme-specific screenshots:
  - dark: `assets/home-hero-dashboard.png`, `assets/home-hero-tracker-detail.png`
  - light: `assets/home-hero-dashboard-light.png`, `assets/home-hero-tracker-light.png`
- The proof section uses `timeline`, `map`, `tracker presets`, `trip modes`, and `import`.
- The privacy section uses `assets/home-proof-privacy.png`.
- Remaining launch work is image optimization and a browser QA pass after deployment.

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

Context used for prompting:
- page `<title>`
- meta description
- on-page `<h1>`
- first real intro paragraph
- article `h2` sections and their first body paragraph
- explicit slot placements and optional notes from `article-image-plan.json`
