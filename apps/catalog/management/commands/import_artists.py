import ast
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Artist

DEFAULT_CSV = Path(settings.BASE_DIR) / "data/artists/artists.csv"


class Command(BaseCommand):
    help = "Import artists from a CSV file (default: the bundled dataset). Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", nargs="?", default=str(DEFAULT_CSV))

    def handle(self, *args, **options):
        path = Path(options["csv_file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        count = 0
        with path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                Artist.objects.update_or_create(
                    uri=row["uri"],
                    defaults={
                        "artist": row["artist"],
                        "genres": ast.literal_eval(row["genres"]),
                        "num_of_followers": int(float(row["num_of_followers"])),
                        "popularity": int(float(row["popularity"])),
                    },
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} artists"))
