import os
import re
import json
import time
import shutil
import asyncio
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
import gdown

from PIL import Image
from mutagen.id3 import ID3, TIT2, TPE1, APIC
from mutagen.mp3 import MP3

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder
from rubka.asynco import InlineBuilder


# =========================================================
# CONFIG
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# آیدی سازنده
OWNER_ID = "b0FXnfh0BD5202f5617bb7eea6e39f2d"

USERS_FILE = "users.json"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_AUDIO_SIZE = 200 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024

DOWNLOAD_TIMEOUT = 60


# =========================================================
# BOT
# =========================================================

bot = Robot(TOKEN)


# =========================================================
# STATE
# =========================================================

user_states = {}


# =========================================================
# USERS
# =========================================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception as e:
        print("users.json error:", e)

    return {}


def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                users,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        print("save users error:", e)


def register_user(chat_id):
    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:
        users[chat_id] = {
            "messages": 0,
            "last_message": int(time.time())
        }

    else:
        if not isinstance(users[chat_id], dict):
            users[chat_id] = {
                "messages": 0,
                "last_message": int(time.time())
            }

    save_users(users)


def count_user_message(chat_id):
    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:
        users[chat_id] = {
            "messages": 0,
            "last_message": int(time.time())
        }

    users[chat_id]["messages"] = int(
        users[chat_id].get("messages", 0)
    ) + 1

    users[chat_id]["last_message"] = int(time.time())

    save_users(users)


def get_users_by_activity():
    users = load_users()

    result = []

    for chat_id, info in users.items():

        if not isinstance(info, dict):
            continue

        messages = int(
            info.get("messages", 0)
        )

        last_message = int(
            info.get("last_message", 0)
        )

        result.append(
            (
                str(chat_id),
                messages,
                last_message
            )
        )

    # بیشترین پیام اول
    # در صورت مساوی بودن، جدیدترین کاربر اول
    result.sort(
        key=lambda x: (x[1], x[2]),
        reverse=True
    )

    return [x[0] for x in result]


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    builder = ChatKeypadBuilder()

    builder.button(
        id="banner",
        text="🖼 ساخت بنر",
        type="Simple"
    )

    builder.button(
        id="music",
        text="🎵 ادیت آهنگ",
        type="Simple"
    )

    return builder.build(
        resize_keyboard=True,
        on_time_keyboard=False
    )


def next_keyboard():
    builder = ChatKeypadBuilder()

    builder.button(
        id="next",
        text="بعدی",
        type="Simple"
    )

    return builder.build(
        resize_keyboard=True,
        on_time_keyboard=False
    )


def media_type_keyboard():
    builder = ChatKeypadBuilder()

    builder.button(
        id="music",
        text="🎵 آهنگ",
        type="Simple"
    )

    builder.button(
        id="voice",
        text="🎤 ویس",
        type="Simple"
    )

    return builder.build(
        resize_keyboard=True,
        on_time_keyboard=False
    )


# =========================================================
# GLASS DISPLAY BUTTON
# =========================================================

def make_glass_button(text):
    """
    دکمه شیشه‌ای نمایشی
    بدون لینک
    """

    if not text:
        return None

    text = str(text).strip()

    if not text:
        return None

    builder = InlineBuilder()

    builder.button(
        id="display_button",
        text=text
    )

    return builder.build()


# =========================================================
# URL
# =========================================================

def extract_url(text):
    if not text:
        return None

    match = re.search(
        r"https?://[^\s]+",
        text.strip()
    )

    if not match:
        return None

    return match.group(0).strip()


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

def download_direct(url, output_path, max_size):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    with requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=DOWNLOAD_TIMEOUT,
        allow_redirects=True
    ) as response:

        response.raise_for_status()

        content_length = response.headers.get(
            "content-length"
        )

        if content_length:
            try:
                if int(content_length) > max_size:
                    raise ValueError(
                        "فایل بزرگ‌تر از حد مجاز است."
                    )
            except ValueError:
                pass

        total = 0

        with open(output_path, "wb") as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                total += len(chunk)

                if total > max_size:
                    f.close()

                    try:
                        os.remove(output_path)
                    except:
                        pass

                    raise ValueError(
                        "حجم فایل بیشتر از حد مجاز است."
                    )

                f.write(chunk)

    return output_path


