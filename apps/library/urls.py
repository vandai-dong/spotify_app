from django.urls import path

from . import views

urlpatterns = [
    path('like_song', views.like_song, name='like_song'),
    path('favorites/toggle/<int:song_id>', views.toggle_favorite, name='toggle_favorite'),
    path('your_library', views.your_library, name='your_library'),
    path('playlists/create', views.playlist_create, name='playlist_create'),
    path('playlists/<int:playlist_id>', views.playlist_detail, name='playlist_detail'),
    path('playlists/<int:playlist_id>/update', views.playlist_update, name='playlist_update'),
    path('playlists/<int:playlist_id>/delete', views.playlist_delete, name='playlist_delete'),
    path('playlists/<int:playlist_id>/add', views.playlist_add_song, name='playlist_add_song'),
    path('playlists/<int:playlist_id>/remove/<int:song_id>', views.playlist_remove_song, name='playlist_remove_song'),
]
