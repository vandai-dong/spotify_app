import re

from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Artist(models.Model):
    artist = models.CharField(max_length=255)
    uri = models.CharField(max_length=100, unique=True)
    genres = models.JSONField(default=list)
    num_of_followers = models.IntegerField()
    popularity = models.IntegerField()
    image_url = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ['-popularity', 'artist']

    def __str__(self):
        return self.artist


class Song(models.Model):
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
    genres = models.ManyToManyField(Genre, related_name='songs', blank=True)
    primary_artist = models.ForeignKey(
        Artist, null=True, blank=True, on_delete=models.SET_NULL, related_name='songs',
    )

    class Meta:
        ordering = ['-track_pop', 'track_name']

    def __str__(self):
        return f"{self.track_name} by {self.artist_names}"

    @property
    def display_title(self):
        """Track name without a trailing '(feat. ...)' / '(From ...)' suffix."""
        return re.sub(r'\s*\(.*$', '', self.track_name) or self.track_name