def download_file(url, output_path, max_size):
    if is_google_drive(url):

        try:
            gdown.download(
                url,
                output_path,
                quiet=False,
                fuzzy=True
            )
        except Exception as e:
            raise ValueError(
                f"خطا در دانلود Google Drive:\n{e}"
            )

        if not os.path.exists(output_path):
            raise ValueError(
                "دانلود فایل انجام نشد."
            )

        if os.path.getsize(output_path) > max_size:
            os.remove(output_path)

            raise ValueError(
                "حجم فایل بیشتر از حد مجاز است."
            )

        return output_path

    return download_direct(
        url,
        output_path,
        max_size
    )


# =========================================================
# COVER
# =========================================================

def download_cover(url, output_path):
    temp_file = output_path + ".download"

    try:
        download_direct(
            url,
            temp_file,
            MAX_COVER_SIZE
        )

        with Image.open(temp_file) as img:

            img = img.convert("RGB")

            img.save(
                output_path,
                "JPEG",
                quality=92
            )

        return output_path

    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


# =========================================================
# AUDIO METADATA
# =========================================================

def edit_mp3_metadata(
    mp3_path,
    title,
    artist,
    cover_path=None
):

    try:
        try:
            audio = MP3(mp3_path)
        except Exception:
            audio = None

        if audio is None:
            return

        try:
            tags = audio.tags

            if tags is None:
                audio.add_tags()

            tags = audio.tags

        except Exception:
            return

        if title:
            tags.delall("TIT2")

            tags.add(
                TIT2(
                    encoding=3,
                    text=str(title)
                )
            )

        if artist:
            tags.delall("TPE1")

            tags.add(
                TPE1(
                    encoding=3,
                    text=str(artist)
                )
            )

        if cover_path and os.path.exists(cover_path):

            try:
                with open(
                    cover_path,
                    "rb"
                ) as f:
                    cover_data = f.read()

                tags.delall("APIC")

                tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=cover_data
                    )
                )

            except Exception as e:
                print(
                    "cover metadata error:",
                    e
                )

        audio.save()

    except Exception as e:
        print(
            "metadata error:",
            e
        )


# =========================================================
# RENAME
# =========================================================

def safe_filename(name):
    if not name:
        return "audio"

    name = str(name).strip()

    name = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        name
    )

    name = name.strip(". ")

    if not name:
        name = "audio"

    return name


# =========================================================
# PREVIEW
# =========================================================

async def send_downloaded_banner_to_user(
    chat_id,
    image_path
):

    try:

        await bot.send_image(
            chat_id=str(chat_id),
            path=image_path,
            text="🖼 پیش‌نمایش تصویر دریافت‌شده"
        )

        return True

    except Exception as e:

        print(
            "banner preview error:",
            e
        )

        return False


async def send_downloaded_audio_to_user(
    chat_id,
    audio_path
):

    try:

        await bot.send_music(
            chat_id=str(chat_id),
            path=audio_path,
            text="🎵 پیش‌نمایش آهنگ دریافت‌شده"
        )

        return True

    except Exception as e:

        print(
            "audio preview error:",
            e
        )

        return False


# =========================================================
# BROADCAST MUSIC
# =========================================================

async def broadcast_music(
    audio_path,
    caption,
    glass_button,
    owner_id
):

    users = get_users_by_activity()

    # -----------------------------------------
    # اول سازنده
    # -----------------------------------------

    sent_to_owner = False

    try:

        await bot.send_music(
            chat_id=str(owner_id),
            path=audio_path,
            text=caption,
            inline_keypad=glass_button
        )

        sent_to_owner = True

    except Exception as e:

        print(
            "send music to owner error:",
            e
        )

    # -----------------------------------------
    # سپس کاربران
    # -----------------------------------------

    for chat_id in users:

        chat_id = str(chat_id)

        # سازنده دوباره ارسال نشود
        if chat_id == str(owner_id):
            continue

        try:

            await bot.send_music(
                chat_id=chat_id,
                path=audio_path,
                text=caption,
                inline_keypad=glass_button
            )

            print(
                "music sent:",
                chat_id
            )

        except Exception as e:

            print(
                "music send error:",
                chat_id,
                e
            )

        # ارسال یکی‌یکی
        await asyncio.sleep(0.3)

    return sent_to_owner


