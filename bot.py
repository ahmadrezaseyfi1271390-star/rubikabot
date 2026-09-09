import os
import re
import json
import uuid
import requests
import gdown

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder, InlineBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC


# =========================================================
# SETTINGS
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# آیدی عددی/شناسه چت سازنده
OWNER_ID = "b0FXnfh0BD5202f5617bb7eea6e39f2d"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_FILE_SIZE = 200 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024

DOWNLOAD_FOLDER = "downloads"
USERS_FILE = "users.json"


# =========================================================
# BOT
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# FOLDERS
# =========================================================

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# USER DATA
# =========================================================

user_data = {}


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

        # نسخه قدیمی که لیست بوده
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
            repr(e)
        )

    return {}


def save_users(users):

    clean = {}

    for user_id, info in users.items():

        clean[str(user_id)] = {
            "messages": int(
                info.get("messages", 0)
            ),
            "last_message": int(
                info.get("last_message", 0)
            )
        }

    with open(
        USERS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            clean,
            f,
            ensure_ascii=False,
            indent=2
        )


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

    users[chat_id]["messages"] = (
        int(users[chat_id].get("messages", 0))
        + 1
    )

    users[chat_id]["last_message"] = int(
        __import__("time").time()
    )

    save_users(users)


def get_users_by_activity():

    users = load_users()

    items = []

    for user_id, info in users.items():

        if str(user_id) == str(OWNER_ID):
            continue

        items.append(
            (
                str(user_id),
                int(info.get("messages", 0)),
                int(info.get("last_message", 0))
            )
        )

    # بیشترین پیام اول
    # در صورت مساوی بودن، جدیدترین پیام اول
    items.sort(
        key=lambda x: (
            x[1],
            x[2]
        ),
        reverse=True
    )

    return [
        x[0]
        for x in items
    ]


# =========================================================
# AWAIT HELPER
# =========================================================

async def maybe_await(result):

    if hasattr(result, "__await__"):
        return await result

    return result


# =========================================================
# SEND TEXT
# =========================================================

async def send_text(
    chat_id,
    text,
    chat_keypad=None,
    inline_keypad=None
):

    result = bot.send_message(
        chat_id=str(chat_id),
        text=text,
        chat_keypad=chat_keypad,
        inline_keypad=inline_keypad
    )

    return await maybe_await(result)


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="make_banner",
            text="🖼 ساخت بنر"
        ),
        builder.button(
            id="edit_music",
            text="🎵 ادیت آهنگ"
        )
    )

    return builder.build(
        resize_keyboard=True,
        on_time_keyboard=False
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
        resize_keyboard=True,
        on_time_keyboard=False
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
        resize_keyboard=True,
        on_time_keyboard=False
    )


# =========================================================
# GLASS BUTTON
# DISPLAY ONLY / NO URL
# =========================================================

def glass_button(text):

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
        r'https?://[^\s]+',
        text
    )

    if match:

        return match.group(0).strip()

    return None


# =========================================================
# DOWNLOAD AUDIO
# =========================================================

