import json

import pytest
from django.urls import reverse

from apps.assistant import playlist_builder as pb
from apps.assistant import services
from apps.catalog.services.linking import link_catalog
from apps.library.models import Playlist
from conftest import make_song

pytestmark = pytest.mark.django_db
URL = 'build_playlist'

CALM = dict(energy=0.2, danceability=0.3, acousticness=0.9, valence=0.2, tempo=70.0, loudness=-14.0)
LOUD = dict(energy=0.95, danceability=0.9, acousticness=0.02, valence=0.8, tempo=130.0, loudness=-3.0)


@pytest.fixture
def catalog(db):
    """A small catalog with distinct moods/tempos/genres, linked so genre filters work."""
    songs = {
        'workout': make_song(1, track_name='Pump It', **LOUD, artist_genres=['pop', 'dance pop'], track_pop=90),
        'fast_rap': make_song(2, track_name='Quick Bars', **{**LOUD, 'tempo': 150.0}, artist_genres=['rap'], track_pop=80),
        'lullaby': make_song(3, track_name='Sleepy', **CALM, artist_genres=['folk'], track_pop=70),
        'k': make_song(4, track_name='Seoul Night', **LOUD, artist_genres=['k-pop'], track_pop=60),
    }
    link_catalog()
    return songs


@pytest.fixture
def no_llm(settings):
    settings.OPENAI_API_KEY = ''


@pytest.fixture
def llm(monkeypatch, settings):
    settings.OPENAI_API_KEY = 'test-key'

    class Fake:
        content = '{}'
        calls = []
        error = None

    fake = Fake()

    def complete(messages, json_mode=False):
        fake.calls.append(messages)
        if fake.error:
            raise fake.error
        return fake.content

    monkeypatch.setattr(services, 'complete', complete)
    return fake


def titles(playlist):
    return [e.song.track_name for e in playlist.playlist_songs.select_related('song')]


# --- Deterministic parsing ----------------------------------------------------------------------------

@pytest.mark.parametrize('text,mood', [
    ('upbeat workout', 'energetic'), ('something to relax', 'chill'), ('study time', 'focus'), ('sad songs', 'sad'),
    ('house party', 'party'),
])
def test_parse_detects_mood_words(catalog, text, mood):
    assert pb.parse_vibe(text).mood == mood


def test_parse_bpm_window_and_speed_words(catalog):
    f = pb.parse_vibe('run at 130 BPM')
    assert (f.tempo_min, f.tempo_max) == (122, 138)
    assert pb.parse_vibe('something fast').tempo_min == 120
    assert pb.parse_vibe('something slow').tempo_max == 100


def test_parse_matches_known_genres_longest_first(catalog):
    f = pb.parse_vibe('late night dance pop')
    assert f.genres == ('dance pop',)  # 'pop' is not matched a second time inside 'dance pop'
    assert pb.parse_vibe('some k-pop please').genres == ('k-pop',)
    assert pb.parse_vibe('rap and folk').genres == ('folk', 'rap')


def test_parse_ignores_unknown_words_and_builds_a_name(catalog):
    f = pb.parse_vibe('  qwerty!!  ')
    assert not f.has_constraints() and f.name == 'Qwerty'
    assert pb.parse_vibe('').name == 'My vibe'


def test_describe_is_human_readable(catalog):
    assert pb.parse_vibe('upbeat workout 130 bpm').describe() == 'mood: energetic, tempo 122–138 BPM'


# --- Validation: the gate between untrusted text and the ORM ----------------------------------------------

def test_validate_keeps_good_values_and_clamps(catalog):
    f = pb.validate_filter({'mood': 'Chill', 'genres': ['rap', 'folk'], 'tempo_min': 10, 'tempo_max': 999, 'energy_max': 7})
    assert f.mood == 'chill' and f.genres == ('folk', 'rap')
    assert (f.tempo_min, f.tempo_max, f.energy_max) == (40, 220, 1.0)


def test_validate_swaps_backwards_ranges(catalog):
    f = pb.validate_filter({'tempo_min': 160, 'tempo_max': 90, 'valence_min': 0.9, 'valence_max': 0.1})
    assert (f.tempo_min, f.tempo_max, f.valence_min, f.valence_max) == (90, 160, 0.1, 0.9)


@pytest.mark.parametrize('raw', [
    None, [], 'text', 5, {'mood': 5}, {'genres': 'rap'}, {'tempo_min': 'fast'}, {'energy_min': True},
])
def test_validate_ignores_wrong_types(catalog, raw):
    assert not pb.validate_filter(raw).has_constraints()


def test_validate_rejects_non_finite_numbers(catalog):
    f = pb.validate_filter(json.loads('{"tempo_min": NaN, "tempo_max": Infinity, "energy_min": -Infinity}'))
    assert not f.has_constraints()


def test_validate_drops_unknown_keys_moods_and_genres(catalog):
    f = pb.validate_filter({
        'mood': "energetic'; DROP TABLE catalog_song; --", 'genres': ["x' OR 1=1 --", 'not-a-genre', 'pk__in'],
        'pk__in': [1], 'id': 3, 'track_pop__gte': 0, '__class__': 'x',
    })
    assert not f.has_constraints()
    assert pb.build_queryset(f).count() == 4  # an empty filter is "no constraints", never a raw string in a query


def test_validate_cleans_the_name(catalog):
    assert pb.validate_filter({'name': 'Hello\n\x00World ' + 'x' * 100}).name.startswith('Hello World xxx')
    assert len(pb.validate_filter({'name': 'y' * 500}).name) == 60
    assert pb.validate_filter({'name': 5}).name == ''


# --- Selecting songs ----------------------------------------------------------------------------------------

