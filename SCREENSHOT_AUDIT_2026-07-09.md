# AtlasDays Website Screenshot Audit - 2026-07-09

Scope checked:
- Static website repo: `jorickvm.github.io`
- All 54 HTML files under root, `help/`, and `learn/`
- All local `<img>` references, homepage screenshot/media assets, Help Center app screenshots, article image markers, and article-image asset existence
- iOS app repo state and simulator availability for possible retakes

Summary:
- Published app screenshots are mostly from 2026-03-28 through 2026-04-07. Only the tracker detail screenshot is from 2026-04-25 and the widget proof screenshot is from 2026-05-20.
- The app is now at 1.11.2 and has had major UI-facing work since those screenshots: Dashboard title/date behavior, Auto-Detect inline timeline cards, US state tracking and state map work, expanded US-state presets, import review polish, Flighty import, Photo Import details, Smart Alerts, Pro/paywall work, widget polish, and PDF/import changes.
- The simulator is available, including iPhone 17 Pro devices, but there is no current screenshot automation harness. The Xcode scheme references a UI test target, but no `AtlasDaysUITests` source files are present.

## P0 - Broken Or Missing On Published Pages

These should be fixed before or alongside any broad retake pass.

1. `learn/overstaying-a-visa-or-stay-limit.html:380`
   - Missing file: `assets/article-images/learn/overstaying-a-visa-or-stay-limit/hero.webp`
   - Current page renders a broken image.
   - Action: regenerate/restore this article hero image, or remove the rendered block until the asset exists.

2. `learn/overstaying-a-visa-or-stay-limit.html:444`
   - Missing file: `assets/article-images/learn/overstaying-a-visa-or-stay-limit/body-2.webp`
   - Current page renders a broken image.
   - Action: regenerate/restore this article body image, or remove the rendered block until the asset exists.

3. `help/flighty-import.html:126`
   - Marker only: `ARTICLE_IMAGE:hero - Screenshot: Flighty import review screen...`
   - No rendered image follows it.
   - Action: take a current Flighty Import review screenshot with inferred trips and status pills, then insert it.

4. `learn/flighty-flight-history-day-count.html:341`
   - Marker only: `ARTICLE_IMAGE:hero`
   - No rendered image follows it.
   - Action: add a Flighty-to-day-count hero image. A product screenshot is acceptable if the page is meant to show the actual workflow.

5. `learn/flighty-flight-history-day-count.html:362`
   - Marker only: `ARTICLE_IMAGE:body-1`
   - No rendered image follows it.
   - Action: add a supporting image for converting flights into country-day stays.

6. `help/dashboard-and-map.html:251`
   - Asset: `assets/article-images/help/dashboard-and-map/screenshot-period-selector.webp`
   - Alt text says this is the period selector, but the asset is visibly the Continents sheet.
   - Action: replace with an actual current period selector screenshot, or move/rename the Continents sheet if that is the intended content.

## P1 - Retake All Homepage App Screenshots

These are the most visible screenshots and should be captured from the current app in one coherent demo dataset.

1. Homepage hero dashboard
   - References:
     - `index.html:178` - `assets/home/home-hero-dashboard-poster.webp`
     - `index.html` video poster/source - `assets/home/home-hero-dashboard.mp4`
     - metadata/share image - `assets/home/home-hero-dashboard.png`
   - Current issue: the poster shows the old `Dashboard` title and an empty 0/90, 0 countries, 0 trips state. Current app uses today's date as the Dashboard large title.
   - Retake target: populated Dashboard with current title/date behavior, one useful tracker, non-empty stats, and map.

2. Homepage tracker detail
   - References:
     - `index.html:186`
     - `index.html:211`
   - Asset: `assets/home/home-hero-tracker-detail.webp`
   - Retake target: current Schengen tracker detail with latest chart, forecast, and counted trips UI.

