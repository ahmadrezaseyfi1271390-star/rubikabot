import os
import re
import json
import hashlib
import asyncio
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder, InlineBuilder


# =========================================================
# CONFIG
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_AUDIO_SIZE = 100 * 1024 * 1024       # 100 MB
MAX_COVER_SIZE = 10 * 1024 * 1024        # 10 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024        # 10 MB

CACHE_FILE = "media_cache.json"
USERS_FILE = "users.json"

executor = ThreadPoolExecutor(max_workers=4)

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# MEMORY
# =========================================================

users_cache = {}
media_cache = {}
message_cache = {}

sessions = {}
last_prompt = {}


# =========================================================
# LOAD / SAVE JSON
# =========================================================

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return default


def save_json(path, data):
    tmp = path + ".tmp"

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(tmp, path)

    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


users_cache = load_json(USERS_FILE, {})
media_cache = load_json(CACHE_FILE, {})

for key, value in media_cache.items():
    if isinstance(value, dict):
        mid = value.get("message_id")
        if mid:
            message_cache[str(mid)] = key


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button("banner", "🖼 ساخت بنر"),
        builder.button("music", "🎵 ادیت آهنگ")
    )

    return builder.build(
        resize_keyboard=True
    )


def yes_no_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button("yes", "بله"),
        builder.button("no", "نه")
    )

    return builder.build(
        resize_keyboard=True
    )


def next_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button("next", "بعدی")
    )

    return builder.build(
        resize_keyboard=True
    )


def media_type_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button("song", "🎵 آهنگ"),
        builder.button("voice", "🎤 ویس")
    )

    return builder.build(
        resize_keyboard=True
    )


def back_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button("back", "🔙 بازگشت")
    )

    return builder.build(
        resize_keyboard=True
    )


# =========================================================
# GLASS BUTTON
# =========================================================

def make_glass_button(text):
    if not text:
        return None

    try:
        builder = InlineBuilder()

        builder.button_url_link(
            id="glass_button",
            text=text,
            url="https://t.me/Black_list_remix"
        )

        return builder.build()

    except Exception as e:
        print("GLASS BUTTON ERROR:", e)
        return None


# =========================================================
# SAFE SEND
# =========================================================

async def safe_send_message(
    chat_id,
    text,
    chat_keypad=None,
    inline_keypad=None
):
    try:
        return await bot.send_message(
            chat_id=str(chat_id),
            text=text,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad
        )

    except Exception as e:
        print("SEND MESSAGE ERROR:", repr(e))
        return None


async def delete_message(chat_id, message_id):
    if not message_id:
        return

    try:
        await bot.delete_message(
            str(chat_id),
            int(message_id)
        )
    except Exception as e:
        print("DELETE ERROR:", repr(e))


async def delete_previous_prompt(chat_id):
    old = last_prompt.get(str(chat_id))

    if old:
        await delete_message(
            str(chat_id),
            old
        )

        last_prompt.pop(str(chat_id), None)


async def prompt(
    chat_id,
    text,
    keyboard=None,
    delete_old=True
):
    chat_id = str(chat_id)

    if delete_old:
        await delete_previous_prompt(chat_id)

    msg = await safe_send_message(
        chat_id,
        text,
        chat_keypad=keyboard
    )

    if msg:
        mid = getattr(msg, "message_id", None)

        if mid:
            last_prompt[chat_id] = mid

    return msg


# =========================================================
# USERS
# =========================================================

def save_user(chat_id):
    chat_id = str(chat_id)

    if chat_id not in users_cache:
        users_cache[chat_id] = {
            "chat_id": chat_id
        }

        save_json(
            USERS_FILE,
            users_cache
        )


# =========================================================
# URL HELPERS
# =========================================================

def is_url(text):
    if not text:
        return False

    text = text.strip()

    return bool(
        re.match(
            r"^https?://",
            text,
            re.IGNORECASE
        )
    )


def is_google_drive(url):
    if not url:
        return False

    return (
        "drive.google.com" in url
        or "docs.google.com" in url
    )


# =========================================================
# DOWNLOAD
# =========================================================

def download_url(url, output_path, max_size):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    with requests.get(
        url,
        stream=True,
        timeout=60,
        headers=headers
    ) as response:

        response.raise_for_status()

        total = 0

        content_length = response.headers.get(
            "content-length"
        )

        if content_length:
            try:
                if int(content_length) > max_size:
                    raise ValueError(
                        "FILE_TOO_LARGE"
                    )
            except ValueError:
                pass

        with open(output_path, "wb") as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 512
            ):
                if not chunk:
                    continue

                total += len(chunk)

                if total > max_size:
                    raise ValueError(
                        "FILE_TOO_LARGE"
                    )

                f.write(chunk)

    return output_path


