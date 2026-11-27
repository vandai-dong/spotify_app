from apps.library.models import FavoriteSong, Playlist


def mark_liked(user, songs):
    """Set `song.liked` on each song (a list) with a single query; returns the list."""
    songs = list(songs)
    liked_ids = set(
        FavoriteSong.objects.filter(user=user, song__in=songs).values_list('song_id', flat=True)
    )
    for song in songs:
        song.liked = song.pk in liked_ids
    return songs


def user_playlists(user):
    return Playlist.objects.filter(user=user)