def test_mood_and_tempo_filters(catalog):
    f = pb.validate_filter({'mood': 'energetic', 'tempo_min': 125, 'tempo_max': 135})
    assert [s.track_name for s in pb.pick_songs(f)] == ['Pump It', 'Seoul Night']


def test_genre_filter_and_popularity_order(catalog):
    assert [s.track_name for s in pb.pick_songs(pb.validate_filter({'genres': ['pop', 'rap']}))] == ['Pump It', 'Quick Bars']


def test_at_most_two_songs_per_artist_and_size_cap(db):
    for i in range(10):
        make_song(i + 1, uri_artist='spotify:artist:same', **LOUD, track_pop=100 - i)
    for i in range(40):
        make_song(100 + i, uri_artist=f'spotify:artist:a{i}', **LOUD, track_pop=50)
    link_catalog()
    picked = pb.pick_songs(pb.validate_filter({'mood': 'energetic'}))
    assert len(picked) == pb.PLAYLIST_SIZE
    assert sum(1 for s in picked if s.uri_artist == 'spotify:artist:same') == 2


# --- View -----------------------------------------------------------------------------------------------------

def build(client, text='upbeat workout 130 bpm'):
    return client.post(reverse(URL), {'prompt': text})


def test_creates_a_playlist_without_any_api_key(logged_in, user, catalog, no_llm):
    response = build(logged_in)
    playlist = Playlist.objects.get(user=user)
    assert response.status_code == 302 and response.url == reverse('playlist_detail', args=[playlist.pk])
    assert titles(playlist) == ['Pump It', 'Seoul Night']
    assert playlist.name == 'Upbeat workout 130 bpm' and 'upbeat workout 130 bpm' in playlist.description
    assert 'mood: energetic' in playlist.description and playlist.tag == 'Playlist'
    assert b'Created' in logged_in.get(response.url).content


def test_unintelligible_prompt_creates_nothing(logged_in, catalog, no_llm):
    response = build(logged_in, 'qwerty')
    assert response.status_code == 302 and response.url == reverse('chatbot')
    assert not Playlist.objects.exists()
    assert b"couldn&#x27;t tell what vibe" in logged_in.get(reverse('chatbot')).content


def test_no_matching_songs_creates_nothing(logged_in, catalog, no_llm):
    build(logged_in, 'study music')  # no catalog song has mid-level energy
    assert not Playlist.objects.exists()
    assert b'No songs in the catalog match' in logged_in.get(reverse('chatbot')).content


def test_empty_and_oversized_prompts(logged_in, catalog, settings):
    assert build(logged_in, '   ').url == reverse('chatbot')
    assert build(logged_in, 'x' * (settings.CHATBOT_MAX_PROMPT_CHARS + 1)).url == reverse('chatbot')
    assert not Playlist.objects.exists()


def test_requires_login_and_post(client, logged_in):
    assert logged_in.get(reverse(URL)).status_code == 405
    client.logout()
    response = build(client)
    assert response.status_code == 302 and response.url.startswith(reverse('login'))


def test_rate_limited_separately_from_chat(logged_in, catalog, no_llm, settings):
    settings.CHATBOT_RATE_LIMIT_PER_MINUTE = 2
    for _ in range(2):
        build(logged_in)
    third = build(logged_in)
    assert third.url == reverse('chatbot') and Playlist.objects.count() == 2
    assert b'Too many requests' in logged_in.get(reverse('chatbot')).content


def test_chatbot_page_has_the_playlist_form(logged_in):
    body = logged_in.get(reverse('chatbot')).content
    assert reverse(URL).encode() in body and b'Build a playlist' in body


# --- LLM path ---------------------------------------------------------------------------------------------------

def test_llm_filter_is_used_when_valid(logged_in, user, catalog, llm):
    llm.content = json.dumps({'mood': 'chill', 'genres': ['folk'], 'name': 'Wind down'})
    build(logged_in, 'help me unwind after work')
    playlist = Playlist.objects.get(user=user)
    assert playlist.name == 'Wind down' and titles(playlist) == ['Sleepy']


def test_llm_receives_only_the_allow_list_and_the_users_text(logged_in, catalog, llm):
    llm.content = json.dumps({'mood': 'energetic'})
    build(logged_in, 'gym time')
    system, user_msg = llm.calls[0]
    assert system['role'] == 'system' and 'energetic' in system['content'] and 'folk' in system['content']
    assert user_msg == {'role': 'user', 'content': 'gym time'}


def test_malicious_llm_output_cannot_reach_the_database(logged_in, user, catalog, llm):
    llm.content = json.dumps({'mood': "x'; DROP TABLE catalog_song;--", 'genres': ["' OR '1'='1"], 'pk__in': [1, 2]})
    build(logged_in, 'qwerty')  # nothing usable from the model *or* the keyword parser
    assert not Playlist.objects.exists()
    from apps.catalog.models import Song

    assert Song.objects.count() == 4


def test_llm_garbage_falls_back_to_keywords(logged_in, user, catalog, llm):
    llm.content = 'sure! here is your playlist'
    build(logged_in, 'upbeat workout 130 bpm')
    assert titles(Playlist.objects.get(user=user)) == ['Pump It', 'Seoul Night']


def test_llm_error_falls_back_to_keywords(logged_in, user, catalog, llm):
    llm.error = RuntimeError('boom')
    response = build(logged_in, 'upbeat workout 130 bpm')
    assert response.status_code == 302 and Playlist.objects.filter(user=user).exists()


def test_llm_with_no_usable_constraints_falls_back(logged_in, user, catalog, llm):
    llm.content = json.dumps({'mood': 'nonsense', 'tempo_min': 'fast'})
    build(logged_in, 'upbeat workout')
    assert Playlist.objects.filter(user=user, description__contains='energetic').exists()