def download_file(url, output_path, max_size):
    # Google Drive
    if is_google_drive(url):

        try:
            import gdown

            downloaded = gdown.download(
                url,
                output_path,
                quiet=True,
                fuzzy=True
            )

            if not downloaded:
                raise RuntimeError(
                    "Google Drive download failed"
                )

            if os.path.getsize(downloaded) > max_size:
                os.remove(downloaded)

                raise ValueError(
                    "FILE_TOO_LARGE"
                )

            return downloaded

        except ImportError:
            raise RuntimeError(
                "gdown نصب نشده است"
            )

    return download_url(
        url,
        output_path,
        max_size
    )


# =========================================================
# IMAGE CONVERSION
# =========================================================

def convert_to_jpg(input_path, output_path):
    with Image.open(input_path) as img:

        if img.mode in (
            "RGBA",
            "LA",
            "P"
        ):
            background = Image.new(
                "RGB",
                img.convert("RGBA").size,
                "white"
            )

            background.paste(
                img.convert("RGBA"),
                mask=img.convert("RGBA").getchannel("A")
            )

            img = background

        else:
            img = img.convert("RGB")

        img.save(
            output_path,
            "JPEG",
            quality=92,
            optimize=True
        )

    return output_path


# =========================================================
# AUDIO METADATA
# =========================================================

def edit_mp3(
    input_path,
    output_path,
    title,
    artist,
    cover_path=None
):
    shutil.copy2(
        input_path,
        output_path
    )

    try:
        audio = MP3(output_path)

        try:
            tags = ID3(output_path)
        except Exception:
            tags = ID3()

        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.delall("APIC")

        tags.add(
            TIT2(
                encoding=3,
                text=title
            )
        )

        tags.add(
            TPE1(
                encoding=3,
                text=artist
            )
        )

        if cover_path and os.path.exists(cover_path):

            with open(
                cover_path,
                "rb"
            ) as f:
                cover_data = f.read()

            tags.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=cover_data
                )
            )

        tags.save(
            output_path,
            v2_version=3
        )

        audio = MP3(output_path)

        return output_path

    except Exception as e:
        print("MP3 EDIT ERROR:", repr(e))
        raise


# =========================================================
# CACHE
# =========================================================

def hash_file(path):
    sha = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)

            if not data:
                break

            sha.update(data)

    return sha.hexdigest()


def cache_key_for_file(path, kind):
    return kind + "_" + hash_file(path)


def save_media_cache(
    key,
    kind,
    file_id,
    message_id=None,
    caption="",
    button_text=""
):
    media_cache[key] = {
        "kind": kind,
        "file_id": file_id,
        "message_id": str(message_id)
        if message_id
        else None,
        "caption": caption or "",
        "button_text": button_text or ""
    }

    if message_id:
        message_cache[
            str(message_id)
        ] = key

    save_json(
        CACHE_FILE,
        media_cache
    )


# =========================================================
# MESSAGE FILE ID
# =========================================================

def get_file_id(msg):
    if not msg:
        return None

    fid = getattr(
        msg,
        "file_id",
        None
    )

    if fid:
        return fid

    for attr in (
        "music",
        "voice",
        "image",
        "document"
    ):
        obj = getattr(
            msg,
            attr,
            None
        )

        if obj:

            fid = getattr(
                obj,
                "file_id",
                None
            )

            if fid:
                return fid

    return None


# =========================================================
# SEND MEDIA
# =========================================================

async def send_music_file(
    chat_id,
    path=None,
    file_id=None,
    caption="",
    inline_keypad=None
):
    try:

        kwargs = {
            "chat_id": str(chat_id),
            "text": caption or ""
        }

        if file_id:
            kwargs["file_id"] = file_id
        else:
            kwargs["path"] = path

        if inline_keypad:
            kwargs["inline_keypad"] = inline_keypad

        return await bot.send_music(
            **kwargs
        )

    except Exception as e:
        print(
            "SEND MUSIC ERROR:",
            repr(e)
        )

        return None


