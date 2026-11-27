import pytest
from django.urls import reverse

from apps.assistant import services

pytestmark = pytest.mark.django_db
URL = 'get_openai_answer'


def test_requires_login(client):
    assert client.post(reverse(URL), {'userInput': 'hi'}).status_code == 302


def test_post_only(logged_in):
    assert logged_in.get(reverse(URL)).status_code == 405


def test_returns_completion(logged_in, monkeypatch):
    monkeypatch.setattr(services, 'ask', lambda prompt: f'echo: {prompt}')
    r = logged_in.post(reverse(URL), {'userInput': 'hello'})
    assert r.status_code == 200 and r.json() == {'completion': 'echo: hello'}


def test_rejects_empty_and_oversized_prompts(logged_in, settings):
    assert logged_in.post(reverse(URL), {'userInput': '  '}).status_code == 400
    too_long = 'x' * (settings.CHATBOT_MAX_PROMPT_CHARS + 1)
    assert logged_in.post(reverse(URL), {'userInput': too_long}).status_code == 400


def test_rate_limit(logged_in, monkeypatch, settings):
    monkeypatch.setattr(services, 'ask', lambda prompt: 'ok')
    settings.CHATBOT_RATE_LIMIT_PER_MINUTE = 2
    codes = [logged_in.post(reverse(URL), {'userInput': 'hi'}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_unconfigured_returns_503_without_leaking(logged_in, settings):
    settings.OPENAI_API_KEY = ''
    services._client = None
    r = logged_in.post(reverse(URL), {'userInput': 'hi'})
    assert r.status_code == 503 and 'OPENAI' not in r.json()['error']


def test_upstream_error_returns_502_without_details(logged_in, monkeypatch):
    def boom(prompt):
        raise RuntimeError('secret internal detail')

    monkeypatch.setattr(services, 'ask', boom)
    r = logged_in.post(reverse(URL), {'userInput': 'hi'})
    assert r.status_code == 502 and 'secret' not in r.content.decode()


def test_chatbot_page_renders_with_csrf_token_for_script(logged_in):
    body = logged_in.get(reverse('chatbot')).content
    assert b'csrfmiddlewaretoken' in body and b'chatbot.js' in body
