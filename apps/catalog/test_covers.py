import io
import sys
import types

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.forms import modelform_factory
from django.urls import reverse
from PIL import Image

from apps.catalog.models import Album, Artist, Song, validate_image_size
from apps.library.models import Playlist, PlaylistSong
from apps.library.views import attach_covers
from conftest import make_album, make_song

pytestmark = pytest.mark.django_db

REMOTE = 'https://img.example/remote.jpg'


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'


def png(name='cover.png', size=(8, 8)):
    buf = io.BytesIO()
    Image.new('RGB', size, 'red').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


# --- cover_url precedence ----------------------------------------------------------------

def test_artist_cover_prefers_upload_over_remote_url(artist):
    assert artist.cover_url == ''
    artist.image_url = REMOTE
    assert artist.cover_url == REMOTE
    artist.image = png()
    artist.save()
    assert artist.cover_url.endswith('.png') and '/media/artists/' in artist.cover_url


def test_song_cover_falls_back_to_album(song):
    assert song.cover_url == ''
    song.album = make_album(image_url='https://img.example/album.jpg')
    assert song.cover_url == 'https://img.example/album.jpg'
    song.song_img_url = REMOTE
    assert song.cover_url == REMOTE
    song.image = png()
    song.save()
    assert '/media/songs/' in song.cover_url


def test_album_cover_upload_wins():
    album = make_album(image_url=REMOTE)
    assert album.cover_url == REMOTE
    album.image = png()
    album.save()
    assert '/media/albums/' in album.cover_url


def test_oversized_image_is_rejected():
    big = types.SimpleNamespace(size=3 * 1024 * 1024)
    with pytest.raises(ValidationError, match='too large'):
        validate_image_size(big)
    validate_image_size(types.SimpleNamespace(size=1024))


def test_admin_form_rejects_non_image_and_accepts_png(artist):
    form_class = modelform_factory(Artist, fields=['image'])
    bad = form_class({}, {'image': SimpleUploadedFile('x.png', b'not an image', content_type='image/png')}, instance=artist)
    assert not bad.is_valid() and 'image' in bad.errors
    good = form_class({}, {'image': png()}, instance=artist)
    assert good.is_valid()


# --- Rendering -----------------------------------------------------------------------------

def test_uploaded_image_renders_on_dashboard_and_detail(logged_in, artist):
    artist.image = png()
    artist.save()
    assert b'/media/artists/' in logged_in.get(reverse('dashboard')).content
    assert b'/media/artists/' in logged_in.get(reverse('artist_detail', args=[artist.uri])).content


def test_placeholder_everywhere_without_images(logged_in, song, artist):
    for name, args in [('dashboard', []), ('song_detail', [song.pk]), ('artist_detail', [artist.uri]), ('charts', [])]:
        assert b'placeholder.svg' in logged_in.get(reverse(name, args=args)).content, name


def test_song_rows_and_artist_lists_show_thumbnails(logged_in):
    artist = Artist.objects.create(
        artist='Ray', uri='ray', genres=[], num_of_followers=1, popularity=90, image_url='https://img.example/ray.jpg',
    )
    make_song(1, artist_names='Ray', song_img_url='https://img.example/s1.jpg', primary_artist=artist)
    body = logged_in.get(reverse('search'), {'q': 'Ray'}).content
    assert b'https://img.example/s1.jpg' in body and b'https://img.example/ray.jpg' in body
    assert b'https://img.example/ray.jpg' in logged_in.get(reverse('charts')).content


# --- Album page ----------------------------------------------------------------------------

def test_album_detail_lists_tracks_and_links_from_song(logged_in, artist):
    album = make_album(primary_artist=artist, image_url=REMOTE)
    song = make_song(1, album=album, primary_artist=artist)
    page = logged_in.get(reverse('album_detail', args=[album.uri])).content
    assert b'Album 1' in page and REMOTE.encode() in page and song.display_title.encode() in page
    assert reverse('album_detail', args=[album.uri]).encode() in logged_in.get(reverse('song_detail', args=[song.pk])).content
    assert b'Album 1' in logged_in.get(reverse('artist_detail', args=[artist.uri])).content


def test_album_detail_requires_login_and_404s(client, logged_in):
    assert logged_in.get(reverse('album_detail', args=['nope'])).status_code == 404
    client.logout()
    assert client.get(reverse('album_detail', args=['nope'])).status_code == 302


# --- Player, chat chips, playlist collage ------------------------------------------------------

def test_player_payload_uses_cover_url(logged_in):
    song = make_song(1, album=make_album(image_url='https://img.example/album.jpg'))
    data = logged_in.post(reverse('player_play', args=[song.pk])).json()
    assert data['song']['image'] == 'https://img.example/album.jpg'


def test_playlist_collage_includes_album_art_in_one_query(django_assert_num_queries, user):
    playlist = Playlist.objects.create(user=user, name='P')
    album = make_album(image_url='https://img.example/album.jpg')
    for i in range(3):
        PlaylistSong.objects.create(playlist=playlist, song=make_song(i + 1, album=album), position=i + 1)
    with django_assert_num_queries(1):
        result = attach_covers([playlist])
    assert result[0].cover_urls == ['https://img.example/album.jpg']


# --- fetch_images --------------------------------------------------------------------------------

class FakeSpotify:
    def __init__(self, *args, **kwargs):
        pass

    def artists(self, ids):
        return {'artists': [{'id': i, 'images': [{'url': f'https://img.example/artist-{i}.jpg'}]} for i in ids]}

    def tracks(self, ids):
        return {'tracks': [{
            'id': i.split(':')[-1],
            'album': {
                'id': 'ALB1', 'name': 'Great Album', 'images': [{'url': 'https://img.example/alb.jpg'}],
                'artists': [{'id': '3TVX'}],
            },
        } for i in ids]}


@pytest.fixture
def fake_spotify(monkeypatch, settings):
    settings.SPOTIFY_CLIENT_ID = settings.SPOTIFY_SECRET_KEY = 'x'
    module = types.ModuleType('spotipy')
    module.Spotify = FakeSpotify
    oauth = types.ModuleType('spotipy.oauth2')
    oauth.SpotifyClientCredentials = lambda **kw: None
    module.oauth2 = oauth
    monkeypatch.setitem(sys.modules, 'spotipy', module)
    monkeypatch.setitem(sys.modules, 'spotipy.oauth2', oauth)


def test_fetch_images_creates_albums_and_is_idempotent(fake_spotify, artist):
    one, two = make_song(1), make_song(2)
    call_command('fetch_images')
    call_command('fetch_images')
    album = Album.objects.get()
    assert (album.name, album.uri, album.image_url, album.primary_artist) == (
        'Great Album', 'ALB1', 'https://img.example/alb.jpg', artist,
    )
    for s in (one, two):
        s.refresh_from_db()
        assert s.album == album and s.song_img_url == 'https://img.example/alb.jpg'
    artist.refresh_from_db()
    assert artist.image_url == 'https://img.example/artist-3TVX.jpg'


def test_fetch_images_never_touches_uploaded_files(fake_spotify, artist):
    artist.image = png()
    artist.save()
    stored = artist.image.name
    song = make_song(1)
    song.image = png('s.png')
    song.save()
    call_command('fetch_images', '--force')
    artist.refresh_from_db()
    song.refresh_from_db()
    assert artist.image.name == stored and song.image.name.startswith('songs/')
    assert Song.objects.get().cover_url.endswith('.png')
