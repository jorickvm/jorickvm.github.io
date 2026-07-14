# AtlasDays Website Implementation Plan

Date: July 14, 2026
Source review: `WEBSITE_REVIEW_2026-07-14.md`

## Implementation status — July 14, 2026

The repository-side program is implemented and all automated gates pass. This includes the dark-default rule, baseline/audit/CI, static generator, shared navigation/footer, image pipeline, 13-scenario app screenshot harness, social cards, testimonial replacement, editorial/cluster manifests, generated related links, local Help/Learn search, route outputs, scheduled source monitoring, and maintenance checklists.

The remaining queue is deliberately not represented as mechanically complete:

- manual browser and VoiceOver testing requires an interactive browser/accessibility environment;
- legacy factual reviews recorded only a month, so exact verification dates remain queued until each official source is substantively reread;
- App Store conversion campaign activation requires the account-owned provider/campaign links from App Store Connect;
- Flighty, CSV, Photo Import, PDF preview, and widget captures depend on deterministic coordinator data or OS-owned surfaces beyond the 13 working core scenarios.

See `EDITORIAL_REVIEW_QUEUE.md`, `CONVERSION_MEASUREMENT.md`, `_site-src/data/screenshots.json`, and `RELEASE_WEBSITE_CHECKLIST.md` for those explicit follow-ups. No date, testimonial, or conversion signal has been fabricated to make the checklist appear complete.

## Objective

Implement every recommendation from the July website review while preserving the strongest parts of the current site:

- static, fast, directly deployable HTML;
- the current AtlasDays visual character;
- the separation between product Help and concept-first Learn content;
- privacy-respecting behavior;
- official-source-first tax and immigration articles;
- no client-side framework and no runtime backend requirement.

The work should be delivered as a sequence of independently reviewable batches. A large visual redesign and a publishing-system migration should not land as one opaque change.

## Product decisions and guardrails

### Theme behavior

Dark mode is the deliberate AtlasDays website default, matching the app.

- With no saved choice, the site renders dark even when the operating system uses light mode.
- Choosing light mode stores that explicit choice and restores it on later visits.
- Choosing dark mode stores dark explicitly.
- Missing, corrupt, or unknown stored values fall back to dark.
- Theme initialization stays in `<head>` so the first painted frame uses the correct theme.
- `prefers-color-scheme` must not select the site palette. It can still be used for browser-adjacent assets when appropriate and for unrelated preferences such as reduced motion.

Acceptance tests:

1. Clear site storage on a device using system light mode: the site opens dark.
2. Toggle to light and reload: the site remains light.
3. Toggle back to dark and reload: the site remains dark.
4. Set an invalid stored theme: the site opens dark.
5. No light-to-dark flash is visible on first load.

### Deployment model

- GitHub Pages continues to serve committed static files from the repository root.
- Generated output remains inspectable and committed; deployment does not depend on a server-side build.
- Source templates and manifests become the editing surface. Generated HTML should not be hand-edited after migration.
- A `--check` build mode must fail when committed output differs from generated output.

### Dependencies

- Prefer Python standard-library tooling to match the existing scripts.
- If a template dependency is genuinely justified, pin it and isolate it to development tooling. It must not become a browser/runtime dependency.
- No React, Vue, client-side router, CMS runtime, tracking SDK, or third-party search service.

### Content and privacy

- “Last verified” changes only after factual review of the official sources, not after layout or metadata edits.
- Analytics must not create visitor profiles or collect full high-stakes article paths unnecessarily.
- No testimonial is presented as a customer quotation without documented provenance and permission or a public review source.

## Target architecture

The final repository should have one source of truth for routes, metadata, article verification, navigation, image placements, and related content.

Suggested structure:

