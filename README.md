# Spindle (Spotify Simulation App)

Spindle is a Django web app that simulates parts of a music-streaming service, dressed as a vinyl record shop:
sign-up / login, a dashboard of top artists and songs, song search, liked songs, playlists (shown as "crates"),
albums with Side A / Side B track lists, a simulated now-playing bar and an AI chat assistant. It runs on a
bundled dataset of ~1,200 globally popular songs and ~110 artists (2023–2024 weekly charts) that comes from
Spotify (see [Data sources](#data-sources)).

> Not affiliated with or endorsed by Spotify. All song, artist and album metadata and cover images belong to
> their respective owners. There is no audio playback.

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
- `fetch_images [--force] [--limit N]` — cache artist/song image URLs and create `Album` rows (name, cover, artist)
  from the Spotify Web API (requires Spotify credentials). The web app itself never calls Spotify.

Images can also be uploaded by hand in the Django admin (Artists, Songs, Albums). An upload overrides the cached
URL and is never overwritten by `fetch_images`. Uploads go to `media/` (git-ignored) and are served by Django only
when `DJANGO_DEBUG` is on; use real storage / a CDN in production. Requires Pillow (in `requirements/base.txt`).

## Design and inspiration

The UI is called **Spindle**. The app simulates a streaming service, but you can't hear anything, so the interface
leans on what you can *see*: the ritual of listening to a record. The look was first drawn as a design canvas
(desktop "now spinning" screen, phone player, phone crates) and then built into the Django templates.

**Inspiration**

- **The record shop and the listening room.** A warm, dark, low-light palette, like a room lit by a single lamp,
  instead of the usual black-and-neon streaming look.
- **Vinyl as the interface.** Songs are records, playlists are *crates* you dig through, albums are sleeves with a
  shaded spine, and an album's tracks are split into **Side A / Side B**. Labels such as "33⅓ RPM · 12" LP" echo
  the print on a real sleeve.
- **Hi-fi equipment.** The song page is a turntable: a spinning record with an orange centre label and a tonearm.
  The mini player carries a small record that spins only while something is playing.

**Design system** (tokens live in [`static/css/tokens.css`](static/css/tokens.css))

| Role | Value |
| --- | --- |
| Background / sidebar / surface | `#15110E` / `#0F0C0A` / `#241C17` |
| Border | `#3A2E26` |
| Text / muted text | `#F1E7D4` / `#B9AB94` |
| Accent (record-label orange) | `#E8602C`, focus ring `#F4C26B` |
| Headings | [Fraunces](https://fonts.google.com/specimen/Fraunces) (serif display) |
| Body | [DM Sans](https://fonts.google.com/specimen/DM+Sans) |
| Labels, times, track numbers | [DM Mono](https://fonts.google.com/specimen/DM+Mono) |

**How it is built**

- Bootstrap 5.3 (dark theme) is still the base; `static/css/app.css` re-points its variables and components at the
  tokens, so unmodified pages pick up the theme automatically.
- The record, turntable, sleeves and mini player are pure CSS / inline SVG: no images or extra dependencies.
  `partials/_record.html` is the shared record; `{% cover obj shape='sleeve' %}` renders album-sleeve covers.
- `static/js/player.js` toggles an `is-playing` class on `<body>` so the records only spin during playback; the
  animation is disabled for visitors who prefer reduced motion.
- Standalone pages (login, sign-up, password reset, 404 and the public shared-crate page) load `tokens.css` plus
  `auth.css` / `spindle-404.css`, so they match the signed-in app.
- Accessibility: visible focus rings, 44 px touch targets for controls, text at 4.5:1 contrast or better.
- Wording is a display-only change: a playlist tagged `Playlist` in the database is shown as a "Crate".

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

All catalog data originates from Spotify:

1. **Artists:** [Spotify Artist Metadata Top 10k](https://www.kaggle.com/datasets/jackharding/spotify-artist-metadata-top-10k)
   (Kaggle), a dataset of Spotify artist metadata.
2. **Songs:** weekly global top-songs charts from
   [charts.spotify.com](https://charts.spotify.com/charts/view/regional-global-weekly/latest), enriched through the
   Spotify Web API (the data carries tempo, mode, danceability and similar audio features). The crawling tools are
   in `scripts/ingestion/`; the processed CSVs are bundled in `data/`.
3. **Cover images:** artist, song and album image URLs are fetched from the Spotify Web API by `fetch_images`
   (needs your own Spotify credentials) and cached in the database. The running web app never calls Spotify.

Fonts are loaded from Google Fonts (SIL Open Font License); icons are [Font Awesome](https://fontawesome.com/) Free.
The sample album, artist and song names in the design canvas are placeholders and are not part of the dataset.
