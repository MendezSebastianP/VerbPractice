from django.shortcuts import render
from .models import UserVerb, Verb
from django.contrib.auth.decorators import login_required
from verbs.services import preselect_verbs, TrainingEngine
import uuid

SESSION_KEY = 'verb_training'
LAST_PREF_LENGTH = 'verb_training_last_length'
LAST_PREF_DIRECTION = 'verb_training_last_direction'

@login_required(login_url="/users/login/")
def verbs_home(request):
    user_verbs = UserVerb.objects.filter(user=request.user).select_related('verb')
    return render(request, 'verbs/verbs_home.html', {'verbs': user_verbs})

@login_required(login_url="/users/login/")
def verbs_training(request):
    state = request.session.get(SESSION_KEY, {
        'id': None,
        'remaining': [],
        'current': None,
        'asked': 0,
        'length': 10,
        'hint': 0,
        'direction': 'fr_es',
    })

    if request.method == 'GET' and (state.get('current') or state.get('remaining')):
        request.session.pop(SESSION_KEY, None)
        state = {
            'id': None,
            'remaining': [],
            'current': None,
            'asked': 0,
            'length': state.get('length', 10),
            'hint': 0,
            'direction': state.get('direction', 'fr_es'),
        }

    action = request.POST.get('action') if request.method == 'POST' else None

    if request.method == 'POST' and action in (None, 'start'):
        prev_length = request.session.get(LAST_PREF_LENGTH)
        prev_direction = request.session.get(LAST_PREF_DIRECTION)
        try:
            length = int(request.POST.get('v_length')) if request.POST.get('v_length') else None
        except (TypeError, ValueError):
            length = None
        if length is None:
            length = prev_length or state.get('length', 10)
        fill_lang = request.POST.get('lenguage_fill')
        if fill_lang == 'French':
            direction = 'es_fr'
        elif fill_lang == 'Spanish':
            direction = 'fr_es'
        else:
            direction = prev_direction or state.get('direction', 'fr_es')
        remaining = preselect_verbs(request.user, length)
        request.session[LAST_PREF_LENGTH] = length
        request.session[LAST_PREF_DIRECTION] = direction
        if not remaining:
            fill_choice = 'French' if direction == 'es_fr' else 'Spanish'
            # no verbs; still show container with a simple finished state (question none)
            return render(request, 'verbs/verbs_training.html', {
                'question': None,
                'finished': True,
                'session_length': length,
                'direction': direction,
                'last_length': length,
                'last_fill': fill_choice,
                'previous_feedback': None,
            })
        current = remaining.pop(0)
        state.update({'id': str(uuid.uuid4()), 'remaining': remaining, 'current': current, 'asked': 0, 'length': length, 'hint': 0, 'direction': direction})
        request.session[SESSION_KEY] = state
    elif request.method == 'POST':
        direction = state.get('direction', 'fr_es')
        engine = TrainingEngine(request.user, direction)
        previous_feedback = None
        if not state.get('current') and state.get('remaining'):
            state['current'] = state['remaining'].pop(0)
        action = action or ''
        if action == 'hint' and state.get('current'):
            state['hint'] += 1
            request.session[SESSION_KEY] = state
        elif action in ('answer', 'giveup') and state.get('current'):
            verb_id = state['current']
            verb = Verb.objects.get(pk=verb_id)
            prompt, correct_field = engine.format_prompt_answer(verb)
            if action == 'giveup':
                engine.update_on_result(verb_id, False)
                previous_feedback = f"The answer is {prompt} : {correct_field.split(',')[0].strip()}"
                state['asked'] += 1
                state['hint'] = 0
                # advance (finish?)
                if state['remaining']:
                    state['current'] = state['remaining'].pop(0)
                    request.session[SESSION_KEY] = state
                else:
                    length = state.get('length', 10)
                    direction = state.get('direction', 'fr_es')
                    request.session[LAST_PREF_LENGTH] = length
                    request.session[LAST_PREF_DIRECTION] = direction
                    request.session.pop(SESSION_KEY, None)
                    fill_choice = 'French' if direction == 'es_fr' else 'Spanish'
                    # show last question container (prompt) with finished flag
                    return render(request, 'verbs/verbs_training.html', {
                        'question': {'verb_id': verb_id, 'prompt': prompt},
                        'session_length': length,
                        'finished': True,
                        'direction': direction,
                        'previous_feedback': previous_feedback,
                        'last_length': length,
                        'last_fill': fill_choice,
                    })
            elif action == 'answer':
                answer = (request.POST.get('answer') or '').strip()
                is_ok = engine.is_correct(correct_field, answer)
                if is_ok:
                    engine.update_on_result(verb_id, True)
                    previous_feedback = 'Correct!'
                    state['asked'] += 1
                    state['hint'] = 0
                    if state['remaining']:
                        state['current'] = state['remaining'].pop(0)
                        request.session[SESSION_KEY] = state
                    else:
                        length = state.get('length', 10)
                        direction = state.get('direction', 'fr_es')
                        request.session[LAST_PREF_LENGTH] = length
                        request.session[LAST_PREF_DIRECTION] = direction
                        request.session.pop(SESSION_KEY, None)
                        fill_choice = 'French' if direction == 'es_fr' else 'Spanish'
                        return render(request, 'verbs/verbs_training.html', {
                            'question': {'verb_id': verb_id, 'prompt': prompt},
                            'session_length': length,
                            'finished': True,
                            'direction': direction,
                            'previous_feedback': previous_feedback,
                            'last_length': length,
                            'last_fill': fill_choice,
                        })
                else:
                    engine.update_on_result(verb_id, False)
                    q = {'verb_id': verb_id, 'prompt': prompt, 'feedback': f"Wrong. The answer is {correct_field.split(',')[0].strip()}"}
                    if state['hint']:
                        q['hint'] = engine.hint(correct_field, state['hint'])
                    request.session[SESSION_KEY] = state
                    return render(request, 'verbs/verbs_training.html', {
                        'question': q,
                        'session_length': state.get('length', 10),
                        'finished': False,
                        'direction': direction,
                        'previous_feedback': None,
                    })
        # fall-through render after hint / advance
        if state.get('current'):
            verb = Verb.objects.get(pk=state['current'])
            prompt, correct_field = engine.format_prompt_answer(verb)
            question = {'verb_id': state['current'], 'prompt': prompt}
            if state['hint']:
                question['hint'] = engine.hint(correct_field, state['hint'])
        else:
            question = None
        return render(request, 'verbs/verbs_training.html', {
            'question': question,
            'session_length': state.get('length', 10),
            'finished': False,
            'direction': direction,
            'previous_feedback': previous_feedback,
        })

    # GET after start or initial menu
    if state.get('current'):
        direction = state.get('direction', 'fr_es')
        engine = TrainingEngine(request.user, direction)
        verb = Verb.objects.get(pk=state['current'])
        prompt, correct_field = engine.format_prompt_answer(verb)
        question = {'verb_id': state['current'], 'prompt': prompt}
        if state['hint']:
            question['hint'] = engine.hint(correct_field, state['hint'])
        context = {
            'question': question,
            'session_length': state.get('length', 10),
            'finished': False,
            'direction': direction,
            'previous_feedback': None,
        }
    else:
        last_length = request.session.get(LAST_PREF_LENGTH, state.get('length', 10))
        last_direction = request.session.get(LAST_PREF_DIRECTION, state.get('direction', 'fr_es'))
        last_fill = 'French' if last_direction == 'es_fr' else 'Spanish'
        context = {
            'question': None,
            'session_length': last_length,
            'finished': False,
            'direction': last_direction,
            'last_length': last_length,
            'last_fill': last_fill,
            'previous_feedback': None,
        }
    return render(request, 'verbs/verbs_training.html', context)

# @login_required(login_url="/users/login/")
# def post_new(request):
#     return render(request, 'posts/post_new.html')