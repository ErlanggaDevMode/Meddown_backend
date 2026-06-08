# MedDown Backend — yt-dlp Wrapper API

A lightweight Flask wrapper around `yt-dlp` that extracts media info from
YouTube, TikTok, Instagram, Facebook, Twitter/X and 1000+ other sites.

## Deploy to Railway (free tier)

1. Push this `backend/` folder to a new GitHub repo (or a subfolder).
2. Go to [railway.app](https://railway.app), create a new project → **Deploy from GitHub**.
3. Railway will auto-detect the `Dockerfile`.
4. Set env var `MEDDOWN_API_TOKEN` (optional — leave empty to skip auth).
5. After deploy you get a URL like `https://meddown-api-production-xxxx.up.railway.app`.
6. Copy that URL into `CONFIG.API_ENDPOINT` in `assets/js/main.js`.

## Deploy to Render (free tier)

1. Push this `backend/` folder to GitHub.
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo.
3. Set root directory to `backend/`, Render will pick up `render.yaml`.
4. Set env var `MEDDOWN_API_TOKEN` if desired.
5. Copy the live URL into `CONFIG.API_ENDPOINT`.

## Local Development

```bash
cd backend
pip install -r requirements.txt
python app.py
# → http://localhost:8000/health
# → http://localhost:8000/api/resolve?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Endpoints

| Method | Path             | Description                    |
|--------|------------------|--------------------------------|
| GET    | `/health`        | Health check                   |
| GET    | `/api/resolve`   | Extract media info from a URL  |

### `/api/resolve` query params

| Param | Required | Description                   |
|-------|----------|-------------------------------|
| `url` | yes      | The media URL to resolve      |

### Response schema

```json
{
  "success": true,
  "media": {
    "id": "dQw4w9WgXcQ",
    "platform": "youtube",
    "title": "...",
    "author": "...",
    "thumbnail": "https://...",
    "duration": 213,
    "formats": [
      {
        "id": "mp4_1080p",
        "label": "1080p",
        "extension": "mp4",
        "quality": "1080p",
        "filesize": 142000000,
        "url": "https://direct-media-url..."
      }
    ]
  },
  "error": null
}
```
