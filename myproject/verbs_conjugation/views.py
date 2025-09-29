from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from verbs.services import ConjugationEngine, init_user_conjugations, preselect_conjugation_verbs, should_unlock_new_conjugation_verbs, add_new_conjugation_verbs
from verbs.models import UserConjugation
from .models import VerbConjugation
import csv
import os
from django.conf import settings
import json

def session_menu(request):
    """Display the verb conjugation session setup menu"""
    context = {
        'title': 'Verb Conjugations',
        'page_title': 'Verb Conjugation Training'
    }
    return render(request, 'verbs_conjugation/session_menu.html', context)

def get_available_tenses(request):
    """AJAX endpoint to get available tenses for selected language, sorted by difficulty/frequency"""
    language = request.GET.get('language', 'fr')
    
    # Define tenses ordered from most used/easy to hardest/least used
    french_tenses = {
        # Easy level tenses - most commonly used by native speakers
        'easy': [
            'Présent',           # Most used - I am, you are, etc.
            'Futur',             # Simple future - I will be  
            'Passé composé',     # Perfect past - I have been
        ],
        # Medium level adds these - moderately common
        'medium': [
            'Imparfait',         # Imperfect past - I was being
            'Conditionnel présent',  # Would + verb
            'Impératif présent', # Commands - Be! Do!
            'Futur antérieur',   # Future perfect - I will have been
        ],
        # Hard level adds these - advanced but still used
        'hard': [
            'Subjonctif présent',    # Subjunctive - doubt, emotion
            'Passé simple',          # Literary past - formal writing only  
            'Plus-que-parfait',      # Pluperfect - I had been
        ],
        # Extremely advanced - beyond hard, rarely used even by natives
        'extreme': [
            'Conditionnel passé',    # Would have + past participle
            'Subjonctif imparfait',  # Imperfect subjunctive - very formal
            'Subjonctif plus-que-parfait',  # Past perfect subjunctive - extremely rare
            'Subjonctif passé'       # Past subjunctive - literary
        ]
    }

    spanish_tenses = {
        # Easy level tenses - most commonly used by native speakers  
        'easy': [
            'Presente',          # Most used - I am, you are, etc.
            'Futuro',            # Simple future - I will be
            'Pretérito perfecto compuesto',  # Perfect past - I have been
        ],
        # Medium level adds these - moderately common
        'medium': [
            'Pretérito imperfecto',  # Imperfect past - I was being
            'Condicional',           # Would + verb
            'Imperativo',        # Commands - Be! Do!
            'Futuro perfecto',   # Future perfect - I will have been
        ],
        # Hard level adds these - advanced but still used
        'hard': [
            'Subjuntivo presente',    # Subjunctive - doubt, emotion
            'Pretérito indefinido',      # Preterite - completed past actions
            'Pretérito pluscuamperfecto',  # Pluperfect - I had been (equivalent to plus-que-parfait)
        ],
        # Extremely advanced - beyond hard, rarely used even by natives
        'extreme': [
            'Condicional compuesto',     # Would have + past participle
            'Subjuntivo imperfecto',  # Imperfect subjunctive - formal
            'Subjuntivo pluscuamperfecto',  # Past perfect subjunctive - extremely rare
            'Subjuntivo perfecto'    # Past subjunctive - literary
        ]
    }

    tenses = french_tenses if language == 'fr' else spanish_tenses

    return JsonResponse({
        'tenses': tenses,
        'language': language
    })

