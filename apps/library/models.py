import secrets

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
    # Random token for the read-only public link; null means the playlist is not shared.
    share_token = models.CharField(max_length=43, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def enable_sharing(self):
        self.share_token = secrets.token_urlsafe(16)
        self.save(update_fields=['share_token'])

    def disable_sharing(self):
        self.share_token = None
        self.save(update_fields=['share_token'])

    def renumber(self):
        """Make PlaylistSong.position a gapless 1..n sequence in the current order."""
        entries = list(self.playlist_songs.all())
        for position, entry in enumerate(entries, start=1):
            entry.position = position
        PlaylistSong.objects.bulk_update(entries, ['position'])


class PlaylistSong(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_songs')
    song = models.ForeignKey('catalog.Song', on_delete=models.CASCADE, related_name='song_playlists')
    added_at = models.DateTimeField(auto_now_add=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('playlist', 'song')
        ordering = ['position', 'added_at', 'id']

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
