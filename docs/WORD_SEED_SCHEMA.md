# Word Seed Schema

- Source file: `app/data/legacy_seed/words/es_fr_top1000.csv`
- Purpose: bootstrap the legacy bilingual word inventory used by the seed importer.

## Columns

| Column | Meaning |
| --- | --- |
| `spanish` | Canonical Spanish headword or short phrase. |
| `french` | Canonical French headword or short phrase. |
| `english` | Canonical English headword or short phrase. |
| `russian` | Canonical Russian headword or short phrase. |
| `spanish synonyms` | Optional semicolon-delimited Spanish alternatives for the same sense. |
| `french synonyms` | Optional semicolon-delimited French alternatives for the same sense. |
| `english synonyms` | Optional semicolon-delimited English alternatives for the same sense. |
| `russian synonyms` | Optional semicolon-delimited Russian alternatives for the same sense. |

## Import Behavior

- `scripts/seed_from_legacy_csv.py` imports any populated language columns pairwise.
- A row with Spanish, French, English, and Russian values creates translation rows for:
  - ES → FR / EN / RU
  - FR → ES / EN / RU
  - EN → ES / FR / RU
  - RU → ES / FR / EN
- Synonym columns are attached to the translation target language for that pair.

## Notes

- Keep one dominant sense per row.
- Use semicolons for synonym lists.
- Leave language fields blank only when a row genuinely cannot be aligned across that language.
