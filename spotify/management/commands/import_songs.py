import ast
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from spotify.models import Song

DEFAULT_CSV = Path(settings.BASE_DIR) / "spotify/data/processed_global_top_songs/full_data.csv"
FLOAT_FIELDS = [
    "acousticness", "danceability", "energy", "instrumentalness", "liveness",
    "loudness", "speechiness", "tempo", "valence",
]
INT_FIELDS = ["duration_ms", "mode", "time_signature", "artist_pop", "num_followers", "track_pop"]


def parse_genres(raw):
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    return list(value) if isinstance(value, (list, tuple)) else []


class Command(BaseCommand):
    help = "Import songs from a CSV file (default: the bundled dataset). Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", nargs="?", default=str(DEFAULT_CSV))

    def handle(self, *args, **options):
        path = Path(options["csv_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        songs = []
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                data = {f: float(row[f]) for f in FLOAT_FIELDS}
                data.update({f: int(float(row[f])) for f in INT_FIELDS})
                songs.append(Song(
                    uri=row["uri"],
                    artist_names=row["artist_names"],
                    track_name=row["track_name"],
                    uri_artist=row["uri_artist"],
                    artist_genres=parse_genres(row["artist_genres"]),
                    **data,
                ))

        # ignore_conflicts makes re-running the import idempotent (uri is unique).
        Song.objects.bulk_create(songs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(songs)} songs ({Song.objects.count()} in DB)"))
