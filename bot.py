import time
import mimetypes
import subprocess
from pathlib import Path

import requests

# ============================================================
# ØªÙ†Ø¸ÛŒÙ…Ø§Øª
# ============================================================
TOKEN = "CEFCFD0ECUJKKLJTVKOPNCVNBUKJBVQZVJIJUQCSYCOPCUQYHFDIEHORVRRRAXCU"

CHANNEL_ID = "c0BOd3T06238bac25a0a403752367011"

COVER_URL = (
    "https://cdn.imgurl.ir/uploads/"
    "s93695_ab8b9c87-0990-4beb-bfaa-cd1bf842caf7.png"
)

ARTIST = "@Black_list_remix"
OWNER_USERNAME = "@reza_127_s"

API_BASE = f"https://botapi.rubika.ir/v3/{TOKEN}"

WORK_DIR = Path("rubika_music_files")
WORK_DIR.mkdir(exist_ok=True)

POLL_DELAY = 0.5
ERROR_DELAY = 2
UPDATE_LIMIT = 20

session = requests.Session()
session.headers.update({"Content-Type": "application/json"})


# ============================================================
# API
# ============================================================
def api(method, data=None, timeout=40):
    url = f"{API_BASE}/{method}"
    response = session.post(url, json=data or {}, timeout=timeout)

    response.raise_for_status()

    result = response.json()

    if result.get("status") != "OK":
        raise RuntimeError(result)

    return result


def data_of(result):
    return result.get("data") or {}


