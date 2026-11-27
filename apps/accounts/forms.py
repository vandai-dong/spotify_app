import datetime

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password

from .models import COUNTRY_CHOICES

User = get_user_model()


def validate_birthdate(value):
    """Shared by sign-up and profile editing."""
    if value > datetime.date.today() or value.year < 1900:
        raise forms.ValidationError('Please enter a valid birthdate.')
    return value


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
        return validate_birthdate(self.cleaned_data['birthdate'])

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


class ProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date', 'max': ''}, format='%Y-%m-%d'),
    )

    class Meta:
        model = User
        fields = ['display_name', 'date_of_birth', 'country', 'gender']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['display_name'].required = True
        self.fields['date_of_birth'].widget.attrs['max'] = datetime.date.today().isoformat()
        countries = sorted((c for c in COUNTRY_CHOICES if c[0] != 'None'), key=lambda c: c[1])
        self.fields['country'].choices = [('None', 'Not specified'), *countries]
        for name, field in self.fields.items():
            css = 'form-select' if name in ('country', 'gender') else 'form-control'
            field.widget.attrs['class'] = css

    def clean_date_of_birth(self):
        value = self.cleaned_data['date_of_birth']
        return validate_birthdate(value) if value else value


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
