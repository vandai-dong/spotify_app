from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.catalog.models import Artist, Song

from .models import FavoriteSong, FollowedArtist, Playlist, PlaylistSong


def _redirect_back(request, default):
    """Redirect to ?next / POSTed next, else the referer, else `default` (open-redirect safe)."""
    target = request.POST.get('next') or request.META.get('HTTP_REFERER') or ''
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(default)


# --- Liked songs ---------------------------------------------------------

@login_required
def like_song(request):
    favorites = FavoriteSong.objects.filter(user=request.user).select_related('song')
    count = favorites.count()
    return render(request, 'library/like_song.html', {
        'favorites': favorites,
        'favorite_count_text': f"{count} song" if count == 1 else f"{count} songs",
    })


@login_required
@require_POST
def toggle_favorite(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    favorite, created = FavoriteSong.objects.get_or_create(user=request.user, song=song)
    if not created:
        favorite.delete()
    return _redirect_back(request, 'like_song')


@login_required
@require_POST
def toggle_follow(request, artist_id):
    artist = get_object_or_404(Artist, uri=artist_id)
    follow, created = FollowedArtist.objects.get_or_create(user=request.user, artist=artist)
    if not created:
        follow.delete()
    return _redirect_back(request, reverse('artist_detail', args=[artist.uri]))


# --- Playlists -------------------------------------------------------------

@login_required
def your_library(request):
    tag = request.GET.get('tag', '')
    playlists = Playlist.objects.filter(user=request.user)
    if tag in dict(Playlist.TAG_CHOICES):
        playlists = playlists.filter(tag=tag)
    else:
        tag = ''
    followed = []
    if tag in ('', Playlist.ARTIST):
        followed = [f.artist for f in FollowedArtist.objects.filter(user=request.user).select_related('artist')]
    return render(request, 'library/your_library.html', {
        'playlists': playlists,
        'followed_artists': followed,
        'tag': tag,
        'tag_choices': Playlist.TAG_CHOICES,
    })


@login_required
@require_POST
def playlist_create(request):
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, 'Please give your playlist a name.')
        return redirect('your_library')
    tag = request.POST.get('tag')
    playlist = Playlist.objects.create(
        user=request.user,
        name=name[:255],
        description=request.POST.get('description', '').strip(),
        tag=tag if tag in dict(Playlist.TAG_CHOICES) else Playlist.PLAYLIST,
    )
    return redirect('playlist_detail', playlist_id=playlist.pk)


@login_required
def playlist_detail(request, playlist_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    entries = playlist.playlist_songs.select_related('song')
    return render(request, 'library/playlist_detail.html', {'playlist': playlist, 'entries': entries})


@login_required
@require_POST
def playlist_update(request, playlist_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    name = request.POST.get('name', '').strip()
    if name:
        playlist.name = name[:255]
        playlist.description = request.POST.get('description', playlist.description).strip()
        playlist.save()
    else:
        messages.error(request, 'A playlist needs a name.')
    return redirect('playlist_detail', playlist_id=playlist.pk)


@login_required
@require_POST
def playlist_delete(request, playlist_id):
    get_object_or_404(Playlist, pk=playlist_id, user=request.user).delete()
    return redirect('your_library')


@login_required
@require_POST
def playlist_add_song(request, playlist_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    song = get_object_or_404(Song, pk=request.POST.get('song_id'))
    PlaylistSong.objects.get_or_create(playlist=playlist, song=song)
    playlist.save(update_fields=['updated_at'])
    return _redirect_back(request, reverse('playlist_detail', args=[playlist.pk]))


@login_required
@require_POST
def playlist_remove_song(request, playlist_id, song_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    PlaylistSong.objects.filter(playlist=playlist, song_id=song_id).delete()
    return redirect('playlist_detail', playlist_id=playlist.pk)
