import pytest
from django.urls import reverse

from apps.catalog.models import Song
from apps.catalog.services import recommend
from apps.catalog.services.linking import link_catalog
from apps.catalog.services.moods import MOODS, get_mood
from apps.library.models import FavoriteSong, Playlist, PlaylistSong
from conftest import make_song

pytestmark = pytest.mark.django_db

CALM = dict(energy=0.2, danceability=0.3, acousticness=0.9, valence=0.2, tempo=70.0, loudness=-14.0)
LOUD = dict(energy=0.95, danceability=0.9, acousticness=0.02, valence=0.8, tempo=150.0, loudness=-3.0)


# --- Moods ------------------------------------------------------------------------

def test_mood_rules_pick_the_right_songs():
    calm = make_song(1, **CALM)
    loud = make_song(2, **LOUD)
    assert list(Song.objects.filter(MOODS['chill'].query)) == [calm]
    assert set(Song.objects.filter(MOODS['energetic'].query)) == {loud}
    assert set(Song.objects.filter(MOODS['party'].query)) == {loud}
    assert set(Song.objects.filter(MOODS['sad'].query)) == {calm}


def test_get_mood_unknown_is_none():
    assert get_mood('nope') is None and get_mood('chill').label == 'Chill'


# --- Recommender ---------------------------------------------------------------------

def test_similar_songs_excludes_self_and_ranks_by_closeness():
    base = make_song(1, **CALM, artist_genres=['folk'])
    near = make_song(2, **{**CALM, 'energy': 0.25}, artist_genres=['folk'])
    far = make_song(3, **LOUD, artist_genres=['edm'])
    result = recommend.similar_songs(base, 10)
    assert base not in result and result == [near, far]


def test_shared_genres_break_ties():
    base = make_song(1, **CALM, artist_genres=['folk'])
    same_genre = make_song(2, **CALM, artist_genres=['folk'])
    other_genre = make_song(3, **CALM, artist_genres=['metal'])
    assert recommend.similar_songs(base, 2) == [same_genre, other_genre]


def test_recommender_cache_picks_up_new_songs():
    base = make_song(1, **CALM)
    assert recommend.similar_songs(base, 10) == []
    extra = make_song(2, **CALM)
    assert recommend.similar_songs(base, 10) == [extra]


def test_recommend_falls_back_to_popular_without_activity(user):
    low = make_song(1, track_pop=10)
    high = make_song(2, track_pop=99)
    songs, personalized = recommend.recommend_for_user(user, 5)
    assert personalized is False and songs == [high, low]


def test_recommend_uses_liked_songs_and_excludes_them(user):
    liked = make_song(1, **CALM, artist_genres=['folk'])
    calm_other = make_song(2, **CALM, artist_genres=['folk'], track_pop=10)
    loud_hit = make_song(3, **LOUD, artist_genres=['edm'], track_pop=90)
    FavoriteSong.objects.create(user=user, song=liked)
    songs, personalized = recommend.recommend_for_user(user, 5)
    assert personalized is True
    assert liked not in songs and songs == [calm_other, loud_hit]


def test_playlist_songs_count_as_taste(user):
    seed = make_song(1, **LOUD, artist_genres=['edm'])
    close = make_song(2, **LOUD, artist_genres=['edm'])
    make_song(3, **CALM, artist_genres=['folk'])
    PlaylistSong.objects.create(playlist=Playlist.objects.create(user=user, name='P'), song=seed)
    songs, personalized = recommend.recommend_for_user(user, 1)
    assert personalized and songs == [close]


def test_recommendations_are_per_user(user, other_user):
    liked = make_song(1, **CALM)
    make_song(2, **LOUD)
    FavoriteSong.objects.create(user=other_user, song=liked)
    assert recommend.recommend_for_user(user, 5)[1] is False


# --- Pages -------------------------------------------------------------------------------

def test_dashboard_heading_reflects_personalization(logged_in, user):
    song = make_song(1)
    make_song(2)
    assert b'Popular right now' in logged_in.get(reverse('dashboard')).content
    FavoriteSong.objects.create(user=user, song=song)
    assert b'Made for you' in logged_in.get(reverse('dashboard')).content


