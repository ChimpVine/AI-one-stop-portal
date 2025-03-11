from django.urls import path
from .views import (
    login_view, 
    dashboard, 
    add_user_view, 
    logout_view, 
    validate_user,
    users_list_view,
    delete_user,
    edit_user_view

)

urlpatterns = [
    path("", login_view, name="login"),
    path("dashboard/", dashboard, name="dashboard"),
    path("add_user/", add_user_view, name="add_user"),
    path("logout/", logout_view, name="logout"),
    path("validate-user/", validate_user, name="validate_user"),
    path('users/', users_list_view, name='users_list'),
    path('delete-user/<int:user_id>/', delete_user, name='delete_user'),
    path('edit_user/<int:user_id>/',edit_user_view, name='edit_user'),


]
