"""Link imported songs to their artists and genres.

The bundled datasets only list 71 of the 472 artists that appear on songs, so any missing primary
artist gets an `Artist` row derived from the song data. Safe to run repeatedly.
"""
from apps.catalog.models import Artist, Genre, Song

INT32_MAX = 2**31 - 1


def artist_id_from_uri(uri_artist):
    return uri_artist.split(':')[-1]


def first_artist_name(artist_names):
    return artist_names.split(',')[0].strip()


def link_catalog():
    """Create missing artists/genres and attach them to songs. Returns (artists_created, genres_created)."""
    songs = list(Song.objects.all())
    artists = {a.uri: a for a in Artist.objects.all()}

    # Artists: derive from the first song seen for each artist id.
    to_create = {}
    for song in songs:
        artist_id = artist_id_from_uri(song.uri_artist)
        if artist_id in artists or artist_id in to_create:
            continue
        to_create[artist_id] = Artist(
            uri=artist_id,
            artist=first_artist_name(song.artist_names),
            genres=song.artist_genres,
            num_of_followers=min(song.num_followers, INT32_MAX),
            popularity=song.artist_pop,
        )
    Artist.objects.bulk_create(to_create.values(), ignore_conflicts=True)
    artists = {a.uri: a for a in Artist.objects.all()}

    changed = []
    for song in songs:
        artist = artists.get(artist_id_from_uri(song.uri_artist))
        if artist and song.primary_artist_id != artist.pk:
            song.primary_artist = artist
            changed.append(song)
    Song.objects.bulk_update(changed, ['primary_artist'], batch_size=500)

    # Genres
    names = {g for song in songs for g in song.artist_genres}
    before = Genre.objects.count()
    Genre.objects.bulk_create([Genre(name=n) for n in sorted(names)], ignore_conflicts=True)
    genre_ids = dict(Genre.objects.values_list('name', 'id'))
    through = Song.genres.through
    links = [
        through(song_id=song.pk, genre_id=genre_ids[name])
        for song in songs
        for name in set(song.artist_genres)
    ]
    through.objects.bulk_create(links, ignore_conflicts=True, batch_size=1000)

    return len(to_create), Genre.objects.count() - before
