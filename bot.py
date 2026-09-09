import os
import re
import uuid
import mimetypes
import requests
import gdown

from urllib.parse import urlparse, unquote
from rubka import Robot, Message


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CDIBFG0LOWKACQPCLOMUZYMXHATMXOPJXNOZEJVDBLAGQYTOWBOQRTZWGHZPQTLS"

DOWNLOAD_FOLDER = "./downloads"

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


# =========================================================
# ساخت پوشه دانلود
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
#
# user_data[chat_id] = {
#     "url": "...",
# }
# =========================================================

user_data = {}


# =========================================================
# کیبورد اصلی
# =========================================================

def get_audio_keyboard():

    return {
        "rows": [
            {
                "buttons": [
                    {
                        "id": "music",
                        "type": "Simple",
                        "button_text": "🎵 آهنگ"
                    },
                    {
                        "id": "voice",
                        "type": "Simple",
                        "button_text": "🎤 ویس"
                    }
                ]
            }
        ]
    }


# =========================================================
# تشخیص لینک
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

    url = urls[0].strip()

    # حذف علائم احتمالی انتهای لینک
    url = url.rstrip('،,؛;.!؟)(')

    return url


# =========================================================
# تشخیص پسوند فایل
# =========================================================

def get_extension_from_url(url):

    try:
        path = urlparse(url).path
        filename = os.path.basename(path)
        filename = unquote(filename)

        ext = os.path.splitext(filename)[1].lower()

        if ext:
            return ext

    except Exception:
        pass

    return ""


# =========================================================
# تشخیص فایل صوتی
# =========================================================

def is_audio_file(path, content_type=""):

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

    ext = os.path.splitext(path)[1].lower()

    if ext in audio_extensions:
        return True

    if content_type:
        content_type = content_type.lower()

        if content_type.startswith("audio/"):
            return True

    return False


# =========================================================
# اسم امن برای فایل
# =========================================================

def safe_filename(filename):

    filename = unquote(filename)

    filename = os.path.basename(filename)

    filename = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        filename
    )

    if not filename:
        filename = "audio"

    return filename


# =========================================================
# دانلود فایل معمولی
# =========================================================

def download_normal_file(url):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Linux; Android 14) "
            "AppleWebKit/537.36 "
            "Chrome/130 Safari/537.36"
        )
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
    ).lower()

    # اسم از URL
    original_name = ""

    try:
        original_name = os.path.basename(
            urlparse(response.url).path
        )
        original_name = unquote(original_name)
    except Exception:
        pass

    original_name = safe_filename(original_name)

    # اگر اسم قابل استفاده نبود
    if (
        not original_name
        or original_name in [".", ".."]
        or "." not in original_name
    ):

        ext = ""

        if content_type:
            ext = mimetypes.guess_extension(
                content_type.split(";")[0].strip()
            ) or ""

        if not ext:
            ext = get_extension_from_url(
                response.url
            )

        if not ext:
            ext = ".mp3"

        original_name = "audio" + ext

    # اسم یکتا
    unique_name = (
        f"{uuid.uuid4().hex[:8]}_{original_name}"
    )

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        unique_name
    )

    total_size = 0

    content_length = response.headers.get(
        "content-length"
    )

    if content_length:

        try:
            if int(content_length) > MAX_FILE_SIZE:
                raise Exception(
                    "حجم فایل بیشتر از 50 مگابایت است."
                )
        except ValueError:
            pass

    # دانلود
    with open(output_path, "wb") as file:

        for chunk in response.iter_content(
            chunk_size=64 * 1024
        ):

            if not chunk:
                continue

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:

                file.close()

                try:
                    os.remove(output_path)
                except Exception:
                    pass

                raise Exception(
                    "حجم فایل بیشتر از 50 مگابایت است."
                )

            file.write(chunk)

    return output_path, content_type


# =========================================================
# دانلود Google Drive
# =========================================================

def download_google_drive(url):

    filename = f"drive_{uuid.uuid4().hex[:8]}.mp3"

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
            "دانلود فایل از Google Drive ناموفق بود."
        )

    if not os.path.exists(output_path):
        raise Exception(
            "فایل Google Drive پیدا نشد."
        )

    size = os.path.getsize(output_path)

    if size > MAX_FILE_SIZE:

        os.remove(output_path)

        raise Exception(
            "حجم فایل بیشتر از 50 مگابایت است."
        )

    return output_path, "audio/mpeg"


# =========================================================
# دانلود فایل
# =========================================================

def download_file(url):

    lower_url = url.lower()

    if (
        "drive.google.com" in lower_url
        or "docs.google.com" in lower_url
    ):

        return download_google_drive(url)

    return download_normal_file(url)


# =========================================================
# شروع ربات
# =========================================================

