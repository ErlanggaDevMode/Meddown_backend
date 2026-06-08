"""
MedDown Backend — yt-dlp Wrapper API
Deploy to Railway / Render for a free cloud endpoint.

Endpoints:
  GET  /api/resolve?url=<media_url>   → returns normalized media info
  GET  /health                        → health check
"""

import os
import json
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # Allow MedDown frontend from any origin

# Optional: simple bearer token auth
API_TOKEN = os.environ.get('MEDDOWN_API_TOKEN', '')


def require_auth(f):
    """Decorator — skip auth when MEDDOWN_API_TOKEN is not set."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if API_TOKEN:
            auth = request.headers.get('Authorization', '')
            if auth != f'Bearer {API_TOKEN}':
                return jsonify(success=False, error='Unauthorized'), 401
        return f(*args, **kwargs)

    return decorated


# ──────────────────────────── helpers ────────────────────────────

QUALITY_ORDER = ['1080', '720', '480', '360']


def _build_format_entry(fmt):
    """Normalize a single yt-dlp format dict into MedDown schema."""
    height = fmt.get('height') or 0
    ext = fmt.get('ext', 'mp4')
    vcodec = fmt.get('vcodec', 'none')
    acodec = fmt.get('acodec', 'none')
    filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0

    # Determine label
    if vcodec != 'none' and acodec != 'none':
        label = f'{height}p' if height else 'Video'
        quality = f'{height}p' if height else 'best'
        fmt_id = f'{ext}_{height}p' if height else f'{ext}_best'
    elif acodec != 'none':
        abr = fmt.get('abr') or fmt.get('tbr') or 128
        label = f'Audio {int(abr)}kbps'
        quality = f'{int(abr)}kbps'
        ext = fmt.get('ext', 'mp3')
        fmt_id = f'{ext}_{int(abr)}'
    else:
        return None  # skip video-only streams without audio

    return {
        'id': fmt_id,
        'label': label,
        'extension': ext,
        'quality': quality,
        'filesize': int(filesize),
        'url': fmt.get('url', ''),
        '_height': height,  # internal, stripped before response
    }


def _normalize(info: dict, url: str) -> dict:
    """
    Turn raw yt-dlp info_dict into the MedDown normalized response
    schema defined in system-architecture.md §3.3.
    """
    # Detect platform from extractor key
    extractor = (info.get('extractor_key') or info.get('extractor') or '').lower()
    platform_map = {
        'youtube': 'youtube', 'youtubeShorts': 'youtube',
        'instagram': 'instagram', 'instagramreel': 'instagram',
        'tiktok': 'tiktok',
        'facebook': 'facebook', 'facebookreel': 'facebook',
        'twitter': 'twitter', 'twitterbroadcast': 'twitter',
    }
    platform = 'unknown'
    for key, val in platform_map.items():
        if key in extractor:
            platform = val
            break

    # Build format list
    raw_formats = info.get('formats') or []
    formats = []
    seen_labels = set()

    for rf in raw_formats:
        entry = _build_format_entry(rf)
        if entry and entry['url'] and entry['label'] not in seen_labels:
            seen_labels.add(entry['label'])
            formats.append(entry)

    # Sort: video by height descending, then audio
    formats.sort(key=lambda x: (x['_height'] == 0, -x['_height']))

    # Strip internal keys
    for f in formats:
        f.pop('_height', None)

    # If no individual formats resolved, use the "best" merged URL
    if not formats and info.get('url'):
        formats.append({
            'id': 'best',
            'label': 'Best Quality',
            'extension': info.get('ext', 'mp4'),
            'quality': 'best',
            'filesize': info.get('filesize') or info.get('filesize_approx') or 0,
            'url': info['url'],
        })

    return {
        'success': True,
        'media': {
            'id': info.get('id', hashlib.md5(url.encode()).hexdigest()[:11]),
            'platform': platform,
            'title': info.get('title', 'Untitled'),
            'author': info.get('uploader') or info.get('channel') or 'Unknown',
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration') or 0,
            'formats': formats,
        },
        'error': None,
    }


# ──────────────────────────── routes ─────────────────────────────

@app.route('/health')
def health():
    return jsonify(status='ok', service='meddown-ytdlp')


@app.route('/api/resolve')
@require_auth
def resolve():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify(success=False, error='Missing url parameter'), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        # Don't actually download — just extract info
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'socket_timeout': 15,
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            return jsonify(success=False, error='Konten ini tidak dapat diakses'), 403

        result = _normalize(info, url)
        return jsonify(result)

    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if 'private' in msg or 'restricted' in msg or 'unavailable' in msg:
            return jsonify(success=False, error='Konten ini tidak dapat diakses'), 403
        if 'not found' in msg or '404' in msg:
            return jsonify(success=False, error='Media tidak ditemukan'), 404
        if 'unsupported' in msg:
            return jsonify(success=False, error='Platform belum didukung'), 400
        # Generic extraction error
        return jsonify(success=False, error=f'Gagal mengambil media: {str(e)[:120]}'), 500

    except Exception as e:
        return jsonify(success=False, error=f'Server error: {str(e)[:120]}'), 500


# ──────────────────────────── entry ──────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
