from django.core.management.base import BaseCommand
from mcp.server.fastmcp import FastMCP
from recommender.models import Movie
from recommender.views import get_personal_recs
from django.contrib.auth.models import User

# 1. Initialize FastMCP
mcp = FastMCP("MovieExpert")

# --- Define your Tools ---
@mcp.tool()
def search_movies(query: str) -> str:
    """Search for movies by title."""
    movies = Movie.objects.filter(series_title__icontains=query)[:5]
    if not movies.exists():
        return "No movies found."
    return "\n".join([f"- {m.series_title} ({m.released_year})" for m in movies])

@mcp.tool()
def get_recommendations(username: str) -> str:
    """Get personalized movie suggestions for a specific user."""
    try:
        user = User.objects.get(username=username)
        watchlist = user.watchlist.all()
        recs = get_personal_recs(watchlist)
        return "\n".join([f"Suggested: {m.series_title}" for m in recs])
    except User.DoesNotExist:
        return f"User '{username}' not found."

# --- The Django Command Class ---
class Command(BaseCommand):
    help = 'Starts the MCP server for the Movie Recommender'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting MCP Server...'))
        # 2. Run the MCP server
        # Note: MCP usually runs over stdio, so don't print extra text after this
        mcp.run()