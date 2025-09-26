from django.contrib import admin
from .models import VerbConjugation, ConjugationSession

@admin.register(VerbConjugation)
class VerbConjugationAdmin(admin.ModelAdmin):
    list_display = ('verb', 'language', 'mood', 'tense', 'pronoun', 'conjugated_form')
    list_filter = ('language', 'mood', 'tense')
    search_fields = ('verb__infinitive', 'conjugated_form', 'mood', 'tense')
    ordering = ('verb__infinitive', 'language', 'mood', 'tense', 'pronoun')
    
    # Read-only fields - conjugations should not be edited manually
    readonly_fields = ('created_at', 'updated_at')
    
    # Improve performance with select_related
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('verb')

@admin.register(ConjugationSession)
class ConjugationSessionAdmin(admin.ModelAdmin):
    list_display = ('language', 'difficulty_level', 'fill_level', 'is_active', 'created_at', 'completed_at')
    list_filter = ('language', 'difficulty_level', 'fill_level', 'is_active', 'created_at')
    search_fields = ('language', 'difficulty_level')
    ordering = ('-created_at',)
    
    readonly_fields = ('created_at',)
    
    # Show selected tenses in a nice format
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ('selected_tenses',)
        return self.readonly_fields
