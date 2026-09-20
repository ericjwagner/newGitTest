# Tadpoles weekly photo sync

![Test](https://github.com/ericjwagner/tadpoles/actions/workflows/test.yml/badge.svg)

Uploads your child's photos from Tadpoles to Google Photos every week via
GitHub Actions.

Tadpoles has no first-party API. This uses the unofficial mobile-app API
reverse-engineered by the community (e.g.
[tylerhall/tadpoles-api](https://github.com/tylerhall/tadpoles-api)).

> **Disclaimer:** This talks to a private, undocumented Tadpoles API endpoint
> that isn't officially supported. It could change or break at any time
> without notice, and using it is not endorsed by Tadpoles/HiMama. Use at
> your own risk.

## Setup

### Tadpoles

In repo Settings → Secrets and variables → Actions, add secrets:
- `TADPOLES_EMAIL` — your Tadpoles login email
- `TADPOLES_PASSWORD` — your **Tadpoles-specific** password (not Google/Apple sign-in;
  create one from the Tadpoles app/site if you normally log in another way)

Add a repo variable (Settings → Secrets and variables → Actions → Variables tab)
`TADPOLES_CHILD_NAME` — must exactly match how your child's name appears in
Tadpoles' `member_display` field.

### Google Photos

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project,
   enable the **Photos Library API**, and configure the OAuth consent screen as
   **External** + **Testing**, adding your own Google account as a test user.
2. Create an **OAuth client ID** of type **Desktop app**. Note the client ID and secret.
3. Locally (not in CI): `pip install -r requirements-dev.txt`, then
   `python get_google_token.py --client-id ... --client-secret ...`. It opens a
   browser for you to approve access, then prints a refresh token.
4. Add three more repo secrets: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
   `GOOGLE_REFRESH_TOKEN`.

**Important:** because this is an unverified personal app, the refresh token
expires after 7 days. When the weekly workflow starts failing with a Google
auth error, re-run `get_google_token.py` locally and update the
`GOOGLE_REFRESH_TOKEN` secret. Going through Google's app verification would
remove this, but it's a multi-week review meant for public apps, not worth it
for a single-user tool.

The workflow runs every Sunday at 13:00 UTC, or trigger it manually from the
Actions tab ("Run workflow").

## Multi-child photo filtering

The Tadpoles app shows a confirmation prompt before downloading a photo that has
other kids tagged in it, but that's a client-side UI check — the events API has
no documented field naming which children are tagged in a photo. Instead, every
downloaded image is run through an offline face detector (OpenCV's YuNet model,
downloaded to `data/` on first use): photos with exactly one detected face are
uploaded, photos with more than one face are dropped. Videos aren't filtered
this way and are always uploaded.

This is verified by `test_face_filter.py` against real one-face/two-face fixture
photos, run automatically on every push by `.github/workflows/test.yml`.

## Avoiding duplicates

Uploaded attachment keys are tracked in `uploaded_keys.txt`, persisted between
runs via a GitHub Actions cache (not committed to the repo). The sync window is
8 days even though the cron is weekly, so a 1-day overlap is expected —
`uploaded_keys.txt` is what prevents re-uploading anything from that overlap.

## Local run

```
pip install -r requirements.txt
TADPOLES_EMAIL=you@example.com TADPOLES_PASSWORD=... \
GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... \
python tadpole_sync.py
```

## Running tests

```
pip install -r requirements-dev.txt
pytest test_face_filter.py -v
```

## License

[MIT](LICENSE)
