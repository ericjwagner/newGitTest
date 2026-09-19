# Tadpoles weekly photo sync

Downloads Madden's photos from Tadpoles every week via GitHub Actions and commits
them to `photos/`.

Tadpoles has no first-party API. This uses the unofficial mobile-app API
reverse-engineered by the community (e.g.
[tylerhall/tadpoles-api](https://github.com/tylerhall/tadpoles-api)).

## Setup

1. In repo Settings → Secrets and variables → Actions, add secrets:
   - `TADPOLES_EMAIL` — your Tadpoles login email
   - `TADPOLES_PASSWORD` — your **Tadpoles-specific** password (not Google/Apple sign-in;
     create one from the Tadpoles app/site if you normally log in another way)
2. Optionally add a repo variable `TADPOLES_CHILD_NAME` (defaults to `Madden`) —
   must exactly match how the child's name appears in Tadpoles' `member_display` field.
3. The workflow runs every Sunday at 13:00 UTC, or trigger it manually from the
   Actions tab ("Run workflow").

## Multi-child photo filtering

The Tadpoles app shows a confirmation prompt before downloading a photo that has
other kids tagged in it. That check is client-side only — it isn't a documented
field in the events API. `tadpole_sync.py` looks for a handful of likely field
names (`CHILD_LIST_FIELDS`) that might list multiple tagged children, and skips
any event where one of those has more than one entry. If Tadpoles' real schema
uses a different field, run:

```
python tadpole_sync.py --dump-schema
```

to print a raw event and see what's actually there, then adjust
`CHILD_LIST_FIELDS` in `tadpole_sync.py` accordingly. Until confirmed, this is a
best-effort filter, not a guarantee.

## Local run

```
pip install -r requirements.txt
TADPOLES_EMAIL=you@example.com TADPOLES_PASSWORD=... python tadpole_sync.py
```
