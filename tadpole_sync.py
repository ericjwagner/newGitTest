#!/usr/bin/env python3
"""Weekly Tadpoles photo sync for YourChild.

Logs into Tadpoles using the unofficial mobile-app API (reverse engineered by
https://github.com/tylerhall/tadpoles-api and other community projects — Tadpoles
has no first-party API), pulls the last N days of events, and downloads photo/video
attachments.

Multi-child detection: Tadpoles' own app blocks downloading a photo that has other
kids tagged in it (a client-side friction/consent dialog). The events API has no
documented field naming which children are tagged in a given photo, so that can't
be checked from the JSON. Instead, each downloaded image is run through an offline
face detector (OpenCV's YuNet model, fetched to data/ on first use): photos with
exactly one detected face are kept, photos with more than one are deleted. This
mirrors what the friction dialog is actually reacting to. Videos aren't filtered
this way since they can't be face-counted the same way; they're always kept.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import cv2
import requests

DATA_DIR = Path(__file__).parent / "data"
FACE_MODEL_PATH = DATA_DIR / "face_detection_yunet.onnx"
FACE_MODEL_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)


def ensure_face_model():
    if FACE_MODEL_PATH.exists():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    r = requests.get(FACE_MODEL_URL, timeout=30)
    r.raise_for_status()
    FACE_MODEL_PATH.write_bytes(r.content)

BASE = "https://www.tadpoles.com"
STANDARD_HEADERS = {
    "content-type": "application/x-www-form-urlencoded; charset=utf-8",
    "accept": "*/*",
    "x-titanium-id": "c5a5bca5-43c7-4b8f-b82a-fe1de0e4793c",
    "x-requested-with": "XMLHttpRequest",
    "accept-language": "en-us",
    "user-agent": (
        "Appcelerator Titanium/7.1.1 (iPhone/12.2; iOS; en_US;), "
        "Appcelerator Titanium/7.1.1 (iPhone/12.2; iOS; en_US;) (gzip)"
    ),
}

def count_faces(image_path):
    """Return the number of faces detected in an image file."""
    ensure_face_model()
    detector = cv2.FaceDetectorYN_create(
        str(FACE_MODEL_PATH), "", (320, 320), score_threshold=0.5
    )
    img = cv2.imread(str(image_path))
    if img is None:
        return 0
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    return 0 if faces is None else len(faces)


class TadpolesClient:
    def __init__(self, email, password):
        self.session = requests.Session()
        self.session.headers.update(STANDARD_HEADERS)
        self.email = email
        self.password = password

    def login(self):
        r = self.session.post(
            f"{BASE}/auth/login",
            data={"service": "tadpoles", "email": self.email, "password": self.password},
        )
        r.raise_for_status()
        if not self.session.cookies:
            raise RuntimeError("Tadpoles login did not return an auth cookie")

        r2 = self.session.post(
            f"{BASE}/remote/v1/athome/admit",
            data={
                "state": "client",
                "mac": "00000000-0000-0000-0000-000000000000",
                "os_name": "iphone",
                "app_version": "8.10.24",
                "ostype": "64bit",
                "tz": "UTC",
                "battery_level": "-1",
                "locale": "en",
                "logged_in": "0",
                "device_id": "00000000-0000-0000-0000-000000000000",
                "v": "2",
            },
        )
        r2.raise_for_status()

    def events(self, earliest_ts, latest_ts):
        events = []
        cursor = ""
        while True:
            params = {
                "num_events": "100",
                "state": "client",
                "direction": "range",
                "earliest_event_time": int(earliest_ts),
                "latest_event_time": int(latest_ts),
                "cursor": cursor,
            }
            r = self.session.get(f"{BASE}/remote/v1/events", params=params)
            r.raise_for_status()
            data = r.json()
            events.extend(data.get("events", []))
            cursor = data.get("cursor", "")
            if not cursor:
                break
        return events

    def download_attachment(self, key, dest_path):
        r = self.session.get(f"{BASE}/remote/v1/attachment", params={"key": key}, stream=True)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)


def extension_for(mime_type):
    return {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4"}.get(mime_type, "")


def sync(email, password, child_name, days, out_dir):
    client = TadpolesClient(email, password)
    client.login()

    now = time.time()
    earliest = now - days * 86400
    events = client.events(earliest, now)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded, skipped_multi_face, skipped_not_child = 0, 0, 0

    for event in events:
        if event.get("type") != "Activity":
            continue
        if event.get("member_display") != child_name:
            skipped_not_child += 1
            continue

        event_time = event.get("event_time", now)
        date_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(event_time))

        for attachment in event.get("new_attachments", []):
            key = attachment.get("key")
            mime_type = attachment.get("mime_type", "")
            ext = extension_for(mime_type)
            if not key or not ext:
                continue
            filename = out_dir / f"{date_str}-{child_name}-{key}{ext}"
            if filename.exists():
                continue
            client.download_attachment(key, filename)

            if mime_type == "image/jpeg" or mime_type == "image/png":
                faces = count_faces(filename)
                if faces != 1:
                    filename.unlink()
                    skipped_multi_face += 1
                    print(f"skipped {filename.name} ({faces} faces detected)")
                    continue

            downloaded += 1
            print(f"downloaded {filename}")

    print(
        f"done: downloaded={downloaded} "
        f"skipped_multi_face={skipped_multi_face} "
        f"skipped_not_target_child={skipped_not_child}"
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=os.environ.get("TADPOLES_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("TADPOLES_PASSWORD"))
    parser.add_argument("--child-name", default=os.environ.get("TADPOLES_CHILD_NAME", "YourChild"))
    parser.add_argument("--days", type=int, default=int(os.environ.get("TADPOLES_SYNC_DAYS", "8")))
    parser.add_argument("--out-dir", default=os.environ.get("TADPOLES_OUT_DIR", "photos"))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("TADPOLES_EMAIL and TADPOLES_PASSWORD are required (env vars or --email/--password)", file=sys.stderr)
        return 1

    return sync(args.email, args.password, args.child_name, args.days, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
