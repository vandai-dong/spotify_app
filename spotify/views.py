from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseRedirect
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import auth
from django.utils.timezone import localtime


from urllib.parse import urlencode
from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials  # To access authorized Spotify data

from .models import User, Song, Artist, FavoriteSong

# Load keys from .env file
load_dotenv() 

_openai_client = None
_spotify_client = None


def get_openai_client():
    """Create the OpenAI client on first use so the app boots without keys."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_spotify_client():
    """Create the Spotify client on first use so the app boots without keys."""
    global _spotify_client
    if _spotify_client is None:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_SECRET_KEY")
        if not (client_id and client_secret):
            raise RuntimeError("SPOTIFY_CLIENT_ID / SPOTIFY_SECRET_KEY are not set")
        _spotify_client = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
        )
    return _spotify_client


# Create your views here.
def home(request):
    # Render the home page
    return render(request, 'test.html') 

def login(request):
    # Render the login page
    return render(request, 'login.html')

def login_validate(request):
    if request.method == "POST":
        user_input = request.POST.get('user')
        password = request.POST.get('password')

        try:
            # Retrieve the user from the database
            user = User.objects.get(Q(user_name=user_input) | Q(email=user_input))

            # Check if the password is correct
            if check_password(password, user.password):
                # Password is correct, proceed with login
                messages.success(request, "Login successful!")
                
                # Store data in the session
                request.session['credential'] = user_input

                return redirect('dashboard')  # Redirect to the home page
            else:
                messages.error(request, "Incorrect username or password.")
        except User.DoesNotExist:
            messages.error(request, "Incorrect username or password.")

    return render(request, 'login.html')  # Render login template again on error

def sign_up(request):
    # Render the home page
    return render(request, 'signup.html') 

def sign_up_email(request):    
    if request.method == "POST":
        email = request.POST.get('email')

        # Validate the email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "This email is invalid. Make sure it's written like example@email.com")
            return render(request, 'signup.html')  # Render the signup page again with the error message
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            # If email exists, create a warning message and redirect to the login page
            login_url = reverse('login')  # Ensure 'login' is the correct URL name
            login_link = mark_safe(f"This address is already linked to an existing account. To continue, <a href='{login_url}'>log in</a>.")
            messages.warning(request, login_link)
            return render(request, 'signup.html')  # Render the signup page again with the warning message
        
        # If email is valid and doesn't exist, redirect to the next step (password signup) and pass the email
        # next_url = reverse('sign_up_form')
        # query_string = urlencode({'email': email})  # Create query string
        # return HttpResponseRedirect(f'{next_url}?{query_string}')
        request.session['email'] = email
        
        # Redirect to the form to sign up
        return redirect("sign_up_form")

    return render(request, 'signup.html')

def sign_up_form(request):
    # email = request.GET.get('email', None)
    # Retrieve the email from the session
    email = request.session.get('email')

    if email is None:
        # If the email is not found, redirect back to the signup page
        messages.error(request, "Session expired or email not provided.")
        return redirect('sign_up')

    # Render the signup password page
    return render(request, 'signup_form.html', {'email': email})

def save_sign_up(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        display_name = request.POST.get('name')
        birth_date = request.POST.get('birthdate')
        gender = request.POST.get('gender')

        new_user = User(
            email=email,
            password=password,
            display_name=display_name,
            date_of_birth=birth_date,
            gender=gender
        )
        new_user.save()

        messages.success(request, "Account created successfully!")
        return redirect('login')  # Replace with your login URL

    return render(request, 'signup.html')  # Render sign-up form if GET request

def reset_password(request):
    # Render the signup password page
    return render(request, 'reset_password.html')

def reset_password_submission(request):
    if request.method == "POST":
        user_input = request.POST.get('user')
        password = request.POST.get('password')

        try:
            # Retrieve the user from the database using username or email
            user = User.objects.get(Q(user_name=user_input) | Q(email=user_input))
            
            # Hash the password before saving it (important for security)
            user.password = make_password(password)  # Hash password using Django's utility
            user.save()

            # Provide feedback to the user
            messages.success(request, "Password has been successfully reset.")
            return redirect('login')  # Redirect to login page or any other page

        except User.DoesNotExist:
            messages.error(request, "Incorrect email address or username.")
    
    # If form submission fails, stay on the same page with the error message
    return render(request, 'reset_password.html')

def retrieve_display_name(request):
    # Retrieve credential info (either username or email of user)
    credential = request.session.get('credential', '')

    # Retrieve display name
    user = User.objects.filter(Q(user_name=credential) | Q(email=credential)).first()
    display_name = user.display_name

    return display_name

# @login_required(login_url='login')
def dashboard(request):
    display_name = retrieve_display_name(request)
    top_artist_profiles = crawl_artist_img_urls()
    top_song_profiles = crawl_song_img_urls()

    return render(request, 'dashboard.html', {'display_name': display_name, 'top_artist_profiles': top_artist_profiles, 'top_song_profiles': top_song_profiles})

def chatbot(request):
    display_name = retrieve_display_name(request)

    return render(request, 'chatbot.html', {'display_name': display_name})

def get_openai_answer(request):
    if request.method == "POST":
        prompt = request.POST.get("userInput")

        try:
            response = get_openai_client().chat.completions.create(
                model = "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens = 1024,
            )

            # Retrieve the response text
            answer = response.choices[0].message.content

            return JsonResponse({"completion": answer})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        display_name = retrieve_display_name(request)

        return render(request, "chatbot.html", {'display_name': display_name})
    
def download_app(request):
    display_name = retrieve_display_name(request)
    return render(request, 'download_app.html', {'display_name': display_name})

def notification(request):
    display_name = retrieve_display_name(request)

    return render(request, 'notification.html', {'display_name': display_name})

# def library(request):
#     display_name = retrieve_display_name(request)
    
#     return render(request, 'your_library.html', {'display_name': display_name})

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    return redirect('login')

def crawl_artist_img_urls():
    # Retrieve artists' uris from the database
    all_top_artist_uris = Artist.objects.values_list('artist', 'uri')
    random_top_artist_uris = random.sample(list(all_top_artist_uris), 7)

    # Crawl artists' profile picture from Spotify
    profile_data = {}
    for artist in random_top_artist_uris:
        profile_url = get_spotify_client().artist(artist[1])['images'][0]['url']
        profile_data[artist[0]] = profile_url

    return profile_data

def crawl_song_img_urls():
    # Retrieve artists' uris from the database
    all_song_artist_uris = Song.objects.values_list('track_name', 'uri')
    random_top_song_uris = random.sample(list(all_song_artist_uris), 7)

    # Crawl artists' profile picture from Spotify
    profile_data = {}
    for song in random_top_song_uris:
        profile_url = get_spotify_client().track(song[1])['album']['images'][0]['url']
        profile_data[song[0]] = profile_url

    # Remove text starting with "(" from the profile_data dictionary keys
    profile_data = {re.sub(r'\(.*$', '', key): value for key, value in profile_data.items()}

    return profile_data

def like_song(request):
    display_name = retrieve_display_name(request)
    favorite_song_info = retrieve_favorite_song(request)
    favorite_song_count = len(favorite_song_info)
    favorite_song_text = f"{favorite_song_count} song" if favorite_song_count == 1 else f"{favorite_song_count} songs"
    
    # Render the like song page
    return render(request, 'like_song.html', {'display_name': display_name, 'favorite_song': favorite_song_text, "favorite_song_info": favorite_song_info}) 

def retrieve_favorite_song(request):
    # Retrieve credential info (either username or email of user)
    credential = request.session.get('credential')

    # Retrieve user
    user = User.objects.filter(Q(user_name=credential) | Q(email=credential)).first()
    
    if not user:
        return []

    # Retrieve favorite songs with title and date added
    favorite_songs = FavoriteSong.objects.filter(user=user).select_related('song')

    # Format favorite song information
    song_info = [
        {
            "title": fav.song.track_name,
            "added_at": localtime(fav.added_at).strftime("%Y-%m-%d")  # Convert to readable format
        }
        for fav in favorite_songs
    ]

    return song_info

def your_library(request):
    display_name = retrieve_display_name(request)
    # Render the home page
    return render(request, 'your_library.html', {'display_name': display_name}) 