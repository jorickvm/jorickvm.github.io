# atlasdays.app website — agent context

Marketing and support website for AtlasDays (`atlasdays.app`), served by GitHub Pages straight from committed HTML. No framework.

This is the **public** repo, so this file is deliberately slim. The full working instructions live in the private `atlasdays-internal/CLAUDE.md` — read that one when you have it.

## Articles are generated, not hand-authored

Deploying has no build step, but **authoring does**, and this is the easy mistake to make. Pages under `learn/` and `help/` are rendered by `scripts/build_site.py` from `_site-src/` (content fragments in `_site-src/content/`, data in `_site-src/data/`, layout in `_site-src/templates/`) and the rendered output is committed.

Edit the source fragment under `_site-src/content/`, then rebuild. Editing a file in `learn/` or `help/` directly will be overwritten by the next build, and `python3 scripts/build_site.py --check` fails when committed HTML no longer matches what the sources produce.

Not everything under `learn/` is generated, despite the above. Two meta-refresh redirect stubs (`how-to-use-atlasdays.html`, `icloud-sync-travel-tracking.html`) are absent from `articles.json`, so a rebuild never touches them and `--check` never guards them. Edit those in place. (Ten tax-residency guides used to be in this state too; they were registered in `articles.json` in August 2026 and are now fully generated.)

Besides those, `index.html`, `support.html`, and `404.html` are genuinely hand-authored and go live as-is, as are the four in-app alias stubs under `app/` (`changelog/`, `help/`, `privacy/`, `terms/index.html`), which redirect via `assets/js/app-page-alias.js`. `about.html`, `privacy.html`, and `terms.html` sit at the root but are generated too: they are listed in `_site-src/data/pages.json` and built from `_site-src/content/pages/`, so edit the fragment and rebuild. `changelog.html` is shared with the AtlasDays repo, which owns the release notes but not the page. Its `update-changelog.yml` workflow runs `scripts/sync_changelog.py` here, replacing only the contents of `<div class="release-stack">`. Everything else on that page (tokens, header, footer, social metadata, the `?theme=` bootstrap) is this repo's and survives a release. It used to `cp` the whole file across, which reverted all of that each time. The release-card markup must stay identical in both repos.

## Structure

- Root HTML: homepage, about, privacy, terms, support
- `learn/` long-form articles, `help/` how-to guides — both generated, see above
- `_site-src/` the sources those are generated from
- `assets/` images and CSS; `scripts/` Python dev tooling (like everything tracked in a Pages repo it is technically fetchable at atlasdays.app/scripts/…, just never linked)

## This repo is public — internal docs are git-ignored on purpose

Internal docs (strategy, brand and voice, editorial and release process, audits, and the full agent-instruction file) live in a separate private repo, not here. Do not create or commit them; `.gitignore` blocks them by name, including `AGENTS.md`.

The build data used to be split the same way, but since August 2026 `_site-src/data/editorial.json`, `_site-src/data/content-clusters.json`, `EDITORIAL_REVIEW_QUEUE.md`, and `article-image-plan.json` are committed here (Jorick approved the change): the first three are deterministic output of the public `build_content_governance.py` over the public `articles.json`, so keeping them private protected nothing, and the image plan is creative briefs for illustrations, not strategy. The Site audit workflow runs entirely from the checkout — the private-repo fetch and its `INTERNAL_DATA_PAT` secret are gone. `conversion.json` was deleted outright; nothing read it.

## User-facing copy

Never use em dashes in anything a reader sees. Use periods or commas.

## Translations

The privacy and terms pages are localized in `assets/js/legal-translations.js`, keyed by language code, with the switcher registry in `assets/js/legal-language.js`.

Before writing or editing any translation here, read `~/Projects/AtlasDays/AtlasDays/Docs/reference/translation-guidelines.md` and follow it. It lives in the app repo but explicitly covers this surface, under "Website legal pages (separate repo)". It sets legal text as its narrowest-freedom category (translate faithfully, do not shorten or soften), fixes the form of address per language, and carries typography rules that are easy to destroy with a scripted edit, such as the nonbreaking space French requires before `:`. Copying the register of the text already on the page is not a substitute for reading it.

When the English wording changes, update `_site-src/content/pages/` first, rebuild, then move every localized copy in the same commit so no language silently drifts.

## Keeping this file honest

Correct **verifiable inventory** here when you find it stale — paths, script names, directory names — after checking with a command, and say so in your response.

Do not self-edit policy (what is public vs private, what is git-ignored). If you think a rule here is outdated or you know a better approach, do not silently follow it and do not silently break it: name it, say why and what you would do instead, and ask Jorick how firm it is before deviating.
