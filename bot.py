import os
import re
import json
import uuid
import requests
import gdown

from urllib.parse import urlparse, unquote

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder

from mutagen import File as MutagenFile
from mutagen.id3 import (
    ID3,
    TIT2,
    TPE1,
    APIC
)


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# کپشن آهنگ
CAPTION = "@Black_list_remix"

# حداکثر حجم فایل: 200 مگابایت
MAX_FILE_SIZE = 200 * 1024 * 1024

DOWNLOAD_FOLDER = "./downloads"

USERS_FILE = "./users.json"


os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# ساخت ربات
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# وضعیت کاربران
# =========================================================

user_data = {}


# =========================================================
# کاربران
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
            "خطا در خواندن users.json:",
            e
        )

    return []


def save_users(users):

    try:

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

    except Exception as e:

        print(
            "خطا در ذخیره کاربران:",
            e
        )


def register_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users.append(
            chat_id
        )

        save_users(
            users
        )

        print(
            "کاربر جدید:",
            chat_id
        )


# =========================================================
# کیبورد انتخاب نوع ارسال
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
# پیدا کردن لینک
# =========================================================

def extract_url(text):

    if not text:
        return None

    match = re.search(
        r"https?://[^\s]+",
        text
    )

    if not match:
        return None

    url = match.group(0).strip()

    url = url.rstrip(
        ".,!?،؛)]}"
    )

    return url


# =========================================================
# نام فایل از لینک
# =========================================================

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


# =========================================================
# دانلود فایل معمولی
# =========================================================

def download_normal(url):

    response = requests.get(
        url,
        stream=True,
        timeout=120,
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
                    "حجم فایل بیشتر از 200 مگابایت است."
                )

        except ValueError:
            pass

    filename = get_filename_from_url(
        url
    )

    if not filename:
        filename = "audio.mp3"

    filename = os.path.basename(
        filename
    )

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_{filename}"
    )

    total_size = 0

    with open(
        output_path,
        "wb"
    ) as file:

        for chunk in response.iter_content(
            chunk_size=256 * 1024
        ):

            if not chunk:
                continue

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:

                file.close()

                try:
                    os.remove(
                        output_path
                    )
                except:
                    pass

                raise Exception(
                    "حجم فایل بیشتر از 200 مگابایت است."
                )

            file.write(
                chunk
            )

    return output_path


# =========================================================
# دانلود Google Drive
# =========================================================

def download_google_drive(url):

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}.mp3"
    )

    result = gdown.download(
        url,
        output_path,
        quiet=True
    )

    if not result or not os.path.exists(
        output_path
    ):

        raise Exception(
            "دانلود از Google Drive انجام نشد."
        )

    if os.path.getsize(
        output_path
    ) > MAX_FILE_SIZE:

        try:
            os.remove(
                output_path
            )
        except:
            pass

        raise Exception(
            "حجم فایل بیشتر از 200 مگابایت است."
        )

    return output_path


# =========================================================
# دانلود
# =========================================================

def download_file(url):

    if "drive.google.com" in url:

        return download_google_drive(
            url
        )

    return download_normal(
        url
    )


# =========================================================
# دانلود عکس کاور
# =========================================================

def download_cover(message):

    """
    سعی می‌کنیم عکس ارسال‌شده را از پیام دریافت کنیم.
    """

    # -----------------------------------------------------
    # حالت‌های مختلفی که ممکن است Rubka عکس را در پیام
    # قرار دهد
    # -----------------------------------------------------

    photo = getattr(
        message,
        "photo",
        None
    )

    if photo is None:

        photo = getattr(
            message,
            "image",
            None
        )

    if photo is None:

        return None

    # -----------------------------------------------------
    # اگر photo لیست باشد، بزرگ‌ترین عکس را انتخاب می‌کنیم
    # -----------------------------------------------------

    if isinstance(
        photo,
        list
    ):

        if len(photo) == 0:
            return None

        photo = photo[-1]

    # -----------------------------------------------------
    # پیدا کردن file_id
    # -----------------------------------------------------

    file_id = None

    if isinstance(
        photo,
        dict
    ):

        file_id = (
            photo.get("file_id")
            or photo.get("fileId")
            or photo.get("id")
        )

    else:

        for attr in (
            "file_id",
            "fileId",
            "id"
        ):

            try:

                value = getattr(
                    photo,
                    attr,
                    None
                )

                if value:
                    file_id = value
                    break

            except:
                pass

    if not file_id:
        return None

    # -----------------------------------------------------
    # تلاش برای دریافت فایل
    # -----------------------------------------------------

    try:

        file_info = await bot.get_file(
            file_id
        )

    except Exception as e:

        print(
            "خطا در get_file:",
            e
        )

        return None

    # -----------------------------------------------------
    # این قسمت بسته به نسخه API ممکن است ساختار متفاوتی
    # داشته باشد.
    # -----------------------------------------------------

    file_url = None

    if isinstance(
        file_info,
        dict
    ):

        file_url = (
            file_info.get("download_url")
            or file_info.get("url")
            or file_info.get("file_url")
        )

    else:

        for attr in (
            "download_url",
            "url",
            "file_url"
        ):

            try:

                value = getattr(
                    file_info,
                    attr,
                    None
                )

                if value:
                    file_url = value
                    break

            except:
                pass

    if not file_url:
        return None

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_cover.jpg"
    )

    response = requests.get(
        file_url,
        timeout=60
    )

    response.raise_for_status()

    if len(response.content) > 10 * 1024 * 1024:

        raise Exception(
            "حجم عکس کاور بیشتر از 10 مگابایت است."
        )

    with open(
        output_path,
        "wb"
    ) as f:

        f.write(
            response.content
        )

    return output_path


