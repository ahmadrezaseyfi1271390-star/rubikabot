import os
import re
import json
import uuid
import shutil
import requests
import gdown

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder, InlineBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC
from PIL import Image


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_FILE_SIZE = 200 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024

DOWNLOAD_FOLDER = "downloads"
USERS_FILE = "users.json"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================================================
# ربات
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# کاربران
# =========================================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register_user(chat_id):
    users = load_users()

    chat_id = str(chat_id)

    if chat_id not in users:
        users.append(chat_id)
        save_users(users)


# =========================================================
# کیبورد اصلی
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
# کیبورد انتخاب آهنگ / ویس
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
# کیبورد بعدی
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
# دکمه شیشه‌ای لینک
# =========================================================

def make_glass_button(button_text, button_url):

    if not button_text or not button_url:
        return None

    button_text = button_text.strip()
    button_url = button_url.strip()

    if not button_text or not button_url:
        return None

    builder = InlineBuilder()

    # مدل دکمه لینک‌دار
    builder.button_url_link(
        id="glass_button",
        text=button_text,
        url=button_url
    )

    return builder.build()


# =========================================================
# استخراج URL
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
# تشخیص Google Drive
# =========================================================

def is_google_drive(url):

    return (
        "drive.google.com" in url
        or "docs.google.com" in url
    )


# =========================================================
# دانلود فایل
# =========================================================

def download_file(url, output_path):

    try:

        # -------------------------------
        # Google Drive
        # -------------------------------

        if is_google_drive(url):

            gdown.download(
                url,
                output_path,
                quiet=False,
                fuzzy=True
            )

            if not os.path.exists(output_path):
                return False, "دانلود انجام نشد."

        # -------------------------------
        # لینک مستقیم
        # -------------------------------

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

            content_length = response.headers.get(
                "content-length"
            )

            if content_length:

                try:
                    size = int(content_length)

                    if size > MAX_FILE_SIZE:
                        return False, "حجم فایل بیشتر از ۲۰۰ مگابایت است."

                except Exception:
                    pass

            total = 0

            with open(output_path, "wb") as f:

                for chunk in response.iter_content(
                    chunk_size=1024 * 256
                ):

                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_FILE_SIZE:

                        f.close()

                        try:
                            os.remove(output_path)
                        except Exception:
                            pass

                        return False, "حجم فایل بیشتر از ۲۰۰ مگابایت است."

                    f.write(chunk)

        if not os.path.exists(output_path):
            return False, "فایل دانلود نشد."

        size = os.path.getsize(output_path)

        if size <= 0:
            return False, "فایل خالی است."

        if size > MAX_FILE_SIZE:
            return False, "حجم فایل بیشتر از ۲۰۰ مگابایت است."

        return True, output_path

    except Exception as e:

        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass

        return False, str(e)


# =========================================================
# دانلود کاور
# =========================================================

def download_cover_from_url(url):

    try:

        headers = {
            "User-Agent":
            "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=60
        )

        response.raise_for_status()

        data = response.content

        if len(data) > MAX_COVER_SIZE:
            return None

        temp_file = os.path.join(
            DOWNLOAD_FOLDER,
            f"cover_{uuid.uuid4().hex}.tmp"
        )

        with open(temp_file, "wb") as f:
            f.write(data)

        # بررسی واقعی تصویر
        image = Image.open(temp_file)

        image.load()

        image = image.convert("RGB")

        final_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"cover_{uuid.uuid4().hex}.jpg"
        )

        image.save(
            final_path,
            "JPEG",
            quality=95
        )

        image.close()

        try:
            os.remove(temp_file)
        except Exception:
            pass

        return final_path

    except Exception:

        return None


# =========================================================
# تنظیم متادیتای آهنگ
# =========================================================

def set_metadata(
    music_path,
    title,
    artist,
    cover_path=None
):

    try:

        try:
            tags = ID3(music_path)
        except Exception:
            tags = ID3()

        # حذف تگ‌های قبلی
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
            music_path,
            v2_version=3
        )

        return True

    except Exception as e:

        print(
            "Metadata Error:",
            e
        )

        return False


