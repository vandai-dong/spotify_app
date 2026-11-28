"""Simulated player: a queue kept in the session plus a play history. No audio is involved."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import Song

from .models import PlayHistory

SESSION_KEY = 'player'
MAX_QUEUE = 100
RECENT_LIMIT = 50


def _get_state(request):
    state = request.session.get(SESSION_KEY) or {}
    return {
        'queue': list(state.get('queue', [])),
        'index': int(state.get('index', 0)),
        'playing': bool(state.get('playing', False)),
    }


def _save_state(request, state):
    request.session[SESSION_KEY] = state


def _song_payload(song):
    return {
        'id': song.pk,
        'title': song.display_title,
        'artist': song.artist_names,
        'image': song.cover_url,
        'url': f'/songs/{song.pk}',
        'duration_ms': song.duration_ms,
    }


def _state_response(request, state):
    song = None
    if state['queue'] and 0 <= state['index'] < len(state['queue']):
        song = Song.objects.select_related('album').filter(pk=state['queue'][state['index']]).first()
    return JsonResponse({
        'song': _song_payload(song) if song else None,
        'playing': state['playing'] and song is not None,
        'position': state['index'] + 1 if song else 0,
        'length': len(state['queue']),
    })


def _parse_queue(raw):
    ids = []
    for part in (raw or '').split(','):
        part = part.strip()
        if part.isdigit() and int(part) not in ids:
            ids.append(int(part))
        if len(ids) >= MAX_QUEUE:
            break
    return ids


def _record(request, song_id):
    PlayHistory.objects.create(user=request.user, song_id=song_id)


@login_required
@require_GET
def state(request):
    return _state_response(request, _get_state(request))


@login_required
@require_POST
def play(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    wanted = _parse_queue(request.POST.get('queue'))
    existing = set(Song.objects.filter(pk__in=wanted).values_list('pk', flat=True))
    queue = [pk for pk in wanted if pk in existing]
    if song.pk not in queue:
        queue.insert(0, song.pk)
    state = {'queue': queue, 'index': queue.index(song.pk), 'playing': True}
    _save_state(request, state)
    _record(request, song.pk)
    return _state_response(request, state)


def _step(request, delta):
    state = _get_state(request)
    if not state['queue']:
        return _state_response(request, state)
    state['index'] = (state['index'] + delta) % len(state['queue'])
    state['playing'] = True
    _save_state(request, state)
    _record(request, state['queue'][state['index']])
    return _state_response(request, state)


@login_required
@require_POST
def next_song(request):
    return _step(request, 1)


@login_required
@require_POST
def previous_song(request):
    return _step(request, -1)


@login_required
@require_POST
def toggle(request):
    state = _get_state(request)
    if state['queue']:
        state['playing'] = not state['playing']
        _save_state(request, state)
    return _state_response(request, state)


@login_required
def recent(request):
    plays = PlayHistory.objects.filter(user=request.user).select_related('song')[:RECENT_LIMIT]
    return render(request, 'library/recent.html', {'plays': plays})
