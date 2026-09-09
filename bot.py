import os
import re
import json
import uuid
import requests
import gdown

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder

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
            e
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
        r'https?://[^\s]+',
        text
    )

    if match:

        return match.group(0).strip()

    return None


# =========================================================
# AWAIT HELPER
# =========================================================

async def maybe_await(result):

    if hasattr(
        result,
        "__await__"
    ):

        return await result

    return result


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
                e
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
    # CHECK FILE
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

    print(
        "AUDIO SIZE:",
        size
    )

    if size > MAX_FILE_SIZE:

        try:
            os.remove(
                output_path
            )
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

    temp_path = None
    jpg_path = None

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

        # -------------------------------------------------
        # SIZE
        # -------------------------------------------------

        if len(data) > MAX_COVER_SIZE:

            print(
                "COVER TOO LARGE"
            )

            return None

        # -------------------------------------------------
        # PIL CHECK
        # -------------------------------------------------

        from PIL import Image
        from io import BytesIO

        try:

            image = Image.open(
                BytesIO(data)
            )

            image.load()

        except Exception as e:

            print(
                "INVALID IMAGE:",
                e
            )

            return None

        print(
            "COVER FORMAT:",
            image.format
        )

        # -------------------------------------------------
        # TEMP
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
        # CONVERT TO JPG
        # -------------------------------------------------

        image = image.convert(
            "RGB"
        )

        jpg_path = os.path.join(
            DOWNLOAD_FOLDER,
            f"cover_{uuid.uuid4().hex}.jpg"
        )

        image.save(
            jpg_path,
            "JPEG",
            quality=95
        )

        image.close()

        # -------------------------------------------------
        # DELETE TEMP
        # -------------------------------------------------

        if os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )

        print(
            "COVER SAVED:",
            jpg_path
        )

        return jpg_path

    except Exception as e:

        print(
            "COVER DOWNLOAD ERROR:",
            repr(e)
        )

        if (
            temp_path
            and os.path.exists(temp_path)
        ):

            try:
                os.remove(temp_path)
            except:
                pass

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
# MP3 METADATA
# =========================================================

def set_metadata(
    file_path,
    title,
    artist,
    cover_path
):

    print(
        "SETTING MP3 METADATA..."
    )

    try:

        try:

            tags = ID3(
                file_path
            )

        except:

            tags = ID3()

        # -------------------------------------------------
        # REMOVE OLD TAGS
        # -------------------------------------------------

        tags.delall(
            "TIT2"
        )

        tags.delall(
            "TPE1"
        )

        tags.delall(
            "APIC"
        )

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        tags.add(
            TIT2(
                encoding=3,
                text=title
            )
        )

        # -------------------------------------------------
        # ARTIST
        # -------------------------------------------------

        tags.add(
            TPE1(
                encoding=3,
                text=artist
            )
        )

        # -------------------------------------------------
        # COVER
        # -------------------------------------------------

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

        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

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

        raise


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

    # Object

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

            return str(
                value
            )

    # Dict

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
# FORWARD
# =========================================================

async def forward_to_users(
    from_chat_id,
    message_id
):

    if not message_id:

        print(
            "NO MESSAGE ID"
        )

        return

    users = load_users()

    print(
        "FORWARD USERS:",
        users
    )

    for user_id in users:

        user_id = str(
            user_id
        )

        # Don't send again to requester

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

            await maybe_await(
                result
            )

            print(
                "FORWARDED:",
                user_id
            )

        except Exception as e:

            print(
                "FORWARD ERROR:",
                user_id,
                repr(e)
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
            "⏳ در حال دانلود فایل..."
        )

        file_path = download_file(
            data["url"]
        )

        await message.reply(
            "📤 در حال ارسال ویس..."
        )

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
            "VOICE MESSAGE ID:",
            message_id
        )

        await forward_to_users(
            chat_id,
            message_id
        )

        await message.reply(
            "✅ ویس ارسال شد."
        )

    except Exception as e:

        print(
            "VOICE ERROR:",
            repr(e)
        )

        if "200MB" in str(e):

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

        # -------------------------------------------------
        # DOWNLOAD
        # -------------------------------------------------

        await message.reply(
            "⏳ در حال دانلود آهنگ..."
        )

        file_path = download_file(
            data["url"]
        )

        # -------------------------------------------------
        # METADATA
        # -------------------------------------------------

        await message.reply(
            "🎨 در حال قرار دادن کاور..."
        )

        set_metadata(
            file_path,
            data["title"],
            data["artist"],
            cover_path
        )

        # -------------------------------------------------
        # RENAME
        # -------------------------------------------------

        file_path = rename_file(
            file_path,
            data["title"]
        )

        # -------------------------------------------------
        # SEND
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
            "MUSIC MESSAGE ID:",
            message_id
        )

        # -------------------------------------------------
        # FORWARD
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
            repr(e)
        )

        if "200MB" in str(e):

            await message.reply(
                "❌ حجم فایل بیشتر از ۲۰۰ مگابایت است."
            )

        else:

            await message.reply(
                "❌ ارسال آهنگ انجام نشد."
            )

    finally:

        # -------------------------------------------------
        # DELETE AUDIO
        # -------------------------------------------------

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

        # -------------------------------------------------
        # DELETE COVER
        # -------------------------------------------------

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
# MESSAGE HANDLER
# =========================================================
#
# IMPORTANT:
# Rubka calls handler with:
# bot, message
#
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

        # -------------------------------------------------
        # REGISTER USER
        # -------------------------------------------------

        register_user(
            chat_id
        )

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

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
                "🎵 سلام!\n\n"
                "لینک فایل صوتی را ارسال کن."
            )

            return

        # -------------------------------------------------
        # CURRENT DATA
        # -------------------------------------------------

        data = user_data.get(
            chat_id
        )

        # =================================================
        # VOICE BUTTON
        # =================================================

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

        # =================================================
        # MUSIC BUTTON
        # =================================================

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
        # CAPTION
        # =================================================

        if (
            data
            and data.get("step") == "caption"
        ):

            if not text:
                return

            data["caption"] = text

            data["step"] = "type"

            await message.reply(
                "📦 نوع ارسال را انتخاب کن:",
                chat_keypad=type_keyboard()
            )

            return

        # =================================================
        # TITLE
        # =================================================

        if (
            data
            and data.get("step") == "title"
        ):

            if not text:
                return

            if extract_url(text):

                await message.reply(
                    "❌ اینجا اسم آهنگ را ارسال کن."
                )

                return

            data["title"] = text

            data["step"] = "artist"

            await message.reply(
                "🎤 اسم خواننده را بفرست:"
            )

            return

        # =================================================
        # ARTIST
        # =================================================

        if (
            data
            and data.get("step") == "artist"
        ):

            if not text:
                return

            if extract_url(text):

                await message.reply(
                    "❌ اینجا اسم خواننده را ارسال کن."
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
        # COVER URL
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
                    "❌ لطفاً لینک عکس را ارسال کن."
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
                    "❌ این لینک یک عکس معتبر نیست.\n\n"
                    "لطفاً لینک مستقیم JPG یا PNG ارسال کن."
                )

                return

            data["cover_path"] = (
                cover_path
            )

            await message.reply(
                "✅ کاور دریافت شد."
            )

            await send_music(
                message
            )

            return

        # =================================================
        # AUDIO URL
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
        # OTHER MESSAGES
        # =================================================

        return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )


# =========================================================
# START BOT
# =========================================================

print(
    "======================================"
)

print(
    "        RUBIKA MUSIC BOT"
)

print(
    "======================================"
)

print(
    "BOT STARTED..."
)

bot.run()
