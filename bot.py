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
from mutagen.id3 import ID3, TIT2, TPE1, APIC


# =========================================================
# SETTINGS
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# کپشن فایل
CAPTION = "@Black_list_remix"

# حداکثر حجم فایل: 200 مگابایت
MAX_FILE_SIZE = 200 * 1024 * 1024

# حداکثر حجم کاور: 10 مگابایت
MAX_COVER_SIZE = 10 * 1024 * 1024

DOWNLOAD_FOLDER = "./downloads"
USERS_FILE = "./users.json"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =========================================================
# BOT
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# USER STATES
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
            "users.json error:",
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
            "save users error:",
            e
        )


def register_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users.append(chat_id)

        save_users(users)

        print(
            "New user:",
            chat_id
        )


# =========================================================
# KEYBOARD
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
# URL
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
# FILENAME
# =========================================================

def get_filename_from_url(url):

    try:

        path = urlparse(url).path

        filename = os.path.basename(
            unquote(path)
        )

        if filename and "." in filename:
            return filename

    except:
        pass

    return None


# =========================================================
# DOWNLOAD NORMAL FILE
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

    filename = get_filename_from_url(url)

    if not filename:
        filename = "audio.mp3"

    filename = os.path.basename(filename)

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_{filename}"
    )

    total_size = 0

    with open(
        output_path,
        "wb"
    ) as f:

        for chunk in response.iter_content(
            chunk_size=256 * 1024
        ):

            if not chunk:
                continue

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:

                f.close()

                try:
                    os.remove(output_path)
                except:
                    pass

                raise Exception(
                    "حجم فایل بیشتر از 200 مگابایت است."
                )

            f.write(chunk)

    return output_path


# =========================================================
# GOOGLE DRIVE
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
            os.remove(output_path)
        except:
            pass

        raise Exception(
            "حجم فایل بیشتر از 200 مگابایت است."
        )

    return output_path


# =========================================================
# DOWNLOAD
# =========================================================

def download_file(url):

    if "drive.google.com" in url:

        return download_google_drive(url)

    return download_normal(url)


# =========================================================
# FIND MESSAGE FILE ID
# =========================================================

def get_message_file_id(message):

    # حالت‌های مختلف احتمالی Rubka

    file_id = getattr(
        message,
        "file_id",
        None
    )

    if file_id:
        return file_id

    photo = getattr(
        message,
        "photo",
        None
    )

    if photo:

        if isinstance(photo, list):

            photo = photo[-1]

        if isinstance(photo, dict):

            return (
                photo.get("file_id")
                or photo.get("fileId")
                or photo.get("id")
            )

        for attr in (
            "file_id",
            "fileId",
            "id"
        ):

            value = getattr(
                photo,
                attr,
                None
            )

            if value:
                return value

    image = getattr(
        message,
        "image",
        None
    )

    if image:

        if isinstance(image, dict):

            return (
                image.get("file_id")
                or image.get("fileId")
                or image.get("id")
            )

        for attr in (
            "file_id",
            "fileId",
            "id"
        ):

            value = getattr(
                image,
                attr,
                None
            )

            if value:
                return value

    return None


# =========================================================
# DOWNLOAD COVER
# =========================================================

async def download_cover(message):

    file_id = get_message_file_id(
        message
    )

    if not file_id:

        print(
            "Cover file_id پیدا نشد."
        )

        return None

    try:

        # دریافت اطلاعات فایل
        file_info = await bot.get_file(
            file_id
        )

        print(
            "Cover file info:",
            file_info
        )

    except Exception as e:

        print(
            "get_file error:",
            e
        )

        return None

    # -----------------------------------------------------
    # پیدا کردن URL
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

        file_url = (
            file_info.get("download_url")
            or file_info.get("file_url")
            or file_info.get("url")
        )

        # بعضی پاسخ‌ها ممکن است داخل data باشند
        if not file_url:

            data = file_info.get(
                "data"
            )

            if isinstance(
                data,
                dict
            ):

                file_url = (
                    data.get("download_url")
                    or data.get("file_url")
                    or data.get("url")
                )

    else:

        for attr in (
            "download_url",
            "file_url",
            "url"
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
            "Cover download URL پیدا نشد."
        )

        return None

    # -----------------------------------------------------
    # دانلود عکس
    # -----------------------------------------------------

    try:

        response = requests.get(
            file_url,
            timeout=60
        )

        response.raise_for_status()

        if len(response.content) > MAX_COVER_SIZE:

            raise Exception(
                "حجم کاور بیشتر از 10 مگابایت است."
            )

        cover_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"{uuid.uuid4().hex}_cover.jpg"
        )

        with open(
            cover_path,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        print(
            "Cover downloaded:",
            cover_path
        )

        return cover_path

    except Exception as e:

        print(
            "Cover download error:",
            e
        )

        return None


# =========================================================
# MP3 METADATA + COVER
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
                "MP3 metadata + cover OK"
            )

            return True

        except Exception as e:

            print(
                "MP3 metadata error:",
                e
            )

            return False

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
                "Metadata OK"
            )

            return True

    except Exception as e:

        print(
            "Metadata error:",
            e
        )

    return False


