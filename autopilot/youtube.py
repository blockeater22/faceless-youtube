"""YouTube Data API v3 uploader.

Auth uses a long-lived OAuth refresh token (generate once locally with
`python scripts/youtube_authorize.py`, then store the three values as secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

NOTE: Until your Google Cloud project passes the YouTube API audit, videos
uploaded via the API are forced to PRIVATE regardless of the requested status.
You publish them from Studio until the audit is approved. See docs/AUTOPILOT.md.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _credentials():
    from google.oauth2.credentials import Credentials
    cid = os.environ.get("YT_CLIENT_ID")
    secret = os.environ.get("YT_CLIENT_SECRET")
    refresh = os.environ.get("YT_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        raise RuntimeError("Missing YouTube auth: set YT_CLIENT_ID, YT_CLIENT_SECRET, "
                           "YT_REFRESH_TOKEN (run scripts/youtube_authorize.py once).")
    return Credentials(token=None, refresh_token=refresh, client_id=cid,
                       client_secret=secret, token_uri=TOKEN_URI, scopes=SCOPES)


def service():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credentials(), cache_discovery=False)


def _execute(request, tries=5):
    from googleapiclient.errors import HttpError
    for attempt in range(tries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504, 429) and attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


def ensure_playlist(yt, title: str) -> str | None:
    if not title:
        return None
    resp = _execute(yt.playlists().list(part="snippet", mine=True, maxResults=50))
    for item in resp.get("items", []):
        if item["snippet"]["title"].strip() == title.strip():
            return item["id"]
    created = _execute(yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": title},
        "status": {"privacyStatus": "public"}}))
    return created["id"]


def upload_video(yt, path, *, title, description, tags, category_id="22",
                 privacy="private", publish_at=None) -> str:
    from googleapiclient.http import MediaFileUpload
    status = {"privacyStatus": "private" if publish_at else privacy,
              "selfDeclaredMadeForKids": False}
    if publish_at:
        status["publishAt"] = publish_at  # RFC3339 UTC, e.g. 2026-06-23T13:00:00Z
    body = {"snippet": {"title": title[:100], "description": description,
                        "tags": tags, "categoryId": category_id},
            "status": status}
    media = MediaFileUpload(str(path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status_chunk, response = request.next_chunk(num_retries=4)
    return response["id"]


def set_thumbnail(yt, video_id, thumb_path):
    from googleapiclient.http import MediaFileUpload
    _execute(yt.thumbnails().set(
        videoId=video_id, media_body=MediaFileUpload(str(thumb_path), mimetype="image/png")))


def add_to_playlist(yt, playlist_id, video_id):
    if not playlist_id:
        return
    _execute(yt.playlistItems().insert(part="snippet", body={"snippet": {
        "playlistId": playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": video_id}}}))


def publish(artifact, *, privacy="private", publish_at=None, category_id="22") -> str:
    """Upload one produced artifact and return the new video id."""
    yt = service()
    m = artifact["meta"]
    video_id = upload_video(yt, artifact["video"], title=m["title"],
                            description=m["description"], tags=m["tags"],
                            category_id=category_id, privacy=privacy, publish_at=publish_at)
    if Path(artifact["thumb"]).exists():
        set_thumbnail(yt, video_id, artifact["thumb"])
    add_to_playlist(yt, ensure_playlist(yt, m.get("playlist")), video_id)
    return video_id
