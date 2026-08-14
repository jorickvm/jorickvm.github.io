# atlasdays.app website — agent context

Marketing and support website for AtlasDays (`atlasdays.app`), served by GitHub Pages straight from committed HTML. No framework.

This is the **public** repo, so this file is deliberately slim. The full working instructions live in the private `~/Projects/atlasdays-internal/CLAUDE.md` — read that one when you have it. It also carries a task-to-document table for the private guides: `RESIDENCY_ARTICLES.md` before writing a visa or tax-residency Learn article, `EDITORIAL_CHECKLIST.md` before a substantive fact update, `SCREENSHOT_GUIDE.md` before capturing a Help Center screenshot, `TRANSLATION_HANDOFF.md` before adding a language, `TRANSLATION_GUIDELINES.md` before writing or editing any translated copy on this site.

Brand and voice live in the app repo: `~/Projects/AtlasDays/AtlasDays/Docs/reference/BRAND.md` is canonical for this site too.

## Articles are generated, not hand-authored

Deploying has no build step, but **authoring does**, and this is the easy mistake to make. Pages under `learn/` and `help/` are rendered by `scripts/build_site.py` from `_site-src/` (content fragments in `_site-src/content/`, data in `_site-src/data/`, layout in `_site-src/templates/`) and the rendered output is committed.

Edit the source fragment under `_site-src/content/`, then rebuild. Editing a file in `learn/` or `help/` directly will be overwritten by the next build, and `python3 scripts/build_site.py --check` fails when committed HTML no longer matches what the sources produce.

Not everything under `learn/` is generated, despite the above. Two meta-refresh redirect stubs (`how-to-use-atlasdays.html`, `icloud-sync-travel-tracking.html`) are absent from `articles.json`, so a rebuild never touches them and `--check` never guards them. Edit those in place. (Ten tax-residency guides used to be in this state too; they were registered in `articles.json` in August 2026 and are now fully generated.)

Besides those, `index.html`, `support.html`, and `404.html` are genuinely hand-authored and go live as-is, as are the four in-app alias stubs under `app/` (`changelog/`, `help/`, `privacy/`, `terms/index.html`), which redirect via `assets/js/app-page-alias.js`. `about.html`, `privacy.html`, and `terms.html` sit at the root but are generated too: they are listed in `_site-src/data/pages.json` and built from `_site-src/content/pages/`, so edit the fragment and rebuild. `changelog.html` is shared with the AtlasDays repo, which owns the release notes but not the page. `scripts/sync_changelog.py` replaces only the contents of `<div class="release-stack">`, so a release updates the cards and nothing else.

**The app repo's `update-changelog.yml` does not currently use it.** It runs `cp changelog.html website/changelog.html`, a whole-file copy, which on 2026-08-08 reverted the en-dash title and stripped the footer, skip link, all six og/twitter image tags, the content stylesheet, and the `?theme=` bootstrap, turning the site audit red and publishing a broken page. Until that workflow is changed to run `python3 scripts/sync_changelog.py <app-repo>/changelog.html`, every release re-breaks this page; the site audit catches it, but only after it deploys. Everything else on that page (tokens, header, footer, social metadata, the `?theme=` bootstrap) is this repo's and survives a release. It used to `cp` the whole file across, which reverted all of that each time. The release-card markup must stay identical in both repos.

## Structure

- Root HTML: homepage, about, privacy, terms, support
- `learn/` long-form articles, `help/` how-to guides — both generated, see above
- `_site-src/` the sources those are generated from
- `assets/` images and CSS; `scripts/` Python dev tooling (like everything tracked in a Pages repo it is technically fetchable at atlasdays.app/scripts/…, just never linked)

## This repo is public — internal docs are git-ignored on purpose

Internal docs (strategy, brand and voice, editorial and release process, audits, and the full agent-instruction file) live in a separate private repo, not here. Do not create or commit them; `.gitignore` blocks them by name, including `AGENTS.md`.

The build data used to be split the same way, but since August 2026 `_site-src/data/editorial.json`, `_site-src/data/content-clusters.json`, and `EDITORIAL_REVIEW_QUEUE.md` are committed here (Jorick approved the change): all three are deterministic output of the public `build_content_governance.py` over the public `articles.json`, so keeping them private protected nothing. The Site audit workflow runs entirely from the checkout — the private-repo fetch and its `INTERNAL_DATA_PAT` secret are gone. `conversion.json` was deleted outright; nothing read it.

