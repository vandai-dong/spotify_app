"""Cache artist and album-cover URLs from the Spotify Web API in the database.

Needs SPOTIFY_CLIENT_ID / SPOTIFY_SECRET_KEY. The web app itself never calls Spotify.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Artist, Song

BATCH_SIZE = 50


def _first_image(images):
    return images[0]['url'] if images else ''


def _batches(items, size=BATCH_SIZE):
    for i in range(0, len(items), size):
        yield items[i:i + size]


class Command(BaseCommand):
    help = "Fetch and store artist/song image URLs from Spotify (only rows still missing one)."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Refetch rows that already have an image')
        parser.add_argument('--limit', type=int, default=None, help='Max rows per model (useful for a quick test)')

    def handle(self, *args, **options):
        if not (settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_SECRET_KEY):
            raise CommandError('Set SPOTIFY_CLIENT_ID and SPOTIFY_SECRET_KEY in your environment / .env first.')

        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_SECRET_KEY,
            ),
            requests_timeout=15,
            retries=3,
        )
        self._fetch_artists(sp, options)
        self._fetch_songs(sp, options)

    def _pending(self, model, field, options):
        qs = model.objects.all() if options['force'] else model.objects.filter(**{field: ''})
        return list(qs[:options['limit']] if options['limit'] else qs)

    def _fetch_artists(self, sp, options):
        updated = 0
        for batch in _batches(self._pending(Artist, 'image_url', options)):
            try:
                result = sp.artists([a.uri for a in batch])
            except Exception as exc:  # network / auth / API restriction
                self.stderr.write(self.style.WARNING(f'Artist batch failed: {exc}'))
                continue
            by_id = {a['id']: a for a in result.get('artists', []) if a}
            for artist in batch:
                data = by_id.get(artist.uri.split(':')[-1])
                if data and (url := _first_image(data.get('images'))):
                    artist.image_url = url
                    artist.save(update_fields=['image_url'])
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'Artists updated: {updated}'))

    def _fetch_songs(self, sp, options):
        updated = 0
        for batch in _batches(self._pending(Song, 'song_img_url', options)):
            try:
                result = sp.tracks([s.uri for s in batch])
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f'Track batch failed: {exc}'))
                continue
            by_id = {t['id']: t for t in result.get('tracks', []) if t}
            for song in batch:
                data = by_id.get(song.uri.split(':')[-1])
                if data and (url := _first_image(data.get('album', {}).get('images'))):
                    song.song_img_url = url
                    song.save(update_fields=['song_img_url'])
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'Songs updated: {updated}'))