# =========================================================
# تغییر نام فایل آهنگ
# =========================================================

def rename_music_file(
    path,
    title
):

    if not title:
        return path

    # حذف کاراکترهای خطرناک
    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        '',
        title
    ).strip()

    if not safe_title:
        return path

    new_path = os.path.join(
        DOWNLOAD_FOLDER,
        safe_title + ".mp3"
    )

    # اگر فایل قبلی همان نام را دارد
    if os.path.abspath(new_path) != os.path.abspath(path):

        counter = 1
        original = new_path

        while os.path.exists(new_path):

            name, ext = os.path.splitext(
                original
            )

            new_path = (
                f"{name}_{counter}{ext}"
            )

            counter += 1

        try:
            os.rename(
                path,
                new_path
            )

            return new_path

        except Exception:
            pass

    return path


# =========================================================
# ارسال ویس
# =========================================================

async def send_voice(
    chat_id,
    path,
    caption,
    inline_keypad=None
):

    return await bot.send_voice(
        chat_id=chat_id,
        path=path,
        text=caption,
        inline_keypad=inline_keypad
    )


# =========================================================
# ارسال آهنگ
# =========================================================

async def send_music(
    chat_id,
    path,
    caption,
    inline_keypad=None
):

    return await bot.send_music(
        chat_id=chat_id,
        path=path,
        text=caption,
        inline_keypad=inline_keypad
    )


# =========================================================
# گرفتن Message ID
# =========================================================

def get_message_id(result):

    if result is None:
        return None

    # حالت آبجکت
    for attr in [
        "message_id",
        "id"
    ]:

        try:

            value = getattr(
                result,
                attr,
                None
            )

            if value:
                return value

        except Exception:
            pass

    # حالت دیکشنری
    if isinstance(result, dict):

        for key in [
            "message_id",
            "id"
        ]:

            if result.get(key):
                return result[key]

        # بعضی پاسخ‌ها
        # message را داخل result دارند

        message = result.get(
            "message"
        )

        if isinstance(message, dict):

            for key in [
                "message_id",
                "id"
            ]:

                if message.get(key):
                    return message[key]

    return None


# =========================================================
# Forward آهنگ / ویس
# =========================================================

async def forward_to_users(
    owner_chat_id,
    message_id
):

    if not message_id:
        print(
            "Message ID پیدا نشد."
        )
        return

    users = load_users()

    owner_chat_id = str(
        owner_chat_id
    )

    for user_id in users:

        user_id = str(user_id)

        # صاحب بات قبلاً پیام را گرفته
        if user_id == owner_chat_id:
            continue

        try:

            await bot.forward_message(
                from_chat_id=owner_chat_id,
                message_id=message_id,
                to_chat_id=user_id
            )

        except Exception as e:

            print(
                f"Forward Error {user_id}:",
                e
            )


# =========================================================
# ارسال مستقیم بنر به کاربران
# =========================================================

async def send_banner_to_users(
    image_path,
    caption,
    inline_keypad=None,
    owner_chat_id=None
):

    users = load_users()

    owner_chat_id = str(
        owner_chat_id
    ) if owner_chat_id else None

    for user_id in users:

        user_id = str(user_id)

        # سازنده قبلاً بنر را دریافت کرده
        if owner_chat_id and user_id == owner_chat_id:
            continue

        try:

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

        except Exception as e:

            print(
                f"Banner Send Error {user_id}:",
                e
            )


# =========================================================
# وضعیت کاربران
# =========================================================

user_states = {}


def get_state(chat_id):

    return user_states.get(
        str(chat_id),
        {}
    )


def set_state(
    chat_id,
    **kwargs
):

    user_states[str(chat_id)] = kwargs


def clear_state(chat_id):

    user_states.pop(
        str(chat_id),
        None
    )


# =========================================================
# START
# =========================================================

