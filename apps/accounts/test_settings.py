import datetime

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.library.models import FavoriteSong, Playlist

pytestmark = pytest.mark.django_db

SETTINGS = 'settings'
VALID_PROFILE = {'display_name': 'Alice B', 'date_of_birth': '1990-02-03', 'country': 'Australia', 'gender': 'female'}


@pytest.mark.parametrize('name', ['settings', 'password_change'])
def test_settings_pages_render_for_logged_in_user(logged_in, name):
    assert logged_in.get(reverse(name)).status_code == 200


@pytest.mark.parametrize('name', ['settings', 'password_change'])
def test_settings_pages_require_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302 and response.url.startswith(reverse('login'))


def test_delete_requires_login_and_post(client, logged_in, user):
    assert logged_in.get(reverse('delete_account')).status_code == 405
    client.logout()
    assert client.post(reverse('delete_account'), {'password': 'x'}).status_code == 302
    assert User.objects.filter(pk=user.pk).exists()


def test_profile_form_shows_current_values_and_read_only_email(logged_in, user):
    body = logged_in.get(reverse(SETTINGS)).content.decode()
    assert 'value="Alice"' in body and 'alice@example.com' in body


def test_profile_update_saves_changes(logged_in, user):
    response = logged_in.post(reverse(SETTINGS), VALID_PROFILE)
    assert response.status_code == 302 and response.url == reverse(SETTINGS)
    user.refresh_from_db()
    assert (user.display_name, user.country, user.gender) == ('Alice B', 'Australia', 'female')
    assert user.date_of_birth == datetime.date(1990, 2, 3)
    assert b'Profile updated.' in logged_in.get(reverse(SETTINGS)).content


def test_profile_rejects_blank_name_and_future_birthdate(logged_in, user):
    assert logged_in.post(reverse(SETTINGS), {**VALID_PROFILE, 'display_name': '  '}).status_code == 200
    r = logged_in.post(reverse(SETTINGS), {**VALID_PROFILE, 'date_of_birth': '2999-01-01'})
    assert r.status_code == 200 and b'valid birthdate' in r.content
    user.refresh_from_db()
    assert user.display_name == 'Alice' and user.date_of_birth is None


def test_profile_rejects_unknown_country_and_gender(logged_in, user):
    assert logged_in.post(reverse(SETTINGS), {**VALID_PROFILE, 'country': 'Atlantis'}).status_code == 200
    assert logged_in.post(reverse(SETTINGS), {**VALID_PROFILE, 'gender': 'robot'}).status_code == 200


def test_profile_post_cannot_change_email_or_privileged_fields(logged_in, user):
    logged_in.post(reverse(SETTINGS), {
        **VALID_PROFILE, 'email': 'evil@example.com', 'is_staff': 'on', 'is_superuser': 'on', 'subscription_type': 'family',
    })
    user.refresh_from_db()
    assert user.email == 'alice@example.com'
    assert not user.is_staff and not user.is_superuser and user.subscription_type == 'free'


def test_profile_can_clear_birthdate(logged_in, user):
    user.date_of_birth = datetime.date(1990, 1, 1)
    user.save()
    logged_in.post(reverse(SETTINGS), {**VALID_PROFILE, 'date_of_birth': ''})
    user.refresh_from_db()
    assert user.date_of_birth is None


def test_password_change_succeeds_and_keeps_session(logged_in, user):
    response = logged_in.post(reverse('password_change'), {
        'old_password': 'correct-horse-9', 'new_password1': 'brand-New-pass-77', 'new_password2': 'brand-New-pass-77',
    })
    assert response.status_code == 302 and response.url == reverse(SETTINGS)
    user.refresh_from_db()
    assert user.check_password('brand-New-pass-77')
    assert logged_in.get(reverse('dashboard')).status_code == 200  # still logged in


def test_password_change_rejects_wrong_old_and_weak_new(logged_in, user):
    r = logged_in.post(reverse('password_change'), {
        'old_password': 'wrong', 'new_password1': 'brand-New-pass-77', 'new_password2': 'brand-New-pass-77',
    })
    assert r.status_code == 200 and b'password was entered incorrectly' in r.content
    r = logged_in.post(reverse('password_change'), {
        'old_password': 'correct-horse-9', 'new_password1': '12345678', 'new_password2': '12345678',
    })
    assert r.status_code == 200
    user.refresh_from_db()
    assert user.check_password('correct-horse-9')


def test_delete_with_wrong_password_keeps_account(logged_in, user):
    response = logged_in.post(reverse('delete_account'), {'password': 'nope'})
    assert response.status_code == 302 and response.url == reverse(SETTINGS)
    assert User.objects.filter(pk=user.pk).exists()
    assert b'Incorrect password' in logged_in.get(reverse(SETTINGS)).content


def test_delete_removes_account_and_cascades_then_logs_out(logged_in, user, other_user, song):
    Playlist.objects.create(user=user, name='Mine')
    Playlist.objects.create(user=other_user, name='Theirs')
    FavoriteSong.objects.create(user=user, song=song)
    response = logged_in.post(reverse('delete_account'), {'password': 'correct-horse-9'})
    assert response.status_code == 302 and response.url == reverse('login')
    assert not User.objects.filter(pk=user.pk).exists()
    assert list(Playlist.objects.values_list('name', flat=True)) == ['Theirs']
    assert not FavoriteSong.objects.exists()
    assert logged_in.get(reverse('dashboard')).status_code == 302  # session is gone


def test_deleted_account_can_no_longer_log_in(client, user):
    client.force_login(user)
    client.post(reverse('delete_account'), {'password': 'correct-horse-9'})
    r = client.post(reverse('login'), {'username': 'alice@example.com', 'password': 'correct-horse-9'})
    assert r.status_code == 200 and b'Incorrect username or password.' in r.content


def test_country_choices_are_sorted_with_none_first(logged_in):
    from apps.accounts.forms import ProfileForm

    labels = [label for _, label in ProfileForm().fields['country'].choices]
    assert labels[0] == 'Not specified' and labels[1:] == sorted(labels[1:])
