from django.contrib import admin

from .models import FavoriteSong, Playlist, PlaylistSong


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'tag', 'created_at', 'updated_at']
    list_filter = ['tag']
    search_fields = ['name', 'user__username', 'user__email']


@admin.register(PlaylistSong)
class PlaylistSongAdmin(admin.ModelAdmin):
    list_display = ['playlist', 'song', 'added_at']


@admin.register(FavoriteSong)
class FavoriteSongAdmin(admin.ModelAdmin):
    list_display = ['user', 'song', 'added_at']
