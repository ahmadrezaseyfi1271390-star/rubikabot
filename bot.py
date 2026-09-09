import os
import re
import json
import uuid
import mimetypes
import requests
import gdown

from urllib.parse import urlparse, unquote

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TIT2, TPE1


# =========================
# تنظیمات
# =========================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DOWNLOAD_FOLDER = "./downloads"
USERS_FILE = "./users.json"

MAX_FILE_SIZE = 50 * 1024 * 1024

CHANNEL_TAG = "@Black_list_remix"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================
# ربات
# =========================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================
# کاربران
# =========================

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
        json.dump(
            list(dict.fromkeys(users)),
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


# =========================
# وضعیت کاربران
# =========================

user_data = {}


# =========================
# کیبورد انتخاب نوع فایل
# =========================

def type_keyboard():

    builder = ChatKeypadBuilder()

    keypad = (
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

    return keypad


# =========================
# تشخیص لینک
# =========================

def extract_url(text):

    if not text:
        return None

    pattern = r'https?://[^\s]+'

    match = re.search(pattern, text)

    if not match:
        return None

    return match.group(0).strip()


# =========================
# اسم فایل
# =========================

def get_filename_from_url(url):

    try:
        path = urlparse(url).path

        filename = os.path.basename(
            unquote(path)
        )

        if filename and "." in filename:
            return filename

    except Exception:
        pass

    return None


# =========================
# دانلود معمولی
# =========================

def download_normal(url):

    response = requests.get(
        url,
        stream=True,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    content_length = response.headers.get(
        "Content-Length"
    )

    if content_length:

        try:
            if int(content_length) > MAX_FILE_SIZE:
                raise Exception(
                    "حجم فایل بیشتر از حد مجاز است."
                )
        except ValueError:
            pass

    filename = get_filename_from_url(url)

    if not filename:
        filename = "audio.mp3"

    filename = os.path.basename(filename)

    output = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_{filename}"
    )

    total = 0

    with open(output, "wb") as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 256
        ):

            if not chunk:
                continue

            total += len(chunk)

            if total > MAX_FILE_SIZE:
                f.close()

                try:
                    os.remove(output)
                except:
                    pass

                raise Exception(
                    "حجم فایل بیشتر از حد مجاز است."
                )

            f.write(chunk)

    return output


# =========================
# دانلود Google Drive
# =========================

def download_google_drive(url):

    output = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}.mp3"
    )

    result = gdown.download(
        url,
        output,
        quiet=True
    )

    if not result or not os.path.exists(output):
        raise Exception(
            "دانلود از Google Drive انجام نشد."
        )

    if os.path.getsize(output) > MAX_FILE_SIZE:

        try:
            os.remove(output)
        except:
            pass

        raise Exception(
            "حجم فایل بیشتر از حد مجاز است."
        )

    return output


# =========================
# دانلود
# =========================

def download_file(url):

    if "drive.google.com" in url:

        return download_google_drive(url)

    return download_normal(url)


# =========================
# اصلاح متادیتا
# =========================

def set_metadata(
    file_path,
    title,
    artist
):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    # MP3
    if extension == ".mp3":

        try:

            try:
                tags = ID3(file_path)

            except Exception:
                tags = ID3()

            tags.delall("TIT2")
            tags.delall("TPE1")

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

            tags.save(file_path)

            return

        except Exception as e:
            print(
                "خطا در متادیتای MP3:",
                e
            )

    # سایر فرمت‌ها
    try:

        audio = MutagenFile(
            file_path,
            easy=True
        )

        if audio is not None:

            audio["title"] = [title]
            audio["artist"] = [artist]

            audio.save()

    except Exception as e:

        print(
            "خطا در متادیتا:",
            e
        )


# =========================
# تغییر نام فایل
# =========================

def rename_file(
    file_path,
    title
):

    extension = os.path.splitext(
        file_path
    )[1]

    safe_title = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        title
    ).strip()

    if not safe_title:
        safe_title = "audio"

    new_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_{safe_title}{extension}"
    )

    os.rename(
        file_path,
        new_path
    )

    return new_path


# =========================
# گرفتن Message ID
# =========================

def extract_message_id(result):

    if result is None:
        return None

    # اگر خود result عدد باشد
    if isinstance(result, int):
        return result

    # دیکشنری
    if isinstance(result, dict):

        for key in (
            "message_id",
            "id",
            "messageId"
        ):

            if key in result:
                return result[key]

        # بعضی پاسخ‌ها ممکن است message داخل result داشته باشند
        for key in (
            "message",
            "data",
            "result"
        ):

            if key in result:

                value = extract_message_id(
                    result[key]
                )

                if value is not None:
                    return value

    # آبجکت
    for attr in (
        "message_id",
        "id",
        "messageId"
    ):

        try:

            value = getattr(
                result,
                attr,
                None
            )

            if value is not None:
                return value

        except:
            pass

    # اگر داخل message باشد
    for attr in (
        "message",
        "data",
        "result"
    ):

        try:

            value = getattr(
                result,
                attr,
                None
            )

            if value is not None:

                message_id = extract_message_id(
                    value
                )

                if message_id is not None:
                    return message_id

        except:
            pass

    return None


