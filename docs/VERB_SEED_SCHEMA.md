# Verb Seed Schema

- Source file: `app/data/legacy_seed/verbs/1000verbs.csv`
- Purpose: bootstrap French and Spanish verb translation records.

## Columns

| Column | Meaning |
| --- | --- |
| `ID` | Stable legacy identifier. |
| `FR` | Canonical French infinitive. |
| `FR_group` | Legacy French conjugation group. |
| `ES` | Spanish equivalent(s), comma-delimited when several are present. |
| `cefr_level` | Manually curated difficulty: `A1`, `A2`, `B1`, `B2`, `C1`, or `C2`. |

## CEFR behavior

- The level describes the French verb and its aligned core sense; it was
  assigned by manual review without a CEFR package or external word list.
- The seed importer stores it on the French and primary Spanish `Verb` rows and
  mirrors it to the existing difficulty tag.
- The curated multilingual inventory carries the same field to alternate
  Spanish equivalents and the curated English and Russian equivalents.
- If several source senses converge on the same translated infinitive, the
  database keeps the earliest (easiest) level. A headword known in an A1 sense
  should remain available at A1 even if another sense is more advanced.
- `11verbs.csv` and `20verbs.csv` are samples of the master file and must keep
  matching levels.

User-added or admin-created verbs may leave `cefr_level` empty until someone
reviews them; the database constraint rejects values outside A1–C2.
