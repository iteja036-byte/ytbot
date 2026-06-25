"""
ytbot/upload.py
Uploads final_reel.mp4 to configured platforms.

Supported platforms:
  - TikTok   (via TikTok-uploader or selenium-based uploader)
  - Instagram Reels (via instagrapi)
  - YouTube Shorts  (via google-api-python-client)

Set credentials in environment variables or .env file.
See config.py for variable names.

Each uploader is isolated — failure on one platform does NOT stop others.
"""

import os
import json
import sys
import subprocess

import logger
from config import (
    FINAL_REEL, BRAIN_OUTPUT,
    TIKTOK_SESSION_ID,
    INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD,
    YOUTUBE_CLIENT_SECRETS,
    BASE_DIR
)
from validator import validate_brain_output


def load_brain_output() -> dict | None:
    if not os.path.exists(BRAIN_OUTPUT):
        logger.err("brain_output.json not found. Run brain.py first.")
        return None
    try:
        with open(BRAIN_OUTPUT, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.err(f"brain_output.json invalid: {e}")
        return None
    if not validate_brain_output(data):
        return None
    return data


def build_description(data: dict) -> str:
    """Combine caption + hashtags into a single post description."""
    caption  = data["caption"]
    tags     = data.get("hashtag_str") or " ".join(data.get("hashtags", []))
    return f"{caption}\n\n{tags}"


# ── TikTok ────────────────────────────────────────────────────────────────

def upload_tiktok(video_path: str, description: str) -> bool:
    """
    Upload via tiktok-uploader (pip install tiktok-uploader).
    Requires TIKTOK_SESSION_ID set in environment.
    """
    if not TIKTOK_SESSION_ID:
        logger.warn("TikTok: TIKTOK_SESSION_ID not set — skipping")
        return False

    try:
        from tiktok_uploader.upload import upload_video  # type: ignore
        logger.step("Uploading to TikTok…")
        result = upload_video(
            filename=video_path,
            description=description,
            sessionid=TIKTOK_SESSION_ID,
        )
        if result:
            logger.ok(f"TikTok upload SUCCESS")
            return True
        else:
            logger.err("TikTok upload returned falsy result")
            return False
    except ImportError:
        logger.warn("tiktok-uploader not installed. Run: pip install tiktok-uploader")
        return False
    except Exception as e:
        logger.err(f"TikTok upload error: {e}")
        return False


# ── Instagram Reels ───────────────────────────────────────────────────────

def upload_instagram(video_path: str, description: str) -> bool:
    """
    Upload Reel via instagrapi (pip install instagrapi).
    Requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD.
    """
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        logger.warn("Instagram: credentials not set — skipping")
        return False

    try:
        from instagrapi import Client  # type: ignore
        logger.step("Uploading to Instagram Reels…")
        cl = Client()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        media = cl.clip_upload(
            path=video_path,
            caption=description,
        )
        logger.ok(f"Instagram Reel uploaded: {media.pk}")
        return True
    except ImportError:
        logger.warn("instagrapi not installed. Run: pip install instagrapi")
        return False
    except Exception as e:
        logger.err(f"Instagram upload error: {e}")
        return False


# ── YouTube Shorts ────────────────────────────────────────────────────────

def upload_youtube(video_path: str, title: str, description: str) -> bool:
    """
    Upload YouTube Short via google-api-python-client.
    Requires client_secrets.json and google-auth flow.
    First run will open a browser for OAuth.
    """
    if not os.path.exists(YOUTUBE_CLIENT_SECRETS):
        logger.warn(f"YouTube: client_secrets.json not found at {YOUTUBE_CLIENT_SECRETS} — skipping")
        return False

    try:
        from googleapiclient.discovery import build        # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
        import pickle

        SCOPES     = ["https://www.googleapis.com/auth/youtube.upload"]
        TOKEN_FILE = os.path.join(BASE_DIR, "youtube_token.pickle")

        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as t:
                creds = pickle.load(t)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "wb") as t:
                pickle.dump(creds, t)

        logger.step("Uploading to YouTube Shorts…")
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": ["Shorts", "anime", "edit", "viral"],
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            }
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                logger.info(f"  YouTube upload: {pct}%")

        logger.ok(f"YouTube Shorts uploaded: https://youtube.com/shorts/{response['id']}")
        return True

    except ImportError:
        logger.warn("google-api packages not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        return False
    except Exception as e:
        logger.err(f"YouTube upload error: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(FINAL_REEL):
        logger.die(f"final_reel.mp4 not found at {FINAL_REEL}. Run build_reel.py first.")

    data = load_brain_output()
    if data is None:
        logger.die("Cannot upload without valid brain output")

    description = build_description(data)
    title       = data["caption"][:80]

    logger.step(f"Uploading: \"{title}\"")
    logger.info(f"Description:\n{description}\n")

    size_mb = os.path.getsize(FINAL_REEL) / (1024 * 1024)
    logger.info(f"Video: {FINAL_REEL} ({size_mb:.1f} MB)")

    results = {}

    # Try each platform — independent of each other
    results["tiktok"]    = upload_tiktok(FINAL_REEL, description)
    results["instagram"] = upload_instagram(FINAL_REEL, description)
    results["youtube"]   = upload_youtube(FINAL_REEL, title, description)

    # Summary
    logger.step("Upload Summary")
    for platform, success in results.items():
        if success:
            logger.ok(f"  {platform.upper()}: ✅ uploaded")
        else:
            logger.warn(f"  {platform.upper()}: ⚠  skipped or failed")

    any_success = any(results.values())
    if not any_success:
        logger.err("All platforms failed or skipped. Check credentials in config / environment.")
        sys.exit(1)

    logger.ok("upload.py — DONE")


if __name__ == "__main__":
    main()

