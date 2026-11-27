from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileForm, SignUpEmailForm, SignUpForm, StyledPasswordChangeForm


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


@login_required
def settings_page(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('settings')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/settings.html', {'form': form})


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = 'accounts/password_change.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('settings')

    def form_valid(self, form):
        messages.success(self.request, 'Password changed.')
        return super().form_valid(form)


@login_required
@require_POST
def delete_account(request):
    if not request.user.check_password(request.POST.get('password', '')):
        messages.error(request, 'Incorrect password. Your account was not deleted.')
        return redirect('settings')
    user = request.user
    auth_logout(request)
    user.delete()  # cascades to playlists, favourites, etc.
    messages.success(request, 'Your account has been deleted.')
    return redirect('login')
