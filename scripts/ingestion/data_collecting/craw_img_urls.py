import os
import pickle

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials  # To access authorized Spotify data

# Load keys from .env file
load_dotenv()

# Spotify API Credentials
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_SECRET_KEY")

# Initialize Spotipy client
client_credentials_manager = SpotifyClientCredentials(client_id=client_id,
                                                      client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

## Read the preprocessed file
root_directory = os.getcwd()  # Get the current working directory
data_folder = "data/processed_global_top_songs"
path = os.path.join(root_directory, data_folder, "combined_data.pickle")
print("Start reading file")
with open(path, 'rb') as file:
    data = pickle.load(file)
print("Finish reading file")


print(data.columns)