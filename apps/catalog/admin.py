from django.contrib import admin

from .models import Artist, Song


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['track_name', 'artist_names', 'track_pop', 'uri']
    search_fields = ['track_name', 'artist_names']


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['artist', 'popularity', 'num_of_followers', 'uri']
    search_fields = ['artist']
