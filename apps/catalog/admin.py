from django.contrib import admin
from django.utils.html import format_html

from .models import Album, Artist, Song


class CoverPreviewMixin:
    """Small thumbnail of whichever image the site would show (upload wins over the cached URL)."""

    @admin.display(description='Cover')
    def cover_preview(self, obj):
        if url := obj.cover_url:
            return format_html('<img src="{}" alt="" style="width:40px;height:40px;object-fit:cover;border-radius:4px">', url)
        return '—'


@admin.register(Song)
class SongAdmin(CoverPreviewMixin, admin.ModelAdmin):
    list_display = ['cover_preview', 'track_name', 'artist_names', 'track_pop', 'uri']
    search_fields = ['track_name', 'artist_names']
    list_select_related = ['album']
    raw_id_fields = ['album', 'primary_artist']
    readonly_fields = ['cover_preview']


@admin.register(Artist)
class ArtistAdmin(CoverPreviewMixin, admin.ModelAdmin):
    list_display = ['cover_preview', 'artist', 'popularity', 'num_of_followers', 'uri']
    search_fields = ['artist']
    readonly_fields = ['cover_preview']


@admin.register(Album)
class AlbumAdmin(CoverPreviewMixin, admin.ModelAdmin):
    list_display = ['cover_preview', 'name', 'primary_artist', 'uri']
    search_fields = ['name', 'primary_artist__artist']
    list_select_related = ['primary_artist']
    raw_id_fields = ['primary_artist']
    readonly_fields = ['cover_preview']
