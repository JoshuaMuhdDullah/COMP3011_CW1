from django.shortcuts import render, redirect
from django.http import JsonResponse,HttpResponseForbidden
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Movie, Comment
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity

# Create your views here.
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('movie_search')
    else:
        form = UserCreationForm()
    return render(request, 'recommender/register.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('movie_search')
    else:
        form = AuthenticationForm()
    return render(request, 'recommender/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('movie_search')

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

def movie_detail(request, movie_id):
    # 1. Initialize variables at the top to prevent "Unbound" errors
    movie = Movie.objects.get(id=movie_id)
    comments = movie.comments.all().order_by('-created_at')
    recommendations = []
    recommended_ids = [] # Default to empty

    # 2. Try the Recommendation Logic
    if DF_MOVIES is not None:
        try:
            # Get the index of the current movie
            idx = DF_MOVIES.index[DF_MOVIES['id'] == movie.id].tolist()[0]
            
            # Calculate/Get similarity scores
            sim_scores = list(enumerate(COSINE_SIM[idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            
            # Get top 5 indices (skipping the first one which is the movie itself)
            movie_indices = [i[0] for i in sim_scores[1:6]]
            
            # ASSIGN VALUE HERE
            recommended_ids = DF_MOVIES['id'].iloc[movie_indices].values
            
            # Fetch actual objects from DB
            recommendations = Movie.objects.filter(id__in=recommended_ids)
            
        except (IndexError, ValueError):
            # If the movie isn't in our DF, recommendations stays empty
            pass

    if movie.poster_link and "_V1_" in movie.poster_link:
        movie.poster_link = movie.poster_link.split('_V1_')[0] + "_V1_.jpg"

    for rec in recommendations:
        if rec.poster_link and "_V1_" in rec.poster_link:
            rec.poster_link = rec.poster_link.split('_V1_')[0] + "_V1_.jpg"

    return render(request, 'recommender/detail.html', {
        'movie': movie, 
        'recommendations': recommendations,
        'comments': comments
    })

@login_required
def toggle_bookmark(request, movie_id):

    if request.user.is_anonymous:
        return HttpResponseForbidden("You must be logged in.")


    movie = get_object_or_404(Movie, id=movie_id)
    
    if request.user in movie.watchlisted_by.all():
        movie.watchlisted_by.remove(request.user)
    else:
        movie.watchlisted_by.add(request.user)
    
    # Returns the user to the same page they were on
    return redirect(request.META.get('HTTP_REFERER', 'movie_search'))

@login_required
def watchlist_view(request):
    my_movies = request.user.watchlist.all()
    
    # Apply High-Res Fix for current watchlist
    for m in my_movies:
        if m.poster_link and "_V1_" in m.poster_link:
            m.poster_link = m.poster_link.split('_V1_')[0] + "_V1_.jpg"

    # Call our new procedure
    recommendations = get_personal_recs(my_movies) if my_movies.exists() else []

    return render(request, 'recommender/watchlist.html', {
        'movies': my_movies,
        'recommendations': recommendations
    })

@login_required
def add_comment(request, movie_id):

    if request.user.is_anonymous:
        return HttpResponseForbidden("You must be logged in.")

    if request.method == "POST":
        movie = get_object_or_404(Movie, id=movie_id)
        content = request.POST.get('content')
        if content:
            Comment.objects.create(user=request.user, movie=movie, content=content)
    return redirect('movie_detail', movie_id=movie_id)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    movie_id = comment.movie.id
    comment.delete()
    return redirect('movie_detail', movie_id=movie_id)

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

