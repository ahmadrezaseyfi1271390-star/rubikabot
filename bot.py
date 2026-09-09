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


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CDIBFG0LOWKACQPCLOMUZYMXHATMXOPJXNOZEJVDBLAGQYTOWBOQRTZWGHZPQTLS"

# آیدی عددی صاحب ربات
OWNER_CHAT_ID = "آیدی_عددی_خودت"

DOWNLOAD_FOLDER = "./downloads"
USERS_FILE = "./users.json"

MAX_FILE_SIZE = 50 * 1024 * 1024

CHANNEL_TAG = "@Black_list_remix"


# =========================================================
# ساخت پوشه‌ها
# =========================================================

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# ربات
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# اطلاعات موقت کاربران
#
# {
#   chat_id: {
#       "step": "...",
#       "url": "...",
#       "title": "...",
#       "artist": "..."
#   }
# }
# =========================================================

user_data = {}


# =========================================================
# کاربران
# =========================================================

def load_users():

    if not os.path.exists(
        USERS_FILE
    ):
        return []

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(
                data,
                list
            ):
                return data

    except Exception as e:

        print(
            "❌ users.json:",
            e
        )

    return []


def save_users(users):

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

    chat_id = str(
        chat_id
    )

    users = load_users()

    if chat_id not in users:

        users.append(
            chat_id
        )

        save_users(
            users
        )

        print(
            f"👤 کاربر ثبت شد: {chat_id}"
        )


# =========================================================
# کیبورد کوچک
# =========================================================

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


# =========================================================
# استخراج لینک
# =========================================================

def extract_url(text):

    if not text:
        return None

    urls = re.findall(
        r'https?://[^\s]+',
        text
    )

    if not urls:
        return None

    return urls[0].rstrip(
        "،,؛;.!؟)("
    )


# =========================================================
# نام فایل امن
# =========================================================

def safe_filename(filename):

    filename = unquote(
        filename
    )

    filename = os.path.basename(
        filename
    )

    filename = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        filename
    )

    if not filename:
        filename = "audio"

    return filename


# =========================================================
# تشخیص صوت
# =========================================================

def is_audio_file(
    path,
    content_type=""
):

    audio_extensions = {
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".oga",
        ".m4a",
        ".opus",
        ".wma",
        ".webm"
    }

    ext = os.path.splitext(
        path
    )[1].lower()

    if ext in audio_extensions:
        return True

    if content_type:

        if content_type.lower().startswith(
            "audio/"
        ):
            return True

    return False


# =========================================================
# دانلود فایل معمولی
# =========================================================

def download_normal(url):

    headers = {
        "User-Agent":
        "Mozilla/5.0 "
        "(Linux; Android 14) "
        "AppleWebKit/537.36 "
        "Chrome/130 Safari/537.36"
    }

    response = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=(15, 120),
        allow_redirects=True
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        ""
    )

    filename = os.path.basename(
        urlparse(
            response.url
        ).path
    )

    filename = safe_filename(
        filename
    )

    if not filename or "." not in filename:

        ext = mimetypes.guess_extension(
            content_type.split(";")[0]
        )

        if not ext:
            ext = ".mp3"

        filename = (
            filename or "audio"
        ) + ext

    filename = (
        uuid.uuid4().hex[:8]
        + "_"
        + filename
    )

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        filename
    )

    total = 0

    with open(
        output_path,
        "wb"
    ) as f:

        for chunk in response.iter_content(
            chunk_size=64 * 1024
        ):

            if not chunk:
                continue

            total += len(chunk)

            if total > MAX_FILE_SIZE:

                f.close()

                if os.path.exists(
                    output_path
                ):
                    os.remove(
                        output_path
                    )

                raise Exception(
                    "حجم فایل بیشتر از 50 مگابایت است."
                )

            f.write(chunk)

    return (
        output_path,
        content_type
    )


# =========================================================
# Google Drive
# =========================================================

