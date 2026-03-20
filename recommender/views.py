import json

from django.shortcuts import render, redirect
from django.http import JsonResponse,HttpResponseForbidden
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError
from .models import Movie, Comment
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity

# Create your views here.
def register_view(request):
    return render(request, 'recommender/register.html')

def login_view(request):
    return render(request, 'recommender/login.html')

@require_http_methods(["POST"])
def api_register(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')

        if not username or not password:
            return JsonResponse({'error': 'Username and password are required'}, status=400)

        # Create the user resource
        user = User.objects.create_user(username=username, password=password, email=email)
        
        # Automatically log them in (creating the session resource)
        login(request, user)
        
        return JsonResponse({
            'message': 'User created and logged in successfully',
            'user': user.username
        }, status=201)

    except IntegrityError:
        return JsonResponse({'error': 'Username already exists'}, status=409) # 409 Conflict
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
@require_http_methods(["POST"])
def api_login(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return JsonResponse({'message': 'Login successful', 'user': user.username}, status=200)
        return JsonResponse({'error': 'Invalid credentials'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

@require_http_methods(["DELETE"])
def api_logout(request):
    logout(request)
    return JsonResponse({'message': 'Logged out'}, status=204)

def get_similarity_matrix():
    # Fetch data including director and rating
    all_movies = Movie.objects.all().values('id', 'overview', 'director', 'imdb_rating')
    if not all_movies.exists():
        return None, None
        
    df = pd.DataFrame(list(all_movies))
    
    # Clean director names (remove spaces so 'Christopher Nolan' becomes 'ChristopherNolan')
    # This ensures the model treats the full name as a unique keyword
    df['director_cleaned'] = df['director'].apply(lambda x: x.replace(" ", "") if x else "")
    
    # Create the "Content Soup" (Overview + Director mentioned twice to give it more weight)
    df['soup'] = df['overview'] + " " + df['director_cleaned'] + " " + df['director_cleaned']
    
    # TF-IDF on the soup
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['soup'])
    
    # Calculate Base Similarity
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    
    return df, cosine_sim

DF_MOVIES, COSINE_SIM = get_similarity_matrix()

def get_personal_recs(user_watchlist):
    # 1. Fetch data from DB and convert to DataFrame
    # We include 'series_title' to ensure we can identify the movies
    all_movies = Movie.objects.all().values('id', 'series_title', 'overview', 'director')
    if not all_movies.exists():
        return []
    
    df_all = pd.DataFrame(list(all_movies))
    
    # 2. Identify what the user already has (by ID and Title)
    watchlisted_ids = [m.id for m in user_watchlist]
    watchlisted_titles = [m.series_title for m in user_watchlist]
    
    # 3. Create the "Content Soup" 
    # Combining Director and Overview gives the AI more 'context' to match
    df_all['soup'] = df_all['director'].fillna('') + ' ' + df_all['overview'].fillna('')
    
    # 4. Vectorize the library
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df_all['soup'])
    
    # 5. Find the 'Taste Profile' 
    # We find the rows in our matrix that correspond to the user's watchlist
    user_indices = df_all[df_all['id'].isin(watchlisted_ids)].index.tolist()
    
    if not user_indices:
        return []

    # Calculate the average vector of all movies the user likes
    user_profile_vector = np.asarray(tfidf_matrix[user_indices].mean(axis=0))
    
    # 6. Compute Similarity
    sim_scores = cosine_similarity(user_profile_vector, tfidf_matrix).flatten()
    
    # 7. Filter and Return the Top 5
    related_indices = sim_scores.argsort()[::-1]
    
    recommendations = []
    for i in related_indices:
        title = df_all.iloc[i]['series_title']
        
        # Don't suggest movies they've already bookmarked
        if title not in watchlisted_titles:
            movie_obj = Movie.objects.filter(series_title=title).first()
            if movie_obj:
                # Apply High-Res Poster Fix
                if movie_obj.poster_link and "_V1_" in movie_obj.poster_link:
                    movie_obj.poster_link = movie_obj.poster_link.split('_V1_')[0] + "_V1_.jpg"
                recommendations.append(movie_obj)
        
        if len(recommendations) >= 5:
            break
            
    return recommendations

def movie_search(request):
    try:
        query = request.GET.get('q')
        genre_filter = request.GET.get('genre')
        
        # 1. Get all movies - efficient query
        all_movies = Movie.objects.all()
        
        # Handle case where database might be empty
        if not all_movies.exists():
            messages.warning(request, "The movie database is currently empty.")
            return render(request, 'recommender/search.html', {'results': [], 'genres': []})

        # Genre extraction logic...
        genres_set = set()
        for g in all_movies.values_list('genre', flat=True):
            if g:
                genres_set.update([item.strip() for item in g.split(',')])
        sorted_genres = sorted(list(genres_set))

        # 2. Filtering Logic
        results = all_movies
        heading = "Top Rated Classics"

        if query:
            results = results.filter(series_title__icontains=query)
            heading = f"Results for '{query}'"
        
        if genre_filter:
            results = results.filter(genre__icontains=genre_filter)
            heading = f"{genre_filter} Movies"

        # Limit results for better performance
        if not query and not genre_filter:
            results = results.order_by('-imdb_rating')[:10]
        else:
            results = results[:50] 

        for movie in results:
            if movie.poster_link and "_V1_" in movie.poster_link:
                movie.poster_link = movie.poster_link.split('_V1_')[0] + "_V1_.jpg"

        return render(request, 'recommender/search.html', {
            'results': results,
            'query': query,
            'heading': heading,
            'genres': sorted_genres,
            'current_genre': genre_filter
        })

    except Exception as e:
        print(f"Search Error: {e}")
        return render(request, 'errors/500.html', status=500)
    
# AJAX endpoint for live search suggestions
def movie_search_ajax(request):
    query = request.GET.get('q', '')

    if not query:
        return JsonResponse({
            'error': 'Bad Request',
            'message': 'Query parameter "q" is required.'
        }, status=400)

    if len(query) < 2:
        return JsonResponse({
            'error': 'Unprocessable Entity',
            'message': 'Search query must be at least 2 characters.'
        }, status=422)

    try:
        movies = Movie.objects.filter(series_title__icontains=query)[:10]
        
        if not movies.exists():
            return JsonResponse({'status': 'no_results', 'data': []}, status=200)

        results = []
        for m in movies:
            poster = m.poster_link
            if poster and "_V1_" in poster:
                poster = poster.split('_V1_')[0] + "_V1_.jpg"
                
            results.append({
                'id': m.id,
                'title': m.series_title,
                'poster': poster,
                'year': m.released_year,
                'rating': m.imdb_rating
            })
        
        return JsonResponse({'status': 'success', 'data': results}, status=200)

    except Exception as e:
        return JsonResponse({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred on the server.'
        }, status=500)

def api_movie_detail(request, movie_id):
    """Returns movie details, recommendations, and comments as JSON."""
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Aligning with your comment_api: fetching 'content' instead of 'text'
    comments = movie.comments.all().order_by('-created_at')
    
    # Check watchlist status for the logged-in user
    is_in_watchlist = False
    if request.user.is_authenticated:
        is_in_watchlist = request.user.watchlist.filter(id=movie.id).exists()

    recommendations_data = []
    if DF_MOVIES is not None:
        try:
            idx = DF_MOVIES.index[DF_MOVIES['id'] == movie.id].tolist()[0]
            sim_scores = sorted(list(enumerate(COSINE_SIM[idx])), key=lambda x: x[1], reverse=True)
            movie_indices = [i[0] for i in sim_scores[1:6]]
            rec_ids = DF_MOVIES['id'].iloc[movie_indices].values
            
            # Efficiently fetch and order recommendations
            recs = Movie.objects.filter(id__in=rec_ids)
            recs_dict = {r.id: r for r in recs}
            for rid in rec_ids:
                if rid in recs_dict:
                    r = recs_dict[rid]
                    recommendations_data.append({
                        'id': r.id,
                        'title': r.series_title,
                        'poster': r.poster_link.split('_V1_')[0] + "_V1_.jpg" if r.poster_link else None,
                        'rating': r.imdb_rating
                    })
        except Exception as e:
            print(f"Recommendation Error: {e}")
            pass

    return JsonResponse({
        'id': movie.id,
        'title': movie.series_title,
        'overview': movie.overview,
        'poster': movie.poster_link.split('_V1_')[0] + "_V1_.jpg" if movie.poster_link else None,
        'rating': movie.imdb_rating,
        'released_year': movie.released_year,
        'genre': movie.genre,
        'director': movie.director,
        'is_in_watchlist': is_in_watchlist,
        'recommendations': recommendations_data,
        'comments': [
            {
                'id': c.id,
                'user': c.user.username, 
                'content': c.content,
                'created_at': c.created_at.strftime('%Y-%m-%d'),
                'is_owner': c.user == request.user
            } for c in comments
        ]
    })

def movie_detail_page(request, movie_id):
    return render(request, 'recommender/detail.html', {'movie_id': movie_id})

def movie_recommendations_api(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    recommendations = []
    
    if DF_MOVIES is not None:
        try:
            idx = DF_MOVIES.index[DF_MOVIES['id'] == movie.id].tolist()[0]
            sim_scores = sorted(list(enumerate(COSINE_SIM[idx])), key=lambda x: x[1], reverse=True)
            movie_indices = [i[0] for i in sim_scores[1:6]]
            recommended_ids = DF_MOVIES['id'].iloc[movie_indices].values
            
            recs = Movie.objects.filter(id__in=recommended_ids)
            recommendations = [{
                'id': r.id, 
                'title': r.series_title, 
                'rating': r.imdb_rating,
                'poster': r.poster_link.split('_V1_')[0] + "_V1_.jpg" if r.poster_link else None
            } for r in recs]
            
        except (IndexError, ValueError):
            pass
            
    return JsonResponse({'recommendations': recommendations}, status=200)

@login_required
def watchlist_view(request):
    return render(request, 'recommender/watchlist.html')

@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def watchlist_api(request, movie_id=None):
    """
    Unified REST Resource for the Watchlist.
    URL: /api/v1/watchlist/<movie_id>/
    """
    
    # --- GET: Fetch Watchlist & Recommendations ---
    if request.method == "GET":
        my_movies = request.user.watchlist.all()
        
        # Prepare Data with posters and years
        watchlist_data = []
        for m in my_movies:
            poster = m.poster_link
            if poster and "_V1_" in poster:
                poster = poster.split('_V1_')[0] + "_V1_.jpg"
            
            watchlist_data.append({
                'id': m.id,
                'title': m.series_title,
                'rating': m.imdb_rating,
                'year': m.released_year,
                'poster': poster
            })

        # Do the same for recommendations
        recommendations = get_personal_recs(my_movies)
        rec_data = []
        for r in recommendations:
            poster = r.poster_link
            if poster and "_V1_" in poster:
                poster = poster.split('_V1_')[0] + "_V1_.jpg"
            
            rec_data.append({
                'id': r.id,
                'title': r.series_title,
                'poster': poster
            })

        return JsonResponse({
            'watchlist': watchlist_data,
            'suggestions': rec_data
        }, status=200)

    # --- POST: Add to Watchlist (Create Resource) ---
    elif request.method == "POST":
        movie = get_object_or_404(Movie, id=movie_id)
        request.user.watchlist.add(movie)
        return JsonResponse({'message': 'Movie added'}, status=201)

    # --- DELETE: Remove from Watchlist (Delete Resource) ---
    elif request.method == "DELETE":
        movie = get_object_or_404(Movie, id=movie_id)
        request.user.watchlist.remove(movie)
        return JsonResponse({}, status=204)

@login_required
@require_http_methods(["POST", "DELETE"])
def comment_api(request, movie_id=None, comment_id=None):
    # --- CREATE (POST) ---
    if request.method == "POST":
        movie = get_object_or_404(Movie, id=movie_id)
        
        # Handle both standard Form data and JSON data
        content = request.POST.get('content') or json.loads(request.body).get('content')
        
        if not content:
            return JsonResponse({'error': 'Comment content is required'}, status=400)
            
        comment = Comment.objects.create(
            user=request.user, 
            movie=movie, 
            content=content
        )
        
        return JsonResponse({
            'message': 'Comment added successfully',
            'comment_id': comment.id,
            'user': request.user.username
        }, status=201)

    elif request.method == "DELETE":
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        comment.delete()
        
        return JsonResponse({}, status=204)

@login_required
def export_watchlist_json(request):
    # Fetch the user's specific watchlist
    user_watchlist = request.user.watchlist.all()
    
    if not user_watchlist.exists():
        return JsonResponse(
            {'error': 'No movies found in watchlist'}, 
            status=404
        )

    # Create a list of dictionaries (the data structure for JSON)
    watchlist_data = []
    for movie in user_watchlist:
        watchlist_data.append({
            'id': movie.id,
            'title': movie.series_title,
            'director': movie.director,
            'rating': movie.imdb_rating,
            'year': movie.released_year,
            'genre': movie.genre,
            'poster': movie.poster_link,
        })
    
    # Return as a downloadable JSON file
    response = JsonResponse(watchlist_data, safe=False, json_dumps_params={'indent': 4})
    response['Content-Disposition'] = 'attachment; filename="my_watchlist.json"'
    return response

