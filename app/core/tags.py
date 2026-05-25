from __future__ import annotations

from dataclasses import dataclass


WORD_ITEM = "word"
VERB_ITEM = "verb"


@dataclass(frozen=True, slots=True)
class TagDefinition:
    slug: str
    display_name: str
    kind: str
    applies_to: tuple[str, ...] = (WORD_ITEM, VERB_ITEM)


CURATED_TAGS: tuple[TagDefinition, ...] = (
    # Themes: broad enough for smart sets, specific enough to feel useful.
    TagDefinition("travel", "Travel", "thematic"),
    TagDefinition("food", "Food", "thematic"),
    TagDefinition("drink", "Drink", "thematic"),
    TagDefinition("cooking", "Cooking", "thematic"),
    TagDefinition("body", "Body", "thematic"),
    TagDefinition("clothing", "Clothing", "thematic"),
    TagDefinition("family", "Family", "thematic"),
    TagDefinition("work", "Work", "thematic"),
    TagDefinition("professions", "Professions", "thematic"),
    TagDefinition("school", "School", "thematic"),
    TagDefinition("house", "House", "thematic"),
    TagDefinition("furniture", "Furniture", "thematic"),
    TagDefinition("home_appliances", "Home appliances", "thematic"),
    TagDefinition("household_cleaning", "Household cleaning", "thematic"),
    TagDefinition("personal_care", "Personal care", "thematic"),
    TagDefinition("nature", "Nature", "thematic"),
    TagDefinition("animals", "Animals", "thematic"),
    TagDefinition("plants_garden", "Plants and garden", "thematic"),
    TagDefinition("weather", "Weather", "thematic"),
    TagDefinition("places_geography", "Places and geography", "thematic"),
    TagDefinition("time", "Time", "thematic"),
    TagDefinition("transportation", "Transportation", "thematic"),
    TagDefinition("vehicle_parts", "Vehicle parts", "thematic"),
    TagDefinition("money", "Money", "thematic"),
    TagDefinition("shopping", "Shopping", "thematic"),
    TagDefinition("health", "Health", "thematic"),
    TagDefinition("emotions", "Emotions", "thematic"),
    TagDefinition("sports", "Sports", "thematic"),
    TagDefinition("technology", "Technology", "thematic"),
    TagDefinition("media_communication", "Media and communication", "thematic"),
    TagDefinition("music", "Music", "thematic"),
    TagDefinition("art", "Art", "thematic"),
    TagDefinition("literature", "Literature", "thematic"),
    TagDefinition("law_society", "Law and society", "thematic"),
    TagDefinition("religion", "Religion", "thematic"),
    TagDefinition("accessibility", "Accessibility", "thematic"),
    TagDefinition("baby_childcare", "Baby and childcare", "thematic"),
    TagDefinition("tools_diy", "Tools and DIY", "thematic"),
    TagDefinition("construction", "Construction", "thematic"),
    TagDefinition("materials", "Materials", "thematic"),
    TagDefinition("colors_patterns", "Colors and patterns", "thematic"),
    TagDefinition("shapes_measurements", "Shapes and measurements", "thematic"),
    TagDefinition("directions_positions", "Directions and positions", "thematic"),
    TagDefinition("textures_qualities", "Textures and qualities", "thematic"),
    TagDefinition("abstract_concepts", "Abstract concepts", "thematic"),

    # Grammar and part of speech.
    TagDefinition("verb_action", "Action verb", "grammatical"),
    TagDefinition("verb_state", "State verb", "grammatical"),
    TagDefinition("noun_person", "Noun - person", "grammatical", (WORD_ITEM,)),
    TagDefinition("noun_place", "Noun - place", "grammatical", (WORD_ITEM,)),
    TagDefinition("noun_thing", "Noun - thing", "grammatical", (WORD_ITEM,)),
    TagDefinition("adjective", "Adjective", "grammatical", (WORD_ITEM,)),
    TagDefinition("adverb", "Adverb", "grammatical", (WORD_ITEM,)),
    TagDefinition("preposition", "Preposition", "grammatical", (WORD_ITEM,)),
    TagDefinition("conjunction", "Conjunction", "grammatical", (WORD_ITEM,)),
    TagDefinition("interjection", "Interjection", "grammatical", (WORD_ITEM,)),

    # Verb semantics. These apply to Verb rows and to user-added words that are verbs.
    TagDefinition("verb_motion", "Motion verb", "verb_semantic"),
    TagDefinition("verb_communication", "Communication verb", "verb_semantic"),
    TagDefinition("verb_cognition", "Cognition verb", "verb_semantic"),
    TagDefinition("verb_perception", "Perception verb", "verb_semantic"),
    TagDefinition("verb_emotion", "Emotion verb", "verb_semantic"),
    TagDefinition("verb_possession", "Possession verb", "verb_semantic"),
    TagDefinition("verb_creation", "Creation verb", "verb_semantic"),
    TagDefinition("verb_change", "Change verb", "verb_semantic"),
    TagDefinition("verb_consumption", "Consumption verb", "verb_semantic"),
    TagDefinition("verb_social", "Social verb", "verb_semantic"),
    TagDefinition("verb_work_study", "Work and study verb", "verb_semantic"),
    TagDefinition("verb_body_action", "Body action verb", "verb_semantic"),
    TagDefinition("verb_care", "Care verb", "verb_semantic"),
    TagDefinition("verb_commerce", "Commerce verb", "verb_semantic"),

    # Register.
    TagDefinition("formal", "Formal", "register"),
    TagDefinition("informal", "Informal", "register"),
    TagDefinition("slang", "Slang", "register"),
    TagDefinition("vulgar", "Vulgar", "register"),

    # CEFR-like difficulty.
    TagDefinition("a1", "A1", "difficulty"),
    TagDefinition("a2", "A2", "difficulty"),
    TagDefinition("b1", "B1", "difficulty"),
    TagDefinition("b2", "B2", "difficulty"),
    TagDefinition("c1", "C1", "difficulty"),
    TagDefinition("c2", "C2", "difficulty"),
)


TAG_BY_SLUG: dict[str, TagDefinition] = {tag.slug: tag for tag in CURATED_TAGS}
TAG_SLUGS: tuple[str, ...] = tuple(TAG_BY_SLUG)
TAG_SLUG_SET: frozenset[str] = frozenset(TAG_SLUGS)


def tags_for_item_type(item_type: str) -> tuple[TagDefinition, ...]:
    return tuple(tag for tag in CURATED_TAGS if item_type in tag.applies_to)


def tag_slugs_for_item_type(item_type: str) -> tuple[str, ...]:
    return tuple(tag.slug for tag in tags_for_item_type(item_type))


def tag_prompt_list(item_type: str = WORD_ITEM) -> str:
    return ", ".join(tag_slugs_for_item_type(item_type))


def tag_seed_rows() -> list[dict[str, object]]:
    return [
        {
            "slug": tag.slug,
            "display_name": tag.display_name,
            "kind": tag.kind,
            "applies_to": list(tag.applies_to),
        }
        for tag in CURATED_TAGS
    ]
