# AtlasDays Content-Cluster Review

Date: July 14, 2026

All 66 Learn articles now have a unique primary intent, cluster, and pillar relationship in `_site-src/data/content-clusters.json`. Related links are generated from that map; the former hand-picked blocks have been removed from source content.

## Overlap decisions

- **Schengen mechanics:** keep the general 90/180 explainer as the pillar. The country list, worked rolling-window walkthrough, single-entry visa, day-return timing, and day-definition pages answer distinct follow-up questions.
- **183-day and tax residency:** keep the general warning against treating 183 days as a universal rule, the country directory, and each jurisdiction page. Jurisdiction pages are not interchangeable because thresholds, windows, domicile/abode tests, and exceptions differ.
- **Travel history and proof:** keep application requirements, reconstruction, negative-presence proof, imperfect-record evidence, templates, and export workflow separate. Each corresponds to a different stage of producing or defending a chronology.
- **UK topics:** keep visitor permission, ETA comparison, ILR absence, citizenship absence, and statutory residence separate. They concern different legal regimes and audiences; merging would increase the risk of readers applying the wrong test.
- **Help versus Learn imports:** Help remains the operational source for AtlasDays controls and error states. Learn pages cover broader record quality or conceptual workflows and now link back to the relevant Help guide.

## Merge result

No pair was weak enough to merge safely in this pass. The apparent overlaps are deliberate pillar/supporting relationships rather than duplicate intent, so no redirect was introduced. Future additions must declare an intent and cluster before publication; if that intent duplicates an existing record, the existing page should be expanded instead.
