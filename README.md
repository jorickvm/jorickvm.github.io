# atlasdays.app

Marketing and support website for [AtlasDays](https://atlasdays.app), a private iPhone app for tracking trips, visa days, and residency thresholds.

Static HTML: no build step, no framework. Pages are hand-authored and served directly via GitHub Pages, so changes to HTML go live as-is.

## Structure

- Root HTML files: homepage, about, privacy, terms, support
- `learn/` – long-form articles on visa rules and residency
- `help/` – shorter how-to guides
- `assets/` – images and CSS (`assets/obsolete/` holds deprecated assets)
- `scripts/` – Python dev-time tooling (article image generation); not deployed

See [CLAUDE.md](CLAUDE.md) for repo conventions.