```text
_site-src/
  data/
    site.json
    routes.json
    content-clusters.json
  content/
    help/
    learn/
    pages/
  templates/
    base.html
    article.html
    hub.html
    legal.html
    redirect.html
    partials/
      header.html
      mobile-nav.html
      footer.html
      breadcrumbs.html
      article-cta.html
      metadata.html
assets/
  css/
    tokens.css
    base.css
    components.css
    home.css
    article.css
    hubs.css
  js/
    theme.js
    navigation.js
    search.js
scripts/
  build_site.py
  audit_site.py
  check_external_sources.py
  ...existing image scripts...
```

Generated pages continue to land at their current root, `help/`, and `learn/` paths so no public URL changes merely because the implementation changes.

Each indexable content record should eventually contain:

```text
route
page_type
title
description
headline
section
canonical
indexable
breadcrumbs
article_image_slots
social_image
related_content
source_urls
jurisdiction
rule_category
last_fact_verified
next_review_due
review_notes
date_published
date_modified
```

`date_modified` and `last_fact_verified` are separate fields.

## Delivery phases

### Phase 0 — Baseline and corrective rules

Purpose: lock down intended behavior and create a trustworthy migration baseline.

Work:

- Keep dark mode as the default across all existing page families.
- Record the 97-file/89-indexable-route baseline.
- Capture current title, canonical, description, heading, JSON-LD, route, and body-content hashes.
- Classify pages by template family: homepage, hub, article, legal/about, changelog, redirect, and 404.
- List all intentional redirects and noindex pages.
- Preserve the July screenshot audit as the initial asset backlog.

Exit gate:

- Dark-default tests pass.
- Baseline manifest accounts for every HTML file and public route.
- No unclassified page remains.

### Phase 1 — Automated audit and CI foundation

Purpose: establish safety checks before changing how pages are produced.

Work:

- Add `scripts/audit_site.py` using the Python standard library.
- Check:
  - broken local links, assets, and fragments;
  - missing or duplicate canonical URLs;
  - missing title, description, language, or H1;
  - duplicate IDs;
  - missing image alt text and intrinsic dimensions;
  - invalid JSON-LD and XML;
  - sitemap URLs that are missing, redirected, noindex, or noncanonical;
  - indexable pages missing from the sitemap;
  - incorrect dark-default bootstrap;
  - stale generated output;
  - image-plan/catalog/asset drift;
  - article verification fields that are missing or overdue.
- Add a GitHub Actions workflow for pull requests and pushes to `main`.
- Add scheduled external-source checking as a separate non-blocking job initially. Government sites frequently reject HEAD requests or rate-limit automated checks, so failures need classification rather than blind blocking.
- Store audit exceptions explicitly with reasons and expiry dates.

Exit gate:

- The current site passes local and CI audits except for explicitly quarantined, time-limited image-pipeline drift findings. Those findings become blocking in Phase 4.
- A deliberately broken fixture proves each critical check fails correctly.
- CI distinguishes errors from warnings and produces readable route-level output.

### Phase 2 — Shared tokens, templates, and generator

Purpose: remove the hand-authored duplication that is causing drift.

Work:

- Centralize color, spacing, typography, radii, shadows, and breakpoints.
- Encode dark as the base token set and light as an explicit `[data-theme="light"]` override.
- Remove palette selection through `prefers-color-scheme`; retain `prefers-reduced-motion` behavior.
- Build the shared page shell, metadata partial, header, footer, breadcrumbs, theme bootstrap, analytics include, and structured-data helpers.
- Generate sitemap and `llms.txt` from the route/content manifest.
- Add `build_site.py --check`.
- Migrate one page family at a time in this order:
  1. redirects and 404;
  2. About, Privacy, and Terms;
  3. Help articles;
  4. Learn articles;
  5. Help/Learn/Day Limits/residency hubs;
  6. changelog;
  7. homepage.
- During each family migration, compare normalized body text and public metadata against the baseline so template work cannot silently drop content.

Exit gate:

- Every generated public URL remains unchanged.
- Every generated page passes the Phase 1 audit.
- The repository-wide inline CSS total is reduced to page-specific critical exceptions only.
- A shared change to header, footer, theme, or metadata requires editing one source location.
- Generated output is deterministic across repeated builds.