# =========================
# ارسال به کاربران دیگر
# =========================

async def forward_to_users(
    from_chat_id,
    message_id
):

    if message_id is None:
        print(
            "Message ID پیدا نشد؛ فوروارد انجام نشد."
        )
        return

    users = load_users()

    for user_id in users:

        user_id = str(user_id)

        # درخواست‌کننده دوباره فایل نگیرد
        if user_id == str(from_chat_id):
            continue

        try:

            await bot.forward_message(
                from_chat_id=str(from_chat_id),
                message_id=message_id,
                to_chat_id=user_id
            )

            print(
                f"فایل برای {user_id} ارسال شد."
            )

        except Exception as e:

            print(
                f"خطا برای {user_id}: {e}"
            )


# =========================
# پردازش فایل
# =========================

async def process_audio(
    message,
    send_type
):

    chat_id = str(
        message.chat_id
    )

    data = user_data.get(
        chat_id
    )

    if not data:
        return

    url = data["url"]
    title = data["title"]
    artist = data["artist"]

    file_path = None

    try:

        # دانلود
        file_path = download_file(
            url
        )

        # متادیتا
        set_metadata(
            file_path,
            title,
            artist
        )

        # تغییر نام
        file_path = rename_file(
            file_path,
            title
        )

        caption = CHANNEL_TAG

        # =====================
        # ارسال آهنگ
        # =====================

        if send_type == "music":

            result = await bot.send_music(
                chat_id=chat_id,
                path=file_path,
                text=caption,
                file_name=os.path.basename(
                    file_path
                )
            )

        # =====================
        # ارسال ویس
        # =====================

        elif send_type == "voice":

            result = await bot.send_voice(
                chat_id=chat_id,
                path=file_path,
                text=caption,
                file_name=os.path.basename(
                    file_path
                )
            )

        else:
            return

        # گرفتن ID پیام
        message_id = extract_message_id(
            result
        )

        print(
            "Message ID:",
            message_id
        )

        # ارسال برای بقیه کاربران
        await forward_to_users(
            chat_id,
            message_id
        )

    except Exception as e:

        print(
            "ERROR:",
            e
        )

        # فقط در صورتی که پردازش لینک انجام شده
        # به کاربر خطا می‌فرستیم
        try:

            await message.reply(
                "❌ ارسال فایل انجام نشد."
            )

        except:
            pass

    finally:

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(file_path)
            except:
                pass

        # پاک کردن وضعیت کاربر
        user_data.pop(
            chat_id,
            None
        )


# =========================
# Handler اصلی
# =========================

@bot.on_message()
async def handler(
    message: Message
):

    chat_id = str(
        message.chat_id
    )

    text = getattr(
        message,
        "text",
        None
    )

    if text is None:
        text = ""

    text = text.strip()

    # =========================
    # ثبت کاربر
    # =========================

    register_user(
        chat_id
    )

    # =========================
    # START
    # =========================

    if text.lower() == "/start":

        user_data.pop(
            chat_id,
            None
        )

        await message.reply(
            "🎵 سلام!\n\n"
            "لینک فایل صوتی را ارسال کن."
        )

        return

    # =========================
    # انتخاب آهنگ
    # =========================

    if text == "🎵 آهنگ":

        data = user_data.get(
            chat_id
        )

        if not data:
            return

        await process_audio(
            message,
            "music"
        )

        return

    # =========================
    # انتخاب ویس
    # =========================

    if text == "🎤 ویس":

        data = user_data.get(
            chat_id
        )

        if not data:
            return

        await process_audio(
            message,
            "voice"
        )

        return

    # =========================
    # گرفتن عنوان آهنگ
    # =========================

    if chat_id in user_data:

        data = user_data[chat_id]

        if data["step"] == "title":

            # فقط متن عنوان
            if not text:
                return

            data["title"] = text
            data["step"] = "artist"

            await message.reply(
                "🎤 اسم خواننده را بفرست:"
            )

            return

        # =====================
        # گرفتن خواننده
        # =====================

        if data["step"] == "artist":

            if not text:
                return

            data["artist"] = text
            data["step"] = "type"

            await message.reply(
                "نوع ارسال را انتخاب کن:",
                chat_keypad=type_keyboard()
            )

            return

    # =========================
    # دریافت لینک
    # =========================

    url = extract_url(
        text
    )

    if url:

        user_data[chat_id] = {
            "step": "title",
            "url": url,
            "title": "",
            "artist": ""
        }

        await message.reply(
            "🎵 اسم آهنگ را بفرست:"
        )

        return

    # =========================
    # هر چیز دیگری:
    # هیچ پاسخی نده
    # =========================

    return


# =========================
# اجرا
# =========================

print("🤖 ربات اجرا شد...")

bot.run()
