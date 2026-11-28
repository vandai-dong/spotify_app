from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .helpers import mark_liked, paginate, user_playlists
from .models import Artist, Genre, Song
from .services import recommend
from .services.moods import MOODS, get_mood

DASHBOARD_ITEMS = 7
SEARCH_LIMIT = 50


@login_required
def dashboard(request):
    top_artists = Artist.objects.order_by('?')[:DASHBOARD_ITEMS]
    top_songs = Song.objects.order_by('?')[:DASHBOARD_ITEMS]
    for_you, personalized = recommend.recommend_for_user(request.user, DASHBOARD_ITEMS)
    return render(request, 'catalog/dashboard.html', {
        'top_artists': top_artists,
        'top_songs': top_songs,
        'for_you': for_you,
        'for_you_personalized': personalized,
    })


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
SIMILAR_LIMIT = 8
BROWSE_GENRES = 24
CHART_ARTISTS = 20


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
        'similar': mark_liked(request.user, recommend.similar_songs(song, SIMILAR_LIMIT)),
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


def _int_param(request, name):
    try:
        return int(request.GET.get(name, ''))
    except ValueError:
        return None


@login_required
def browse(request):
    genre = request.GET.get('genre', '').strip()
    mood = get_mood(request.GET.get('mood', ''))
    songs = Song.objects.all()
    if genre:
        songs = songs.filter(genres__name=genre)
    if mood:
        songs = songs.filter(mood.query)
    page_obj, querystring = paginate(request, songs.distinct())
    page_obj.object_list = mark_liked(request.user, page_obj.object_list)
    return render(request, 'catalog/browse.html', {
        'genre': genre,
        'mood': mood,
        'moods': MOODS.values(),
        'genres': Genre.objects.annotate(n=Count('songs')).order_by('-n', 'name')[:BROWSE_GENRES],
        'filtered': bool(genre or mood),
        'page_obj': page_obj,
        'querystring': querystring,
        'playlists': user_playlists(request.user),
    })


@login_required
def charts(request):
    genre = request.GET.get('genre', '').strip()
    tempo_min, tempo_max = _int_param(request, 'tempo_min'), _int_param(request, 'tempo_max')
    songs = Song.objects.all()
    if genre:
        songs = songs.filter(genres__name=genre)
    if tempo_min is not None:
        songs = songs.filter(tempo__gte=tempo_min)
    if tempo_max is not None:
        songs = songs.filter(tempo__lte=tempo_max)
    page_obj, querystring = paginate(request, songs.distinct().order_by('-track_pop', 'track_name'))
    page_obj.object_list = mark_liked(request.user, page_obj.object_list)
    offset = (page_obj.number - 1) * page_obj.paginator.per_page
    for rank, song in enumerate(page_obj.object_list, start=offset + 1):
        song.rank = rank
    return render(request, 'catalog/charts.html', {
        'genre': genre,
        'tempo_min': tempo_min if tempo_min is not None else '',
        'tempo_max': tempo_max if tempo_max is not None else '',
        'genres': Genre.objects.annotate(n=Count('songs')).order_by('-n', 'name')[:BROWSE_GENRES],
        'top_artists': Artist.objects.all()[:CHART_ARTISTS],
        'page_obj': page_obj,
        'querystring': querystring,
        'playlists': user_playlists(request.user),
    })
