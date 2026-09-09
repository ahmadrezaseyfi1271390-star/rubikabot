import os
import re
import json
import uuid
import time
import requests
import gdown

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder, InlineBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC
from PIL import Image


# =========================================================
# CONFIG
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_FILE_SIZE = 200 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024

DOWNLOAD_FOLDER = "downloads"
USERS_FILE = "users.json"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================================================
# BOT
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# USERS
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

        # سازگاری با users.json قدیمی
        if isinstance(data, list):

            result = {}

            for user_id in data:
                result[str(user_id)] = {
                    "messages": 0,
                    "last_message": 0
                }

            return result

        if isinstance(data, dict):
            return data

    except Exception as e:

        print(
            "USERS LOAD ERROR:",
            e
        )

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

        print(
            "USERS SAVE ERROR:",
            e
        )


def register_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users[chat_id] = {
            "messages": 0,
            "last_message": time.time()
        }

        save_users(users)


def count_user_message(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users[chat_id] = {
            "messages": 0,
            "last_message": time.time()
        }

    users[chat_id]["messages"] = (
        int(users[chat_id].get("messages", 0)) + 1
    )

    users[chat_id]["last_message"] = time.time()

    save_users(users)


# =========================================================
# USER ORDER
# =========================================================

def get_users_by_activity(owner_id=None):

    users = load_users()

    owner_id = (
        str(owner_id)
        if owner_id is not None
        else None
    )

    result = []

    for user_id, data in users.items():

        if owner_id and str(user_id) == owner_id:
            continue

        try:
            messages = int(
                data.get("messages", 0)
            )
        except Exception:
            messages = 0

        try:
            last_message = float(
                data.get("last_message", 0)
            )
        except Exception:
            last_message = 0

        result.append(
            (
                str(user_id),
                messages,
                last_message
            )
        )

    # اول بیشترین تعداد پیام
    # اگر مساوی بود، آخرین فعالیت جدیدتر اول
    result.sort(
        key=lambda x: (
            -x[1],
            -x[2]
        )
    )

    return [
        x[0]
        for x in result
    ]


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="banner",
            text="🖼 ساخت بنر"
        ),
        builder.button(
            id="music_edit",
            text="🎵 ادیت آهنگ"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


# =========================================================
# TYPE KEYBOARD
# =========================================================

def type_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="music",
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
# NEXT KEYBOARD
# =========================================================

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


# =========================================================
# GLASS BUTTON
# =========================================================

def make_glass_button(
    button_text,
    button_url
):

    if not button_text:
        return None

    if not button_url:
        return None

    button_text = str(
        button_text
    ).strip()

    button_url = str(
        button_url
    ).strip()

    if not button_text:
        return None

    if not button_url:
        return None

    builder = InlineBuilder()

    # مدل لینک‌دار شیشه‌ای
    builder.button_url_link(
        id="glass_button",
        text=button_text,
        url=button_url
    )

    return builder.build()


# =========================================================
# URL
# =========================================================

def extract_url(text):

    if not text:
        return None

    match = re.search(
        r'https?://[^\s]+',
        text.strip()
    )

    if match:
        return match.group(0)

    return None


# =========================================================
# GOOGLE DRIVE
# =========================================================

def is_google_drive(url):

    return (
        "drive.google.com" in url
        or "docs.google.com" in url
    )


# =========================================================
# DOWNLOAD
# =========================================================

def download_file(
    url,
    output_path
):

    try:

        # -----------------------------------------
        # Google Drive
        # -----------------------------------------

        if is_google_drive(url):

            result = gdown.download(
                url,
                output_path,
                quiet=False,
                fuzzy=True
            )

            if not result:
                return False

        # -----------------------------------------
        # Direct URL
        # -----------------------------------------

        else:

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

            content_length = (
                response.headers.get(
                    "content-length"
                )
            )

            if content_length:

                try:

                    if int(content_length) > MAX_FILE_SIZE:

                        return False

                except Exception:
                    pass

            total = 0

            with open(
                output_path,
                "wb"
            ) as f:

                for chunk in response.iter_content(
                    chunk_size=256 * 1024
                ):

                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_FILE_SIZE:

                        return False

                    f.write(chunk)

        if not os.path.exists(
            output_path
        ):
            return False

        if os.path.getsize(
            output_path
        ) <= 0:
            return False

        if os.path.getsize(
            output_path
        ) > MAX_FILE_SIZE:
            return False

        return True

    except Exception as e:

        print(
            "DOWNLOAD ERROR:",
            e
        )

        try:

            if os.path.exists(
                output_path
            ):
                os.remove(
                    output_path
                )

        except Exception:
            pass

        return False


# =========================================================
# COVER
# =========================================================

def download_cover(
    url
):

    temp_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"cover_temp_{uuid.uuid4().hex}"
    )

    final_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"cover_{uuid.uuid4().hex}.jpg"
    )

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            },
            timeout=60
        )

        response.raise_for_status()

        if len(response.content) > MAX_COVER_SIZE:
            return None

        with open(
            temp_path,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        image = Image.open(
            temp_path
        )

        image.load()

        image = image.convert(
            "RGB"
        )

        image.save(
            final_path,
            "JPEG",
            quality=95
        )

        image.close()

        try:
            os.remove(
                temp_path
            )
        except Exception:
            pass

        return final_path

    except Exception as e:

        print(
            "COVER ERROR:",
            e
        )

        try:
            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )
        except Exception:
            pass

        try:
            if os.path.exists(
                final_path
            ):
                os.remove(
                    final_path
                )
        except Exception:
            pass

        return None