# =========================================================
# RENAME
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
# MESSAGE ID
# =========================================================

def extract_message_id(result):

    if result is None:
        return None

    if isinstance(
        result,
        (int, str)
    ):

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

        value = getattr(
            result,
            attr,
            None
        )

        if value is not None:
            return value

    for attr in (
        "message",
        "data",
        "result"
    ):

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

    return None


# =========================================================
# FORWARD TO USERS
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
                "Forwarded:",
                user_id
            )

        except Exception as e:

            print(
                "Forward error:",
                user_id,
                e
            )


# =========================================================
# SEND MUSIC
# =========================================================

async def send_music_file(message):

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

        # دانلود آهنگ
        file_path = download_file(
            data["url"]
        )

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
        result = await bot.send_music(
            chat_id=chat_id,
            path=file_path,
            text=CAPTION,
            file_name=os.path.basename(
                file_path
            )
        )

        print(
            "Music sent."
        )

        # دریافت Message ID
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
            "Music error:",
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
# SEND VOICE
# =========================================================

async def send_voice_file(message):

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

        # دانلود فایل
        file_path = download_file(
            data["url"]
        )

        # برای ویس:
        # هیچ عنوان، خواننده یا کاوری اعمال نمی‌شود.

        result = await bot.send_voice(
            chat_id=chat_id,
            path=file_path,
            text=CAPTION,
            file_name=os.path.basename(
                file_path
            )
        )

        print(
            "Voice sent."
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
            "Voice error:",
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
# MAIN HANDLER
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
        # MUSIC
        # =================================================

        if text == "🎵 آهنگ":

            data = user_data.get(
                chat_id
            )

            if not data:
                return

            # حالا تازه کاور درخواست می‌شود
            data["step"] = "cover"

            await message.reply(
                "🖼 لطفاً عکس کاور آهنگ را ارسال کنید:"
            )

            return

        # =================================================
        # VOICE
        # =================================================

        if text == "🎤 ویس":

            data = user_data.get(
                chat_id
            )

            if not data:
                return

            # ویس مستقیم ارسال می‌شود
            await send_voice_file(
                message
            )

            return

        # =================================================
        # USER STATE
        # =================================================

        if chat_id in user_data:

            data = user_data[
                chat_id
            ]

            # -------------------------------------------------
            # COVER
            # -------------------------------------------------

            if data["step"] == "cover":

                # عکس را دانلود کن
                cover_path = await download_cover(
                    message
                )

                if not cover_path:

                    # چیز دیگری فرستاده شده
                    return

                data["cover_path"] = cover_path

                # حالا آهنگ ارسال شود
                await send_music_file(
                    message
                )

                return

            # -------------------------------------------------
            # TITLE
            # -------------------------------------------------

            if data["step"] == "title":

                if not text:
                    return

                # اگر لینک دوباره فرستاد
                if extract_url(text):
                    return

                data["title"] = text

                data["step"] = "artist"

                await message.reply(
                    "🎤 اسم خواننده را بفرست:"
                )

                return

            # -------------------------------------------------
            # ARTIST
            # -------------------------------------------------

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

            # -------------------------------------------------
            # TYPE
            # -------------------------------------------------

            if data["step"] == "type":

                return

        # =================================================
        # URL
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
        # EVERYTHING ELSE = IGNORE
        # =================================================

        return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            e
        )


# =========================================================
# START
# =========================================================

print(
    "🤖 Rubika Bot Started..."
)

bot.run()
