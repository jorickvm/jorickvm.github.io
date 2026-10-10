# atlasdays.app website — agent context

Marketing and support website for AtlasDays (`atlasdays.app`), served by GitHub Pages straight from committed HTML. No framework.

This is the **public** repo, so this file is deliberately slim. The full working instructions live in the private `~/Projects/atlasdays-internal/CLAUDE.md` — read that one when you have it. It also carries a task-to-document table for the private guides: `RESIDENCY_ARTICLES.md` before writing a visa or tax-residency Learn article, `EDITORIAL_CHECKLIST.md` before a substantive fact update, `SCREENSHOT_GUIDE.md` before capturing a Help Center screenshot, `TRANSLATION_HANDOFF.md` before adding a language, `TRANSLATION_GUIDELINES-web.md` before writing or editing any translated copy on this site.

Brand and voice live in the app repo: `~/Projects/AtlasDays/AtlasDays/Docs/reference/BRAND.md` is canonical for this site too.

## Articles are generated, not hand-authored

Deploying has no build step, but **authoring does**, and this is the easy mistake to make. Pages under `learn/` and `help/` are rendered by `scripts/build_site.py` from `_site-src/` (content fragments in `_site-src/content/`, data in `_site-src/data/`, layout in `_site-src/templates/`) and the rendered output is committed.

Edit the source fragment under `_site-src/content/`, then rebuild. Editing a file in `learn/` or `help/` directly will be overwritten by the next build, and `python3 scripts/build_site.py --check` fails when committed HTML no longer matches what the sources produce.

Merged Learn pages in `_site-src/data/redirects.json` generate redirects in English and every locale, covered by `build_site.py --check`. Three legacy meta-refresh redirect stubs (`day-limits.html`, `how-to-use-atlasdays.html`, `icloud-sync-travel-tracking.html`) are absent from `articles.json`, so a rebuild never touches them and `--check` never guards them. Edit those in place. Because nothing rebuilds them, they are also the only `learn/` pages whose `content_hash` the audit baseline still compares, alongside the four `app/` alias stubs. (Ten tax-residency guides used to be in this state too; they were registered in `articles.json` in August 2026 and are now fully generated.)

Besides those, the four in-app alias stubs under `app/` (`changelog/`, `help/`, `privacy/`, `terms/index.html`) are genuinely hand-authored and go live as-is, redirecting via `assets/js/app-page-alias.js`. Every root HTML page is generated: `_site-src/data/pages.json` lists all ten (`index.html`, `404.html`, `support.html`, `about.html`, `privacy.html`, `terms.html`, `visa-limits.html`, `residency-thresholds.html`, `travel-history.html`, `changelog.html`), built from `_site-src/content/pages/`, so edit the fragment and rebuild. `index.html`, `404.html`, and `support.html` were the last hand-authored holdouts; the Dutch localization commit (August 2026) moved them into `pages.json` so they could be translated. `changelog.html` is shared with the AtlasDays repo, which owns the release notes but not the page, and is served in English only (see Translations). `scripts/sync_changelog.py` replaces only the contents of `<div class="release-stack">` in the fragment, so a release updates the cards and nothing else. It writes the fragment, not the published page, so `build_site.py` has to run after it or nothing reaches the site.

**The app repo's `update-changelog.yml` uses the source-preserving sync.** It checks out both repos, runs `python3 scripts/sync_changelog.py ../changelog.html` and `python3 scripts/build_site.py`, then validates the generated output and translations. Preserve this flow: copying the whole page would replace website-owned chrome and metadata. The release-card markup must stay identical in both repos.

## Structure

- Root HTML: homepage, about, privacy, terms, support
- `learn/` long-form articles, `help/` how-to guides — both generated, see above
- `_site-src/` the sources those are generated from
- `assets/` images and CSS; `scripts/` Python dev tooling (like everything tracked in a Pages repo it is technically fetchable at atlasdays.app/scripts/…, just never linked)
- `shift/` and `<code>/shift/`: frozen legacy copies of the privacy and support pages for **Shift**, a different iOS app of Jorick's (`~/Projects/Shift/`). The live pages are on bysteed.com (`~/Projects/bysteed/shift/`). App Store Connect points at these copies until Shift 2.6 is live, so they stay up at least until then (removal planned for about November 2026); do not edit them, and do not add new ones.

## This repo is public — internal docs are git-ignored on purpose

Internal docs (strategy, brand and voice, editorial and release process, audits, and the full agent-instruction file) live in a separate private repo, not here. Do not create or commit them; `.gitignore` blocks them by name, including `AGENTS.md`.

The build data used to be split the same way, but since August 2026 `_site-src/data/editorial.json`, `_site-src/data/content-clusters.json`, and `EDITORIAL_REVIEW_QUEUE.md` are committed here (Jorick approved the change): all three are deterministic output of the public `build_content_governance.py` over the public `articles.json`, so keeping them private protected nothing. The Site audit workflow runs entirely from the checkout — the private-repo fetch and its `INTERNAL_DATA_PAT` secret are gone. `conversion.json` was deleted outright; nothing read it.

## Article images: only Help Center screenshots

Learn articles carry no illustrations. The AI image generator (OpenAI-backed) and its plan, catalog, markers, and 24 generated Learn illustrations were removed in August 2026 — Jorick did not like the output, and reference articles about day-count rules do not need decoration. Do not reintroduce generated imagery.

