# AtlasDays Website Translation Guidelines

How to translate atlasdays.app. This is the website's own copy of the app's
`Docs/reference/translation-guidelines.md`, kept here because the two surfaces
need opposite defaults in the place that matters most.

**The app document stays canonical for anything about the app**: product
vocabulary, the accepted-terminology tables, the register of each language, and
every decision about `.xcstrings`. Read it first. This file records only what
changes when the target is a web page instead of a screen, and it is the
authority where the two disagree about the website.

Read `README.md` for the build mechanics and `CLAUDE.md` for repository policy.
Neither is optional: this file assumes you know that pages under `learn/`,
`help/`, and the locale directories are generated, never hand-edited.

---

## 1. The inversion: what freedom you have, and where

The app document's house rule is *native and natural beats literal*, with visa
and tax explanations named as one of the few narrow-freedom exceptions.

On this site that exception is not an exception. It is the entire Learn
section. Every article under `learn/` explains a day-count rule, a visa limit,
or a residency threshold that a reader may act on, and the site's own
disclaimer says so on every page. So the setting flips:

| Surface | Default | What you may change |
| --- | --- | --- |
| `learn/` article body | **Faithful.** Preserve every claim, condition, qualifier, exception, and number. | Sentence structure, idiom, word order, connectives. Nothing that carries a fact. |
| `learn/` title, lede, subtitle, meta description | Adapt for the reader and for search in the target language. | Phrasing and emphasis, as long as the promise is the same rule. |
| `help/` article | Natural product copy, as in the app document. | Everything except step order, screen names, and what a control does. |
| Hub chrome, nav, footer, CTA boxes | Natural marketing copy. | Freely, within the length budget. |
| Disclaimers and "not legal or tax advice" lines | **Faithful, no exceptions.** | Grammar only. |

The test for a Learn body sentence: could a reader act differently because of
how you worded it? If yes, you are in faithful territory. "More than 183 days"
and "183 days or more" are different rules. So are "any rolling 12-month
period" and "the calendar year", "the arrival day counts" and "the arrival day
may count", "presumes" and "makes".

What faithful does **not** mean is word-for-word. Dutch, German, and French all
prefer different clause orders from English, and a sentence that is only
comprehensible when mentally back-translated has failed even when every fact
survived. Rewrite the sentence; keep the fact.

### Do not translate a fact into a different fact

- Never convert a number, a threshold, a window length, or a date.
- Never round. `about 270 days` stays approximate; `183` never becomes `ruim
  180`.
- Never resolve an English hedge into certainty, or add a hedge the source does
  not have.
- Never localize a legal instrument's substance. You may gloss a name; you may
  not restate what the law says.
- If the English source is wrong or unclear, **fix the English first** and
  rebuild, then translate the corrected text. Translating a known error
  faithfully into a language nobody here reads is how an error becomes
  permanent. This is the same rule the app document sets for the Help Center,
  and it applies with more force here, because these articles carry
  `review_tier` and a verification date.

---

## 2. What a translation is allowed to supply

Prose. That is the whole list.

Paths, canonicals, hreflang, JSON-LD, og tags, next-step URLs, screenshot
slots, and the rendered date are all derived from the English record. Setting
one of them in an overlay is a build error, and that is the point: a
translation cannot invent a URL or a structured-data graph in a language nobody
here can proofread.

An overlay record therefore carries:

| Field | What it is |
| --- | --- |
| `source` | The English record it translates, e.g. `learn/portugal-183-day-tax-residency.html` |
| `headline` | The `<h1>` and the basis of the `<title>` |
| `description` | The meta description |
| `content` | Path to the translated fragment |
| `next_steps` | Titles and descriptions only; the URLs come from English |
| `search_synonyms` | Query terms in the target language, for the site search index |
| `screenshot_alt` | Per-slot alt text (Help only) |
| `source_hash`, `source_meta_hash` | What the translation was made from |
| `translated_on`, `translated_by` | Provenance |

### Slugs stay English

`/nl/learn/portugal-183-day-tax-residency`, not `/nl/leren/portugal-183-dagen-regel`.

This is a deliberate trade. A Dutch slug would carry a little more keyword
signal, but the build derives every route from the English record on purpose,
and a translated path would mean each locale can mint URLs that nobody here can
audit, plus a permanent redirect obligation the first time a translator changes
their mind about a word. The title, the `<h1>`, the description, and the body
carry the target-language keywords, and those are where the weight actually
sits. Japanese Help has worked this way since it shipped.