3. Homepage timeline proof
   - Reference: `index.html:222`
   - Asset: `assets/home/home-proof-timeline.webp`
   - Retake target: current Timeline with exact, ongoing, upcoming, and ideally one Auto-Detect suggestion/inline card if that is now a key feature.

4. Homepage map/country proof
   - Reference: `index.html:233`
   - Asset: `assets/home/home-proof-map-country.webp`
   - Retake target: current map with country detail. Consider adding a US-state variant elsewhere because US state tracking is now a major feature.

5. Homepage alerts proof
   - Reference: `index.html:244`
   - Asset: `assets/home/home-proof-alerts.webp`
   - Retake target: current Smart Alerts settings and warning thresholds.

6. Homepage import proof
   - Reference: `index.html:255`
   - Asset: `assets/home/home-proof-import-preview.webp`
   - Current issue: old generic CSV import screenshot, while the site now claims Photo, CSV, and Flighty imports.
   - Retake target: current import review. Prefer Flighty or Photo Import if the homepage copy keeps saying "photos or CSV"; otherwise split into separate current screenshots.

7. Homepage PDF export proof
   - Reference: `index.html:266`
   - Asset: `assets/home/home-proof-pdf-export.webp`
   - Retake target: current PDF export preview and current report formatting.

8. Homepage widgets proof
   - Reference: `index.html:277`
   - Asset: `assets/home/home-proof-widgets.webp`
   - Retake target: current widget designs after the June widget warnings/polish changes.

9. Homepage privacy proof
   - Reference: `index.html:353`
   - Asset: `assets/home/home-proof-privacy.webp`
   - Retake target: current privacy/location/sync settings, especially if Auto-Detect copy changed.

## P1 - Retake Existing Help Center App Screenshots

The following screenshots exist, but should be regenerated from the current app because they predate many current behaviors.

### `help/getting-started.html`

1. `help/getting-started.html:242`
   - Asset: `assets/article-images/help/getting-started/screenshot-home-country.webp`
   - Retake: current Settings/Home Country picker, including home-country suggestions if visible.

2. `help/getting-started.html:262`
   - Asset: `assets/article-images/help/getting-started/screenshot-add-trip.webp`
   - Retake: current Timeline add-trip entry point.

3. `help/getting-started.html:270`
   - Asset: `assets/article-images/help/getting-started/screenshot-trip-modes.webp`
   - Retake: current trip form mode selector, year/unknown/exact behavior.

4. `help/getting-started.html:278`
   - Asset: `assets/article-images/help/getting-started/screenshot-add-tracker.webp`
   - Retake: current Dashboard add-tracker entry and current preset sheet.

### `help/history-and-import.html`

1. `help/history-and-import.html:243`
   - Asset: `assets/article-images/help/history-and-import/screenshot-exact-dates.webp`
   - Retake: current Exact Dates trip form.

2. `help/history-and-import.html:296`
   - Asset: `assets/article-images/help/history-and-import/screenshot-timeline-sections.webp`
   - Retake: current Timeline sections with current trip cards, US-state behavior if relevant, and auto-detect suggestion cards if the article mentions them.

### `help/trackers-and-limits.html`

1. `help/trackers-and-limits.html:244`
   - Asset: `assets/article-images/help/trackers-and-limits/screenshot-tracker-card.webp`
   - Retake: current tracker card on Dashboard.

2. `help/trackers-and-limits.html:284`
   - Asset: `assets/article-images/help/trackers-and-limits/screenshot-presets.webp`
   - Retake: current tracker preset sheet, including expanded US-state preset work if applicable.

3. `help/trackers-and-limits.html:294`
   - Asset: `assets/article-images/help/trackers-and-limits/screenshot-mode.webp`
   - Retake: current tracker mode selector.

4. `help/trackers-and-limits.html:313`
   - Asset: `assets/article-images/help/trackers-and-limits/screenshot-window.webp`
   - Retake: current rolling/per-stay/yearly/fiscal-year window selector.

### `help/dashboard-and-map.html`

