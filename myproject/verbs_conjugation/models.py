from django.db import models
from verbs.models import Verb

class VerbConjugation(models.Model):
    """
    Stores individual conjugated forms for verbs.
    Each row represents one conjugated form (e.g., "je suis", "tu es", etc.)
    """
    LANGUAGE_CHOICES = [
        ('FR', 'French'),
        ('ES', 'Spanish'),
    ]
    
    verb = models.ForeignKey(Verb, on_delete=models.CASCADE, related_name='conjugations')
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    mood = models.CharField(max_length=50)  # Indicatif, Subjonctif, Imperativo, etc.
    tense = models.CharField(max_length=50)  # Présent, Imparfait, Futuro, etc.
    pronoun = models.CharField(max_length=20, blank=True)  # je, tu, él, etc. (can be empty for infinitives)
    conjugated_form = models.CharField(max_length=100)  # The actual conjugated form
    
    # For optimization
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['verb', 'language']),
            models.Index(fields=['verb', 'language', 'mood']),
            models.Index(fields=['verb', 'language', 'mood', 'tense']),
            models.Index(fields=['language', 'mood', 'tense']),
        ]
        unique_together = ('verb', 'language', 'mood', 'tense', 'pronoun')
        
    def __str__(self):
        pronoun_part = f"{self.pronoun} " if self.pronoun else ""
        return f"{self.verb.infinitive} ({self.language}) - {self.mood}/{self.tense}: {pronoun_part}{self.conjugated_form}"

class ConjugationSession(models.Model):
    """
    Stores user training sessions for verb conjugations.
    Links to the training session functionality.
    """
    LANGUAGE_CHOICES = [
        ('FR', 'French'),
        ('ES', 'Spanish'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'), 
        ('hard', 'Hard'),
        ('custom', 'Custom'),
    ]
    
    FILL_LEVEL_CHOICES = [
        ('easy', 'Easy (80% filled)'),
        ('medium', 'Medium (20% filled)'),
        ('hard', 'Hard (0% filled)'),
    ]
    
    # Session configuration
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    difficulty_level = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    fill_level = models.CharField(max_length=10, choices=FILL_LEVEL_CHOICES)
    selected_tenses = models.JSONField()  # List of selected tense names
    
    # Session tracking
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['language', 'difficulty_level']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
        ]
        
    def __str__(self):
        status = "Active" if self.is_active else "Completed"
        return f"{self.get_language_display()} {self.get_difficulty_level_display()} Session - {status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
