import re

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

SIGNUP = {'password': 'a-Strong-pass-42', 'name': 'Carol', 'birthdate': '1999-05-04', 'gender': 'female'}


def test_login_page_renders(client):
    assert client.get(reverse('login')).status_code == 200


@pytest.mark.parametrize('identifier', ['alice', 'alice@example.com', 'ALICE@Example.com'])
def test_login_by_username_or_email(client, user, identifier):
    response = client.post(reverse('login'), {'username': identifier, 'password': 'correct-horse-9'})
    assert response.status_code == 302 and response.url == reverse('dashboard')


def test_login_wrong_password_shows_error(client, user):
    response = client.post(reverse('login'), {'username': 'alice', 'password': 'nope'})
    assert response.status_code == 200
    assert b'Incorrect username or password.' in response.content


@pytest.mark.parametrize('name', ['dashboard', 'chatbot', 'like_song', 'your_library', 'notification', 'download_app', 'search'])
def test_app_pages_redirect_anonymous_to_login(client, name):
    # Previously these crashed with a 500 (AttributeError on a missing user).
    response = client.get(reverse(name))
    assert response.status_code == 302 and response.url.startswith(reverse('login'))


@pytest.mark.parametrize('name', ['dashboard', 'chatbot', 'like_song', 'your_library', 'notification', 'download_app', 'search'])
def test_app_pages_render_for_logged_in_user(logged_in, name):
    assert logged_in.get(reverse(name)).status_code == 200


def test_logout_requires_post_and_ends_session(logged_in):
    assert logged_in.get(reverse('logout')).status_code == 405
    assert logged_in.post(reverse('logout')).status_code == 302
    assert logged_in.get(reverse('dashboard')).status_code == 302


def test_signup_full_flow_hashes_password_and_generates_username(client):
    r = client.post(reverse('sign_up'), {'email': 'new@example.com'})
    assert r.status_code == 302 and r.url == reverse('sign_up_form')
    r = client.post(reverse('sign_up_form'), SIGNUP)
    assert r.status_code == 302 and r.url == reverse('login')
    user = User.objects.get(email='new@example.com')
    assert user.display_name == 'Carol' and len(user.username) == 26
    assert user.password.startswith('pbkdf2_') and user.check_password(SIGNUP['password'])
    # and the new account can log in with its email
    assert client.post(reverse('login'), {'username': 'new@example.com', 'password': SIGNUP['password']}).status_code == 302


def test_signup_rejects_invalid_and_existing_email(client, user):
    assert b'This email is invalid' in client.post(reverse('sign_up'), {'email': 'nope'}).content
    r = client.post(reverse('sign_up'), {'email': 'ALICE@example.com'})
    assert b'already linked to an existing account' in r.content
    assert b'<a href="/">log in</a>' in r.content


def test_signup_form_requires_email_in_session(client):
    assert client.get(reverse('sign_up_form')).url == reverse('sign_up')


def test_signup_rejects_weak_password_and_future_birthdate(client):
    client.post(reverse('sign_up'), {'email': 'new@example.com'})
    r = client.post(reverse('sign_up_form'), {**SIGNUP, 'password': '12345678'})
    assert r.status_code == 200 and not User.objects.filter(email='new@example.com').exists()
    r = client.post(reverse('sign_up_form'), {**SIGNUP, 'birthdate': '2999-01-01'})
    assert r.status_code == 200 and not User.objects.filter(email='new@example.com').exists()


def test_signup_ignores_posted_email_and_uses_session_email(client):
    client.post(reverse('sign_up'), {'email': 'real@example.com'})
    client.post(reverse('sign_up_form'), {**SIGNUP, 'email': 'attacker@example.com'})
    assert User.objects.filter(email='real@example.com').exists()
    assert not User.objects.filter(email='attacker@example.com').exists()


def test_password_reset_requires_emailed_token(client, user):
    # The old flow let anyone set any account's password without verification.
    client.post(reverse('reset_password'), {'email': 'alice@example.com'})
    assert len(mail.outbox) == 1
    link = re.search(r'http://testserver(/reset_password/[^\s]+)', mail.outbox[0].body).group(1)
    r = client.get(link)  # Django redirects to the session-bound "set-password" URL
    assert r.status_code == 302
    r = client.post(r.url, {'new_password1': 'brand-New-pass-77', 'new_password2': 'brand-New-pass-77'})
    assert r.status_code == 302 and r.url == reverse('password_reset_complete')
    user.refresh_from_db()
    assert user.check_password('brand-New-pass-77')


def test_password_reset_unknown_email_does_not_leak(client):
    r = client.post(reverse('reset_password'), {'email': 'ghost@example.com'})
    assert r.status_code == 302 and r.url == reverse('password_reset_done') and mail.outbox == []
