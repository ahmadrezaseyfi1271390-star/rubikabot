import os
import re
import json
import asyncio
import hashlib
import requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
from mutagen.id3 import ID3, TIT2, TPE1, APIC
from mutagen.mp3 import MP3

from rubka import Robot, Message
from rubka.builders import ChatKeypadBuilder, InlineBuilder


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

MAX_AUDIO_SIZE = 100 * 1024 * 1024       # 100MB
MAX_COVER_SIZE = 10 * 1024 * 1024        # 10MB

CACHE_FILE = "cache.json"
USERS_FILE = "users.json"

bot = Robot(
    token=TOKEN,
    safeSendMode=True
)

executor = ThreadPoolExecutor(max_workers=4)

user_data = {}
prompt_messages = {}

users_cache = set()


# =========================================================
# فایل‌های JSON
# =========================================================

def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


def save_json(filename, data):
    temp = filename + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp, filename)


cache = load_json(CACHE_FILE, {})
users_cache = set(load_json(USERS_FILE, []))


def register_user(chat_id):
    chat_id = str(chat_id)

    if chat_id not in users_cache:
        users_cache.add(chat_id)
        save_json(
            USERS_FILE,
            list(users_cache)
        )


# =========================================================
# اجرای کارهای سنگین خارج از Event Loop
# =========================================================

async def run_blocking(func, *args):
    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        lambda: func(*args)
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

    if not match:
        return None

    return match.group(0).rstrip(
        ".,!?،؛)]}"
    )


# =========================================================
# دانلود فایل
# =========================================================

def download_url(url, output, max_size):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        with requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=60
        ) as response:

            response.raise_for_status()

            total = 0

            with open(output, "wb") as f:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > max_size:
                        try:
                            os.remove(output)
                        except:
                            pass

                        return False

                    f.write(chunk)

        return os.path.exists(output)

    except Exception as e:
        print("DOWNLOAD ERROR:", e)

        try:
            os.remove(output)
        except:
            pass

        return False


def download_audio(url, output):
    return download_url(
        url,
        output,
        MAX_AUDIO_SIZE
    )


def download_image(url, output):
    return download_url(
        url,
        output,
        MAX_COVER_SIZE
    )


# =========================================================
# تبدیل کاور به JPG
# =========================================================

def convert_to_jpg(input_file, output_file):

    try:

        with Image.open(input_file) as img:

            if img.mode in (
                "RGBA",
                "LA",
                "P"
            ):
                background = Image.new(
                    "RGB",
                    img.size,
                    "white"
                )

                if img.mode == "P":
                    img = img.convert("RGBA")

                background.paste(
                    img,
                    mask=img.getchannel("A")
                    if "A" in img.getbands()
                    else None
                )

                img = background

            else:
                img = img.convert("RGB")

            img.save(
                output_file,
                "JPEG",
                quality=92
            )

        return True

    except Exception as e:
        print("IMAGE ERROR:", e)
        return False


# =========================================================
# ویرایش MP3
# =========================================================

