from django.contrib import admin
from .models import Movie

# Register your models here.
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    # This controls which columns show up in the list view
    list_display = ('series_title', 'released_year', 'genre', 'imdb_rating')
    # This adds a search bar to find movies by title or director
    search_fields = ('series_title', 'director')
    # This adds a filter sidebar
    list_filter = ('genre', 'released_year')