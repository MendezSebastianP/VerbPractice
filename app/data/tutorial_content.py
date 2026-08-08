"""Curated content for the first-run tutorial.

The tutorial is scripted — it tells the learner exactly what to type — so the
words it uses cannot come from the scheduler. They are fixed here, in every
supported language, and seeded into the inventory on demand.

Selection rules for anything added here:
  * one word in, one word out — no phrases, so "type this" is unambiguous;
  * A1 concrete nouns, recognisable to a complete beginner;
  * no near-synonym traps, so a correct answer is never marked wrong;
  * short enough to type on a phone, including the Cyrillic forms.
"""
from __future__ import annotations

LANGUAGE_CODES: tuple[str, ...] = ("EN", "ES", "FR", "RU")

# Five concepts, in the order the tutorial teaches them. The script attaches a
# role to each position (see TUTORIAL_STEP_ROLES), so the order is meaningful.
TUTORIAL_WORDS: tuple[dict[str, str], ...] = (
    {"EN": "day", "ES": "día", "FR": "jour", "RU": "день"},
    {"EN": "water", "ES": "agua", "FR": "eau", "RU": "вода"},
    {"EN": "house", "ES": "casa", "FR": "maison", "RU": "дом"},
    {"EN": "book", "ES": "libro", "FR": "livre", "RU": "книга"},
    {"EN": "friend", "ES": "amigo", "FR": "ami", "RU": "друг"},
)

# Definitions in each language, so the Add Word step of the tutorial resolves
# entirely from the inventory. Without these the lookup falls through to the
# model and every first run costs tokens for a result we already know.
# Two sentences each, matching the shape a real lookup returns — a one-clause
# gloss made the tutorial card visibly thinner than the thing it is teaching.
TUTORIAL_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "EN": "The time between sunrise and sunset, when it is light. It also means a whole period of 24 hours.",
        "ES": "El tiempo entre la salida y la puesta del sol, cuando hay luz. También designa un periodo completo de 24 horas.",
        "FR": "Le temps entre le lever et le coucher du soleil, quand il fait jour. Désigne aussi une période entière de 24 heures.",
        "RU": "Время между восходом и заходом солнца, когда светло. Также означает целый период в 24 часа.",
    },
    {
        "EN": "The clear liquid that falls as rain and fills rivers and seas. It is also what people and animals drink.",
        "ES": "El líquido transparente que cae como lluvia y llena ríos y mares. Es también lo que beben las personas y los animales.",
        "FR": "Le liquide transparent qui tombe en pluie et remplit les rivières et les mers. C'est aussi ce que boivent les personnes et les animaux.",
        "RU": "Прозрачная жидкость, которая выпадает в виде дождя и наполняет реки и моря. Это также то, что пьют люди и животные.",
    },
    {
        "EN": "A building made for people to live in. It usually belongs to one family rather than being divided into flats.",
        "ES": "Un edificio construido para que vivan personas. Suele pertenecer a una sola familia en lugar de estar dividido en pisos.",
        "FR": "Un bâtiment construit pour que des personnes y habitent. Il appartient en général à une seule famille plutôt que d'être divisé en appartements.",
        "RU": "Здание, построенное для проживания людей. Обычно принадлежит одной семье, а не разделено на квартиры.",
    },
    {
        "EN": "A set of printed pages bound together inside a cover. It can hold a story, or information about a subject.",
        "ES": "Un conjunto de páginas impresas encuadernadas dentro de una cubierta. Puede contener una historia o información sobre un tema.",
        "FR": "Un ensemble de pages imprimées reliées à l'intérieur d'une couverture. Il peut contenir une histoire ou des informations sur un sujet.",
        "RU": "Набор печатных страниц, скреплённых под обложкой. Может содержать историю или сведения о какой-либо теме.",
    },
    {
        "EN": "A person you know well and like, who is not part of your family. Friendship is chosen rather than inherited.",
        "ES": "Una persona que conoces bien y aprecias, que no forma parte de tu familia. La amistad se elige, no se hereda.",
        "FR": "Une personne que vous connaissez bien et appréciez, qui ne fait pas partie de votre famille. L'amitié se choisit, elle ne s'hérite pas.",
        "RU": "Человек, которого вы хорошо знаете и любите, но который не является членом вашей семьи. Дружбу выбирают, а не наследуют.",
    },
)

