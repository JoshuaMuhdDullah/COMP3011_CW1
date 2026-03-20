from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_search, name='movie_search'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('api/search/', views.movie_search_ajax, name='movie_search_ajax'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('bookmark/<int:movie_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('movie/<int:movie_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('watchlist/export/', views.export_watchlist_json, name='export_watchlist_json'),
]