from typing import List, Literal, Tuple
from django.db import transaction
from django.db.models import F
from django.contrib.auth.models import AbstractBaseUser
from .models import Word, UserWord
import random
from unidecode import unidecode

Direction = Literal['fr_es', 'es_fr']


def preselect_words(user, length: int) -> List[int]:
    qs = (
        UserWord.objects
        .filter(user=user, unlocked=True)
        .select_related('word')
        .values_list('word_id', 'probability')
    )
    rows = list(qs)
    if not rows:
        return []
    pool = [(wid, float(p)) for wid, p in rows]
    total = sum(p for _, p in pool) or 1.0
    pool = [(wid, p / total) for wid, p in pool]
    chosen: List[int] = []
    length = min(length, len(pool))
    for _ in range(length):
        r = random.random()
        acc = 0.0
        for i, (wid, w) in enumerate(pool):
            acc += w
            if r <= acc:
                chosen.append(wid)
                del pool[i]
                s = sum(w2 for _, w2 in pool) or 1.0
                pool = [(w2_id, w2 / s) for w2_id, w2 in pool]
                break
    return chosen


class TrainingEngine:
    def __init__(self, user: AbstractBaseUser, direction: Direction):
        self.user = user
        self.direction = direction

    def format_prompt_answer(self, word: Word) -> Tuple[str, str]:
        if self.direction == 'fr_es':
            return word.word, word.translation or ''
        else:
            return word.translation or '', word.word

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

    def update_on_result(self, word_id: int, correct: bool):
        if correct:
            UserWord.objects.filter(user=self.user, word_id=word_id).update(
                probability=F('probability') * 0.7,
                times_correct=F('times_correct') + 1,
            )
            # floor
            uw = UserWord.objects.get(user=self.user, word_id=word_id)
            if uw.probability < 1:
                uw.probability = 1
                uw.save(update_fields=['probability'])
        else:
            UserWord.objects.filter(user=self.user, word_id=word_id).update(
                probability=F('probability') * 1.3,
                times_correct=F('times_correct') + 1,
            )
