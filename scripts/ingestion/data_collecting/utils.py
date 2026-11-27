import os
import pickle

import pandas as pd


def save_data(data, subfolder, file_name, append=False):
    """
    Save DataFrame as a pickle and CSV file.

    Parameters
    ----------
    data : DataFrame
        A DataFrame that contains all songs' features
    subfolder : str
        A path that leads to the folder that contains all data files
    file_name: str
        Name of the file to be saved
    append: boolean
        False if creating a new file or True if appending the new data to existing files

    Returns
    -------
    None
    """
    root_directory = os.getcwd()  # Get the current working directory
    path = os.path.join(root_directory, subfolder)

    # Create the directory and all its parents if they don't exist
    os.makedirs(path, exist_ok=True)  # This will create the directory if it doesn't exist

    # Change to the new directory
    os.chdir(path)

    # Check if append mode is selected and the pickle file exists
    pickle_file_path = f'{file_name}.pickle'
    if append and os.path.exists(pickle_file_path):
        # Load existing data
        with open(pickle_file_path, 'rb') as picklefile:
            try:
                existing_data = pickle.load(picklefile)
            except EOFError:
                existing_data = []
        
        # Append the new data
        if isinstance(existing_data, list):
            existing_data.append(data)
        else:
            existing_data = [existing_data, data]

        # Save the updated data
        with open(pickle_file_path, 'wb') as picklefile:
            pickle.dump(existing_data, picklefile)
        print(f"Data appended successfully to {file_name}.pickle")
    else:
        # Save new or overwrite existing pickle file
        with open(pickle_file_path, 'wb') as picklefile:
            pickle.dump(data, picklefile)
        print(f"Pickle file saved successfully: {file_name}.pickle")

    # Save as CSV (overwrite or create new CSV)
    if isinstance(data, pd.DataFrame):
        if append and os.path.exists(f"{file_name}.csv"):
            # Append without writing the header
            data.to_csv(f"{file_name}.csv", mode='a', index=False, header=False)
            print(f"Data appended to existing CSV file: {file_name}.csv")
        else:
            # Create a new file with header
            data.to_csv(f"{file_name}.csv", mode='w', index=False)
            print(f"CSV file created and saved successfully: {file_name}.csv")