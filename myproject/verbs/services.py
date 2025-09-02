from django.db import transaction
from .models import Verb, UserVerb
import random

def init_user_verbs(user, n=10):
    with transaction.atomic():
        base = list(Verb.objects.order_by('id')[:n])
        UserVerb.objects.bulk_create(
            [UserVerb(user=user, verb=v, unlocked=True, probability=1.0) for v in base],
            ignore_conflicts=True,
        )

class verb_session():
	def __init__(self, nverbs):
		self.nverbs = nverbs
	def score_to_prob(self, scores):
		total_score = sum(item['score'] for item in scores.values())
		return {key: value['score'] / total_score for key, value in scores.items()}
	def pick_next_verb(self):
		pass