async def send_voice_file(
    chat_id,
    path=None,
    file_id=None,
    caption="",
    inline_keypad=None
):
    try:

        kwargs = {
            "chat_id": str(chat_id),
            "text": caption or ""
        }

        if file_id:
            kwargs["file_id"] = file_id
        else:
            kwargs["path"] = path

        if inline_keypad:
            kwargs["inline_keypad"] = inline_keypad

        return await bot.send_voice(
            **kwargs
        )

    except Exception as e:
        print(
            "SEND VOICE ERROR:",
            repr(e)
        )

        return None


async def send_image_file(
    chat_id,
    path=None,
    file_id=None,
    caption="",
    inline_keypad=None
):
    try:

        kwargs = {
            "chat_id": str(chat_id),
            "text": caption or ""
        }

        if file_id:
            kwargs["file_id"] = file_id
        else:
            kwargs["path"] = path

        if inline_keypad:
            kwargs["inline_keypad"] = inline_keypad

        return await bot.send_image(
            **kwargs
        )

    except Exception as e:
        print(
            "SEND IMAGE ERROR:",
            repr(e)
        )

        return None


# =========================================================
# SEND CACHED MEDIA
# =========================================================

async def send_cached(
    chat_id,
    cache_item
):
    if not cache_item:
        return None

    kind = cache_item.get(
        "kind"
    )

    file_id = cache_item.get(
        "file_id"
    )

    caption = cache_item.get(
        "caption",
        ""
    )

    button_text = cache_item.get(
        "button_text",
        ""
    )

    inline = None

    if button_text:
        inline = make_glass_button(
            button_text
        )

    if kind == "music":

        return await send_music_file(
            chat_id,
            file_id=file_id,
            caption=caption,
            inline_keypad=inline
        )

    if kind == "voice":

        return await send_voice_file(
            chat_id,
            file_id=file_id,
            caption=caption,
            inline_keypad=inline
        )

    if kind == "banner":

        return await send_image_file(
            chat_id,
            file_id=file_id,
            caption=caption,
            inline_keypad=inline
        )

    return None


# =========================================================
# EXTRACT MESSAGE TEXT
# =========================================================

def get_text(message):
    text = getattr(
        message,
        "text",
        None
    )

    if text is None:
        text = getattr(
            message,
            "body",
            None
        )

    if text is None:
        return ""

    return str(text).strip()


def get_chat_id(message):
    chat_id = getattr(
        message,
        "chat_id",
        None
    )

    if chat_id is None:
        chat = getattr(
            message,
            "chat",
            None
        )

        if chat:
            chat_id = getattr(
                chat,
                "chat_id",
                None
            )

    return str(chat_id)


def get_message_id(message):
    mid = getattr(
        message,
        "message_id",
        None
    )

    if mid is None:
        mid = getattr(
            message,
            "id",
            None
        )

    return mid


# =========================================================
# SESSION
# =========================================================

def new_session(chat_id):
    return {
        "step": "main",
        "kind": None,

        "source_url": None,
        "source_path": None,

        "preview": False,

        "caption": DEFAULT_CAPTION,

        "title": None,
        "artist": None,

        "cover_url": None,
        "cover_path": None,

        "button_text": None
    }


# =========================================================
# CLEAN TEMP
# =========================================================

def clean_session_files(session):
    if not session:
        return

    for key in (
        "source_path",
        "cover_path"
    ):
        path = session.get(key)

        if path and os.path.exists(path):

            try:
                os.remove(path)
            except Exception:
                pass


# =========================================================
# DOWNLOAD ASYNC
# =========================================================

async def async_download(
    url,
    max_size,
    suffix=".bin"
):
    folder = tempfile.mkdtemp(
        prefix="rubka_"
    )

    path = os.path.join(
        folder,
        "file" + suffix
    )

    loop = asyncio.get_running_loop()

    try:

        result = await loop.run_in_executor(
            executor,
            download_file,
            url,
            path,
            max_size
        )

        return result

    except Exception:

        shutil.rmtree(
            folder,
            ignore_errors=True
        )

        raise


async def async_convert_jpg(
    input_path
):
    folder = os.path.dirname(
        input_path
    )

    output = os.path.join(
        folder,
        "cover.jpg"
    )

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        convert_to_jpg,
        input_path,
        output
    )


async def async_edit_mp3(
    input_path,
    title,
    artist,
    cover_path
):
    folder = os.path.dirname(
        input_path
    )

    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        title
    ).strip()

    if not safe_title:
        safe_title = "song"

    output = os.path.join(
        folder,
        safe_title + ".mp3"
    )

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        edit_mp3,
        input_path,
        output,
        title,
        artist,
        cover_path
    )