def download_file(url):

    os.makedirs(
        DOWNLOAD_FOLDER,
        exist_ok=True
    )

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"audio_{uuid.uuid4().hex}.mp3"
    )

    print(
        "AUDIO URL:",
        url
    )

    # Google Drive
    if "drive.google.com" in url:

        try:

            gdown.download(
                url,
                output_path,
                quiet=False
            )

        except Exception as e:

            print(
                "GDRIVE ERROR:",
                repr(e)
            )

            raise Exception(
                "دانلود از Google Drive انجام نشد."
            )

    # Direct URL
    else:

        try:

            response = requests.get(
                url,
                stream=True,
                timeout=60,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            response.raise_for_status()

            total_size = 0

            with open(
                output_path,
                "wb"
            ) as f:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if not chunk:
                        continue

                    total_size += len(chunk)

                    if total_size > MAX_FILE_SIZE:

                        raise Exception(
                            "حجم فایل بیشتر از 200MB است."
                        )

                    f.write(chunk)

        except Exception:

            if os.path.exists(output_path):

                try:
                    os.remove(output_path)
                except:
                    pass

            raise

    if not os.path.exists(output_path):

        raise Exception(
            "فایل دانلود نشد."
        )

    size = os.path.getsize(
        output_path
    )

    if size > MAX_FILE_SIZE:

        try:
            os.remove(output_path)
        except:
            pass

        raise Exception(
            "حجم فایل بیشتر از 200MB است."
        )

    return output_path


# =========================================================
# DOWNLOAD COVER
# =========================================================

async def download_cover_from_url(url):

    jpg_path = None

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        data = response.content

        if len(data) > MAX_COVER_SIZE:

            return None

        from PIL import Image
        from io import BytesIO

        try:

            image = Image.open(
                BytesIO(data)
            )

            image.load()

        except Exception:

            return None

        jpg_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"cover_{uuid.uuid4().hex}.jpg"
        )

        image = image.convert(
            "RGB"
        )

        image.save(
            jpg_path,
            "JPEG",
            quality=95
        )

        image.close()

        return jpg_path

    except Exception as e:

        print(
            "COVER ERROR:",
            repr(e)
        )

        if (
            jpg_path
            and os.path.exists(jpg_path)
        ):

            try:
                os.remove(jpg_path)
            except:
                pass

        return None


# =========================================================
# DOWNLOAD BANNER
# =========================================================

def download_banner(url):

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"banner_{uuid.uuid4().hex}.jpg"
    )

    try:

        response = requests.get(
            url,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        data = response.content

        if len(data) > MAX_COVER_SIZE:

            raise Exception(
                "حجم تصویر بیشتر از 10MB است."
            )

        from PIL import Image
        from io import BytesIO

        image = Image.open(
            BytesIO(data)
        )

        image.load()

        image = image.convert(
            "RGB"
        )

        image.save(
            output_path,
            "JPEG",
            quality=95
        )

        image.close()

        return output_path

    except Exception:

        if os.path.exists(output_path):

            try:
                os.remove(output_path)
            except:
                pass

        raise


# =========================================================
# MP3 METADATA
# =========================================================

def set_metadata(
    file_path,
    title,
    artist,
    cover_path
):

    try:

        try:

            tags = ID3(
                file_path
            )

        except:

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

        if (
            cover_path
            and os.path.exists(cover_path)
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
            file_path
        )

    except Exception as e:

        print(
            "METADATA ERROR:",
            repr(e)
        )

        raise


# =========================================================
# RENAME MP3
# =========================================================

def rename_file(
    file_path,
    title
):

    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        title
    )

    safe_title = safe_title.strip()

    if not safe_title:
        safe_title = "music"

    new_path = os.path.join(
        DOWNLOAD_FOLDER,
        safe_title + ".mp3"
    )

    counter = 1

    while os.path.exists(new_path):

        new_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"{safe_title}_{counter}.mp3"
        )

        counter += 1

    os.rename(
        file_path,
        new_path
    )

    return new_path


# =========================================================
# SEND MUSIC DIRECTLY
# =========================================================

async def direct_send_music(
    chat_id,
    file_path,
    caption,
    inline_keypad=None
):

    try:

        result = bot.send_music(
            chat_id=str(chat_id),
            path=file_path,
            text=caption,
            file_name=os.path.basename(
                file_path
            ),
            inline_keypad=inline_keypad
        )

        return await maybe_await(result)

    except Exception as e:

        print(
            "SEND MUSIC ERROR:",
            chat_id,
            repr(e)
        )

        return None


# =========================================================
# SEND VOICE DIRECTLY
# =========================================================

