# atlasdays.app Website - Codex Instructions

## What This Project Is
This is the marketing and support website for AtlasDays at `atlasdays.app`. It is static HTML with no build step and no framework. Pages are hand-authored HTML files. The repo also contains Python tooling for AI-generated article images.

## Structure
- Root HTML files: homepage, about, privacy, terms, and support.
- `learn/`: long-form articles about visa rules, residency tracking, and related topics.
- `help/`: shorter how-to articles.
- `assets/`: images, CSS, and brand files. Deprecated assets live in `assets/obsolete/`.
- `scripts/`: Python tooling for article image generation. These are dev-time tools and are not deployed as app code.

## Article Image Generation
Image generation requires `OPENAI_API_KEY` in `.env.local`; copy from `.env.example` if needed.

```bash
# Sync placement markers into article HTML first
python3 scripts/sync_article_image_markers.py

# Dry run to preview prompts
python3 scripts/generate_article_images.py --section learn --limit 2 --dry-run --show-prompts

# Generate images
python3 scripts/generate_article_images.py --section learn
python3 scripts/generate_article_images.py --section help

# Insert generated images into HTML
python3 scripts/insert_article_images.py
```

Useful flags include `--slug schengen-90-180-rule`, `--limit 3`, `--force`, and `--strict`.

Placement config lives in `article-image-plan.json`. Generated images land in `assets/article-images/<section>/<slug>/`. Markers in HTML use comments like `<!-- ARTICLE_IMAGE:hero -->` and `<!-- ARTICLE_IMAGE:body-1 -->`.

## Pre-Commit Hook
`scripts/pre-commit` runs automatically on commit. Check it if commits are rejected unexpectedly.

## Deployment
Static files are served directly. There is no build step; changes to HTML go live as-is.