What remains under `assets/article-images/` is `help/` only: real product screenshots, declared as `screenshot_slots` on each Help record in `articles.json` and wired in by `scripts/sync_help_screenshots.py`. Country and jurisdiction articles carry a `title-flag` image beside the H1; that is the only illustration Learn uses.

## User-facing copy

Never use em dashes in **English** copy a reader sees. Replace them with en dashes (`–`), or reword with periods or commas. Jorick's reasoning (2026-08): em dashes read as AI-written text; the en dash is deliberately kept even where an em dash would be the typographically correct choice. The rule was scoped to English on 2026-08-21: it is a house-style rule about how English reads, not a typographic one, so it does not travel to languages that own the mark.

**Russian, Ukrainian, and Spanish are exempt** (`ru`/`uk` Jorick 2026-08-17, `es` 2026-08-21). The reasoning above is about English, where the mark signals AI authorship. In Russian and Ukrainian U+2014 is the тире, the ordinary parenthetical and zero-copula dash (`AtlasDays — это инструмент учёта`), and an en dash there looks foreign rather than clean. Spanish is the same shape but weaker: the raya is the standard mark for an inciso, though Spanish can usually reword the way English does, so rewording stays the better default there. `check_translations.py` skips the em-dash check for `ru`, `uk`, and `es`; it still enforces it everywhere else. Do not bulk-replace U+2014 in those languages, in this repo or the app's catalogs.

## Translations

The published locales and their coverage are declared in `_site-src/data/locales.json`; each uses `_site-src/content/<code>/` and `_site-src/data/articles.<code>.json`. README has the mechanics; the rules that matter here:

- **Never edit a file under `ja/` (or any other locale directory) directly.** They are generated, exactly like `help/` and `learn/`.
- **A translation supplies prose only.** Paths, canonicals, hreflang, JSON-LD, og tags, next-step URLs, and the rendered date are derived from the English record. Setting one in an overlay is a build error, and that is the point: a translation cannot invent a URL or a JSON-LD graph in a language nobody here reads.
- **The app is the terminology authority, not this repo.** `_site-src/data/glossary.json` is a generated snapshot of the AtlasDays app's shipped strings and its accepted-terminology tables; regenerate it with `python3 scripts/sync_glossary.py` when the app repo moves. A help article naming a button differently from the app is worse than no article, and nobody here can see that by reading.
- **Editing English copy breaks its translations on purpose.** Each overlay pins the hash of the English fragment and metadata it came from, and the build refuses until the translation catches up. For an edit that genuinely does not change meaning, add a `stale_ack` with the new hash, a reason, and an `expires` date.
- **Not every page gets translated, and the changelog never does.** A locale with `coverage: complete` must cover every English page; the deliberate exceptions are listed under `untranslated` in `locales.json`. `changelog.html` is there on purpose. Its release cards come from the AtlasDays repo on every release, so a translated changelog pins a hash that each release invalidates and blocks the build until the new cards are retranslated, which made a release able to turn the site red on its own. Do not add an overlay for a page listed there: `check_translations.py` rejects it, and rejects a listed page that is not an English source, so the list cannot rot quietly. Dutch shipped one until August 2026; `/nl/changelog` is gone and Dutch chrome links to `/changelog`.
- `scripts/check_translations.py` runs first in CI and enforces terminology, structural parity with the English source, typography, and staleness. It is the substitute for a reviewer, not a proof of quality.

### Japanese punctuation, and the em-dash rule

The house rule below says to replace an em dash with an en dash. That was written for English and misfires in Japanese, which has neither mark: its parenthetical break is conventionally an em dash, which the rule bans, and the en dash is not Japanese punctuation at all. The guidelines already require full-width Japanese punctuation in prose, so the ruling is:

- U+2014 stays banned in English and every other language except Russian, Ukrainian, and Spanish, and `check_translations.py` enforces it (it never did before). Those three own the mark and are exempt, see User-facing copy above.
- U+2013 is also banned inside Japanese copy. Japanese uses neither dash: split the sentence with `。`, or use `（…）` / `「…」`.
- Title separator is per locale: `" – "` in English, `"｜"` in Japanese.

The localized privacy and terms pages are generated locale pages like every other translation: `/<code>/privacy` and `/<code>/terms`, built from `_site-src/content/<code>/pages/`. The iOS app deep-links to the English URL with `?lang=`, and the page head redirects that to the locale route for a published locale. The support address in their contact link is assembled by `assets/js/navigation.js`, which every locale loads.

Before writing or editing any translation here, read `~/Projects/AtlasDays/AtlasDays/Docs/reference/translation-guidelines.md` and follow it. It lives in the app repo but explicitly covers this surface, under "Website legal pages (separate repo)". It sets legal text as its narrowest-freedom category (translate faithfully, do not shorten or soften), fixes the form of address per language, and carries typography rules that are easy to destroy with a scripted edit, such as the nonbreaking space French requires before `:`. Copying the register of the text already on the page is not a substitute for reading it.

When the English wording changes, update `_site-src/content/pages/` first, rebuild, then move every localized copy in the same commit so no language silently drifts.

## Keeping this file honest

Correct **verifiable inventory** here when you find it stale — paths, script names, directory names — after checking with a command, and say so in your response.

Do not self-edit policy (what is public vs private, what is git-ignored). If you think a rule here is outdated or you know a better approach, do not silently follow it and do not silently break it: name it, say why and what you would do instead, and ask Jorick how firm it is before deviating.