# =========================================================
# FINAL SEND + CACHE
# =========================================================

async def upload_and_cache(
    chat_id,
    path,
    kind,
    caption,
    button_text=""
):
    inline = None

    if button_text:
        inline = make_glass_button(
            button_text
        )

    if kind == "music":

        sent = await send_music_file(
            chat_id,
            path=path,
            caption=caption,
            inline_keypad=inline
        )

    elif kind == "voice":

        sent = await send_voice_file(
            chat_id,
            path=path,
            caption=caption,
            inline_keypad=inline
        )

    elif kind == "banner":

        sent = await send_image_file(
            chat_id,
            path=path,
            caption=caption,
            inline_keypad=inline
        )

    else:
        return None

    if not sent:
        return None

    file_id = get_file_id(
        sent
    )

    message_id = get_message_id(
        sent
    )

    if file_id:

        key = cache_key_for_file(
            path,
            kind
        )

        save_media_cache(
            key=key,
            kind=kind,
            file_id=file_id,
            message_id=message_id,
            caption=caption,
            button_text=button_text
        )

    return sent


# =========================================================
# RESEND
# =========================================================

async def resend_replied(
    chat_id,
    message
):
    reply = getattr(
        message,
        "reply_to_message",
        None
    )

    if not reply:
        return False

    reply_id = get_message_id(
        reply
    )

    if not reply_id:
        return False

    key = message_cache.get(
        str(reply_id)
    )

    if not key:
        return False

    item = media_cache.get(
        key
    )

    if not item:
        return False

    sent = await send_cached(
        chat_id,
        item
    )

    return bool(sent)


# =========================================================
# START
# =========================================================

async def handle_start(
    message,
    chat_id
):
    save_user(
        chat_id
    )

    sessions[chat_id] = new_session(
        chat_id
    )

    await prompt(
        chat_id,
        "👇",
        main_keyboard()
    )


# =========================================================
# BANNER
# =========================================================

async def start_banner(
    chat_id
):
    sessions[chat_id] = new_session(
        chat_id
    )

    sessions[chat_id]["kind"] = "banner"
    sessions[chat_id]["step"] = "banner_url"

    await prompt(
        chat_id,
        "🔗"
    )


async def banner_url(
    chat_id,
    text
):
    if not is_url(text):

        await prompt(
            chat_id,
            "❌"
        )

        return

    sessions[chat_id][
        "source_url"
    ] = text

    sessions[chat_id][
        "step"
    ] = "banner_preview"

    await prompt(
        chat_id,
        "پیش‌نمایش لازم دارید؟",
        yes_no_keyboard()
    )


async def banner_preview_answer(
    chat_id,
    text
):
    session = sessions[chat_id]

    if text == "بله":

        session["preview"] = True

        try:

            path = await async_download(
                session["source_url"],
                MAX_IMAGE_SIZE,
                ".img"
            )

            jpg = await async_convert_jpg(
                path
            )

            session["source_path"] = jpg

            await send_image_file(
                chat_id,
                path=jpg
            )

        except Exception as e:

            print(
                "BANNER PREVIEW ERROR:",
                repr(e)
            )

            await prompt(
                chat_id,
                "❌"
            )

            return

    elif text != "نه":

        return

    else:
        session["preview"] = False

        try:

            path = await async_download(
                session["source_url"],
                MAX_IMAGE_SIZE,
                ".img"
            )

            jpg = await async_convert_jpg(
                path
            )

            session["source_path"] = jpg

        except Exception as e:

            print(
                "BANNER DOWNLOAD ERROR:",
                repr(e)
            )

            await prompt(
                chat_id,
                "❌"
            )

            return

    session["step"] = "banner_caption"

    await prompt(
        chat_id,
        "✏️",
        next_keyboard()
    )


async def banner_caption(
    chat_id,
    text
):
    if text == "بعدی":
        text = DEFAULT_CAPTION

    sessions[chat_id][
        "caption"
    ] = text

    sessions[chat_id][
        "step"
    ] = "banner_button"

    await prompt(
        chat_id,
        "🔘",
        next_keyboard()
    )


