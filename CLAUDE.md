# atlasdays.app website – Claude Code Context

Marketing and support website for AtlasDays (`atlasdays.app`). Static HTML: no build step, no framework. Hand-authored HTML served directly via GitHub Pages; HTML changes go live as-is.

## Structure
- Root HTML: homepage, about, privacy, terms, support
- `learn/` long-form articles; `help/` how-to guides
- `assets/` images + CSS (`assets/obsolete/` = deprecated); `scripts/` Python dev tooling (not deployed)

## This repo is public – some files are intentionally git-ignored
Internal docs (strategy, brand/voice, editorial and release process, audits, and the full agent-instruction / build-workflow files) live in a **separate private repo** – they are not in this repo. Do not create or commit them here; `.gitignore` blocks them by name.

The following are **git-ignored on purpose** but must stay on disk for the Python build scripts to run. Do not `git add -f` or commit them:
- `_site-src/data/editorial.json`
- `_site-src/data/conversion.json`
- `_site-src/data/content-clusters.json`
- `article-image-plan.json`

Their only versioned copies live in the private repo. If you change them, back them up there.
