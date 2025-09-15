from django.urls import path
from . import views

app_name = 'word_training'

urlpatterns = [
	path('', views.word_home, name="home"),
	path('train/', views.word_training, name="word_training"),
	path('addwords/', views.addwords, name="addwords"),
    # path('fill/', views.auto_fill, name="fill"),  # to be implemented later
]
