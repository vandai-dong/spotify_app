from django.contrib import admin

from .models import FavoriteSong, FollowedArtist, PlayHistory, Playlist, PlaylistSong


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


@admin.register(FollowedArtist)
class FollowedArtistAdmin(admin.ModelAdmin):
    list_display = ['user', 'artist', 'followed_at']


@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'song', 'played_at']
