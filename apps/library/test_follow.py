import pytest
from django.urls import reverse

from apps.library.models import FollowedArtist
from conftest import make_song

pytestmark = pytest.mark.django_db


def test_follow_toggles_on_and_off(logged_in, user, artist):
    url = reverse('toggle_follow', args=[artist.uri])
    response = logged_in.post(url)
    assert response.status_code == 302 and response.url == reverse('artist_detail', args=[artist.uri])
    assert FollowedArtist.objects.filter(user=user, artist=artist).count() == 1
    logged_in.post(url)
    assert not FollowedArtist.objects.exists()


def test_follow_is_post_only_login_protected_and_404s(client, logged_in, artist):
    assert logged_in.get(reverse('toggle_follow', args=[artist.uri])).status_code == 405
    assert logged_in.post(reverse('toggle_follow', args=['missing'])).status_code == 404
    client.logout()
    assert client.post(reverse('toggle_follow', args=[artist.uri])).status_code == 302
    assert not FollowedArtist.objects.exists()


def test_follow_rejects_external_next(logged_in, artist):
    r = logged_in.post(reverse('toggle_follow', args=[artist.uri]), {'next': 'https://evil.example/'})
    assert r.url == reverse('artist_detail', args=[artist.uri])


def test_artist_page_shows_follow_state(logged_in, user, artist):
    assert b'Follow' in logged_in.get(reverse('artist_detail', args=[artist.uri])).content
    FollowedArtist.objects.create(user=user, artist=artist)
    assert b'Following' in logged_in.get(reverse('artist_detail', args=[artist.uri])).content


def test_followed_artists_listed_in_library_and_dashboard(logged_in, user, artist):
    FollowedArtist.objects.create(user=user, artist=artist)
    assert b'Followed artists' in logged_in.get(reverse('your_library')).content
    assert b'Drake' in logged_in.get(reverse('your_library'), {'tag': 'Artist'}).content
    assert b'Your artists' in logged_in.get(reverse('dashboard')).content


def test_library_artist_tab_empty_state_and_hidden_in_other_tabs(logged_in, user, artist):
    assert b'not following any artists' in logged_in.get(reverse('your_library'), {'tag': 'Artist'}).content
    FollowedArtist.objects.create(user=user, artist=artist)
    assert b'Followed artists' not in logged_in.get(reverse('your_library'), {'tag': 'Podcast'}).content


def test_follows_are_per_user(logged_in, other_user, artist):
    FollowedArtist.objects.create(user=other_user, artist=artist)
    assert b'Your artists' not in logged_in.get(reverse('dashboard')).content
    assert b'Following' not in logged_in.get(reverse('artist_detail', args=[artist.uri])).content


def test_dashboard_without_follows_has_no_row(logged_in):
    assert b'Your artists' not in logged_in.get(reverse('dashboard')).content


def test_deleting_artist_or_user_removes_follows(user, artist):
    FollowedArtist.objects.create(user=user, artist=artist)
    artist.delete()
    assert not FollowedArtist.objects.exists()


def test_song_rows_have_play_buttons(logged_in):
    song = make_song(1)
    assert b'js-play' in logged_in.get(reverse('search'), {'q': song.track_name[:4]}).content