def test_song_detail_lists_similar_songs(logged_in):
    base = make_song(1, **CALM)
    make_song(2, **CALM, track_name='Neighbour')
    assert b'More like this' in logged_in.get(reverse('song_detail', args=[base.pk])).content
    assert b'Neighbour' in logged_in.get(reverse('song_detail', args=[base.pk])).content


def test_browse_without_filters_prompts(logged_in):
    body = logged_in.get(reverse('browse')).content
    assert b'Pick a mood or a genre' in body


def test_browse_filters_by_mood_and_genre(logged_in):
    make_song(1, **CALM, track_name='Quiet', artist_genres=['folk'])
    make_song(2, **LOUD, track_name='Banger', artist_genres=['edm'])
    make_song(3, **CALM, track_name='Calm Edm', artist_genres=['edm'])
    link_catalog()
    mood = logged_in.get(reverse('browse'), {'mood': 'chill'}).content
    assert b'Quiet' in mood and b'Calm Edm' in mood and b'Banger' not in mood
    genre = logged_in.get(reverse('browse'), {'genre': 'edm'}).content
    assert b'Banger' in genre and b'Quiet' not in genre
    both = logged_in.get(reverse('browse'), {'genre': 'edm', 'mood': 'chill'}).content
    assert b'Calm Edm' in both and b'Banger' not in both and b'Quiet' not in both


def test_browse_ignores_unknown_mood_and_handles_unknown_genre(logged_in, song):
    link_catalog()
    assert b'Pick a mood or a genre' in logged_in.get(reverse('browse'), {'mood': 'bogus'}).content
    assert b'Nothing matches' in logged_in.get(reverse('browse'), {'genre': 'no-such-genre'}).content


def test_browse_paginates_and_clamps_bad_pages(logged_in):
    for i in range(30):
        make_song(i + 1, **CALM)
    link_catalog()
    page1 = logged_in.get(reverse('browse'), {'mood': 'chill'}).content
    assert b'Page 1 of 2' in page1 and b'mood=chill&amp;page=2' in page1
    assert b'Page 2 of 2' in logged_in.get(reverse('browse'), {'mood': 'chill', 'page': 2}).content
    assert b'Page 2 of 2' in logged_in.get(reverse('browse'), {'mood': 'chill', 'page': 99}).content
    assert b'Page 1 of 2' in logged_in.get(reverse('browse'), {'mood': 'chill', 'page': 'abc'}).content


def test_charts_rank_by_popularity_with_filters(logged_in):
    make_song(1, track_name='Slow Hit', tempo=80.0, track_pop=95, artist_genres=['pop'])
    make_song(2, track_name='Fast Hit', tempo=160.0, track_pop=90, artist_genres=['pop'])
    make_song(3, track_name='Deep Cut', tempo=120.0, track_pop=10, artist_genres=['rap'])
    link_catalog()
    body = logged_in.get(reverse('charts')).content.decode()
    assert body.index('Slow Hit') < body.index('Fast Hit') < body.index('Deep Cut')
    fast = logged_in.get(reverse('charts'), {'tempo_min': 100}).content.decode()
    assert 'Slow Hit' not in fast and 'Fast Hit' in fast and 'Deep Cut' in fast
    window = logged_in.get(reverse('charts'), {'tempo_min': 100, 'tempo_max': 130, 'genre': 'rap'}).content.decode()
    assert 'Deep Cut' in window and 'Fast Hit' not in window


def test_charts_ignore_invalid_tempo_and_show_global_ranks(logged_in):
    for i in range(30):
        make_song(i + 1, track_pop=100 - i)
    link_catalog()
    assert logged_in.get(reverse('charts'), {'tempo_min': 'fast'}).status_code == 200
    page2 = logged_in.get(reverse('charts'), {'page': 2}).content.decode()
    assert '>26<' in page2  # ranks continue across pages


def test_charts_with_empty_catalog(logged_in):
    body = logged_in.get(reverse('charts')).content
    assert b'No songs match' in body


@pytest.mark.parametrize('name', ['browse', 'charts'])
def test_discovery_pages_require_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302 and response.url.startswith(reverse('login'))