async def direct_send_voice(
    chat_id,
    file_path,
    caption,
    inline_keypad=None
):

    try:

        result = bot.send_voice(
            chat_id=str(chat_id),
            path=file_path,
            text=caption,
            file_name=os.path.basename(
                file_path
            ),
            inline_keypad=inline_keypad
        )

        return await maybe_await(result)

    except Exception as e:

        print(
            "SEND VOICE ERROR:",
            chat_id,
            repr(e)
        )

        return None


# =========================================================
# SEND BANNER DIRECTLY
# =========================================================

async def direct_send_banner(
    chat_id,
    file_path,
    caption,
    inline_keypad=None
):

    try:

        result = bot.send_image(
            chat_id=str(chat_id),
            path=file_path,
            text=caption,
            file_name=os.path.basename(
                file_path
            ),
            inline_keypad=inline_keypad
        )

        return await maybe_await(result)

    except Exception as e:

        print(
            "SEND BANNER ERROR:",
            chat_id,
            repr(e)
        )

        return None


# =========================================================
# BROADCAST MUSIC
# =========================================================

async def broadcast_music(
    owner_id,
    file_path,
    caption,
    inline_keypad=None
):

    print(
        "========== MUSIC BROADCAST =========="
    )

    # سازنده اول
    await direct_send_music(
        owner_id,
        file_path,
        caption,
        inline_keypad
    )

    # کاربران بر اساس فعالیت
    users = get_users_by_activity()

    print(
        "USERS ORDER:",
        users
    )

    for user_id in users:

        await direct_send_music(
            user_id,
            file_path,
            caption,
            inline_keypad
        )

    print(
        "MUSIC BROADCAST FINISHED"
    )


# =========================================================
# BROADCAST VOICE
# =========================================================

async def broadcast_voice(
    owner_id,
    file_path,
    caption,
    inline_keypad=None
):

    print(
        "========== VOICE BROADCAST =========="
    )

    await direct_send_voice(
        owner_id,
        file_path,
        caption,
        inline_keypad
    )

    users = get_users_by_activity()

    print(
        "USERS ORDER:",
        users
    )

    for user_id in users:

        await direct_send_voice(
            user_id,
            file_path,
            caption,
            inline_keypad
        )

    print(
        "VOICE BROADCAST FINISHED"
    )


# =========================================================
# BROADCAST BANNER
# =========================================================

async def broadcast_banner(
    owner_id,
    file_path,
    caption,
    inline_keypad=None
):

    print(
        "========== BANNER BROADCAST =========="
    )

    await direct_send_banner(
        owner_id,
        file_path,
        caption,
        inline_keypad
    )

    users = get_users_by_activity()

    print(
        "USERS ORDER:",
        users
    )

    for user_id in users:

        await direct_send_banner(
            user_id,
            file_path,
            caption,
            inline_keypad
        )

    print(
        "BANNER BROADCAST FINISHED"
    )


# =========================================================
# SEND MUSIC PROCESS
# =========================================================

async def finish_music(message):

    chat_id = str(
        message.chat_id
    )

    data = user_data.get(
        chat_id
    )

    if not data:
        return

    file_path = None
    cover_path = data.get(
        "cover_path"
    )

    try:

        await send_text(
            chat_id,
            "⏳ در حال دانلود آهنگ..."
        )

        file_path = download_file(
            data["url"]
        )

        # پیش‌نمایش فوری برای درخواست‌کننده
        await direct_send_music(
            chat_id,
            file_path,
            "👀 پیش‌نمایش آهنگ"
        )

        await send_text(
            chat_id,
            "🎨 در حال آماده‌سازی اطلاعات آهنگ..."
        )

        set_metadata(
            file_path,
            data["title"],
            data["artist"],
            cover_path
        )

        file_path = rename_file(
            file_path,
            data["title"]
        )

        caption = data.get(
            "caption"
        ) or DEFAULT_CAPTION

        inline = glass_button(
            data.get("button_text")
        )

        await send_text(
            chat_id,
            "📤 آهنگ آماده شد.\nدر حال ارسال برای کاربران..."
        )

        await broadcast_music(
            OWNER_ID,
            file_path,
            caption,
            inline
        )

        await send_text(
            OWNER_ID,
            "✅ ارسال آهنگ به سازنده و کاربران تمام شد.",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "MUSIC ERROR:",
            repr(e)
        )

        await send_text(
            chat_id,
            "❌ ارسال آهنگ انجام نشد."
        )

    finally:

        if (
            file_path
            and os.path.exists(file_path)
        ):

            try:
                os.remove(file_path)
            except:
                pass

        if (
            cover_path
            and os.path.exists(cover_path)
        ):

            try:
                os.remove(cover_path)
            except:
                pass

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# SEND VOICE PROCESS
# =========================================================

