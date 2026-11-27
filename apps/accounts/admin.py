from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ['id', 'username', 'display_name', 'email', 'status', 'subscription_type', 'created_at']
    list_filter = DjangoUserAdmin.list_filter + ('status', 'subscription_type')
    search_fields = ['username', 'email', 'display_name']
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Profile', {'fields': ('display_name', 'phone_number', 'date_of_birth', 'gender', 'country')}),
        ('Account', {'fields': ('status', 'email_verified', 'subscription_type')}),
    )
