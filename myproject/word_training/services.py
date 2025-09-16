from typing import List, Literal, Tuple
from django.db import transaction
from django.db.models import F, Max, Avg, Max
from django.contrib.auth.models import AbstractBaseUser
from .models import Word, UserWord
import random
from unidecode import unidecode

Direction = Literal['fr_es', 'es_fr']

def init_user_words(user, n=10):
    with transaction.atomic():
        base = list(Word.objects.order_by('id')[:n])
        UserWord.objects.bulk_create(
            [UserWord(user=user, word=v, unlocked=True) for v in base],
            ignore_conflicts=True,
        )

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

    def format_prompt_answer(self, word: Word) -> Tuple[str, str, str]:
        if self.direction == 'fr_es':
            return word.word, word.translation or '', word.translation_sy or ''
        else:
            return word.translation or '', word.word, word.word_sy or ''

    def normalize(self, text: str) -> str:
        return unidecode((text or '').strip().lower())

    def is_correct(self, correct_field: str, correct_synonyms_field: str, answer: str) -> float:
        options = [self.normalize(p) for p in (correct_field or '').split(',') if p.strip()]
        if self.normalize(answer) in options:
            return 0.7
        
        synonyms = [self.normalize(p) for p in (correct_synonyms_field or '').split(',') if p.strip()]
        if self.normalize(answer) in synonyms:
            return 0.8
        
        return 1.3

    def hint(self, target: str, level: int) -> str:
        target = target or ''
        level = max(0, min(level, len(target)))
        target = target.strip().split(',')[0]
        return target[:level]

    def update_on_result(self, word_id: int, multiplier: float):
        if multiplier < 1:
            UserWord.objects.filter(user=self.user, word_id=word_id).update(
                probability=F('probability') * multiplier,
                times_correct=F('times_correct') + 1,
            )
            # floor
            uw = UserWord.objects.get(user=self.user, word_id=word_id)
            if uw.probability < 20:
                uw.probability = 20
                uw.save(update_fields=['probability'])
        else:
            UserWord.objects.filter(user=self.user, word_id=word_id).update(
                probability=F('probability') * multiplier,
            )

    def test_if_new_words(self, points_next_level: float, new_words_next_level: int):
        top_words = UserWord.objects.filter(user=self.user).order_by('-probability')[:5]
        if not top_words:
            avg_prob = None
        else:
            avg_prob = sum(v.probability for v in top_words) / len(top_words)
        
        if avg_prob is None:
            return
        if avg_prob > points_next_level:
            return
        add_new_words(self.user, new_words_next_level)

def add_new_words(user, n=3):
    with transaction.atomic():
        max_id = UserWord.objects.filter(user=user).aggregate(max_id=Max('word_id'))['max_id'] or 0
        new_words = list(Word.objects.filter(id__gt=max_id).order_by('id')[:n])
        if not new_words:
            return 0
        UserWord.objects.bulk_create(
            [UserWord(user=user, word=v, unlocked=True) for v in new_words],
            ignore_conflicts=True,
        )
        return len(new_words)
