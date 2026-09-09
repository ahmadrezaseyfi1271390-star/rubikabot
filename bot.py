import os
import re
import json
import asyncio
import shutil
import tempfile
import hashlib
from concurrent.futures import ThreadPoolExecutor

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

MAX_AUDIO_SIZE = 100 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024

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

sessions = {}
last_prompt = {}

users_cache = {}
media_cache = {}
message_cache = {}


# =========================================================
# JSON
# =========================================================

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print("LOAD JSON ERROR:", repr(e))

    return default


def save_json(path, data):
    temp = path + ".tmp"

    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp, path)

    except Exception as e:
        print("SAVE JSON ERROR:", repr(e))


users_cache = load_json(
    USERS_FILE,
    {}
)

media_cache = load_json(
    CACHE_FILE,
    {}
)

for key, item in media_cache.items():
    if isinstance(item, dict):
        mid = item.get("message_id")

        if mid:
            message_cache[str(mid)] = key


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="banner",
            text="🖼 ساخت بنر"
        ),
        builder.button(
            id="music",
            text="🎵 ادیت آهنگ"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


def yes_no_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="yes",
            text="بله"
        ),
        builder.button(
            id="no",
            text="نه"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


def next_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="next",
            text="بعدی"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


def media_keyboard():
    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="song",
            text="🎵 آهنگ"
        ),
        builder.button(
            id="voice",
            text="🎤 ویس"
        )
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
        print("INLINE BUTTON ERROR:", repr(e))
        return None


# =========================================================
# MESSAGE HELPERS
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

    return str(text).strip() if text else ""


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

    return str(chat_id) if chat_id is not None else ""


def get_message_id(message):
    value = getattr(
        message,
        "message_id",
        None
    )

    if value is None:
        value = getattr(
            message,
            "id",
            None
        )

    return value


def get_file_id(message):
    if not message:
        return None

    value = getattr(
        message,
        "file_id",
        None
    )

    if value:
        return value

    for name in (
        "music",
        "voice",
        "image",
        "document"
    ):
        obj = getattr(
            message,
            name,
            None
        )

        if obj:

            value = getattr(
                obj,
                "file_id",
                None
            )

            if value:
                return value

    return None


# =========================================================
# SEND / DELETE
# =========================================================

async def delete_message(
    chat_id,
    message_id
):
    if not message_id:
        return

    try:
        await bot.delete_message(
            str(chat_id),
            int(message_id)
        )
    except Exception as e:
        print("DELETE ERROR:", repr(e))


async def delete_old_prompt(chat_id):
    chat_id = str(chat_id)

    old_id = last_prompt.get(
        chat_id
    )

    if old_id:
        await delete_message(
            chat_id,
            old_id
        )

        last_prompt.pop(
            chat_id,
            None
        )


async def send_prompt(
    chat_id,
    text,
    keyboard=None
):
    chat_id = str(chat_id)

    await delete_old_prompt(
        chat_id
    )

    try:

        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            chat_keypad=keyboard
        )

        if msg:

            mid = get_message_id(
                msg
            )

            if mid:
                last_prompt[
                    chat_id
                ] = mid

        return msg

    except Exception as e:
        print("SEND MESSAGE ERROR:", repr(e))
        return None


# =========================================================
# USER
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
# URL
# =========================================================

def is_url(text):
    if not text:
        return False

    return bool(
        re.match(
            r"^https?://",
            text.strip(),
            re.I
        )
    )


def is_google_drive(url):
    return (
        "drive.google.com" in url
        or "docs.google.com" in url
    )


# =========================================================
# DOWNLOAD
# =========================================================

def download_direct(
    url,
    output,
    max_size
):
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

        content_length = response.headers.get(
            "content-length"
        )

        if content_length:

            try:
                if int(content_length) > max_size:
                    raise ValueError(
                        "FILE_TOO_LARGE"
                    )
            except ValueError as e:

                if str(e) == "FILE_TOO_LARGE":
                    raise

        size = 0

        with open(
            output,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=512 * 1024
            ):

                if not chunk:
                    continue

                size += len(chunk)

                if size > max_size:
                    raise ValueError(
                        "FILE_TOO_LARGE"
                    )

                f.write(chunk)

    return output


def download_file(
    url,
    output,
    max_size
):
    if is_google_drive(url):

        try:
            import gdown

            result = gdown.download(
                url,
                output,
                quiet=True,
                fuzzy=True
            )

            if not result:
                raise RuntimeError(
                    "GOOGLE_DRIVE_DOWNLOAD_FAILED"
                )

            if os.path.getsize(result) > max_size:

                try:
                    os.remove(result)
                except Exception:
                    pass

                raise ValueError(
                    "FILE_TOO_LARGE"
                )

            return result

        except ImportError:
            raise RuntimeError(
                "gdown is not installed"
            )

    return download_direct(
        url,
        output,
        max_size
    )


