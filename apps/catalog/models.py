import re

from django.core.exceptions import ValidationError
from django.db import models

MAX_IMAGE_BYTES = 2 * 1024 * 1024


def validate_image_size(file):
    if file.size > MAX_IMAGE_BYTES:
        raise ValidationError(f'Image is too large (max {MAX_IMAGE_BYTES // (1024 * 1024)} MB).')


def _image_field(folder):
    return models.ImageField(upload_to=folder, blank=True, validators=[validate_image_size])


class CoverMixin:
    """Shared "which image do we show" rule: uploaded file, then cached remote URL, else empty."""

    remote_image_field = 'image_url'

    @property
    def cover_url(self):
        if self.image:
            return self.image.url
        return getattr(self, self.remote_image_field) or ''


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Artist(CoverMixin, models.Model):
    artist = models.CharField(max_length=255)
    uri = models.CharField(max_length=100, unique=True)
    genres = models.JSONField(default=list)
    num_of_followers = models.IntegerField()
    popularity = models.IntegerField()
    image_url = models.URLField(max_length=500, blank=True)
    image = _image_field('artists/')

    class Meta:
        ordering = ['-popularity', 'artist']

    def __str__(self):
        return self.artist


class Album(CoverMixin, models.Model):
    name = models.CharField(max_length=255)
    uri = models.CharField(max_length=100, unique=True)  # bare Spotify album id
    primary_artist = models.ForeignKey(
        Artist, null=True, blank=True, on_delete=models.SET_NULL, related_name='albums',
    )
    image_url = models.URLField(max_length=500, blank=True)
    image = _image_field('albums/')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Song(CoverMixin, models.Model):
    uri = models.CharField(max_length=100, unique=True)
    artist_names = models.CharField(max_length=255)
    track_name = models.CharField(max_length=255)
    acousticness = models.FloatField()
    danceability = models.FloatField()
    duration_ms = models.IntegerField()
    energy = models.FloatField()
    instrumentalness = models.FloatField()
    liveness = models.FloatField()
    loudness = models.FloatField()
    mode = models.IntegerField(choices=[(0, 'Minor'), (1, 'Major')])
    speechiness = models.FloatField()
    tempo = models.FloatField()
    time_signature = models.IntegerField()
    valence = models.FloatField()
    uri_artist = models.CharField(max_length=100)
    artist_pop = models.IntegerField()
    num_followers = models.BigIntegerField()
    artist_genres = models.JSONField(default=list)
    track_pop = models.IntegerField()
    song_img_url = models.URLField(max_length=500, blank=True)
    image = _image_field('songs/')
    genres = models.ManyToManyField(Genre, related_name='songs', blank=True)
    primary_artist = models.ForeignKey(
        Artist, null=True, blank=True, on_delete=models.SET_NULL, related_name='songs',
    )
    album = models.ForeignKey(
        Album, null=True, blank=True, on_delete=models.SET_NULL, related_name='songs',
    )

    remote_image_field = 'song_img_url'

    class Meta:
        ordering = ['-track_pop', 'track_name']

    def __str__(self):
        return f"{self.track_name} by {self.artist_names}"

    @property
    def cover_url(self):
        return super().cover_url or (self.album.cover_url if self.album_id else '')

    @property
    def display_title(self):
        """Track name without a trailing '(feat. ...)' / '(From ...)' suffix."""
        return re.sub(r'\s*\(.*$', '', self.track_name) or self.track_name