async def finish_voice(message):

    chat_id = str(
        message.chat_id
    )

    data = user_data.get(
        chat_id
    )

    if not data:
        return

    file_path = None

    try:

        await send_text(
            chat_id,
            "⏳ در حال دانلود ویس..."
        )

        file_path = download_file(
            data["url"]
        )

        # پیش نمایش برای درخواست کننده
        await direct_send_voice(
            chat_id,
            file_path,
            "👀 پیش‌نمایش ویس"
        )

        caption = data.get(
            "caption"
        ) or DEFAULT_CAPTION

        inline = glass_button(
            data.get("button_text")
        )

        await send_text(
            chat_id,
            "📤 ویس آماده شد.\nدر حال ارسال برای کاربران..."
        )

        await broadcast_voice(
            OWNER_ID,
            file_path,
            caption,
            inline
        )

        await send_text(
            OWNER_ID,
            "✅ ارسال ویس به سازنده و کاربران تمام شد.",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "VOICE ERROR:",
            repr(e)
        )

        await send_text(
            chat_id,
            "❌ ارسال ویس انجام نشد."
        )

    finally:

        if (
            file_path
            and os.path.exists(file_path)
        ):

            try:
                os.remove(file_path)
            except:
                pass

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# SEND BANNER PROCESS
# =========================================================

