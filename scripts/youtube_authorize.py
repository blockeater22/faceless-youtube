#!/usr/bin/env python3
"""One-time: get a YouTube OAuth refresh token to use in autopilot.

Run this LOCALLY (it opens a browser). Prereqs:
  1. Google Cloud project with the "YouTube Data API v3" enabled.
  2. An OAuth client of type "Desktop app" -> note its Client ID + Client secret.
  3. pip install google-auth-oauthlib

Usage:
  YT_CLIENT_ID=... YT_CLIENT_SECRET=... python scripts/youtube_authorize.py
It prints the three values to store as secrets: YT_CLIENT_ID, YT_CLIENT_SECRET,
YT_REFRESH_TOKEN.
"""
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def main():
    cid = os.environ.get("YT_CLIENT_ID") or input("Client ID: ").strip()
    secret = os.environ.get("YT_CLIENT_SECRET") or input("Client secret: ").strip()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("pip install google-auth-oauthlib first.")

    cfg = {"installed": {
        "client_id": cid, "client_secret": secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]}}
    flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        sys.exit("No refresh token returned — revoke prior access and retry with prompt=consent.")
    print("\n=== Store these as secrets (GitHub repo → Settings → Secrets → Actions) ===")
    print(f"YT_CLIENT_ID={cid}")
    print(f"YT_CLIENT_SECRET={secret}")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
