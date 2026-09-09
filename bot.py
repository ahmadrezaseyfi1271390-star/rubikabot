import os
import re
import json
import uuid
import requests
import gdown

from urllib.parse import urlparse, unquote

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC
from mutagen.mp3 import MP3


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_FILE_SIZE = 200 * 1024 * 1024       # 200 MB
MAX_COVER_SIZE = 10 * 1024 * 1024       # 10 MB

DOWNLOAD_FOLDER = "downloads"
USERS_FILE = "users.json"


# =========================================================
# ساخت پوشه
# =========================================================

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================================================
# ساخت ربات
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# اطلاعات موقت کاربران
# =========================================================

user_data = {}


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

    except Exception as e:
        print("users.json error:", e)

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


# =========================================================
# کیبورد انتخاب نوع
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
# استخراج لینک
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
# اجرای تابع sync یا async
# =========================================================

async def maybe_await(result):

    if hasattr(result, "__await__"):
        return await result

    return result


# =========================================================
# دانلود فایل صوتی
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

    print("Downloading audio:")
    print(url)

    # -----------------------------------------------------
    # Google Drive
    # -----------------------------------------------------

    if "drive.google.com" in url:

        try:

            gdown.download(
                url,
                output_path,
                quiet=False
            )

        except Exception as e:

            print("Google Drive ERROR:", e)

            raise Exception(
                "دانلود از گوگل درایو انجام نشد."
            )

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

                    # محدودیت 200MB
                    if total_size > MAX_FILE_SIZE:

                        f.close()

                        try:
                            os.remove(output_path)
                        except:
                            pass

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

    # بررسی حجم نهایی
    if not os.path.exists(output_path):
        raise Exception(
            "فایل دانلود نشد."
        )

    file_size = os.path.getsize(
        output_path
    )

    print(
        "Downloaded size:",
        file_size
    )

    if file_size > MAX_FILE_SIZE:

        try:
            os.remove(output_path)
        except:
            pass

        raise Exception(
            "حجم فایل بیشتر از 200MB است."
        )

    return output_path


# =========================================================
# دانلود کاور از لینک
# =========================================================

async def download_cover_from_url(url):

    try:

        print("Downloading cover:")
        print(url)

        response = requests.get(
            url,
            stream=True,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        content_type = (
            response.headers
            .get("content-type", "")
            .lower()
        )

        print(
            "Cover content type:",
            content_type
        )

        # -------------------------------------------------
        # بررسی نوع فایل
        # -------------------------------------------------

        if not content_type.startswith("image/"):

            # بعضی سایت‌ها Content-Type درست نمی‌فرستند.
            # پس ابتدا داده را می‌خوانیم و با PIL بررسی می‌کنیم.

            data = response.content

            if len(data) > MAX_COVER_SIZE:
                return None

            try:

                from PIL import Image
                from io import BytesIO

                img = Image.open(
                    BytesIO(data)
                )

                img.verify()

            except Exception:

                print(
                    "URL is not a valid image."
                )

                return None

        else:

            data = response.content

        # -------------------------------------------------
        # محدودیت حجم کاور
        # -------------------------------------------------

        if len(data) > MAX_COVER_SIZE:

            print(
                "Cover is too large."
            )

            return None

        # -------------------------------------------------
        # پوشه
        # -------------------------------------------------

        os.makedirs(
            DOWNLOAD_FOLDER,
            exist_ok=True
        )

        # -------------------------------------------------
        # فایل موقت
        # -------------------------------------------------

        temp_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"cover_{uuid.uuid4().hex}"
        )

        with open(
            temp_path,
            "wb"
        ) as f:

            f.write(data)

        # -------------------------------------------------
        # تبدیل کاور به JPG استاندارد
        # -------------------------------------------------

        try:

            from PIL import Image

            image = Image.open(
                temp_path
            )

            image = image.convert(
                "RGB"
            )

            jpg_path = (
                temp_path +
                ".jpg"
            )

            image.save(
                jpg_path,
                "JPEG",
                quality=95
            )

            image.close()

            try:
                os.remove(temp_path)
            except:
                pass

            print(
                "Cover saved:",
                jpg_path
            )

            return jpg_path

        except Exception as e:

            print(
                "Cover conversion ERROR:",
                e
            )

            try:
                os.remove(temp_path)
            except:
                pass

            return None

    except Exception as e:

        print(
            "DOWNLOAD COVER ERROR:",
            e
        )

        return None


# =========================================================
# افزودن متادیتا به MP3
# =========================================================

