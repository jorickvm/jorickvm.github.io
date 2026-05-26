# atlasdays.app website — Claude Code Context

## What this project is
Marketing and support website for AtlasDays (`atlasdays.app`). Static HTML — no build step, no framework. Pages are hand-authored HTML files. The repo also contains Python tooling for AI-generated article images.

## Structure
- Root HTML files: homepage, about, privacy, terms, support
- `learn/` — long-form articles (visa rules, residency tracking, etc.)
- `help/` — shorter how-to articles
- `assets/` — images, CSS, brand files; `assets/obsolete/` for deprecated assets
- `scripts/` — Python tooling for article image generation (dev-time only, not deployed)

## Article image generation
Requires `OPENAI_API_KEY` in `.env.local` (copy from `.env.example`).

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

Useful flags: `--slug schengen-90-180-rule`, `--limit 3`, `--force`, `--strict`.

Placement config: `article-image-plan.json`. Generated images land in `assets/article-images/<section>/<slug>/`. Markers in HTML use `<!-- ARTICLE_IMAGE:hero -->`, `<!-- ARTICLE_IMAGE:body-1 -->`, etc.

## Inbox
`assets/inbox/` is a staging folder for files to be added to the project (screenshots, images, etc.). When Jorick says "I put it in inbox", look here.

## Pre-commit hook
`scripts/pre-commit` runs automatically on commit. Check it if commits are rejected unexpectedly.

## Deployment
Static files served directly — no build step needed. Changes to HTML go live as-is.
