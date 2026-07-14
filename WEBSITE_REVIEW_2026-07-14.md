# AtlasDays Website Review — July 14, 2026

## Executive summary

AtlasDays has a clear proposition, unusually good privacy positioning, strong long-form coverage, and a sensible split between product help and conceptual Learn content. The homepage communicates the high-stakes use case well, while the Day Limits, country-tax-residency, and US-state hubs give the growing article library a useful hierarchy.

The main weakness is no longer page-level quality. It is scale. The site now contains 97 HTML files, with 89 indexable URLs, but it still behaves like a small hand-authored site. Shared logic, design tokens, article structure, metadata, and content-maintenance data are duplicated across dozens of files. That duplication has already produced drift: product-plan copy diverged from the app, image tooling no longer validates cleanly, social metadata usually points to the generic homepage image, and even a one-line theme rule is repeated across more than 90 pages.

The next meaningful improvement should therefore be a lightweight publishing-system overhaul, not a visual redesign for its own sake. Keep the static output and current visual character, but generate repeated page chrome and metadata from shared templates and structured content.

## What is already working well

- The homepage has a focused promise: private day tracking that remains trustworthy when dates matter.
- Privacy is treated as a product feature and explained with concrete boundaries, not vague claims.
- Help and Learn have distinct jobs: operational product guidance versus conceptual rules and evidence.
- The Day Limits, country, and US-state hubs provide a strong base for topical authority and internal navigation.
- All 89 sitemap URLs currently resolve to local source pages, and there are no duplicate sitemap entries.
- Every indexable Learn page includes at least one external non-App-Store source link; government and official domains dominate the citation set.
- Local links, assets, fragments, image alt attributes, JSON-LD blocks, and duplicate IDs pass the repository-wide static audit after the fixes in this review.
- Page media weight is generally reasonable. The homepage references about 1.1 MB of unique media and code; representative article pages are substantially lighter.

## Fixes made during this review

### Content and product truth

- Updated homepage FAQ copy and Terms to include quarterly, annual, and lifetime Pro options, matching the current app configuration.
- Generalized the Pro help copy so subscription-management guidance applies to quarterly and annual subscribers.
- Removed the obsolete `/support` redirect URL from the sitemap and pointed `llms.txt` to the real Help Center support section.
- Corrected two stale sitemap modification dates and refreshed the homepage modification date.

### Broken or misleading output

- Removed two rendered image blocks whose files did not exist on the overstaying article. Placement markers remain so the images can be regenerated later without showing broken media now.
- Added missing descriptions to two noindex legacy Learn redirects so repository tooling can inspect them consistently.

### Theme, contrast, and interaction

- Standardized theme initialization across the site. AtlasDays now deliberately starts in dark mode unless the visitor has explicitly selected light mode, matching the app’s product behavior.
- Added accessible light-theme blue tokens. The main light-theme blue now has a 5.22:1 contrast ratio against the page background, and white CTA text has a 5.55:1 ratio against the button.
- Added visible keyboard focus treatment to homepage and shared-header controls.
- Underlined article-body links so they are not identified by color alone, while preserving the quieter breadcrumb treatment.
- Made the homepage preview video keyboard-operable and gave it an accessible replay label.
- Added explicit button types where they were missing.
- Tightened the shared mobile header below 560 px to prevent the expanded navigation from overflowing narrow screens.
- Bumped CSS and JavaScript cache keys so returning visitors receive the fixes promptly.

### Structure

- Added main landmarks to About, Privacy, Terms, and the 404 page.
- Added intrinsic dimensions to the 404-page logos to avoid layout shifts.

## Findings by area

### Content and positioning

The core product story is strong. “One underlying trip record powers visa math, residency thresholds, and travel history” is a meaningful differentiator. The privacy story is also specific enough to be credible: no AtlasDays server copy, optional iCloud, reviewable location suggestions, and on-device photo processing.

The homepage becomes less credible in its testimonial section. Three five-star quotations are presented with generic descriptions rather than names, App Store provenance, dates, or permission-based attribution. Even if the statements are genuine, the presentation resembles invented marketing copy. For a product whose brand promise is trustworthiness, weakly sourced social proof is worse than no social proof.