def download_google_drive(url):

    filename = (
        "drive_"
        + uuid.uuid4().hex[:8]
        + ".mp3"
    )

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        filename
    )

    result = gdown.download(
        url,
        output_path,
        quiet=True,
        fuzzy=True
    )

    if not result:
        raise Exception(
            "دانلود Google Drive ناموفق بود."
        )

    if not os.path.exists(
        output_path
    ):
        raise Exception(
            "فایل Google Drive پیدا نشد."
        )

    if os.path.getsize(
        output_path
    ) > MAX_FILE_SIZE:

        os.remove(
            output_path
        )

        raise Exception(
            "حجم فایل بیشتر از 50 مگابایت است."
        )

    return (
        output_path,
        "audio/mpeg"
    )


# =========================================================
# دانلود
# =========================================================

def download_file(url):

    lower = url.lower()

    if (
        "drive.google.com" in lower
        or
        "docs.google.com" in lower
    ):

        return download_google_drive(
            url
        )

    return download_normal(
        url
    )


# =========================================================
# تغییر متادیتای آهنگ
# =========================================================

def edit_audio_metadata(
    path,
    title,
    artist
):

    ext = os.path.splitext(
        path
    )[1].lower()

    # -----------------------------------------------------
    # MP3
    # -----------------------------------------------------

    if ext == ".mp3":

        try:

            try:
                tags = ID3(path)
            except Exception:
                tags = ID3()

            tags.delall(
                "TIT2"
            )

            tags.delall(
                "TPE1"
            )

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

            tags.save(
                path
            )

            print(
                "✅ متادیتای MP3 تغییر کرد."
            )

            return True

        except Exception as e:

            print(
                "⚠️ خطای ID3:",
                e
            )


    # -----------------------------------------------------
    # سایر فرمت‌های پشتیبانی‌شده توسط Mutagen
    # -----------------------------------------------------

    try:

        audio = MutagenFile(
            path,
            easy=True
        )

        if audio is None:

            print(
                "⚠️ این فرمت متادیتای قابل ویرایش ندارد."
            )

            return False

        if audio.tags is None:

            audio.add_tags()

        audio["title"] = [
            title
        ]

        audio["artist"] = [
            artist
        ]

        audio.save()

        print(
            "✅ متادیتای فایل تغییر کرد."
        )

        return True

    except Exception as e:

        print(
            "⚠️ خطای متادیتا:",
            e
        )

        return False


# =========================================================
# تغییر نام فایل
# =========================================================

def rename_audio_file(
    path,
    title
):

    ext = os.path.splitext(
        path
    )[1]

    safe_title = safe_filename(
        title
    )

    new_name = (
        safe_title
        + ext
    )

    new_path = os.path.join(
        DOWNLOAD_FOLDER,
        new_name
    )

    # اگر وجود داشت، اسم یکتا
    if os.path.exists(
        new_path
    ):

        new_name = (
            safe_title
            + "_"
            + uuid.uuid4().hex[:6]
            + ext
        )

        new_path = os.path.join(
            DOWNLOAD_FOLDER,
            new_name
        )

    os.rename(
        path,
        new_path
    )

    return new_path


# =========================================================
# گرفتن ID پیام ارسال‌شده
# =========================================================

def extract_message_id(
    result
):

    if result is None:
        return None

    if isinstance(
        result,
        str
    ):
        return result

    if isinstance(
        result,
        dict
    ):

        for key in [
            "message_id",
            "msg_id",
            "id"
        ]:

            if key in result:
                return str(
                    result[key]
                )

        nested = result.get(
            "result"
        )

        if isinstance(
            nested,
            dict
        ):

            for key in [
                "message_id",
                "msg_id",
                "id"
            ]:

                if key in nested:

                    return str(
                        nested[key]
                    )

    return None


# =========================================================
# ارسال به کاربران
# =========================================================

