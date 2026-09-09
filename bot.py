import os
import re
import json
import uuid
import inspect
import mimetypes
import requests
import gdown

from urllib.parse import urlparse, unquote

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

CAPTION = "@Black_list_remix"

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
                str(x) for x in users
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
            "خطا در ذخیره users.json:",
            e
        )


def register_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users.append(chat_id)

        save_users(users)

        print(
            "کاربر جدید ثبت شد:",
            chat_id
        )


# =========================================================
# کیبورد
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
# پیدا کردن URL
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

    return url.rstrip(
        ".,!?،؛)]}"
    )


# =========================================================
# نام فایل از URL
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

    print(
        "در حال دانلود:",
        url
    )

    response = requests.get(
        url,
        stream=True,
        timeout=180,
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

                raise ValueError(
                    "حجم فایل بیشتر از 200 مگابایت است."
                )

        except ValueError as e:

            if "200" in str(e):

                response.close()

                raise e

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

    try:

        with open(
            output_path,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 256
            ):

                if not chunk:
                    continue

                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:

                    raise ValueError(
                        "حجم فایل بیشتر از 200 مگابایت است."
                    )

                f.write(chunk)

    except Exception:

        if os.path.exists(output_path):

            try:
                os.remove(output_path)
            except Exception:
                pass

        raise

    print(
        "دانلود شد:",
        output_path
    )

    return output_path


# =========================================================
# Google Drive
# =========================================================

def download_google_drive(url):

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}.mp3"
    )

    print(
        "دانلود از Google Drive..."
    )

    result = gdown.download(
        url,
        output_path,
        quiet=True
    )

    if not result or not os.path.exists(
        output_path
    ):

        raise ValueError(
            "دانلود Google Drive ناموفق بود."
        )

    size = os.path.getsize(
        output_path
    )

    if size > MAX_FILE_SIZE:

        try:
            os.remove(output_path)
        except Exception:
            pass

        raise ValueError(
            "حجم فایل بیشتر از 200 مگابایت است."
        )

    return output_path


# =========================================================
# دانلود فایل
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
# پیدا کردن File ID عکس
# =========================================================

def find_file_id(value):

    if value is None:
        return None

    if isinstance(
        value,
        str
    ):

        return value

    if isinstance(
        value,
        dict
    ):

        for key in (
            "file_id",
            "fileId",
            "id"
        ):

            if value.get(key):
                return value[key]

        for key in (
            "file",
            "image",
            "photo",
            "data"
        ):

            if key in value:

                result = find_file_id(
                    value[key]
                )

                if result:
                    return result

    for attr in (
        "file_id",
        "fileId",
        "id"
    ):

        value2 = getattr(
            value,
            attr,
            None
        )

        if value2:
            return value2

    for attr in (
        "file",
        "image",
        "photo",
        "data"
    ):

        value2 = getattr(
            value,
            attr,
            None
        )

        if value2:

            result = find_file_id(
                value2
            )

            if result:
                return result

    return None


# =========================================================
# دریافت اطلاعات فایل از Rubka
# =========================================================

async def call_maybe_async(
    function,
    *args,
    **kwargs
):

    result = function(
        *args,
        **kwargs
    )

    if inspect.isawaitable(result):

        result = await result

    return result


# =========================================================
# دانلود کاور
# =========================================================

