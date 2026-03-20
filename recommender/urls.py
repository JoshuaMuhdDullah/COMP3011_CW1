from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_search, name='movie_search'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
]