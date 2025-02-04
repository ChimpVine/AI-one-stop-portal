from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.quiz, name='quiz'),
    path('submit_quiz/', views.submit_quiz, name='submit_quiz'),

]
