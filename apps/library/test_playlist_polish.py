import importlib

import pytest
from django.urls import reverse

from apps.library.models import FavoriteSong, Playlist, PlaylistSong
from apps.library.views import attach_covers
from conftest import make_song

pytestmark = pytest.mark.django_db


@pytest.fixture
def playlist(user):
    return Playlist.objects.create(user=user, name='Mix')


@pytest.fixture
def three(playlist, db):
    songs = [make_song(i, track_name=f'Track {i}') for i in (1, 2, 3)]
    for song in songs:
        PlaylistSong.objects.create(playlist=playlist, song=song, position=0)
    playlist.renumber()
    return songs


def order(playlist):
    return [e.song.track_name for e in playlist.playlist_songs.select_related('song')]


def move(client, playlist, song, direction):
    return client.post(reverse('playlist_move_song', args=[playlist.pk, song.pk]), {'direction': direction})


# --- Ordering ---------------------------------------------------------------------------

def test_added_songs_are_appended_with_sequential_positions(logged_in, playlist):
    songs = [make_song(i) for i in (1, 2, 3)]
    for song in songs:
        logged_in.post(reverse('playlist_add_song', args=[playlist.pk]), {'song_id': song.pk})
    assert list(playlist.playlist_songs.values_list('position', flat=True)) == [1, 2, 3]
    assert order(playlist) == ['Song 1 (feat. X)', 'Song 2 (feat. X)', 'Song 3 (feat. X)']


def test_adding_the_same_song_twice_keeps_one_entry(logged_in, playlist, song):
    for _ in range(2):
        logged_in.post(reverse('playlist_add_song', args=[playlist.pk]), {'song_id': song.pk})
    assert playlist.playlist_songs.count() == 1


def test_move_down_and_up(logged_in, playlist, three):
    move(logged_in, playlist, three[0], 'down')
    assert order(playlist) == ['Track 2', 'Track 1', 'Track 3']
    move(logged_in, playlist, three[2], 'up')
    assert order(playlist) == ['Track 2', 'Track 3', 'Track 1']
    assert list(playlist.playlist_songs.values_list('position', flat=True)) == [1, 2, 3]


def test_moving_past_the_ends_is_a_no_op(logged_in, playlist, three):
    move(logged_in, playlist, three[0], 'up')
    move(logged_in, playlist, three[2], 'down')
    move(logged_in, playlist, three[1], 'sideways')
    assert order(playlist) == ['Track 1', 'Track 2', 'Track 3']


def test_move_unknown_song_and_foreign_playlist_404(logged_in, other_user, playlist, three):
    outsider = make_song(99)
    assert move(logged_in, playlist, outsider, 'up').status_code == 404
    theirs = Playlist.objects.create(user=other_user, name='Theirs')
    PlaylistSong.objects.create(playlist=theirs, song=outsider, position=1)
    assert logged_in.post(reverse('playlist_move_song', args=[theirs.pk, outsider.pk]), {'direction': 'down'}).status_code == 404


def test_move_is_post_only(logged_in, playlist, three):
    assert logged_in.get(reverse('playlist_move_song', args=[playlist.pk, three[0].pk])).status_code == 405


def test_remove_renumbers_without_gaps(logged_in, playlist, three):
    logged_in.post(reverse('playlist_remove_song', args=[playlist.pk, three[1].pk]))
    assert list(playlist.playlist_songs.values_list('position', flat=True)) == [1, 2]
    assert order(playlist) == ['Track 1', 'Track 3']


def test_detail_page_shows_songs_in_position_order(logged_in, playlist, three):
    move(logged_in, playlist, three[2], 'up')
    body = logged_in.get(reverse('playlist_detail', args=[playlist.pk])).content.decode()
    assert body.index('Track 1') < body.index('Track 3') < body.index('Track 2')


def test_migration_backfill_orders_existing_rows_by_added_time(user):
    module = importlib.import_module('apps.library.migrations.0003_playlist_position_and_share_token')
    from django.apps import apps

    playlist = Playlist.objects.create(user=user, name='Old')
    first, second = make_song(1), make_song(2)
    a = PlaylistSong.objects.create(playlist=playlist, song=first, position=0)
    b = PlaylistSong.objects.create(playlist=playlist, song=second, position=0)
    module.backfill_positions(apps, None)
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.position, b.position) == (1, 2)


# --- Covers ------------------------------------------------------------------------------

def test_covers_use_up_to_four_distinct_images_in_one_query(django_assert_num_queries, user):
    playlists = [Playlist.objects.create(user=user, name=f'P{i}') for i in range(3)]
    for i in range(6):
        song = make_song(i + 1, song_img_url=f'https://img.example/{i % 5}.jpg')
        PlaylistSong.objects.create(playlist=playlists[0], song=song, position=i + 1)
    make_song(50)
    with django_assert_num_queries(1):
        result = attach_covers(playlists)
    assert len(result[0].cover_urls) == 4 and len(set(result[0].cover_urls)) == 4
    assert result[1].cover_urls == []


def test_library_and_detail_render_cover_images(logged_in, user, playlist):
    song = make_song(1, song_img_url='https://img.example/cover.jpg')
    PlaylistSong.objects.create(playlist=playlist, song=song, position=1)
    assert b'https://img.example/cover.jpg' in logged_in.get(reverse('your_library')).content
    assert b'https://img.example/cover.jpg' in logged_in.get(reverse('playlist_detail', args=[playlist.pk])).content