def set_metadata(
    file_path,
    title,
    artist,
    cover_path
):

    print("Setting metadata...")

    try:

        try:

            audio = ID3(
                file_path
            )

        except:

            audio = ID3()

        # حذف متادیتای قبلی
        audio.delall("TIT2")
        audio.delall("TPE1")
        audio.delall("APIC")

        # عنوان
        audio.add(
            TIT2(
                encoding=3,
                text=title
            )
        )

        # خواننده
        audio.add(
            TPE1(
                encoding=3,
                text=artist
            )
        )

        # کاور
        if (
            cover_path
            and os.path.exists(cover_path)
        ):

            with open(
                cover_path,
                "rb"
            ) as f:

                cover_data = f.read()

            audio.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=cover_data
                )
            )

        audio.save(
            file_path
        )

        print(
            "Metadata saved."
        )

    except Exception as e:

        print(
            "Metadata ERROR:",
            e
        )

        raise


# =========================================================
# تغییر نام فایل
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

    # اگر فایل همنام وجود داشت
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
# گرفتن Message ID
# =========================================================

def get_message_id(result):

    if result is None:
        return None

    # حالت‌های مختلف پاسخ API

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

    if isinstance(result, dict):

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
# فوروارد برای کاربران
# =========================================================

async def forward_to_users(
    from_chat_id,
    message_id
):

    if not message_id:

        print(
            "Message ID پیدا نشد."
        )

        return

    users = load_users()

    print(
        "Users:",
        users
    )

    for user_id in users:

        user_id = str(user_id)

        # برای درخواست‌کننده دوباره ارسال نکن
        if user_id == str(from_chat_id):
            continue

        try:

            result = bot.forward_message(
                from_chat_id=str(
                    from_chat_id
                ),
                message_id=str(
                    message_id
                ),
                to_chat_id=user_id
            )

            await maybe_await(
                result
            )

            print(
                "Forwarded:",
                user_id
            )

        except Exception as e:

            print(
                "Forward ERROR:",
                user_id,
                e
            )


# =========================================================
# ارسال ویس
# =========================================================

