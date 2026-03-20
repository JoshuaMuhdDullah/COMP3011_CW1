from django.shortcuts import render
from .models import Movie
from django.shortcuts import render
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Create your views here.
def get_similarity_matrix():
    all_movies = Movie.objects.all().values('id', 'overview')
    if not all_movies.exists():
        return None, None
        
    df = pd.DataFrame(list(all_movies))
    
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['overview'])
    
    # Pre-compute the similarity scores
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

    return render(request, 'recommender/search.html', {
        'results': results,
        'query': query,
        'heading': heading,
        'genres': sorted_genres,
        'current_genre': genre_filter
    })

def movie_detail(request, movie_id):
    # 1. Get current movie
    movie = Movie.objects.get(id=movie_id)
    
    # 2. Get all movies for comparison
    all_movies = Movie.objects.all()
    
    # Create a DataFrame for processing
    df = pd.DataFrame(list(all_movies.values('id', 'series_title', 'overview')))
    
    # 3. Setup TF-IDF
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['overview'])
    
    # 4. Calculate Similarity
    # This finds how similar every movie is to every other movie
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    
    # 5. Get the index of our current movie in the DataFrame
    idx = df.index[df['id'] == movie.id].tolist()[0]
    
    # 6. Get scores for all movies compared to this one
    sim_scores = list(enumerate(cosine_sim[idx]))
    
    # 7. Sort them by similarity score (highest first)
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    
    # 8. Get the top 5 (skipping the first one because it's the movie itself)
    sim_scores = sim_scores[1:6]
    movie_indices = [i[0] for i in sim_scores]
    
    # 9. Get the actual Movie objects from the DB
    recommended_ids = df['id'].iloc[movie_indices]
    recommendations = Movie.objects.filter(id__in=recommended_ids)

    return render(request, 'recommender/detail.html', {
        'movie': movie,
        'recommendations': recommendations
    })