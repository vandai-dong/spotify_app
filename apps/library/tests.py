import pytest
from django.urls import reverse

from apps.library.models import FavoriteSong, Playlist, PlaylistSong
from conftest import make_song

pytestmark = pytest.mark.django_db


def test_liked_songs_empty_state(logged_in):
    # Previously the template tested the wrong variable so this never rendered.
    body = logged_in.get(reverse('like_song')).content
    assert b'Songs you like will appear here' in body and b'0 songs' in body


def test_toggle_favorite_adds_then_removes(logged_in, user, song):
    url = reverse('toggle_favorite', args=[song.pk])
    logged_in.post(url)
    assert FavoriteSong.objects.filter(user=user, song=song).count() == 1
    body = logged_in.get(reverse('like_song')).content
    assert b'1 song' in body and b'Song 1' in body
    logged_in.post(url)
    assert not FavoriteSong.objects.exists()


def test_toggle_favorite_is_post_only_and_login_protected(client, logged_in, song):
    assert logged_in.get(reverse('toggle_favorite', args=[song.pk])).status_code == 405
    client.logout()
    assert client.post(reverse('toggle_favorite', args=[song.pk])).status_code == 302


def test_toggle_next_rejects_external_redirect(logged_in, song):
    r = logged_in.post(reverse('toggle_favorite', args=[song.pk]), {'next': 'https://evil.example/'})
    assert r.url == reverse('like_song')


def test_playlist_lifecycle(logged_in, user, song):
    r = logged_in.post(reverse('playlist_create'), {'name': 'Road trip', 'tag': 'Playlist'})
    playlist = Playlist.objects.get(user=user)
    assert r.url == reverse('playlist_detail', args=[playlist.pk])

    add = reverse('playlist_add_song', args=[playlist.pk])
    logged_in.post(add, {'song_id': song.pk})
    logged_in.post(add, {'song_id': song.pk})  # duplicate add is a no-op
    assert PlaylistSong.objects.filter(playlist=playlist).count() == 1
    assert b'Song 1' in logged_in.get(reverse('playlist_detail', args=[playlist.pk])).content

    logged_in.post(reverse('playlist_update', args=[playlist.pk]), {'name': 'Renamed', 'description': 'd'})
    playlist.refresh_from_db()
    assert playlist.name == 'Renamed'

    logged_in.post(reverse('playlist_remove_song', args=[playlist.pk, song.pk]))
    assert not PlaylistSong.objects.exists()
    logged_in.post(reverse('playlist_delete', args=[playlist.pk]))
    assert not Playlist.objects.exists()


def test_playlist_requires_name(logged_in):
    logged_in.post(reverse('playlist_create'), {'name': '   '})
    assert not Playlist.objects.exists()


def test_playlists_are_private_to_their_owner(logged_in, other_user, song):
    theirs = Playlist.objects.create(user=other_user, name='Secret')
    assert logged_in.get(reverse('playlist_detail', args=[theirs.pk])).status_code == 404
    assert logged_in.post(reverse('playlist_delete', args=[theirs.pk])).status_code == 404
    assert logged_in.post(reverse('playlist_add_song', args=[theirs.pk]), {'song_id': song.pk}).status_code == 404
    assert Playlist.objects.filter(pk=theirs.pk).exists()
    assert b'Secret' not in logged_in.get(reverse('your_library')).content


def test_library_tag_filter(logged_in, user):
    Playlist.objects.create(user=user, name='Mix', tag='Playlist')
    Playlist.objects.create(user=user, name='Cast', tag='Podcast')
    body = logged_in.get(reverse('your_library'), {'tag': 'Podcast'}).content
    assert b'Cast' in body and b'Mix' not in body


def test_playlistsong_str_does_not_crash(user):
    # Previously referenced a non-existent `song.title`.
    song = make_song(7)
    playlist = Playlist.objects.create(user=user, name='P')
    assert 'Song 7' in str(PlaylistSong.objects.create(playlist=playlist, song=song))


def test_search_shows_like_state_and_add_to_playlist(logged_in, user, song):
    Playlist.objects.create(user=user, name='Road trip')
    FavoriteSong.objects.create(user=user, song=song)
    body = logged_in.get(reverse('search'), {'q': 'Song'}).content
    assert b'fa-solid fa-heart' in body and b'Road trip' in body