def send_message(chat_id, text, reply_to_message_id=None, keypad=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id

    if keypad:
        data["chat_keypad"] = keypad

    return api("sendMessage", data)


def delete_message(chat_id, message_id):
    return api(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )


def get_updates(offset_id=None, limit=UPDATE_LIMIT):
    data = {"limit": limit}

    if offset_id:
        data["offset_id"] = offset_id

    return api("getUpdates", data, timeout=15)


def set_commands():
    return api(
        "setCommands",
        {
            "bot_commands": [
                {
                    "command": "start",
                    "description": "Ø´Ø±ÙˆØ¹ Ø±Ø¨Ø§Øª",
                },
                {
                    "command": "help",
                    "description": "Ø±Ø§Ù‡Ù†Ù…Ø§ÛŒ Ø±Ø¨Ø§Øª",
                },
            ]
        },
    )


def get_file(file_id):
    return api(
        "getFile",
        {
            "file_id": file_id,
        },
    )


# ============================================================
# Upload
# ============================================================
def request_upload_url(media_type):
    result = api(
        "requestSendFile",
        {
            "type": media_type,
        },
    )

    data = data_of(result)
    upload_url = data.get("upload_url")

    if not upload_url:
        raise RuntimeError(f"upload_url Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯: {result}")

    return upload_url


def upload_file(upload_url, path):
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    with path.open("rb") as file:
        response = requests.post(
            upload_url,
            files={
                "file": (
                    path.name,
                    file,
                    mime,
                )
            },
            timeout=180,
        )

    response.raise_for_status()
    result = response.json()

    if result.get("status") not in (None, "OK"):
        raise RuntimeError(result)

    file_id = (result.get("data") or {}).get("file_id")

    if not file_id:
        raise RuntimeError(f"file_id Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯: {result}")

    return file_id


def upload_to_rubika(path, media_type="Music"):
    upload_url = request_upload_url(media_type)
    return upload_file(upload_url, path)


def send_file(chat_id, file_id, reply_to_message_id=None):
    data = {
        "chat_id": chat_id,
        "file_id": file_id,
    }

    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id

    return api("sendFile", data)


# ============================================================
# Keypad
# ============================================================
OWNER_KEYBOARD = {
    "rows": [
        [
            {
                "id": "owner",
                "type": "Simple",
                "button_text": "Ù…Ø§Ù„Ú©",
            }
        ]
    ]
}

INLINE_KEYBOARD = {
    "rows": [
        [
            {
                "id": "time",
                "type": "Simple",
                "button_text": "ðŸ• Ø³Ø§Ø¹Øª",
            }
        ],
        [
            {
                "id": "date",
                "type": "Simple",
                "button_text": "ðŸ“… ØªØ§Ø±ÛŒØ®",
            }
        ],
        [
            {
                "id": "channel",
                "type": "Simple",
                "button_text": "@Black_list_remix",
            }
        ],
    ]
}


# ============================================================
# Download
# ============================================================
def download_file(file_id, filename):
    result = get_file(file_id)
    data = data_of(result)

    download_url = data.get("download_url")

    if not download_url:
        raise RuntimeError(f"download_url Ù¾ÛŒØ¯Ø§ Ù†Ø´Ø¯: {result}")

    safe_name = Path(filename).name or "input_audio"
    path = WORK_DIR / safe_name

    with requests.get(
        download_url,
        stream=True,
        timeout=180,
    ) as response:
        response.raise_for_status()

        with path.open("wb") as file:
            for chunk in response.iter_content(1024 * 256):
                if chunk:
                    file.write(chunk)

    return path


# ============================================================
# FFmpeg
# ============================================================
def ffmpeg_convert(source_path):
    source_path = Path(source_path)

    # Ù†Ø§Ù… Ø¢Ù‡Ù†Ú¯ Ø§Ø² Ù†Ø§Ù… Ø§ØµÙ„ÛŒ ÙØ§ÛŒÙ„ Ú¯Ø±ÙØªÙ‡ Ù…ÛŒâ€ŒØ´ÙˆØ¯.
    # Ù¾Ø³ÙˆÙ†Ø¯ Ø¬Ø¯ÛŒØ¯ MP3 Ø§Ø³ØªØŒ ÙˆÙ„ÛŒ Title Ù‡Ù…Ø§Ù† Ù†Ø§Ù… Ø§ØµÙ„ÛŒ Ø¢Ù‡Ù†Ú¯ Ù…ÛŒâ€ŒÙ…Ø§Ù†Ø¯.
    title = source_path.stem

    cover_path = WORK_DIR / "cover.jpg"

    if not cover_path.exists():
        response = requests.get(COVER_URL, timeout=60)
        response.raise_for_status()
        cover_path.write_bytes(response.content)

    output_path = WORK_DIR / f"{source_path.stem}.mp3"

    # Ø§Ú¯Ø± ÙØ§ÛŒÙ„ Ø®Ø±ÙˆØ¬ÛŒ Ù‚Ø¨Ù„ÛŒ ÙˆØ¬ÙˆØ¯ Ø¯Ø§Ø´Øª Ø­Ø°ÙØ´ Ú©Ù†.
    if output_path.exists():
        output_path.unlink()

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-i",
        str(cover_path),

        # ÙÙ‚Ø· ØµØ¯Ø§ÛŒ ÙˆØ±ÙˆØ¯ÛŒ
        "-map",
        "0:a:0",

        # Ø¹Ú©Ø³ Ú©Ø§ÙˆØ±
        "-map",
        "1:v:0",

        # ØªØ¨Ø¯ÛŒÙ„ ØµØ¯Ø§ Ø¨Ù‡ MP3
        "-c:a",
        "libmp3lame",
        "-b:a",
        "320k",

        # Ø¹Ú©Ø³ Ø¨Ù‡ JPEG Ø¨Ø±Ø§ÛŒ ID3 cover
        "-c:v",
        "mjpeg",

        # Ø¹Ú©Ø³ Ø¨Ù‡ Ø¹Ù†ÙˆØ§Ù† attached picture
        "-disposition:v:0",
        "attached_pic",

        # Ù…ØªØ§Ø¯ÛŒØªØ§
        "-metadata",
        f"title={title}",
        "-metadata",
        f"artist={ARTIST}",
        "-metadata",
        "album=Black List Remix",

        str(output_path),
    ]

    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
    )

    if process.returncode != 0:
        raise RuntimeError(
            "FFmpeg error:\n" + process.stderr[-4000:]
        )

    if not output_path.exists():
        raise RuntimeError("ÙØ§ÛŒÙ„ MP3 Ø³Ø§Ø®ØªÙ‡ Ù†Ø´Ø¯.")

    return output_path


