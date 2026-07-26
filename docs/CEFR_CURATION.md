# CEFR Curation

The bundled vocabulary levels are editorial estimates made by manually
reviewing each aligned word concept and each French verb row. No CEFR package,
frequency library, external vocabulary list, or automatic classifier was used.

## Rubric

| Level | Editorial guideline |
| --- | --- |
| `A1` | Essential function words and concrete vocabulary for identity, family, time, food, home, and basic actions. |
| `A2` | Frequent daily-life, travel, shopping, work, and descriptive vocabulary. |
| `B1` | General independent-use vocabulary, including common abstract ideas and less routine actions. |
| `B2` | Nuanced, lower-frequency, technical, idiomatic, or domain-specific vocabulary. |
| `C1` | Specialized, literary, formal, or distinctly uncommon vocabulary. |
| `C2` | Archaic, culturally specific, nonstandard, or exceptionally rare vocabulary. |

The level estimates lexical acquisition difficulty, not conjugation difficulty.
French verb group and irregularity informed borderline decisions but did not
automatically determine the level.

## Scope and duplicate policy

- Word levels apply to the shared sense aligned across Spanish, French,
  English, and Russian in one CSV row.
- Verb levels are authored on the French master row and inherited by its
  aligned translations.
- The database stores one item per normalized language and spelling. When
  several senses or source rows converge on the same headword, the easiest
  level wins so a common A1 sense is not hidden by a rarer B2 sense.
- User-added content remains unclassified (`NULL`) until reviewed.

## Current coverage

| Source | A1 | A2 | B1 | B2 | C1 | C2 | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Word concepts | 265 | 309 | 223 | 127 | 38 | 2 | 964 |
| Legacy verb rows | 117 | 313 | 421 | 241 | 35 | 3 | 1,130 |

Run `pytest tests/test_seed_cefr.py` after editing any level. The test checks
coverage, valid values, duplicate consistency, subset drift, and propagation to
the normalized verb inventory and batch manifests.
