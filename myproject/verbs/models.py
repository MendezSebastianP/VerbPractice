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

class UserConjugation(models.Model):
    """
    Tracks user's conjugation performance per verb and language.
    Uses JSON field to store granular tense-level scores for precise targeting.
    """
    LANGUAGE_CHOICES = [
        ('FR', 'French'),
        ('ES', 'Spanish'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    verb = models.ForeignKey(Verb, on_delete=models.CASCADE)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    
    # Overall verb stats for quick overview
    overall_score = models.FloatField(default=1000)  # Average of all tense scores
    unlocked = models.BooleanField(default=False)
    
    # Granular tense-level difficulty tracking
    # Example: {"Présent": 800, "Imparfait": 1200, "Subjonctif présent": 1500}
    tense_scores = models.JSONField(default=dict)
    
    # Summary statistics
    total_attempts = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)
    last_practiced = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'verb', 'language')
        indexes = [
            models.Index(fields=['user', 'language', 'unlocked']),
            models.Index(fields=['user', 'language', 'overall_score']),
            models.Index(fields=['user', 'verb', 'language']),
            models.Index(fields=['last_practiced']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.verb.infinitive} ({self.get_language_display()})"
    
    @property
    def accuracy_percentage(self):
        """Calculate overall accuracy percentage."""
        if self.total_attempts == 0:
            return 0
        return round((self.total_correct / self.total_attempts) * 100, 1)
    
    def get_tense_score(self, tense_name):
        """Get score for a specific tense, defaulting to 1000 if not practiced yet."""
        return self.tense_scores.get(tense_name, 1000)