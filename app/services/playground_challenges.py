from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class MinimumGloss:
    text: str
    concept_evidence: tuple[
        tuple[
            str,
            Literal["explicit", "context", "optional_omitted"],
        ],
        ...,
    ]


@dataclass(frozen=True, slots=True)
class PlaygroundChallenge:
    accepted_answers: tuple[str, ...]
    required_concepts: tuple[tuple[str, tuple[str, ...]], ...]
    hard_negatives: tuple[tuple[str, tuple[str, ...]], ...]
    minimum_glosses: tuple[MinimumGloss, ...] = ()
    context_concepts: tuple[str, ...] = ()


PLAYGROUND_CHALLENGES: dict[str, PlaygroundChallenge] = {
    "depaysement": PlaygroundChallenge(
        accepted_answers=(
            "the feeling of being outside one’s familiar surroundings and habits",
            "the feeling of unfamiliarity or change caused by leaving one’s usual environment",
            "le sentiment d’être hors de son environnement et de ses habitudes",
            "la sensación de estar fuera del entorno y de las costumbres habituales",
            "ощущение непривычности вдали от знакомого окружения и привычек",
        ),
        required_concepts=(
            (
                "Away from the familiar",
                (
                    "outside one’s usual surroundings or environment",
                    "hors de son environnement habituel",
                    "fuera del entorno habitual",
                    "вне привычного окружения",
                ),
            ),
            (
                "A resulting feeling or shift",
                (
                    "a feeling of unfamiliarity, disorientation, or refreshing change",
                    "un sentiment de changement ou de perte de repères",
                    "una sensación de cambio o desorientación",
                    "ощущение перемены или непривычности",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Comfort in familiar surroundings",
                (
                    "feeling completely at home in familiar surroundings",
                    "se sentir parfaitement chez soi dans un environnement familier",
                    "sentirse completamente a gusto en un entorno familiar",
                    "чувствовать себя уютно в знакомом окружении",
                ),
            ),
            (
                "Travel alone",
                (
                    "travelling to another country without describing a feeling",
                    "voyager dans un autre pays sans décrire de sentiment",
                    "viajar a otro país sin describir ninguna sensación",
                    "поездка в другую страну без описания чувства",
                ),
            ),
            (
                "Homesickness alone",
                (
                    "missing home and wanting to return home",
                    "avoir le mal du pays et vouloir rentrer",
                    "echar de menos casa y querer volver",
                    "скучать по дому и хотеть вернуться",
                ),
            ),
        ),
    ),
    "sobremesa": PlaygroundChallenge(
        accepted_answers=(
            "the time after a meal when people remain at the table talking together",
            "the conversation and social time shared at the table after eating",
            "le moment après le repas où l’on reste à table pour discuter",
            "el tiempo después de comer que se pasa conversando en la mesa",
            "время после еды, когда люди остаются за столом и разговаривают",
        ),
        required_concepts=(
            (
                "After the meal",
                (
                    "after the meal has finished",
                    "après la fin du repas",
                    "después de terminar de comer",
                    "после окончания еды",
                ),
            ),
            (
                "Staying together at the table",
                (
                    "people remain together around the table",
                    "on reste ensemble à table",
                    "la gente permanece junta en la mesa",
                    "люди остаются вместе за столом",
                ),
            ),
            (
                "Conversation or social time",
                (
                    "talking and enjoying social time",
                    "discuter et passer un moment ensemble",
                    "conversar y compartir tiempo",
                    "разговаривать и общаться",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Before the meal",
                (
                    "talking together at the table before the meal begins",
                    "parler ensemble à table avant le début du repas",
                    "hablar juntos en la mesa antes de empezar a comer",
                    "разговаривать за столом до начала еды",
                ),
            ),
            (
                "Conversation during the meal",
                (
                    "talking while everyone is still eating dinner",
                    "parler pendant que tout le monde mange encore",
                    "hablar mientras todos siguen comiendo",
                    "разговаривать, пока все ещё едят",
                ),
            ),
            (
                "Dessert",
                (
                    "the dessert or sweet course served after a meal",
                    "le dessert servi après le repas",
                    "el postre servido después de la comida",
                    "десерт, который подают после еды",
                ),
            ),
            (
                "Leaving immediately",
                (
                    "leaving the table immediately when the meal ends",
                    "quitter la table dès que le repas se termine",
                    "levantarse de la mesa en cuanto termina la comida",
                    "сразу уйти из-за стола после окончания еды",
                ),
            ),
        ),
        minimum_glosses=(
            *(
                MinimumGloss(
                    text=text,
                    concept_evidence=(
                        ("After the meal", "context"),
                        ("Staying together at the table", "explicit"),
                        ("Conversation or social time", "optional_omitted"),
                    ),
                )
                for text in (
                    "staying at the table",
                    "rester à table",
                    "quedarse en la mesa",
                    "оставаться за столом",
                )
            ),
            *(
                MinimumGloss(
                    text=text,
                    concept_evidence=(
                        ("After the meal", "explicit"),
                        ("Staying together at the table", "optional_omitted"),
                        ("Conversation or social time", "optional_omitted"),
                    ),
                )
                for text in (
                    "the time after eating",
                    "the time after a meal",
                    "the time after the meal",
                    "le moment après le repas",
                    "le temps après le repas",
                    "tiempo después de comer",
                    "el tiempo después de comer",
                    "tiempo después de la comida",
                    "el rato después de comer",
                    "el momento después de comer",
                    "el tiempo tras la comida",
                    "время после еды",
                    "время после приёма пищи",
                )
            ),
            MinimumGloss(
                text="quedarse hablando después de comer",
                concept_evidence=(
                    ("After the meal", "explicit"),
                    ("Staying together at the table", "optional_omitted"),
                    ("Conversation or social time", "explicit"),
                ),
            ),
        ),
        context_concepts=("After the meal",),
    ),
    "tutoyer": PlaygroundChallenge(
        accepted_answers=(
            "to address someone using the informal singular tu rather than formal vous",
            "to use the familiar second-person form when speaking to someone",
            "s’adresser à quelqu’un en utilisant tu plutôt que vous",
            "dirigirse a alguien usando tú en lugar de la forma formal",
            "обращаться к человеку на ты, а не на вы",
        ),
        required_concepts=(
            (
                "Addressing another person",
                (
                    "the way one addresses or speaks to someone",
                    "la manière de s’adresser à quelqu’un",
                    "la forma de dirigirse a otra persona",
                    "форма обращения к другому человеку",
                ),
            ),
            (
                "Using the informal singular form",
                (
                    "using informal singular tu instead of formal vous",
                    "employer tu plutôt que vous",
                    "usar tú en vez de la forma formal",
                    "использовать ты вместо вежливого вы",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Formal address",
                (
                    "addressing someone using formal vous rather than informal tu",
                    "s’adresser à quelqu’un avec vous plutôt que tu",
                    "dirigirse a alguien con la forma formal en lugar de tú",
                    "обращаться к человеку на вы, а не на ты",
                ),
            ),
            (
                "Giving a nickname",
                (
                    "giving someone a friendly nickname",
                    "donner un surnom amical à quelqu’un",
                    "ponerle a alguien un apodo amistoso",
                    "дать человеку дружеское прозвище",
                ),
            ),
            (
                "Being generally rude",
                (
                    "speaking rudely or insulting someone",
                    "parler grossièrement ou insulter quelqu’un",
                    "hablar de manera grosera o insultar a alguien",
                    "говорить грубо или оскорблять человека",
                ),
            ),
        ),
        minimum_glosses=tuple(
            MinimumGloss(
                text=text,
                concept_evidence=(
                    ("Addressing another person", "explicit"),
                    ("Using the informal singular form", "explicit"),
                ),
            )
            for text in (
                "use tu with someone",
                "use informal tu",
                "address someone with tu",
                "talk using tu",
                "utiliser tu avec quelqu’un",
                "dire tu à quelqu’un",
                "employer tu",
                "hablar de tú",
                "tratar de tú",
                "hablarle de tú",
                "hablarse de tú",
                "tratarse de tú",
                "usar tú con alguien",
                "говорить на ты",
                "обращаться на ты",
            )
        ),
    ),
}


def get_playground_challenge(challenge_id: str) -> PlaygroundChallenge:
    try:
        return PLAYGROUND_CHALLENGES[challenge_id]
    except KeyError as exc:
        raise ValueError("Unknown semantic playground challenge.") from exc
