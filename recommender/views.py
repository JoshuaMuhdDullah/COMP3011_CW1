from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Movie, Comment
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Create your views here.
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Automatically log them in after registering
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

def movie_search(request):
    query = request.GET.get('q')
    genre_filter = request.GET.get('genre')
    
    # 1. Get all unique genres for the dropdown
    # This splits strings like "Action, Sci-Fi" and gets unique values
    all_movies = Movie.objects.all()
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

    # If no search/filter, just show top 10
    if not query and not genre_filter:
        results = results.order_by('-imdb_rating')[:10]

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

def movie_search_ajax(request):
    query = request.GET.get('q', '')
    if len(query) > 1:  # Only search if user typed 2+ characters
        movies = Movie.objects.filter(series_title__icontains=query)[:10]
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
        return JsonResponse({'status': 'success', 'data': results})
    return JsonResponse({'status': 'empty', 'data': []})

@login_required
def toggle_bookmark(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    
    if request.user in movie.watchlisted_by.all():
        movie.watchlisted_by.remove(request.user)
    else:
        movie.watchlisted_by.add(request.user)
    
    # Returns the user to the same page they were on
    return redirect(request.META.get('HTTP_REFERER', 'movie_search'))

@login_required
def watchlist_view(request):
    # Fetch only the movies this user has added
    my_movies = request.user.watchlist.all()
    
    # Apply our High-Res fix so the watchlist looks great
    for m in my_movies:
        if m.poster_link and "_V1_" in m.poster_link:
            m.poster_link = m.poster_link.split('_V1_')[0] + "_V1_.jpg"
            
    return render(request, 'recommender/watchlist.html', {'movies': my_movies})

@login_required
def add_comment(request, movie_id):
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