async def banner_button(
    chat_id,
    text
):
    if text == "بعدی":
        text = ""

    sessions[chat_id][
        "button_text"
    ] = text

    session = sessions[chat_id]

    await prompt(
        chat_id,
        "⚙️"
    )

    try:

        sent = await upload_and_cache(
            chat_id=chat_id,
            path=session["source_path"],
            kind="banner",
            caption=session["caption"],
            button_text=session["button_text"]
        )

        if sent:

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

        else:

            await prompt(
                chat_id,
                "❌",
                main_keyboard()
            )

    except Exception as e:

        print(
            "BANNER FINAL ERROR:",
            repr(e)
        )

        await prompt(
            chat_id,
            "❌",
            main_keyboard()
        )

    finally:

        clean_session_files(
            session
        )

        sessions.pop(
            chat_id,
            None
        )


# =========================================================
# MUSIC
# =========================================================

async def start_music(
    chat_id
):
    sessions[chat_id] = new_session(
        chat_id
    )

    sessions[chat_id]["kind"] = "music"
    sessions[chat_id]["step"] = "music_url"

    await prompt(
        chat_id,
        "🔗"
    )


async def music_url(
    chat_id,
    text
):
    if not is_url(text):

        await prompt(
            chat_id,
            "❌"
        )

        return

    sessions[chat_id][
        "source_url"
    ] = text

    sessions[chat_id][
        "step"
    ] = "music_preview"

    await prompt(
        chat_id,
        "پیش‌نمایش لازم دارید؟",
        yes_no_keyboard()
    )


async def music_preview_answer(
    chat_id,
    text
):
    session = sessions[chat_id]

    if text not in (
        "بله",
        "نه"
    ):
        return

    try:

        path = await async_download(
            session["source_url"],
            MAX_AUDIO_SIZE,
            ".audio"
        )

        session["source_path"] = path

        if text == "بله":

            session["preview"] = True

            await send_music_file(
                chat_id,
                path=path
            )

        else:

            session["preview"] = False

    except Exception as e:

        print(
            "MUSIC DOWNLOAD ERROR:",
            repr(e)
        )

        await prompt(
            chat_id,
            "❌"
        )

        return

    session["step"] = "music_caption"

    await prompt(
        chat_id,
        "✏️",
        next_keyboard()
    )


async def music_caption(
    chat_id,
    text
):
    if text == "بعدی":
        text = DEFAULT_CAPTION

    sessions[chat_id][
        "caption"
    ] = text

    sessions[chat_id][
        "step"
    ] = "media_type"

    await prompt(
        chat_id,
        "🎵",
        media_type_keyboard()
    )


# =========================================================
# SONG
# =========================================================

async def start_song(
    chat_id
):
    session = sessions[chat_id]

    session["step"] = "song_title"

    await prompt(
        chat_id,
        "🎵"
    )


async def song_title(
    chat_id,
    text
):
    sessions[chat_id][
        "title"
    ] = text

    sessions[chat_id][
        "step"
    ] = "song_artist"

    await prompt(
        chat_id,
        "🎤"
    )


async def song_artist(
    chat_id,
    text
):
    sessions[chat_id][
        "artist"
    ] = text

    sessions[chat_id][
        "step"
    ] = "song_cover"

    await prompt(
        chat_id,
        "🖼️",
        next_keyboard()
    )


async def song_cover(
    chat_id,
    text
):
    session = sessions[chat_id]

    if text == "بعدی":

        session[
            "cover_path"
        ] = None

    else:

        if not is_url(text):

            await prompt(
                chat_id,
                "❌",
                next_keyboard()
            )

            return

        session[
            "cover_url"
        ] = text

        try:

            raw = await async_download(
                text,
                MAX_COVER_SIZE,
                ".img"
            )

            jpg = await async_convert_jpg(
                raw
            )

            session[
                "cover_path"
            ] = jpg

        except Exception as e:

            print(
                "COVER ERROR:",
                repr(e)
            )

            await prompt(
                chat_id,
                "❌"
            )

            return

    session[
        "step"
    ] = "song_button"

    await prompt(
        chat_id,
        "🔘",
        next_keyboard()
    )


async def song_button(
    chat_id,
    text
):
    if text == "بعدی":
        text = ""

    sessions[chat_id][
        "button_text"
    ] = text

    session = sessions[chat_id]

    await prompt(
        chat_id,
        "⚙️"
    )

    try:

        final_path = await async_edit_mp3(
            session["source_path"],
            session["title"],
            session["artist"],
            session["cover_path"]
        )

        sent = await upload_and_cache(
            chat_id=chat_id,
            path=final_path,
            kind="music",
            caption=session["caption"],
            button_text=session["button_text"]
        )

        if sent:

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

        else:

            await prompt(
                chat_id,
                "❌",
                main_keyboard()
            )

    except Exception as e:

        print(
            "SONG FINAL ERROR:",
            repr(e)
        )

        await prompt(
            chat_id,
            "❌",
            main_keyboard()
        )

    finally:

        clean_session_files(
            session
        )

        sessions.pop(
            chat_id,
            None
        )


