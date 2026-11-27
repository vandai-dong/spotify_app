import os
import re

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials  # To access authorized Spotify data
from utils import save_data  # run from scripts/ingestion/data_collecting (see scripts/ingestion/README.md)

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
data_folder = "data"
file_name = "top_spotify_artist.csv"
path = os.path.join(root_directory, data_folder, file_name)
print("Start reading file")
data = pd.read_csv(path)
print("Finish reading file")

crawled_data = pd.DataFrame(columns=["artist", "uri", "genres", "num_of_followers", "popularity"])
url_list = data['url'].tolist()
uri_list = [re.search(r'artist/([^?]+)', url).group(1) for url in url_list]

# Crawl artists' data from Spotify
print("\nStart crawling data from Spotify")
for i in range(len(uri_list)):
    artist_info = sp.artist(uri_list[i])

    genres = artist_info['genres']
    num_of_followers = artist_info['followers']['total']
    popularity = artist_info['popularity']
    # profile_url = sp.artist(artist_info[1])['images'][0]['url']

    artist_features = [data.iloc[i, 0], uri_list[i], genres, num_of_followers, popularity]
    crawled_data.loc[i] = artist_features

print("Finish crawling data from Spotify")
print(crawled_data.tail(3))


# Save the full data
save_data(crawled_data, "data/artists", "artists", False)