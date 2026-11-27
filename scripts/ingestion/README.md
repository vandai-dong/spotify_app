# Data ingestion (offline tooling)

These scripts and the notebook built the bundled CSVs in `/data`. They are **not** part of the web app.

- Install: `pip install -r requirements/ingestion.txt`
- Needs `SPOTIFY_CLIENT_ID` / `SPOTIFY_SECRET_KEY` in `.env`. Note that Spotify has restricted several Web API endpoints
  (audio features, related artists, ...) for newer apps, so re-crawling may no longer work; the committed CSVs are the source of truth.
- Run from the repository root, e.g. `python scripts/ingestion/data_collecting/artist_data_crawl.py` (paths are relative to the root).
- To load data into the app, use the Django commands instead: `python manage.py import_songs` and `python manage.py import_artists`.
