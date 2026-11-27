"""Project URL configuration."""
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('', include('apps.catalog.urls')),
    path('', include('apps.library.urls')),
    path('', include('apps.assistant.urls')),
    path('notification', login_required(TemplateView.as_view(template_name='pages/notification.html')), name='notification'),
    path('download_app', login_required(TemplateView.as_view(template_name='pages/download_app.html')), name='download_app'),
]
