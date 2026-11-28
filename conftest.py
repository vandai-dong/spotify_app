import pytest
from django.core.cache import cache

from apps.accounts.models import User
from apps.catalog.models import Artist, Song


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='alice', email='alice@example.com', password='correct-horse-9', display_name='Alice',
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='bob', email='bob@example.com', password='correct-horse-9')


@pytest.fixture
def logged_in(client, user):
    client.force_login(user)
    return client


def make_song(n=1, **overrides):
    data = dict(
        uri=f'spotify:track:{n}', artist_names=f'Artist {n}', track_name=f'Song {n} (feat. X)',
        acousticness=0.1, danceability=0.5, duration_ms=200000, energy=0.5, instrumentalness=0.0,
        liveness=0.1, loudness=-5.0, mode=1, speechiness=0.05, tempo=120.0, time_signature=4,
        valence=0.5, uri_artist=f'spotify:artist:{n}', artist_pop=50, num_followers=1000,
        artist_genres=['pop'], track_pop=50,
    )
    data.update(overrides)
    return Song.objects.create(**data)


@pytest.fixture
def song(db):
    return make_song(1)


@pytest.fixture
def artist(db):
    return Artist.objects.create(artist='Drake', uri='3TVX', genres=['rap'], num_of_followers=10, popularity=90)


@pytest.fixture(autouse=True)
def _clear_recommender_cache():
    from apps.catalog.services import recommend

    recommend.clear_cache()
    yield
    recommend.clear_cache()
