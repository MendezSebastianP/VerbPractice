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
    # IMPORTANT: These names must match exactly what's in the database
    french_tenses = {
        # Easy level tenses - most commonly used by native speakers
        'easy': [
            'présent',           # Most used - I am, you are, etc.
            'futur',             # Simple future - I will be  
            'Passé composé',     # Perfect past - I have been
        ],
        # Medium level adds these - moderately common
        'medium': [
            'imparfait',         # Imperfect past - I was being
            'Conditionnel présent',  # Would + verb
            'Impératif',         # Commands - Be! Do!
        ],
        # Hard level adds these - advanced but still used
        'hard': [
            'Subjonctif présent',    # Subjunctive - doubt, emotion
            'passé simple',          # Literary past - formal writing only  
            'Subjonctif imparfait',  # Imperfect subjunctive - very formal
        ],
    }

    spanish_tenses = {
        # Easy level tenses - most commonly used by native speakers  
        'easy': [
            'Presente',          # Most used - I am, you are, etc.
            'Futuro',            # Simple future - I will be
            'pretérito perfecto compuesto',  # Perfect past - I have been
        ],
        # Medium level adds these - moderately common
        'medium': [
            'Imperfecto',        # Imperfect past - I was being
            'Condicional',       # Would + verb
            'Imperativo',        # Commands - Be! Do!
            'futuro perfecto',   # Future perfect - I will have been
        ],
        # Hard level adds these - advanced but still used
        'hard': [
            'Subjuntivo presente',    # Subjunctive - doubt, emotion
            'Pretérito indefinido',   # Preterite - completed past actions
            'pretérito pluscuamperfecto',  # Pluperfect - I had been
        ],
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
        
        # Clear any existing training session
        if 'current_session' in request.session:
            del request.session['current_session']
        
        # Redirect to training interface
        return redirect('verbs_conjugation:training_session')
        
    except Exception as e:
        messages.error(request, f'Error starting training session: {str(e)}')
        return redirect('verbs_conjugation:session_menu')

@login_required
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
    """API endpoint to get a verb for practice - returns session of 5 verbs"""
    try:
        # Check if this is an AJAX request and user is not authenticated
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Check if user wants to advance to next verb
        advance_verb = request.GET.get('next', 'false').lower() == 'true'
        
        # Get session configuration
        config = request.session.get('conjugation_config')
        if not config:
            return JsonResponse({'error': 'No active session'}, status=400)
        
        # Get language and determine selected tenses
        language = 'FR' if config['language'] == 'fr' else 'ES'
        
        if config['conjugation_level'] == 'custom':
            selected_tenses = config['selected_tenses']
        else:
            # Get tenses for the level - FIXED: Using actual database tense names
            if language == 'FR':
                all_tenses = {
                    'easy': ['présent', 'futur', 'Passé composé'],
                    'medium': ['imparfait', 'Conditionnel présent', 'Impératif'],
                    'hard': ['Subjonctif présent', 'passé simple', 'Subjonctif imparfait']
                }
            else:
                all_tenses = {
                    'easy': ['Presente', 'Futuro', 'pretérito perfecto compuesto'],
                    'medium': ['Imperfecto', 'Condicional', 'Imperativo', 'futuro perfecto'],
                    'hard': ['Subjuntivo presente', 'Pretérito indefinido', 'pretérito pluscuamperfecto']
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
        
        # Check if we already have a session in progress
        if 'current_session' not in request.session:
            # Start new session - select 5 verbs for the entire session
            print(f"\n🎯 STARTING NEW SESSION")
            print(f"Language: {language}, Level: {config['conjugation_level']}")
            print(f"Selected tenses: {selected_tenses}")
            
            selected_verb_ids = preselect_conjugation_verbs(
                request.user, language, selected_tenses, 5  # Changed to 5 verbs
            )
            
            if not selected_verb_ids:
                print("❌ No verbs available for session")
                return JsonResponse({'error': 'No verbs available for practice'}, status=200)
            
            # Get verb information and scores
            session_verbs = []
            print(f"\n📚 SESSION VERBS AND SCORES:")
            for i, verb_id in enumerate(selected_verb_ids, 1):
                user_conj = UserConjugation.objects.get(
                    user=request.user, verb_id=verb_id, language=language
                )
                
                # Get current scores for this verb
                verb_scores = {}
                for tense in selected_tenses:
                    score = user_conj.tense_scores.get(tense, 1000)  # Default score
                    verb_scores[tense] = score
                
                session_verbs.append({
                    'verb_id': verb_id,
                    'infinitive': user_conj.verb.infinitive,
                    'translation': user_conj.verb.translation,
                    'scores': verb_scores
                })
                
                print(f"  {i}. {user_conj.verb.infinitive} ({user_conj.verb.translation})")
                for tense, score in verb_scores.items():
                    print(f"     {tense}: {score}")
            
            # Store session data
            request.session['current_session'] = {
                'verbs': session_verbs,
                'selected_tenses': selected_tenses,
                'current_verb_index': 0,
                'language': language
            }
            request.session.save()
        
        # Get current session data
        session_data = request.session['current_session']
        current_index = session_data['current_verb_index']
        
        # If user requested to advance to next verb, increment the index
        if advance_verb and current_index < len(session_data['verbs']) - 1:
            current_index += 1
            request.session['current_session']['current_verb_index'] = current_index
            request.session.save()
            print(f"⏭️ ADVANCING TO NEXT VERB")
        
        # Check if session is complete
        if current_index >= len(session_data['verbs']):
            print("✅ SESSION COMPLETE!")
            del request.session['current_session']
            return JsonResponse({'session_complete': True})
        
        # Get current verb
        current_verb = session_data['verbs'][current_index]
        verb_id = current_verb['verb_id']
        
        print(f"\n🔍 EVALUATING VERB {current_index + 1}/5: {current_verb['infinitive']}")
        
        # Use our ConjugationEngine to generate questions for this specific verb
        engine = ConjugationEngine(request.user, language)
        questions = engine.generate_questions([verb_id], selected_tenses)
        
        if not questions:
            print(f"❌ No conjugations available for {current_verb['infinitive']}")
            # Skip to next verb
            request.session['current_session']['current_verb_index'] += 1
            request.session.save()
            return get_practice_verb(request)  # Recursive call to try next verb
        
        question = questions[0]
        
        # Get all conjugations for this verb/tense to provide the complete table
        all_conjugations = {}
        for tense in selected_tenses:
            conjugations = VerbConjugation.objects.filter(
                verb_id=verb_id,
                language=language,
                tense=tense
            ).values_list('pronoun', 'conjugated_form')
            
            if conjugations:
                all_conjugations[tense] = dict(conjugations)
            else:
                # For missing tenses, create entries with "-" for all pronouns
                pronouns_for_language = {
                    'FR': ['je', 'tu', 'il (elle, on)', 'nous', 'vous', 'ils (elles)'],
                    'ES': ['yo', 'tú', 'él/ella', 'nosotros', 'vosotros', 'ellos/ellas']
                }
                all_conjugations[tense] = {pronoun: '-' for pronoun in pronouns_for_language[language]}
        
        return JsonResponse({
            'verb_id': verb_id,
            'verb': current_verb['infinitive'],
            'translation': current_verb['translation'],
            'selected_tense': question['tense'],
            'all_conjugations': all_conjugations,
            'selected_tenses': selected_tenses,
            'session_progress': {
                'current': current_index + 1,
                'total': len(session_data['verbs']),
                'verb_name': current_verb['infinitive']
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR in get_practice_verb: {str(e)}")
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
        
        # Get current verb info for logging
        session_data = request.session.get('current_session')
        if session_data:
            current_index = session_data['current_verb_index']
            current_verb = session_data['verbs'][current_index]
            
            print(f"📊 VERB COMPLETED: {current_verb['infinitive']}")
            print(f"   Tense: {tense}")
            print(f"   Score: {correct_count}/{total_count} ({accuracy:.1f}%)")
            if new_score:
                print(f"   New tense score: {new_score}")
            
            # Advance to next verb
            request.session['current_session']['current_verb_index'] += 1
            request.session.save()
        
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
        print(f"❌ ERROR in submit_answers: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def debug_session(request):
    """Debug endpoint to check session and user state"""
    config = request.session.get('conjugation_config')
    current_session = request.session.get('current_session')
    
    return JsonResponse({
        'user_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'has_config': bool(config),
        'config': config,
        'has_current_session': bool(current_session),
        'session_info': {
            'verb_count': len(current_session['verbs']) if current_session else 0,
            'current_index': current_session.get('current_verb_index', 0) if current_session else 0,
        } if current_session else None
    })
