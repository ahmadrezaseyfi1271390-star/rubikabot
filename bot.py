import os
import re
import json
import uuid
import asyncio
import inspect
import requests
import gdown

from io import BytesIO
from PIL import Image

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder
from rubka.keypad import InlineBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC


# =========================================================
# SETTINGS
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_FILE_SIZE = 100 * 1024 * 1024
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
# FOLDER
# =========================================================

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# USER DATA
# =========================================================

user_data = {}

# آخرین پیام راهنمای ربات برای هر کاربر
prompt_messages = {}


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


def save_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    users = [
        str(x)
        for x in users
    ]

    if chat_id not in users:

        users.append(
            chat_id
        )

        try:

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
                "USERS SAVE ERROR:",
                repr(e)
            )


# =========================================================
# ASYNC
# =========================================================

async def maybe_await(result):

    if inspect.isawaitable(result):
        return await result

    return result


async def run_blocking(
    function,
    *args
):

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        None,
        lambda: function(*args)
    )


# =========================================================
# MESSAGE ID
# =========================================================

def get_message_id(result):

    if result is None:
        return None

    for attr in (
        "message_id",
        "id"
    ):

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

        for key in (
            "message_id",
            "id"
        ):

            if key in result:
                return str(
                    result[key]
                )

    return None


# =========================================================
# DELETE OLD BOT PROMPT
# =========================================================

async def delete_old_prompt(
    chat_id
):

    chat_id = str(chat_id)

    old_id = prompt_messages.get(
        chat_id
    )

    if not old_id:
        return

    try:

        result = bot.delete_message(
            chat_id=chat_id,
            message_id=str(old_id)
        )

        await maybe_await(
            result
        )

    except Exception as e:

        print(
            "DELETE OLD PROMPT:",
            repr(e)
        )

    prompt_messages.pop(
        chat_id,
        None
    )


# =========================================================
# SEND SHORT PROMPT
# =========================================================

