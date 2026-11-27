import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.catalog.models import Artist, Song
from conftest import make_song

pytestmark = pytest.mark.django_db


def test_dashboard_with_empty_database_does_not_crash(logged_in):
    # Previously random.sample(..., 7) raised ValueError on an empty/small DB.
    response = logged_in.get(reverse('dashboard'))
    assert response.status_code == 200 and b'import_songs' in response.content


def test_dashboard_shows_data_and_placeholder_without_calling_spotify(logged_in, artist, song):
    response = logged_in.get(reverse('dashboard'))
    assert b'Drake' in response.content and b'Song 1' in response.content
    assert b'placeholder.svg' in response.content


def test_dashboard_uses_cached_image_urls(logged_in, artist):
    artist.image_url = 'https://img.example/drake.jpg'
    artist.save()
    assert b'https://img.example/drake.jpg' in logged_in.get(reverse('dashboard')).content


def test_display_title_strips_suffix():
    assert make_song(1).display_title == 'Song 1'


def test_search_matches_song_and_artist(logged_in, song, artist):
    make_song(2, track_name='Other', artist_names='Someone')
    body = logged_in.get(reverse('search'), {'q': 'song 1'}).content
    assert b'Song 1' in body and b'Other' not in body
    assert b'Drake' in logged_in.get(reverse('search'), {'q': 'drak'}).content


def test_search_without_query_is_ok(logged_in):
    assert logged_in.get(reverse('search')).status_code == 200


def test_import_commands_are_idempotent_and_parse_genres():
    call_command('import_songs')
    call_command('import_songs')
    call_command('import_artists')
    assert Song.objects.count() == 1178 and Artist.objects.count() == 114
    assert isinstance(Song.objects.first().artist_genres, list)  # was stored as a raw string before


def test_fetch_images_requires_credentials(settings):
    from django.core.management.base import CommandError

    settings.SPOTIFY_CLIENT_ID = settings.SPOTIFY_SECRET_KEY = ''
    with pytest.raises(CommandError):
        call_command('fetch_images')