def test_playlist_without_images_shows_placeholder_icon(logged_in, playlist):
    assert b'cover-empty' in logged_in.get(reverse('your_library')).content


# --- Sharing -----------------------------------------------------------------------------

def share(client, playlist, action):
    return client.post(reverse('playlist_share', args=[playlist.pk]), {'action': action})


def test_enable_sharing_exposes_a_public_read_only_page(logged_in, client, user, playlist, three):
    share(logged_in, playlist, 'enable')
    playlist.refresh_from_db()
    assert playlist.share_token
    assert playlist.share_token in logged_in.get(reverse('playlist_detail', args=[playlist.pk])).content.decode()

    anonymous = type(client)()  # fresh, logged-out client
    response = anonymous.get(reverse('shared_playlist', args=[playlist.share_token]))
    body = response.content.decode()
    assert response.status_code == 200 and 'Mix' in body and 'Track 1' in body and 'By Alice' in body
    assert 'noindex' in body


def test_shared_page_does_not_leak_owner_details_or_controls(logged_in, client, user, playlist, three):
    share(logged_in, playlist, 'enable')
    playlist.refresh_from_db()
    body = type(client)().get(reverse('shared_playlist', args=[playlist.share_token])).content.decode()
    assert user.email not in body and 'csrfmiddlewaretoken' not in body and 'Delete' not in body


def test_disable_sharing_revokes_the_link(logged_in, client, playlist):
    share(logged_in, playlist, 'enable')
    playlist.refresh_from_db()
    token = playlist.share_token
    share(logged_in, playlist, 'disable')
    playlist.refresh_from_db()
    assert playlist.share_token is None
    assert type(client)().get(reverse('shared_playlist', args=[token])).status_code == 404


def test_re_enabling_issues_a_new_token(logged_in, playlist):
    share(logged_in, playlist, 'enable')
    playlist.refresh_from_db()
    old = playlist.share_token
    share(logged_in, playlist, 'disable')
    share(logged_in, playlist, 'enable')
    playlist.refresh_from_db()
    assert playlist.share_token and playlist.share_token != old


def test_only_the_owner_can_change_sharing(logged_in, other_user, user):
    theirs = Playlist.objects.create(user=other_user, name='Theirs')
    assert share(logged_in, theirs, 'enable').status_code == 404
    theirs.refresh_from_db()
    assert theirs.share_token is None


def test_unknown_action_and_methods(logged_in, playlist):
    share(logged_in, playlist, 'explode')
    playlist.refresh_from_db()
    assert playlist.share_token is None
    assert logged_in.get(reverse('playlist_share', args=[playlist.pk])).status_code == 405


def test_unknown_token_404_and_sharing_requires_login(client, playlist):
    assert client.get(reverse('shared_playlist', args=['nope'])).status_code == 404
    assert client.post(reverse('playlist_share', args=[playlist.pk]), {'action': 'enable'}).status_code == 302


def test_empty_shared_playlist_renders(logged_in, client, playlist):
    share(logged_in, playlist, 'enable')
    playlist.refresh_from_db()
    assert b'This crate is empty' in type(client)().get(reverse('shared_playlist', args=[playlist.share_token])).content


# --- Pagination --------------------------------------------------------------------------

def test_library_paginates_playlists(logged_in, user):
    for i in range(25):
        Playlist.objects.create(user=user, name=f'List {i:02d}')
    assert b'Page 1 of 2' in logged_in.get(reverse('your_library')).content
    page2 = logged_in.get(reverse('your_library'), {'page': 2}).content
    assert b'Page 2 of 2' in page2


def test_library_pagination_keeps_tag_filter(logged_in, user):
    for i in range(25):
        Playlist.objects.create(user=user, name=f'Cast {i}', tag='Podcast')
    assert b'tag=Podcast&amp;page=2' in logged_in.get(reverse('your_library'), {'tag': 'Podcast'}).content


def test_liked_songs_paginate_with_continuous_numbering(logged_in, user):
    for i in range(30):
        FavoriteSong.objects.create(user=user, song=make_song(i + 1))
    page1 = logged_in.get(reverse('like_song')).content
    assert b'30 songs' in page1 and b'Page 1 of 2' in page1
    page2 = logged_in.get(reverse('like_song'), {'page': 2}).content.decode()
    assert '>26<' in page2 and '>30<' in page2


def test_search_paginates_and_keeps_query(logged_in):
    for i in range(30):
        make_song(i + 1, track_name=f'Needle {i}')
    page1 = logged_in.get(reverse('search'), {'q': 'Needle'}).content
    assert b'(30)' in page1 and b'q=Needle&amp;page=2' in page1
    page2 = logged_in.get(reverse('search'), {'q': 'Needle', 'page': 2}).content.decode()
    assert '>26<' in page2


def test_search_without_results_or_query_still_renders(logged_in):
    assert b'No songs found' in logged_in.get(reverse('search'), {'q': 'zzzz'}).content
    assert logged_in.get(reverse('search')).status_code == 200


def test_new_playlist_form_defaults_to_the_playlist_tag(logged_in):
    body = logged_in.get(reverse('your_library')).content.decode()
    assert '<option value="Playlist" selected>' in body
