from django.urls import path

from . import views

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('search', views.search, name='search'),
    path('songs/<int:song_id>', views.song_detail, name='song_detail'),
    path('artists/<slug:artist_id>', views.artist_detail, name='artist_detail'),
]
