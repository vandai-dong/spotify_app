import glob
import os
import pickle

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

# Function to load and process raw CSV data
def load_raw_data(raw_data_folder):
    root_directory = os.getcwd()
    path = os.path.join(root_directory, raw_data_folder)
    os.chdir(path)  # Point to the raw data path

    csv_files = glob.glob('*.csv')
    list_data = []

    for filename in csv_files:
        data = pd.read_csv(filename)
        list_data.append(data)

    combined_data = pd.concat(list_data)

    # Select relevant columns and drop duplicates
    combined_data = combined_data[['uri', 'artist_names', 'track_name']]
    combined_data.drop_duplicates(subset=['artist_names', 'track_name'],
                                  inplace=True, ignore_index=True, keep="last")

    return combined_data    


# Function to crawl data from Spotify
def spotify_crawl_data(raw_data):
    """
    Crawl features of songs from Spotify.

    Parameters
    ----------
    raw_data : DataFrame
        A DataFrame that contains songs' uri, artist names, and track names.

    Returns
    -------
    DataFrame
        A DataFrame that has more features added from Spotify.
    """
    print("\nStart crawling data")
    data = pd.DataFrame(columns=["uri", "artist_names", "track_name", 
                                  "acousticness", "danceability", "duration_ms",
                                  "energy", "instrumentalness", "liveness", 
                                  "loudness", "mode", "speechiness", "tempo", 
                                  "time_signature", "valence", "uri_artist", 
                                  "artist_pop", "num_followers", 
                                  "artist_genres", "track_pop"])

    selected_features = ["acousticness", "danceability", "duration_ms", "energy", 
                         "instrumentalness", "liveness", "loudness", "mode", 
                         "speechiness", "tempo", "time_signature", "valence"]

    for i in range(0, len(raw_data)):
        try:
            features = sp.audio_features(raw_data.loc[i, "uri"])
            audio_features = [features[0][feature] for feature in selected_features]

            # Continue with processing
            uri_artist = sp.track(raw_data.loc[i, "uri"])['artists'][0]['uri']
            artist_pop = sp.artist(uri_artist)['popularity']
            num_followers = sp.artist(uri_artist)['followers']['total']
            genres_list = sp.artist(uri_artist)["genres"]
            artist_genres = genres_list if genres_list else ["unknown"]
            track_pop = sp.track(raw_data.loc[i, "uri"])['popularity']
            
            extra_features = [uri_artist, artist_pop, num_followers, artist_genres, track_pop]
            data.loc[i] = raw_data.iloc[i, :].tolist() + audio_features + extra_features
            
            print(f"{i + 1}. Retrieved data for song '{raw_data.iloc[i]['track_name']}'")
        except Exception as e:
            print(f"\n{i + 1}. Error processing song '{raw_data.iloc[i]['track_name']}': {e}\n")
            continue  # Skip this entry and continue with the next song

    return data

# Main execution
if __name__ == "__main__":
    ## Load and process raw data
    # raw_data_folder = "data/global_top_songs"
    # combined_data = load_raw_data(raw_data_folder)

    # # Save the combined data to disk
    # save_data(combined_data, "data/processed_global_top_songs", "combined_data")


    ## Read the preprocessed file
    root_directory = os.getcwd()  # Get the current working directory
    data_folder = "data/processed_global_top_songs"
    path = os.path.join(root_directory, data_folder, "combined_data.pickle")
    print("Start reading file")
    with open(path, 'rb') as file:
        combined_data = pickle.load(file)
    print("Finish reading file")

    # Crawl additional features from Spotify
    full_data = spotify_crawl_data(combined_data)
    print(full_data.tail(5))

    # Save the full data
    save_data(full_data, "data/processed_global_top_songs", "full_data", True)
