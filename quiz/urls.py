from django.urls import path
from .views import quiz, submit_quiz

urlpatterns = [
    path("", quiz, name="quiz"),
    path("submit_quiz/", submit_quiz, name="submit_quiz"),
]