# ============================================================
# Extract update
# ============================================================
def extract_message(update):
    """
    Rubika may send the Start-button event as StartedBot rather than
    NewMessage. Accept both event types.
    """
    if not isinstance(update, dict):
        return None

    event_type = update.get("type", "")

    if event_type not in ("NewMessage", "StartedBot"):
        return None

    msg = update.get("new_message") or {}
    if not isinstance(msg, dict):
        msg = {}

    chat_id = (
        update.get("chat_id")
        or msg.get("chat_id")
        or update.get("object_guid")
    )

    message_id = (
        msg.get("message_id")
        or msg.get("id")
        or update.get("message_id")
    )

    text = msg.get("text") or update.get("text") or ""

    # Pressing Rubika's Start button can arrive as StartedBot
    # without a text field.
    if event_type == "StartedBot":
        text = "/start"

    if not chat_id:
        return None

    return (
        chat_id,
        message_id,
        text,
        msg,
        update,
    )


def extract_file_info(msg):
    file_obj = msg.get("file")

    if isinstance(file_obj, dict):
        file_id = (
            file_obj.get("file_id")
            or file_obj.get("id")
        )

        file_name = (
            file_obj.get("file_name")
            or file_obj.get("name")
            or msg.get("file_name")
            or "music"
        )

        if file_id:
            return file_id, file_name

    file_id = msg.get("file_id")

    if file_id:
        return (
            file_id,
            msg.get("file_name") or "music",
        )

    return None, None


# ============================================================
# Start / Help
# ============================================================
def send_start(chat_id, message_id=None):
    text = (
        "ðŸŽµ Ø³Ù„Ø§Ù… Ùˆ Ø®ÙˆØ´ Ø¢Ù…Ø¯ÛŒØ¯!\n\n"
        "ÙØ§ÛŒÙ„ ØµÙˆØªÛŒ Ø®ÙˆØ¯ Ø±Ø§ Ø§Ø±Ø³Ø§Ù„ Ú©Ù†ÛŒØ¯ ØªØ§ Ù¾Ø±Ø¯Ø§Ø²Ø´ Ùˆ Ø¯Ø± Ú©Ø§Ù†Ø§Ù„ Ø§Ø±Ø³Ø§Ù„ Ø´ÙˆØ¯.\n"
        "ðŸ–¼ Ú©Ø§ÙˆØ± Ùˆ Ù†Ø§Ù… Ø®ÙˆØ§Ù†Ù†Ø¯Ù‡ Ø±ÙˆÛŒ ÙØ§ÛŒÙ„ ØªÙ†Ø¸ÛŒÙ… Ù…ÛŒâ€ŒØ´ÙˆØ¯."
    )

    send_message(
        chat_id,
        text,
        reply_to_message_id=message_id,
        keypad=OWNER_KEYBOARD,
    )

    send_message(
        chat_id,
        " ",
        keypad=INLINE_KEYBOARD,
    )


def send_help(chat_id, message_id):
    text = (
        "ðŸ“– Ø±Ø§Ù‡Ù†Ù…Ø§ÛŒ Ø±Ø¨Ø§Øª\n\n"
        "ðŸŽµ ÙØ§ÛŒÙ„ ØµÙˆØªÛŒ Ø®ÙˆØ¯ Ø±Ø§ Ø§Ø±Ø³Ø§Ù„ Ú©Ù†ÛŒØ¯.\n"
        "ðŸ–¼ Ú©Ø§ÙˆØ± Ø§Ø®ØªØµØ§ØµÛŒ Ø±ÙˆÛŒ Ù…ÙˆØ²ÛŒÚ© Ù‚Ø±Ø§Ø± Ù…ÛŒâ€ŒÚ¯ÛŒØ±Ø¯.\n"
        f"ðŸŽ¤ Ø®ÙˆØ§Ù†Ù†Ø¯Ù‡: {ARTIST}\n"
        "ðŸ“¤ Ø³Ù¾Ø³ Ù…ÙˆØ²ÛŒÚ© Ø¨Ù‡ Ú©Ø§Ù†Ø§Ù„ Ø§Ø±Ø³Ø§Ù„ Ù…ÛŒâ€ŒØ´ÙˆØ¯."
    )

    send_message(
        chat_id,
        text,
        reply_to_message_id=message_id,
        keypad=OWNER_KEYBOARD,
    )


