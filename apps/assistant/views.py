import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.helpers import mark_liked, user_playlists

from . import chat, playlist_builder, services

logger = logging.getLogger(__name__)


@login_required
def chatbot(request):
    return render(request, 'assistant/chatbot.html')


def _rate_limited(user_id, scope='chatbot'):
    key = f'{scope}-rate:{user_id}'
    cache.add(key, 0, timeout=60)
    return cache.incr(key) > settings.CHATBOT_RATE_LIMIT_PER_MINUTE


@login_required
@require_POST
def get_openai_answer(request):
    prompt = request.POST.get('userInput', '').strip()
    if not prompt:
        return JsonResponse({'error': 'Please type a message.'}, status=400)
    if len(prompt) > settings.CHATBOT_MAX_PROMPT_CHARS:
        return JsonResponse({'error': 'That message is too long.'}, status=400)
    if _rate_limited(request.user.pk):
        return JsonResponse({'error': 'Too many requests. Please wait a minute.'}, status=429)

    try:
        result = chat.chat(request.user, prompt, request.POST.get('history', ''))
    except services.AssistantUnavailable:
        return JsonResponse({'error': 'The assistant is not configured.'}, status=503)
    except Exception:
        logger.exception('OpenAI request failed')
        return JsonResponse({'error': 'The assistant could not answer right now.'}, status=502)
    songs = mark_liked(request.user, result.songs)
    return JsonResponse({
        'completion': result.reply,
        'songs': [
            {'id': s.pk, 'title': s.display_title, 'artist': s.artist_names, 'url': f'/songs/{s.pk}', 'liked': s.liked}
            for s in songs
        ],
        'playlists': [{'id': p.pk, 'name': p.name} for p in user_playlists(request.user)] if songs else [],
    })


@login_required
@require_POST
def build_playlist(request):
    prompt = request.POST.get('prompt', '').strip()
    if not prompt:
        messages.error(request, 'Describe the playlist you want first.')
        return redirect('chatbot')
    if len(prompt) > settings.CHATBOT_MAX_PROMPT_CHARS:
        messages.error(request, 'That description is too long.')
        return redirect('chatbot')
    if _rate_limited(request.user.pk, scope='ai-playlist'):
        messages.error(request, 'Too many requests. Please wait a minute.')
        return redirect('chatbot')
    try:
        playlist = playlist_builder.create_playlist(request.user, prompt)
    except playlist_builder.PlaylistBuildError as exc:
        messages.error(request, str(exc))
        return redirect('chatbot')
    messages.success(request, f'Created “{playlist.name}”.')
    return redirect('playlist_detail', playlist_id=playlist.pk)
