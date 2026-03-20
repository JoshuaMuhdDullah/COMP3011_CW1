from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Movie(models.Model):
    poster_link = models.URLField(max_length=500)
    series_title = models.CharField(max_length=255)
    released_year = models.CharField(max_length=10)  # CharField handles rare cases like 'PG' in year column
    certificate = models.CharField(max_length=50, null=True, blank=True)
    runtime = models.CharField(max_length=20)
    genre = models.CharField(max_length=100)
    imdb_rating = models.FloatField()
    overview = models.TextField()
    meta_score = models.FloatField(null=True, blank=True)
    director = models.CharField(max_length=255)
    star1 = models.CharField(max_length=255)
    star2 = models.CharField(max_length=255)
    star3 = models.CharField(max_length=255)
    star4 = models.CharField(max_length=255)
    no_of_votes = models.IntegerField()
    # Gross is stored as a string to preserve the commas/formatting from your CSV
    gross = models.CharField(max_length=100, null=True, blank=True)

    watchlisted_by = models.ManyToManyField(User, related_name="watchlist", blank=True)

    def __str__(self):
        return self.series_title
    
class Comment(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} on {self.movie.series_title}"