Revisit this only with evidence that the path segment is costing real traffic,
and only together with a redirect plan.

---

## 3. Structural parity, and why it is mechanical

`scripts/check_translations.py` fails the build when a translation has a
different number of `<h2>` sections, `<ol>` lists, `<li>` items,
troubleshooting blocks, or screenshot slots than its English source, when it
drops an internal link, invents one, or loses a number that the English
contains.

None of this judges quality. It exists because the failure it catches is
invisible: a translation that quietly drops the third step of a five-step
procedure, or the sentence carrying the exception to the rule, looks completely
normal on the page to everyone who cannot read both.

Consequences for how you work:

- **Keep the fragment's shape.** One English `<li>` is one target `<li>`. Do
  not merge two short list items into a natural-sounding single one, and do not
  split a long one.
- **Every number in the English must appear in the translation.** The check is
  one-directional, so adding numbers is allowed (`6月1日、6月2日` for `June 1 to
  June 2` is fine, and so is Dutch writing a range out). Losing one is not,
  including when a number moves into a word: `nine months` may become `negen
  maanden`, but if the English also wrote `(about 270 days)` the `270` has to
  survive.
- **Internal links are positional, not optional.** The checker resolves each
  English `href` through the locale and expects exactly that set. A link to a
  page the locale does not have resolves to the English page, which is correct
  and intended.
- **External sources keep their original URL and their original language.** Do
  not translate the name of a government page, and do not swap a source for a
  target-language equivalent. `Belastingdienst` is not a substitute for the
  Portuguese tax authority. Where the official source has an official page in
  the target language, you may add its name in parentheses; the URL still
  points where English points.

### Staleness is a feature

Each overlay pins `source_hash` (the English fragment) and `source_meta_hash`
(its title, description, next steps, and screenshot alt text). Editing English
copy fails the build until every translation catches up.

When an English edit genuinely does not change meaning, add a `stale_ack` with
the new hash, a one-line reason, and an `expires` date. When it does change
meaning, retranslate. Do not add a `stale_ack` because the retranslation is
inconvenient; the expiry exists to make that visible.

**Edit English and its translations in the same commit.** Do not leave a
language behind and plan to catch up.

---

## 4. Terminology

### The app is the authority for the Help Center

Unchanged from the app document. A Help article is a set of instructions about
the app's screens, so every UI element it names must use the string the app
ships in that language. `scripts/sync_glossary.py` snapshots the app's
accepted-terminology tables and shipped `.xcstrings` values into
`_site-src/data/glossary.json`, and `check_translations.py` enforces them.
Re-run the sync whenever the app moves.

### Learn is domain vocabulary, not app vocabulary

`check_translations.py` applies the term tables to `help/` only. Learn articles
explain tax and immigration rules and mostly never name a control, so the app's
UI table starts matching ordinary prose instead: the tracker preset `Custom`
generates the plural `Customs`, which is border control in four English
articles, and enforcing the preset's wording there would corrupt a sentence to
satisfy a check.

Brand and format names are still enforced everywhere: `AtlasDays`, `iPhone`,
`iCloud`, `App Store`, `CSV`, `PDF`, `Flighty`, `ESTA` must survive
untranslated in every section, and the brand stays in Latin script in every
script.

What replaces the table for Learn is the per-language domain vocabulary in
section 8. Fill it in as you go; a term you had to think about once is a term
the next translator will have to think about again.

### Where the two meet

