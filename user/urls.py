from django.urls import path
from .views import (
    login_view, 
    dashboard, 
    add_user_view, 
    logout_view, 
    validate_user
)

urlpatterns = [
    path("", login_view, name="login"),
    path("dashboard/", dashboard, name="dashboard"),
    path("add_user/", add_user_view, name="add_user"),
    path("logout/", logout_view, name="logout"),
    path("validate-user/", validate_user, name="validate_user"),
]
