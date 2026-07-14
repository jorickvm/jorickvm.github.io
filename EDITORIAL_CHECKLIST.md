# AtlasDays Editorial Checklist

Use this checklist for substantive Help or Learn updates. Cosmetic edits do not change `last_fact_verified`.

## Official-source review

- Open every source URL in the article's editorial record and confirm it still supports the precise claim.
- Prefer legislation, official government guidance, or the responsible authority over summaries.
- Record the exact review date only after reading the source; never advance it during template, spelling, or metadata work.
- Capture exceptions, nationality/status scope, counting window, entry/exit treatment, and authority discretion in plain language.
- Set the next review date using the risk interval in `_site-src/data/editorial.json`.

## Reader safety and clarity

- Keep the general-information and professional-advice boundary visible.
- Distinguish a threshold from automatic legal or tax residence.
- Do not present AtlasDays, a calculator, or an article as the operative authority.
- Use jurisdiction-specific terminology and explain ambiguous shorthand such as “183-day rule.”
- Check examples independently and state any simplifying assumptions.

## Content architecture

- Confirm the page still has one unique primary intent in `_site-src/data/content-clusters.json`.
- Link to the cluster pillar and the most relevant supporting pages; avoid near-duplicate sections.
- Send product operation questions to Help and rule/concept questions to Learn.
- Preserve existing public URLs or add an explicit redirect when merging content.

## Before publishing

- Run `python3 scripts/build_content_governance.py --check`.
- Run `python3 scripts/build_search_index.py --check`.
- Run `python3 scripts/build_site.py --check` and the strict site audit.
