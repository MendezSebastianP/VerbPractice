from django.conf import settings
from django.db import models

class Verb(models.Model):
    infinitive = models.CharField(max_length=64, unique=True)
    translation = models.CharField(max_length=128)

    def __str__(self):
        return self.infinitive

class UserVerb(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    verb = models.ForeignKey(Verb, on_delete=models.CASCADE)
    unlocked = models.BooleanField(default=False)
    probability = models.FloatField(default=1000)
    times_correct = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'verb')
        indexes = [
            models.Index(fields=['user', 'unlocked']),
            models.Index(fields=['user', 'verb']),
        ]