async def send_voice(message):

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

        await message.reply(
            "⏳ در حال دانلود و آماده‌سازی ویس..."
        )

        # دانلود
        file_path = download_file(
            data["url"]
        )

        await message.reply(
            "📤 در حال ارسال ویس..."
        )

        # ارسال ویس
        result = bot.send_voice(
            chat_id=chat_id,
            path=file_path,
            text=data["caption"],
            file_name=os.path.basename(
                file_path
            )
        )

        result = await maybe_await(
            result
        )

        message_id = get_message_id(
            result
        )

        print(
            "Voice message ID:",
            message_id
        )

        # فوروارد
        await forward_to_users(
            chat_id,
            message_id
        )

        await message.reply(
            "✅ ویس با موفقیت ارسال شد."
        )

    except Exception as e:

        print(
            "VOICE ERROR:",
            e
        )

        error_text = str(e)

        if "200MB" in error_text:

            await message.reply(
                "❌ حجم فایل بیشتر از ۲۰۰ مگابایت است."
            )

        else:

            await message.reply(
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
# ارسال آهنگ
# =========================================================

async def send_music(message):

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

        # -------------------------------------------------
        # دانلود آهنگ
        # -------------------------------------------------

        file_path = download_file(
            data["url"]
        )

        # -------------------------------------------------
        # افزودن متادیتا
        # -------------------------------------------------

        await message.reply(
            "🎨 در حال قرار دادن کاور و اطلاعات آهنگ..."
        )

        set_metadata(
            file_path=file_path,
            title=data["title"],
            artist=data["artist"],
            cover_path=cover_path
        )

        # -------------------------------------------------
        # تغییر نام
        # -------------------------------------------------

        file_path = rename_file(
            file_path,
            data["title"]
        )

        # -------------------------------------------------
        # ارسال آهنگ
        # -------------------------------------------------

        await message.reply(
            "📤 در حال ارسال آهنگ..."
        )

        result = bot.send_music(
            chat_id=chat_id,
            path=file_path,
            text=data["caption"],
            file_name=os.path.basename(
                file_path
            )
        )

        result = await maybe_await(
            result
        )

        message_id = get_message_id(
            result
        )

        print(
            "Music message ID:",
            message_id
        )

        # -------------------------------------------------
        # فوروارد
        # -------------------------------------------------

        await forward_to_users(
            chat_id,
            message_id
        )

        await message.reply(
            "✅ آهنگ با موفقیت ارسال شد."
        )

    except Exception as e:

        print(
            "MUSIC ERROR:",
            e
        )

        error_text = str(e)

        if "200MB" in error_text:

            await message.reply(
                "❌ حجم فایل بیشتر از ۲۰۰ مگابایت است."
            )

        else:

            print(
                "Full error:",
                repr(e)
            )

            await message.reply(
                "❌ ارسال آهنگ انجام نشد."
            )

    finally:

        # -------------------------------------------------
        # حذف فایل آهنگ
        # -------------------------------------------------

        if (
            file_path
            and os.path.exists(file_path)
        ):

            try:
                os.remove(file_path)
            except:
                pass

        # -------------------------------------------------
        # حذف کاور
        # -------------------------------------------------

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
# دریافت پیام
# =========================================================

@bot.on_message()
async def handle_message(
    message: Message
):

    try:

        chat_id = str(
            message.chat_id
        )

        register_user(
            chat_id
        )

        # -------------------------------------------------
        # متن پیام
        # -------------------------------------------------

        text = getattr(
            message,
            "text",
            None
        )

        if text:
            text = text.strip()

        # -------------------------------------------------
        # START
        # -------------------------------------------------

        if text == "/start":

            user_data.pop(
                chat_id,
                None
            )

            await message.reply(
                "🎵 سلام!\n\n"
                "لینک فایل صوتی را ارسال کن."
            )

            return

        # -------------------------------------------------
        # اطلاعات فعلی کاربر
        # -------------------------------------------------

        data = user_data.get(
            chat_id
        )

        # -------------------------------------------------
        # دکمه ویس
        # -------------------------------------------------

        if text == "🎤 ویس":

            if (
                not data
                or data.get("step") != "type"
            ):
                return

            await send_voice(
                message
            )

            return

        # -------------------------------------------------
        # دکمه آهنگ
        # -------------------------------------------------

        if text == "🎵 آهنگ":

            if (
                not data
                or data.get("step") != "type"
            ):
                return

            data["step"] = "title"

            await message.reply(
                "🎵 اسم آهنگ را بفرست:"
            )

            return

        # =================================================
        # مرحله کپشن
        # =================================================

        if (
            data
            and data.get("step") == "caption"
        ):

            if not text:
                return

            # کپشن
            data["caption"] = text

            data["step"] = "type"

            await message.reply(
                "📦 نوع ارسال را انتخاب کن:",
                chat_keypad=type_keyboard()
            )

            return

        # =================================================
        # مرحله اسم آهنگ
        # =================================================

        if (
            data
            and data.get("step") == "title"
        ):

            if not text:
                return

            # اگر کاربر لینک فرستاد قبول نکن
            if extract_url(text):

                await message.reply(
                    "❌ اینجا باید اسم آهنگ را ارسال کنی."
                )

                return

            data["title"] = text

            data["step"] = "artist"

            await message.reply(
                "🎤 اسم خواننده را بفرست:"
            )

            return

        # =================================================
        # مرحله خواننده
        # =================================================

        if (
            data
            and data.get("step") == "artist"
        ):

            if not text:
                return

            if extract_url(text):

                await message.reply(
                    "❌ اینجا باید اسم خواننده را ارسال کنی."
                )

                return

            data["artist"] = text

            data["step"] = "cover_url"

            await message.reply(
                "🖼 لطفاً لینک مستقیم عکس کاور را ارسال کن:\n\n"
                "مثال:\n"
                "https://example.com/cover.jpg"
            )

            return

        # =================================================
        # مرحله لینک کاور
        # =================================================

        if (
            data
            and data.get("step") == "cover_url"
        ):

            cover_url = extract_url(
                text
            )

            if not cover_url:

                await message.reply(
                    "❌ لطفاً لینک عکس را درست ارسال کن."
                )

                return

            await message.reply(
                "⏳ در حال دانلود کاور..."
            )

            cover_path = (
                await download_cover_from_url(
                    cover_url
                )
            )

            if not cover_path:

                await message.reply(
                    "❌ این لینک به یک عکس معتبر اشاره نمی‌کند.\n\n"
                    "لطفاً لینک مستقیم JPG یا PNG را ارسال کن."
                )

                return

            data["cover_path"] = (
                cover_path
            )

            await message.reply(
                "✅ کاور دریافت شد.\n\n"
                "⏳ حالا آهنگ در حال آماده‌سازی است..."
            )

            await send_music(
                message
            )

            return

        # =================================================
        # دریافت لینک آهنگ
        # =================================================

        url = extract_url(
            text
        )

        if url:

            user_data[chat_id] = {

                "step": "caption",

                "url": url,

                "caption": DEFAULT_CAPTION,

                "title": "",

                "artist": "",

                "cover_path": None
            }

            await message.reply(
                "✏️ کپشن فایل را ارسال کن:"
            )

            return

        # =================================================
        # پیام‌های نامرتبط
        # =================================================

        return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )


# =========================================================
# اجرای ربات
# =========================================================

print("===================================")
print("      RUBIKA MUSIC BOT")
print("===================================")
print("Bot is starting...")

bot.run()