async def download_async(
    url,
    max_size,
    extension
):
    folder = tempfile.mkdtemp(
        prefix="rubka_"
    )

    output = os.path.join(
        folder,
        "file" + extension
    )

    loop = asyncio.get_running_loop()

    try:

        result = await loop.run_in_executor(
            executor,
            download_file,
            url,
            output,
            max_size
        )

        return result

    except Exception:
        shutil.rmtree(
            folder,
            ignore_errors=True
        )

        raise


# =========================================================
# IMAGE
# =========================================================

def convert_jpg(
    source,
    output
):
    with Image.open(source) as image:

        image = image.convert(
            "RGB"
        )

        image.save(
            output,
            "JPEG",
            quality=92,
            optimize=True
        )

    return output


async def convert_jpg_async(
    source
):
    output = os.path.join(
        os.path.dirname(source),
        "image.jpg"
    )

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        convert_jpg,
        source,
        output
    )


# =========================================================
# MP3
# =========================================================

def edit_mp3(
    source,
    output,
    title,
    artist,
    cover
):
    shutil.copy2(
        source,
        output
    )

    try:
        MP3(output)

        try:
            tags = ID3(output)
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

        if cover and os.path.exists(cover):

            with open(
                cover,
                "rb"
            ) as f:
                data = f.read()

            tags.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=data
                )
            )

        tags.save(
            output,
            v2_version=3
        )

        return output

    except Exception:
        raise


async def edit_mp3_async(
    source,
    title,
    artist,
    cover
):
    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        title
    ).strip()

    if not safe_title:
        safe_title = "song"

    output = os.path.join(
        os.path.dirname(source),
        safe_title + ".mp3"
    )

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        edit_mp3,
        source,
        output,
        title,
        artist,
        cover
    )


# =========================================================
# CACHE
# =========================================================

def file_hash(path):
    sha = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as f:

        while True:

            data = f.read(
                1024 * 1024
            )

            if not data:
                break

            sha.update(data)

    return sha.hexdigest()


def cache_file(
    path,
    kind
):
    return (
        kind
        + "_"
        + file_hash(path)
    )