@require_http_methods(["POST"])
def start_training_session(request):
    """Process session setup and start training"""
    try:
        # Get form data
        language = request.POST.get('language')
        conjugation_level = request.POST.get('conjugation_level')
        fill_level = request.POST.get('fill_level')
        selected_tenses = request.POST.getlist('selected_tenses')
        
        # Validate required fields
        if not all([language, conjugation_level, fill_level]):
            messages.error(request, 'Please fill all required fields.')
            return redirect('verbs_conjugation:session_menu')
        
        # For custom level, ensure tenses are selected
        if conjugation_level == 'custom' and not selected_tenses:
            messages.error(request, 'Please select at least one tense for custom level.')
            return redirect('verbs_conjugation:session_menu')
        
        # Store session configuration
        request.session['conjugation_config'] = {
            'language': language,
            'conjugation_level': conjugation_level,
            'fill_level': fill_level,
            'selected_tenses': selected_tenses,
        }
        
        # Redirect to training interface
        return redirect('verbs_conjugation:training_session')
        
    except Exception as e:
        messages.error(request, f'Error starting training session: {str(e)}')
        return redirect('verbs_conjugation:session_menu')

def training_session(request):
    """Display the verb conjugation training interface"""
    # Get session configuration
    config = request.session.get('conjugation_config')
    
    if not config:
        messages.error(request, 'No training session found. Please start a new session.')
        return redirect('verbs_conjugation:session_menu')
    
    context = {
        'config': json.dumps(config),  # Serialize for JavaScript
        'config_obj': config,  # Keep original for template logic
        'title': 'Verb Conjugation Training',
        'page_title': f'Training - {config["language"].upper()}'
    }
    
    return render(request, 'verbs_conjugation/training_session.html', context)