# =========================================================
# MP3 METADATA
# =========================================================

def set_metadata(
    music_path,
    title,
    artist,
    cover_path=None
):

    try:

        try:
            tags = ID3(
                music_path
            )
        except Exception:
            tags = ID3()

        try:
            tags.delall("TIT2")
            tags.delall("TPE1")
            tags.delall("APIC")
        except Exception:
            pass

        if title:

            tags.add(
                TIT2(
                    encoding=3,
                    text=title
                )
            )

        if artist:

            tags.add(
                TPE1(
                    encoding=3,
                    text=artist
                )
            )

        if cover_path and os.path.exists(
            cover_path
        ):

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
            music_path,
            v2_version=3
        )

        return True

    except Exception as e:

        print(
            "TAG ERROR:",
            e
        )

        return False


# =========================================================
# RENAME
# =========================================================

def rename_music(
    path,
    title
):

    if not title:
        return path

    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        "",
        str(title)
    ).strip()

    if not safe_title:
        return path

    new_path = os.path.join(
        DOWNLOAD_FOLDER,
        safe_title + ".mp3"
    )

    original = new_path
    counter = 1

    while (
        os.path.exists(new_path)
        and os.path.abspath(new_path)
        != os.path.abspath(path)
    ):

        name, ext = os.path.splitext(
            original
        )

        new_path = (
            f"{name}_{counter}{ext}"
        )

        counter += 1

    try:

        if os.path.abspath(
            new_path
        ) != os.path.abspath(
            path
        ):

            os.rename(
                path,
                new_path
            )

            return new_path

    except Exception as e:

        print(
            "RENAME ERROR:",
            e
        )

    return path


# =========================================================
# STATE
# =========================================================

user_states = {}


def get_state(
    chat_id
):

    return user_states.get(
        str(chat_id),
        {}
    )


def set_state(
    chat_id,
    **data
):

    user_states[
        str(chat_id)
    ] = data


def clear_state(
    chat_id
):

    user_states.pop(
        str(chat_id),
        None
    )


# =========================================================
# SEND MUSIC DIRECTLY TO EVERY USER
# =========================================================

async def broadcast_music(
    path,
    caption,
    inline_keypad,
    owner_id
):

    users = get_users_by_activity(
        owner_id
    )

    print(
        "MUSIC USERS ORDER:",
        users
    )

    for user_id in users:

        try:

            print(
                "Sending music to:",
                user_id
            )

            await bot.send_music(
                chat_id=user_id,
                path=path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Music sent:",
                user_id
            )

        except Exception as e:

            print(
                "MUSIC SEND ERROR",
                user_id,
                e
            )

        # یکی‌یکی
        await sleep_small()