### Phase 3 — Navigation, footer, and accessibility completion

Purpose: unify the experience and close the remaining semantic gaps.

Work:

- Design one global desktop navigation hierarchy:
  - Product/Home;
  - Help;
  - Learn;
  - Day Limits;
  - Changelog;
  - Get the app.
- Add a compact mobile menu rather than hiding whole sections.
- Keep primary navigation usable without JavaScript; enhance open/close behavior with minimal JavaScript where needed.
- Add a shared footer to all indexable pages with Help, Learn, Day Limits, Changelog, About, Privacy, Terms, Support, and App Store links.
- Emit one `<main>` landmark per page and `<main><article>…</article></main>` for articles.
- Add a skip-to-content link.
- Preserve visible keyboard focus, underlined body links, minimum touch targets, reduced-motion behavior, and sufficient contrast.
- Give the mobile menu correct expanded state, focus behavior, Escape handling, and screen-reader labels.
- Run automated accessibility checks against each template and manual VoiceOver checks against representative pages.

Representative manual test pages:

- homepage;
- Help index;
- Getting Started;
- Learn index;
- Day Limits;
- Schengen 90/180;
- one country tax article;
- one US-state article;
- Privacy;
- 404.

Exit gate:

- All 89 indexable pages contain a main landmark.
- All indexable Help/Learn pages contain the shared footer.
- Navigation works at 320 px without overflow.
- Keyboard-only and VoiceOver users can open, traverse, and close the mobile menu.
- No critical or serious automated accessibility findings remain.

### Phase 4 — Repair the image pipeline

Purpose: make article art, screenshots, and metadata reproducible instead of manually synchronized.

Website work:

- Replace heading-text-only placement with stable slot IDs or explicit insertion markers. Headings may change without invalidating the plan.
- Rebuild the catalog from the plan plus files on disk, not only from the most recent generation run.
- Make these states explicit:
  - planned and present;
  - planned but intentionally pending;
  - planned but missing/error;
  - present but orphaned;
  - rendered but missing.
- Make `sync_article_image_markers.py --check` and `insert_article_images.py --strict --dry-run` pass.
- Update image tooling so article hero assets can also drive social metadata.
- Generate a machine-readable screenshot manifest with source scenario, app version, capture date, device, dimensions, crop, and target website paths.

App screenshot-harness work in the AtlasDays project:

- Add a debug/UI-testing-only deterministic dataset.
- Add launch arguments such as `--ui-testing --website-screenshot <scenario>`.
- Route directly to each required screen, sheet, tracker, import state, widget preview, or report.
- Keep screenshot-only code excluded from release behavior.
- Capture on one named simulator/device configuration.
- Convert and compress outputs to the established WebP dimensions and filenames.

Initial scenario list comes from `SCREENSHOT_AUDIT_2026-07-09.md`, including:

- homepage dashboard and tracker detail;
- timeline, map/country, alerts, import, PDF, widgets, and privacy;
- actual dashboard period selector;
- getting started and trip modes;
- tracker presets/modes/windows;
- CSV, Flighty, and Photo import review;
- export options/PDF preview;
- iCloud/privacy/smart-alert states;
- AtlasDays Pro and US-state tracking.

Exit gate:

- No rendered image points to a missing file.
- No known screenshot has mismatched alt text or content.
- All homepage and Help screenshots use one deterministic demo dataset and current app UI.
- A documented command can recapture and replace the full website screenshot set.

### Phase 5 — Social proof and social metadata

Purpose: increase credibility and sharing quality without overstating evidence.

Testimonials:

- Inventory the source of each existing quote.
- If a quote has permission or a public review source, store its source, date, display attribution, and approved wording.
- Prefer short App Store excerpts linked or labeled as App Store reviews.
- Do not combine fragments or edit a quote in a way that changes its meaning.
- If adequate provenance is unavailable, remove the star/testimonial section and replace it with verifiable product proof: App Store rating count, privacy facts, screenshot evidence, or a concise maker note.