async def prompt(
    chat_id,
    text,
    chat_keypad=None,
    inline_keypad=None
):

    chat_id = str(chat_id)

    await delete_old_prompt(
        chat_id
    )

    try:

        result = bot.send_message(
            chat_id=chat_id,
            text=text,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad
        )

        result = await maybe_await(
            result
        )

        message_id = get_message_id(
            result
        )

        if message_id:

            prompt_messages[
                chat_id
            ] = message_id

        return result

    except Exception as e:

        print(
            "PROMPT ERROR:",
            repr(e)
        )

        return None


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    builder = ChatKeypadBuilder()

    return (
        builder
        .row(
            builder.button(
                id="banner",
                text="🖼 ساخت بنر"
            )
        )
        .row(
            builder.button(
                id="music_edit",
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
# YES / NO KEYBOARD
# =========================================================

def yes_no_keyboard():

    builder = ChatKeypadBuilder()

    return (
        builder
        .row(
            builder.button(
                id="yes",
                text="بله"
            ),
            builder.button(
                id="no",
                text="نه"
            )
        )
        .build(
            resize_keyboard=True,
            on_time_keyboard=False
        )
    )


# =========================================================
# NEXT KEYBOARD
# =========================================================

def next_keyboard():

    builder = ChatKeypadBuilder()

    return (
        builder
        .row(
            builder.button(
                id="next",
                text="بعدی"
            )
        )
        .build(
            resize_keyboard=True,
            on_time_keyboard=False
        )
    )


# =========================================================
# GLASS BUTTON
# =========================================================

def make_glass_button(
    text
):

    if not text:
        return None

    try:

        builder = InlineBuilder()

        builder.button(
            id="display_button",
            text=text
        )

        return builder.build()

    except Exception as e:

        print(
            "GLASS BUTTON ERROR:",
            repr(e)
        )

        return None


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

    if not match:
        return None

    return (
        match.group(0)
        .strip()
        .rstrip("،,؛;)")
    )


# =========================================================
# DOWNLOAD AUDIO
# =========================================================

def download_audio(
    url
):

    path = os.path.join(
        DOWNLOAD_FOLDER,
        "audio_" +
        uuid.uuid4().hex +
        ".mp3"
    )

    try:

        print(
            "DOWNLOAD AUDIO:",
            url
        )

        # ---------------------------------------------
        # GOOGLE DRIVE
        # ---------------------------------------------

        if "drive.google.com" in url:

            gdown.download(
                url,
                path,
                quiet=True
            )

        # ---------------------------------------------
        # NORMAL URL
        # ---------------------------------------------

        else:

            response = requests.get(
                url,
                stream=True,
                timeout=60,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            response.raise_for_status()

            total = 0

            with open(
                path,
                "wb"
            ) as f:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_FILE_SIZE:

                        raise Exception(
                            "FILE_TOO_LARGE"
                        )

                    f.write(chunk)

        if not os.path.exists(
            path
        ):

            raise Exception(
                "DOWNLOAD_FAILED"
            )

        size = os.path.getsize(
            path
        )

        if size <= 0:

            raise Exception(
                "EMPTY_FILE"
            )

        if size > MAX_FILE_SIZE:

            raise Exception(
                "FILE_TOO_LARGE"
            )

        return path

    except Exception:

        if os.path.exists(
            path
        ):

            try:
                os.remove(path)
            except:
                pass

        raise


# =========================================================
# DOWNLOAD COVER
# =========================================================

def download_cover(
    url
):

    path = os.path.join(
        DOWNLOAD_FOLDER,
        "cover_" +
        uuid.uuid4().hex +
        ".jpg"
    )

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        data = response.content

        if len(data) > MAX_COVER_SIZE:

            raise Exception(
                "COVER_TOO_LARGE"
            )

        image = Image.open(
            BytesIO(data)
        )

        image.load()

        image = image.convert(
            "RGB"
        )

        image.save(
            path,
            "JPEG",
            quality=95
        )

        image.close()

        return path

    except Exception:

        if os.path.exists(
            path
        ):

            try:
                os.remove(path)
            except:
                pass

        raise


# =========================================================
# DOWNLOAD BANNER
# =========================================================

def download_banner(
    url
):

    path = os.path.join(
        DOWNLOAD_FOLDER,
        "banner_" +
        uuid.uuid4().hex +
        ".jpg"
    )

    try:

        response = requests.get(
            url,
            timeout=60,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        data = response.content

        if len(data) > MAX_FILE_SIZE:

            raise Exception(
                "FILE_TOO_LARGE"
            )

        image = Image.open(
            BytesIO(data)
        )

        image.load()

        image = image.convert(
            "RGB"
        )

        image.save(
            path,
            "JPEG",
            quality=95
        )

        image.close()

        return path

    except Exception:

        if os.path.exists(
            path
        ):

            try:
                os.remove(path)
            except:
                pass

        raise


# =========================================================
# MP3 METADATA
# =========================================================

def edit_mp3(
    file_path,
    title,
    artist,
    cover_path
):

    try:

        try:

            tags = ID3(
                file_path
            )

        except:

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

        if (
            cover_path
            and os.path.exists(
                cover_path
            )
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

    except Exception as e:

        print(
            "MP3 EDIT ERROR:",
            repr(e)
        )

        raise


# =========================================================
# RENAME MP3
# =========================================================

def rename_mp3(
    file_path,
    title
):

    safe_title = re.sub(
        r'[\/:*?"<>|]',
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
# SEND MUSIC
# =========================================================

async def send_music_to_user(
    chat_id,
    file_path,
    caption,
    inline_keypad=None
):

    result = bot.send_music(
        chat_id=str(chat_id),
        path=file_path,
        text=caption,
        file_name=os.path.basename(
            file_path
        ),
        inline_keypad=inline_keypad
    )

    return await maybe_await(
        result
    )


# =========================================================
# SEND VOICE
# =========================================================

async def send_voice_to_user(
    chat_id,
    file_path,
    caption,
    inline_keypad=None
):

    result = bot.send_voice(
        chat_id=str(chat_id),
        path=file_path,
        text=caption,
        file_name=os.path.basename(
            file_path
        ),
        inline_keypad=inline_keypad
    )

    return await maybe_await(
        result
    )


# =========================================================
# SEND IMAGE
# =========================================================

async def send_image_to_user(
    chat_id,
    file_path,
    caption,
    inline_keypad=None
):

    result = bot.send_image(
        chat_id=str(chat_id),
        path=file_path,
        text=caption,
        inline_keypad=inline_keypad
    )

    return await maybe_await(
        result
    )


# =========================================================
# PREVIEW
# همان کاربری که درخواست داده
# =========================================================

async def send_preview(
    chat_id,
    data
):

    file_path = data.get(
        "file_path"
    )

    if not file_path:
        return

    try:

        if data.get(
            "mode"
        ) == "music":

            await send_music_to_user(
                chat_id,
                file_path,
                "👀 پیش‌نمایش"
            )

        elif data.get(
            "mode"
        ) == "banner":

            await send_image_to_user(
                chat_id,
                file_path,
                "👀 پیش‌نمایش"
            )

    except Exception as e:

        print(
            "PREVIEW ERROR:",
            repr(e)
        )


# =========================================================
# FINISH MUSIC
# =========================================================

async def finish_music(
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

    file_path = data.get(
        "file_path"
    )

    cover_path = data.get(
        "cover_path"
    )

    try:

        # ---------------------------------------------
        # EDIT
        # ---------------------------------------------

        await prompt(
            chat_id,
            "🎨"
        )

        await run_blocking(
            edit_mp3,
            file_path,
            data["title"],
            data["artist"],
            cover_path
        )

        # ---------------------------------------------
        # RENAME
        # ---------------------------------------------

        file_path = await run_blocking(
            rename_mp3,
            file_path,
            data["title"]
        )

        data["file_path"] = file_path

        # ---------------------------------------------
        # BUTTON
        # ---------------------------------------------

        inline_keypad = make_glass_button(
            data.get(
                "button_text"
            )
        )

        # ---------------------------------------------
        # FINAL
        # ---------------------------------------------

        await prompt(
            chat_id,
            "📤"
        )

        await send_music_to_user(
            chat_id,
            file_path,
            data["caption"],
            inline_keypad
        )

        await prompt(
            chat_id,
            "✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "FINISH MUSIC ERROR:",
            repr(e)
        )

        if "FILE_TOO_LARGE" in str(e):

            await prompt(
                chat_id,
                "❌ حجم فایل بیشتر از ۱۰۰MB است.",
                chat_keypad=main_keyboard()
            )

        else:

            await prompt(
                chat_id,
                "❌",
                chat_keypad=main_keyboard()
            )

    finally:

        remove_file(
            file_path
        )

        remove_file(
            cover_path
        )

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# FINISH VOICE
# =========================================================

async def finish_voice(
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

    file_path = data.get(
        "file_path"
    )

    try:

        inline_keypad = make_glass_button(
            data.get(
                "button_text"
            )
        )

        await prompt(
            chat_id,
            "📤"
        )

        await send_voice_to_user(
            chat_id,
            file_path,
            data["caption"],
            inline_keypad
        )

        await prompt(
            chat_id,
            "✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "FINISH VOICE ERROR:",
            repr(e)
        )

        await prompt(
            chat_id,
            "❌",
            chat_keypad=main_keyboard()
        )

    finally:

        remove_file(
            file_path
        )

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# FINISH BANNER
# =========================================================

async def finish_banner(
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

    file_path = data.get(
        "file_path"
    )

    try:

        inline_keypad = make_glass_button(
            data.get(
                "button_text"
            )
        )

        await prompt(
            chat_id,
            "📤"
        )

        await send_image_to_user(
            chat_id,
            file_path,
            data["caption"],
            inline_keypad
        )

        await prompt(
            chat_id,
            "✅",
            chat_keypad=main_keyboard()
        )

    except Exception as e:

        print(
            "FINISH BANNER ERROR:",
            repr(e)
        )

        await prompt(
            chat_id,
            "❌",
            chat_keypad=main_keyboard()
        )

    finally:

        remove_file(
            file_path
        )

        user_data.pop(
            chat_id,
            None
        )


# =========================================================
# REMOVE FILE
# =========================================================

def remove_file(
    path
):

    if (
        path
        and os.path.exists(path)
    ):

        try:

            os.remove(
                path
            )

        except Exception as e:

            print(
                "REMOVE FILE ERROR:",
                repr(e)
            )


# =========================================================
# MESSAGE HANDLER
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

        save_user(
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

            await prompt(
                chat_id,
                "👇",
                chat_keypad=main_keyboard()
            )

            return

        data = user_data.get(
            chat_id
        )

        # =================================================
        # MAIN - MUSIC
        # =================================================

        if text == "🎵 ادیت آهنگ":

            user_data[chat_id] = {

                "mode": "music",

                "step": "audio_url",

                "url": None,

                "file_path": None,

                "caption":
                    DEFAULT_CAPTION,

                "type": None,

                "title": "",

                "artist": "",

                "cover_path": None,

                "button_text": ""
            }

            await prompt(
                chat_id,
                "🔗"
            )

            return

        # =================================================
        # MAIN - BANNER
        # =================================================

        if text == "🖼 ساخت بنر":

            user_data[chat_id] = {

                "mode": "banner",

                "step": "banner_url",

                "url": None,

                "file_path": None,

                "caption":
                    DEFAULT_CAPTION,

                "button_text": ""
            }

            await prompt(
                chat_id,
                "🔗"
            )

            return

        # =================================================
        # AUDIO URL
        # =================================================

        if (
            data
            and data.get("step")
            == "audio_url"
        ):

            url = extract_url(
                text
            )

            if not url:
                return

            data["url"] = url
            data["step"] = "preview"

            await prompt(
                chat_id,
                "پیش‌نمایش لازم دارید؟",
                chat_keypad=yes_no_keyboard()
            )

            return

        # =================================================
        # BANNER URL
        # =================================================

        if (
            data
            and data.get("step")
            == "banner_url"
        ):

            url = extract_url(
                text
            )

            if not url:
                return

            data["url"] = url
            data["step"] = "preview"

            await prompt(
                chat_id,
                "پیش‌نمایش لازم دارید؟",
                chat_keypad=yes_no_keyboard()
            )

            return

        # =================================================
        # PREVIEW ANSWER
        # =================================================

        if (
            data
            and data.get("step")
            == "preview"
        ):

            answer = (
                text or ""
            ).strip().lower()

            if answer not in (
                "بله",
                "بله",
                "اره",
                "آره",
                "yes",
                "y",
                "نه",
                "خیر",
                "no",
                "n"
            ):

                return

            wants_preview = answer in (
                "بله",
                "اره",
                "آره",
                "yes",
                "y"
            )

            # ---------------------------------------------
            # DOWNLOAD
            # ---------------------------------------------

            try:

                if data.get(
                    "mode"
                ) == "music":

                    await prompt(
                        chat_id,
                        "⏳"
                    )

                    file_path = (
                        await run_blocking(
                            download_audio,
                            data["url"]
                        )
                    )

                else:

                    await prompt(
                        chat_id,
                        "⏳"
                    )

                    file_path = (
                        await run_blocking(
                            download_banner,
                            data["url"]
                        )
                    )

                data["file_path"] = (
                    file_path
                )

            except Exception as e:

                print(
                    "DOWNLOAD ERROR:",
                    repr(e)
                )

                if "FILE_TOO_LARGE" in str(e):

                    await prompt(
                        chat_id,
                        "❌ حجم فایل بیشتر از ۱۰۰MB است.",
                        chat_keypad=main_keyboard()
                    )

                else:

                    await prompt(
                        chat_id,
                        "❌",
                        chat_keypad=main_keyboard()
                    )

                user_data.pop(
                    chat_id,
                    None
                )

                return

            # ---------------------------------------------
            # PREVIEW
            # ---------------------------------------------

            if wants_preview:

                await send_preview(
                    chat_id,
                    data
                )

            # ---------------------------------------------
            # CAPTION
            # ---------------------------------------------

            data["step"] = "caption"

            await prompt(
                chat_id,
                "✏️"
            )

            return

        # =================================================
        # CAPTION
        # =================================================

        if (
            data
            and data.get("step")
            == "caption"
        ):

            if not text:
                return

            if text == "بعدی":

                data["caption"] = (
                    DEFAULT_CAPTION
                )

            else:

                data["caption"] = text

            # ---------------------------------------------
            # BANNER
            # ---------------------------------------------

            if data.get(
                "mode"
            ) == "banner":

                data["step"] = (
                    "button"
                )

                await prompt(
                    chat_id,
                    "🔘",
                    chat_keypad=next_keyboard()
                )

                return

            # ---------------------------------------------
            # MUSIC
            # ---------------------------------------------

            data["step"] = "type"

            await prompt(
                chat_id,
                "🎵",
                chat_keypad=type_keyboard()
            )

            return

        # =================================================
        # TYPE - MUSIC
        # =================================================

        if text == "🎵 آهنگ":

            if (
                not data
                or data.get("step")
                != "type"
            ):
                return

            data["type"] = "music"
            data["step"] = "title"

            await prompt(
                chat_id,
                "🎵"
            )

            return

        # =================================================
        # TYPE - VOICE
        # =================================================

        if text == "🎤 ویس":

            if (
                not data
                or data.get("step")
                != "type"
            ):
                return

            data["type"] = "voice"
            data["step"] = "button"

            await prompt(
                chat_id,
                "🔘",
                chat_keypad=next_keyboard()
            )

            return

        # =================================================
        # TITLE
        # =================================================

        if (
            data
            and data.get("step")
            == "title"
        ):

            if not text:
                return

            data["title"] = text
            data["step"] = "artist"

            await prompt(
                chat_id,
                "🎤"
            )

            return

        # =================================================
        # ARTIST
        # =================================================

        if (
            data
            and data.get("step")
            == "artist"
        ):

            if not text:
                return

            data["artist"] = text
            data["step"] = "cover"

            await prompt(
                chat_id,
                "🖼️"
            )

            return

        # =================================================
        # COVER
        # =================================================

        if (
            data
            and data.get("step")
            == "cover"
        ):

            if text == "بعدی":

                data["cover_path"] = None
                data["step"] = "button"

                await prompt(
                    chat_id,
                    "🔘",
                    chat_keypad=next_keyboard()
                )

                return

            cover_url = extract_url(
                text
            )

            if not cover_url:
                return

            try:

                cover_path = (
                    await run_blocking(
                        download_cover,
                        cover_url
                    )
                )

                data["cover_path"] = (
                    cover_path
                )

                data["step"] = "button"

                await prompt(
                    chat_id,
                    "🔘",
                    chat_keypad=next_keyboard()
                )

            except Exception as e:

                print(
                    "COVER ERROR:",
                    repr(e)
                )

                await prompt(
                    chat_id,
                    "❌"
                )

            return

        # =================================================
        # BUTTON
        # =================================================

        if (
            data
            and data.get("step")
            == "button"
        ):

            if text == "بعدی":

                data["button_text"] = ""

            else:

                if not text:
                    return

                data["button_text"] = (
                    text
                )

            # ---------------------------------------------
            # BANNER
            # ---------------------------------------------

            if data.get(
                "mode"
            ) == "banner":

                await finish_banner(
                    message
                )

                return

            # ---------------------------------------------
            # VOICE
            # ---------------------------------------------

            if data.get(
                "type"
            ) == "voice":

                await finish_voice(
                    message
                )

                return

            # ---------------------------------------------
            # MUSIC
            # ---------------------------------------------

            if data.get(
                "type"
            ) == "music":

                await finish_music(
                    message
                )

                return

    except Exception as e:

        print(
            "HANDLER ERROR:",
            repr(e)
        )


# =========================================================
# START
# =========================================================

print(
    "======================================"
)

print(
    "          RUBIKA EDIT BOT"
)

print(
    "======================================"
)

print(
    "BOT STARTED..."
)

bot.run()
