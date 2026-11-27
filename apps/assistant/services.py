"""Thin wrapper around the OpenAI client so views stay testable."""
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


def ask(prompt):
    response = get_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content or ''