# =========================================================
# BROADCAST VOICE
# =========================================================

async def broadcast_voice(
    audio_path,
    caption,
    glass_button,
    owner_id
):

    users = get_users_by_activity()

    # -----------------------------------------
    # اول سازنده
    # -----------------------------------------

    sent_to_owner = False

    try:

        await bot.send_voice(
            chat_id=str(owner_id),
            path=audio_path,
            text=caption,
            inline_keypad=glass_button
        )

        sent_to_owner = True

    except Exception as e:

        print(
            "send voice to owner error:",
            e
        )

    # -----------------------------------------
    # سپس کاربران
    # -----------------------------------------

    for chat_id in users:

        chat_id = str(chat_id)

        if chat_id == str(owner_id):
            continue

        try:

            await bot.send_voice(
                chat_id=chat_id,
                path=audio_path,
                text=caption,
                inline_keypad=glass_button
            )

            print(
                "voice sent:",
                chat_id
            )

        except Exception as e:

            print(
                "voice send error:",
                chat_id,
                e
            )

        await asyncio.sleep(0.3)

    return sent_to_owner


# =========================================================
# BROADCAST BANNER
# =========================================================

async def broadcast_banner(
    image_path,
    caption,
    glass_button,
    owner_id
):

    users = get_users_by_activity()

    # -----------------------------------------
    # اول سازنده
    # -----------------------------------------

    sent_to_owner = False

    try:

        await bot.send_image(
            chat_id=str(owner_id),
            path=image_path,
            text=caption,
            inline_keypad=glass_button
        )

        sent_to_owner = True

    except Exception as e:

        print(
            "send banner to owner error:",
            e
        )

    # -----------------------------------------
    # سپس کاربران
    # -----------------------------------------

    for chat_id in users:

        chat_id = str(chat_id)

        if chat_id == str(owner_id):
            continue

        try:

            await bot.send_image(
                chat_id=chat_id,
                path=image_path,
                text=caption,
                inline_keypad=glass_button
            )

            print(
                "banner sent:",
                chat_id
            )

        except Exception as e:

            print(
                "banner send error:",
                chat_id,
                e
            )

        await asyncio.sleep(0.3)

    return sent_to_owner


# =========================================================
# RESET
# =========================================================

def reset_user(chat_id):
    chat_id = str(chat_id)

    if chat_id in user_states:
        del user_states[chat_id]


# =========================================================
# SEND MESSAGE HELPER
# =========================================================

async def send_text(
    chat_id,
    text,
    keypad=None
):

    await bot.send_message(
        chat_id=str(chat_id),
        text=text,
        chat_keypad=keypad
    )


# =========================================================
# START
# =========================================================

async def handle_start(chat_id):

    reset_user(chat_id)

    await send_text(
        chat_id,
        "سلام 👋\nیک گزینه را انتخاب کن:",
        main_keyboard()
    )


# =========================================================
# MAIN HANDLER
# =========================================================

