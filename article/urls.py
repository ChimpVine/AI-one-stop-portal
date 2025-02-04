from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.article, name='article'),
    path('generate_and_post_article/', views.generate_and_post_article, name='generate_and_post_article'),

]
