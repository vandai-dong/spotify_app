from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from apps.library.models import FavoriteSong, Playlist

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
    songs = list(songs)
    liked_ids = set(
        FavoriteSong.objects.filter(user=request.user, song__in=songs).values_list('song_id', flat=True)
    )
    for song in songs:
        song.liked = song.pk in liked_ids
    playlists = Playlist.objects.filter(user=request.user)
    return render(request, 'catalog/search.html', {
        'query': query, 'songs': songs, 'artists': artists, 'playlists': playlists,
    })