# =========================================================
# SEND VOICE DIRECTLY TO EVERY USER
# =========================================================

async def broadcast_voice(
    path,
    caption,
    inline_keypad,
    owner_id
):

    users = get_users_by_activity(
        owner_id
    )

    print(
        "VOICE USERS ORDER:",
        users
    )

    for user_id in users:

        try:

            print(
                "Sending voice to:",
                user_id
            )

            await bot.send_voice(
                chat_id=user_id,
                path=path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Voice sent:",
                user_id
            )

        except Exception as e:

            print(
                "VOICE SEND ERROR",
                user_id,
                e
            )

        await sleep_small()


# =========================================================
# SEND BANNER DIRECTLY TO EVERY USER
# =========================================================

async def broadcast_banner(
    image_path,
    caption,
    inline_keypad,
    owner_id
):

    users = get_users_by_activity(
        owner_id
    )

    print(
        "BANNER USERS ORDER:",
        users
    )

    for user_id in users:

        try:

            print(
                "Sending banner to:",
                user_id
            )

            if image_path:

                await bot.send_image(
                    chat_id=user_id,
                    path=image_path,
                    text=caption,
                    inline_keypad=inline_keypad
                )

            else:

                await bot.send_message(
                    chat_id=user_id,
                    text=caption,
                    inline_keypad=inline_keypad
                )

            print(
                "Banner sent:",
                user_id
            )

        except Exception as e:

            print(
                "BANNER SEND ERROR",
                user_id,
                e
            )

        await sleep_small()


# =========================================================
# SMALL DELAY
# =========================================================

async def sleep_small():

    # بدون نیاز به کتابخانه اضافی
    import asyncio

    await asyncio.sleep(
        0.3
    )


# =========================================================
# FINISH BANNER
# =========================================================

async def finish_banner(
    chat_id
):

    state = get_state(
        chat_id
    )

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

    button_url = state.get(
        "button_url"
    )

    inline_keypad = make_glass_button(
        button_text,
        button_url
    )

    try:

        # -----------------------------------------
        # اول برای سازنده
        # -----------------------------------------

        if image_path and os.path.exists(
            image_path
        ):

            await bot.send_image(
                chat_id=chat_id,
                path=image_path,
                text=caption,
                inline_keypad=inline_keypad
            )

        else:

            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                inline_keypad=inline_keypad
            )

        # -----------------------------------------
        # بعد برای کاربران
        # -----------------------------------------

        await broadcast_banner(
            image_path=image_path,
            caption=caption,
            inline_keypad=inline_keypad,
            owner_id=chat_id
        )

        # -----------------------------------------
        # پاک کردن فایل
        # -----------------------------------------

        if image_path:

            try:

                if os.path.exists(
                    image_path
                ):
                    os.remove(
                        image_path
                    )

            except Exception:
                pass

        clear_state(
            chat_id
        )

        await bot.send_message(
            chat_id=chat_id,
            text="✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "FINISH BANNER ERROR:",
            e
        )

        try:

            if image_path and os.path.exists(
                image_path
            ):
                os.remove(
                    image_path
                )

        except Exception:
            pass

        clear_state(
            chat_id
        )

        await bot.send_message(
            chat_id=chat_id,
            text="❌",
            chat_keypad=main_keyboard()
        )


# =========================================================
# FINISH MUSIC
# =========================================================

