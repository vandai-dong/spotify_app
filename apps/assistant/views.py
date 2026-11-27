import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from . import services

logger = logging.getLogger(__name__)


@login_required
def chatbot(request):
    return render(request, 'assistant/chatbot.html')


def _rate_limited(user_id):
    key = f'chatbot-rate:{user_id}'
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
        answer = services.ask(prompt)
    except services.AssistantUnavailable:
        return JsonResponse({'error': 'The assistant is not configured.'}, status=503)
    except Exception:
        logger.exception('OpenAI request failed')
        return JsonResponse({'error': 'The assistant could not answer right now.'}, status=502)
    return JsonResponse({'completion': answer})
