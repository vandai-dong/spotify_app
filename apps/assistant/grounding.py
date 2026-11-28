"""Pick catalog songs to offer the model, so it only recommends songs that exist in the database."""
import re
from functools import reduce

from django.db.models import Q

from apps.catalog.models import Song
from apps.catalog.services import recommend
from apps.catalog.services.moods import MOODS

MOOD_KEYWORDS = {
    'energetic': {'energetic', 'workout', 'gym', 'running', 'hype', 'pump'},
    'party': {'party', 'dance', 'dancing', 'club'},
    'happy': {'happy', 'upbeat', 'cheerful', 'fun', 'sunny', 'feelgood'},
    'chill': {'chill', 'relax', 'relaxing', 'calm', 'mellow', 'sleep', 'unwind'},
    'sad': {'sad', 'melancholy', 'heartbreak', 'cry', 'blue'},
    'focus': {'focus', 'study', 'studying', 'concentrate', 'reading'},
}
STOPWORDS = {
    'the', 'and', 'for', 'with', 'some', 'any', 'can', 'you', 'give', 'recommend', 'suggest', 'songs', 'song', 'music',
    'play', 'like', 'want', 'need', 'something', 'about', 'that', 'this', 'what', 'good', 'best', 'please', 'tracks',
}
MAX_TOKENS = 6
KEYWORD_SONGS = 8
MOOD_SONGS = 6
MAX_MOODS = 2
PERSONAL_SONGS = 4


def tokenize(prompt):
    words = re.findall(r"[a-z0-9']+", prompt.lower())
    seen, tokens = set(), []
    for word in words:
        if len(word) >= 3 and word not in STOPWORDS and word not in seen:
            seen.add(word)
            tokens.append(word)
    return tokens[:MAX_TOKENS]


def find_candidates(user, prompt, limit):
    """Return up to `limit` distinct songs relevant to `prompt` and the user's taste."""
    tokens = tokenize(prompt)
    found = []

    def add(songs):
        for song in songs:
            if song.pk not in {s.pk for s in found}:
                found.append(song)

    if tokens:
        match = reduce(lambda a, b: a | b, (Q(track_name__icontains=t) | Q(artist_names__icontains=t) for t in tokens))
        add(Song.objects.filter(match).order_by('-track_pop', 'track_name')[:KEYWORD_SONGS])

    moods = [key for key, words in MOOD_KEYWORDS.items() if words & set(tokens)][:MAX_MOODS]
    for key in moods:
        add(Song.objects.filter(MOODS[key].query).order_by('-track_pop', 'track_name')[:MOOD_SONGS])

    personal, personalized = recommend.recommend_for_user(user, PERSONAL_SONGS)
    if personalized:
        add(personal)

    if not found:
        add(recommend.popular_songs(KEYWORD_SONGS))
    return found[:limit]


def format_candidates(songs):
    """One line per song: `id | title | artist | genres`, with whitespace flattened (titles are data, not prose)."""
    def clean(text):
        return ' '.join(str(text).split())

    return '\n'.join(
        f"{s.pk} | {clean(s.display_title)} | {clean(s.artist_names)} | {clean(', '.join(s.artist_genres[:3]))}"
        for s in songs
    )