async def finish_banner(message):

    chat_id = str(
        message.chat_id
    )

    data = user_data.get(
        chat_id
    )

    if not data:
        return

    file_path = None

    try:

        await send_text(
            chat_id,
            "⏳ در حال دانلود بنر..."
        )

        file_path = download_banner(
            data["url"]
        )

        # پیش‌نمایش فقط برای درخواست‌کننده
        await direct_send_banner(
            chat_id,
            file_path,
            "👀 پیش‌نمایش بنر"
        )

        caption = data.get(
            "caption"
        ) or DEFAULT_CAPTION

        inline = glass_button(
            data.get("button_text")
        )

        await send_text(
            chat_id,
            "📤 بنر آماده شد.\nدر حال ارسال برای کاربران..."
        )

        await broadcast_banner(
            OWNER_ID,
            file_path,
            caption,
            inline
        )

        await send_text(
            OWNER_ID,
            "✅ ارسال بنر به سازنده و کاربران تمام شد.",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "BANNER ERROR:",
            repr(e)
        )

        await send_text(
            chat_id,
            "❌ ساخت بنر انجام نشد."
        )

    finally:

        if (
            file_path
            and os.path.exists(file_path)
        ):

            try:
                os.remove(file_path)
            except:
                pass

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# MESSAGE HANDLER
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

        print(
            "--------------------------------"
        )

        print(
            "CHAT ID:",
            chat_id
        )

        text = getattr(
            message,
            "text",
            None
        )

        if text:
            text = text.strip()

        print(
            "TEXT:",
            repr(text)
        )

        # ثبت کاربر
        register_user(
            chat_id
        )

        # شمارش پیام
        count_user_message(
            chat_id
        )

        # =================================================
        # START
        # =================================================

        if text == "/start":

            user_data.pop(
                chat_id,
                None
            )

            await send_text(
                chat_id,
                "سلام 👋\nلطفاً از منوی زیر استفاده کنید.",
                chat_keypad=main_keyboard()
            )

            return

        # =================================================
        # MAIN - BANNER
        # =================================================

        if text == "🖼 ساخت بنر":

            user_data[chat_id] = {
                "type": "banner",
                "step": "banner_url",
                "url": None,
                "caption": DEFAULT_CAPTION,
                "button_text": None
            }

            await send_text(
                chat_id,
                "🔗 لینک مستقیم عکس را ارسال کن:"
            )

            return

        # =================================================
        # MAIN - MUSIC
        # =================================================

        if text == "🎵 ادیت آهنگ":

            user_data[chat_id] = {
                "type": "music",
                "step": "audio_url",
                "url": None,
                "caption": DEFAULT_CAPTION,
                "title": "",
                "artist": "",
                "cover_path": None,
                "button_text": None
            }

            await send_text(
                chat_id,
                "🔗 لینک مستقیم آهنگ را ارسال کن:"
            )

            return

        # =================================================
        # CURRENT DATA
        # =================================================

        data = user_data.get(
            chat_id
        )

        if not data:
            return

        # =================================================
        # BANNER URL
        # =================================================

        if (
            data.get("type") == "banner"
            and data.get("step") == "banner_url"
        ):

            url = extract_url(
                text
            )

            if not url:

                await send_text(
                    chat_id,
                    "❌ لینک عکس معتبر نیست."
                )

                return

            data["url"] = url

            await send_text(
                chat_id,
                "⏳ در حال دریافت بنر..."
            )

            try:

                file_path = download_banner(
                    url
                )

                # فقط برای درخواست کننده
                await direct_send_banner(
                    chat_id,
                    file_path,
                    "👀 پیش‌نمایش بنر"
                )

                try:
                    os.remove(file_path)
                except:
                    pass

                data["step"] = "caption"

                await send_text(
                    chat_id,
                    "✏️ کپشن را ارسال کن یا «بعدی» را بزن:",
                    chat_keypad=next_keyboard()
                )

            except Exception as e:

                print(
                    "BANNER DOWNLOAD ERROR:",
                    repr(e)
                )

                await send_text(
                    chat_id,
                    "❌ دریافت بنر انجام نشد."
                )

            return

        # =================================================
        # AUDIO URL
        # =================================================

        if (
            data.get("type") == "music"
            and data.get("step") == "audio_url"
        ):

            url = extract_url(
                text
            )

            if not url:

                await send_text(
                    chat_id,
                    "❌ لینک آهنگ معتبر نیست."
                )

                return

            data["url"] = url

            await send_text(
                chat_id,
                "⏳ در حال دانلود آهنگ..."
            )

            try:

                preview_path = download_file(
                    url
                )

                # فقط برای درخواست کننده
                await direct_send_music(
                    chat_id,
                    preview_path,
                    "👀 پیش‌نمایش آهنگ"
                )

                try:
                    os.remove(preview_path)
                except:
                    pass

                data["step"] = "caption"

                await send_text(
                    chat_id,
                    "✏️ کپشن را ارسال کن یا «بعدی» را بزن:",
                    chat_keypad=next_keyboard()
                )

            except Exception as e:

                print(
                    "AUDIO DOWNLOAD ERROR:",
                    repr(e)
                )

                await send_text(
                    chat_id,
                    "❌ دانلود آهنگ انجام نشد."
                )

            return

        # =================================================
        # CAPTION
        # =================================================

        if data.get("step") == "caption":

            if text == "بعدی":

                data["caption"] = DEFAULT_CAPTION

            else:

                if not text:
                    return

                data["caption"] = text

            if data["type"] == "banner":

                data["step"] = "button"

                await send_text(
                    chat_id,
                    "متن دکمه شیشه‌ای نمایشی را ارسال کن یا «بعدی» را بزن:",
                    chat_keypad=next_keyboard()
                )

            else:

                data["step"] = "type"

                await send_text(
                    chat_id,
                    "📦 نوع ارسال را انتخاب کن:",
                    chat_keypad=type_keyboard()
                )

            return

        # =================================================
        # BANNER BUTTON
        # =================================================

        if (
            data.get("type") == "banner"
            and data.get("step") == "button"
        ):

            if text == "بعدی":

                data["button_text"] = None

            else:

                if not text:
                    return

                data["button_text"] = text

            # دوباره دانلود نکن؛ اینجا نهایی می‌سازیم
            data["step"] = "finish_banner"

            await finish_banner(
                message
            )

            return

        # =================================================
        # TYPE
        # =================================================

        if data.get("step") == "type":

            if text == "🎤 ویس":

                data["type"] = "voice"
                data["step"] = "button"

                await send_text(
                    chat_id,
                    "متن دکمه شیشه‌ای نمایشی را ارسال کن یا «بعدی» را بزن:",
                    chat_keypad=next_keyboard()
                )

                return

            if text == "🎵 آهنگ":

                data["type"] = "music"
                data["step"] = "title"

                await send_text(
                    chat_id,
                    "🎵 اسم آهنگ را بفرست:"
                )

                return

            return

        # =================================================
        # TITLE
        # =================================================

        if (
            data.get("type") == "music"
            and data.get("step") == "title"
        ):

            if not text:
                return

            if extract_url(text):

                await send_text(
                    chat_id,
                    "❌ اینجا اسم آهنگ را ارسال کن."
                )

                return

            data["title"] = text
            data["step"] = "artist"

            await send_text(
                chat_id,
                "🎤 اسم خواننده را بفرست:"
            )

            return

        # =================================================
        # ARTIST
        # =================================================

        if (
            data.get("type") == "music"
            and data.get("step") == "artist"
        ):

            if not text:
                return

            if extract_url(text):

                await send_text(
                    chat_id,
                    "❌ اینجا اسم خواننده را ارسال کن."
                )

                return

            data["artist"] = text
            data["step"] = "cover"

            await send_text(
                chat_id,
                "🖼 لینک کاور را ارسال کن یا «بعدی» را بزن:",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # COVER
        # =================================================

        if (
            data.get("type") == "music"
            and data.get("step") == "cover"
        ):

            if text == "بعدی":

                data["cover_path"] = None

            else:

                cover_url = extract_url(
                    text
                )

                if not cover_url:

                    await send_text(
                        chat_id,
                        "❌ لینک کاور معتبر نیست."
                    )

                    return

                await send_text(
                    chat_id,
                    "⏳ در حال دانلود کاور..."
                )

                cover_path = (
                    await download_cover_from_url(
                        cover_url
                    )
                )

                if not cover_path:

                    await send_text(
                        chat_id,
                        "❌ عکس معتبر نیست یا حجم آن بیشتر از 10MB است."
                    )

                    return

                data["cover_path"] = cover_path

            data["step"] = "button"

            await send_text(
                chat_id,
                "متن دکمه شیشه‌ای نمایشی را ارسال کن یا «بعدی» را بزن:",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # MUSIC / VOICE BUTTON
        # =================================================

        if data.get("step") == "button":

            if text == "بعدی":

                data["button_text"] = None

            else:

                if not text:
                    return

                data["button_text"] = text

            if data["type"] == "music":

                await finish_music(
                    message
                )

            elif data["type"] == "voice":

                await finish_voice(
                    message
                )

            return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )


# =========================================================
# START
# =========================================================

print(
    "======================================"
)

print(
    "        RUBIKA MEDIA BOT"
)

print(
    "======================================"
)

print(
    "BOT STARTED..."
)

bot.run()
