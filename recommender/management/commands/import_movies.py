import csv
from django.core.management.base import BaseCommand
from recommender.models import Movie

class Command(BaseCommand):
    help = 'Import movies from IMDB CSV'

    def handle(self, *args, **kwargs):
        # Path to your CSV file
        path = 'data/imdb_top_1000.csv'
        
        with open(path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) # Skip the header row
            
            for row in reader:
                # Based on your example record:
                # row[0]=Poster, row[1]=Title, row[2]=Year, row[3]=Cert, row[4]=Runtime...
                
                Movie.objects.get_or_create(
                    poster_link=row[0],
                    series_title=row[1],
                    released_year=row[2],
                    certificate=row[3],
                    runtime=row[4],
                    genre=row[5],
                    imdb_rating=float(row[6]),
                    overview=row[7],
                    meta_score=float(row[8]) if row[8] else None,
                    director=row[9],
                    star1=row[10],
                    star2=row[11],
                    star3=row[12],
                    star4=row[13],
                    no_of_votes=int(row[14]),
                    gross=row[15]
                )
        self.stdout.write(self.style.SUCCESS('Successfully imported all movies!'))