async def download_cover(message):

    # طبق ساختار Message در Rubka
    # فایل دریافت‌شده معمولاً در message.file قرار دارد.

    file_object = getattr(
        message,
        "file",
        None
    )

    file_id = find_file_id(
        file_object
    )

    # حالت‌های جایگزین
    if not file_id:

        file_id = find_file_id(
            getattr(
                message,
                "photo",
                None
            )
        )

    if not file_id:

        file_id = find_file_id(
            getattr(
                message,
                "image",
                None
            )
        )

    if not file_id:

        print(
            "File ID عکس پیدا نشد."
        )

        return None

    print(
        "Cover file ID:",
        file_id
    )

    # -----------------------------------------------------
    # تلاش برای دریافت URL
    # -----------------------------------------------------

    if not hasattr(
        bot,
        "get_file"
    ):

        print(
            "این نسخه Rubka متد get_file ندارد."
        )

        return None

    try:

        file_info = await call_maybe_async(
            bot.get_file,
            file_id
        )

    except Exception as e:

        print(
            "خطا در get_file:",
            e
        )

        return None

    print(
        "File info:",
        file_info
    )

    # -----------------------------------------------------
    # استخراج URL
    # -----------------------------------------------------

    file_url = None

    if isinstance(
        file_info,
        str
    ):

        file_url = file_info

    elif isinstance(
        file_info,
        dict
    ):

        for key in (
            "download_url",
            "file_url",
            "url",
            "downloadUrl"
        ):

            if file_info.get(key):

                file_url = file_info[key]
                break

        if not file_url:

            for key in (
                "data",
                "result",
                "file"
            ):

                if key in file_info:

                    file_url = find_url(
                        file_info[key]
                    )

                    if file_url:
                        break

    else:

        for attr in (
            "download_url",
            "file_url",
            "url",
            "downloadUrl"
        ):

            value = getattr(
                file_info,
                attr,
                None
            )

            if value:

                file_url = value
                break

    if not file_url:

        print(
            "URL دانلود عکس پیدا نشد."
        )

        return None

    # -----------------------------------------------------
    # دانلود عکس
    # -----------------------------------------------------

    try:

        response = requests.get(
            file_url,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        if len(response.content) > MAX_COVER_SIZE:

            raise ValueError(
                "حجم کاور بیشتر از 10MB است."
            )

        content_type = (
            response.headers
            .get(
                "Content-Type",
                ""
            )
            .lower()
        )

        extension = ".jpg"

        if "png" in content_type:
            extension = ".png"

        elif "webp" in content_type:
            extension = ".webp"

        elif "jpeg" in content_type:
            extension = ".jpg"

        cover_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"{uuid.uuid4().hex}_cover{extension}"
        )

        with open(
            cover_path,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        print(
            "کاور دانلود شد:",
            cover_path
        )

        return cover_path

    except Exception as e:

        print(
            "خطا در دانلود کاور:",
            e
        )

        return None


def find_url(value):

    if value is None:
        return None

    if isinstance(
        value,
        str
    ):

        if value.startswith(
            "http://"
        ) or value.startswith(
            "https://"
        ):

            return value

        return None

    if isinstance(
        value,
        dict
    ):

        for key in (
            "download_url",
            "file_url",
            "url",
            "downloadUrl"
        ):

            value2 = value.get(
                key
            )

            if value2:
                return value2

        for value2 in value.values():

            result = find_url(
                value2
            )

            if result:
                return result

    for attr in (
        "download_url",
        "file_url",
        "url",
        "downloadUrl"
    ):

        value2 = getattr(
            value,
            attr,
            None
        )

        if value2:
            return value2

    return None


# =========================================================
# اضافه کردن Metadata و کاور
# =========================================================

def set_metadata(
    file_path,
    title,
    artist,
    cover_path
):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    # فقط MP3
    if extension != ".mp3":

        print(
            "فایل MP3 نیست؛ metadata مخصوص MP3 اعمال نشد."
        )

        return False

    try:

        try:

            tags = ID3(
                file_path
            )

        except Exception:

            tags = ID3()

        # حذف اطلاعات قبلی

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

            mime = (
                mimetypes.guess_type(
                    cover_path
                )[0]
                or "image/jpeg"
            )

            tags.add(
                APIC(
                    encoding=3,
                    mime=mime,
                    type=3,
                    desc="Cover",
                    data=cover_data
                )
            )

        tags.save(
            file_path
        )

        print(
            "Metadata و کاور اضافه شد."
        )

        return True

    except Exception as e:

        print(
            "خطای metadata:",
            e
        )

        return False


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
        f"{safe_title}{extension}"
    )

    # جلوگیری از تداخل نام فایل

    if os.path.exists(
        new_path
    ):

        new_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"{safe_title}_{uuid.uuid4().hex[:6]}{extension}"
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
        (str, int)
    ):

        return result

    if isinstance(
        result,
        dict
    ):

        for key in (
            "message_id",
            "messageId"
        ):

            if result.get(key) is not None:
                return result[key]

        # Rubka معمولاً result را داخل data برمی‌گرداند

        for key in (
            "data",
            "result",
            "message"
        ):

            if key in result:

                value = extract_message_id(
                    result[key]
                )

                if value is not None:
                    return value

    for attr in (
        "message_id",
        "messageId"
    ):

        value = getattr(
            result,
            attr,
            None
        )

        if value is not None:
            return value

    for attr in (
        "data",
        "result",
        "message"
    ):

        value = getattr(
            result,
            attr,
            None
        )

        if value is not None:

            result_id = extract_message_id(
                value
            )

            if result_id is not None:
                return result_id

    return None


# =========================================================
# فوروارد فایل
# =========================================================

