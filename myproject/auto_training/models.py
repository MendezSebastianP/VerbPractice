from django.conf import settings
from django.db import models


class Word(models.Model):
    word = models.CharField(max_length=128, unique=True)
    translation = models.CharField(max_length=128)

    def __str__(self):
        return self.word


class UserWord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    unlocked = models.BooleanField(default=False)
    probability = models.FloatField(default=1000)
    times_correct = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'word')
        indexes = [
            models.Index(fields=['user', 'unlocked']),
            models.Index(fields=['user', 'word']),
        ]

