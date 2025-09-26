from django.contrib import admin
from .models import Verb, UserVerb, UserConjugation

@admin.register(Verb)
class VerbAdmin(admin.ModelAdmin):
    list_display = ('infinitive', 'translation')
    search_fields = ('infinitive', 'translation')
    ordering = ('infinitive',)

@admin.register(UserVerb)
class UserVerbAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'unlocked', 'probability', 'times_correct')
    list_filter = ('unlocked',)
    search_fields = ('user__username', 'verb__infinitive')
    ordering = ('user', 'verb')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'verb')

@admin.register(UserConjugation)
class UserConjugationAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'language', 'unlocked', 'overall_score', 'accuracy_percentage', 'last_practiced')
    list_filter = ('language', 'unlocked', 'last_practiced')
    search_fields = ('user__username', 'verb__infinitive')
    ordering = ('user', 'verb', 'language')
    
    readonly_fields = ('created_at', 'updated_at', 'accuracy_percentage')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'verb', 'language', 'unlocked')
        }),
        ('Scoring', {
            'fields': ('overall_score', 'tense_scores'),
            'description': 'Tense scores are stored as JSON: {"Présent": 800, "Imparfait": 1200, ...}'
        }),
        ('Statistics', {
            'fields': ('total_attempts', 'total_correct', 'accuracy_percentage', 'last_practiced')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'verb')
    
    def accuracy_percentage(self, obj):
        return f"{obj.accuracy_percentage}%"
    accuracy_percentage.short_description = 'Accuracy'