# Grammatical gender of each headword, for the usage note a real lookup carries.
# None means the language does not mark gender on nouns.
TUTORIAL_GENDER: tuple[dict[str, tuple[str | None, str]], ...] = (
    {"EN": (None, "the"), "ES": ("m", "el"), "FR": ("m", "le"), "RU": ("m", "")},
    {"EN": (None, "the"), "ES": ("f", "el"), "FR": ("f", "l'"), "RU": ("f", "")},
    {"EN": (None, "the"), "ES": ("f", "la"), "FR": ("f", "la"), "RU": ("m", "")},
    {"EN": (None, "the"), "ES": ("m", "el"), "FR": ("m", "le"), "RU": ("f", "")},
    {"EN": (None, "the"), "ES": ("m", "el"), "FR": ("l'", "l'"), "RU": ("m", "")},
)

# Note templates, written in the language the definition is shown in.
_NOTE_TEMPLATES: dict[str, dict[str | None, str]] = {
    "EN": {
        "m": "Masculine noun: « {article} {word} ».",
        "f": "Feminine noun: « {article} {word} ».",
        None: "Countable noun: « the {word} », « two {word}s ».",
    },
    "ES": {
        "m": "Sustantivo masculino: «{article} {word}».",
        "f": "Sustantivo femenino: «{article} {word}».",
        None: "Sustantivo contable: «{article} {word}».",
    },
    "FR": {
        "m": "Nom masculin : « {article} {word} ».",
        "f": "Nom féminin : « {article} {word} ».",
        None: "Nom dénombrable : « {article} {word} ».",
    },
    "RU": {
        "m": "Существительное мужского рода: «{word}».",
        "f": "Существительное женского рода: «{word}».",
        None: "Исчисляемое существительное: «{word}».",
    },
}

# The line printed under the translation itself.
_TRANSLATION_NOTE_TEMPLATES: dict[str, str] = {
    "EN": "The everyday translation of « {word} » — the one you will meet most often.",
    "ES": "La traducción cotidiana de «{word}»: la que encontrarás más a menudo.",
    "FR": "La traduction courante de « {word} » — celle que vous rencontrerez le plus souvent.",
    "RU": "Обычный перевод слова «{word}» — тот, который встречается чаще всего.",
}

# Classification tags, matching the shape the AI path suggests.
TUTORIAL_TAGS: tuple[tuple[str, ...], ...] = (
    ("time", "noun_thing", "a1"),
    ("nature", "noun_thing", "a1"),
    ("house", "noun_thing", "a1"),
    ("objects", "noun_thing", "a1"),
    ("people", "noun_person", "a1"),
)


def tutorial_notes(
    word_text: str, source_code: str, definition_code: str
) -> tuple[str | None, str | None, list[str]] | None:
    """(translation note, usage note, tags) for a curated word, or None.

    Everything is rendered in `definition_code`, the language the learner reads
    the result in, so a tutorial card carries the same Note and Tags blocks a
    real lookup does.
    """
    source = source_code.upper()
    target = definition_code.upper()
    if source not in LANGUAGE_CODES or target not in LANGUAGE_CODES:
        return None
    cleaned = word_text.strip().casefold()
    for index, entry in enumerate(TUTORIAL_WORDS):
        if entry[source].casefold() != cleaned:
            continue
        gender, article = TUTORIAL_GENDER[index][source]
        key = gender if gender in ("m", "f") else None
        usage = _NOTE_TEMPLATES[target][key].format(
            article=article, word=entry[source]
        ).replace("  ", " ").replace("' ", "'")
        translation_note = _TRANSLATION_NOTE_TEMPLATES[target].format(word=entry[source])
        return translation_note, usage, list(TUTORIAL_TAGS[index])
    return None

TUTORIAL_PART_OF_SPEECH = "noun"

