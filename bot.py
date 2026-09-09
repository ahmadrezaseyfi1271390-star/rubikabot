import os
import re
import json
import uuid
import asyncio
import requests
import gdown

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder
from rubka.button import InlineBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC


# =========================================================
# SETTINGS
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

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
        return []

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):
                return data

    except Exception as e:

        print(
            "USERS LOAD ERROR:",
            repr(e)
        )

    return []


def save_users(users):

    users = list(
        dict.fromkeys(
            str(x)
            for x in users
        )
    )

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


def register_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users.append(chat_id)

        save_users(users)

        print(
            "NEW USER:",
            chat_id
        )


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    builder = ChatKeypadBuilder()

    return (
        builder
        .row(
            builder.button(
                id="make_banner",
                text="🖼 ساخت بنر"
            ),
            builder.button(
                id="edit_music",
                text="🎵 ادیت آهنگ"
            )
        )
        .build(
            resize_keyboard=True,
            on_time_keyboard=False
        )
    )


# =========================================================
# TYPE KEYBOARD
# =========================================================

def type_keyboard():

    builder = ChatKeypadBuilder()

    return (
        builder
        .row(
            builder.button(
                id="music",
                text="🎵 آهنگ"
            ),
            builder.button(
                id="voice",
                text="🎤 ویس"
            )
        )
        .build(
            resize_keyboard=True,
            on_time_keyboard=False
        )
    )


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
# AWAIT
# =========================================================

async def maybe_await(result):

    if hasattr(
        result,
        "__await__"
    ):

        return await result

    return result


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

    try:

        builder = InlineBuilder()

        keypad = (
            builder
            .row(
                builder.button_url_link(
                    id="glass_button",
                    text=button_text,
                    url=button_url
                )
            )
            .build()
        )

        print(
            "GLASS BUTTON:",
            keypad
        )

        return keypad

    except Exception as e:

        print(
            "GLASS BUTTON ERROR:",
            repr(e)
        )

        return None


# =========================================================
# DOWNLOAD AUDIO
# =========================================================

def download_file(url):

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"audio_{uuid.uuid4().hex}.mp3"
    )

    print(
        "AUDIO URL:",
        url
    )

    # -----------------------------------------------------
    # GOOGLE DRIVE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # NORMAL URL
    # -----------------------------------------------------

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

            if os.path.exists(
                output_path
            ):

                try:
                    os.remove(
                        output_path
                    )
                except:
                    pass

            raise

    # -----------------------------------------------------
    # CHECK
    # -----------------------------------------------------

    if not os.path.exists(
        output_path
    ):

        raise Exception(
            "فایل دانلود نشد."
        )

    size = os.path.getsize(
        output_path
    )

    if size <= 0:

        raise Exception(
            "فایل دانلود شده خالی است."
        )

    if size > MAX_FILE_SIZE:

        try:
            os.remove(output_path)
        except:
            pass

        raise Exception(
            "حجم فایل بیشتر از 200MB است."
        )

    print(
        "AUDIO SIZE:",
        size
    )

    return output_path


# =========================================================
# DOWNLOAD COVER
# =========================================================

def download_cover(url):

    try:

        print(
            "COVER URL:",
            url
        )

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

            print(
                "COVER TOO LARGE"
            )

            return None

        from PIL import Image
        from io import BytesIO

        image = Image.open(
            BytesIO(data)
        )

        image.load()

        image = image.convert(
            "RGB"
        )

        path = os.path.join(
            DOWNLOAD_FOLDER,
            f"cover_{uuid.uuid4().hex}.jpg"
        )

        image.save(
            path,
            "JPEG",
            quality=95
        )

        image.close()

        print(
            "COVER SAVED:",
            path
        )

        return path

    except Exception as e:

        print(
            "COVER ERROR:",
            repr(e)
        )

        return None


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
            tags = ID3(file_path)
        except:
            tags = ID3()

        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.delall("APIC")

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

        print(
            "METADATA OK"
        )

    except Exception as e:

        print(
            "METADATA ERROR:",
            repr(e)
        )


