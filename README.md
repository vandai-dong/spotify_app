# Spotify Simulation App

A Django web app that simulates parts of Spotify: sign-up / login, a dashboard of top artists and songs,
song search, liked songs, playlists (your library) and an AI chat assistant. It runs on a bundled dataset of
~1,200 globally popular songs and ~110 artists (2023–2024 weekly charts).

> Not affiliated with Spotify. There is no audio playback.

## Quick start

Requires Python 3.12+ (developed on 3.14).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env          # optional: only needed for the chatbot / image fetching
python manage.py migrate
python manage.py import_songs
python manage.py import_artists
python manage.py createsuperuser   # optional, for /admin
python manage.py runserver
```

Open <http://127.0.0.1:8000/>, sign up, and log in with your email (or username).

The app boots without any API keys. The dashboard shows placeholder covers until you run `fetch_images`;
the chatbot answers "not configured" until you set `OPENAI_API_KEY`.

## Configuration (`.env`)

| Variable | Purpose | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key — **set a real one outside local dev** | insecure dev key |
| `DJANGO_DEBUG` | `true` / `false` | `true` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated hosts | `localhost,127.0.0.1` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | chat assistant | unset, `gpt-4o-mini` |
| `SPOTIFY_CLIENT_ID`, `SPOTIFY_SECRET_KEY` | only for `fetch_images` | unset |
| `DJANGO_EMAIL_BACKEND` | password-reset email; prints to the console by default | console |

With `DJANGO_DEBUG=false`, also run `python manage.py collectstatic` (WhiteNoise serves `staticfiles/`).

## Management commands

- `import_songs [csv]`, `import_artists [csv]` — load the bundled CSVs (idempotent; safe to re-run).
- `fetch_images [--force] [--limit N]` — cache artist/album image URLs from the Spotify Web API in the database
  (requires Spotify credentials). The web app itself never calls Spotify.

## Project layout

```
config/            settings, root URLs, wsgi/asgi
apps/accounts/     User model (email-or-username login), sign-up, password reset
apps/catalog/      Song, Artist, dashboard, search, import/fetch commands
apps/library/      Playlists, playlist songs, liked songs
apps/assistant/    OpenAI-backed chat assistant (login required, rate limited)
templates/         base.html + shared partials; per-app templates
static/            CSS / JS / images
data/              bundled CSV datasets
scripts/ingestion/ offline crawling tools and notebook (not part of the web app)
```

## Development

```bash
pytest                         # test suite
ruff check .                   # lint
python manage.py makemigrations --check --dry-run
```

CI (GitHub Actions) runs the same checks on every push.

## Data sources

1. Artist dataset: [Spotify Artist Metadata Top 10k](https://www.kaggle.com/datasets/jackharding/spotify-artist-metadata-top-10k)
2. Weekly global top-songs charts from [charts.spotify.com](https://charts.spotify.com/charts/view/regional-global-weekly/latest), enriched via the Spotify Web API.
