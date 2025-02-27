from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.articlequiz, name='articlequiz'),
    path('process_quiz_article/', views.process_quiz_article, name='process_quiz_article'),

]
