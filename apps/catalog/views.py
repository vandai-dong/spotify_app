from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .helpers import mark_liked, user_playlists
from .models import Artist, Song

DASHBOARD_ITEMS = 7
SEARCH_LIMIT = 50


@login_required
def dashboard(request):
    top_artists = Artist.objects.order_by('?')[:DASHBOARD_ITEMS]
    top_songs = Song.objects.order_by('?')[:DASHBOARD_ITEMS]
    return render(request, 'catalog/dashboard.html', {'top_artists': top_artists, 'top_songs': top_songs})


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    songs, artists = [], []
    if query:
        songs = Song.objects.filter(Q(track_name__icontains=query) | Q(artist_names__icontains=query))[:SEARCH_LIMIT]
        artists = Artist.objects.filter(artist__icontains=query)[:SEARCH_LIMIT]
    return render(request, 'catalog/search.html', {
        'query': query,
        'songs': mark_liked(request.user, songs),
        'artists': artists,
        'playlists': user_playlists(request.user),
    })


AUDIO_FEATURES = [
    ('danceability', 'Danceability'),
    ('energy', 'Energy'),
    ('valence', 'Positivity'),
    ('acousticness', 'Acousticness'),
    ('instrumentalness', 'Instrumentalness'),
    ('liveness', 'Liveness'),
    ('speechiness', 'Speechiness'),
]
ARTIST_SONG_LIMIT = 100


def _format_duration(ms):
    minutes, seconds = divmod(round(ms / 1000), 60)
    return f"{minutes}:{seconds:02d}"


@login_required
def song_detail(request, song_id):
    song = get_object_or_404(Song.objects.select_related('primary_artist').prefetch_related('genres'), pk=song_id)
    features = [
        {'label': label, 'percent': round(max(0.0, min(1.0, getattr(song, field))) * 100)}
        for field, label in AUDIO_FEATURES
    ]
    return render(request, 'catalog/song_detail.html', {
        'song': mark_liked(request.user, [song])[0],
        'features': features,
        'duration': _format_duration(song.duration_ms),
        'playlists': user_playlists(request.user),
    })


@login_required
def artist_detail(request, artist_id):
    artist = get_object_or_404(Artist, uri=artist_id)
    songs = artist.songs.order_by('-track_pop', 'track_name')[:ARTIST_SONG_LIMIT]
    return render(request, 'catalog/artist_detail.html', {
        'artist': artist,
        'songs': mark_liked(request.user, songs),
        'playlists': user_playlists(request.user),
    })