## Article images: only Help Center screenshots

Learn articles carry no illustrations. The AI image generator (OpenAI-backed) and its plan, catalog, markers, and 24 generated Learn illustrations were removed in August 2026 — Jorick did not like the output, and reference articles about day-count rules do not need decoration. Do not reintroduce generated imagery.

What remains under `assets/article-images/` is `help/` only: real product screenshots, declared as `screenshot_slots` on each Help record in `articles.json` and wired in by `scripts/sync_help_screenshots.py`. Country and jurisdiction articles carry a `title-flag` image beside the H1; that is the only illustration Learn uses.

## User-facing copy

Never use em dashes in anything a reader sees. Replace them with en dashes (`–`), or reword with periods or commas. Jorick's reasoning (2026-08): em dashes read as AI-written text; the en dash is deliberately kept even where an em dash would be the typographically correct choice.

## Translations

The Help Center ships Japanese at `/ja/help/…`, generated by the same build from `_site-src/content/ja/` plus the overlay registry `_site-src/data/articles.ja.json`. README has the mechanics; the rules that matter here:

- **Never edit a file under `ja/` (or any other locale directory) directly.** They are generated, exactly like `help/` and `learn/`.
- **A translation supplies prose only.** Paths, canonicals, hreflang, JSON-LD, og tags, next-step URLs, and the rendered date are derived from the English record. Setting one in an overlay is a build error, and that is the point: a translation cannot invent a URL or a JSON-LD graph in a language nobody here reads.
- **The app is the terminology authority, not this repo.** `_site-src/data/glossary.json` is a generated snapshot of the AtlasDays app's shipped strings and its accepted-terminology tables; regenerate it with `python3 scripts/sync_glossary.py` when the app repo moves. A help article naming a button differently from the app is worse than no article, and nobody here can see that by reading.
- **Editing English copy breaks its translations on purpose.** Each overlay pins the hash of the English fragment and metadata it came from, and the build refuses until the translation catches up. For an edit that genuinely does not change meaning, add a `stale_ack` with the new hash, a reason, and an `expires` date.
- `scripts/check_translations.py` runs first in CI and enforces terminology, structural parity with the English source, typography, and staleness. It is the substitute for a reviewer, not a proof of quality.

### Japanese punctuation, and the em-dash rule

The house rule below says to replace an em dash with an en dash. That was written for English and misfires in Japanese, which has neither mark: its parenthetical break is conventionally an em dash, which the rule bans, and the en dash is not Japanese punctuation at all. The guidelines already require full-width Japanese punctuation in prose, so the ruling is:

- U+2014 stays banned in every language, and `check_translations.py` now enforces it (it never was before).
- U+2013 is also banned inside Japanese copy. Japanese uses neither dash: split the sentence with `。`, or use `（…）` / `「…」`.
- Title separator is per locale: `" – "` in English, `"｜"` in Japanese.

The privacy and terms pages are a **separate, older system**: localized in `assets/js/legal-translations.js`, keyed by language code, with the switcher registry in `assets/js/legal-language.js`. It swaps `main.innerHTML` at runtime, so it has one URL, no per-language canonical, and no search visibility. Leave it alone for now: the iOS app deep-links into it with `?lang=`. It should eventually be absorbed into the locale system above, but that needs app-repo coordination and is Jorick's call. Its Japanese legal text is a useful reviewed reference for register and terminology.

Before writing or editing any translation here, read `~/Projects/AtlasDays/AtlasDays/Docs/reference/translation-guidelines.md` and follow it. It lives in the app repo but explicitly covers this surface, under "Website legal pages (separate repo)". It sets legal text as its narrowest-freedom category (translate faithfully, do not shorten or soften), fixes the form of address per language, and carries typography rules that are easy to destroy with a scripted edit, such as the nonbreaking space French requires before `:`. Copying the register of the text already on the page is not a substitute for reading it.

When the English wording changes, update `_site-src/content/pages/` first, rebuild, then move every localized copy in the same commit so no language silently drifts.

## Keeping this file honest

Correct **verifiable inventory** here when you find it stale — paths, script names, directory names — after checking with a command, and say so in your response.

Do not self-edit policy (what is public vs private, what is git-ignored). If you think a rule here is outdated or you know a better approach, do not silently follow it and do not silently break it: name it, say why and what you would do instead, and ask Jorick how firm it is before deviating.
