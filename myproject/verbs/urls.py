from django.urls import path
from . import views

app_name = 'verbs'

urlpatterns = [
    path('', views.verbs_home, name="verbhome"),
	path('verbs_training', views.verbs_training, name="verbstraining"),
    # path('new-session/', views.post_new, name="new-session"),
]