async def forward_to_users(
    from_chat_id,
    message_id
):

    if not message_id:
        print(
            "⚠️ message_id موجود نیست."
        )
        return

    users = load_users()

    print(
        f"📢 ارسال به {len(users)} کاربر..."
    )

    for target_chat_id in users:

        target_chat_id = str(
            target_chat_id
        )

        # فرستنده اصلی دوباره دریافت نکند
        if target_chat_id == str(
            from_chat_id
        ):
            continue

        try:

            await bot.forward_message(
                from_chat_id=str(
                    from_chat_id
                ),
                message_id=str(
                    message_id
                ),
                to_chat_id=target_chat_id
            )

            print(
                f"✅ فوروارد شد → "
                f"{target_chat_id}"
            )

        except Exception as e:

            print(
                f"⚠️ فوروارد نشد → "
                f"{target_chat_id}:",
                e
            )


# =========================================================
# پردازش فایل
# =========================================================

async def process_audio(
    message,
    mode
):

    chat_id = str(
        message.chat_id
    )

    if chat_id not in user_data:

        await message.reply(
            "❌ اطلاعات فایل پیدا نشد.\n"
            "لطفاً دوباره لینک را بفرست."
        )

        return

    data = user_data[
        chat_id
    ]

    url = data["url"]
    title = data["title"]
    artist = data["artist"]

    output_path = None

    try:

        await message.reply(
            "⏳ در حال دانلود فایل..."
        )

        # -------------------------------------------------
        # دانلود
        # -------------------------------------------------

        output_path, content_type = (
            download_file(
                url
            )
        )

        if not os.path.exists(
            output_path
        ):

            raise Exception(
                "دانلود فایل ناموفق بود."
            )

        # -------------------------------------------------
        # بررسی صوت
        # -------------------------------------------------

        if not is_audio_file(
            output_path,
            content_type
        ):

            raise Exception(
                "لینک، فایل صوتی قابل تشخیص نیست."
            )

        # -------------------------------------------------
        # تغییر متادیتا
        # -------------------------------------------------

        await message.reply(
            "📝 در حال ویرایش نام آهنگ و خواننده..."
        )

        edit_audio_metadata(
            output_path,
            title,
            artist
        )

        # -------------------------------------------------
        # تغییر نام فایل
        # -------------------------------------------------

        try:

            output_path = rename_audio_file(
                output_path,
                title
            )

        except Exception as e:

            print(
                "⚠️ تغییر نام انجام نشد:",
                e
            )

        filename = os.path.basename(
            output_path
        )

        # -------------------------------------------------
        # کپشن
        # -------------------------------------------------

        caption = CHANNEL_TAG

        await message.reply(
            "📤 فایل آماده شد.\n"
            "⏳ در حال ارسال..."
        )

        # -------------------------------------------------
        # ارسال آهنگ
        # -------------------------------------------------

        if mode == "music":

            print(
                "🎵 ارسال Music"
            )

            result = await bot.send_music(
                chat_id=chat_id,
                path=output_path,
                text=caption,
                file_name=filename
            )

        # -------------------------------------------------
        # ارسال ویس
        # -------------------------------------------------

        else:

            print(
                "🎤 ارسال Voice"
            )

            result = await bot.send_voice(
                chat_id=chat_id,
                path=output_path,
                text=caption,
                file_name=filename
            )

        print(
            "📦 نتیجه ارسال:",
            result
        )

        # -------------------------------------------------
        # گرفتن Message ID
        # -------------------------------------------------

        message_id = extract_message_id(
            result
        )

        # -------------------------------------------------
        # فوروارد به کاربران
        # -------------------------------------------------

        if message_id:

            await forward_to_users(
                chat_id,
                message_id
            )

        # -------------------------------------------------
        # پاک کردن اطلاعات
        # -------------------------------------------------

        if chat_id in user_data:

            del user_data[
                chat_id
            ]

        # -------------------------------------------------
        # حذف فایل
        # -------------------------------------------------

        if os.path.exists(
            output_path
        ):

            os.remove(
                output_path
            )

        await message.reply(
            "✅ انجام شد!\n\n"
            f"🎵 {title}\n"
            f"🎤 {artist}\n\n"
            f"{CHANNEL_TAG}"
        )

    except Exception as e:

        print(
            "❌ PROCESS ERROR:",
            repr(e)
        )

        if output_path:

            try:

                if os.path.exists(
                    output_path
                ):

                    os.remove(
                        output_path
                    )

            except Exception:
                pass

        await message.reply(
            "❌ خطا هنگام پردازش:\n\n"
            f"{str(e)}"
        )


