"""Content-based recommendations from audio features and genres (pure Python, no external API)."""
import math
from collections import Counter

from django.db.models import Max

from apps.catalog.models import Song

FEATURE_FIELDS = [
    'acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence',
]
GENRE_WEIGHT = 0.25
POPULARITY_WEIGHT = 0.05

_cache = {'signature': None, 'data': {}}


def _vector(song):
    values = [getattr(song, f) for f in FEATURE_FIELDS]
    values.append(min(max(song.tempo, 0.0), 250.0) / 250.0)
    values.append(min(max((song.loudness + 60.0) / 60.0, 0.0), 1.0))
    return values


def clear_cache():
    _cache['signature'] = None
    _cache['data'] = {}


def _load():
    """Return {song_id: (vector, genre_set, popularity)}, rebuilt when the song table changes."""
    agg = Song.objects.aggregate(max_id=Max('pk'))
    signature = (Song.objects.count(), agg['max_id'])
    if _cache['signature'] != signature:
        _cache['data'] = {
            s.pk: (_vector(s), set(s.artist_genres), s.track_pop)
            for s in Song.objects.only('pk', 'artist_genres', 'track_pop', 'tempo', 'loudness', *FEATURE_FIELDS)
        }
        _cache['signature'] = signature
    return _cache['data']


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _songs_in_order(ids):
    by_id = Song.objects.in_bulk(ids)
    return [by_id[i] for i in ids if i in by_id]


def similar_songs(song, limit=10):
    """Songs closest to `song` by audio features, with a bonus for shared genres. Excludes `song`."""
    data = _load()
    if song.pk not in data:
        return []
    vector, genres, _ = data[song.pk]
    scored = []
    for pk, (other_vector, other_genres, popularity) in data.items():
        if pk == song.pk:
            continue
        union = genres | other_genres
        jaccard = len(genres & other_genres) / len(union) if union else 0.0
        scored.append((_cosine(vector, other_vector) + GENRE_WEIGHT * jaccard + POPULARITY_WEIGHT * popularity / 100, pk))
    scored.sort(reverse=True)
    return _songs_in_order([pk for _, pk in scored[:limit]])


def popular_songs(limit=10, exclude=()):
    return list(Song.objects.exclude(pk__in=exclude).order_by('-track_pop', 'track_name')[:limit])


def taste_seed_ids(user):
    """Songs that express a user's taste: liked songs plus songs in their playlists."""
    from apps.library.models import FavoriteSong, PlaylistSong

    liked = set(FavoriteSong.objects.filter(user=user).values_list('song_id', flat=True))
    in_playlists = set(PlaylistSong.objects.filter(playlist__user=user).values_list('song_id', flat=True))
    return liked | in_playlists


def recommend_for_user(user, limit=10):
    """Return (songs, personalized). Falls back to popular songs when the user has no activity yet."""
    seeds = taste_seed_ids(user)
    data = _load()
    seeds = {pk for pk in seeds if pk in data}
    if not seeds:
        return popular_songs(limit), False

    dims = len(next(iter(data.values()))[0])
    centroid = [sum(data[pk][0][i] for pk in seeds) / len(seeds) for i in range(dims)]
    genre_share = Counter(g for pk in seeds for g in data[pk][1])
    scored = []
    for pk, (vector, genres, popularity) in data.items():
        if pk in seeds:
            continue
        genre_score = sum(genre_share[g] / len(seeds) for g in genres) / len(genres) if genres else 0.0
        scored.append((_cosine(centroid, vector) + GENRE_WEIGHT * genre_score + POPULARITY_WEIGHT * popularity / 100, pk))
    scored.sort(reverse=True)
    return _songs_in_order([pk for _, pk in scored[:limit]]), True