def save_cache(
    path,
    kind,
    file_id,
    message_id,
    caption,
    button_text
):
    key = cache_file(
        path,
        kind
    )

    media_cache[key] = {
        "kind": kind,
        "file_id": file_id,
        "message_id": (
            str(message_id)
            if message_id
            else None
        ),
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

    return key


# =========================================================
# SEND MEDIA
# =========================================================

async def send_music(
    chat_id,
    path=None,
    file_id=None,
    caption="",
    inline=None
):
    kwargs = {
        "chat_id": str(chat_id),
        "text": caption or ""
    }

    if file_id:
        kwargs["file_id"] = file_id
    else:
        kwargs["path"] = path

    if inline:
        kwargs["inline_keypad"] = inline

    try:
        return await bot.send_music(
            **kwargs
        )
    except Exception as e:
        print("SEND MUSIC ERROR:", repr(e))
        return None


async def send_voice(
    chat_id,
    path=None,
    file_id=None,
    caption="",
    inline=None
):
    kwargs = {
        "chat_id": str(chat_id),
        "text": caption or ""
    }

    if file_id:
        kwargs["file_id"] = file_id
    else:
        kwargs["path"] = path

    if inline:
        kwargs["inline_keypad"] = inline

    try:
        return await bot.send_voice(
            **kwargs
        )
    except Exception as e:
        print("SEND VOICE ERROR:", repr(e))
        return None


async def send_image(
    chat_id,
    path=None,
    file_id=None,
    caption="",
    inline=None
):
    kwargs = {
        "chat_id": str(chat_id),
        "text": caption or ""
    }

    if file_id:
        kwargs["file_id"] = file_id
    else:
        kwargs["path"] = path

    if inline:
        kwargs["inline_keypad"] = inline

    try:
        return await bot.send_image(
            **kwargs
        )
    except Exception as e:
        print("SEND IMAGE ERROR:", repr(e))
        return None


# =========================================================
# UPLOAD + CACHE
# =========================================================

async def upload_and_cache(
    chat_id,
    path,
    kind,
    caption,
    button_text
):
    inline = None

    if button_text:
        inline = make_glass_button(
            button_text
        )

    if kind == "music":

        sent = await send_music(
            chat_id,
            path=path,
            caption=caption,
            inline=inline
        )

    elif kind == "voice":

        sent = await send_voice(
            chat_id,
            path=path,
            caption=caption,
            inline=inline
        )

    elif kind == "banner":

        sent = await send_image(
            chat_id,
            path=path,
            caption=caption,
            inline=inline
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

        save_cache(
            path=path,
            kind=kind,
            file_id=file_id,
            message_id=message_id,
            caption=caption,
            button_text=button_text
        )

    return sent


# =========================================================
# SEND CACHED
# =========================================================

async def send_cached(
    chat_id,
    item
):
    if not item:
        return None

    kind = item.get(
        "kind"
    )

    file_id = item.get(
        "file_id"
    )

    caption = item.get(
        "caption",
        ""
    )

    button_text = item.get(
        "button_text",
        ""
    )

    inline = None

    if button_text:
        inline = make_glass_button(
            button_text
        )

    if kind == "music":

        return await send_music(
            chat_id,
            file_id=file_id,
            caption=caption,
            inline=inline
        )

    if kind == "voice":

        return await send_voice(
            chat_id,
            file_id=file_id,
            caption=caption,
            inline=inline
        )

    if kind == "banner":

        return await send_image(
            chat_id,
            file_id=file_id,
            caption=caption,
            inline=inline
        )

    return None


# =========================================================
# RESEND
# =========================================================

async def try_resend(
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

    result = await send_cached(
        chat_id,
        item
    )

    return result is not None


# =========================================================
# SESSION CLEANUP
# =========================================================

def cleanup_session(
    session
):
    if not session:
        return

    paths = [
        session.get("source_path"),
        session.get("cover_path")
    ]

    folders = set()

    for path in paths:

        if path and os.path.exists(path):

            folders.add(
                os.path.dirname(path)
            )

    for path in paths:

        if path and os.path.exists(path):

            try:
                os.remove(path)
            except Exception:
                pass

    for folder in folders:

        try:
            if os.path.exists(folder):
                os.rmdir(folder)
        except Exception:
            pass


# =========================================================
# START
# =========================================================

async def start_bot_session(
    chat_id
):
    sessions[chat_id] = {
        "step": "main",
        "kind": None,
        "source_url": None,
        "source_path": None,
        "cover_path": None,
        "caption": DEFAULT_CAPTION,
        "title": None,
        "artist": None,
        "button_text": ""
    }

    await send_prompt(
        chat_id,
        "👇",
        main_keyboard()
    )


# =========================================================
# BANNER
# =========================================================

async def banner_start(
    chat_id
):
    sessions[chat_id] = {
        "step": "banner_url",
        "kind": "banner",
        "source_url": None,
        "source_path": None,
        "cover_path": None,
        "caption": DEFAULT_CAPTION,
        "title": None,
        "artist": None,
        "button_text": ""
    }

    await send_prompt(
        chat_id,
        "🔗"
    )


async def banner_url(
    chat_id,
    text
):
    if not is_url(text):

        await send_prompt(
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

    await send_prompt(
        chat_id,
        "پیش‌نمایش لازم دارید؟",
        yes_no_keyboard()
    )


async def banner_preview(
    chat_id,
    text
):
    if text not in (
        "بله",
        "نه"
    ):
        return

    session = sessions[chat_id]

    try:

        raw = await download_async(
            session["source_url"],
            MAX_IMAGE_SIZE,
            ".img"
        )

        jpg = await convert_jpg_async(
            raw
        )

        session[
            "source_path"
        ] = jpg

        if text == "بله":

            await send_image(
                chat_id,
                path=jpg
            )

    except Exception as e:

        print(
            "BANNER DOWNLOAD ERROR:",
            repr(e)
        )

        await send_prompt(
            chat_id,
            "❌"
        )

        return

    session[
        "step"
    ] = "banner_caption"

    await send_prompt(
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

    await send_prompt(
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

    session = sessions[chat_id]

    session[
        "button_text"
    ] = text

    await send_prompt(
        chat_id,
        "⚙️"
    )

    try:

        sent = await upload_and_cache(
            chat_id,
            session["source_path"],
            "banner",
            session["caption"],
            session["button_text"]
        )

        if sent:
            await send_prompt(
                chat_id,
                "👇",
                main_keyboard()
            )
        else:
            await send_prompt(
                chat_id,
                "❌",
                main_keyboard()
            )

    except Exception as e:

        print(
            "BANNER FINAL ERROR:",
            repr(e)
        )

        await send_prompt(
            chat_id,
            "❌",
            main_keyboard()
        )

    finally:

        cleanup_session(
            session
        )

        sessions.pop(
            chat_id,
            None
        )


# =========================================================
# MUSIC
# =========================================================

async def music_start(
    chat_id
):
    sessions[chat_id] = {
        "step": "music_url",
        "kind": "music",
        "source_url": None,
        "source_path": None,
        "cover_path": None,
        "caption": DEFAULT_CAPTION,
        "title": None,
        "artist": None,
        "button_text": ""
    }

    await send_prompt(
        chat_id,
        "🔗"
    )


async def music_url(
    chat_id,
    text
):
    if not is_url(text):

        await send_prompt(
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

    await send_prompt(
        chat_id,
        "پیش‌نمایش لازم دارید؟",
        yes_no_keyboard()
    )


async def music_preview(
    chat_id,
    text
):
    if text not in (
        "بله",
        "نه"
    ):
        return

    session = sessions[chat_id]

    try:

        path = await download_async(
            session["source_url"],
            MAX_AUDIO_SIZE,
            ".audio"
        )

        session[
            "source_path"
        ] = path

        if text == "بله":

            await send_music(
                chat_id,
                path=path
            )

    except Exception as e:

        print(
            "MUSIC DOWNLOAD ERROR:",
            repr(e)
        )

        await send_prompt(
            chat_id,
            "❌"
        )

        return

    session[
        "step"
    ] = "music_caption"

    await send_prompt(
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

    await send_prompt(
        chat_id,
        "🎵",
        media_keyboard()
    )


# =========================================================
# SONG
# =========================================================

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

    await send_prompt(
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

    await send_prompt(
        chat_id,
        "🖼️",
        next_keyboard()
    )


async def song_cover(
    chat_id,
    text
):
    session = sessions[chat_id]

    if text != "بعدی":

        if not is_url(text):

            await send_prompt(
                chat_id,
                "❌",
                next_keyboard()
            )

            return

        try:

            raw = await download_async(
                text,
                MAX_COVER_SIZE,
                ".img"
            )

            jpg = await convert_jpg_async(
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

            await send_prompt(
                chat_id,
                "❌"
            )

            return

    session[
        "step"
    ] = "song_button"

    await send_prompt(
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

    session = sessions[chat_id]

    session[
        "button_text"
    ] = text

    await send_prompt(
        chat_id,
        "⚙️"
    )

    try:

        final_mp3 = await edit_mp3_async(
            session["source_path"],
            session["title"],
            session["artist"],
            session["cover_path"]
        )

        sent = await upload_and_cache(
            chat_id,
            final_mp3,
            "music",
            session["caption"],
            session["button_text"]
        )

        if sent:

            await send_prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

        else:

            await send_prompt(
                chat_id,
                "❌",
                main_keyboard()
            )

    except Exception as e:

        print(
            "SONG FINAL ERROR:",
            repr(e)
        )

        await send_prompt(
            chat_id,
            "❌",
            main_keyboard()
        )

    finally:

        cleanup_session(
            session
        )

        sessions.pop(
            chat_id,
            None
        )


# =========================================================
# VOICE
# =========================================================

async def voice_button(
    chat_id,
    text
):
    if text == "بعدی":
        text = ""

    session = sessions[chat_id]

    session[
        "button_text"
    ] = text

    await send_prompt(
        chat_id,
        "⚙️"
    )

    try:

        sent = await upload_and_cache(
            chat_id,
            session["source_path"],
            "voice",
            session["caption"],
            session["button_text"]
        )

        if sent:

            await send_prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

        else:

            await send_prompt(
                chat_id,
                "❌",
                main_keyboard()
            )

    except Exception as e:

        print(
            "VOICE FINAL ERROR:",
            repr(e)
        )

        await send_prompt(
            chat_id,
            "❌",
            main_keyboard()
        )

    finally:

        cleanup_session(
            session
        )

        sessions.pop(
            chat_id,
            None
        )


# =========================================================
# MAIN HANDLER
# =========================================================
# Rubka 8.1.10 handler receives:
# bot, message
# =========================================================

@bot.on_message()
async def on_message(
    bot_instance,
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

            await start_bot_session(
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

            result = await try_resend(
                chat_id,
                message
            )

            if result:
                return

        # ---------------------------------------------
        # MAIN MENU
        # ---------------------------------------------

        if text == "🖼 ساخت بنر":

            await banner_start(
                chat_id
            )

            return

        if text == "🎵 ادیت آهنگ":

            await music_start(
                chat_id
            )

            return

        # ---------------------------------------------
        # NO SESSION
        # ---------------------------------------------

        if chat_id not in sessions:

            await send_prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

            return

        session = sessions[
            chat_id
        ]

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

            await banner_preview(
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

            await music_preview(
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

                session[
                    "step"
                ] = "song_title"

                await send_prompt(
                    chat_id,
                    "🎵"
                )

            elif text == "🎤 ویس":

                session[
                    "step"
                ] = "voice_button"

                await send_prompt(
                    chat_id,
                    "🔘",
                    next_keyboard()
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
        "======================================"
    )

    print(
        "       RUBIKA BOT STARTED"
    )

    print(
        "       Rubka 8.1.10"
    )

    print(
        "======================================"
    )

    bot.run()
