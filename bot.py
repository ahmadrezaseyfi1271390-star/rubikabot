import os
import re
import json
import time
import asyncio
import requests
import gdown

from PIL import Image
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC

from rubka import Robot, Message
from rubka.button import InlineBuilder


# =========================================================
# CONFIG
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# شناسه سازنده
# مهم: رشته باشد، نه int
OWNER_ID = "b0FXnfh0BD5202f5617bb7eea6e39f2d"

USERS_FILE = "users.json"

DOWNLOAD_DIR = "downloads"

MAX_AUDIO_SIZE = 200 * 1024 * 1024
MAX_IMAGE_SIZE = 20 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024

DEFAULT_CAPTION = "@Black_list_remix"


os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =========================================================
# BOT
# =========================================================

bot = Robot(
    token=TOKEN,
    parse_mode="HTML"
)


# =========================================================
# USER STATES
# =========================================================

user_states = {}


# =========================================================
# USERS JSON
# =========================================================

def load_users():

    if not os.path.exists(USERS_FILE):
        return {}

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):
                return data

    except Exception as e:

        print("users.json read error:", e)

    return {}


def save_users(users):

    try:

        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                users,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print("users.json save error:", e)


def register_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users[chat_id] = {
            "messages": 0,
            "last_message": 0
        }

        save_users(users)


