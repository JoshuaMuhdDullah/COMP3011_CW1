### Project Overview
Movie Recommender app that utilises a data set of imdb movies to 
allow users to browse and watchlists movies, suggesting recommended 
movies. Suggestions may be movie based or user specific with their 
watchlist.

### Setting up the program
```
git clone https://github.com/JoshuaMuhdDullah/COMP3011_CW1.git
cd COMP3011_CW1

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
```

### Usage
Running the standard web interface.
python manage.py runserver
The app will now be accessible at http://127.0.0.1:8000/

Running the MCP server
python manage.py run_mcp
Tools Exposed: ```search_movie, get_recommendations.```

### API Documentation
Can be accessed from: [here](API_Documentation.pdf)
