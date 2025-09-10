from django.urls import path
from . import views

app_name = 'auto_training'

urlpatterns = [
	path('', views.auto_home, name="home"),
	path('train/', views.auto_training, name="autotraining"),
	path('addwords/', views.addwords, name="addwords"),
    # path('fill/', views.auto_fill, name="fill"),  # to be implemented later
]
