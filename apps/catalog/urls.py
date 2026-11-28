from django.urls import path

from . import views

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('search', views.search, name='search'),
    path('browse', views.browse, name='browse'),
    path('charts', views.charts, name='charts'),
    path('songs/<int:song_id>', views.song_detail, name='song_detail'),
    path('artists/<slug:artist_id>', views.artist_detail, name='artist_detail'),
    path('albums/<slug:album_id>', views.album_detail, name='album_detail'),
]