Social metadata:

- Generate an article-specific Open Graph/Twitter image for every indexable Help/Learn article.
- Add `og:image:width`, `og:image:height`, `og:image:alt`, and `twitter:image:alt`.
- Use a broadly supported share format and stable dimensions.
- Provide branded generated cards for pages without suitable article imagery.
- Validate a sample with Apple Messages, Slack, LinkedIn, X, and common Open Graph debuggers.

Exit gate:

- No anonymous quotation is presented as verified customer feedback.
- Every indexable page has an intentional social image and alt description.
- Social cards remain readable in both light and dark host applications.

### Phase 6 — Editorial governance and content-cluster cleanup

Purpose: make the high-stakes content maintainable and reduce search-intent overlap.

Work:

- Add structured source and verification fields to every rule article.
- Separate factual verification dates from ordinary modification dates.
- Define review intervals by risk:
  - immigration/entry rules: frequent;
  - tax residency rules: at least annual and after known legislative cycles;
  - product Help: each app release that touches the feature;
  - evergreen travel-record workflow: periodic.
- Create a review queue sorted by overdue date and risk.
- Write an editorial checklist for official-source review, exceptions, terminology, disclaimers, and internal links.
- Create a content-cluster map assigning one primary intent and one canonical pillar to every Learn page.
- Review overlap in these clusters first:
  - Schengen mechanics;
  - 183-day/tax residency;
  - travel history, proof, reconstruction, templates, and export;
  - UK visitor/absence/residence topics;
  - import workflows crossing Help and Learn.
- Merge pages where the distinction is weak, add redirects, and preserve useful unique examples.
- Make related-content links generated from the cluster map rather than hand-selected independently on every page.

Exit gate:

- Every high-stakes article has primary sources, an exact fact-verification date, and a next review date.
- Every Learn page has a unique documented intent and pillar relationship.
- Merged URLs redirect and are absent from the sitemap.
- A cosmetic build does not change fact-verification dates.

### Phase 7 — Help/Learn search and filtering

Purpose: make the expanded libraries usable without scanning every card.

Work:

- Generate a compact search index from the content manifest.
- Implement client-side search with plain JavaScript.
- Search title, description, jurisdiction, rule category, feature, and curated keywords—not full article bodies initially.
- Add filters appropriate to each section:
  - Help: setup, trips, import, trackers, reports, privacy/sync, Pro/widgets;
  - Learn: visa/entry, tax residency, US states, evidence/history, country/jurisdiction.
- Keep canonical pages fully usable and discoverable without JavaScript.
- Use a real label, result count/status announcement, keyboard navigation, clear/reset control, and no-results guidance.
- Avoid indexing visitor queries or sending them to a third party.

Exit gate:

- Search works locally with no network request.
- Results update accessibly and remain keyboard-usable.
- Common queries such as “Schengen,” “183 days,” “CSV,” “Flighty,” “iCloud,” and “New York” return the expected canonical page first.

### Phase 8 — Privacy-respecting conversion measurement

Purpose: learn which site paths help people reach the App Store without undermining the privacy message.

Work:

- Define a minimal event taxonomy before choosing implementation:
  - App Store click location: header, hero, article CTA, footer;
  - page family: home, Help, Learn, Day Limits, legal;
  - mobile-menu use;
  - Help/Learn search use and no-results count.
- Do not include personal data, search text, precise location, or a full sensitive article URL in events.
- First evaluate App Store Connect campaign links and capabilities already available in Cloudflare Web Analytics.
- If those cannot answer the questions, add only the smallest first-party aggregate mechanism and document it on the website privacy page.
- Establish a baseline before changing the homepage funnel.
- Review conversion by page family and CTA position after enough aggregate data exists; do not optimize around tiny samples.

Exit gate:

