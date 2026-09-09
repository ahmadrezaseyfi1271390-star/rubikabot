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


# =========================================================
# SETTINGS
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# کپشن پیش‌فرض
DEFAULT_CAPTION = "@Black_list_remix"

# حداکثر حجم فایل
MAX_FILE_SIZE = 200 * 1024 * 1024

# حداکثر حجم کاور
MAX_COVER_SIZE = 10 * 1024 * 1024

DOWNLOAD_FOLDER = "downloads"
USERS_FILE = "users.json"

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# BOT
# =========================================================

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)


# =========================================================
# USER DATA
# =========================================================

user_data = {}


# =========================================================
# USERS
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
            "users.json error:",
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
            "save users error:",
            e
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
            "Registered user:",
            chat_id
        )


# =========================================================
# KEYBOARD
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
        r"https?://[^\s]+",
        text
    )

    if not match:
        return None

    return match.group(
        0
    ).strip().rstrip(
        ".,!?،؛)]}"
    )


# =========================================================
# FILENAME
# =========================================================

def get_filename_from_url(
    url
):

    try:

        path = urlparse(
            url
        ).path

        filename = os.path.basename(
            unquote(path)
        )

        if filename and "." in filename:
            return filename

    except Exception:
        pass

    return "audio.mp3"


# =========================================================
# DOWNLOAD NORMAL FILE
# =========================================================

def download_normal(
    url
):

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

            size = int(
                content_length
            )

            if size > MAX_FILE_SIZE:

                response.close()

                raise ValueError(
                    "حجم فایل بیشتر از 200 مگابایت است."
                )

        except ValueError as e:

            if "200" in str(e):

                raise

    filename = get_filename_from_url(
        url
    )

    filename = os.path.basename(
        filename
    )

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_{filename}"
    )

    total = 0

    try:

        with open(
            output_path,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=256 * 1024
            ):

                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if total > MAX_FILE_SIZE:

                    raise ValueError(
                        "حجم فایل بیشتر از 200 مگابایت است."
                    )

                f.write(
                    chunk
                )

    except Exception:

        if os.path.exists(
            output_path
        ):

            try:
                os.remove(
                    output_path
                )
            except Exception:
                pass

        raise

    finally:

        response.close()

    return output_path


# =========================================================
# GOOGLE DRIVE
# =========================================================

def download_google_drive(
    url
):

    output_path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}.mp3"
    )

    result = gdown.download(
        url,
        output_path,
        quiet=True
    )

    if not result:

        raise ValueError(
            "دانلود Google Drive انجام نشد."
        )

    if not os.path.exists(
        output_path
    ):

        raise ValueError(
            "فایل Google Drive پیدا نشد."
        )

    if os.path.getsize(
        output_path
    ) > MAX_FILE_SIZE:

        os.remove(
            output_path
        )

        raise ValueError(
            "حجم فایل بیشتر از 200 مگابایت است."
        )

    return output_path


# =========================================================
# DOWNLOAD FILE
# =========================================================

def download_file(
    url
):

    if "drive.google.com" in url:

        return download_google_drive(
            url
        )

    return download_normal(
        url
    )


# =========================================================
# FIND FILE ID
# =========================================================

def get_file_id(
    message
):

    file_obj = getattr(
        message,
        "file",
        None
    )

    if not file_obj:
        return None

    # object
    file_id = getattr(
        file_obj,
        "file_id",
        None
    )

    if file_id:
        return str(
            file_id
        )

    # بعضی نسخه‌ها
    file_id = getattr(
        file_obj,
        "id",
        None
    )

    if file_id:
        return str(
            file_id
        )

    # dictionary
    if isinstance(
        file_obj,
        dict
    ):

        for key in (
            "file_id",
            "fileId",
            "id"
        ):

            if file_obj.get(
                key
            ):

                return str(
                    file_obj[key]
                )

    return None


# =========================================================
# DOWNLOAD COVER
# =========================================================

async def download_cover(
    message
):

    file_id = get_file_id(
        message
    )

    print(
        "Cover file_id:",
        file_id
    )

    if not file_id:

        return None

    # -----------------------------------------------------
    # روش 1: اگر Robot نسخه نصب‌شده get_file داشته باشد
    # -----------------------------------------------------

    get_file_method = getattr(
        bot,
        "get_file",
        None
    )

    if not get_file_method:

        print(
            "get_file در این نسخه موجود نیست."
        )

        return None

    try:

        result = get_file_method(
            file_id
        )

        # اگر async باشد
        if hasattr(
            result,
            "__await__"
        ):

            result = await result

        print(
            "get_file result:",
            result
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
        result,
        str
    ):

        file_url = result

    elif isinstance(
        result,
        dict
    ):

        for key in (
            "url",
            "file_url",
            "download_url",
            "downloadUrl"
        ):

            if result.get(
                key
            ):

                file_url = result[key]
                break

        if not file_url:

            for key in (
                "data",
                "result",
                "file"
            ):

                nested = result.get(
                    key
                )

                if isinstance(
                    nested,
                    dict
                ):

                    for url_key in (
                        "url",
                        "file_url",
                        "download_url",
                        "downloadUrl"
                    ):

                        if nested.get(
                            url_key
                        ):

                            file_url = nested[
                                url_key
                            ]

                            break

                if file_url:
                    break

    else:

        for attr in (
            "url",
            "file_url",
            "download_url",
            "downloadUrl"
        ):

            value = getattr(
                result,
                attr,
                None
            )

            if value:

                file_url = value
                break

    if not file_url:

        print(
            "Download URL پیدا نشد."
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

        data = response.content

        if len(data) > MAX_COVER_SIZE:

            raise ValueError(
                "حجم کاور بیشتر از 10MB است."
            )

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        extension = ".jpg"

        if "png" in content_type:
            extension = ".png"

        elif "webp" in content_type:
            extension = ".webp"

        cover_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"{uuid.uuid4().hex}_cover{extension}"
        )

        with open(
            cover_path,
            "wb"
        ) as f:

            f.write(
                data
            )

        return cover_path

    except Exception as e:

        print(
            "Cover download error:",
            e
        )

        return None


