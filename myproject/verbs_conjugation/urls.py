from django.urls import path
from . import views

app_name = 'verbs_conjugation'

urlpatterns = [
    path('', views.session_menu, name='session_menu'),
    path('get-tenses/', views.get_available_tenses, name='get_tenses'),
    path('start-session/', views.start_training_session, name='start_session'),
    path('training/', views.training_session, name='training_session'),
    path('api/get-verb/', views.get_practice_verb, name='get_practice_verb'),
    path('api/submit-answers/', views.submit_answers, name='submit_answers'),
]
