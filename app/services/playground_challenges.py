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
    "retrouvailles": PlaygroundChallenge(
        accepted_answers=(
            "the meeting again of people who have been apart, often with strong emotion",
            "the reunion of people after a long period of separation",
            "le fait de se revoir après une période de séparation, souvent avec émotion",
            "el reencuentro de personas que llevaban tiempo separadas, a menudo con emoción",
            "es volver a verse después de haber pasado mucho tiempo separados",
            "встреча людей после долгой разлуки, часто сопровождаемая сильными эмоциями",
        ),
        required_concepts=(
            (
                "Meeting one another again",
                (
                    "people who already know each other meet or see one another again",
                    "des personnes qui se connaissent se revoient",
                    "personas que ya se conocen vuelven a verse",
                    "знакомые люди снова встречаются",
                ),
            ),
            (
                "After time apart",
                (
                    "after a significant period of separation",
                    "après une période de séparation",
                    "después de pasar un tiempo separadas",
                    "после долгого периода разлуки",
                ),
            ),
        ),
        hard_negatives=(
            (
                "First introduction",
                (
                    "two strangers meeting and introducing themselves for the first time",
                    "deux inconnus qui font connaissance pour la première fois",
                    "dos desconocidos que se conocen por primera vez",
                    "первая встреча незнакомых людей",
                ),
            ),
            (
                "Farewell",
                (
                    "people saying goodbye before separating",
                    "des personnes qui se disent au revoir avant de se séparer",
                    "personas que se despiden antes de separarse",
                    "люди прощаются перед расставанием",
                ),
            ),
            (
                "Finding a lost object",
                (
                    "recovering something that had been lost",
                    "retrouver un objet que l’on avait perdu",
                    "encontrar un objeto que se había perdido",
                    "найти потерянную вещь",
                ),
            ),
        ),
        minimum_glosses=(
            *(
                MinimumGloss(
                    text=text,
                    concept_evidence=(
                        ("Meeting one another again", "explicit"),
                        ("After time apart", "context"),
                    ),
                )
                for text in (
                    "seeing each other again",
                    "meeting again",
                    "a reunion",
                    "se revoir",
                    "se retrouver",
                    "volver a verse",
                    "reencontrarse",
                    "снова встретиться",
                    "снова увидеться",
                )
            ),
            *(
                MinimumGloss(
                    text=text,
                    concept_evidence=(
                        ("Meeting one another again", "explicit"),
                        ("After time apart", "explicit"),
                    ),
                )
                for text in (
                    "meeting again after time apart",
                    "seeing each other again after a long time",
                    "a reunion after a long time",
                    "se revoir après longtemps",
                    "se retrouver après une longue séparation",
                    "volver a verse después de mucho tiempo",
                    "reencontrarse después de una separación",
                    "reencuentro después de mucho tiempo",
                    "personas que se vuelven a encontrar después de años",
                    "встретиться снова после долгой разлуки",
                    "увидеться снова спустя долгое время",
                )
            ),
        ),
        context_concepts=("After time apart",),
    ),
    "esprit_escalier": PlaygroundChallenge(
        accepted_answers=(
            "the experience of thinking of the perfect reply only after the conversation has ended",
            "thinking of the response one should have given when it is already too late",
            "le fait de trouver la bonne réplique seulement après que la conversation est terminée",
            "la experiencia de pensar en la respuesta perfecta cuando la conversación ya ha terminado",
            "la respuesta perfecta se te ocurre cuando la conversación ya ha terminado",
            "ситуация, когда удачный ответ приходит в голову лишь после окончания разговора",
        ),
        required_concepts=(
            (
                "Thinking of the fitting reply",
                (
                    "thinking of the response or comeback one should have given",
                    "trouver la réponse ou la réplique que l’on aurait voulu donner",
                    "pensar en la respuesta o réplica que se debería haber dado",
                    "придумать подходящий ответ, который следовало дать",
                ),
            ),
            (
                "Only after the opportunity has passed",
                (
                    "the reply occurs too late, after the conversation or moment has ended",
                    "la réponse vient trop tard, après la fin de la conversation",
                    "la respuesta llega demasiado tarde, cuando la conversación ya terminó",
                    "ответ приходит слишком поздно, уже после окончания разговора",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Immediate wit",
                (
                    "giving the perfect reply immediately during the conversation",
                    "donner immédiatement la réplique parfaite pendant la conversation",
                    "dar inmediatamente la respuesta perfecta durante la conversación",
                    "сразу дать меткий ответ во время разговора",
                ),
            ),
            (
                "Never finding a reply",
                (
                    "never thinking of anything to say",
                    "ne jamais trouver quoi répondre",
                    "no llegar nunca a pensar en una respuesta",
                    "так и не придумать, что ответить",
                ),
            ),
            (
                "Literal staircase",
                (
                    "a thought about stairs or climbing steps",
                    "une pensée concernant un escalier ou le fait de monter des marches",
                    "un pensamiento sobre una escalera o subir peldaños",
                    "мысль о лестнице или подъёме по ступеням",
                ),
            ),
        ),
        minimum_glosses=tuple(
            MinimumGloss(
                text=text,
                concept_evidence=(
                    ("Thinking of the fitting reply", "explicit"),
                    ("Only after the opportunity has passed", "explicit"),
                ),
            )
            for text in (
                "thinking of the right reply too late",
                "thinking of a reply too late",
                "the perfect comeback comes too late",
                "the answer comes too late",
                "finding the right words after the conversation",
                "trouver la bonne réponse trop tard",
                "trouver la réponse trop tard",
                "penser à la réponse trop tard",
                "penser à la réplique après la conversation",
                "pensar la respuesta correcta demasiado tarde",
                "pensar la respuesta demasiado tarde",
                "una respuesta que se te ocurre cuando ya es tarde",
                "encontrar la réplica cuando ya terminó la conversación",
                "trouver quoi dire une fois la conversation finie",
                "придумать хороший ответ слишком поздно",
                "ответ приходит в голову после разговора",
            )
        ),
    ),
    "madrugar": PlaygroundChallenge(
        accepted_answers=(
            "to get up at dawn or very early in the morning",
            "to wake up and leave bed much earlier than usual",
            "se lever à l’aube ou très tôt le matin",
            "levantarse al amanecer o muy temprano",
            "levantarse mucho antes de lo normal, cuando todavía está amaneciendo",
            "вставать на рассвете или очень рано утром",
        ),
        required_concepts=(
            (
                "Getting out of bed",
                (
                    "waking up and getting out of bed",
                    "se réveiller et se lever",
                    "despertarse y levantarse de la cama",
                    "проснуться и встать с постели",
                ),
            ),
            (
                "At a very early hour",
                (
                    "at dawn or very early in the morning",
                    "à l’aube ou très tôt le matin",
                    "al amanecer o muy temprano por la mañana",
                    "на рассвете или очень рано утром",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Going to bed early",
                (
                    "going to bed early in the evening",
                    "se coucher tôt le soir",
                    "acostarse temprano por la noche",
                    "рано ложиться спать вечером",
                ),
            ),
            (
                "Staying awake until dawn",
                (
                    "staying awake all night until the sun rises",
                    "rester éveillé toute la nuit jusqu’au lever du soleil",
                    "quedarse despierto toda la noche hasta el amanecer",
                    "не спать всю ночь до рассвета",
                ),
            ),
            (
                "Sleeping late",
                (
                    "sleeping until late in the morning",
                    "dormir jusque tard dans la matinée",
                    "dormir hasta tarde por la mañana",
                    "спать допоздна утром",
                ),
            ),
        ),
        minimum_glosses=tuple(
            MinimumGloss(
                text=text,
                concept_evidence=(
                    ("Getting out of bed", "explicit"),
                    ("At a very early hour", "explicit"),
                ),
            )
            for text in (
                "get up very early",
                "get up early",
                "wake up very early",
                "wake up early",
                "rise at dawn",
                "se lever très tôt",
                "se lever tôt",
                "se réveiller à l’aube",
                "se réveiller tôt",
                "levantarse muy temprano",
                "levantarse temprano",
                "despertarse al amanecer",
                "despertarse temprano",
                "salir de la cama al amanecer",
                "вставать очень рано",
                "вставать рано",
                "просыпаться на рассвете",
                "просыпаться рано",
            )
        ),
    ),
    "estrenar": PlaygroundChallenge(
        accepted_answers=(
            "to use or wear something for the first time",
            "to make the first use of something new",
            "utiliser ou porter quelque chose pour la première fois",
            "usar o llevar algo por primera vez",
            "ponerse de verdad el abrigo por primera vez",
            "использовать или надеть что-либо в первый раз",
        ),
        required_concepts=(
            (
                "Using or wearing something",
                (
                    "using, wearing, or putting something into service",
                    "utiliser, porter ou mettre quelque chose en service",
                    "usar, llevar o poner algo en servicio",
                    "использовать, надевать или вводить что-либо в действие",
                ),
            ),
            (
                "For the first time",
                (
                    "doing so for the first time",
                    "le faire pour la première fois",
                    "hacerlo por primera vez",
                    "сделать это в первый раз",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Buying something",
                (
                    "buying or receiving something new without using it",
                    "acheter ou recevoir quelque chose de neuf sans l’utiliser",
                    "comprar o recibir algo nuevo sin usarlo",
                    "купить или получить новую вещь, не используя её",
                ),
            ),
            (
                "Using it again",
                (
                    "using again something that has already been used many times",
                    "réutiliser quelque chose qui a déjà beaucoup servi",
                    "volver a usar algo que ya se ha usado muchas veces",
                    "снова использовать вещь, которой уже много раз пользовались",
                ),
            ),
            (
                "Repairing it",
                (
                    "repairing or restoring something old",
                    "réparer ou restaurer quelque chose d’ancien",
                    "reparar o restaurar algo viejo",
                    "чинить или восстанавливать старую вещь",
                ),
            ),
            (
                "Premiering a performance",
                (
                    "presenting a film, play, or public performance for the first time",
                    "présenter un film, une pièce ou un spectacle au public pour la première fois",
                    "presentar una película, obra o espectáculo al público por primera vez",
                    "впервые представить публике фильм, пьесу или спектакль",
                ),
            ),
        ),
        minimum_glosses=tuple(
            MinimumGloss(
                text=text,
                concept_evidence=(
                    ("Using or wearing something", "explicit"),
                    ("For the first time", "explicit"),
                ),
            )
            for text in (
                "use it for the first time",
                "use something for the first time",
                "wear it for the first time",
                "wear something for the first time",
                "first use of something",
                "l’utiliser pour la première fois",
                "utiliser quelque chose pour la première fois",
                "le porter pour la première fois",
                "usarlo por primera vez",
                "usar algo por primera vez",
                "ponérselo por primera vez",
                "ponerse algo por primera vez",
                "использовать впервые",
                "надеть в первый раз",
            )
        ),
    ),
    "empalagar": PlaygroundChallenge(
        accepted_answers=(
            "for something sweet or rich to become cloying and cause weariness or dislike",
            "to overwhelm someone with excessive sweetness until it is no longer pleasant",
            "devenir écœurant parce que c’est excessivement sucré ou riche",
            "resultar empalagoso por ser demasiado dulce y terminar causando hastío",
            "ser tan dulce que acaba cansando y quita las ganas de seguir tomándolo",
            "стать приторным из-за чрезмерной сладости и вызвать отвращение",
        ),
        required_concepts=(
            (
                "Excessive sweetness or richness",
                (
                    "so sweet or rich that it becomes excessive",
                    "si sucré ou riche que cela devient excessif",
                    "tan dulce o intenso que resulta excesivo",
                    "настолько сладкий или насыщенный, что это становится чрезмерным",
                ),
            ),
            (
                "Causing weariness or dislike",
                (
                    "causing weariness, aversion, or loss of enjoyment",
                    "provoquer de la lassitude, du dégoût ou une perte de plaisir",
                    "causar hastío, rechazo o dejar de resultar agradable",
                    "вызывать пресыщение, отвращение или потерю удовольствия",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Pleasant sweetness",
                (
                    "being pleasantly sweet and enjoyable",
                    "être agréablement sucré et plaisant",
                    "ser agradablemente dulce y apetecible",
                    "быть приятно сладким и вкусным",
                ),
            ),
            (
                "Spoiled or bitter food",
                (
                    "food tasting spoiled, rotten, or bitter",
                    "un aliment au goût avarié, pourri ou amer",
                    "una comida con sabor estropeado, podrido o amargo",
                    "еда с испорченным, тухлым или горьким вкусом",
                ),
            ),
            (
                "Food allergy",
                (
                    "having an allergic reaction to an ingredient",
                    "avoir une réaction allergique à un ingrédient",
                    "tener una reacción alérgica a un ingrediente",
                    "испытывать аллергическую реакцию на ингредиент",
                ),
            ),
        ),
        minimum_glosses=(
            *(
                MinimumGloss(
                    text=text,
                    concept_evidence=(
                        ("Excessive sweetness or richness", "explicit"),
                        ("Causing weariness or dislike", "optional_omitted"),
                    ),
                )
                for text in (
                    "too sweet",
                    "it is too sweet",
                    "overly sweet",
                    "excessively rich",
                    "trop sucré",
                    "c’est trop sucré",
                    "écœurant de sucre",
                    "demasiado dulce",
                    "es demasiado dulce",
                    "excesivamente dulce",
                    "слишком сладкий",
                    "приторный",
                )
            ),
            *(
                MinimumGloss(
                    text=text,
                    concept_evidence=(
                        ("Excessive sweetness or richness", "explicit"),
                        ("Causing weariness or dislike", "explicit"),
                    ),
                )
                for text in (
                    "so sweet it becomes unpleasant",
                    "cloyingly sweet",
                    "very sweet and tiring",
                    "si sucré que cela devient écœurant",
                    "tan dulce que termina cansando",
                    "tan dulce que cansa",
                    "muy dulce y te termina cansando",
                    "tan dulce que resulta desagradable",
                    "настолько сладкий, что становится неприятно",
                )
            ),
        ),
    ),
}


def get_playground_challenge(challenge_id: str) -> PlaygroundChallenge:
    try:
        return PLAYGROUND_CHALLENGES[challenge_id]
    except KeyError as exc:
        raise ValueError("Unknown semantic playground challenge.") from exc