def edit_mp3(
    input_file,
    output_file,
    title,
    artist,
    cover_file=None
):

    try:

        audio = MP3(input_file)

        try:
            audio.add_tags()
        except:
            pass

        tags = audio.tags

        if tags is None:
            audio.add_tags()
            tags = audio.tags

        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.delall("APIC")

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

        if cover_file and os.path.exists(cover_file):

            with open(
                cover_file,
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

        audio.save()

        os.replace(
            input_file,
            output_file
        )

        return True

    except Exception as e:
        print("MP3 EDIT ERROR:", e)
        return False


# =========================================================
# ساخت کلید یکتا برای فایل
# =========================================================

def make_cache_key(
    kind,
    title="",
    artist="",
    source=""
):

    raw = "|".join([
        str(kind),
        str(title),
        str(artist),
        str(source)
    ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# =========================================================
# ذخیره مرجع فایل ارسال‌شده
# =========================================================

def save_cache(
    key,
    kind,
    file_id,
    caption="",
    button_text=None
):

    cache[key] = {
        "kind": kind,
        "file_id": file_id,
        "caption": caption,
        "button_text": button_text
    }

    save_json(
        CACHE_FILE,
        cache
    )


# =========================================================
# حذف پیام راهنمای قبلی ربات
# =========================================================

async def delete_previous_prompt(chat_id):

    chat_id = str(chat_id)

    old_id = prompt_messages.get(chat_id)

    if not old_id:
        return

    try:
        await bot.delete_message(
            chat_id,
            old_id
        )
    except Exception as e:
        print("DELETE PROMPT:", e)

    prompt_messages.pop(
        chat_id,
        None
    )


# =========================================================
# ارسال راهنما
# =========================================================

async def prompt(
    chat_id,
    text,
    keypad=None,
    inline_keypad=None
):

    chat_id = str(chat_id)

    await delete_previous_prompt(chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=text,
        chat_keypad=keypad,
        inline_keypad=inline_keypad
    )

    try:
        message_id = getattr(
            msg,
            "message_id",
            None
        )

        if message_id:
            prompt_messages[chat_id] = message_id

    except:
        pass

    return msg


# =========================================================
# کیبورد اصلی
# =========================================================

def main_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="make_banner",
            text="🖼 ساخت بنر"
        ),
        builder.button(
            id="edit_music",
            text="🎵 ادیت آهنگ"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


# =========================================================
# کیبورد بله / نه
# =========================================================

def yes_no_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="preview_yes",
            text="بله"
        ),
        builder.button(
            id="preview_no",
            text="نه"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


# =========================================================
# کیبورد نوع خروجی
# =========================================================

def type_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="song",
            text="🎵 آهنگ"
        ),
        builder.button(
            id="voice",
            text="🎤 ویس"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


# =========================================================
# کیبورد بعدی
# =========================================================

def next_keyboard():

    builder = ChatKeypadBuilder()

    builder.row(
        builder.button(
            id="next",
            text="بعدی"
        )
    )

    return builder.build(
        resize_keyboard=True
    )


# =========================================================
# دکمه شیشه‌ای
# =========================================================

def make_glass_button(text):

    builder = InlineBuilder()

    try:

        builder.button_simple(
            id="display_button",
            text=text
        )

    except Exception:

        builder.button(
            id="display_button",
            text=text
        )

    return builder.build()


# =========================================================
# ارسال فایل با file_id
# =========================================================

async def send_cached_file(
    chat_id,
    data
):

    chat_id = str(chat_id)

    kind = data.get("kind")
    file_id = data.get("file_id")
    caption = data.get(
        "caption",
        ""
    )

    button_text = data.get(
        "button_text"
    )

    inline_keypad = None

    if button_text:
        inline_keypad = make_glass_button(
            button_text
        )

    try:

        if kind == "music":

            return await bot.send_music(
                chat_id=chat_id,
                file_id=file_id,
                text=caption,
                inline_keypad=inline_keypad
            )

        if kind == "voice":

            return await bot.send_voice(
                chat_id=chat_id,
                file_id=file_id,
                text=caption,
                inline_keypad=inline_keypad
            )

        if kind == "image":

            return await bot.send_image(
                chat_id=chat_id,
                file_id=file_id,
                text=caption,
                inline_keypad=inline_keypad
            )

    except Exception as e:

        print("CACHE SEND ERROR:", e)

        return None


# =========================================================
# ارسال فایل اولیه و ثبت file_id
# =========================================================

async def send_and_cache_music(
    chat_id,
    file_path,
    caption,
    button_text,
    cache_key
):

    inline_keypad = None

    if button_text:
        inline_keypad = make_glass_button(
            button_text
        )

    msg = await bot.send_music(
        chat_id=str(chat_id),
        path=file_path,
        text=caption,
        inline_keypad=inline_keypad
    )

    file_id = getattr(
        msg,
        "file_id",
        None
    )

    if not file_id:

        try:
            file_id = msg.music.file_id
        except:
            pass

    if file_id:

        save_cache(
            cache_key,
            "music",
            file_id,
            caption,
            button_text
        )

    return msg


async def send_and_cache_voice(
    chat_id,
    file_path,
    caption,
    button_text,
    cache_key
):

    inline_keypad = None

    if button_text:
        inline_keypad = make_glass_button(
            button_text
        )

    msg = await bot.send_voice(
        chat_id=str(chat_id),
        path=file_path,
        text=caption,
        inline_keypad=inline_keypad
    )

    file_id = getattr(
        msg,
        "file_id",
        None
    )

    if not file_id:

        try:
            file_id = msg.voice.file_id
        except:
            pass

    if file_id:

        save_cache(
            cache_key,
            "voice",
            file_id,
            caption,
            button_text
        )

    return msg


async def send_and_cache_image(
    chat_id,
    file_path,
    caption,
    button_text,
    cache_key
):

    inline_keypad = None

    if button_text:
        inline_keypad = make_glass_button(
            button_text
        )

    msg = await bot.send_image(
        chat_id=str(chat_id),
        path=file_path,
        text=caption,
        inline_keypad=inline_keypad
    )

    file_id = getattr(
        msg,
        "file_id",
        None
    )

    if not file_id:

        try:
            file_id = msg.image.file_id
        except:
            pass

    if file_id:

        save_cache(
            cache_key,
            "image",
            file_id,
            caption,
            button_text
        )

    return msg


# =========================================================
# /start
# =========================================================

@bot.on_message()
async def handler(message: Message):

    try:

        chat_id = str(message.chat_id)
        text = (
            getattr(
                message,
                "text",
                ""
            )
            or ""
        ).strip()

        register_user(chat_id)

        # ---------------------------------------------
        # آخرین کاربر فعال
        # ---------------------------------------------

        # این مقدار فقط برای ثبت آخرین تعامل نگه داشته می‌شود.
        # ارسال واقعی همیشه به chat_id همان درخواست‌کننده است.

        user = user_data.setdefault(
            chat_id,
            {}
        )

        user["active"] = True


        # =================================================
        # START
        # =================================================

        if text == "/start":

            user_data[chat_id] = {
                "step": "main"
            }

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

            return


        # =================================================
        # باز ارسال
        # =================================================

        if text in (
            "باز ارسال",
            "بازارسال",
            "ارسال مجدد"
        ):

            reply = getattr(
                message,
                "reply_to_message",
                None
            )

            if not reply:

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            replied_message_id = getattr(
                reply,
                "message_id",
                None
            )

            if not replied_message_id:

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            found = None

            # پیام‌های ذخیره‌شده را بررسی می‌کنیم
            for key, item in cache.items():

                if str(
                    item.get(
                        "message_id",
                        ""
                    )
                ) == str(replied_message_id):

                    found = item
                    break

            if not found:

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            result = await send_cached_file(
                chat_id,
                found
            )

            if result:

                await prompt(
                    chat_id,
                    "✅",
                    main_keyboard()
                )

            else:

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

            return


        # =================================================
        # ساخت بنر
        # =================================================

        if text == "🖼 ساخت بنر":

            user_data[chat_id] = {
                "step": "banner_url"
            }

            await prompt(
                chat_id,
                "🔗"
            )

            return


        # =================================================
        # ادیت آهنگ
        # =================================================

        if text == "🎵 ادیت آهنگ":

            user_data[chat_id] = {
                "step": "music_url"
            }

            await prompt(
                chat_id,
                "🔗"
            )

            return


        step = user.get(
            "step"
        )


        # =================================================
        # لینک آهنگ
        # =================================================

        if step == "music_url":

            url = extract_url(text)

            if not url:

                await prompt(
                    chat_id,
                    "❌"
                )

                return

            user["url"] = url
            user["step"] = "music_preview"

            await prompt(
                chat_id,
                "پیش‌نمایش لازم دارید؟",
                yes_no_keyboard()
            )

            return


        # =================================================
        # بله / نه پیش نمایش آهنگ
        # =================================================

        if step == "music_preview":

            if text == "بله":

                file_path = (
                    f"audio_{chat_id}.mp3"
                )

                ok = await run_blocking(
                    download_audio,
                    user["url"],
                    file_path
                )

                if not ok:

                    await prompt(
                        chat_id,
                        "❌"
                    )

                    return

                user["audio_path"] = file_path

                # پیش‌نمایش برای همان درخواست‌کننده
                try:

                    await bot.send_music(
                        chat_id=chat_id,
                        path=file_path,
                        text="👀"
                    )

                except Exception as e:

                    print(
                        "PREVIEW ERROR:",
                        e
                    )

                user["step"] = "music_caption"

                await prompt(
                    chat_id,
                    "✏️"
                )

                return


            if text == "نه":

                file_path = (
                    f"audio_{chat_id}.mp3"
                )

                ok = await run_blocking(
                    download_audio,
                    user["url"],
                    file_path
                )

                if not ok:

                    await prompt(
                        chat_id,
                        "❌"
                    )

                    return

                user["audio_path"] = file_path
                user["step"] = "music_caption"

                await prompt(
                    chat_id,
                    "✏️"
                )

                return


        # =================================================
        # کپشن آهنگ
        # =================================================

        if step == "music_caption":

            if text == "بعدی":

                user["caption"] = DEFAULT_CAPTION

            else:

                user["caption"] = text

            user["step"] = "music_type"

            await prompt(
                chat_id,
                "🎵",
                type_keyboard()
            )

            return


        # =================================================
        # انتخاب آهنگ
        # =================================================

        if step == "music_type" and text == "🎵 آهنگ":

            user["step"] = "music_title"

            await prompt(
                chat_id,
                "🎵"
            )

            return


        # =================================================
        # اسم آهنگ
        # =================================================

        if step == "music_title":

            user["title"] = text
            user["step"] = "music_artist"

            await prompt(
                chat_id,
                "🎤"
            )

            return


        # =================================================
        # خواننده
        # =================================================

        if step == "music_artist":

            user["artist"] = text
            user["step"] = "music_cover"

            await prompt(
                chat_id,
                "🖼️",
                next_keyboard()
            )

            return


        # =================================================
        # کاور
        # =================================================

        if step == "music_cover":

            cover_path = None

            if text != "بعدی":

                url = extract_url(text)

                if not url:

                    await prompt(
                        chat_id,
                        "❌",
                        next_keyboard()
                    )

                    return

                original_cover = (
                    f"cover_{chat_id}"
                )

                jpg_cover = (
                    f"cover_{chat_id}.jpg"
                )

                ok = await run_blocking(
                    download_image,
                    url,
                    original_cover
                )

                if not ok:

                    await prompt(
                        chat_id,
                        "❌",
                        next_keyboard()
                    )

                    return

                ok = await run_blocking(
                    convert_to_jpg,
                    original_cover,
                    jpg_cover
                )

                if not ok:

                    await prompt(
                        chat_id,
                        "❌",
                        next_keyboard()
                    )

                    return

                cover_path = jpg_cover

            user["cover_path"] = cover_path
            user["step"] = "music_button"

            await prompt(
                chat_id,
                "🔘",
                next_keyboard()
            )

            return


        # =================================================
        # متن دکمه آهنگ
        # =================================================

        if step == "music_button":

            button_text = None

            if text != "بعدی":
                button_text = text

            audio_path = user.get(
                "audio_path"
            )

            title = user.get(
                "title",
                "song"
            )

            artist = user.get(
                "artist",
                ""
            )

            cover_path = user.get(
                "cover_path"
            )

            if not audio_path or not os.path.exists(
                audio_path
            ):

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            safe_title = re.sub(
                r'[\\/:*?"<>|]+',
                "_",
                title
            ).strip()

            if not safe_title:
                safe_title = "song"

            output_file = (
                f"{safe_title}.mp3"
            )

            ok = await run_blocking(
                edit_mp3,
                audio_path,
                output_file,
                title,
                artist,
                cover_path
            )

            if not ok:

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            cache_key = make_cache_key(
                "music",
                title,
                artist,
                user.get("url", "")
            )

            # اگر قبلاً همین خروجی وجود داشته،
            # از file_id ذخیره‌شده استفاده می‌کنیم.
            if cache_key in cache:

                await send_cached_file(
                    chat_id,
                    cache[cache_key]
                )

            else:

                msg = await send_and_cache_music(
                    chat_id,
                    output_file,
                    user.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    button_text,
                    cache_key
                )

                # message_id خروجی ربات را ذخیره می‌کنیم
                try:

                    message_id = getattr(
                        msg,
                        "message_id",
                        None
                    )

                    if message_id:

                        cache[cache_key][
                            "message_id"
                        ] = message_id

                        save_json(
                            CACHE_FILE,
                            cache
                        )

                except:
                    pass

            await prompt(
                chat_id,
                "✅",
                main_keyboard()
            )

            return


        # =================================================
        # انتخاب ویس
        # =================================================

        if step == "music_type" and text == "🎤 ویس":

            user["step"] = "voice_button"

            await prompt(
                chat_id,
                "🔘",
                next_keyboard()
            )

            return


        # =================================================
        # دکمه ویس
        # =================================================

        if step == "voice_button":

            button_text = None

            if text != "بعدی":
                button_text = text

            audio_path = user.get(
                "audio_path"
            )

            if not audio_path or not os.path.exists(
                audio_path
            ):

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            cache_key = make_cache_key(
                "voice",
                source=user.get(
                    "url",
                    ""
                )
            )

            if cache_key in cache:

                await send_cached_file(
                    chat_id,
                    cache[cache_key]
                )

            else:

                msg = await send_and_cache_voice(
                    chat_id,
                    audio_path,
                    user.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    button_text,
                    cache_key
                )

                try:

                    message_id = getattr(
                        msg,
                        "message_id",
                        None
                    )

                    if message_id:

                        cache[cache_key][
                            "message_id"
                        ] = message_id

                        save_json(
                            CACHE_FILE,
                            cache
                        )

                except:
                    pass

            await prompt(
                chat_id,
                "✅",
                main_keyboard()
            )

            return


        # =================================================
        # لینک بنر
        # =================================================

        if step == "banner_url":

            url = extract_url(text)

            if not url:

                await prompt(
                    chat_id,
                    "❌"
                )

                return

            user["url"] = url
            user["step"] = "banner_preview"

            await prompt(
                chat_id,
                "پیش‌نمایش لازم دارید؟",
                yes_no_keyboard()
            )

            return


        # =================================================
        # پیش نمایش بنر
        # =================================================

        if step == "banner_preview":

            if text not in (
                "بله",
                "نه"
            ):

                return

            image_path = (
                f"banner_{chat_id}.jpg"
            )

            original = (
                f"banner_{chat_id}.tmp"
            )

            ok = await run_blocking(
                download_image,
                user["url"],
                original
            )

            if not ok:

                await prompt(
                    chat_id,
                    "❌"
                )

                return

            ok = await run_blocking(
                convert_to_jpg,
                original,
                image_path
            )

            if not ok:

                await prompt(
                    chat_id,
                    "❌"
                )

                return

            user["image_path"] = image_path

            if text == "بله":

                try:

                    await bot.send_image(
                        chat_id=chat_id,
                        path=image_path,
                        text="👀"
                    )

                except Exception as e:

                    print(
                        "BANNER PREVIEW:",
                        e
                    )

            user["step"] = "banner_caption"

            await prompt(
                chat_id,
                "✏️"
            )

            return


        # =================================================
        # کپشن بنر
        # =================================================

        if step == "banner_caption":

            if text == "بعدی":
                user["caption"] = DEFAULT_CAPTION
            else:
                user["caption"] = text

            user["step"] = "banner_button"

            await prompt(
                chat_id,
                "🔘",
                next_keyboard()
            )

            return


        # =================================================
        # دکمه بنر
        # =================================================

        if step == "banner_button":

            button_text = None

            if text != "بعدی":
                button_text = text

            image_path = user.get(
                "image_path"
            )

            if not image_path or not os.path.exists(
                image_path
            ):

                await prompt(
                    chat_id,
                    "❌",
                    main_keyboard()
                )

                return

            cache_key = make_cache_key(
                "image",
                source=user.get(
                    "url",
                    ""
                )
            )

            if cache_key in cache:

                await send_cached_file(
                    chat_id,
                    cache[cache_key]
                )

            else:

                msg = await send_and_cache_image(
                    chat_id,
                    image_path,
                    user.get(
                        "caption",
                        DEFAULT_CAPTION
                    ),
                    button_text,
                    cache_key
                )

                try:

                    message_id = getattr(
                        msg,
                        "message_id",
                        None
                    )

                    if message_id:

                        cache[cache_key][
                            "message_id"
                        ] = message_id

                        save_json(
                            CACHE_FILE,
                            cache
                        )

                except:
                    pass

            await prompt(
                chat_id,
                "✅",
                main_keyboard()
            )

            return


        # =================================================
        # متن ناشناخته
        # =================================================

        if text:

            await prompt(
                chat_id,
                "👇",
                main_keyboard()
            )

    except Exception as e:

        print(
            "BOT ERROR:",
            repr(e)
        )

        try:

            await prompt(
                str(message.chat_id),
                "❌",
                main_keyboard()
            )

        except:
            pass


# =========================================================
# اجرای ربات
# =========================================================

print("🤖 Bot started...")

bot.run()