def count_user_message(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users[chat_id] = {
            "messages": 0,
            "last_message": 0
        }

    users[chat_id]["messages"] += 1
    users[chat_id]["last_message"] = int(time.time())

    save_users(users)


def get_users_by_activity():

    users = load_users()

    result = []

    for chat_id, data in users.items():

        try:

            messages = int(
                data.get("messages", 0)
            )

            last_message = int(
                data.get("last_message", 0)
            )

            result.append(
                (
                    str(chat_id),
                    messages,
                    last_message
                )
            )

        except Exception:
            continue

    # بیشترین پیام اول
    # در صورت مساوی بودن، آخرین فعالیت جدیدتر اول
    result.sort(
        key=lambda x: (
            x[1],
            x[2]
        ),
        reverse=True
    )

    return [
        item[0]
        for item in result
    ]


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    return bot.build_keypad(
        [
            [
                ("🖼 ساخت بنر", "🖼 ساخت بنر"),
                ("🎵 ادیت آهنگ", "🎵 ادیت آهنگ")
            ]
        ]
    )


# =========================================================
# NEXT BUTTON
# =========================================================

def next_keyboard():

    return bot.build_keypad(
        [
            [
                ("بعدی", "بعدی")
            ]
        ]
    )


# =========================================================
# MUSIC / VOICE TYPE
# =========================================================

def media_type_keyboard():

    return bot.build_keypad(
        [
            [
                ("🎵 آهنگ", "🎵 آهنگ"),
                ("🎤 ویس", "🎤 ویس")
            ]
        ]
    )


# =========================================================
# GLASS BUTTON
# =========================================================

def make_glass_button(text):

    if not text:
        return None

    try:

        builder = InlineBuilder()

        builder.button(
            id="display_button",
            text=text
        )

        return builder.build()

    except Exception as e:

        print(
            "Glass button error:",
            e
        )

        return None


# =========================================================
# URL
# =========================================================

def extract_url(text):

    if not text:
        return None

    match = re.search(
        r'https?://[^\s]+',
        text
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

def download_file(
    url,
    output_path,
    max_size
):

    try:

        print("Downloading:")
        print(url)

        # -------------------------------------------------
        # GOOGLE DRIVE
        # -------------------------------------------------

        if is_google_drive(url):

            print(
                "Google Drive detected"
            )

            result = gdown.download(
                url,
                output_path,
                quiet=False
            )

            if not result:
                return False

            if not os.path.exists(
                output_path
            ):
                return False

            size = os.path.getsize(
                output_path
            )

            if size > max_size:

                print(
                    "File is too large:",
                    size
                )

                try:
                    os.remove(
                        output_path
                    )
                except:
                    pass

                return False

            return True

        # -------------------------------------------------
        # DIRECT URL
        # -------------------------------------------------

        headers = {
            "User-Agent":
                "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=60
        )

        response.raise_for_status()

        total = 0

        with open(
            output_path,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                total += len(chunk)

                # محدودیت حجم
                if total > max_size:

                    print(
                        "Download exceeded limit"
                    )

                    try:
                        f.close()
                    except:
                        pass

                    try:
                        os.remove(
                            output_path
                        )
                    except:
                        pass

                    return False

                f.write(chunk)

        if not os.path.exists(
            output_path
        ):
            return False

        if os.path.getsize(
            output_path
        ) == 0:

            try:
                os.remove(
                    output_path
                )
            except:
                pass

            return False

        print(
            "Downloaded:",
            total,
            "bytes"
        )

        return True

    except Exception as e:

        print(
            "Download error:",
            repr(e)
        )

        try:

            if os.path.exists(
                output_path
            ):
                os.remove(
                    output_path
                )

        except:
            pass

        return False


# =========================================================
# COVER DOWNLOAD
# =========================================================

def download_cover(
    url,
    output_path
):

    temp_path = (
        output_path +
        ".tmp"
    )

    try:

        if not download_file(
            url,
            temp_path,
            MAX_COVER_SIZE
        ):
            return False

        image = Image.open(
            temp_path
        )

        image = image.convert(
            "RGB"
        )

        image.save(
            output_path,
            "JPEG",
            quality=95
        )

        try:
            os.remove(
                temp_path
            )
        except:
            pass

        return True

    except Exception as e:

        print(
            "Cover error:",
            repr(e)
        )

        try:

            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )

        except:
            pass

        return False


# =========================================================
# MP3 METADATA
# =========================================================

def set_mp3_metadata(
    audio_path,
    title,
    singer,
    cover_path=None
):

    try:

        try:

            audio = MP3(
                audio_path,
                ID3=ID3
            )

        except:

            audio = MP3(
                audio_path
            )

        if audio.tags is None:

            audio.add_tags()

        tags = audio.tags

        # TITLE
        if title:

            tags.delall(
                "TIT2"
            )

            tags.add(
                TIT2(
                    encoding=3,
                    text=title
                )
            )

        # ARTIST
        if singer:

            tags.delall(
                "TPE1"
            )

            tags.add(
                TPE1(
                    encoding=3,
                    text=singer
                )
            )

        # COVER
        if cover_path:

            if os.path.exists(
                cover_path
            ):

                with open(
                    cover_path,
                    "rb"
                ) as f:

                    cover_data = f.read()

                tags.delall(
                    "APIC"
                )

                tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=cover_data
                    )
                )

        audio.save()

        return True

    except Exception as e:

        print(
            "Metadata error:",
            repr(e)
        )

        return False


# =========================================================
# SAFE FILENAME
# =========================================================

def safe_filename(name):

    if not name:
        return "song"

    name = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        name
    )

    name = name.strip()

    if not name:
        return "song"

    return name


# =========================================================
# SEND ORIGINAL DOWNLOAD TO REQUESTER
# =========================================================

async def send_downloaded_banner_to_user(
    chat_id,
    image_path
):

    try:

        await bot.send_image(
            chat_id=chat_id,
            path=image_path,
            text="✅"
        )

        return True

    except Exception as e:

        print(
            "Preview banner error:",
            e
        )

        return False


async def send_downloaded_audio_to_user(
    chat_id,
    audio_path
):

    try:

        await bot.send_music(
            chat_id=chat_id,
            path=audio_path,
            text="✅"
        )

        return True

    except Exception as e:

        print(
            "Preview audio error:",
            e
        )

        return False


# =========================================================
# BROADCAST MUSIC
# =========================================================