1. `help/dashboard-and-map.html:251`
   - Asset: `assets/article-images/help/dashboard-and-map/screenshot-period-selector.webp`
   - Retake: actual current period selector. Current asset is the wrong screen.

2. `help/dashboard-and-map.html:295`
   - Asset: `assets/article-images/help/dashboard-and-map/screenshot-share-cards.webp`
   - Retake: current share card carousel and current map rendering.

### `help/csv-import.html`

1. `help/csv-import.html:206`
   - Asset: `assets/article-images/help/csv-import/screenshot-import-preview.webp`
   - Retake: current CSV Import preview, including current row checkmarks, select-all/summary behavior, duplicates/errors, and US-state fields if shown.

### `help/export-and-reports.html`

1. `help/export-and-reports.html:174`
   - Asset: `assets/article-images/help/export-and-reports/screenshot-export-options.webp`
   - Retake: current Export options screen.

2. `help/export-and-reports.html:223`
   - Asset: `assets/article-images/help/export-and-reports/screenshot-pdf-export.webp`
   - Retake: current PDF export preview after alphabetized country groups and US State column changes.

### `help/privacy-location-and-sync.html`

1. `help/privacy-location-and-sync.html:219`
   - Asset: `assets/article-images/help/privacy-location-and-sync/screenshot-privacy-overview.webp`
   - Retake: current privacy/location/sync overview.

2. `help/privacy-location-and-sync.html:284`
   - Asset: `assets/article-images/help/privacy-location-and-sync/screenshot-alerts.webp`
   - Retake: current notification/Smart Alerts settings.

## P2 - Substantive Pages With No Product Screenshot Or Article Image

These pages are not broken, but they look under-illustrated compared with the rest of the Help Center/Learn system.

1. `help/photo-import.html`
   - Needs screenshots for:
     - Photo Import entry point
     - scan range/options
     - review screen with Ready/Duplicate/Overlap/Transit/Older Trips/US states where applicable
     - Find Photos or imported trip photo previews

2. `help/widgets.html`
   - Needs screenshots for:
     - widget gallery/configuration
     - current small/medium/large tracker widgets
     - world map widget

3. `help/atlasdays-pro.html`
   - Needs screenshots for:
     - current Pro/paywall screen
     - Pro feature gates, if useful
     - US state tracking or widget/alerts Pro examples

4. `help/icloud-sync-and-restore.html`
   - Needs screenshots for:
     - iCloud sync settings/status
     - restore/empty/sync state if present in-app

5. `learn/japan-90-day-rule.html`
   - No article image currently.
   - If adding product screenshots, use a Japan visa-limit tracker setup or day-count example.

6. `learn/uk-ilr-absence-limit.html`
   - No article image currently.
   - If adding product screenshots, use a UK absence/residency tracker or export/report example.

7. `learn/uk-citizenship-absence-limits.html`
   - Uses interim UK statutory residence-test images rather than article-specific assets.
   - Action: create article-specific images or screenshots if this page is meant to stand on its own.

## Simulator Retake Feasibility

Confirmed:
- `xcrun simctl list devices available` works with elevated simulator access.
- iPhone 17 Pro simulators are available.
- Existing raw captures were also iPhone 17 Pro sized at `1206x2622`, matching most current assets.

Blocked for full automation right now:
- No UI test source files exist, even though the scheme references `AtlasDaysUITests`.
- No app-level screenshot/deep-link route currently opens each required screen with seeded demo data.
- The app repo currently has unrelated local modifications, so a screenshot-harness change should be planned carefully and kept isolated.

Practical path:
1. Add a debug-only screenshot harness or UI test target that launches with `--ui-testing --website-screenshot <scenario>`.
2. Seed a deterministic demo dataset in-memory.
3. Route directly to each required screen/sheet.
4. Capture with `xcrun simctl io <device> screenshot`.
5. Convert/compress to the existing `.webp` naming scheme.
6. Replace assets in place and update dimensions/alt text where needed.

Without that harness, retaking is still possible manually in Simulator, but it will be slow and easy to make inconsistent.