@bot.on_message()
async def handle_message(
    bot: Robot,
    message: Message
):

    try:

        text = message.text

        if not text:
            return

        text = text.strip()

        print(
            f"📩 پیام جدید: {text}"
        )

        chat_id = message.chat_id


        # =================================================
        # انتخاب آهنگ
        # =================================================

        if text == "🎵 آهنگ":

            await process_audio(
                bot,
                message,
                "music"
            )

            return


        # =================================================
        # انتخاب ویس
        # =================================================

        if text == "🎤 ویس":

            await process_audio(
                bot,
                message,
                "voice"
            )

            return


        # =================================================
        # لغو
        # =================================================

        if text == "❌ لغو":

            if chat_id in user_data:
                del user_data[chat_id]

            await message.reply(
                "❌ عملیات لغو شد."
            )

            return


        # =================================================
        # لینک
        # =================================================

        url = extract_url(text)

        if not url:

            await message.reply(
                "👋 سلام!\n\n"
                "🔗 لینک فایل صوتی را برای من بفرست."
            )

            return


        # ذخیره لینک
        user_data[chat_id] = {
            "url": url
        }


        # =================================================
        # نمایش دکمه‌ها
        # =================================================

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🔗 لینک دریافت شد.\n\n"
                "حالا نوع ارسال فایل را انتخاب کن:"
            ),
            chat_keypad=get_audio_keyboard(),
            chat_keypad_type="New"
        )


        print(
            f"🔗 لینک ذخیره شد: {url}"
        )


    except Exception as e:

        print(
            "❌ ERROR:",
            repr(e)
        )

        try:

            await message.reply(
                f"❌ خطا:\n{str(e)}"
            )

        except Exception:
            pass


# =========================================================
# پردازش آهنگ / ویس
# =========================================================

async def process_audio(
    bot,
    message,
    mode
):

    chat_id = message.chat_id


    # =====================================================
    # آیا لینک داریم؟
    # =====================================================

    if chat_id not in user_data:

        await message.reply(
            "❌ اول یک لینک فایل صوتی بفرست."
        )

        return


    url = user_data[chat_id]["url"]


    # =====================================================
    # پیام دانلود
    # =====================================================

    status_message = await message.reply(
        "⏳ در حال دانلود فایل..."
    )


    output_path = None


    try:

        print(
            f"⬇️ Downloading: {url}"
        )


        # =================================================
        # دانلود
        # =================================================

        output_path, content_type = download_file(
            url
        )


        print(
            f"✅ Downloaded: {output_path}"
        )


        # =================================================
        # بررسی فایل
        # =================================================

        if not os.path.exists(output_path):

            raise Exception(
                "فایل دانلود نشد."
            )


        file_size = os.path.getsize(
            output_path
        )


        if file_size == 0:

            raise Exception(
                "فایل دانلودشده خالی است."
            )


        # =================================================
        # تشخیص صوت
        # =================================================

        if not is_audio_file(
            output_path,
            content_type
        ):

            # بعضی لینک‌ها content-type اشتباه دارند
            # پس پسوند را هم بررسی می‌کنیم

            ext = os.path.splitext(
                output_path
            )[1].lower()

            audio_exts = {
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

            if ext not in audio_exts:

                raise Exception(
                    "فایلی که لینک آن را فرستادی "
                    "فایل صوتی قابل تشخیص نیست."
                )


        # =================================================
        # نام فایل
        # =================================================

        filename = os.path.basename(
            output_path
        )


        await message.reply(
            "📤 فایل دانلود شد.\n"
            "⏳ در حال ارسال..."
        )


        # =================================================
        # ارسال به عنوان آهنگ
        # =================================================

        if mode == "music":

            print(
                "🎵 Sending as music..."
            )

            await bot.send_music(
                chat_id=chat_id,
                path=output_path,
                text=f"🎵 {filename}",
                file_name=filename
            )


        # =================================================
        # ارسال به عنوان ویس
        # =================================================

        elif mode == "voice":

            print(
                "🎤 Sending as voice..."
            )

            await bot.send_voice(
                chat_id=chat_id,
                path=output_path,
                text=f"🎤 {filename}",
                file_name=filename
            )


        # =================================================
        # حذف اطلاعات کاربر
        # =================================================

        if chat_id in user_data:
            del user_data[chat_id]


        # =================================================
        # حذف فایل
        # =================================================

        if output_path and os.path.exists(
            output_path
        ):

            os.remove(output_path)


        await message.reply(
            "✅ فایل با موفقیت ارسال شد."
        )


        print(
            "✅ Done."
        )


    except Exception as e:

        print(
            "❌ PROCESS ERROR:",
            repr(e)
        )


        # حذف فایل در صورت خطا
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
            "❌ ارسال فایل انجام نشد.\n\n"
            f"جزئیات خطا:\n{str(e)}"
        )


# =========================================================
# اجرای ربات
# =========================================================

if __name__ == "__main__":

    print("=" * 50)

    print(
        "🤖 Audio Downloader Bot"
    )

    print(
        "📡 Rubka Bot"
    )

    print(
        "⏳ Bot is running..."
    )

    print("=" * 50)

    bot.run()