async def broadcast_music(
    audio_path,
    caption,
    inline_keypad
):

    users = get_users_by_activity()

    print(
        "=============================="
    )

    print(
        "MUSIC BROADCAST"
    )

    print(
        "Users:",
        users
    )

    # -----------------------------------------------------
    # OWNER FIRST
    # -----------------------------------------------------

    try:

        await bot.send_music(
            chat_id=OWNER_ID,
            path=audio_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        print(
            "Music -> OWNER"
        )

    except Exception as e:

        print(
            "Owner music error:",
            repr(e)
        )

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    for chat_id in users:

        chat_id = str(chat_id)

        if chat_id == str(OWNER_ID):
            continue

        try:

            await bot.send_music(
                chat_id=chat_id,
                path=audio_path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Music ->",
                chat_id
            )

        except Exception as e:

            print(
                "Music error:",
                chat_id,
                repr(e)
            )

        # جلوگیری از فشار زیاد
        await asyncio.sleep(
            0.3
        )


# =========================================================
# BROADCAST VOICE
# =========================================================

async def broadcast_voice(
    audio_path,
    caption,
    inline_keypad
):

    users = get_users_by_activity()

    print(
        "=============================="
    )

    print(
        "VOICE BROADCAST"
    )

    # -----------------------------------------------------
    # OWNER FIRST
    # -----------------------------------------------------

    try:

        await bot.send_voice(
            chat_id=OWNER_ID,
            path=audio_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        print(
            "Voice -> OWNER"
        )

    except Exception as e:

        print(
            "Owner voice error:",
            repr(e)
        )

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    for chat_id in users:

        chat_id = str(chat_id)

        if chat_id == str(OWNER_ID):
            continue

        try:

            await bot.send_voice(
                chat_id=chat_id,
                path=audio_path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Voice ->",
                chat_id
            )

        except Exception as e:

            print(
                "Voice error:",
                chat_id,
                repr(e)
            )

        await asyncio.sleep(
            0.3
        )


# =========================================================
# BROADCAST BANNER
# =========================================================

async def broadcast_banner(
    image_path,
    caption,
    inline_keypad
):

    users = get_users_by_activity()

    print(
        "=============================="
    )

    print(
        "BANNER BROADCAST"
    )

    # -----------------------------------------------------
    # OWNER FIRST
    # -----------------------------------------------------

    try:

        await bot.send_image(
            chat_id=OWNER_ID,
            path=image_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        print(
            "Banner -> OWNER"
        )

    except Exception as e:

        print(
            "Owner banner error:",
            repr(e)
        )

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    for chat_id in users:

        chat_id = str(chat_id)

        if chat_id == str(OWNER_ID):
            continue

        try:

            await bot.send_image(
                chat_id=chat_id,
                path=image_path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Banner ->",
                chat_id
            )

        except Exception as e:

            print(
                "Banner error:",
                chat_id,
                repr(e)
            )

        await asyncio.sleep(
            0.3
        )


# =========================================================
# FINISH BANNER
# =========================================================

async def finish_banner(
    chat_id
):

    state = user_states.get(
        chat_id
    )

    if not state:
        return

    image_path = state.get(
        "image_path"
    )

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    button_text = state.get(
        "button_text"
    )

    inline_keypad = None

    if button_text:

        inline_keypad = make_glass_button(
            button_text
        )

    # -----------------------------------------------------
    # IMAGE EXISTS
    # -----------------------------------------------------

    if image_path and os.path.exists(
        image_path
    ):

        await broadcast_banner(
            image_path,
            caption,
            inline_keypad
        )

    # -----------------------------------------------------
    # TEXT ONLY
    # -----------------------------------------------------

    else:

        users = get_users_by_activity()

        # OWNER
        try:

            await bot.send_message(
                chat_id=OWNER_ID,
                text=caption,
                inline_keypad=inline_keypad
            )

        except Exception as e:

            print(
                "Owner text error:",
                e
            )

        # USERS
        for user_id in users:

            user_id = str(user_id)

            if user_id == str(
                OWNER_ID
            ):
                continue

            try:

                await bot.send_message(
                    chat_id=user_id,
                    text=caption,
                    inline_keypad=inline_keypad
                )

            except Exception as e:

                print(
                    "Text broadcast error:",
                    user_id,
                    e
                )

            await asyncio.sleep(
                0.3
            )

    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    try:

        if image_path:

            if os.path.exists(
                image_path
            ):
                os.remove(
                    image_path
                )

    except Exception as e:

        print(
            "Image delete error:",
            e
        )

    user_states.pop(
        chat_id,
        None
    )

    # -----------------------------------------------------
    # DONE
    # -----------------------------------------------------

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text="✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "Finish banner error:",
            e
        )


# =========================================================
# FINISH MUSIC
# =========================================================

async def finish_music(
    chat_id
):

    state = user_states.get(
        chat_id
    )

    if not state:
        return

    audio_path = state.get(
        "audio_path"
    )

    cover_path = state.get(
        "cover_path"
    )

    title = state.get(
        "title"
    )

    singer = state.get(
        "singer"
    )

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    button_text = state.get(
        "button_text"
    )

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    if audio_path and os.path.exists(
        audio_path
    ):

        set_mp3_metadata(
            audio_path,
            title,
            singer,
            cover_path
        )

        # -------------------------------------------------
        # RENAME
        # -------------------------------------------------

        if title:

            filename = (
                safe_filename(title)
                + ".mp3"
            )

            new_path = os.path.join(
                DOWNLOAD_DIR,
                filename
            )

            try:

                if os.path.abspath(
                    new_path
                ) != os.path.abspath(
                    audio_path
                ):

                    if os.path.exists(
                        new_path
                    ):
                        os.remove(
                            new_path
                        )

                    os.rename(
                        audio_path,
                        new_path
                    )

                    audio_path = new_path

            except Exception as e:

                print(
                    "Rename error:",
                    e
                )

    # -----------------------------------------------------
    # GLASS BUTTON
    # -----------------------------------------------------

    inline_keypad = None

    if button_text:

        inline_keypad = make_glass_button(
            button_text
        )

    # -----------------------------------------------------
    # BROADCAST
    # -----------------------------------------------------

    if audio_path and os.path.exists(
        audio_path
    ):

        await broadcast_music(
            audio_path,
            caption,
            inline_keypad
        )

    # -----------------------------------------------------
    # DELETE AUDIO
    # -----------------------------------------------------

    try:

        if audio_path and os.path.exists(
            audio_path
        ):
            os.remove(
                audio_path
            )

    except Exception as e:

        print(
            "Audio delete error:",
            e
        )

    # -----------------------------------------------------
    # DELETE COVER
    # -----------------------------------------------------

    try:

        if cover_path and os.path.exists(
            cover_path
        ):
            os.remove(
                cover_path
            )

    except Exception as e:

        print(
            "Cover delete error:",
            e
        )

    user_states.pop(
        chat_id,
        None
    )

    # -----------------------------------------------------
    # DONE
    # -----------------------------------------------------

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text="✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "Finish music error:",
            e
        )


# =========================================================
# FINISH VOICE
# =========================================================

async def finish_voice(
    chat_id
):

    state = user_states.get(
        chat_id
    )

    if not state:
        return

    audio_path = state.get(
        "audio_path"
    )

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    button_text = state.get(
        "button_text"
    )

    inline_keypad = None

    if button_text:

        inline_keypad = make_glass_button(
            button_text
        )

    # -----------------------------------------------------
    # BROADCAST
    # -----------------------------------------------------

    if audio_path and os.path.exists(
        audio_path
    ):

        await broadcast_voice(
            audio_path,
            caption,
            inline_keypad
        )

    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    try:

        if audio_path and os.path.exists(
            audio_path
        ):
            os.remove(
                audio_path
            )

    except Exception as e:

        print(
            "Voice delete error:",
            e
        )

    user_states.pop(
        chat_id,
        None
    )

    # -----------------------------------------------------
    # DONE
    # -----------------------------------------------------

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text="✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "Finish voice error:",
            e
        )


