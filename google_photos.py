"""Minimal Google Photos Library API client: refresh a token, upload one file."""

import mimetypes

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://photoslibrary.googleapis.com/v1/uploads"
BATCH_CREATE_URL = "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"


def get_access_token(client_id, client_secret, refresh_token):
    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def upload_to_library(access_token, file_path, mime_type=None):
    """Upload one file's bytes and create a library media item from it."""
    mime_type = mime_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    filename = file_path.name if hasattr(file_path, "name") else str(file_path)

    with open(file_path, "rb") as f:
        data = f.read()

    upload_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
        "X-Goog-Upload-Content-Type": mime_type,
        "X-Goog-Upload-Protocol": "raw",
    }
    r = requests.post(UPLOAD_URL, headers=upload_headers, data=data, timeout=60)
    r.raise_for_status()
    upload_token = r.text

    create_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "newMediaItems": [
            {
                "simpleMediaItem": {"fileName": filename, "uploadToken": upload_token},
            }
        ]
    }
    r = requests.post(BATCH_CREATE_URL, headers=create_headers, json=body, timeout=30)
    r.raise_for_status()
    result = r.json()["newMediaItemResults"][0]
    status = result.get("status", {})
    if status.get("code"):
        raise RuntimeError(f"Google Photos upload failed for {filename}: {status}")
    return result["mediaItem"]["id"]
