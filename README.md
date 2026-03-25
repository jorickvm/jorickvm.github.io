Landing page for [AtlasDays](https://atlasdays.app) — a private iPhone app for tracking trips, visa days, and residency thresholds.

## Website launch TODO

### Homepage screenshot checklist

The homepage is now wired to these portrait iPhone screenshots.

1. `Hero primary`
   File target: `assets/home-hero-dashboard.png`
   Needed state: dashboard overview with tracker cards, top stats, and the mini map visible in the same shot.

2. `Hero secondary`
   File target: `assets/home-hero-tracker-detail.png`
   Needed state: one tracker detail view with used days, remaining days, and a clear forward-looking insight.

3. `Proof timeline`
   File target: `assets/home-proof-timeline.png`
   Needed state: timeline/history with realistic trips, visible day badges, and enough variety to show the app is not a toy dataset.

4. `Proof map`
   File target: `assets/home-proof-map-country.png`
   Needed state: full map with visited countries highlighted and a country detail sheet open.

5. `Proof tracker presets`
   File target: `assets/home-proof-tracker-presets.png`
   Needed state: preset picker showing `Residence`, `Schengen`, `Visa Limit`, and `Travel Goal`.

6. `Proof trip modes`
   File target: `assets/home-proof-trip-modes.png`
   Needed state: trip form showing the difference between `Exact Dates` and `Month & Year`.
   Bonus: include `Dates Unknown` if it still reads clearly in one capture.

7. `Proof import`
   File target: `assets/home-proof-import.png`
   Needed state: CSV import or import-preview flow with mapped columns.
   Bonus: include the AI helper if it looks polished enough for public marketing.

8. `Proof privacy`
   File target: `assets/home-proof-privacy.png`
   Needed state: privacy/location onboarding or permission flow that clearly reinforces on-device processing and optional iCloud sync.

### Notes

- The hero supports theme-specific screenshots:
  - dark: `assets/home-hero-dashboard.png`, `assets/home-hero-tracker-detail.png`
  - light: `assets/home-hero-dashboard-light.png`, `assets/home-hero-tracker-light.png`
- The proof section uses `timeline`, `map`, `tracker presets`, `trip modes`, and `import`.
- The privacy section uses `assets/home-proof-privacy.png`.
- Remaining launch work is image optimization and a browser QA pass after deployment.
