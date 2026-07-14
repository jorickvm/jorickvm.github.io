# Privacy-Respecting Conversion Measurement

Decision date: July 14, 2026

## Current implementation

The site keeps Cloudflare Web Analytics for aggregate page and performance measurement. It does not add a custom event endpoint, visitor identifier, session replay, search-query logging, or third-party marketing SDK.

Cloudflare Web Analytics does not currently support custom events, so it cannot responsibly measure CTA placement or search events by itself. App Store Connect campaign links are the preferred acquisition mechanism, but Apple requires a campaign token **and the account-specific provider token**. That private App Store Connect value is not stored or guessed in this repository.

## Approved taxonomy

When App Store campaign links are configured, use only broad aggregate labels:

- Page family: `home`, `help`, `learn`, `daylimits`, `legal`.
- CTA placement: `header`, `hero`, `article`, `footer`.
- Campaign token format: `site_<family>_<placement>`.

Do not send the article slug, travel rule, country, search query, precise location, or any user-entered value.

## Activation

1. Create campaign links in App Store Connect and obtain the provider token there.
2. Add the generated links to a small checked-in manifest rather than hard-coding a token in content files.
3. Apply links during the static build by page family and placement.
4. Verify that every campaign link contains Apple's provider and campaign tokens.
5. Establish a baseline before changing CTA placement; do not optimize around cohorts below Apple's reporting threshold.

Until those account-owned links are supplied, the deliberate privacy-preserving choice is no custom conversion event collection.
