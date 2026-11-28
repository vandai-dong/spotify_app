"""Named moods expressed as audio-feature rules (one source of truth for browse and AI playlists)."""
from dataclasses import dataclass

from django.db.models import Q


@dataclass(frozen=True)
class Mood:
    key: str
    label: str
    query: Q


MOODS = {
    m.key: m
    for m in [
        Mood('energetic', 'Energetic', Q(energy__gte=0.7, danceability__gte=0.6)),
        Mood('party', 'Party', Q(danceability__gte=0.75, energy__gte=0.65, valence__gte=0.5)),
        Mood('happy', 'Happy', Q(valence__gte=0.7, energy__gte=0.5)),
        Mood('chill', 'Chill', Q(energy__lt=0.55, acousticness__gte=0.25)),
        Mood('focus', 'Focus', Q(speechiness__lt=0.08, energy__gte=0.3, energy__lt=0.65, liveness__lt=0.25)),
        Mood('sad', 'Sad', Q(valence__lt=0.3, energy__lt=0.6)),
    ]
}


def get_mood(key):
    """Return the Mood for `key`, or None if unknown."""
    return MOODS.get(key)
