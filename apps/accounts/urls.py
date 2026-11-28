from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path('', views.LoginView.as_view(), name='login'),
    path('logout', views.logout, name='logout'),
    path('settings', views.settings_page, name='settings'),
    path('settings/password', login_required(views.PasswordChangeView.as_view()), name='password_change'),
    path('settings/delete', views.delete_account, name='delete_account'),
    path('sign_up', views.sign_up, name='sign_up'),
    path('sign_up_form', views.sign_up_form, name='sign_up_form'),
    path('reset_password', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.txt',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='reset_password'),
    path('reset_password/sent', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset_password/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset_password/complete', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
]