The Learn library is comprehensive, but several clusters are close enough to compete with one another:

- the Schengen rule, rolling-window walkthrough, countries list, and “when days return” pages;
- travel-history preparation, templates, rebuilding, exporting, and proof/evidence pages;
- the general 183-day article, country directory, and individual country explainers.

The hubs reduce this risk, but the collection needs an explicit pillar/supporting-page map so each page owns one search intent and links to the canonical next step.

### High-stakes editorial quality

The articles generally use good disclaimers and official sources. However, tax and immigration rules are time-sensitive and consequential. “Last verified” is currently free-form page copy, while sources, jurisdiction, rule type, and verification dates are embedded separately in HTML and JSON-LD. This makes systematic re-verification difficult.

A structured editorial record should drive each high-stakes article:

- jurisdiction and rule category;
- official primary source URLs;
- exact last-verified date;
- reviewer and verification notes;
- known exceptions that the page intentionally does not cover;
- next review date or source-change monitor.

The site should never imply that an article has been re-verified merely because layout, images, or internal links changed.

### Layout and navigation

The visual system is calm, legible, and appropriate for the product. Dark and light themes are both supported, card radii and spacing are consistent within the main page families, and app screenshots make the product tangible.

Navigation is inconsistent across page families. The homepage, Help/Learn hubs, articles, legal pages, changelog, redirects, and 404 page all use different amounts of chrome. On very small screens the shared header now avoids overflow, but it does so by showing only the current section, Get the app, and theme control. A real mobile menu is the longer-term answer.

None of the 84 indexable Help/Learn pages has a shared footer. That removes the most reliable place for cross-section navigation, support, Privacy, Terms, and product-download context. Adding one consistent footer would improve discovery without making article headers heavier.

The recent screenshot audit remains the authority on visual asset freshness. It identifies outdated homepage captures, a wrong Help screenshot for the period selector, missing Flighty imagery, and a lack of a deterministic capture harness. Those are still substantive product-presentation issues even though the two actually broken image references were removed here.

### Accessibility

This pass fixed focus visibility, link identification, color contrast, keyboard replay behavior, several button types, and a few missing landmarks.

The largest remaining semantic gap is that 79 of 89 indexable pages do not contain a `<main>` landmark. Most use a top-level `<article>` instead. The next template pass should emit `<main><article>…</article></main>`, add a skip link, and run an automated axe or equivalent check across representative desktop and mobile pages.

The article pages also need a deliberate heading and landmark audit after templating. The current static parser found no duplicate IDs or broken fragments, but semantic behavior should be verified with VoiceOver once fresh browser control is available.

### SEO and discoverability

Canonical and sitemap coverage are strong after removing the redirect-only Support URL. Titles and descriptions are generally specific, and the major content pages use Article and Breadcrumb structured data.

Social metadata is the largest missed opportunity. Sixty-nine of 70 indexable Learn pages use the generic homepage dashboard image for Open Graph sharing even though many have article-specific hero images. Only two `og:image:alt`/`twitter:image:alt` entries exist across Help and Learn. Article-specific share cards should be generated alongside article images, with stable dimensions, alt text, and a non-WebP fallback if required by target crawlers.

Sitemap and `llms.txt` updates are manual. They should be derived from the same content manifest as canonical URLs, titles, dates, and navigation so redirect pages cannot be reintroduced accidentally.

### Architecture and maintainability

This is the highest-leverage area.

- The repository contains roughly 629 KB of duplicated inline CSS across HTML files.
- Theme initialization was copied into 91 pages.
- Eighty-four pages load a shared header stylesheet, but most article body styling, scripts, metadata, and page structure remain duplicated inline.
- Seventy-nine indexable pages lack the same landmark because there is no single article template to fix.
- The image pipeline does not currently validate end to end: marker sync stops on an outdated `help/getting-started` anchor, while image insertion stops because the catalog contains only one article and lacks configured entries.

Keep static HTML as the deployment artifact, but introduce a small Python-based generator using templates and structured front matter or JSON/YAML. The existing Python tooling makes that a natural fit and avoids adopting a JavaScript framework or runtime.

The generated system should own:

