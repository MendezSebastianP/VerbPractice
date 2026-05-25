from __future__ import annotations

from enrich_word_seed_with_language import main


if __name__ == "__main__":
    main(
        default_target_code="EN",
        default_target_language="English",
        default_text_column="english",
        default_synonyms_column="english synonyms",
    )