@bot.on_message()
async def handle_message(bot_instance, message):

    try:

        # -----------------------------------------
        # CHAT ID
        # -----------------------------------------

        chat_id = str(
            getattr(
                message,
                "chat_id",
                ""
            )
        )

        if not chat_id:
            return

        # -----------------------------------------
        # REGISTER
        # -----------------------------------------

        register_user(chat_id)
        count_user_message(chat_id)

        # -----------------------------------------
        # TEXT
        # -----------------------------------------

        text = getattr(
            message,
            "text",
            None
        )

        if text is None:
            text = ""

        text = str(text).strip()

        # -----------------------------------------
        # START
        # -----------------------------------------

        if text == "/start":

            await handle_start(chat_id)

            return

        # =================================================
        # EXISTING STATE
        # =================================================

        state = user_states.get(chat_id)

        # =================================================
        # MAIN MENU
        # =================================================

        if not state:

            if text == "🖼 ساخت بنر":

                user_states[chat_id] = {
                    "type": "banner",
                    "step": "banner_url",
                    "temp_dir": tempfile.mkdtemp(
                        prefix="rubka_banner_"
                    )
                }

                await send_text(
                    chat_id,
                    "لینک تصویر را بفرست:"
                )

                return

            if text == "🎵 ادیت آهنگ":

                user_states[chat_id] = {
                    "type": "music",
                    "step": "audio_url",
                    "temp_dir": tempfile.mkdtemp(
                        prefix="rubka_audio_"
                    )
                }

                await send_text(
                    chat_id,
                    "لینک آهنگ را بفرست:"
                )

                return

            await send_text(
                chat_id,
                "یکی از گزینه‌های منو را انتخاب کن:",
                main_keyboard()
            )

            return

        # =================================================
        # BANNER
        # =================================================

        if state["type"] == "banner":

            step = state["step"]
            temp_dir = state["temp_dir"]

            # -----------------------------------------
            # URL
            # -----------------------------------------

            if step == "banner_url":

                url = extract_url(text)

                if not url:

                    await send_text(
                        chat_id,
                        "لینک تصویر معتبر نیست."
                    )

                    return

                image_path = os.path.join(
                    temp_dir,
                    "banner.jpg"
                )

                try:

                    await send_text(
                        chat_id,
                        "⏳ در حال دریافت تصویر..."
                    )

                    download_file(
                        url,
                        image_path,
                        MAX_IMAGE_SIZE
                    )

                    # پیش نمایش فقط برای درخواست کننده
                    await send_downloaded_banner_to_user(
                        chat_id,
                        image_path
                    )

                except Exception as e:

                    print(
                        "banner download:",
                        e
                    )

                    await send_text(
                        chat_id,
                        f"❌ دریافت تصویر انجام نشد.\n{e}"
                    )

                    return

                state["image_path"] = image_path
                state["step"] = "banner_caption"

                await send_text(
                    chat_id,
                    "کپشن را بفرست یا «بعدی» را بزن:",
                    next_keyboard()
                )

                return

            # -----------------------------------------
            # CAPTION
            # -----------------------------------------

            if step == "banner_caption":

                if text == "بعدی":

                    state["caption"] = ""

                else:

                    state["caption"] = text

                state["step"] = "banner_button"

                await send_text(
                    chat_id,
                    "متن دکمه شیشه‌ای نمایشی را بفرست یا «بعدی» را بزن:",
                    next_keyboard()
                )

                return

            # -----------------------------------------
            # BUTTON
            # -----------------------------------------

            if step == "banner_button":

                if text == "بعدی":

                    state["button_text"] = ""

                else:

                    state["button_text"] = text

                glass_button = make_glass_button(
                    state["button_text"]
                )

                await send_text(
                    chat_id,
                    "⏳ در حال ارسال بنر..."
                )

                try:

                    await broadcast_banner(
                        image_path=state["image_path"],
                        caption=state.get(
                            "caption",
                            ""
                        ),
                        glass_button=glass_button,
                        owner_id=OWNER_ID
                    )

                    await send_text(
                        chat_id,
                        "✅ بنر برای سازنده و کاربران ارسال شد.",
                        main_keyboard()
                    )

                except Exception as e:

                    print(
                        "banner broadcast:",
                        e
                    )

                    await send_text(
                        chat_id,
                        f"❌ خطا در ارسال بنر:\n{e}",
                        main_keyboard()
                    )

                finally:

                    try:
                        shutil.rmtree(
                            temp_dir,
                            ignore_errors=True
                        )
                    except:
                        pass

                    reset_user(chat_id)

                return

        # =================================================
        # AUDIO
        # =================================================

        if state["type"] == "music":

            step = state["step"]
            temp_dir = state["temp_dir"]

            # -----------------------------------------
            # AUDIO URL
            # -----------------------------------------

            if step == "audio_url":

                url = extract_url(text)

                if not url:

                    await send_text(
                        chat_id,
                        "لینک آهنگ معتبر نیست."
                    )

                    return

                audio_path = os.path.join(
                    temp_dir,
                    "audio.mp3"
                )

                try:

                    await send_text(
                        chat_id,
                        "⏳ در حال دریافت آهنگ..."
                    )

                    download_file(
                        url,
                        audio_path,
                        MAX_AUDIO_SIZE
                    )

                    # پیش‌نمایش فقط برای درخواست‌کننده
                    await send_downloaded_audio_to_user(
                        chat_id,
                        audio_path
                    )

                except Exception as e:

                    print(
                        "audio download:",
                        e
                    )

                    await send_text(
                        chat_id,
                        f"❌ دریافت آهنگ انجام نشد.\n{e}"
                    )

                    return

                state["audio_path"] = audio_path
                state["step"] = "audio_caption"

                await send_text(
                    chat_id,
                    "کپشن را بفرست یا «بعدی» را بزن:",
                    next_keyboard()
                )

                return

            # -----------------------------------------
            # CAPTION
            # -----------------------------------------

            if step == "audio_caption":

                if text == "بعدی":

                    state["caption"] = DEFAULT_CAPTION

                else:

                    state["caption"] = text

                state["step"] = "audio_type"

                await send_text(
                    chat_id,
                    "نوع ارسال را انتخاب کن:",
                    media_type_keyboard()
                )

                return

            # -----------------------------------------
            # TYPE
            # -----------------------------------------

            if step == "audio_type":

                if text == "🎵 آهنگ":

                    state["media_type"] = "music"
                    state["step"] = "song_title"

                    await send_text(
                        chat_id,
                        "نام آهنگ را بفرست:"
                    )

                    return

                if text == "🎤 ویس":

                    state["media_type"] = "voice"
                    state["step"] = "voice_button"

                    await send_text(
                        chat_id,
                        "متن دکمه شیشه‌ای نمایشی را بفرست یا «بعدی» را بزن:",
                        next_keyboard()
                    )

                    return

                await send_text(
                    chat_id,
                    "یکی از گزینه‌ها را انتخاب کن:",
                    media_type_keyboard()
                )

                return

            # =================================================
            # MUSIC
            # =================================================

            if state.get("media_type") == "music":

                # -----------------------------------------
                # TITLE
                # -----------------------------------------

                if step == "song_title":

                    if not text:

                        await send_text(
                            chat_id,
                            "نام آهنگ را بفرست:"
                        )

                        return

                    state["title"] = text
                    state["step"] = "song_artist"

                    await send_text(
                        chat_id,
                        "نام خواننده را بفرست:"
                    )

                    return

                # -----------------------------------------
                # ARTIST
                # -----------------------------------------

                if step == "song_artist":

                    if not text:

                        await send_text(
                            chat_id,
                            "نام خواننده را بفرست:"
                        )

                        return

                    state["artist"] = text
                    state["step"] = "song_cover"

                    await send_text(
                        chat_id,
                        "لینک کاور را بفرست یا «بعدی» را بزن:",
                        next_keyboard()
                    )

                    return

                # -----------------------------------------
                # COVER
                # -----------------------------------------

                if step == "song_cover":

                    cover_path = None

                    if text != "بعدی":

                        cover_url = extract_url(text)

                        if not cover_url:

                            await send_text(
                                chat_id,
                                "لینک کاور معتبر نیست یا «بعدی» را بزن."
                            )

                            return

                        cover_path = os.path.join(
                            temp_dir,
                            "cover.jpg"
                        )

                        try:

                            await send_text(
                                chat_id,
                                "⏳ در حال دریافت کاور..."
                            )

                            download_cover(
                                cover_url,
                                cover_path
                            )

                        except Exception as e:

                            print(
                                "cover download:",
                                e
                            )

                            await send_text(
                                chat_id,
                                f"❌ دریافت کاور انجام نشد.\n{e}"
                            )

                            return

                    state["cover_path"] = cover_path
                    state["step"] = "music_button"

                    await send_text(
                        chat_id,
                        "متن دکمه شیشه‌ای نمایشی را بفرست یا «بعدی» را بزن:",
                        next_keyboard()
                    )

                    return

                # -----------------------------------------
                # MUSIC BUTTON
                # -----------------------------------------

                if step == "music_button":

                    if text == "بعدی":

                        state["button_text"] = ""

                    else:

                        state["button_text"] = text

                    glass_button = make_glass_button(
                        state["button_text"]
                    )

                    audio_path = state["audio_path"]

                    # متادیتا
                    edit_mp3_metadata(
                        mp3_path=audio_path,
                        title=state.get(
                            "title",
                            ""
                        ),
                        artist=state.get(
                            "artist",
                            ""
                        ),
                        cover_path=state.get(
                            "cover_path"
                        )
                    )

                    # تغییر نام فایل
                    new_name = (
                        safe_filename(
                            state.get(
                                "title",
                                "audio"
                            )
                        )
                        + ".mp3"
                    )

                    new_path = os.path.join(
                        temp_dir,
                        new_name
                    )

                    try:

                        os.rename(
                            audio_path,
                            new_path
                        )

                        audio_path = new_path

                    except Exception as e:

                        print(
                            "rename error:",
                            e
                        )

                    await send_text(
                        chat_id,
                        "⏳ در حال ارسال آهنگ..."
                    )

                    try:

                        await broadcast_music(
                            audio_path=audio_path,
                            caption=state.get(
                                "caption",
                                DEFAULT_CAPTION
                            ),
                            glass_button=glass_button,
                            owner_id=OWNER_ID
                        )

                        await send_text(
                            chat_id,
                            "✅ آهنگ برای سازنده و کاربران ارسال شد.",
                            main_keyboard()
                        )

                    except Exception as e:

                        print(
                            "music broadcast:",
                            e
                        )

                        await send_text(
                            chat_id,
                            f"❌ خطا در ارسال آهنگ:\n{e}",
                            main_keyboard()
                        )

                    finally:

                        try:
                            shutil.rmtree(
                                temp_dir,
                                ignore_errors=True
                            )
                        except:
                            pass

                        reset_user(chat_id)

                    return

            # =================================================
            # VOICE
            # =================================================

            if state.get("media_type") == "voice":

                if step == "voice_button":

                    if text == "بعدی":

                        state["button_text"] = ""

                    else:

                        state["button_text"] = text

                    glass_button = make_glass_button(
                        state["button_text"]
                    )

                    await send_text(
                        chat_id,
                        "⏳ در حال ارسال ویس..."
                    )

                    try:

                        await broadcast_voice(
                            audio_path=state["audio_path"],
                            caption=state.get(
                                "caption",
                                DEFAULT_CAPTION
                            ),
                            glass_button=glass_button,
                            owner_id=OWNER_ID
                        )

                        await send_text(
                            chat_id,
                            "✅ ویس برای سازنده و کاربران ارسال شد.",
                            main_keyboard()
                        )

                    except Exception as e:

                        print(
                            "voice broadcast:",
                            e
                        )

                        await send_text(
                            chat_id,
                            f"❌ خطا در ارسال ویس:\n{e}",
                            main_keyboard()
                        )

                    finally:

                        try:
                            shutil.rmtree(
                                temp_dir,
                                ignore_errors=True
                            )
                        except:
                            pass

                        reset_user(chat_id)

                    return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )

        try:

            await send_text(
                chat_id,
                f"❌ خطای غیرمنتظره:\n{e}",
                main_keyboard()
            )

        except Exception as send_error:

            print(
                "error message failed:",
                send_error
            )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    print("====================================")
    print("        RUBKA BOT STARTED")
    print("====================================")
    print("Owner:", OWNER_ID)
    print("Rubka:", "8.1.10")
    print()

    bot.run()