async def finish_music(
    chat_id
):

    state = get_state(
        chat_id
    )

    music_path = state.get(
        "music_path"
    )

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    title = state.get(
        "title",
        "Unknown"
    )

    artist = state.get(
        "artist",
        "Unknown"
    )

    cover_path = state.get(
        "cover_path"
    )

    button_text = state.get(
        "button_text"
    )

    button_url = state.get(
        "button_url"
    )

    inline_keypad = make_glass_button(
        button_text,
        button_url
    )

    try:

        if not music_path:
            raise Exception(
                "Music path missing"
            )

        if not os.path.exists(
            music_path
        ):
            raise Exception(
                "Music file missing"
            )

        # -----------------------------------------
        # metadata
        # -----------------------------------------

        set_metadata(
            music_path,
            title,
            artist,
            cover_path
        )

        # -----------------------------------------
        # rename
        # -----------------------------------------

        music_path = rename_music(
            music_path,
            title
        )

        # -----------------------------------------
        # اول سازنده
        # -----------------------------------------

        await bot.send_music(
            chat_id=chat_id,
            path=music_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        # -----------------------------------------
        # سپس همه کاربران
        # مستقیم، بدون Forward
        # -----------------------------------------

        await broadcast_music(
            path=music_path,
            caption=caption,
            inline_keypad=inline_keypad,
            owner_id=chat_id
        )

        # -----------------------------------------
        # حذف
        # -----------------------------------------

        try:

            if os.path.exists(
                music_path
            ):
                os.remove(
                    music_path
                )

        except Exception:
            pass

        if cover_path:

            try:

                if os.path.exists(
                    cover_path
                ):
                    os.remove(
                        cover_path
                    )

            except Exception:
                pass

        clear_state(
            chat_id
        )

        await bot.send_message(
            chat_id=chat_id,
            text="✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "FINISH MUSIC ERROR:",
            e
        )

        try:

            if music_path and os.path.exists(
                music_path
            ):
                os.remove(
                    music_path
                )

        except Exception:
            pass

        try:

            if cover_path and os.path.exists(
                cover_path
            ):
                os.remove(
                    cover_path
                )

        except Exception:
            pass

        clear_state(
            chat_id
        )

        await bot.send_message(
            chat_id=chat_id,
            text="❌",
            chat_keypad=main_keyboard()
        )


# =========================================================
# FINISH VOICE
# =========================================================

async def finish_voice(
    chat_id
):

    state = get_state(
        chat_id
    )

    music_path = state.get(
        "music_path"
    )

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    button_text = state.get(
        "button_text"
    )

    button_url = state.get(
        "button_url"
    )

    inline_keypad = make_glass_button(
        button_text,
        button_url
    )

    try:

        if not music_path:
            raise Exception(
                "Voice path missing"
            )

        if not os.path.exists(
            music_path
        ):
            raise Exception(
                "Voice file missing"
            )

        # -----------------------------------------
        # اول سازنده
        # -----------------------------------------

        await bot.send_voice(
            chat_id=chat_id,
            path=music_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        # -----------------------------------------
        # سپس کاربران
        # مستقیم
        # -----------------------------------------

        await broadcast_voice(
            path=music_path,
            caption=caption,
            inline_keypad=inline_keypad,
            owner_id=chat_id
        )

        # -----------------------------------------
        # حذف
        # -----------------------------------------

        try:

            if os.path.exists(
                music_path
            ):
                os.remove(
                    music_path
                )

        except Exception:
            pass

        clear_state(
            chat_id
        )

        await bot.send_message(
            chat_id=chat_id,
            text="✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "FINISH VOICE ERROR:",
            e
        )

        try:

            if music_path and os.path.exists(
                music_path
            ):
                os.remove(
                    music_path
                )

        except Exception:
            pass

        clear_state(
            chat_id
        )

        await bot.send_message(
            chat_id=chat_id,
            text="❌",
            chat_keypad=main_keyboard()
        )


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.on_message()
async def handle_message(
    bot_instance,
    message: Message
):

    chat_id = str(
        message.chat_id
    )

    try:

        register_user(
            chat_id
        )

        text = (
            message.text or ""
        ).strip()

        # هر پیام کاربر
        # برای سیستم اولویت ارسال ثبت می‌شود
        count_user_message(
            chat_id
        )

        # =================================================
        # START
        # =================================================

        if text == "/start":

            clear_state(
                chat_id
            )

            await bot.send_message(
                chat_id=chat_id,
                text="به ربات خوش آمدید.",
                chat_keypad=main_keyboard()
            )

            return

        # =================================================
        # MAIN MENU
        # =================================================

        if text == "🖼 ساخت بنر":

            set_state(
                chat_id,
                step="banner_url"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🖼",
                chat_keypad=next_keyboard()
            )

            return

        if text == "🎵 ادیت آهنگ":

            set_state(
                chat_id,
                step="music_url"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🎵"
            )

            return

        state = get_state(
            chat_id
        )

        step = state.get(
            "step"
        )

        # =================================================
        # BANNER URL
        # =================================================

        if step == "banner_url":

            if text == "بعدی":

                set_state(
                    chat_id,
                    step="banner_caption",
                    image_path=None
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text="✏️"
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
                DOWNLOAD_FOLDER,
                f"banner_{uuid.uuid4().hex}.jpg"
            )

            ok = download_file(
                url,
                image_path
            )

            if not ok:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            # بررسی تصویر
            try:

                image = Image.open(
                    image_path
                )

                image.load()

                image = image.convert(
                    "RGB"
                )

                new_path = os.path.join(
                    DOWNLOAD_FOLDER,
                    f"banner_{uuid.uuid4().hex}.jpg"
                )

                image.save(
                    new_path,
                    "JPEG",
                    quality=95
                )

                image.close()

                try:
                    os.remove(
                        image_path
                    )
                except Exception:
                    pass

                image_path = new_path

            except Exception:

                try:

                    if os.path.exists(
                        image_path
                    ):
                        os.remove(
                            image_path
                        )

                except Exception:
                    pass

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            set_state(
                chat_id,
                step="banner_caption",
                image_path=image_path
            )

            await bot.send_message(
                chat_id=chat_id,
                text="✏️"
            )

            return

        # =================================================
        # BANNER CAPTION
        # =================================================

        if step == "banner_caption":

            caption = (
                DEFAULT_CAPTION
                if text == "بعدی"
                else text
            )

            set_state(
                chat_id,
                step="banner_button_text",
                image_path=state.get(
                    "image_path"
                ),
                caption=caption
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # BANNER BUTTON TEXT
        # =================================================

        if step == "banner_button_text":

            if text == "بعدی":

                set_state(
                    chat_id,
                    step="banner_finish",
                    image_path=state.get(
                        "image_path"
                    ),
                    caption=state.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    button_text=None,
                    button_url=None
                )

                await finish_banner(
                    chat_id
                )

                return

            set_state(
                chat_id,
                step="banner_button_url",
                image_path=state.get(
                    "image_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                button_text=text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🔗",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # BANNER BUTTON URL
        # =================================================

        if step == "banner_button_url":

            button_url = None

            if text != "بعدی":

                button_url = extract_url(
                    text
                )

            set_state(
                chat_id,
                step="banner_finish",
                image_path=state.get(
                    "image_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                button_text=state.get(
                    "button_text"
                ),
                button_url=button_url
            )

            await finish_banner(
                chat_id
            )

            return

        # =================================================
        # MUSIC URL
        # =================================================

        if step == "music_url":

            url = extract_url(
                text
            )

            if not url:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            music_path = os.path.join(
                DOWNLOAD_FOLDER,
                f"music_{uuid.uuid4().hex}.mp3"
            )

            ok = download_file(
                url,
                music_path
            )

            if not ok:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            set_state(
                chat_id,
                step="music_caption",
                music_path=music_path
            )

            await bot.send_message(
                chat_id=chat_id,
                text="✏️"
            )

            return

        # =================================================
        # MUSIC CAPTION
        # =================================================

        if step == "music_caption":

            caption = (
                DEFAULT_CAPTION
                if text == "بعدی"
                else text
            )

            set_state(
                chat_id,
                step="music_type",
                music_path=state.get(
                    "music_path"
                ),
                caption=caption
            )

            await bot.send_message(
                chat_id=chat_id,
                text="نوع خروجی:",
                chat_keypad=type_keyboard()
            )

            return

        # =================================================
        # TYPE
        # =================================================

        if step == "music_type":

            if text == "🎵 آهنگ":

                set_state(
                    chat_id,
                    step="music_title",
                    music_path=state.get(
                        "music_path"
                    ),
                    caption=state.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    output_type="music"
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text="🎵"
                )

                return

            if text == "🎤 ویس":

                set_state(
                    chat_id,
                    step="voice_button_text",
                    music_path=state.get(
                        "music_path"
                    ),
                    caption=state.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    output_type="voice"
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text="🔘",
                    chat_keypad=next_keyboard()
                )

                return

        # =================================================
        # MUSIC TITLE
        # =================================================

        if step == "music_title":

            title = (
                "Unknown"
                if text == "بعدی"
                else text
            )

            set_state(
                chat_id,
                step="music_artist",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="music",
                title=title
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🎤"
            )

            return

        # =================================================
        # MUSIC ARTIST
        # =================================================

        if step == "music_artist":

            artist = (
                "Unknown"
                if text == "بعدی"
                else text
            )

            set_state(
                chat_id,
                step="music_cover",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="music",
                title=state.get(
                    "title",
                    "Unknown"
                ),
                artist=artist
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🖼",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # MUSIC COVER
        # =================================================

        if step == "music_cover":

            cover_path = None

            if text != "بعدی":

                cover_url = extract_url(
                    text
                )

                if cover_url:

                    cover_path = download_cover(
                        cover_url
                    )

            set_state(
                chat_id,
                step="music_button_text",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="music",
                title=state.get(
                    "title",
                    "Unknown"
                ),
                artist=state.get(
                    "artist",
                    "Unknown"
                ),
                cover_path=cover_path
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # MUSIC BUTTON TEXT
        # =================================================

        if step == "music_button_text":

            if text == "بعدی":

                set_state(
                    chat_id,
                    step="music_finish",
                    music_path=state.get(
                        "music_path"
                    ),
                    caption=state.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    output_type="music",
                    title=state.get(
                        "title",
                        "Unknown"
                    ),
                    artist=state.get(
                        "artist",
                        "Unknown"
                    ),
                    cover_path=state.get(
                        "cover_path"
                    ),
                    button_text=None,
                    button_url=None
                )

                await finish_music(
                    chat_id
                )

                return

            set_state(
                chat_id,
                step="music_button_url",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="music",
                title=state.get(
                    "title",
                    "Unknown"
                ),
                artist=state.get(
                    "artist",
                    "Unknown"
                ),
                cover_path=state.get(
                    "cover_path"
                ),
                button_text=text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🔗",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # MUSIC BUTTON URL
        # =================================================

        if step == "music_button_url":

            button_url = None

            if text != "بعدی":

                button_url = extract_url(
                    text
                )

            set_state(
                chat_id,
                step="music_finish",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="music",
                title=state.get(
                    "title",
                    "Unknown"
                ),
                artist=state.get(
                    "artist",
                    "Unknown"
                ),
                cover_path=state.get(
                    "cover_path"
                ),
                button_text=state.get(
                    "button_text"
                ),
                button_url=button_url
            )

            await finish_music(
                chat_id
            )

            return

        # =================================================
        # VOICE BUTTON TEXT
        # =================================================

        if step == "voice_button_text":

            if text == "بعدی":

                set_state(
                    chat_id,
                    step="voice_finish",
                    music_path=state.get(
                        "music_path"
                    ),
                    caption=state.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    output_type="voice",
                    button_text=None,
                    button_url=None
                )

                await finish_voice(
                    chat_id
                )

                return

            set_state(
                chat_id,
                step="voice_button_url",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="voice",
                button_text=text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🔗",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # VOICE BUTTON URL
        # =================================================

        if step == "voice_button_url":

            button_url = None

            if text != "بعدی":

                button_url = extract_url(
                    text
                )

            set_state(
                chat_id,
                step="voice_finish",
                music_path=state.get(
                    "music_path"
                ),
                caption=state.get(
                    "caption",
                    DEFAULT_CAPTION
                ),
                output_type="voice",
                button_text=state.get(
                    "button_text"
                ),
                button_url=button_url
            )

            await finish_voice(
                chat_id
            )

            return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )

        try:

            await bot.send_message(
                chat_id=chat_id,
                text="❌ خطایی رخ داد."
            )

        except Exception:
            pass


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "Rubka Bot Started"
    )

    print(
        "Rubka 8.1.10"
    )

    print(
        "Direct Broadcast Mode"
    )

    print(
        "================================"
    )

    bot.run()
