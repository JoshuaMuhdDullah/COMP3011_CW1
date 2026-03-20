from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_search, name='movie_search'),
    path('movie/<int:movie_id>/', views.movie_detail_page, name='movie_detail'),
    path('api/search/', views.movie_search_ajax, name='movie_search_ajax'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('login/', views.login_view, name='login'),         
    path('register/', views.register_view, name='register'),
    
    # RESTful Auth Endpoints
    path('api/v1/auth/register/', views.api_register, name='api_register'),
    path('api/v1/auth/login/', views.api_login, name='api_login'),
    path('api/v1/auth/logout/', views.api_logout, name='logout'),
    
    # Movie & recommendations
    path('api/v1/movies/<int:movie_id>/', views.api_movie_detail, name='api_movie_detail'),
    path('api/v1/movies/', views.movie_search_ajax, name='api_movie_search'),
    
    # Watchlist Resource: Handles GET (list), POST (add), and DELETE (remove)
    path('api/v1/watchlist/', views.watchlist_api, name='api_watchlist'),
    path('api/v1/watchlist/<int:movie_id>/', views.watchlist_api, name='api_watchlist_item'),
    path('export/watchlist/', views.export_watchlist_json, name='export_watchlist_json'),

    # Comment Resource: Handles POST (create) and DELETE (remove)
    path('api/v1/movies/<int:movie_id>/comments/', views.comment_api, name='api_add_comment'),
    path('api/v1/comments/<int:comment_id>/', views.comment_api, name='api_delete_comment'),
]