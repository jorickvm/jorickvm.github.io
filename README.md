# atlasdays.app

Source for [atlasdays.app](https://atlasdays.app), the website of AtlasDays, an iPhone app that counts the days you spend in each country and tracks visa limits and tax-residency thresholds.

The site is static HTML published with GitHub Pages. Most pages, including every translation, are generated from the sources in `_site-src/` and committed, so publishing needs no build step. The tooling is Python 3 with the standard library only.

## Layout

```
_site-src/   content fragments, templates and data the pages are generated from
assets/      stylesheets, scripts, images and downloads
learn/       articles on visa and residency rules (generated)
help/        Help Center articles (generated)
<locale>/    translated pages, one directory per language (generated)
scripts/     build, check and maintenance tooling
```

## Building

```bash
python3 scripts/build_site.py            # regenerate pages from _site-src/
python3 scripts/build_site.py --check    # fail if committed pages are out of date
```

## Local preview

```bash
python3 scripts/serve_site.py --port 8899
```

## Checks

```bash
python3 scripts/audit_site.py --strict-semantics --check-baseline _site-src/data/baseline.json
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
```

CI runs the audit, the translation checks and every `--check` mode on each push to `main`.

## License

Copyright © 2026 Apps by Steed. All rights reserved.