@login_required
def get_practice_verb(request):
    """API endpoint to get a verb for practice"""
    try:
        # Check if this is an AJAX request and user is not authenticated
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Get session configuration
        config = request.session.get('conjugation_config')
        if not config:
            return JsonResponse({'error': 'No active session'}, status=400)
        
        # Get language and determine selected tenses
        language = 'FR' if config['language'] == 'fr' else 'ES'
        
        if config['conjugation_level'] == 'custom':
            selected_tenses = config['selected_tenses']
        else:
            # Get tenses for the level
            if language == 'FR':
                all_tenses = {
                    'easy': ['Présent', 'Futur', 'Passé composé'],
                    'medium': ['Imparfait', 'Conditionnel présent', 'Impératif présent', 'Futur antérieur'],
                    'hard': ['Subjonctif présent', 'Passé simple', 'Plus-que-parfait']
                }
            else:
                all_tenses = {
                    'easy': ['Presente', 'Futuro', 'Pretérito perfecto compuesto'],
                    'medium': ['Pretérito imperfecto', 'Condicional', 'Imperativo', 'Futuro perfecto'],
                    'hard': ['Subjuntivo presente', 'Pretérito indefinido', 'Pretérito pluscuamperfecto']
                }
            
            selected_tenses = []
            if config['conjugation_level'] in ['easy', 'medium', 'hard']:
                selected_tenses.extend(all_tenses['easy'])
            if config['conjugation_level'] in ['medium', 'hard']:
                selected_tenses.extend(all_tenses['medium'])
            if config['conjugation_level'] == 'hard':
                selected_tenses.extend(all_tenses['hard'])
        
        # Initialize user conjugations if needed
        if not UserConjugation.objects.filter(user=request.user, language=language).exists():
            init_user_conjugations(request.user, language, 10)
        
        # Use our ConjugationEngine to get practice questions
        engine = ConjugationEngine(request.user, language)
        selected_verb_ids = preselect_conjugation_verbs(
            request.user, language, selected_tenses, 1
        )
        
        # Debug logging to understand the issue
        user_conjugations_count = UserConjugation.objects.filter(
            user=request.user, language=language, unlocked=True
        ).count()
        
        print(f"DEBUG - User: {request.user.id}")
        print(f"DEBUG - Language: {language}")
        print(f"DEBUG - Selected tenses: {selected_tenses}")
        print(f"DEBUG - Available user conjugations: {user_conjugations_count}")
        print(f"DEBUG - Selected verb IDs: {selected_verb_ids}")
        
        questions = engine.generate_questions(selected_verb_ids, selected_tenses)
        print(f"DEBUG - Generated questions: {len(questions) if questions else 0}")
        
        if not questions:
            # Let's investigate why no questions were generated
            if not selected_verb_ids:
                print("DEBUG - No verb IDs selected by preselect_conjugation_verbs")
            else:
                # Check if the selected verbs have conjugations for the selected tenses
                for verb_id in selected_verb_ids:
                    for tense in selected_tenses:
                        conjugations_count = VerbConjugation.objects.filter(
                            verb_id=verb_id,
                            language=language,
                            tense=tense
                        ).count()
                        print(f"DEBUG - Verb {verb_id}, Tense {tense}: {conjugations_count} conjugations")
            
            return JsonResponse({'error': 'No verbs available for practice'}, status=200)
        
        question = questions[0]
        
        # Get the verb object for translation
        user_conj = UserConjugation.objects.get(
            user=request.user, verb_id=question['verb_id'], language=language
        )
        
        # Get all conjugations for this verb/tense to provide the complete table
        all_conjugations = {}
        for tense in selected_tenses:
            conjugations = VerbConjugation.objects.filter(
                verb_id=question['verb_id'],
                language=language,
                tense=tense
            ).values_list('pronoun', 'conjugated_form')
            
            # Always include the tense, even if no conjugations exist
            if conjugations:
                all_conjugations[tense] = dict(conjugations)
                print(f"DEBUG - Tense {tense}: {len(conjugations)} conjugations found")
            else:
                # For missing tenses, create entries with "-" for all pronouns
                pronouns_for_language = {
                    'FR': ['je', 'tu', 'il/elle', 'nous', 'vous', 'ils/elles'],
                    'ES': ['yo', 'tú', 'él/ella', 'nosotros', 'vosotros', 'ellos/ellas']
                }
                all_conjugations[tense] = {pronoun: '-' for pronoun in pronouns_for_language[language]}
                print(f"DEBUG - Tense {tense}: No conjugations found, using '-' for all pronouns")
        
        return JsonResponse({
            'verb_id': question['verb_id'],
            'verb': user_conj.verb.infinitive,
            'translation': user_conj.verb.translation,
            'selected_tense': question['tense'],
            'all_conjugations': all_conjugations,
            'selected_tenses': selected_tenses
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def submit_answers(request):
    """API endpoint to submit conjugation answers and get feedback"""
    try:
        data = json.loads(request.body)
        verb_id = data.get('verb_id')
        tense = data.get('tense')
        answers = data.get('answers', {})  # {pronoun: user_answer, ...}
        
        if not all([verb_id, tense, answers]):
            return JsonResponse({'error': 'Missing required data'}, status=400)
        
        # Get session configuration
        config = request.session.get('conjugation_config')
        if not config:
            return JsonResponse({'error': 'No active session'}, status=400)
        
        language = 'FR' if config['language'] == 'fr' else 'ES'
        
        # Get correct answers from database
        correct_conjugations = VerbConjugation.objects.filter(
            verb_id=verb_id,
            language=language,
            tense=tense
        ).values_list('pronoun', 'conjugated_form')
        
        correct_dict = dict(correct_conjugations)
        
        # Evaluate answers
        results = {}
        correct_count = 0
        total_count = 0
        
        for pronoun, user_answer in answers.items():
            if user_answer.strip():  # Only evaluate non-empty answers
                total_count += 1
                correct_answer = correct_dict.get(pronoun, '')
                is_correct = user_answer.strip().lower() == correct_answer.lower()
                
                results[pronoun] = {
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct
                }
                
                if is_correct:
                    correct_count += 1
        
        # Update user's progress using our scoring system
        engine = ConjugationEngine(request.user, language)
        pronoun_results = {p: r['is_correct'] for p, r in results.items()}
        
        if pronoun_results:  # Only update if there were actual answers
            new_score = engine.update_tense_score(verb_id, tense, pronoun_results)
        else:
            new_score = None
        
        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
        
        return JsonResponse({
            'results': results,
            'score': {
                'correct': correct_count,
                'total': total_count,
                'accuracy': round(accuracy, 1)
            },
            'new_tense_score': new_score,
            'all_correct_answers': correct_dict
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
