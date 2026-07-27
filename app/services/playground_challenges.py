from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Evidence = Literal["explicit", "context", "optional_omitted"]
ConceptEvidence = tuple[tuple[str, Evidence], ...]


@dataclass(frozen=True, slots=True)
class MinimumGloss:
    text: str
    concept_evidence: ConceptEvidence


@dataclass(frozen=True, slots=True)
class PlaygroundChallenge:
    accepted_answers: tuple[str, ...]
    required_concepts: tuple[tuple[str, tuple[str, ...]], ...]
    hard_negatives: tuple[tuple[str, tuple[str, ...]], ...]
    minimum_glosses: tuple[MinimumGloss, ...] = ()
    context_concepts: tuple[str, ...] = ()


def _glosses(
    texts: tuple[str, ...],
    evidence: ConceptEvidence,
) -> tuple[MinimumGloss, ...]:
    return tuple(
        MinimumGloss(text=text, concept_evidence=evidence) for text in texts
    )


PLAYGROUND_CHALLENGES: dict[str, PlaygroundChallenge] = {
    "se_retrouver": PlaygroundChallenge(
        accepted_answers=(
            "they met or saw each other again after many years apart",
            "to meet or see one another again after having been apart",
            "ils se sont revus après avoir été séparés pendant longtemps",
            "volvieron a verse después de muchos años separados",
            "они снова встретились после многих лет разлуки",
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
                    "après une longue période de séparation",
                    "después de pasar mucho tiempo separados",
                    "после долгого периода разлуки",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Meeting for the first time",
                (
                    "two strangers meet and introduce themselves for the first time",
                    "deux inconnus font connaissance pour la première fois",
                    "dos desconocidos se conocen por primera vez",
                    "два незнакомца встречаются впервые",
                ),
            ),
            (
                "Finding a lost object",
                (
                    "finding an object that had been lost",
                    "retrouver un objet que l’on avait perdu",
                    "encontrar un objeto que se había perdido",
                    "найти потерянную вещь",
                ),
            ),
            (
                "Farewell",
                (
                    "meeting a friend only in order to say goodbye",
                    "retrouver un ami seulement pour lui dire adieu",
                    "ver a un amigo para despedirse",
                    "встретиться с другом только для того, чтобы попрощаться",
                ),
            ),
        ),
        minimum_glosses=(
            *_glosses(
                (
                    "meeting again",
                    "seeing each other again",
                    "seeing a friend again",
                    "se revoir",
                    "retrouver un ami",
                    "ver de nuevo a un amigo",
                    "volver a ver a un amigo",
                    "ver otra vez a un amigo",
                    "ver otra vez a mi amigo",
                    "ver otra vez a alguien conocido",
                    "ver de nuevo a alguien conocido",
                    "volver a verse",
                    "volver a encontrarse con un amigo",
                    "volver a encontrarme con un viejo amigo",
                    "reencontrarse",
                    "reencontrarse con un amigo",
                    "reencontrarse con alguien conocido",
                    "encontrarse otra vez con un amigo",
                    "снова встретиться",
                    "увидеть друга снова",
                ),
                (
                    ("Meeting one another again", "explicit"),
                    ("After time apart", "context"),
                ),
            ),
            *_glosses(
                (
                    "meeting again after a long time",
                    "seeing each other after years apart",
                    "se revoir après une longue séparation",
                    "volver a verse después de muchos años",
                    "volver a ver a una amiga después de años",
                    "encontrarse después de mucho tiempo",
                    "снова встретиться после долгой разлуки",
                ),
                (
                    ("Meeting one another again", "explicit"),
                    ("After time apart", "explicit"),
                ),
            ),
        ),
        context_concepts=("After time apart",),
    ),
    "tutoyer": PlaygroundChallenge(
        accepted_answers=(
            "to address someone with informal tu instead of formal vous",
            "to use the informal singular form of address with another person",
            "s’adresser à quelqu’un avec « tu » plutôt qu’avec « vous »",
            "dirigirse a alguien usando el tú francés en vez de vous",
            "обращаться к человеку на «ты», а не на «вы»",
        ),
        required_concepts=(
            (
                "Addressing another person",
                (
                    "speaking directly to or addressing another person",
                    "s’adresser directement à une autre personne",
                    "dirigirse directamente a otra persona",
                    "обращаться непосредственно к другому человеку",
                ),
            ),
            (
                "Using informal singular tu",
                (
                    "using informal singular tu rather than formal vous",
                    "employer le pronom informel tu plutôt que vous",
                    "usar la forma informal singular tu en vez de vous",
                    "использовать неформальное ты вместо формального вы",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Using formal vous",
                (
                    "addressing someone with formal vous",
                    "s’adresser à quelqu’un en utilisant le vous formel",
                    "tratar a alguien de usted o de vous formalmente",
                    "обращаться к человеку на вы",
                ),
            ),
            (
                "Insulting or being rude",
                (
                    "insulting someone or speaking rudely",
                    "insulter quelqu’un ou lui parler grossièrement",
                    "insultar a alguien o hablarle con grosería",
                    "оскорблять человека или грубо с ним говорить",
                ),
            ),
            (
                "Simply chatting casually",
                (
                    "having a casual conversation without changing the form of address",
                    "bavarder simplement sans changer de pronom",
                    "charlar de manera informal sin cambiar el tratamiento",
                    "просто непринуждённо беседовать",
                ),
            ),
        ),
        minimum_glosses=_glosses(
            (
                "use tu",
                "address informally",
                "address someone as tu",
                "say tu to them",
                "lui dire tu",
                "parler en disant tu",
                "utiliser le tutoiement",
                "hablar de tú",
                "hablarle de tú",
                "hablarse de tu",
                "tratar de tú",
                "usar tú en vez de usted al hablarle",
                "tutear",
                "tutear a alguien",
                "dirigirse a alguien usando tú",
                "dirigirse a él usando tú",
                "обращаться на ты",
                "говорить на ты",
            ),
            (
                ("Addressing another person", "context"),
                ("Using informal singular tu", "explicit"),
            ),
        ),
        context_concepts=("Addressing another person",),
    ),
    "flaner": PlaygroundChallenge(
        accepted_answers=(
            "to stroll or wander at leisure without a particular destination",
            "to move around slowly for pleasure without hurrying anywhere",
            "se promener tranquillement, sans but précis et sans se presser",
            "pasear tranquilamente, sin rumbo concreto ni prisa",
            "paseaba tranquilamente, sin rumbo concreto ni prisa",
            "неспешно гулять ради удовольствия без определённой цели",
        ),
        required_concepts=(
            (
                "Moving around leisurely",
                (
                    "walking or moving around slowly and leisurely",
                    "marcher ou se promener tranquillement",
                    "caminar o pasear tranquilamente",
                    "неспешно ходить или прогуливаться",
                ),
            ),
            (
                "Without a fixed or urgent destination",
                (
                    "without a precise destination or any hurry",
                    "sans destination précise et sans se presser",
                    "sin destino concreto y sin prisa",
                    "без определённой цели и без спешки",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Hurrying directly somewhere",
                (
                    "hurrying directly to an urgent appointment",
                    "se dépêcher directement vers un rendez-vous urgent",
                    "ir deprisa y directamente a una cita urgente",
                    "спешить прямо на срочную встречу",
                ),
            ),
            (
                "Being involuntarily lost",
                (
                    "being lost and urgently trying to find the way",
                    "être perdu et chercher son chemin avec inquiétude",
                    "estar perdido e intentar encontrar el camino",
                    "заблудиться и пытаться найти дорогу",
                ),
            ),
            (
                "Walking briskly for exercise",
                (
                    "walking briskly as physical exercise",
                    "marcher d’un pas rapide pour faire de l’exercice",
                    "caminar rápido para hacer ejercicio",
                    "быстро ходить ради физической нагрузки",
                ),
            ),
        ),
        minimum_glosses=(
            *_glosses(
                (
                    "stroll",
                    "take a leisurely walk",
                    "se promener",
                    "marcher tranquillement",
                    "pasear",
                    "dar una vuelta",
                    "caminar tranquilamente",
                    "caminar sin apuro",
                    "andar sin rumbo",
                    "неспешно гулять",
                ),
                (
                    ("Moving around leisurely", "explicit"),
                    ("Without a fixed or urgent destination", "context"),
                ),
            ),
            *_glosses(
                (
                    "wander without a destination",
                    "stroll without hurry",
                    "se promener sans but",
                    "flâner sans se presser",
                    "pasear sin rumbo",
                    "pasear tranquilamente sin rumbo",
                    "pasear sin prisa ni destino",
                    "andar despacio sin un destino",
                    "caminar sin prisa y sin rumbo",
                    "vagar tranquilamente sin destino",
                    "бродить без цели",
                ),
                (
                    ("Moving around leisurely", "explicit"),
                    ("Without a fixed or urgent destination", "explicit"),
                ),
            ),
        ),
        context_concepts=("Without a fixed or urgent destination",),
    ),
    "depanner": PlaygroundChallenge(
        accepted_answers=(
            "to help someone out of a temporary practical difficulty",
            "he solved her immediate problem by giving her a ride",
            "il l’a aidée à sortir de son problème immédiat en la conduisant",
            "la ayudó a salir del apuro llevándola en coche",
            "он выручил её в трудной ситуации, подвезя до аэропорта",
        ),
        required_concepts=(
            (
                "Helping someone",
                (
                    "giving someone practical help",
                    "apporter une aide pratique à quelqu’un",
                    "dar ayuda práctica a alguien",
                    "оказать человеку практическую помощь",
                ),
            ),
            (
                "Solving an immediate practical difficulty",
                (
                    "getting the person out of an immediate temporary difficulty",
                    "tirer la personne d’un embarras immédiat et temporaire",
                    "sacar a la persona de un apuro inmediato y temporal",
                    "выручить человека из временного затруднения",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Only expressing sympathy",
                (
                    "expressing sympathy without offering practical help",
                    "exprimer de la sympathie sans apporter d’aide concrète",
                    "mostrar simpatía sin ofrecer ayuda práctica",
                    "посочувствовать, не предложив практической помощи",
                ),
            ),
            (
                "Making the difficulty worse",
                (
                    "making the person’s practical problem worse",
                    "aggraver le problème pratique de la personne",
                    "empeorar el problema práctico de la persona",
                    "усугубить практическую проблему человека",
                ),
            ),
            (
                "Repairing a broken machine",
                (
                    "repairing a broken machine rather than helping the traveler",
                    "réparer une machine en panne au lieu d’aider la voyageuse",
                    "reparar una máquina averiada en vez de ayudar a la viajera",
                    "ремонтировать сломанный механизм",
                ),
            ),
        ),
        minimum_glosses=_glosses(
            (
                "helped her out",
                "got her out of a bind",
                "gave practical help",
                "l’a aidée",
                "lui a rendu service",
                "l’a sortie d’affaire",
                "la sacó del apuro",
                "ayudarla a salir del apuro",
                "ayudarla con una dificultad urgente",
                "la ayudó con el problema",
                "la ayudó de forma práctica",
                "resolverle el problema urgente",
                "ayudarla a salir de un problema",
                "echarle una mano",
                "выручил её",
                "помог ей выйти из положения",
            ),
            (
                ("Helping someone", "explicit"),
                ("Solving an immediate practical difficulty", "context"),
            ),
        ),
        context_concepts=("Solving an immediate practical difficulty",),
    ),
    "s_attarder": PlaygroundChallenge(
        accepted_answers=(
            "to remain somewhere longer or later than expected",
            "to remain somewhere longer than expected before leaving",
            "she stayed there longer than expected",
            "elle est restée plus longtemps que prévu",
            "se quedó más tiempo de lo previsto",
            "se quedó más tiempo de lo previsto antes de irse",
            "она задержалась там дольше, чем собиралась",
        ),
        required_concepts=(
            (
                "Remaining in place",
                (
                    "remaining or staying in the same place",
                    "rester dans le même lieu",
                    "quedarse en el mismo lugar",
                    "остаться в том же месте",
                ),
            ),
            (
                "Longer or later than expected",
                (
                    "for longer or until later than expected",
                    "plus longtemps ou plus tard que prévu",
                    "durante más tiempo o hasta más tarde de lo previsto",
                    "дольше или позже, чем ожидалось",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Arriving late",
                (
                    "arriving late after everyone else",
                    "arriver en retard après tout le monde",
                    "llegar tarde después de los demás",
                    "опоздать и прийти позже всех",
                ),
            ),
            (
                "Leaving immediately",
                (
                    "leaving immediately without staying",
                    "partir immédiatement sans rester",
                    "irse inmediatamente sin quedarse",
                    "сразу уйти, не задерживаясь",
                ),
            ),
            (
                "Being prevented from leaving",
                (
                    "being forcibly prevented from leaving",
                    "être empêché de force de partir",
                    "ser obligado a quedarse contra la propia voluntad",
                    "быть насильно удержанным",
                ),
            ),
        ),
        minimum_glosses=(
            *_glosses(
                (
                    "lingered",
                    "stayed a little longer",
                    "est restée",
                    "a tardé à partir",
                    "se quedó un rato más",
                    "se quedó más rato",
                    "tardó en irse",
                    "se quedó más tiempo",
                    "задержалась",
                    "осталась подольше",
                ),
                (
                    ("Remaining in place", "explicit"),
                    ("Longer or later than expected", "context"),
                ),
            ),
            *_glosses(
                (
                    "stayed longer than expected",
                    "remained there late",
                    "est restée plus longtemps",
                    "quedarse ahí más de lo esperado",
                    "se quedó más de lo previsto",
                    "quedarse más de la cuenta",
                    "quedarse más tiempo antes de irse",
                    "задержалась дольше обычного",
                ),
                (
                    ("Remaining in place", "explicit"),
                    ("Longer or later than expected", "explicit"),
                ),
            ),
        ),
        context_concepts=("Longer or later than expected",),
    ),
    "madrugar": PlaygroundChallenge(
        accepted_answers=(
            "to get up at dawn or very early in the morning",
            "she got out of bed at dawn or very early in the morning",
            "se lever à l’aube ou très tôt le matin",
            "levantarse al amanecer o muy temprano",
            "se levantó al amanecer o muy temprano",
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
                "Remaining awake all night",
                (
                    "staying awake all night until dawn",
                    "rester éveillé toute la nuit jusqu’à l’aube",
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
        minimum_glosses=_glosses(
            (
                "get up very early",
                "get up early",
                "rise at dawn",
                "se lever très tôt",
                "se lever à l’aube",
                "levantarse muy temprano",
                "levantarse temprano",
                "levantarse al amanecer",
                "levantarse antes del amanecer",
                "salir de la cama muy temprano",
                "despertarse temprano",
                "despertarse al amanecer",
                "встать очень рано",
                "встать на рассвете",
            ),
            (
                ("Getting out of bed", "explicit"),
                ("At a very early hour", "explicit"),
            ),
        ),
    ),
    "estrenar": PlaygroundChallenge(
        accepted_answers=(
            "to use or wear something for the first time",
            "she wore the new coat for the first time",
            "porter ou utiliser quelque chose pour la première fois",
            "ponerse o usar algo por primera vez",
            "se puso el abrigo nuevo por primera vez",
            "впервые надеть или использовать новую вещь",
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
                "Buying without using",
                (
                    "buying something new without using it",
                    "acheter quelque chose de neuf sans l’utiliser",
                    "comprar algo nuevo sin usarlo",
                    "купить новую вещь, не используя её",
                ),
            ),
            (
                "Using it again",
                (
                    "using again something already used many times",
                    "réutiliser quelque chose qui a déjà beaucoup servi",
                    "volver a usar algo que ya se usó muchas veces",
                    "снова использовать вещь, которой уже пользовались",
                ),
            ),
            (
                "Repairing an old item",
                (
                    "repairing or restoring an old item",
                    "réparer ou restaurer un objet ancien",
                    "reparar o restaurar algo viejo",
                    "чинить или восстанавливать старую вещь",
                ),
            ),
        ),
        minimum_glosses=_glosses(
            (
                "use it for the first time",
                "wear it for the first time",
                "first use",
                "le porter pour la première fois",
                "l’utiliser pour la première fois",
                "usarlo por primera vez",
                "usar algo por primera vez",
                "usar por primera vez",
                "ponerse algo nuevo por primera vez",
                "ponérselo por primera vez",
                "ponerse algo por primera vez",
                "darle su primer uso",
                "vestirlo por primera vez",
                "надеть впервые",
                "использовать впервые",
            ),
            (
                ("Using or wearing something", "explicit"),
                ("For the first time", "explicit"),
            ),
        ),
    ),
    "empalagar": PlaygroundChallenge(
        accepted_answers=(
            "to become unpleasant or cloying because of excessive sweetness or richness",
            "its excessive sweetness caused weariness and made me dislike it",
            "son excès de sucre a fini par m’écœurer",
            "me causó desagrado o hartazgo por tener demasiado azúcar",
            "из-за чрезмерной сладости напиток стал приторным и неприятным",
        ),
        required_concepts=(
            (
                "Excessive sweetness or richness",
                (
                    "so sweet or rich that it becomes excessive",
                    "si sucré ou riche que cela devient excessif",
                    "tan dulce o intenso que resulta excesivo",
                    "настолько сладкий или насыщенный, что это чрезмерно",
                ),
            ),
            (
                "Resulting weariness, saturation, or dislike",
                (
                    "causing weariness, saturation, aversion, or loss of enjoyment",
                    "provoquer de la lassitude, de l’écœurement ou du dégoût",
                    "causar hastío, hartazgo, rechazo o desagrado",
                    "вызывать пресыщение, отвращение или потерю удовольствия",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Pleasant sweetness",
                (
                    "being pleasantly sweet and making someone want more",
                    "être agréablement sucré et donner envie d’en reprendre",
                    "ser agradablemente dulce y dar ganas de tomar más",
                    "быть приятно сладким и вызывать желание съесть ещё",
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
                "An allergic reaction",
                (
                    "having an allergic reaction to an ingredient",
                    "avoir une réaction allergique à un ingrédient",
                    "tener una reacción alérgica a un ingrediente",
                    "испытывать аллергическую реакцию на ингредиент",
                ),
            ),
        ),
        minimum_glosses=(
            *_glosses(
                (
                    "too sweet",
                    "overly rich",
                    "trop sucré",
                    "écœurant de sucre",
                    "demasiado dulce",
                    "excesivamente dulce",
                    "слишком сладкий",
                    "приторный",
                ),
                (
                    ("Excessive sweetness or richness", "explicit"),
                    (
                        "Resulting weariness, saturation, or dislike",
                        "optional_omitted",
                    ),
                ),
            ),
            *_glosses(
                (
                    "dislike from too much sugar",
                    "too sweet and cloying",
                    "cloyingly sweet",
                    "écœuré par trop de sucre",
                    "trop sucré au point de déplaire",
                    "desagrado luego de comer mucho azúcar",
                    "desagrado después de comer mucho azúcar",
                    "desagrado por exceso de azúcar",
                    "sentir desagrado por demasiado azúcar",
                    "mucho azúcar causa desagrado",
                    "mucho azúcar me causa desagrado",
                    "asco por demasiado azúcar",
                    "demasiado azúcar me dio asco",
                    "me dio asco de tan dulce",
                    "quedar harto de tanto dulce",
                    "hartarse de tanto azúcar",
                    "hartar por ser demasiado dulce",
                    "me hartó por ser demasiado dulce",
                    "me hartó el exceso de azúcar",
                    "cansarse por exceso de dulzor",
                    "hartazgo por demasiado azúcar",
                    "tan dulce que cansa",
                    "неприятно от избытка сахара",
                    "приторно до отвращения",
                ),
                (
                    ("Excessive sweetness or richness", "explicit"),
                    (
                        "Resulting weariness, saturation, or dislike",
                        "explicit",
                    ),
                ),
            ),
        ),
    ),
    "trasnochar": PlaygroundChallenge(
        accepted_answers=(
            "to stay awake until very late at night instead of sleeping",
            "she stayed awake working until very late at night",
            "rester éveillé à travailler jusque très tard dans la nuit",
            "quedarse despierto hasta muy entrada la noche",
            "se quedó despierta trabajando hasta muy entrada la noche",
            "не спать и работать до глубокой ночи",
        ),
        required_concepts=(
            (
                "Remaining awake",
                (
                    "remaining awake instead of sleeping",
                    "rester éveillé au lieu de dormir",
                    "permanecer despierto en vez de dormir",
                    "оставаться бодрствующим вместо сна",
                ),
            ),
            (
                "Until very late at night",
                (
                    "until very late or deep into the night",
                    "jusque très tard ou au cœur de la nuit",
                    "hasta muy tarde o muy entrada la noche",
                    "до очень позднего времени или глубокой ночи",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Getting up early after sleeping",
                (
                    "sleeping first and then getting up very early",
                    "dormir puis se lever très tôt",
                    "dormir y después levantarse muy temprano",
                    "поспать, а затем встать очень рано",
                ),
            ),
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
                "Sleeping through the night",
                (
                    "sleeping peacefully through the whole night",
                    "dormir paisiblement toute la nuit",
                    "dormir tranquilamente toda la noche",
                    "спокойно проспать всю ночь",
                ),
            ),
        ),
        minimum_glosses=_glosses(
            (
                "stay up very late",
                "be awake deep into the night",
                "stay awake most of the night",
                "veiller très tard",
                "rester éveillé jusque tard",
                "quedarse despierto hasta muy tarde",
                "estar despierto hasta tarde",
                "pasar la noche sin dormir",
                "no dormir hasta muy tarde",
                "no dormir hasta las cuatro de la mañana",
                "seguir sin dormir hasta las cuatro",
                "acostarse muy tarde",
                "permanecer despierto hasta las cinco",
                "не спать допоздна",
                "бодрствовать глубокой ночью",
            ),
            (
                ("Remaining awake", "explicit"),
                ("Until very late at night", "explicit"),
            ),
        ),
    ),
    "anorar": PlaygroundChallenge(
        accepted_answers=(
            "to miss or long for someone or something valued that is absent",
            "she emotionally longs for valued family experiences that are now absent",
            "regretter avec nostalgie quelqu’un ou quelque chose qui manque",
            "echar de menos con nostalgia a alguien o algo ausente",
            (
                "echa de menos y desea volver a vivir las comidas "
                "familiares de los domingos"
            ),
            "тосковать по дорогому человеку или опыту, которого больше нет рядом",
        ),
        required_concepts=(
            (
                "Something valued is absent",
                (
                    "a valued person, place, or experience is absent or lost",
                    "une personne, un lieu ou une expérience chère est absente",
                    "una persona, lugar o experiencia querida está ausente",
                    "дорогого человека, места или опыта сейчас нет рядом",
                ),
            ),
            (
                "Feeling emotional longing",
                (
                    "feeling sadness, nostalgia, or longing for it",
                    "ressentir du manque, de la nostalgie ou du regret",
                    "sentir añoranza, nostalgia o tristeza por ello",
                    "чувствовать тоску или ностальгию по этому",
                ),
            ),
        ),
        hard_negatives=(
            (
                "Remembering neutrally",
                (
                    "remembering something neutrally without missing it",
                    "se souvenir de quelque chose sans ressentir de manque",
                    "recordar algo de manera neutral sin echarlo de menos",
                    "нейтрально вспоминать, не испытывая тоски",
                ),
            ),
            (
                "Forgetting or feeling no attachment",
                (
                    "forgetting it or feeling no emotional attachment",
                    "oublier ou ne ressentir aucun attachement",
                    "olvidarlo o no sentir ningún apego",
                    "забыть или не чувствовать привязанности",
                ),
            ),
            (
                "Anticipating something never experienced",
                (
                    "looking forward to a new experience that has never happened",
                    "attendre avec impatience une expérience jamais vécue",
                    "tener ganas de algo nuevo que nunca se ha vivido",
                    "ждать нового события, которого ещё никогда не было",
                ),
            ),
        ),
        minimum_glosses=_glosses(
            (
                "misses them",
                "longs for them",
                "misses home",
                "ça lui manque",
                "éprouve de la nostalgie",
                "regrette leur absence",
                "las echa de menos",
                "los echa de menos",
                "echar de menos",
                "siente nostalgia",
                "sentir nostalgia por la familia que está lejos",
                "extrañar",
                "extrañar mucho a su familia",
                "echar de menos a los amigos lejanos",
                "extraña esos momentos",
                "скучает по ним",
                "тоскует по ним",
            ),
            (
                ("Something valued is absent", "context"),
                ("Feeling emotional longing", "explicit"),
            ),
        ),
        context_concepts=("Something valued is absent",),
    ),
}


def get_playground_challenge(challenge_id: str) -> PlaygroundChallenge:
    try:
        return PLAYGROUND_CHALLENGES[challenge_id]
    except KeyError as exc:
        raise ValueError("Unknown semantic playground challenge.") from exc