# =========================================================
# RENAME
# =========================================================

def rename_file(
    file_path,
    title
):

    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        title or "music"
    )

    safe_title = safe_title.strip()

    if not safe_title:

        safe_title = "music"

    new_path = os.path.join(
        DOWNLOAD_FOLDER,
        safe_title + ".mp3"
    )

    counter = 1

    while os.path.exists(
        new_path
    ):

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
# MESSAGE ID
# =========================================================

def get_message_id(result):

    if result is None:
        return None

    for attr in [
        "message_id",
        "id"
    ]:

        value = getattr(
            result,
            attr,
            None
        )

        if value:

            return str(value)

    if isinstance(
        result,
        dict
    ):

        for key in [
            "message_id",
            "id"
        ]:

            if key in result:

                return str(
                    result[key]
                )

    return None


# =========================================================
# BROADCAST MUSIC / VOICE
# =========================================================

async def broadcast_file(
    message_id,
    owner_chat_id
):

    users = load_users()

    success = 0
    failed = 0

    print(
        "BROADCAST USERS:",
        len(users)
    )

    for user_id in users:

        user_id = str(user_id)

        # اول برای سازنده فرستاده شده،
        # پس دوباره برای خودش نفرست

        if user_id == str(
            owner_chat_id
        ):

            continue

        try:

            result = bot.forward_message(
                from_chat_id=str(
                    owner_chat_id
                ),
                message_id=str(
                    message_id
                ),
                to_chat_id=user_id
            )

            await maybe_await(
                result
            )

            success += 1

            print(
                "FORWARDED:",
                user_id
            )

        except Exception as e:

            failed += 1

            print(
                "FORWARD ERROR:",
                user_id,
                repr(e)
            )

        await asyncio.sleep(
            0.15
        )

    return success, failed


# =========================================================
# BROADCAST BANNER
# =========================================================

async def broadcast_banner(
    banner_message_id,
    owner_chat_id
):

    users = load_users()

    success = 0
    failed = 0

    print(
        "BANNER BROADCAST:",
        len(users)
    )

    for user_id in users:

        user_id = str(user_id)

        if user_id == str(
            owner_chat_id
        ):

            continue

        try:

            result = bot.forward_message(
                from_chat_id=str(
                    owner_chat_id
                ),
                message_id=str(
                    banner_message_id
                ),
                to_chat_id=user_id
            )

            await maybe_await(
                result
            )

            success += 1

            print(
                "BANNER SENT:",
                user_id
            )

        except Exception as e:

            failed += 1

            print(
                "BANNER ERROR:",
                user_id,
                repr(e)
            )

        await asyncio.sleep(
            0.15
        )

    return success, failed


# =========================================================
# SEND MUSIC
# =========================================================