# =========================================================
# VOICE
# =========================================================

async def start_voice(
    chat_id
):
    sessions[chat_id][
        "step"
    ] = "voice_button"

    await prompt(
        chat_id,
        "🔘",
        next_keyboard()
    )


async def voice_button(
    chat_id,
    text
):
    if text == "بعدی":
        text = ""

    sessions[chat_id][
        "button_text"
    ] = text

    session = sessions[chat_id]

    await prompt(
        chat_id,
        "⚙️"
    )

    try:

        sent = await upload_and_cache(
            chat_id=chat_id,
            path=session["source_path"],
            kind="voice",
            caption=session["caption"],
            button_text=session["button_text"]
        )

        if sent:

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

        else:

            await prompt(
                chat_id,
                "❌",
                main_keyboard()
            )

    except Exception as e:

        print(
            "VOICE FINAL ERROR:",
            repr(e)
        )

        await prompt(
            chat_id,
            "❌",
            main_keyboard()
        )

    finally:

        clean_session_files(
            session
        )

        sessions.pop(
            chat_id,
            None
        )


# =========================================================
# MAIN MESSAGE HANDLER
# =========================================================

@bot.on_message()
async def on_message(
    message: Message
):

    try:

        chat_id = get_chat_id(
            message
        )

        text = get_text(
            message
        )

        if not chat_id:
            return

        save_user(
            chat_id
        )

        # ---------------------------------------------
        # START
        # ---------------------------------------------

        if text == "/start":

            await handle_start(
                message,
                chat_id
            )

            return

        # ---------------------------------------------
        # RESEND
        # ---------------------------------------------

        if text in (
            "باز ارسال",
            "بازارسال",
            "ارسال مجدد"
        ):

            if await resend_replied(
                chat_id,
                message
            ):
                return

        # ---------------------------------------------
        # MAIN MENU
        # ---------------------------------------------

        if text == "🖼 ساخت بنر":

            await start_banner(
                chat_id
            )

            return

        if text == "🎵 ادیت آهنگ":

            await start_music(
                chat_id
            )

            return

        # ---------------------------------------------
        # BACK
        # ---------------------------------------------

        if text == "🔙 بازگشت":

            old = sessions.get(
                chat_id
            )

            if old:
                clean_session_files(
                    old
                )

            sessions.pop(
                chat_id,
                None
            )

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

            return

        # ---------------------------------------------
        # NO SESSION
        # ---------------------------------------------

        if chat_id not in sessions:

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

            return

        session = sessions[chat_id]

        step = session.get(
            "step"
        )

        # ---------------------------------------------
        # BANNER
        # ---------------------------------------------

        if step == "banner_url":

            await banner_url(
                chat_id,
                text
            )

        elif step == "banner_preview":

            await banner_preview_answer(
                chat_id,
                text
            )

        elif step == "banner_caption":

            await banner_caption(
                chat_id,
                text
            )

        elif step == "banner_button":

            await banner_button(
                chat_id,
                text
            )

        # ---------------------------------------------
        # MUSIC
        # ---------------------------------------------

        elif step == "music_url":

            await music_url(
                chat_id,
                text
            )

        elif step == "music_preview":

            await music_preview_answer(
                chat_id,
                text
            )

        elif step == "music_caption":

            await music_caption(
                chat_id,
                text
            )

        elif step == "media_type":

            if text == "🎵 آهنگ":

                await start_song(
                    chat_id
                )

            elif text == "🎤 ویس":

                await start_voice(
                    chat_id
                )

        # ---------------------------------------------
        # SONG
        # ---------------------------------------------

        elif step == "song_title":

            await song_title(
                chat_id,
                text
            )

        elif step == "song_artist":

            await song_artist(
                chat_id,
                text
            )

        elif step == "song_cover":

            await song_cover(
                chat_id,
                text
            )

        elif step == "song_button":

            await song_button(
                chat_id,
                text
            )

        # ---------------------------------------------
        # VOICE
        # ---------------------------------------------

        elif step == "voice_button":

            await voice_button(
                chat_id,
                text
            )

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        " RUBKA BOT STARTED"
    )

    print(
        " Rubka 8.1.10"
    )

    print(
        "================================"
    )

    bot.run()
