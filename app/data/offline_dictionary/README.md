# Offline sense dictionary

Download and import trusted senses for words already in the database:

```bash
make sense-import
```

The bootstrap reads the native English, French, Spanish, and Russian
Wiktionary editions from Kaikki's per-word JSONL files. Downloads are cached
under `.local/dictionary/`, so a repeated import does not redownload them.
Only translations that have an explicit source sense index or a unique
lexical match are accepted. Ambiguous translation-to-sense mappings are
skipped instead of guessed.

Kaikki data is derived from Wiktionary and is distributed under Wiktionary's
CC BY-SA and GFDL terms. Preserve source attribution when publishing imported
definitions, examples, or translations outside this local application.

For a custom source, normalize it first and run:

```bash
make sense-import SENSE_FILE=your-senses.jsonl
```

Each normalized JSONL line represents one sense:

```json
{"language":"EN","word":"bank","sense_key":"wiktionary:en:bank:noun:1","part_of_speech":"noun","definition":"A financial institution that accepts deposits and lends money.","examples":["She deposited her salary at the bank."],"translations":{"FR":[{"translation":"banque"}],"ES":[{"translation":"banco"}],"RU":[{"translation":"банк"}]},"source":"wiktextract","source_version":"2026-07","is_primary":true}
```

The importer accepts only languages already present in the application. It
updates matching `(word, sense_key)` rows and does not delete other senses.
Imported rows are marked trusted; AI-created and migration-backfilled legacy
senses are not eligible for automatic contextual selection.
User context and questions are never part of this file or the global sense
tables.

Wiktextract/Kaikki output should be normalized into this deliberately small
format before import. Keep the original source and version so dictionary
licensing and future refreshes remain traceable.