async def process_music(
    message
):

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

        await message.reply(
            "⏳ در حال دانلود آهنگ..."
        )

        file_path = download_file(
            data["url"]
        )

        # -------------------------------------------------
        # METADATA
        # -------------------------------------------------

        if data["media_type"] == "🎵 آهنگ":

            await message.reply(
                "🎨 در حال آماده‌سازی آهنگ..."
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

        # -------------------------------------------------
        # GLASS BUTTON
        # -------------------------------------------------

        inline_keypad = make_glass_button(
            data.get("button_text"),
            data.get("button_url")
        )

        # -------------------------------------------------
        # SEND TO OWNER
        # -------------------------------------------------

        await message.reply(
            "📤 فایل آماده شد؛ در حال ارسال..."
        )

        if data["media_type"] == "🎵 آهنگ":

            result = bot.send_music(
                chat_id=chat_id,
                path=file_path,
                text=data["caption"],
                file_name=os.path.basename(
                    file_path
                ),
                inline_keypad=inline_keypad
            )

        else:

            result = bot.send_voice(
                chat_id=chat_id,
                path=file_path,
                text=data["caption"],
                file_name=os.path.basename(
                    file_path
                ),
                inline_keypad=inline_keypad
            )

        result = await maybe_await(
            result
        )

        message_id = get_message_id(
            result
        )

        print(
            "CREATED MESSAGE ID:",
            message_id
        )

        if not message_id:

            await message.reply(
                "⚠️ فایل برای شما ارسال شد، "
                "اما شناسه پیام برای ارسال همگانی پیدا نشد."
            )

            return

        # -------------------------------------------------
        # BROADCAST
        # -------------------------------------------------

        await message.reply(
            "📢 حالا در حال ارسال به کاربران..."
        )

        success, failed = await broadcast_file(
            message_id,
            chat_id
        )

        await message.reply(
            "✅ <b>ارسال کامل شد.</b>\n\n"
            f"👤 برای شما: ارسال شد\n"
            f"📢 کاربران موفق: {success}\n"
            f"❌ کاربران ناموفق: {failed}",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "PROCESS MUSIC ERROR:",
            repr(e)
        )

        await message.reply(
            "❌ خطا در پردازش فایل:\n\n"
            f"<code>{e}</code>",
            chat_keypad=main_keyboard()
        )

    finally:

        if (
            file_path
            and os.path.exists(file_path)
        ):

            try:
                os.remove(
                    file_path
                )
            except:
                pass

        if (
            cover_path
            and os.path.exists(cover_path)
        ):

            try:
                os.remove(
                    cover_path
                )
            except:
                pass

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# PROCESS BANNER
# =========================================================

async def process_banner(
    message
):

    chat_id = str(
        message.chat_id
    )

    data = user_data.get(
        chat_id
    )

    if not data:
        return

    try:

        image_url = data.get(
            "image_url"
        )

        caption = data.get(
            "caption",
            ""
        )

        button_text = data.get(
            "button_text"
        )

        button_url = data.get(
            "button_url"
        )

        inline_keypad = make_glass_button(
            button_text,
            button_url
        )

        # -------------------------------------------------
        # SEND BANNER TO OWNER
        # -------------------------------------------------

        await message.reply(
            "📤 بنر آماده شد؛ در حال ارسال برای شما..."
        )

        if image_url:

            result = bot.send_image(
                chat_id=chat_id,
                path=image_url,
                text=caption,
                inline_keypad=inline_keypad
            )

        else:

            result = bot.send_message(
                chat_id=chat_id,
                text=caption or "🖼 بنر",
                inline_keypad=inline_keypad
            )

        result = await maybe_await(
            result
        )

        message_id = get_message_id(
            result
        )

        print(
            "BANNER MESSAGE ID:",
            message_id
        )

        if not message_id:

            await message.reply(
                "⚠️ بنر ارسال شد، اما شناسه پیام پیدا نشد."
            )

            return

        # -------------------------------------------------
        # BROADCAST
        # -------------------------------------------------

        await message.reply(
            "📢 بنر برای شما ارسال شد.\n"
            "حالا در حال ارسال به همه کاربران..."
        )

        success, failed = await broadcast_banner(
            message_id,
            chat_id
        )

        await message.reply(
            "✅ <b>ارسال بنر کامل شد.</b>\n\n"
            f"👤 برای شما: ارسال شد\n"
            f"📢 کاربران موفق: {success}\n"
            f"❌ کاربران ناموفق: {failed}",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "BANNER ERROR:",
            repr(e)
        )

        await message.reply(
            "❌ خطا در ساخت یا ارسال بنر:\n\n"
            f"<code>{e}</code>",
            chat_keypad=main_keyboard()
        )

    finally:

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# START
# =========================================================

@bot.on_message(commands=["start"])
async def start(
    bot,
    message: Message
):

    chat_id = str(
        message.chat_id
    )

    register_user(
        chat_id
    )

    user_data.pop(
        chat_id,
        None
    )

    await message.reply(
        "🤖 <b>پنل مدیریت ربات</b>\n\n"
        "یکی از گزینه‌های زیر را انتخاب کن:",
        chat_keypad=main_keyboard()
    )


# =========================================================
# MAIN HANDLER
# =========================================================

@bot.on_message()
async def handle_message(
    bot,
    message: Message
):

    try:

        chat_id = str(
            message.chat_id
        )

        register_user(
            chat_id
        )

        text = getattr(
            message,
            "text",
            None
        )

        if text:
            text = text.strip()

        # =================================================
        # START
        # =================================================

        if text == "/start":

            user_data.pop(
                chat_id,
                None
            )

            await message.reply(
                "🤖 <b>پنل مدیریت ربات</b>\n\n"
                "یکی از گزینه‌های زیر را انتخاب کن:",
                chat_keypad=main_keyboard()
            )

            return


        # =================================================
        # MAKE BANNER
        # =================================================

        if text == "🖼 ساخت بنر":

            user_data[chat_id] = {

                "type": "banner",

                "step": "image",

                "image_url": None,

                "caption": "",

                "button_text": None,

                "button_url": None
            }

            await message.reply(
                "🖼 <b>ساخت بنر</b>\n\n"
                "🔗 لینک مستقیم تصویر را بفرست.\n\n"
                "مثال:\n"
                "https://example.com/banner.jpg\n\n"
                "برای رد کردن بنویس: <code>بعدی</code>"
            )

            return


        # =================================================
        # EDIT MUSIC
        # =================================================

        if text == "🎵 ادیت آهنگ":

            user_data[chat_id] = {

                "type": "music",

                "step": "url",

                "url": None,

                "caption": DEFAULT_CAPTION,

                "media_type": None,

                "title": "",

                "artist": "",

                "cover_path": None,

                "button_text": None,

                "button_url": None
            }

            await message.reply(
                "🎵 <b>ادیت آهنگ</b>\n\n"
                "🔗 لینک مستقیم دانلود آهنگ را بفرست."
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
        # BANNER FLOW
        # =================================================

        if data["type"] == "banner":

            step = data["step"]


            # ---------------------------------------------
            # IMAGE
            # ---------------------------------------------

            if step == "image":

                if text == "بعدی":

                    data["image_url"] = None

                else:

                    url = extract_url(
                        text
                    )

                    if not url:

                        await message.reply(
                            "❌ لطفاً لینک تصویر را ارسال کن."
                        )

                        return

                    data["image_url"] = url

                data["step"] = "caption"

                await message.reply(
                    "📝 کپشن بنر را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )

                return


            # ---------------------------------------------
            # CAPTION
            # ---------------------------------------------

            if step == "caption":

                data["caption"] = (
                    ""
                    if text == "بعدی"
                    else text
                )

                data["step"] = "button_text"

                await message.reply(
                    "🔘 متن دکمه شیشه‌ای را بفرست.\n\n"
                    "مثلاً:\n"
                    "🌐 ورود به سایت\n\n"
                    "یا <code>بعدی</code>."
                )

                return


            # ---------------------------------------------
            # BUTTON TEXT
            # ---------------------------------------------

            if step == "button_text":

                if text == "بعدی":

                    data["button_text"] = None
                    data["button_url"] = None

                    await process_banner(
                        message
                    )

                    return

                data["button_text"] = text

                data["step"] = "button_url"

                await message.reply(
                    "🔗 لینک دکمه شیشه‌ای را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )

                return


            # ---------------------------------------------
            # BUTTON URL
            # ---------------------------------------------

            if step == "button_url":

                if text == "بعدی":

                    data["button_url"] = None

                else:

                    url = extract_url(
                        text
                    )

                    if not url:

                        await message.reply(
                            "❌ لطفاً یک لینک معتبر بفرست."
                        )

                        return

                    data["button_url"] = url

                await process_banner(
                    message
                )

                return


        # =================================================
        # MUSIC FLOW
        # =================================================

        if data["type"] == "music":

            step = data["step"]


            # ---------------------------------------------
            # URL
            # ---------------------------------------------

            if step == "url":

                url = extract_url(
                    text
                )

                if not url:

                    await message.reply(
                        "❌ لطفاً لینک دانلود را ارسال کن."
                    )

                    return

                data["url"] = url

                data["step"] = "caption"

                await message.reply(
                    "📝 کپشن آهنگ را بفرست.\n\n"
                    "اگر همان کپشن پیش‌فرض را می‌خواهی، بنویس:\n"
                    "<code>بعدی</code>"
                )

                return


            # ---------------------------------------------
            # CAPTION
            # ---------------------------------------------

            if step == "caption":

                if text == "بعدی":

                    data["caption"] = DEFAULT_CAPTION

                else:

                    data["caption"] = text

                data["step"] = "type"

                await message.reply(
                    "📦 نوع فایل را انتخاب کن:",
                    chat_keypad=type_keyboard()
                )

                return


            # ---------------------------------------------
            # TYPE
            # ---------------------------------------------

            if step == "type":

                if text == "🎤 ویس":

                    data["media_type"] = "🎤 ویس"

                    data["step"] = "button_text"

                    await message.reply(
                        "🔘 متن دکمه شیشه‌ای را بفرست.\n\n"
                        "یا <code>بعدی</code>."
                    )

                    return


                if text == "🎵 آهنگ":

                    data["media_type"] = "🎵 آهنگ"

                    data["step"] = "title"

                    await message.reply(
                        "🎵 اسم آهنگ را بفرست:"
                    )

                    return

                return


            # ---------------------------------------------
            # TITLE
            # ---------------------------------------------

            if step == "title":

                if not text:

                    return

                if text == "بعدی":

                    data["title"] = "music"

                else:

                    data["title"] = text

                data["step"] = "artist"

                await message.reply(
                    "🎤 اسم خواننده را بفرست:"
                )

                return


            # ---------------------------------------------
            # ARTIST
            # ---------------------------------------------

            if step == "artist":

                if not text:

                    return

                if text == "بعدی":

                    data["artist"] = "Unknown"

                else:

                    data["artist"] = text

                data["step"] = "cover_url"

                await message.reply(
                    "🖼 لینک مستقیم کاور را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )

                return


            # ---------------------------------------------
            # COVER
            # ---------------------------------------------

            if step == "cover_url":

                if text == "بعدی":

                    data["cover_path"] = None

                else:

                    url = extract_url(
                        text
                    )

                    if not url:

                        await message.reply(
                            "❌ لینک معتبر ارسال کن."
                        )

                        return

                    await message.reply(
                        "⏳ در حال دانلود کاور..."
                    )

                    cover = download_cover(
                        url
                    )

                    if not cover:

                        await message.reply(
                            "❌ دانلود کاور انجام نشد."
                        )

                        return

                    data["cover_path"] = cover

                    await message.reply(
                        "✅ کاور دریافت شد."
                    )

                data["step"] = "button_text"

                await message.reply(
                    "🔘 متن دکمه شیشه‌ای را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )

                return


            # ---------------------------------------------
            # BUTTON TEXT
            # ---------------------------------------------

            if step == "button_text":

                if text == "بعدی":

                    data["button_text"] = None
                    data["button_url"] = None

                    await process_music(
                        message
                    )

                    return

                data["button_text"] = text

                data["step"] = "button_url"

                await message.reply(
                    "🔗 لینک دکمه شیشه‌ای را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )

                return


            # ---------------------------------------------
            # BUTTON URL
            # ---------------------------------------------

            if step == "button_url":

                if text == "بعدی":

                    data["button_url"] = None

                else:

                    url = extract_url(
                        text
                    )

                    if not url:

                        await message.reply(
                            "❌ لطفاً لینک معتبر ارسال کن."
                        )

                        return

                    data["button_url"] = url

                await process_music(
                    message
                )

                return


    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )


# =========================================================
# RUN
# =========================================================

print(
    "======================================"
)

print(
    "       RUBIKA MUSIC + BANNER BOT"
)

print(
    "======================================"
)

print(
    "BOT STARTED..."
)

bot.run()