# =========================================================
# METADATA
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

    if extension != ".mp3":

        print(
            "فایل MP3 نیست؛ metadata اعمال نشد."
        )

        return False

    try:

        try:

            tags = ID3(
                file_path
            )

        except Exception:

            tags = ID3()

        tags.delall(
            "TIT2"
        )

        tags.delall(
            "TPE1"
        )

        tags.delall(
            "APIC"
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
        f"{safe_title}{extension}"
    )

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
# GET MESSAGE ID
# =========================================================

def get_message_id(
    result
):

    if result is None:
        return None

    if isinstance(
        result,
        (str, int)
    ):

        return str(
            result
        )

    if isinstance(
        result,
        dict
    ):

        for key in (
            "message_id",
            "messageId"
        ):

            if result.get(
                key
            ):

                return str(
                    result[key]
                )

        for key in (
            "data",
            "result",
            "message"
        ):

            if key in result:

                value = get_message_id(
                    result[key]
                )

                if value:
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

        if value:

            return str(
                value
            )

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

        if value:

            result_id = get_message_id(
                value
            )

            if result_id:
                return result_id

    return None


# =========================================================
# FORWARD
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

    for user_id in users:

        user_id = str(
            user_id
        )

        # برای صاحب فایل دوباره نفرست
        if user_id == str(
            from_chat_id
        ):
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

            if hasattr(
                result,
                "__await__"
            ):

                await result

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
# SEND VOICE
# =========================================================

async def send_voice(
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

        file_path = download_file(
            data["url"]
        )

        # هیچ اسم آهنگ، خواننده یا کاوری
        # روی فایل اعمال نمی‌شود.

        result = bot.send_voice(
            chat_id=chat_id,
            path=file_path,
            text=data["caption"],
            file_name=os.path.basename(
                file_path
            )
        )

        if hasattr(
            result,
            "__await__"
        ):

            result = await result

        print(
            "Voice result:",
            result
        )

        message_id = get_message_id(
            result
        )

        # فوروارد ویس به همه
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
                "❌ ارسال ویس انجام نشد."
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
# SEND MUSIC
# =========================================================

async def send_music(
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

        file_path = download_file(
            data["url"]
        )

        # اضافه کردن عنوان، خواننده و کاور
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

        result = bot.send_music(
            chat_id=chat_id,
            path=file_path,
            text=data["caption"],
            file_name=os.path.basename(
                file_path
            )
        )

        if hasattr(
            result,
            "__await__"
        ):

            result = await result

        print(
            "Music result:",
            result
        )

        message_id = get_message_id(
            result
        )

        # فوروارد آهنگ به همه
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
                "❌ ارسال آهنگ انجام نشد."
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
        # وضعیت کاربر
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

            if data.get(
                "step"
            ) != "type":

                return

            await send_voice(
                message
            )

            return

        # =================================================
        # انتخاب آهنگ
        # =================================================

        if text == "🎵 آهنگ":

            if not data:
                return

            if data.get(
                "step"
            ) != "type":

                return

            data["step"] = "title"

            await message.reply(
                "🎵 اسم آهنگ را بفرست:"
            )

            return

        # =================================================
        # کپشن
        # =================================================

        if data:

            if data.get(
                "step"
            ) == "caption":

                if not text:
                    return

                data["caption"] = text

                data["step"] = "type"

                await message.reply(
                    "نوع ارسال را انتخاب کن:",
                    chat_keypad=type_keyboard()
                )

                return

        # =================================================
        # اسم آهنگ
        # =================================================

        if data:

            if data.get(
                "step"
            ) == "title":

                if not text:
                    return

                if extract_url(
                    text
                ):

                    return

                data["title"] = text

                data["step"] = "artist"

                await message.reply(
                    "🎤 اسم خواننده را بفرست:"
                )

                return

        # =================================================
        # خواننده
        # =================================================

        if data:

            if data.get(
                "step"
            ) == "artist":

                if not text:
                    return

                if extract_url(
                    text
                ):

                    return

                data["artist"] = text

                data["step"] = "cover"

                await message.reply(
                    "🖼 لطفاً عکس کاور آهنگ را ارسال کنید:"
                )

                return

        # =================================================
        # کاور
        # =================================================

        if data:

            if data.get(
                "step"
            ) == "cover":

                # Rubka فایل را در message.file قرار می‌دهد
                file_obj = getattr(
                    message,
                    "file",
                    None
                )

                if not file_obj:

                    await message.reply(
                        "❌ لطفاً یک عکس ارسال کن."
                    )

                    return

                cover_path = await download_cover(
                    message
                )

                if not cover_path:

                    await message.reply(
                        "❌ دریافت کاور انجام نشد."
                    )

                    return

                data["cover_path"] = cover_path

                await send_music(
                    message
                )

                return

        # =================================================
        # لینک جدید
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
        # سایر پیام‌ها
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
    "===================================="
)

print(
    "🤖 Rubika Bot Started"
)

print(
    "📦 Maximum file size: 200 MB"
)

print(
    "🎤 Voice → direct + forward"
)

print(
    "🎵 Music → title + artist + cover"
)

print(
    "✏️ Caption → before type selection"
)

print(
    "===================================="
)

bot.run()
