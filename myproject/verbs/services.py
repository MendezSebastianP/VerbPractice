from typing import Dict, List, Literal, Tuple
from django.db import transaction
from django.db.models import F, Max, Avg
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone
from .models import Verb, UserVerb, UserConjugation
from verbs_conjugation.models import VerbConjugation
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


# Conjugation System Functions

def init_user_conjugations(user, language='FR', n=10):
    """Initialize first 10 verbs with all available tenses at score 1000"""
    with transaction.atomic():
        base_verbs = list(Verb.objects.order_by('id')[:n])
        
        for verb in base_verbs:
            # Get all available tenses for this verb in specified language
            available_tenses = VerbConjugation.objects.filter(
                verb=verb, language=language
            ).values_list('tense', flat=True).distinct()
            
            # Initialize tense_scores with all tenses at 1000
            initial_tense_scores = {tense: 1000 for tense in available_tenses}
            
            UserConjugation.objects.get_or_create(
                user=user, verb=verb, language=language,
                defaults={
                    'overall_score': 1000,
                    'tense_scores': initial_tense_scores,
                    'unlocked': True
                }
            )


def should_unlock_new_conjugation_verbs(user, language):
    """
    Determine if user should unlock new verbs based on performance
    Logic: Get worst 5 verbs by overall_score, if average < 700, unlock new verbs
    """
    # Only consider verbs that have been practiced
    practiced_verbs = UserConjugation.objects.filter(
        user=user, 
        language=language,
        total_attempts__gt=0  # Has been practiced
    ).order_by('-overall_score')  # Worst first
    
    if practiced_verbs.count() < 5:
        return False  # Need at least 5 practiced verbs
    
    worst_5_verbs = practiced_verbs[:5]
    avg_worst_score = sum(v.overall_score for v in worst_5_verbs) / 5
    
    return avg_worst_score < 700  # Unlock when performing well


def add_new_conjugation_verbs(user, language, n=3):
    """Add new verbs with all tenses initialized at 1000"""
    with transaction.atomic():
        # Find highest verb ID already unlocked by user
        max_id = UserConjugation.objects.filter(
            user=user, language=language
        ).aggregate(max_id=Max('verb_id'))['max_id'] or 0
        
        # Get next N verbs
        new_verbs = list(Verb.objects.filter(id__gt=max_id).order_by('id')[:n])
        if not new_verbs:
            return 0
        
        # Initialize with all available tenses at score 1000
        for verb in new_verbs:
            available_tenses = VerbConjugation.objects.filter(
                verb=verb, language=language
            ).values_list('tense', flat=True).distinct()
            
            UserConjugation.objects.create(
                user=user, verb=verb, language=language,
                overall_score=1000,
                tense_scores={tense: 1000 for tense in available_tenses},
                unlocked=True
            )
        
        return len(new_verbs)


def preselect_conjugation_verbs(user, language, selected_tenses, length=10):
    """
    Select verbs for practice based on aggregated tense difficulties
    """
    # Get all unlocked verbs for user
    user_conjugations = UserConjugation.objects.filter(
        user=user, language=language, unlocked=True
    ).select_related('verb')
    
    if not user_conjugations:
        return []
    
    # Calculate aggregated difficulty for selected tenses
    verb_weights = []
    for user_conj in user_conjugations:
        # Get scores for selected tenses (default 1000 for unpracticed)
        selected_scores = [
            user_conj.tense_scores.get(tense, 1000) 
            for tense in selected_tenses
        ]
        # Average difficulty across selected tenses
        avg_difficulty = sum(selected_scores) / len(selected_scores)
        verb_weights.append((user_conj.verb.id, float(avg_difficulty)))
    
    # Apply weighted random selection (same algorithm as existing preselect_verbs)
    pool = verb_weights[:]
    total = sum(weight for _, weight in pool) or 1.0
    pool = [(vid, weight / total) for vid, weight in pool]
    
    chosen = []
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


class ConjugationEngine:
    def __init__(self, user: AbstractBaseUser, language: str):
        self.user = user
        self.language = language  # 'FR' or 'ES'
    
    def calculate_tense_multiplier(self, pronoun_results: Dict[str, bool]) -> float:
        """
        Calculate multiplier based on pronoun-level results
        Args: pronoun_results: {'je': True, 'tu': False, 'il': True, ...}
        Returns: Average multiplier (0.7 for correct, 1.5 for incorrect)
        """
        multipliers = []
        for pronoun, is_correct in pronoun_results.items():
            multipliers.append(0.7 if is_correct else 1.5)
        
        return sum(multipliers) / len(multipliers)
    
    def update_tense_score(self, verb_id: int, tense: str, pronoun_results: Dict[str, bool]):
        """Update tense score and recalculate overall score"""
        user_conj, created = UserConjugation.objects.get_or_create(
            user=self.user, verb_id=verb_id, language=self.language,
            defaults={
                'overall_score': 1000,
                'tense_scores': {},
                'unlocked': True
            }
        )
        
        # 1. Calculate multiplier from pronoun results
        multiplier = self.calculate_tense_multiplier(pronoun_results)
        
        # 2. Apply to current tense score
        current_score = user_conj.get_tense_score(tense)
        new_score = current_score * multiplier
        
        # 3. Apply bounds (20 minimum, 100000 maximum)
        new_score = max(20, min(100000, new_score))
        user_conj.tense_scores[tense] = new_score
        
        # 4. Recalculate overall score (average of practiced tenses)
        if user_conj.tense_scores:
            user_conj.overall_score = sum(user_conj.tense_scores.values()) / len(user_conj.tense_scores)
        
        # 5. Update statistics
        correct_count = sum(1 for correct in pronoun_results.values() if correct)
        user_conj.total_attempts += len(pronoun_results)
        user_conj.total_correct += correct_count
        user_conj.last_practiced = timezone.now()
        
        user_conj.save()
        return new_score
    
    def start_session(self, selected_tenses: List[str], session_length: int = 10):
        """Start a new training session"""
        # 1. Check if new verbs should be unlocked (start of session)
        if should_unlock_new_conjugation_verbs(self.user, self.language):
            add_new_conjugation_verbs(self.user, self.language, 3)
        
        # 2. Select verbs based on tense difficulties
        selected_verb_ids = preselect_conjugation_verbs(
            self.user, self.language, selected_tenses, session_length
        )
        
        # 3. Generate practice questions
        return self.generate_questions(selected_verb_ids, selected_tenses)
    
    def end_session(self):
        """End session - check for new verb unlocks again"""
        if should_unlock_new_conjugation_verbs(self.user, self.language):
            add_new_conjugation_verbs(self.user, self.language, 3)
    
    def generate_questions(self, verb_ids: List[int], selected_tenses: List[str]):
        """Generate conjugation questions for selected verbs and tenses"""
        questions = []
        
        for verb_id in verb_ids:
            # Randomly select one tense from user's selected tenses
            tense = random.choice(selected_tenses)
            
            # Get all conjugations for this verb/tense
            conjugations = VerbConjugation.objects.filter(
                verb_id=verb_id,
                language=self.language,
                tense=tense
            ).values_list('pronoun', 'conjugated_form')
            
            if conjugations:
                questions.append({
                    'verb_id': verb_id,
                    'tense': tense,
                    'pronouns': dict(conjugations)  # {'je': 'suis', 'tu': 'es', ...}
                })
        
        return questions