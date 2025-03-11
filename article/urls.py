from django.urls import path
from .views import article,generate_and_post_article
urlpatterns = [
    path("", article, name="article"),
    path("generate_and_post_article/",generate_and_post_article, name="generate_and_post_article"),
]
