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
    assert Song.objects.count() == 1178 and Artist.objects.count() == 515  # 114 curated + derived, 71 overlap
    assert isinstance(Song.objects.first().artist_genres, list)  # was stored as a raw string before


def test_fetch_images_requires_credentials(settings):
    from django.core.management.base import CommandError

    settings.SPOTIFY_CLIENT_ID = settings.SPOTIFY_SECRET_KEY = ''
    with pytest.raises(CommandError):
        call_command('fetch_images')


# --- Linking songs to artists / genres --------------------------------------

def test_import_links_every_song_to_an_artist_and_genres():
    from apps.catalog.models import Genre

    call_command('import_songs')
    assert not Song.objects.filter(primary_artist__isnull=True).exists()
    assert Artist.objects.count() == 472  # 71 from artists.csv + derived from song data
    assert Genre.objects.count() == 375
    assert not Song.objects.filter(genres__isnull=True).exists()


def test_linking_is_idempotent():
    from apps.catalog.models import Genre

    call_command('import_songs')
    counts = (Artist.objects.count(), Genre.objects.count(), Song.genres.through.objects.count())
    call_command('import_songs')
    assert counts == (Artist.objects.count(), Genre.objects.count(), Song.genres.through.objects.count())


@pytest.mark.parametrize('order', [('import_artists', 'import_songs'), ('import_songs', 'import_artists')])
def test_curated_artist_data_wins_in_either_import_order(order):
    for name in order:
        call_command(name)
    drake = Artist.objects.get(uri='3TVXtAsR1Inumwj472S9r4')
    assert drake.artist == 'Drake' and drake.popularity == 96  # from artists.csv, not derived from a song row
    assert drake.songs.exists()


def test_derived_artist_uses_first_listed_name():
    from apps.catalog.services.linking import link_catalog

    make_song(5, artist_names='Lead Singer, Guest', uri_artist='spotify:artist:abc123', num_followers=3_000_000_000)
    link_catalog()
    artist = Artist.objects.get(uri='abc123')
    assert artist.artist == 'Lead Singer' and artist.num_of_followers == 2**31 - 1  # clamped to the int column


# --- Detail pages -------------------------------------------------------------

def test_song_detail_shows_metadata_and_audio_profile(logged_in):
    from apps.catalog.services.linking import link_catalog

    song = make_song(1, tempo=127.6, duration_ms=185000, artist_genres=['pop', 'dance pop'])
    link_catalog()
    body = logged_in.get(reverse('song_detail', args=[song.pk])).content.decode()
    assert 'Song 1 (feat. X)' in body and '3:05' in body and '128 BPM' in body and 'Major' in body
    assert 'dance pop' in body and 'Danceability' in body
    assert '/artists/1' in body  # links to the derived artist (uri_artist spotify:artist:1)


def test_song_detail_works_without_linked_artist(logged_in, song):
    assert logged_in.get(reverse('song_detail', args=[song.pk])).status_code == 200


def test_song_detail_reflects_like_state(logged_in, user, song):
    from apps.library.models import FavoriteSong

    assert b'Like' in logged_in.get(reverse('song_detail', args=[song.pk])).content
    FavoriteSong.objects.create(user=user, song=song)
    assert b'Liked' in logged_in.get(reverse('song_detail', args=[song.pk])).content


def test_artist_detail_lists_their_songs_by_popularity(logged_in):
    from apps.catalog.services.linking import link_catalog

    make_song(1, track_name='Low', uri_artist='spotify:artist:zzz', track_pop=10, artist_names='Zed')
    make_song(2, track_name='High', uri_artist='spotify:artist:zzz', track_pop=90, artist_names='Zed')
    make_song(3, track_name='Other', uri_artist='spotify:artist:other')
    link_catalog()
    body = logged_in.get(reverse('artist_detail', args=['zzz'])).content.decode()
    assert body.index('High') < body.index('Low') and 'Other' not in body


@pytest.mark.parametrize('name,args', [('song_detail', [999999]), ('artist_detail', ['nope'])])
def test_detail_pages_404_for_unknown_ids(logged_in, name, args):
    assert logged_in.get(reverse(name, args=args)).status_code == 404


@pytest.mark.parametrize('name,args', [('song_detail', [1]), ('artist_detail', ['abc'])])
def test_detail_pages_require_login(client, name, args):
    response = client.get(reverse(name, args=args))
    assert response.status_code == 302 and response.url.startswith(reverse('login'))


def test_dashboard_cards_link_to_detail_pages(logged_in, artist, song):
    body = logged_in.get(reverse('dashboard')).content.decode()
    assert reverse('artist_detail', args=[artist.uri]) in body and reverse('song_detail', args=[song.pk]) in body
