from typing import Dict, List, Literal, Tuple
from django.db import transaction
from django.db.models import F, Max, Avg
from django.contrib.auth.models import AbstractBaseUser
from .models import Verb, UserVerb
import random
from unidecode import unidecode

Direction = Literal['fr_es', 'es_fr']


def init_user_verbs(user, n=10):
    with transaction.atomic():
        base = list(Verb.objects.order_by('id')[:n])
        UserVerb.objects.bulk_create(
            [UserVerb(user=user, verb=v, unlocked=True) for v in base],
            ignore_conflicts=True,
        )


def preselect_verbs(user, length: int) -> List[int]:
    qs = UserVerb.objects.filter(user=user, unlocked=True).select_related('verb').values_list('verb_id', 'probability')
    rows = list(qs)
    if not rows:
        return []
    # weighted sample without replacement (simple proportional removal)
    pool = [(vid, float(p)) for vid, p in rows]
    total = sum(p for _, p in pool) or 1.0
    pool = [(vid, p / total) for vid, p in pool]
    chosen: List[int] = []
    length = min(length, len(pool))
    for _ in range(length):
        r = random.random()
        acc = 0.0
        for i, (vid, w) in enumerate(pool):
            acc += w
            if r <= acc:
                chosen.append(vid)
                del pool[i]
                s = sum(w2 for _, w2 in pool) or 1.0
                pool = [(v2, w2 / s) for v2, w2 in pool]
                break
    return chosen


def add_new_verbs(user, n=3):
    with transaction.atomic():
        max_id = UserVerb.objects.filter(user=user).aggregate(max_id=Max('verb_id'))['max_id'] or 0
        new_verbs = list(Verb.objects.filter(id__gt=max_id).order_by('id')[:n])
        if not new_verbs:
            return 0
        UserVerb.objects.bulk_create(
            [UserVerb(user=user, verb=v, unlocked=True) for v in new_verbs],
            ignore_conflicts=True,
        )
        return len(new_verbs)


class TrainingEngine:
    def __init__(self, user: AbstractBaseUser, direction: Direction):
        self.user = user
        self.direction = direction  # 'fr_es' or 'es_fr'

    def format_prompt_answer(self, verb: Verb) -> Tuple[str, str]:
        if self.direction == 'fr_es':
            return verb.infinitive, verb.translation or ''
        else:
            return verb.translation or '', verb.infinitive

    def normalize(self, text: str) -> str:
        return unidecode((text or '').strip().lower())

    def is_correct(self, correct_field: str, answer: str) -> bool:
        options = [self.normalize(p) for p in (correct_field or '').split(',') if p.strip()]
        return self.normalize(answer) in options

    def hint(self, target: str, level: int) -> str:
        target = target or ''
        level = max(0, min(level, len(target)))
        target = target.strip().split(',')[0]
        return target[:level]

    def update_on_result(self, verb_id: int, correct: bool):
        # Simple probability adjustment
        if correct:
            UserVerb.objects.filter(user=self.user, verb_id=verb_id).update(
                probability=F('probability') * 0.7,
                times_correct=F('times_correct') + 1,
            )
            # floor
            uv = UserVerb.objects.get(user=self.user, verb_id=verb_id)
            if uv.probability < 20:
                uv.probability = 20
                uv.save(update_fields=['probability'])
        else:
            UserVerb.objects.filter(user=self.user, verb_id=verb_id).update(
                probability=F('probability') * 1.3,
                times_correct=F('times_correct') + 1,
            )

    def test_if_new_verbs(self, points_next_level: float, new_verbs_next_level: int):
        top_verbs = UserVerb.objects.filter(user=self.user).order_by('-probability')[:5]
        if not top_verbs:
            avg_prob = None
        else:
            avg_prob = sum(v.probability for v in top_verbs) / len(top_verbs)
        print(avg_prob)
        if avg_prob is None:
            return
        if avg_prob > points_next_level:
            return
        add_new_verbs(self.user, new_verbs_next_level)