# =========================================================
# MAIN MESSAGE HANDLER
# =========================================================

@bot.on_message()
async def handle_message(
    bot: Robot,
    message: Message
):

    # -----------------------------------------------------
    # CHAT ID
    # -----------------------------------------------------

    chat_id = getattr(
        message,
        "chat_id",
        None
    )

    if chat_id is None:
        return

    # مهم:
    # هرگز int نکن
    chat_id = str(chat_id)

    text = getattr(
        message,
        "text",
        ""
    ) or ""

    text = text.strip()

    print(
        "MESSAGE:",
        chat_id,
        repr(text)
    )

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    register_user(
        chat_id
    )

    count_user_message(
        chat_id
    )

    # =====================================================
    # START
    # =====================================================

    if text == "/start":

        user_states.pop(
            chat_id,
            None
        )

        await bot.send_message(
            chat_id=chat_id,
            text="سلام 👋",
            chat_keypad=main_keyboard()
        )

        return

    # =====================================================
    # BANNER
    # =====================================================

    if text == "🖼 ساخت بنر":

        user_states[chat_id] = {
            "type": "banner",
            "step": "image",
            "image_path": None,
            "caption": DEFAULT_CAPTION,
            "button_text": None
        }

        await bot.send_message(
            chat_id=chat_id,
            text="🖼",
            chat_keypad=next_keyboard()
        )

        return

    # =====================================================
    # MUSIC
    # =====================================================

    if text == "🎵 ادیت آهنگ":

        user_states[chat_id] = {
            "type": "audio",
            "step": "url",
            "audio_path": None,
            "cover_path": None,
            "caption": DEFAULT_CAPTION
        }

        await bot.send_message(
            chat_id=chat_id,
            text="🎵",
            chat_keypad=next_keyboard()
        )

        return

    # =====================================================
    # NO STATE
    # =====================================================

    if chat_id not in user_states:

        await bot.send_message(
            chat_id=chat_id,
            text="یکی از گزینه‌ها را انتخاب کن.",
            chat_keypad=main_keyboard()
        )

        return

    state = user_states[chat_id]

    step = state.get(
        "step"
    )

    # =====================================================
    # BANNER FLOW
    # =====================================================

    if state.get("type") == "banner":

        # -------------------------------------------------
        # IMAGE URL
        # -------------------------------------------------

        if step == "image":

            if text == "بعدی":

                state["image_path"] = None
                state["step"] = "caption"

                await bot.send_message(
                    chat_id=chat_id,
                    text="✏️",
                    chat_keypad=next_keyboard()
                )

                return

            url = extract_url(
                text
            )

            if not url:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            image_path = os.path.join(
                DOWNLOAD_DIR,
                "banner_"
                + safe_filename(chat_id)
                + "_"
                + str(int(time.time()))
                + ".jpg"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳"
            )

            # دانلود
            success = download_file(
                url,
                image_path,
                MAX_IMAGE_SIZE
            )

            if not success:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ دانلود انجام نشد."
                )

                return

            # ---------------------------------------------
            # فقط برای خود درخواست‌کننده
            # ---------------------------------------------

            await send_downloaded_banner_to_user(
                chat_id,
                image_path
            )

            state["image_path"] = image_path
            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text="✏️",
                chat_keypad=next_keyboard()
            )

            return

        # -------------------------------------------------
        # CAPTION
        # -------------------------------------------------

        if step == "caption":

            if text == "بعدی":

                state["caption"] = DEFAULT_CAPTION

            else:

                state["caption"] = text

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # -------------------------------------------------
        # GLASS BUTTON TEXT
        # -------------------------------------------------

        if step == "button_text":

            if text == "بعدی":

                state["button_text"] = None

                await finish_banner(
                    chat_id
                )

                return

            state["button_text"] = text

            # چون دکمه فقط نمایشی است
            # دیگر لینک نمی‌خواهیم

            await finish_banner(
                chat_id
            )

            return

    # =====================================================
    # AUDIO FLOW
    # =====================================================

    if state.get("type") == "audio":

        # -------------------------------------------------
        # DOWNLOAD URL
        # -------------------------------------------------

        if step == "url":

            url = extract_url(
                text
            )

            if not url:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ لینک نامعتبر است."
                )

                return

            audio_path = os.path.join(
                DOWNLOAD_DIR,
                "audio_"
                + safe_filename(chat_id)
                + "_"
                + str(int(time.time()))
                + ".mp3"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳"
            )

            # ---------------------------------------------
            # DOWNLOAD
            # ---------------------------------------------

            success = download_file(
                url,
                audio_path,
                MAX_AUDIO_SIZE
            )

            if not success:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ دانلود انجام نشد یا حجم فایل بیشتر از ۲۰۰MB است."
                )

                return

            # ---------------------------------------------
            # فقط برای خود کاربر
            # ---------------------------------------------

            await send_downloaded_audio_to_user(
                chat_id,
                audio_path
            )

            state["audio_path"] = audio_path
            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text="✏️",
                chat_keypad=next_keyboard()
            )

            return

        # -------------------------------------------------
        # CAPTION
        # -------------------------------------------------

        if step == "caption":

            if text == "بعدی":

                state["caption"] = DEFAULT_CAPTION

            else:

                state["caption"] = text

            state["step"] = "media_type"

            await bot.send_message(
                chat_id=chat_id,
                text="انتخاب کن:",
                chat_keypad=media_type_keyboard()
            )

            return

        # -------------------------------------------------
        # MEDIA TYPE
        # -------------------------------------------------

        if step == "media_type":

            # MUSIC
            if text == "🎵 آهنگ":

                state["media_type"] = "music"
                state["step"] = "title"

                await bot.send_message(
                    chat_id=chat_id,
                    text="🎵 عنوان آهنگ:"
                )

                return

            # VOICE
            if text == "🎤 ویس":

                state["media_type"] = "voice"
                state["step"] = "button_text"

                await bot.send_message(
                    chat_id=chat_id,
                    text="🔘",
                    chat_keypad=next_keyboard()
                )

                return

            return

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        if step == "title":

            if not text:
                return

            state["title"] = text
            state["step"] = "singer"

            await bot.send_message(
                chat_id=chat_id,
                text="🎤 نام خواننده:"
            )

            return

        # -------------------------------------------------
        # SINGER
        # -------------------------------------------------

        if step == "singer":

            if not text:
                return

            state["singer"] = text
            state["step"] = "cover"

            await bot.send_message(
                chat_id=chat_id,
                text="🖼",
                chat_keypad=next_keyboard()
            )

            return

        # -------------------------------------------------
        # COVER
        # -------------------------------------------------

        if step == "cover":

            if text == "بعدی":

                state["cover_path"] = None

            else:

                url = extract_url(
                    text
                )

                if not url:

                    await bot.send_message(
                        chat_id=chat_id,
                        text="❌"
                    )

                    return

                cover_path = os.path.join(
                    DOWNLOAD_DIR,
                    "cover_"
                    + safe_filename(chat_id)
                    + "_"
                    + str(int(time.time()))
                    + ".jpg"
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text="⏳"
                )

                success = download_cover(
                    url,
                    cover_path
                )

                if not success:

                    await bot.send_message(
                        chat_id=chat_id,
                        text="❌ دانلود کاور انجام نشد."
                    )

                    return

                state["cover_path"] = cover_path

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # -------------------------------------------------
        # GLASS BUTTON
        # -------------------------------------------------

        if step == "button_text":

            if text == "بعدی":

                state["button_text"] = None

            else:

                state["button_text"] = text

            # ---------------------------------------------
            # MUSIC
            # ---------------------------------------------

            if state.get(
                "media_type"
            ) == "music":

                await finish_music(
                    chat_id
                )

            # ---------------------------------------------
            # VOICE
            # ---------------------------------------------

            else:

                await finish_voice(
                    chat_id
                )

            return


# =========================================================
# RUN
# =========================================================

print(
    "======================================"
)

print(
    "🤖 RUBKA MUSIC + BANNER BOT"
)

print(
    "======================================"
)

print(
    "✅ String Chat ID mode"
)

print(
    "✅ Direct broadcast"
)

print(
    "✅ Download preview"
)

print(
    "✅ Glass display button"
)

print(
    "🚀 Bot is running..."
)

bot.run()
