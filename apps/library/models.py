from django.conf import settings
from django.db import models


class Playlist(models.Model):
    ARTIST = 'Artist'
    PLAYLIST = 'Playlist'
    AUDIOBOOK = 'Audiobook'
    PODCAST = 'Podcast'
    TAG_CHOICES = [
        (ARTIST, 'Artist'),
        (PLAYLIST, 'Playlist'),
        (AUDIOBOOK, 'Audiobook'),
        (PODCAST, 'Podcast'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    tag = models.CharField(max_length=50, choices=TAG_CHOICES, default=PLAYLIST)
    songs = models.ManyToManyField('catalog.Song', through='PlaylistSong', related_name='playlists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class PlaylistSong(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_songs')
    song = models.ForeignKey('catalog.Song', on_delete=models.CASCADE, related_name='song_playlists')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('playlist', 'song')
        ordering = ['added_at']

    def __str__(self):
        return f"{self.song.track_name} in {self.playlist.name}"


class FavoriteSong(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_songs')
    song = models.ForeignKey('catalog.Song', on_delete=models.CASCADE, related_name='favorited_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'song')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.song.track_name}"


class FollowedArtist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_artists')
    artist = models.ForeignKey('catalog.Artist', on_delete=models.CASCADE, related_name='followers')
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artist')
        ordering = ['-followed_at']

    def __str__(self):
        return f"{self.user.username} follows {self.artist.artist}"


class PlayHistory(models.Model):
    """One row per (simulated) play. There is no audio; this just records what was 'played'."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='play_history')
    song = models.ForeignKey('catalog.Song', on_delete=models.CASCADE, related_name='plays')
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-played_at', '-id']
        verbose_name_plural = 'play history'

    def __str__(self):
        return f"{self.user.username} played {self.song.track_name}"
