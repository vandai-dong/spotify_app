from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.catalog.helpers import paginate
from apps.catalog.models import Artist, Song

from .models import FavoriteSong, FollowedArtist, Playlist, PlaylistSong

PLAYLISTS_PER_PAGE = 20
COVER_TILES = 4


def attach_covers(playlists):
    """Set `playlist.cover_urls` (up to 4 image URLs) on each playlist using a single query."""
    playlists = list(playlists)
    covers = defaultdict(list)
    entries = PlaylistSong.objects.filter(playlist__in=playlists).select_related('song', 'song__album')
    for entry in entries:
        urls = covers[entry.playlist_id]
        url = entry.song.cover_url
        if url and len(urls) < COVER_TILES and url not in urls:
            urls.append(url)
    for playlist in playlists:
        playlist.cover_urls = covers.get(playlist.pk, [])
    return playlists


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
    page_obj, querystring = paginate(request, favorites)
    count = page_obj.paginator.count
    return render(request, 'library/like_song.html', {
        'page_obj': page_obj,
        'querystring': querystring,
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
    playlists = Playlist.objects.filter(user=request.user).annotate(song_count=Count('playlist_songs')).order_by('-updated_at')
    if tag in dict(Playlist.TAG_CHOICES):
        playlists = playlists.filter(tag=tag)
    else:
        tag = ''
    followed = []
    if tag in ('', Playlist.ARTIST):
        followed = [f.artist for f in FollowedArtist.objects.filter(user=request.user).select_related('artist')]
    page_obj, querystring = paginate(request, playlists, per_page=PLAYLISTS_PER_PAGE)
    attach_covers(page_obj.object_list)
    return render(request, 'library/your_library.html', {
        'page_obj': page_obj,
        'querystring': querystring,
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
    entries = list(playlist.playlist_songs.select_related('song', 'song__album'))
    attach_covers([playlist])
    return render(request, 'library/playlist_detail.html', {
        'playlist': playlist,
        'entries': entries,
        'share_url': request.build_absolute_uri(reverse('shared_playlist', args=[playlist.share_token]))
        if playlist.share_token else '',
    })


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
    if not PlaylistSong.objects.filter(playlist=playlist, song=song).exists():
        last = playlist.playlist_songs.aggregate(last=Max('position'))['last'] or 0
        PlaylistSong.objects.create(playlist=playlist, song=song, position=last + 1)
    playlist.save(update_fields=['updated_at'])
    return _redirect_back(request, reverse('playlist_detail', args=[playlist.pk]))


@login_required
@require_POST
def playlist_remove_song(request, playlist_id, song_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    PlaylistSong.objects.filter(playlist=playlist, song_id=song_id).delete()
    playlist.renumber()
    return redirect('playlist_detail', playlist_id=playlist.pk)


@login_required
@require_POST
def playlist_move_song(request, playlist_id, song_id):
    """Move a song one place up or down (`direction` = up|down)."""
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    direction = request.POST.get('direction')
    entries = list(playlist.playlist_songs.all())
    index = next((i for i, e in enumerate(entries) if e.song_id == song_id), None)
    if index is None:
        raise Http404('Song is not in this playlist')
    swap = index - 1 if direction == 'up' else index + 1 if direction == 'down' else None
    if swap is not None and 0 <= swap < len(entries):
        entries[index], entries[swap] = entries[swap], entries[index]
        for position, entry in enumerate(entries, start=1):
            entry.position = position
        PlaylistSong.objects.bulk_update(entries, ['position'])
    return redirect('playlist_detail', playlist_id=playlist.pk)


@login_required
@require_POST
def playlist_share(request, playlist_id):
    """Turn the public read-only link on or off (`action` = enable|disable). Re-enabling issues a new token."""
    playlist = get_object_or_404(Playlist, pk=playlist_id, user=request.user)
    if request.POST.get('action') == 'enable':
        playlist.enable_sharing()
    elif request.POST.get('action') == 'disable':
        playlist.disable_sharing()
    return redirect('playlist_detail', playlist_id=playlist.pk)


def shared_playlist(request, token):
    """Public, read-only view. Exposes only the playlist, its songs and the owner's display name."""
    playlist = get_object_or_404(Playlist.objects.select_related('user'), share_token=token)
    entries = list(playlist.playlist_songs.select_related('song', 'song__album'))
    attach_covers([playlist])
    return render(request, 'library/shared_playlist.html', {
        'playlist': playlist,
        'entries': entries,
        'owner_name': playlist.user.display_name,
    })
