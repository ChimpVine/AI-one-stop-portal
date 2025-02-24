from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add_user/', views.add_user_view, name='add_user'),
    path('logout/',views.logout_view,name='logout'),
    # path('article/',views.article,name='article'),


    
    
    
    
]

