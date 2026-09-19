# Tadpoles weekly photo sync

Downloads YourChild's photos from Tadpoles every week via GitHub Actions and commits
them to `photos/`.

Tadpoles has no first-party API. This uses the unofficial mobile-app API
reverse-engineered by the community (e.g.
[tylerhall/tadpoles-api](https://github.com/tylerhall/tadpoles-api)).

## Setup

1. In repo Settings → Secrets and variables → Actions, add secrets:
   - `TADPOLES_EMAIL` — your Tadpoles login email
   - `TADPOLES_PASSWORD` — your **Tadpoles-specific** password (not Google/Apple sign-in;
     create one from the Tadpoles app/site if you normally log in another way)
2. Optionally add a repo variable `TADPOLES_CHILD_NAME` (defaults to `YourChild`) —
   must exactly match how the child's name appears in Tadpoles' `member_display` field.
3. The workflow runs every Sunday at 13:00 UTC, or trigger it manually from the
   Actions tab ("Run workflow").

## Multi-child photo filtering

The Tadpoles app shows a confirmation prompt before downloading a photo that has
other kids tagged in it, but that's a client-side UI check — the events API has
no documented field naming which children are tagged in a photo. Instead, every
downloaded image is run through an offline face detector (OpenCV's YuNet model,
downloaded to `data/` on first use): photos with exactly one detected face are
kept, photos with more than one face are deleted. Videos aren't filtered this
way and are always kept.

This is verified by `test_face_filter.py` against real one-face/two-face fixture
photos in `tests/fixtures/`, run automatically on every push by
`.github/workflows/test.yml`.

## Local run

```
pip install -r requirements.txt
TADPOLES_EMAIL=you@example.com TADPOLES_PASSWORD=... python tadpole_sync.py
```

## Running tests

```
pip install -r requirements-dev.txt
pytest test_face_filter.py -v
```