# ============================================================
# Process Audio
# ============================================================
def process_audio(chat_id, message_id, file_id, original_name):
    status_id = None
    status2_id = None
    source_path = None
    output_path = None

    try:
        # ðŸ“¥
        status = send_message(
            chat_id,
            "ðŸ“¥",
            reply_to_message_id=message_id,
        )

        status_id = data_of(status).get("message_id")

        source_path = download_file(
            file_id,
            original_name,
        )

        # âœï¸
        if status_id:
            try:
                delete_message(
                    chat_id,
                    status_id,
                )
            except Exception:
                pass

        status2 = send_message(
            chat_id,
            "âœï¸",
            reply_to_message_id=message_id,
        )

        status2_id = data_of(status2).get("message_id")

        # ØªØ¨Ø¯ÛŒÙ„ + Ú©Ø§ÙˆØ± + Artist
        output_path = ffmpeg_convert(source_path)

        # Ø¢Ù¾Ù„ÙˆØ¯ Ø®Ø±ÙˆØ¬ÛŒ Ø¨Ù‡ Ø¹Ù†ÙˆØ§Ù† Music
        music_file_id = upload_to_rubika(
            output_path,
            "Music",
        )

        # Ø§Ø±Ø³Ø§Ù„ Ø¨Ù‡ Ú©Ø§Ù†Ø§Ù„
        send_file(
            CHANNEL_ID,
            music_file_id,
        )

        # Ø­Ø°Ù âœï¸
        if status2_id:
            try:
                delete_message(
                    chat_id,
                    status2_id,
                )
            except Exception:
                pass

        # âœ…
        send_message(
            chat_id,
            "âœ…",
            reply_to_message_id=message_id,
        )

        print(
            f"MUSIC SENT: {original_name} -> "
            f"{output_path.name}"
        )

    except Exception as error:
        print("AUDIO ERROR:", repr(error))

        if status_id:
            try:
                delete_message(
                    chat_id,
                    status_id,
                )
            except Exception:
                pass

        if status2_id:
            try:
                delete_message(
                    chat_id,
                    status2_id,
                )
            except Exception:
                pass

        try:
            send_message(
                chat_id,
                "âŒ Ø¯Ø± Ù¾Ø±Ø¯Ø§Ø²Ø´ ÛŒØ§ Ø§Ø±Ø³Ø§Ù„ Ù…ÙˆØ²ÛŒÚ© Ø®Ø·Ø§ÛŒÛŒ Ø±Ø® Ø¯Ø§Ø¯.",
                reply_to_message_id=message_id,
            )
        except Exception:
            pass

    finally:
        for path in (source_path, output_path):
            try:
                if path and path.exists():
                    path.unlink()
            except Exception:
                pass