@bot.on_message()
async def handle_message(
    bot_instance,
    message: Message
):

    try:

        chat_id = str(
            message.chat_id
        )

        register_user(chat_id)

        text = (
            message.text or ""
        ).strip()

        # =============================================
        # START
        # =============================================

        if text == "/start":

            clear_state(chat_id)

            await bot.send_message(
                chat_id=chat_id,
                text="به ربات خوش آمدید.",
                chat_keypad=main_keyboard()
            )

            return

        # =============================================
        # منوی ساخت بنر
        # =============================================

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

        # =============================================
        # منوی ادیت آهنگ
        # =============================================

        if text == "🎵 ادیت آهنگ":

            set_state(
                chat_id,
                step="music_url"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🎵",
                chat_keypad=next_keyboard()
            )

            return

        state = get_state(chat_id)

        step = state.get(
            "step"
        )

        # =====================================================
        # ساخت بنر - URL
        # =====================================================

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

            url = extract_url(text)

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

            ok, result = download_file(
                url,
                image_path
            )

            if not ok:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            # تبدیل و بررسی تصویر
            try:

                image = Image.open(
                    image_path
                )

                image.load()

                image = image.convert(
                    "RGB"
                )

                converted = os.path.join(
                    DOWNLOAD_FOLDER,
                    f"banner_{uuid.uuid4().hex}.jpg"
                )

                image.save(
                    converted,
                    "JPEG",
                    quality=95
                )

                image.close()

                if converted != image_path:

                    try:
                        os.remove(
                            image_path
                        )
                    except Exception:
                        pass

                image_path = converted

            except Exception:

                try:
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

        # =====================================================
        # ساخت بنر - کپشن
        # =====================================================

        if step == "banner_caption":

            caption = (
                DEFAULT_CAPTION
                if text == "بعدی"
                else text
            )

            image_path = state.get(
                "image_path"
            )

            set_state(
                chat_id,
                step="banner_button_text",
                image_path=image_path,
                caption=caption
            )

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # =====================================================
        # ساخت بنر - متن دکمه
        # =====================================================

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
                    button_text=None
                )

                # مستقیم ساخت
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

        # =====================================================
        # ساخت بنر - لینک دکمه
        # =====================================================

        if step == "banner_button_url":

            button_url = None

            if text != "بعدی":
                button_url = extract_url(text)

            button_text = state.get(
                "button_text"
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
                button_text=button_text,
                button_url=button_url
            )

            await finish_banner(
                chat_id
            )

            return

        # =====================================================
        # آهنگ - URL
        # =====================================================

        if step == "music_url":

            if text == "بعدی":

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            url = extract_url(text)

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

            ok, result = download_file(
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

        # =====================================================
        # آهنگ - کپشن
        # =====================================================

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
                text="نوع خروجی را انتخاب کن:",
                chat_keypad=type_keyboard()
            )

            return

        # =====================================================
        # انتخاب نوع
        # =====================================================

        if step == "music_type":

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

        # =====================================================
        # نام آهنگ
        # =====================================================

        if step == "music_title":

            if text == "بعدی":
                title = "Unknown"
            else:
                title = text

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

        # =====================================================
        # خواننده
        # =====================================================

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

        # =====================================================
        # کاور
        # =====================================================

        if step == "music_cover":

            cover_path = None

            if text != "بعدی":

                cover_url = extract_url(
                    text
                )

                if cover_url:

                    cover_path = (
                        download_cover_from_url(
                            cover_url
                        )
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

        # =====================================================
        # دکمه آهنگ
        # =====================================================

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

        # =====================================================
        # لینک دکمه آهنگ
        # =====================================================

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

        # =====================================================
        # دکمه ویس
        # =====================================================

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

        # =====================================================
        # لینک ویس
        # =====================================================

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
            "BOT ERROR:",
            repr(e)
        )

        try:

            await bot.send_message(
                chat_id=message.chat_id,
                text="❌ خطایی رخ داد."
            )

        except Exception:
            pass


