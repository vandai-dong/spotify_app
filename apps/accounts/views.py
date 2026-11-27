from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignUpEmailForm, SignUpForm


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


@require_POST
def logout(request):
    auth_logout(request)
    return redirect('login')


def sign_up(request):
    """Step 1: collect and validate the email address."""
    if request.method == 'POST':
        form = SignUpEmailForm(request.POST)
        if form.is_valid():
            request.session['signup_email'] = form.cleaned_data['email']
            return redirect('sign_up_form')
        for error in form.errors.get('email', []):
            if error == 'EXISTING_ACCOUNT':
                messages.warning(request, format_html(
                    'This address is already linked to an existing account. To continue, <a href="{}">log in</a>.',
                    reverse('login'),
                ))
            else:
                messages.error(request, error)
    return render(request, 'accounts/signup.html')


def sign_up_form(request):
    """Step 2: password, profile details; creates the account."""
    email = request.session.get('signup_email')
    if not email:
        messages.error(request, 'Session expired or email not provided.')
        return redirect('sign_up')

    if request.method == 'POST':
        form = SignUpForm({**request.POST.dict(), 'email': email})
        if form.is_valid():
            form.save()
            request.session.pop('signup_email', None)
            messages.success(request, 'Account created successfully!')
            return redirect('login')
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return render(request, 'accounts/signup_form.html', {'email': email})