# =========================================================
# ثبت عنوان و خواننده + کاور
# =========================================================

def set_metadata(
    file_path,
    title,
    artist,
    cover_path=None
):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    # =====================================================
    # MP3
    # =====================================================

    if extension == ".mp3":

        try:

            try:

                tags = ID3(
                    file_path
                )

            except Exception:

                tags = ID3()

            # حذف قبلی
            tags.delall(
                "TIT2"
            )

            tags.delall(
                "TPE1"
            )

            tags.delall(
                "APIC"
            )

            # عنوان
            tags.add(
                TIT2(
                    encoding=3,
                    text=title
                )
            )

            # خواننده
            tags.add(
                TPE1(
                    encoding=3,
                    text=artist
                )
            )

            # کاور
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
                file_path
            )

            print(
                "عنوان، خواننده و کاور ثبت شد."
            )

            return

        except Exception as e:

            print(
                "خطا در metadata MP3:",
                e
            )

    # =====================================================
    # سایر فرمت‌ها
    # =====================================================

    try:

        audio = MutagenFile(
            file_path,
            easy=True
        )

        if audio is not None:

            audio["title"] = [
                title
            ]

            audio["artist"] = [
                artist
            ]

            audio.save()

            print(
                "Metadata ثبت شد."
            )

    except Exception as e:

        print(
            "خطا در metadata:",
            e
        )


# =========================================================
# تغییر نام فایل
# =========================================================

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


# =========================================================
# استخراج Message ID
# =========================================================

