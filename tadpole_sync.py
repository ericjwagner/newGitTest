#!/usr/bin/env python3
"""Weekly Tadpoles photo sync for YourChild.

Logs into Tadpoles using the unofficial mobile-app API (reverse engineered by
https://github.com/tylerhall/tadpoles-api and other community projects — Tadpoles
has no first-party API), pulls the last N days of events, and downloads photo/video
attachments.

Multi-child detection: Tadpoles' own app blocks downloading a photo that has other
kids tagged in it (privacy friction dialog), but that block is client-side only —
the API itself doesn't expose a clean "how many kids are in this photo" field in the
events response. As a best-effort heuristic, an event is treated as "YourChild plus
other kids" (and skipped) if its JSON contains any of the CHILD_LIST_FIELDS below
with more than one entry. If none of those fields are present, the photo is treated
as solo and downloaded. Run with --dump-schema once to inspect a raw event and
confirm/adjust CHILD_LIST_FIELDS for your account if Tadpoles' schema differs.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

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

# Candidate field names that might list multiple tagged children on an event.
# member_display is always the single "primary" child string and is not included.
CHILD_LIST_FIELDS = [
    "associated_students",
    "other_members",
    "tagged_kids",
    "tagged_children",
    "members",
    "group_members",
    "students",
]


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


def is_multi_child_event(event):
    for field in CHILD_LIST_FIELDS:
        value = event.get(field)
        if isinstance(value, list) and len(value) > 1:
            return True
    return False


def extension_for(mime_type):
    return {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4"}.get(mime_type, "")


def sync(email, password, child_name, days, out_dir, dump_schema=False):
    client = TadpolesClient(email, password)
    client.login()

    now = time.time()
    earliest = now - days * 86400
    events = client.events(earliest, now)

    if dump_schema:
        activity_events = [e for e in events if e.get("type") == "Activity"]
        sample = activity_events[0] if activity_events else (events[0] if events else None)
        print(json.dumps(sample, indent=2))
        return 0

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded, skipped_other_child, skipped_not_child = 0, 0, 0

    for event in events:
        if event.get("type") != "Activity":
            continue
        if event.get("member_display") != child_name:
            skipped_not_child += 1
            continue
        if is_multi_child_event(event):
            skipped_other_child += 1
            continue

        event_time = event.get("event_time", now)
        date_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(event_time))

        for attachment in event.get("new_attachments", []):
            key = attachment.get("key")
            ext = extension_for(attachment.get("mime_type", ""))
            if not key or not ext:
                continue
            filename = out_dir / f"{date_str}-{child_name}-{key}{ext}"
            if filename.exists():
                continue
            client.download_attachment(key, filename)
            downloaded += 1
            print(f"downloaded {filename}")

    print(
        f"done: downloaded={downloaded} "
        f"skipped_multi_child={skipped_other_child} "
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
    parser.add_argument(
        "--dump-schema",
        action="store_true",
        help="Print one raw event's JSON and exit, to inspect field names for your account.",
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        print("TADPOLES_EMAIL and TADPOLES_PASSWORD are required (env vars or --email/--password)", file=sys.stderr)
        return 1

    return sync(args.email, args.password, args.child_name, args.days, args.out_dir, args.dump_schema)


if __name__ == "__main__":
    sys.exit(main())
