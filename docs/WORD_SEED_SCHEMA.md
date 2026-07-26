# Word Seed Schema

- Source file: `app/data/legacy_seed/words/es_fr_top1000.csv`
- Purpose: bootstrap the aligned multilingual word inventory used by the seed importer.

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
| `tags` | Semicolon-delimited curated thematic and grammatical tag slugs. |
| `cefr_level` | Manually curated concept difficulty: `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`. |

## Import Behavior

- `scripts/seed_from_legacy_csv.py` imports any populated language columns pairwise.
- A row with Spanish, French, English, and Russian values creates translation rows for:
  - ES → FR / EN / RU
  - FR → ES / EN / RU
  - EN → ES / FR / RU
  - RU → ES / FR / EN
- Synonym columns are attached to the translation target language for that pair.
- `cefr_level` is copied to every language-specific `Word` created from the
  aligned row and mirrored to its matching difficulty tag for smart sets.

## Notes

- Keep one dominant sense per row.
- Use semicolons for synonym lists.
- Leave language fields blank only when a row genuinely cannot be aligned across that language.
- CEFR is a hand-curated learning estimate, not a claim that every equivalent
  appears at exactly the same stage in every curriculum.
- When the same normalized headword appears in more than one row, those rows
  must use the same level because the database stores one `Word` per language
  and spelling.