# ============================================================
# Update handler
# ============================================================
def handle_update(update):
    extracted = extract_message(update)

    if not extracted:
        return

    (
        chat_id,
        message_id,
        text,
        msg,
        raw,
    ) = extracted

    if text == "/start":
        send_start(
            chat_id,
            message_id,
        )
        return

    if text == "/help":
        send_help(
            chat_id,
            message_id,
        )
        return

    if text.strip() == "Ù…Ø§Ù„Ú©":
        send_message(
            chat_id,
            "Ø³Ù„Ø§Ù… Ùˆ Ø¹Ø±Ø¶ Ø§Ø¯Ø¨ Ø®Ø¯Ù…Øª Ø´Ù…Ø§ Ø¯ÙˆØ³Øª Ø¹Ø²ÛŒØ².\n"
            "Ø¨Ø±Ø§ÛŒ Ø§Ø·Ù„Ø§Ø¹Ø§Øª Ø¨ÛŒØ´ØªØ± ÛŒØ§ Ù‡Ù…Ú©Ø§Ø±ÛŒ Ùˆ ÛŒØ§ Ø§Ù†ØªÙ‚Ø§Ø¯Ø§Øª Ø®ÙˆØ¯ Ùˆ ØªØ¨Ù„ÛŒØºØ§ØªÙ…ÛŒØªÙˆØ§Ù†ÛŒØ¯ Ø¨Ø§ Ù…Ø§Ù„Ú© ØµØ­Ø¨Øª Ú©Ù†ÛŒØ¯:\n"
            "@reza_127_s",
            reply_to_message_id=message_id,
        )
        return

    file_id, filename = extract_file_info(msg)

    if file_id:
        process_audio(
            chat_id,
            message_id,
            file_id,
            filename,
        )
        return

    if not text:
        try:
            send_message(
                chat_id,
                "Ù„Ø·ÙØ§ ÙØ§ÛŒÙ„ ØµÙˆØªÛŒ Ø¨ÙØ±Ø³ØªÛŒØ¯.",
                reply_to_message_id=message_id,
            )
        except Exception:
            pass


# ============================================================
# Polling
# ============================================================
def clear_old_updates():
    try:
        result = get_updates(
            limit=UPDATE_LIMIT,
        )

        return data_of(result).get(
            "next_offset_id"
        )

    except Exception as error:
        print(
            "CLEAR OLD UPDATES ERROR:",
            repr(error),
        )
        return None


def run():
    print("=" * 50, flush=True)
    print("Rubika Music Bot - GitHub Actions", flush=True)
    print("=" * 50, flush=True)

    try:
        set_commands()
        print("âœ… /start Ùˆ /help Ø«Ø¨Øª Ø´Ø¯Ù†Ø¯.", flush=True)
    except Exception as error:
        print(
            "âš ï¸ setCommands error:",
            repr(error),
        )

    # Do not discard updates at startup. We want to see exactly what
    # getUpdates returns and make sure incoming messages are received.
    offset_id = None

    print("ðŸ“¡ getUpdates polling started...", flush=True)
    print("ðŸ¤– Rubika Music Bot is running...", flush=True)
    print("âš¡ polling: 0.5 second", flush=True)
    print(f"ðŸŽ¤ Artist: {ARTIST}", flush=True)
    print("ðŸ–¼ Cover: ÙØ¹Ø§Ù„", flush=True)
    print("ðŸŽµ MP3 conversion: ÙØ¹Ø§Ù„", flush=True)

    while True:
        try:
            result = get_updates(
                offset_id=offset_id,
                limit=UPDATE_LIMIT,
            )

            # Diagnostic output: if a message arrives, this confirms
            # whether the problem is polling or message handling.
            print(
                "GETUPDATES:",
                {
                    "status": result.get("status"),
                    "data_keys": list((result.get("data") or {}).keys()),
                    "updates_count": len((result.get("data") or {}).get("updates") or []),
                    "next_offset_id": (result.get("data") or {}).get("next_offset_id"),
                },
                flush=True,
            )

            data = data_of(result)

            next_offset = data.get(
                "next_offset_id"
            )

            if next_offset:
                offset_id = next_offset

            updates = (
                data.get("updates")
                or data.get("new_messages")
                or []
            )

            for update in updates:
                try:
                    print(
                        "UPDATE RECEIVED:",
                        update,
                        flush=True,
                    )
                    handle_update(update)
                except Exception as error:
                    print(
                        "UPDATE ERROR:",
                        repr(error),
                        flush=True,
                    )

            if not updates:
                time.sleep(POLL_DELAY)

        except KeyboardInterrupt:
            print("Bot stopped.")
            break

        except Exception as error:
            print(
                "POLL ERROR:",
                repr(error),
                flush=True,
            )
            time.sleep(ERROR_DELAY)


if __name__ == "__main__":
    run()