A Learn article that describes what the app does (the CTA box, a "how AtlasDays
counts this" aside) is app copy inside a Learn page. Use the app's shipped
wording there, and check it against the app rather than inventing a synonym.

---

## 5. Titles, descriptions, and search

This is the part with no counterpart in the app document, and the part where
being literal actively costs something.

- **The `<h1>` and `<title>` should read like the thing a native speaker would
  search for.** English `Portugal's 183-Day Tax Residency Rule` is a search
  phrase, not a sentence, and the Dutch equivalent is a different search
  phrase. Translate the intent.
- **Follow the target language's title convention.** English uses title case;
  Dutch, German, French, and Spanish use sentence case. Copying English
  capitalization into them is the single most obvious mark of a translated
  page.
- **Keep the meta description under about 155 characters** and make it a real
  summary, not the first sentence of the article. It has the same job in every
  language: tell someone scanning a result page whether this answers their
  question.
- **`search_synonyms` is not a translation.** It is the list of things people
  actually type in that language, including the spellings you would never write
  in prose (`183 dagen regel` without the hyphen, `belasting buitenland`, the
  English term a Dutch reader may search anyway). Never translate the English
  synonym list; write the target-language one from scratch.
- **The title separator is per locale.** `" – "` in English and Dutch, `"｜"` in
  Japanese. It comes from `locales.json`; do not put it in copy.

---

## 6. Typography

- **The em dash (U+2014) is banned in every language, on every surface.** House
  rule, mechanically enforced. Replace it with an en dash, or reword with a
  period or comma.
- **The en dash (U+2013) is the English and Dutch replacement.** It is not
  Japanese punctuation and is banned there too: split the sentence with `。` or
  use `（…）` / `「…」`.
- Use the target language's own quotation marks, ellipsis, and spacing. French
  needs a nonbreaking space before `:`, `;`, `?`, and `!`, and guillemets. A
  scripted find-and-replace will destroy these; check after any bulk edit.
- Counts are written as uninterrupted digits in every locale: `2296`, never
  `2.296` or `2,296`.
- Japanese: full-width punctuation, no half-width katakana, no space between a
  digit and its counter, full-width ellipsis.

---

## 7. Workflow

```sh
python3 scripts/check_translations.py        # run this first; it gates the rest
python3 scripts/build_site.py                # render every locale
python3 scripts/build_search_index.py        # per-locale search entries
python3 scripts/build_site.py --check        # committed HTML matches the sources
python3 scripts/audit_site.py --strict-semantics --check-baseline _site-src/data/baseline.json
```

A new language is `locales.json` + an `ui-strings.json` column + an overlay
registry + fragments. If it needs a change under `scripts/`, that is a bug in
the machinery, not a missing feature.

Ship it as `status: "draft"` first. A draft locale builds and previews but is
`noindex`, and stays out of the sitemap, hreflang, `llms.txt`, and the language
switcher, which is how a language is verified end to end before anyone can find
it. Flip to `published` only when the section is complete, because partial
coverage that is indexed is worse than no coverage: it puts a reader on a
target-language page whose neighbours are all English.

### Order of work

1. Chrome (`ui-strings.json`), so every page frame is in the language.
2. The section hub, which is the entry point and sets the vocabulary.
3. The pillar articles the hub leads with.
4. The rest, in clusters, so terminology settles cluster by cluster.

### Keeping the hub honest while a section is partly translated

A hub has to carry the same link set as its English source, so it lists every
article whether or not that article exists in the target language yet. Which
means the hub can lie: a translated title next to a link that lands on English.

The rule is that **a card shows the target-language title only when the article
behind it is translated, and the English title otherwise.** Translating an
article is therefore two edits, not one: the fragment, and its card on the hub.

The Dutch hub was produced by transforming the English fragment
programmatically, which is worth repeating for the next language and the next
batch: place names, types, and article titles are all data the build already
has, so deriving them keeps the link set and the list counts identical by
construction rather than by proofreading.

Reread each finished article in the target language alone, without the English
beside it. That pass catches copied capitalization, English word order that is
grammatical but foreign, and sentences that only parse if you know the source.

### What to report back

The reader of your report does not speak the target language. Give them:

1. What is covered and what is not, by count.
2. The register and conventions chosen, with the reason.
3. Domain terminology decided, with rejected alternatives and why.
4. Every material adaptation: final wording, literal back-translation, reason.
5. Any English source error found and fixed along the way.
6. Validation run and its result.
7. Where a native review would still be worth having.

Routine word order and inflection do not need a note. A changed metaphor, a
combined or dropped idea, a loanword chosen over a native term, and any copy
shortened to fit do.

---

## 8. Per-language notes

### Dutch (`nl`)

Register and conventions carry over from the app document: informal `je/jij`,
never `u`; Dutch sentence case; ungrouped digits; `datums`, never `data`, for
calendar dates.

Loanwords the app keeps and this site keeps: `app`, `tracker`, `widget`,
`preset`, `CSV`, `PDF`. Visa terms the app keeps because the Dutch
alternatives sound coined: `Visitor Visa`, `Standard Visitor`, `Visa Waiver
Program`, and the codes `ESTA`, `eTA`, `B-1/B-2` exactly as written. Generic
descriptions stay Dutch: `kort verblijf`, `visumvrij verblijf`.

#### Accepted Dutch domain terms

Learn-specific. The app's own table still governs anything naming a screen.

| English | Dutch | Note |
| --- | --- | --- |
| tax residency (the status) | fiscaal inwonerschap | Never `fiscale residentie`, an anglicism |
| tax resident (the person) | fiscaal inwoner | |
| tax residence (the place) | fiscale woonplaats | |
| day count | dagentelling | Not `dagtelling`; plural `dagentellingen` |
| day limit | daglimiet | Never `daggrens`: in a travel app `grens` reads as a border |
| threshold | drempel | Only for a true threshold; a cap is a `limiet` |
| rolling window | voortschrijdende periode | Never `verschuivende` |
| rolling 12 months | voortschrijdende periode van 12 maanden | |
| calendar year | kalenderjaar | |
| tax year | belastingjaar | |
| income year (AU) | inkomstenjaar | Australia's own term; do not flatten to `belastingjaar` |
| arrival day / departure day | dag van aankomst / dag van vertrek | |
| day of presence | verblijfsdag | |
| stay | verblijf | |
| short stay | kort verblijf | |
| visa-free | visumvrij | |
| entry (an admission) | inreis | One family: `inreisregel`, `visum voor één inreis` |
| overstay (verb) | langer blijven dan is toegestaan | |
| overstay (noun) | overschrijding van de toegestane verblijfsduur | Compact contexts may use `overstay` |
| statutory residency | wettelijk inwonerschap | US state articles |
| presumption | vermoeden | `rebuttable presumption` is `weerlegbaar vermoeden` |
| substantial presence test | Substantial Presence Test | Official name; gloss once, then keep |
| Statutory Residence Test (UK) | Statutory Residence Test | Official name; gloss once, then keep |
| travel history | reisgeschiedenis | |
| travel record | reisadministratie | The evidence, not the app's Timeline |
| proof / evidence | bewijs | |
| border control, customs | douane, grenscontrole | Nothing to do with the app's `Custom` preset |
| layover | overstap | `transit` stays `transit` where the app's concept is meant |

#### Place names

- Countries take their normal Dutch name: `Ierland`, `Griekenland`, `Tsjechië`,
  `Turkije`, `Estland`, `Roemenië`, `Servië`, `Bulgarije`, `Australië`,
  `Indonesië`, `Italië`, `Maleisië`, `Nieuw-Zeeland`, `Verenigd Koninkrijk`,
  `Verenigde Staten`, `Verenigde Arabische Emiraten`, `Georgië` (the country).
- The English site writes `Türkiye`; Dutch prose uses `Turkije`. Name the
  official form once where the article is about Türkiye itself.
- **US state names keep their American spelling**, with `Californië` and
  `Hawaï` as the only exceptions. This is a reviewed AtlasDays decision against
  the prescriptive list: the Taalunie registers `Pennsylvanië` and
  `Nieuw-Mexico`, but contemporary Dutch writing does not use them. Do not
  change it from a dictionary alone.
- `Georgia` the US state stays `Georgia`, which conveniently disambiguates it
  from `Georgië` the country. Both have an article.
- `Schengen` keeps its Latin spelling and so does the whole word family:
  `Schengengebied`, `Schengenvisum`, `de Schengenregels`.

#### Numbers and rules in Dutch

- Hyphenate a numeral compound: `183-dagenregel`, `90/180-regel`,
  `6-maandenlimiet`. Not `183 dagen regel`.
- `meer dan 183 dagen` and `183 dagen of meer` are different rules. Read the
  English operator before you write either.
- Write `1 juli` and `14 augustus 2026`; the build renders record dates itself.
- `dagen` and `nachten` are counted, not estimated: keep `about` as `ongeveer`
  where English hedges.

#### Sentences that must survive intact

The disclaimer, in every article and hub that carries it:

> **Let op:** AtlasDays geeft algemene informatie, geen juridisch of fiscaal
> advies. Controleer beslissingen die je nu neemt bij een officiële bron of een
> gekwalificeerde professional.

Keep it identical everywhere. It is the sentence a reader is most likely to
quote back.