async def forward_to_users(
    from_chat_id,
    message_id
):

    if not message_id:

        print(
            "Message ID برای فوروارد پیدا نشد."
        )

        return

    users = load_users()

    print(
        "تعداد کاربران:",
        len(users)
    )

    for user_id in users:

        user_id = str(
            user_id
        )

        # برای درخواست‌کننده دوباره ارسال نکن
        if user_id == str(
            from_chat_id
        ):
            continue

        try:

            result = await call_maybe_async(
                bot.forward_message,
                from_chat_id=str(
                    from_chat_id
                ),
                message_id=str(
                    message_id
                ),
                to_chat_id=user_id
            )

            print(
                "Forward OK:",
                user_id,
                result
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

    file_path = None

    try:

        await message.reply(
            "⏳ در حال آماده‌سازی ویس..."
        )

        # دانلود
        file_path = download_file(
            data["url"]
        )

        # ارسال مستقیم
        # هیچ metadata یا کاوری اضافه نمی‌شود.

        result = await call_maybe_async(
            bot.send_voice,
            chat_id=chat_id,
            path=file_path,
            text=CAPTION,
            file_name=os.path.basename(
                file_path
            )
        )

        print(
            "Voice result:",
            result
        )

        message_id = extract_message_id(
            result
        )

        # فوروارد
        await forward_to_users(
            chat_id,
            message_id
        )

    except Exception as e:

        print(
            "VOICE ERROR:",
            e
        )

        try:

            await message.reply(
                f"❌ ارسال ویس انجام نشد.\n\n"
                f"خطا: {e}"
            )

        except Exception:
            pass

    finally:

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(
                    file_path
                )
            except Exception:
                pass

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# ارسال آهنگ
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

    file_path = None

    cover_path = data.get(
        "cover_path"
    )

    try:

        await message.reply(
            "⏳ در حال آماده‌سازی آهنگ..."
        )

        # دانلود آهنگ
        file_path = download_file(
            data["url"]
        )

        # اگر فایل MP3 بود:
        # عنوان + خواننده + کاور
        set_metadata(
            file_path,
            data["title"],
            data["artist"],
            cover_path
        )

        # تغییر نام
        file_path = rename_file(
            file_path,
            data["title"]
        )

        # ارسال آهنگ
        result = await call_maybe_async(
            bot.send_music,
            chat_id=chat_id,
            path=file_path,
            text=CAPTION,
            file_name=os.path.basename(
                file_path
            )
        )

        print(
            "Music result:",
            result
        )

        message_id = extract_message_id(
            result
        )

        # فوروارد
        await forward_to_users(
            chat_id,
            message_id
        )

    except Exception as e:

        print(
            "MUSIC ERROR:",
            e
        )

        try:

            await message.reply(
                f"❌ ارسال آهنگ انجام نشد.\n\n"
                f"خطا: {e}"
            )

        except Exception:
            pass

    finally:

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(
                    file_path
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

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# HANDLER
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

        text = str(
            text
        ).strip()

        # ثبت کاربر
        register_user(
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

            await message.reply(
                "🎵 سلام!\n\n"
                "لینک فایل صوتی را ارسال کن."
            )

            return

        # =================================================
        # وضعیت فعلی کاربر
        # =================================================

        data = user_data.get(
            chat_id
        )

        # =================================================
        # انتخاب ویس
        # =================================================

        if text == "🎤 ویس":

            if not data:
                return

            if data.get("step") != "type":
                return

            await send_voice_file(
                message
            )

            return

        # =================================================
        # انتخاب آهنگ
        # =================================================

        if text == "🎵 آهنگ":

            if not data:
                return

            if data.get("step") != "type":
                return

            data["step"] = "title"

            await message.reply(
                "🎵 اسم آهنگ را بفرست:"
            )

            return

        # =================================================
        # مرحله اسم آهنگ
        # =================================================

        if data:

            if data.get("step") == "title":

                if not text:
                    return

                # اگر دوباره لینک فرستاد
                if extract_url(text):
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

            if data.get("step") == "artist":

                if not text:
                    return

                if extract_url(text):
                    return

                data["artist"] = text

                data["step"] = "cover"

                await message.reply(
                    "🖼 لطفاً عکس کاور آهنگ را ارسال کنید:"
                )

                return

            # =================================================
            # مرحله کاور
            # =================================================

            if data.get("step") == "cover":

                # عکس باید فایل داشته باشد
                file_object = getattr(
                    message,
                    "file",
                    None
                )

                photo_object = getattr(
                    message,
                    "photo",
                    None
                )

                image_object = getattr(
                    message,
                    "image",
                    None
                )

                if (
                    not file_object
                    and not photo_object
                    and not image_object
                ):

                    return

                cover_path = await download_cover(
                    message
                )

                if not cover_path:

                    await message.reply(
                        "❌ دریافت عکس کاور انجام نشد.\n"
                        "لطفاً یک عکس معمولی ارسال کن."
                    )

                    return

                data["cover_path"] = cover_path

                await send_music_file(
                    message
                )

                return

            # اگر در حالت type است
            if data.get("step") == "type":

                return

        # =================================================
        # لینک
        # =================================================

        url = extract_url(
            text
        )

        if url:

            user_data[chat_id] = {

                "step": "type",

                "url": url,

                "title": "",

                "artist": "",

                "cover_path": None
            }

            await message.reply(
                "نوع ارسال را انتخاب کن:",
                chat_keypad=type_keyboard()
            )

            return

        # =================================================
        # سایر پیام‌ها
        # نادیده گرفته می‌شوند
        # =================================================

        return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            e
        )


# =========================================================
# RUN
# =========================================================

print(
    "================================="
)

print(
    "🤖 Rubika Bot Started"
)

print(
    "📦 Max file size: 200 MB"
)

print(
    "🎵 Music: title + artist + cover"
)

print(
    "🎤 Voice: direct"
)

print(
    "================================="
)

bot.run()
