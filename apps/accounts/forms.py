import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=254, label='Email or username')

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Incorrect username or password.',
    }


class SignUpEmailForm(forms.Form):
    email = forms.EmailField(
        error_messages={'invalid': "This email is invalid. Make sure it's written like example@email.com"},
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('EXISTING_ACCOUNT', code='existing')
        return email


class SignUpForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    name = forms.CharField(max_length=150)
    birthdate = forms.DateField()
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False)

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This address is already linked to an existing account.')
        return email

    def clean_birthdate(self):
        birthdate = self.cleaned_data['birthdate']
        if birthdate > datetime.date.today() or birthdate.year < 1900:
            raise forms.ValidationError('Please enter a valid birthdate.')
        return birthdate

    def clean_gender(self):
        return self.cleaned_data.get('gender') or 'prefer_not_to_say'

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        if password:
            candidate = User(email=cleaned.get('email') or '', display_name=cleaned.get('name') or '')
            try:
                validate_password(password, candidate)
            except forms.ValidationError as exc:
                self.add_error('password', exc)
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User(
            email=data['email'],
            display_name=data['name'],
            date_of_birth=data['birthdate'],
            gender=data['gender'],
        )
        user.set_password(data['password'])
        user.save()  # User.save() generates a username
        return user
