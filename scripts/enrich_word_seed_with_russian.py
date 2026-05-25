from __future__ import annotations

from enrich_word_seed_with_language import main


if __name__ == "__main__":
    main(
        default_target_code="RU",
        default_target_language="Russian",
        default_text_column="russian",
        default_synonyms_column="russian synonyms",
    )
