#!/usr/bin/env python3
"""Run this LOCALLY (not in CI) to get a Google Photos refresh token.

Since this is a personal, unverified Google OAuth app, the refresh token it
issues expires after 7 days. Re-run this script whenever the weekly sync
starts failing with a Google auth error, and update the GOOGLE_REFRESH_TOKEN
GitHub secret with the new value it prints.

Usage:
    pip install -r requirements-dev.txt
    python get_google_token.py --client-id ... --client-secret ...
"""

import argparse
import webbrowser

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/photoslibrary.appendonly"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    args = parser.parse_args()

    auth_url = (
        f"{AUTH_URL}?client_id={args.client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    print(f"Opening browser to authorize:\n{auth_url}\n")
    webbrowser.open(auth_url)

    code = input("Paste the authorization code Google gives you: ").strip()

    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    r.raise_for_status()
    tokens = r.json()

    print("\nSuccess. Set this as the GOOGLE_REFRESH_TOKEN GitHub secret:\n")
    print(tokens["refresh_token"])


if __name__ == "__main__":
    main()
