from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add_user/', views.add_user_view, name='add_user'),
    path('logout/',views.logout,name='logout'),
    # path('article/',views.article,name='article'),
    path('token/refresh/', views.refresh_token_view, name='token_refresh'),


    
    
    
    
]