# =========================================================
# پایان ساخت بنر
# =========================================================

async def finish_banner(chat_id):

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

    inline_keypad = None

    if button_text and button_url:

        inline_keypad = make_glass_button(
            button_text,
            button_url
        )

    try:

        # =============================================
        # اول برای سازنده
        # =============================================

        if image_path and os.path.exists(
            image_path
        ):

            result = await bot.send_image(
                chat_id=chat_id,
                path=image_path,
                text=caption,
                inline_keypad=inline_keypad
            )

        else:

            result = await bot.send_message(
                chat_id=chat_id,
                text=caption,
                inline_keypad=inline_keypad
            )

        # =============================================
        # سپس ارسال مستقیم برای کاربران
        # =============================================

        await send_banner_to_users(
            image_path=image_path,
            caption=caption,
            inline_keypad=inline_keypad,
            owner_chat_id=chat_id
        )

        # =============================================
        # حذف فایل
        # =============================================

        if image_path and os.path.exists(
            image_path
        ):

            try:
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
            "BANNER ERROR:",
            repr(e)
        )

        if image_path and os.path.exists(
            image_path
        ):

            try:
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
# پایان آهنگ
# =========================================================

async def finish_music(chat_id):

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

    inline_keypad = None

    if button_text and button_url:

        inline_keypad = make_glass_button(
            button_text,
            button_url
        )

    try:

        if not music_path or not os.path.exists(
            music_path
        ):

            raise Exception(
                "Music file not found"
            )

        # متادیتا
        set_metadata(
            music_path,
            title,
            artist,
            cover_path
        )

        # تغییر نام
        music_path = rename_music_file(
            music_path,
            title
        )

        # =============================================
        # ارسال برای سازنده
        # =============================================

        result = await send_music(
            chat_id=chat_id,
            path=music_path,
            caption=caption,
            inline_keypad=inline_keypad
        )

        message_id = get_message_id(
            result
        )

        print(
            "Music Message ID:",
            message_id
        )

        # =============================================
        # Forward برای کاربران
        # =============================================

        await forward_to_users(
            owner_chat_id=chat_id,
            message_id=message_id
        )

        # =============================================
        # حذف فایل‌ها
        # =============================================

        if os.path.exists(
            music_path
        ):

            try:
                os.remove(
                    music_path
                )
            except Exception:
                pass

        if cover_path and os.path.exists(
            cover_path
        ):

            try:
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
            "MUSIC ERROR:",
            repr(e)
        )

        if music_path and os.path.exists(
            music_path
        ):

            try:
                os.remove(
                    music_path
                )
            except Exception:
                pass

        if cover_path and os.path.exists(
            cover_path
        ):

            try:
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
# پایان ویس
# =========================================================

async def finish_voice(chat_id):

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

    inline_keypad = None

    if button_text and button_url:

        inline_keypad = make_glass_button(
            button_text,
            button_url
        )

    try:

        if not music_path or not os.path.exists(
            music_path
        ):

            raise Exception(
                "Voice file not found"
            )

        # =============================================
        # ارسال برای سازنده
        # =============================================

        result = await send_voice(
            chat_id=chat_id,
            path=music_path,
            caption=caption,
            inline_keypad=inline_keypad
        )

        message_id = get_message_id(
            result
        )

        print(
            "Voice Message ID:",
            message_id
        )

        # =============================================
        # Forward برای کاربران
        # =============================================

        await forward_to_users(
            owner_chat_id=chat_id,
            message_id=message_id
        )

        # =============================================
        # حذف
        # =============================================

        if os.path.exists(
            music_path
        ):

            try:
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
            "VOICE ERROR:",
            repr(e)
        )

        if music_path and os.path.exists(
            music_path
        ):

            try:
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
# اجرای ربات
# =========================================================

if __name__ == "__main__":

    print("===================================")
    print("Bot Started")
    print("Rubka 8.1.10")
    print("===================================")

    bot.run()