# Example sentences, in the same language as the headword. A real lookup always
# comes back with these, and a tutorial result that omits them does not look
# like the thing it is teaching — the Examples section simply disappears.
TUTORIAL_EXAMPLES: tuple[dict[str, list[str]], ...] = (
    {
        "EN": ["It rained all day.", "We spent the day at the beach."],
        "ES": ["Llovió todo el día.", "Pasamos el día en la playa."],
        "FR": ["Il a plu toute la journée.", "Nous avons passé la journée à la plage."],
        "RU": ["Дождь шёл весь день.", "Мы провели день на пляже."],
    },
    {
        "EN": ["Can I have a glass of water?", "The water is very cold."],
        "ES": ["¿Me puedes dar un vaso de agua?", "El agua está muy fría."],
        "FR": ["Puis-je avoir un verre d'eau ?", "L'eau est très froide."],
        "RU": ["Можно мне стакан воды?", "Вода очень холодная."],
    },
    {
        "EN": ["Their house is near the river.", "She is not at home today."],
        "ES": ["Su casa está cerca del río.", "Hoy no está en casa."],
        "FR": ["Leur maison est près de la rivière.", "Elle n'est pas à la maison aujourd'hui."],
        "RU": ["Их дом находится у реки.", "Сегодня её нет дома."],
    },
    {
        "EN": ["I am reading a book about birds.", "This book is very long."],
        "ES": ["Estoy leyendo un libro sobre pájaros.", "Este libro es muy largo."],
        "FR": ["Je lis un livre sur les oiseaux.", "Ce livre est très long."],
        "RU": ["Я читаю книгу о птицах.", "Эта книга очень длинная."],
    },
    {
        "EN": ["He is an old friend of mine.", "She came with a friend."],
        "ES": ["Es un viejo amigo mío.", "Vino con un amigo."],
        "FR": ["C'est un vieil ami à moi.", "Elle est venue avec un ami."],
        "RU": ["Он мой старый друг.", "Она пришла с другом."],
    },
)

# What each position teaches. The client mirrors this; it is here so the two
# cannot drift apart silently.
TUTORIAL_STEP_ROLES: tuple[str, ...] = (
    "type-and-enter",   # the prompt, the field, then Enter
    "quick-shot",       # perfect answer auto-submits
    "quick-shot-lost",  # one wrong letter spends it
    "skip",             # skipping costs nothing
    "hint",             # hints are free too
)

TUTORIAL_SOURCE = "tutorial"

# --- verb tables ------------------------------------------------------------
# One regular verb per language plus the tense the tutorial fills. Kept regular
# on purpose: the tutorial teaches the interface, not the exceptions.
TUTORIAL_VERBS: dict[str, dict[str, str]] = {
    "FR": {"infinitive": "parler", "tense": "Présent", "gloss_en": "to speak"},
    "ES": {"infinitive": "hablar", "tense": "Presente", "gloss_en": "to speak"},
    "EN": {"infinitive": "to speak", "tense": "Past", "gloss_en": "to speak"},
    "RU": {"infinitive": "говорить", "tense": "Настоящее", "gloss_en": "to speak"},
}


def tutorial_definition(
    word_text: str, source_code: str, definition_code: str
) -> str | None:
    """The curated definition of a tutorial word, already in the wanted language.

    Lets the Add Word step of the tutorial skip the model call that would
    otherwise rewrite the definition into the learner's language — the one
    remaining place a scripted, fully known lookup would still cost tokens.
    """
    source = source_code.upper()
    target = definition_code.upper()
    if source not in LANGUAGE_CODES or target not in LANGUAGE_CODES:
        return None
    cleaned = word_text.strip().casefold()
    for index, entry in enumerate(TUTORIAL_WORDS):
        if entry[source].casefold() == cleaned:
            return TUTORIAL_DEFINITIONS[index].get(target)
    return None


def tutorial_pairs(source_code: str, target_code: str) -> list[tuple[str, str]]:
    """Prompt/answer pairs for one direction, in tutorial order."""
    source = source_code.upper()
    target = target_code.upper()
    if source not in LANGUAGE_CODES or target not in LANGUAGE_CODES or source == target:
        return []
    return [(entry[source], entry[target]) for entry in TUTORIAL_WORDS]
