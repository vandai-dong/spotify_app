"""Cache artist, song and album image URLs (and the album itself) from the Spotify Web API.

Needs SPOTIFY_CLIENT_ID / SPOTIFY_SECRET_KEY. The web app itself never calls Spotify.
Only the remote URL fields are written; images uploaded through the admin are never touched.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.catalog.models import Album, Artist, Song

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

    def _pending(self, model, options, **missing):
        """Rows still lacking data: every kwarg is a "field is missing" filter, OR-ed together."""
        qs = model.objects.all()
        if not options['force']:
            cond = Q()
            for field, value in missing.items():
                cond |= Q(**{field: value})
            qs = qs.filter(cond)
        return list(qs[:options['limit']] if options['limit'] else qs)

    def _fetch_artists(self, sp, options):
        updated = 0
        for batch in _batches(self._pending(Artist, options, image_url='')):
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
        artists = {a.uri: a for a in Artist.objects.all()}
        for batch in _batches(self._pending(Song, options, song_img_url='', album__isnull=True)):
            try:
                result = sp.tracks([s.uri for s in batch])
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f'Track batch failed: {exc}'))
                continue
            by_id = {t['id']: t for t in result.get('tracks', []) if t}
            for song in batch:
                data = by_id.get(song.uri.split(':')[-1])
                if not data:
                    continue
                album_data = data.get('album') or {}
                url = _first_image(album_data.get('images'))
                album = self._save_album(album_data, url, artists)
                fields = []
                if url and song.song_img_url != url:
                    song.song_img_url = url
                    fields.append('song_img_url')
                if album and song.album_id != album.pk:
                    song.album = album
                    fields.append('album')
                if fields:
                    song.save(update_fields=fields)
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'Songs updated: {updated} (albums known: {Album.objects.count()})'))

    def _save_album(self, data, url, artists):
        if not data.get('id'):
            return None
        first_artist = (data.get('artists') or [{}])[0].get('id')
        album, _ = Album.objects.get_or_create(uri=data['id'], defaults={'name': (data.get('name') or '')[:255]})
        changed = []
        if url and album.image_url != url:
            album.image_url = url
            changed.append('image_url')
        if album.primary_artist_id is None and first_artist in artists:
            album.primary_artist = artists[first_artist]
            changed.append('primary_artist')
        if changed:
            album.save(update_fields=changed)
        return album
