from django.db import transaction
from django.db.models import F, Value
from .models import Verb, UserVerb
import random
import math
import numpy as np
from unidecode import unidecode


def init_user_verbs(user, n=10):
	with transaction.atomic():
		base = list(Verb.objects.order_by('id')[:n])
		UserVerb.objects.bulk_create(
			[UserVerb(user=user, verb=v, unlocked=True) for v in base],
			ignore_conflicts=True,
		)

class verb_session():
	def __init__(self, nverbs, user):
		N_VERBS = 1000
		self.nverbs = nverbs
		self.user = user
		self.first_answer = True

	def score_to_prob(self, scores):
		"""
		Converts a dictionary of scores into probabilities by normalizing the values.

		Args:
			scores (dict): Dictionary with keys as IDs and values as scores.

		Returns:
			dict: Dictionary with keys as IDs and values as probabilities.
		"""
		prob = {}
		sum_scores = sum(scores.values())
		for key, value in scores.items():
			prob[key] = value / sum_scores
		return (prob)
	
	def next_verb(self, scores):
		"""
		Chooses the next verb based on probability derived from scores.

		Args:
			scores (Dict): A dictionary of scores.

		Returns:
			int: The selected verb key.
		"""
		prob = self.score_to_prob(scores)
		verb_choose = np.random.choice(list(prob.keys()), p=list(prob.values()))
		return (verb_choose)
	
	def verbs_session(self, scores, n):
		"""
		Selects a set number of verbs for a training session.

		Args:
			scores (Dict): A dictionary of scores.
			n (int): Number of verbs to select.

		Returns:
			list: A list of selected verb keys.
		"""
		temp_scores = scores.copy()
		selected_verbs = []
		for i in range(n):
			verb_choose = self.next_verb(temp_scores)
			selected_verbs.append(verb_choose)
			del temp_scores[verb_choose]
		return (selected_verbs)
	
	def wr_answer(self, scores, index):
		mult = 1.2 + ((self.N_VERBS - index + 1) / (self.N_VERBS - 1))
		scores[index]['score'] *= mult
		if not self.first_answer:
			return
		if (scores[index]['score'] > 10**5):
			scores[index]['score'] = 10**5
		UserVerb.objects.filter(user=self.user, verb_id=index).update(
			probability=scores[index]['score'],
			times_correct= F('times_correct') + 1,
		)
		self.first_answer = False

	def right_answer(self, scores, index):
		scores[index]['score'] = scores[index]['score'] * (0.7)
		if (scores[index]['score'] < 1):
			scores[index]['score'] = 1
		UserVerb.objects.filter(user=self.user, verb_id=index).update(
			probability=scores[index]['score'],
			times_correct= F('times_correct') + 1,
		)

	def hint_answer(self, scores, index, n_hint, len_verb):
		base_right_answer = (0.7)
		base_right_answer = 1 - base_right_answer
		if not self.first_answer:
			return
		if (n_hint >= len_verb/2):
			self.wr_answer(scores, index)
			return
		elif (n_hint > 3 & n_hint < len_verb/2):
			base_right_answer = 1
		else:
			base_right_answer = base_right_answer * (1 - (n_hint * (1/4)))
			base_right_answer = 1 - base_right_answer
		scores[index]['score'] = scores[index]['score'] * base_right_answer
		if (scores[index]['score'] < 1):
			scores[index]['score'] = 1
		UserVerb.objects.filter(user=self.user, verb_id=index).update(
			probability=scores[index]['score'],
			times_correct= F('times_correct') + 1,
		)

	def hint(verb, times):
		if (times <= len(verb)):
				hinted = verb[0:times]
				return (hinted)
		else:
				return -1
	

	def next_scores(self, scores, index, response, verb = None, n_hint = None):
		if (response == 1):
			self.right_answer(scores, index)
		elif (response == 2):
			if (verb is None or n_hint is None):
				print("Error (next_scores): response with hint need the verb and the number of hints")
				return
			self.hint_answer(scores, index, n_hint, len(verb))
		elif (response == 0):
			self.wr_answer(scores, index)
		else:
			print("Error (next_scores): not valid input")

	def test_verb(self, scores, index, verb: str, response: str, n_hint = 0): # toleramos una letra o acento? minusculas mayusculas?
		response = (unidecode(verb.lower()) == unidecode(response.lower())) #toleramos acentos y mayusculas
		if (n_hint > 0):
				response += 1
				self.next_scores(scores, index, response, verb, n_hint)
		else:
				self.next_scores(scores, index, response)