def extract_message_id(result):

    if result is None:
        return None

    if isinstance(
        result,
        int
    ):
        return result

    if isinstance(
        result,
        str
    ):

        if result.isdigit():
            return result

    if isinstance(
        result,
        dict
    ):

        for key in (
            "message_id",
            "messageId",
            "id"
        ):

            if key in result:
                return result[key]

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

    for attr in (
        "message_id",
        "messageId",
        "id"
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


# =========================================================
# فوروارد به کاربران
# =========================================================

async def forward_to_users(
    from_chat_id,
    message_id
):

    if message_id is None:

        print(
            "Message ID پیدا نشد."
        )

        return

    users = load_users()

    for user_id in users:

        user_id = str(
            user_id
        )

        # درخواست‌کننده دوباره دریافت نکند
        if user_id == str(
            from_chat_id
        ):
            continue

        try:

            await bot.forward_message(
                from_chat_id=str(
                    from_chat_id
                ),
                message_id=message_id,
                to_chat_id=user_id
            )

            print(
                "فوروارد شد:",
                user_id
            )

        except Exception as e:

            print(
                f"خطا برای {user_id}:",
                e
            )


# =========================================================
# ارسال نهایی آهنگ
# =========================================================

async def send_music_file(
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

    url = data["url"]
    title = data["title"]
    artist = data["artist"]

    file_path = None
    cover_path = data.get(
        "cover_path"
    )

    try:

        print(
            "شروع دانلود آهنگ..."
        )

        # دانلود
        file_path = download_file(
            url
        )

        # متادیتا + کاور
        set_metadata(
            file_path,
            title,
            artist,
            cover_path
        )

        # تغییر نام
        file_path = rename_file(
            file_path,
            title
        )

        # ارسال آهنگ
        result = await bot.send_music(
            chat_id=chat_id,
            path=file_path,
            text=CAPTION,
            file_name=os.path.basename(
                file_path
            )
        )

        print(
            "🎵 آهنگ ارسال شد."
        )

        # Message ID
        message_id = extract_message_id(
            result
        )

        # فوروارد برای کاربران
        await forward_to_users(
            chat_id,
            message_id
        )

    except Exception as e:

        print(
            "خطا در ارسال آهنگ:",
            e
        )

        try:

            await message.reply(
                "❌ ارسال آهنگ انجام نشد."
            )

        except:
            pass

    finally:

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(
                    file_path
                )
            except:
                pass

        if cover_path and os.path.exists(
            cover_path
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
# ارسال ویس
# =========================================================

async def send_voice_file(
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

    url = data["url"]

    file_path = None

    try:

        print(
            "شروع دانلود ویس..."
        )

        # دانلود
        file_path = download_file(
            url
        )

        # -------------------------------------------------
        # برای ویس هیچ metadata و کاوری اعمال نمی‌کنیم
        # -------------------------------------------------

        result = await bot.send_voice(
            chat_id=chat_id,
            path=file_path,
            text=CAPTION,
            file_name=os.path.basename(
                file_path
            )
        )

        print(
            "🎤 ویس ارسال شد."
        )

        message_id = extract_message_id(
            result
        )

        await forward_to_users(
            chat_id,
            message_id
        )

    except Exception as e:

        print(
            "خطا در ارسال ویس:",
            e
        )

        try:

            await message.reply(
                "❌ ارسال ویس انجام نشد."
            )

        except:
            pass

    finally:

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(
                    file_path
                )
            except:
                pass

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# Handler اصلی
# =========================================================

@bot.on_message()
async def handler(
    bot,
    message: Message
):

    try:

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

        # ثبت کاربر
        register_user(
            chat_id
        )

        # =================================================
        # START
        # =================================================

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

        # =================================================
        # دکمه آهنگ
        # =================================================

        if text == "🎵 آهنگ":

            data = user_data.get(
                chat_id
            )

            if not data:
                return

            data["step"] = "cover"

            await message.reply(
                "🖼 لطفاً عکس کاور آهنگ را ارسال کنید:"
            )

            return

        # =================================================
        # دکمه ویس
        # =================================================

        if text == "🎤 ویس":

            data = user_data.get(
                chat_id
            )

            if not data:
                return

            await send_voice_file(
                message
            )

            return

        # =================================================
        # اگر کاربر در مرحله دریافت کاور است
        # =================================================

        if chat_id in user_data:

            data = user_data[
                chat_id
            ]

            if data["step"] == "cover":

                # -----------------------------------------
                # تلاش برای دانلود عکس
                # -----------------------------------------

                cover_path = await download_cover(
                    message
                )

                if not cover_path:

                    # پیام متنی یا فایل غیرعکس:
                    # هیچ پاسخی نده
                    return

                data["cover_path"] = cover_path

                await send_music_file(
                    message
                )

                return

            # =================================================
            # نام آهنگ
            # =================================================

            if data["step"] == "title":

                if not text:
                    return

                # اگر لینک دوباره فرستاده شد
                if extract_url(text):
                    return

                data["title"] = text

                data["step"] = "artist"

                await message.reply(
                    "🎤 اسم خواننده را بفرست:"
                )

                return

            # =================================================
            # نام خواننده
            # =================================================

            if data["step"] == "artist":

                if not text:
                    return

                if extract_url(text):
                    return

                data["artist"] = text

                data["step"] = "type"

                await message.reply(
                    "نوع ارسال را انتخاب کن:",
                    chat_keypad=type_keyboard()
                )

                return

            # =================================================
            # مرحله انتخاب نوع
            # =================================================

            if data["step"] == "type":

                return

        # =================================================
        # دریافت لینک
        # =================================================

        url = extract_url(
            text
        )

        if url:

            user_data[chat_id] = {

                "step": "title",

                "url": url,

                "title": "",

                "artist": "",

                "cover_path": None
            }

            await message.reply(
                "🎵 اسم آهنگ را بفرست:"
            )

            return

        # =================================================
        # هر چیز دیگری = هیچ پاسخ
        # =================================================

        return

    except Exception as e:

        print(
            "❌ ERROR:",
            e
        )


# =========================================================
# اجرای ربات
# =========================================================

print(
    "🤖 Rubika Bot Started..."
)

bot.run()
