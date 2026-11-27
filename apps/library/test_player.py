import pytest
from django.urls import reverse

from apps.library.models import PlayHistory
from conftest import make_song

pytestmark = pytest.mark.django_db


@pytest.fixture
def songs(db):
    return [make_song(i, track_name=f'Track {i}', artist_names=f'Artist {i}') for i in range(1, 4)]


def play(client, song, queue=''):
    return client.post(reverse('player_play', args=[song.pk]), {'queue': queue})


def ids(*songs):
    return ','.join(str(s.pk) for s in songs)


def test_state_is_empty_initially(logged_in):
    data = logged_in.get(reverse('player_state')).json()
    assert data == {'song': None, 'playing': False, 'position': 0, 'length': 0}


def test_play_sets_queue_position_and_records_history(logged_in, user, songs):
    data = play(logged_in, songs[1], ids(*songs)).json()
    assert data['song']['id'] == songs[1].pk and data['song']['title'] == 'Track 2'
    assert data['playing'] is True and (data['position'], data['length']) == (2, 3)
    assert PlayHistory.objects.filter(user=user, song=songs[1]).count() == 1
    assert logged_in.get(reverse('player_state')).json()['song']['id'] == songs[1].pk  # persisted in the session


def test_play_without_queue_plays_just_that_song(logged_in, songs):
    data = play(logged_in, songs[0]).json()
    assert data['length'] == 1 and data['position'] == 1


def test_queue_input_is_sanitised(logged_in, songs):
    data = play(logged_in, songs[0], f'abc,,{songs[2].pk},-5,999999,{songs[2].pk}').json()
    # unknown/invalid/duplicate ids are dropped; the played song is added at the front
    assert data['length'] == 2 and data['song']['id'] == songs[0].pk


def test_queue_is_capped(logged_in, songs):
    flood = ','.join(str(i) for i in range(1, 500))
    assert play(logged_in, songs[0], flood).json()['length'] <= 100


def test_next_and_previous_wrap_around(logged_in, user, songs):
    play(logged_in, songs[2], ids(*songs))
    assert logged_in.post(reverse('player_next')).json()['song']['id'] == songs[0].pk  # wraps forward
    assert logged_in.post(reverse('player_prev')).json()['song']['id'] == songs[2].pk  # and back
    assert PlayHistory.objects.filter(user=user).count() == 3


def test_next_with_empty_queue_is_a_no_op(logged_in, user):
    assert logged_in.post(reverse('player_next')).json()['song'] is None
    assert not PlayHistory.objects.exists()


def test_toggle_pauses_and_resumes_without_recording(logged_in, user, songs):
    play(logged_in, songs[0])
    assert logged_in.post(reverse('player_toggle')).json()['playing'] is False
    assert logged_in.post(reverse('player_toggle')).json()['playing'] is True
    assert PlayHistory.objects.filter(user=user).count() == 1


def test_toggle_with_nothing_queued_stays_stopped(logged_in):
    assert logged_in.post(reverse('player_toggle')).json()['playing'] is False


def test_state_survives_a_deleted_song(logged_in, songs):
    play(logged_in, songs[0])
    songs[0].delete()
    assert logged_in.get(reverse('player_state')).json()['song'] is None


def test_play_unknown_song_404(logged_in):
    assert logged_in.post(reverse('player_play', args=[99999])).status_code == 404


@pytest.mark.parametrize('name,method', [
    ('player_state', 'get'), ('player_next', 'post'), ('player_prev', 'post'), ('player_toggle', 'post'), ('recent', 'get'),
])
def test_player_endpoints_require_login(client, name, method):
    response = getattr(client, method)(reverse(name))
    assert response.status_code == 302 and response.url.startswith(reverse('login'))


def test_mutating_endpoints_reject_get(logged_in, songs):
    for name in ('player_next', 'player_prev', 'player_toggle'):
        assert logged_in.get(reverse(name)).status_code == 405
    assert logged_in.get(reverse('player_play', args=[songs[0].pk])).status_code == 405


def test_player_state_is_per_session(client, logged_in, songs, other_user):
    from django.test import Client

    play(logged_in, songs[0])
    other = Client()
    other.force_login(other_user)
    assert other.get(reverse('player_state')).json()['song'] is None


def test_recent_page_lists_own_plays_newest_first(logged_in, user, other_user, songs):
    play(logged_in, songs[0])
    play(logged_in, songs[1])
    PlayHistory.objects.create(user=other_user, song=songs[2])
    body = logged_in.get(reverse('recent')).content.decode()
    assert body.index('Track 2') < body.index('Track 1') and 'Track 3' not in body


def test_recent_page_empty_state(logged_in):
    assert b'Nothing played yet' in logged_in.get(reverse('recent')).content


def test_player_bar_markup_only_for_authenticated_pages(logged_in, client):
    assert b'id="player-bar"' in logged_in.get(reverse('dashboard')).content
    assert b'player-bar' not in client.get(reverse('login')).content
