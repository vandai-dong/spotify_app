"""Thin wrapper around the OpenAI client so everything above it stays testable."""
from django.conf import settings

_client = None


class AssistantUnavailable(Exception):
    """Raised when the assistant isn't configured (no API key)."""


def get_client():
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise AssistantUnavailable('OPENAI_API_KEY is not set')
        from openai import OpenAI

        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def complete(messages, json_mode=False):
    """Send chat `messages` to the model and return the reply text."""
    kwargs = {'response_format': {'type': 'json_object'}} if json_mode else {}
    response = get_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=1024,
        **kwargs,
    )
    return response.choices[0].message.content or ''
