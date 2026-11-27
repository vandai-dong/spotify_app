import pycountry
from django.contrib.auth.models import AbstractUser
from django.db import models

from .utils import generate_random_username

COUNTRY_CHOICES = [(c.name, c.name) for c in pycountry.countries] + [('None', 'None')]


class User(AbstractUser):
    """Application user. Logs in with email or username; password hashing is Django's."""

    GENDER_CHOICES = [
        ('female', 'Female'),
        ('male', 'Male'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
        ('non_binary', 'Non-binary'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('individual', 'Individual'),
        ('student', 'Student'),
        ('duo', 'Duo'),
        ('family', 'Family'),
    ]

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='prefer_not_to_say')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    email_verified = models.BooleanField(default=False)
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='free')
    country = models.CharField(max_length=100, choices=COUNTRY_CHOICES, default='None')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ['email']

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = generate_random_username()
            while type(self).objects.filter(username=self.username).exists():
                self.username = generate_random_username()
        if not self.display_name:
            self.display_name = self.username
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