- `<head>` metadata and JSON-LD;
- theme bootstrap, shared header, mobile navigation, and footer;
- article shell, breadcrumbs, main/article landmarks, and CTA components;
- canonical URLs, sitemap, `llms.txt`, index cards, and related-article links;
- source/verification metadata;
- article-image placements and social-image metadata.

Generated HTML can remain committed if zero-build GitHub Pages deployment is important.

### Performance and analytics

The site is not media-heavy by modern marketing-site standards, and image dimensions/lazy loading are generally handled well. The main avoidable cost is repeated inline CSS, which browsers must download and parse again on every article rather than reusing a cached stylesheet.

Cloudflare Web Analytics is present sitewide. The next analytics step should be narrow and conversion-oriented: distinguish header, hero, mid-article, and footer App Store clicks; measure Help/Learn-to-App-Store paths; and track on-site search/filter use if introduced. Avoid adding session replay or invasive travel-topic profiling, which would conflict with the privacy positioning.

## Prioritized recommendations

### P0 — next substantial work

1. **Create a lightweight static publishing system.** Consolidate templates, tokens, metadata, sitemap generation, and article manifests while keeping static output.
2. **Repair and integrate the image pipeline.** Make marker, plan, catalog, asset, and HTML checks pass in CI. Then implement the screenshot harness described in `SCREENSHOT_AUDIT_2026-07-09.md` and retake the product images against deterministic app data.
3. **Replace or remove anonymous testimonials.** Prefer attributed App Store review excerpts, permission-based customer quotes, or transparent aggregate proof.
4. **Formalize high-stakes editorial governance.** Store source and verification data structurally, assign review intervals, and separate factual re-verification from cosmetic page updates.

### P1 — immediately after the publishing foundation

5. **Unify navigation and add a shared footer.** Use a compact mobile menu rather than hiding whole sections; include Help, Learn, Day Limits, Changelog, Privacy, Terms, support, and download paths consistently.
6. **Complete semantic accessibility.** Add main landmarks to the remaining 79 indexable pages, add skip links, and test representative templates with VoiceOver and automated accessibility checks.
7. **Generate article-specific social metadata.** Produce stable share images and alt metadata from each article’s hero/content manifest.
8. **Create an explicit content-cluster map.** Give each overlapping page a unique intent, merge weak duplication, and define pillar-to-supporting-page internal links.
9. **Add repository CI for static output.** Fail on broken local references, missing metadata, malformed JSON-LD, sitemap/canonical drift, missing planned assets, stale generator config, duplicate IDs, and unexpected noindex/indexable combinations.

### P2 — optimization

10. **Move repeated article CSS and scripts into cached shared assets.** Keep only genuinely page-specific critical styles inline.
11. **Add lightweight Help/Learn search and filtering.** The libraries are now large enough that scanning cards is no longer sufficient for every visitor.
12. **Instrument privacy-respecting conversion events.** Measure which content and CTA positions lead to App Store visits before redesigning the homepage funnel.
13. **Monitor official outbound sources.** Add scheduled link checks and a review queue for changed or redirected government guidance.

## Verification performed

- Parsed all 97 HTML files.
- Checked every local `href`/`src` and local fragment target.
- Checked duplicate IDs, image alt attributes, button types, and JSON-LD parsing.
- Parsed `sitemap.xml`, confirmed 89 unique current URLs, and confirmed the redirect-only Support URL is absent.
- Confirmed pages initialize in dark mode when no saved preference exists and preserve an explicit light-mode choice.
- Checked shared CSS brace balance and calculated the new light-theme contrast ratios.
- Served the homepage, Help index, Learn index, and shared CSS locally and received successful HTTP responses.
- Ran `git diff --check` successfully.

Fresh interactive browser screenshots were not available in this session. Visual conclusions therefore combine source/responsive-CSS inspection with `SCREENSHOT_AUDIT_2026-07-09.md`. A fresh desktop/mobile/browser and VoiceOver pass should be part of the recommended screenshot/template work.

The existing article-image validation commands do not currently pass. This is a pre-existing pipeline drift issue, not a failure introduced by the page fixes: marker sync stops on a stale Getting Started heading anchor, and image insertion stops on an incomplete catalog.