# =========================================================
# دریافت پیام
# =========================================================

@bot.on_message()
async def handle_message(
    bot,
    message
):

    try:

        text = message.text

        if not text:
            return

        text = text.strip()

        chat_id = str(
            message.chat_id
        )

        print(
            f"📩 {chat_id}: {text}"
        )

        # -------------------------------------------------
        # ثبت کاربر
        # -------------------------------------------------

        register_user(
            chat_id
        )

        # -------------------------------------------------
        # انتخاب آهنگ
        # -------------------------------------------------

        if text == "🎵 آهنگ":

            if chat_id not in user_data:

                await message.reply(
                    "❌ اول لینک آهنگ را بفرست."
                )

                return

            await process_audio(
                message,
                "music"
            )

            return

        # -------------------------------------------------
        # انتخاب ویس
        # -------------------------------------------------

        if text == "🎤 ویس":

            if chat_id not in user_data:

                await message.reply(
                    "❌ اول لینک آهنگ را بفرست."
                )

                return

            await process_audio(
                message,
                "voice"
            )

            return

        # -------------------------------------------------
        # اگر کاربر در مرحله اسم آهنگ است
        # -------------------------------------------------

        if (
            chat_id in user_data
            and
            user_data[chat_id]["step"]
            == "title"
        ):

            user_data[
                chat_id
            ]["title"] = text

            user_data[
                chat_id
            ]["step"] = "artist"

            await message.reply(
                "🎤 حالا اسم خواننده را بفرست:"
            )

            return

        # -------------------------------------------------
        # اگر کاربر در مرحله اسم خواننده است
        # -------------------------------------------------

        if (
            chat_id in user_data
            and
            user_data[chat_id]["step"]
            == "artist"
        ):

            user_data[
                chat_id
            ]["artist"] = text

            user_data[
                chat_id
            ]["step"] = "type"

            await message.reply_keypad(
                "🎧 نوع ارسال را انتخاب کن:",
                type_keyboard()
            )

            return

        # -------------------------------------------------
        # لینک جدید
        # -------------------------------------------------

        url = extract_url(
            text
        )

        if not url:

            await message.reply(
                "👋 سلام!\n\n"
                "🔗 لینک فایل صوتی را بفرست."
            )

            return

        # -------------------------------------------------
        # شروع فرآیند
        # -------------------------------------------------

        user_data[
            chat_id
        ] = {
            "step": "title",
            "url": url,
            "title": "",
            "artist": ""
        }

        await message.reply(
            "🔗 لینک دریافت شد.\n\n"
            "🎵 اسم آهنگ را بفرست:"
        )

    except Exception as e:

        print(
            "❌ HANDLER ERROR:",
            repr(e)
        )

        try:

            await message.reply(
                f"❌ خطا:\n{str(e)}"
            )

        except Exception:
            pass


# =========================================================
# اجرای ربات
# =========================================================

if __name__ == "__main__":

    print(
        "===================================="
    )

    print(
        "🎧 Black List Remix Downloader"
    )

    print(
        "📡 Rubka 8.1.10"
    )

    print(
        "===================================="
    )

    print(
        "🤖 Bot is running..."
    )

    bot.run()
