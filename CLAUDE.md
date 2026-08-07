# atlasdays.app website — agent context

Marketing and support website for AtlasDays (`atlasdays.app`), served by GitHub Pages straight from committed HTML. No framework.

This is the **public** repo, so this file is deliberately slim. The full working instructions live in the private `atlasdays-internal/CLAUDE.md` — read that one when you have it.

## Articles are generated, not hand-authored

Deploying has no build step, but **authoring does**, and this is the easy mistake to make. Pages under `learn/` and `help/` are rendered by `scripts/build_site.py` from `_site-src/` (content fragments in `_site-src/content/`, data in `_site-src/data/`, layout in `_site-src/templates/`) and the rendered output is committed.

Edit the source fragment under `_site-src/content/`, then rebuild. Editing a file in `learn/` or `help/` directly will be overwritten by the next build, and `python3 scripts/build_site.py --check` fails when committed HTML no longer matches what the sources produce.

Only `index.html`, `support.html`, and `404.html` are genuinely hand-authored and go live as-is. `about.html`, `privacy.html`, and `terms.html` sit at the root but are generated too: they are listed in `_site-src/data/pages.json` and built from `_site-src/content/pages/`, so edit the fragment and rebuild. `changelog.html` is owned by the release workflow, which mirrors it from the AtlasDays repo.

## Structure

- Root HTML: homepage, about, privacy, terms, support
- `learn/` long-form articles, `help/` how-to guides — both generated, see above
- `_site-src/` the sources those are generated from
- `assets/` images and CSS (`assets/obsolete/` is deprecated); `scripts/` Python dev tooling, not deployed

## This repo is public — some files are git-ignored on purpose

Internal docs (strategy, brand and voice, editorial and release process, audits, and the full agent-instruction file) live in a separate private repo, not here. Do not create or commit them; `.gitignore` blocks them by name, including `AGENTS.md`.

These are git-ignored deliberately but must stay on disk for the Python scripts to run. Do not `git add -f` or commit them:
- `_site-src/data/editorial.json`
- `_site-src/data/conversion.json`
- `_site-src/data/content-clusters.json`
- `article-image-plan.json`

Their only versioned copies live in the private repo. If you change them, back them up there.

## User-facing copy

Never use em dashes in anything a reader sees. Use periods or commas.

## Keeping this file honest

Correct **verifiable inventory** here when you find it stale — paths, script names, directory names — after checking with a command, and say so in your response.

Do not self-edit policy (what is public vs private, what is git-ignored). If you think a rule here is outdated or you know a better approach, do not silently follow it and do not silently break it: name it, say why and what you would do instead, and ask Jorick how firm it is before deviating.