- Event definitions and retention are documented.
- No third-party analytics SDK or session replay is introduced.
- App Store clicks can be compared by CTA location and broad page family.

### Phase 9 — Source monitoring and ongoing maintenance

Purpose: keep the site reliable after the overhaul lands.

Work:

- Run scheduled official-source link checks.
- Distinguish temporary network failures, bot blocking, redirects, content movement, and true removal.
- Create issues or a generated review report for actionable source changes.
- Run the full static audit and generator drift check in pre-commit and CI.
- Add a release checklist connecting app changes to Help copy, screenshots, changelog, privacy, Terms, and Pro-plan wording.
- Add an annual full-site content and accessibility audit, with focused checks after major product releases.

Exit gate:

- Broken or redirected official sources create an actionable review item.
- Product releases have an explicit website-impact checklist.
- Generated output cannot drift silently from its source manifests/templates.

## Recommended delivery batches

Keep each batch reviewable and reversible:

1. Dark-default rule, baseline manifest, and audit script.
2. CI and generator `--check` foundation.
3. Shared tokens/theme/header/footer prototypes without migrating all pages.
4. Redirect/legal/404 template migration.
5. Help article migration plus accessibility shell.
6. Learn article migration plus editorial fields.
7. Hub, changelog, and homepage migration.
8. Mobile navigation/footer and full accessibility pass.
9. Image-plan/catalog repair.
10. AtlasDays screenshot harness and screenshot replacement.
11. Social proof and article-specific social cards.
12. Content-cluster merges and redirects.
13. Search/filter experience.
14. Privacy-respecting conversion measurement.
15. Scheduled source monitoring and release-maintenance workflow.

Do not mix the bulk template migration, screenshot replacement, and content merging in one batch. Separating them makes regression diagnosis and rollback much safer.

## Validation matrix

Every phase must preserve or improve these checks:

| Area | Required validation |
|---|---|
| Routes | All intended public routes resolve; redirects are explicit; no redirect is in the sitemap |
| Content | Normalized article text and headings are preserved unless a content change is intentional |
| Metadata | Unique title/description/canonical; valid JSON-LD; correct index/noindex state |
| Theme | Dark default; explicit light/dark persistence; no first-paint flash |
| Responsive layout | 320, 375, 430, 768, 1024, and wide desktop widths |
| Accessibility | Keyboard, VoiceOver, landmarks, skip link, focus, contrast, touch targets, reduced motion |
| Images | File exists, dimensions and alt are correct, screenshot metadata is current |
| Performance | No material regression in homepage or representative article transferred bytes and render timing |
| Privacy | No new personal data collection; analytics fields match documented taxonomy |
| Generated output | Clean `build_site.py --check` and `audit_site.py` results |

## Rollout and rollback

- Land work in the delivery batches above rather than a long-lived all-or-nothing branch.
- Before each template-family migration, retain normalized metadata/body snapshots for comparison.
- Preview generated output locally and attach representative desktop/mobile screenshots to the review.
- Deploy only after the generated-output and audit checks pass.
- Roll back a defective phase by reverting that batch; do not manually patch generated HTML in production.
- If a generator defect is found after migration, fix the source/template and regenerate every affected page before redeploying.

## Definition of done

The complete recommendation program is finished when:

- all public pages are generated from shared templates and structured manifests;
- the site defaults to dark and reliably preserves explicit light/dark choices;
- CI validates links, metadata, structured data, sitemap, generated output, accessibility basics, and image state;
- every indexable page has correct landmarks, global navigation, footer, and social metadata;
- current product screenshots can be regenerated deterministically from the app;
- no anonymous or unverifiable testimonial remains;
- every high-stakes article has structured primary sources and verification scheduling;
- overlapping content has an explicit pillar/intent map and intentional redirects;
- Help/Learn search works locally and accessibly;
- conversion measurement is aggregate, minimal, documented, and privacy-respecting;
- official-source and app-release maintenance is part of the normal workflow rather than a periodic rescue project.
