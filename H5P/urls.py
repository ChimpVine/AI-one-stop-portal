from django.urls import path
from .views import h5p,cross_word,process_crossword_h5p
from .findthewordviews import find_the_word,process_word_search
urlpatterns = [
    path("", h5p, name="h5p"),
    path("find_the_word/",find_the_word,name="find_the_word"),
    path("cross_word/",cross_word,name="cross_word"),
    path('process_crossword_h5p/', process_crossword_h5p, name='process_crossword_h5p'),
    path('process_word_search/', process_word_search, name='process_word_search'),
    

]
