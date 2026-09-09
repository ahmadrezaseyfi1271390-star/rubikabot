import os
import re
import json
import time
import asyncio
import requests
import gdown

from PIL import Image
from mutagen.id3 import ID3, TIT2, TPE1, APIC
from mutagen.mp3 import MP3

from rubka import Robot, Message
from rubka.button import InlineBuilder


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

# آیدی عددی سازنده ربات را اینجا بگذار
OWNER_ID = 123456789

MAX_AUDIO_SIZE = 200 * 1024 * 1024
MAX_COVER_SIZE = 10 * 1024 * 1024

USERS_FILE = "users.json"

DEFAULT_CAPTION = "@Black_list_remix"

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


bot = Robot(
    token=TOKEN,
    parse_mode="HTML"
)


# =========================================================
# وضعیت کاربران
# =========================================================

user_states = {}


# =========================================================
# کاربران
# =========================================================

def load_users():

    if not os.path.exists(USERS_FILE):
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}


def save_users(users):

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            users,
            f,
            ensure_ascii=False,
            indent=2
        )


def register_user(chat_id):

    users = load_users()

    chat_id = str(chat_id)

    if chat_id not in users:

        users[chat_id] = {
            "messages": 0,
            "last_message": 0
        }

        save_users(users)


def count_user_message(chat_id):

    users = load_users()

    chat_id = str(chat_id)

    if chat_id not in users:

        users[chat_id] = {
            "messages": 0,
            "last_message": 0
        }

    users[chat_id]["messages"] += 1
    users[chat_id]["last_message"] = int(time.time())

    save_users(users)


def get_users_by_activity():

    users = load_users()

    result = []

    for chat_id, data in users.items():

        try:

            result.append(
                (
                    int(chat_id),
                    int(data.get("messages", 0)),
                    int(data.get("last_message", 0))
                )
            )

        except Exception:
            pass

    # بیشترین پیام اول
    # در صورت مساوی بودن، آخرین فعالیت جدیدتر اول
    result.sort(
        key=lambda x: (x[1], x[2]),
        reverse=True
    )

    return [x[0] for x in result]


# =========================================================
# کیبورد اصلی
# =========================================================

def main_keyboard():

    return bot.build_keypad(
        [
            [
                ("🖼 ساخت بنر", "🖼 ساخت بنر"),
                ("🎵 ادیت آهنگ", "🎵 ادیت آهنگ")
            ]
        ]
    )


# =========================================================
# دکمه بعدی
# =========================================================

def next_keyboard():

    return bot.build_keypad(
        [
            [
                ("بعدی", "بعدی")
            ]
        ]
    )


# =========================================================
# انتخاب آهنگ / ویس
# =========================================================

def music_type_keyboard():

    return bot.build_keypad(
        [
            [
                ("🎵 آهنگ", "🎵 آهنگ"),
                ("🎤 ویس", "🎤 ویس")
            ]
        ]
    )


# =========================================================
# دکمه شیشه‌ای نمایشی
#
# اینجا از button معمولی Inline استفاده شده.
# هیچ URL ندارد.
# =========================================================

def make_glass_button(text):

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

        print("Glass button error:", e)

        return None


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

    return match.group(0).strip()


# =========================================================
# تشخیص Google Drive
# =========================================================

def is_google_drive(url):

    if not url:
        return False

    return (
        "drive.google.com" in url
        or "docs.google.com" in url
    )


# =========================================================
# دانلود فایل
# =========================================================

def download_file(url, output_path, max_size):

    try:

        # Google Drive
        if is_google_drive(url):

            print("Google Drive download...")

            gdown.download(
                url,
                output_path,
                quiet=False
            )

            if not os.path.exists(output_path):
                return False

            size = os.path.getsize(output_path)

            if size > max_size:

                try:
                    os.remove(output_path)
                except:
                    pass

                return False

            return True

        # Direct URL
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=60
        )

        response.raise_for_status()

        total = 0

        with open(output_path, "wb") as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                total += len(chunk)

                if total > max_size:

                    try:
                        f.close()
                    except:
                        pass

                    try:
                        os.remove(output_path)
                    except:
                        pass

                    return False

                f.write(chunk)

        return True

    except Exception as e:

        print("Download error:", e)

        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass

        return False


# =========================================================
# دانلود کاور
# =========================================================

def download_cover(url, output_path):

    temp_path = output_path + "_temp"

    try:

        if not download_file(
            url,
            temp_path,
            MAX_COVER_SIZE
        ):
            return False

        image = Image.open(temp_path)

        image = image.convert("RGB")

        image.save(
            output_path,
            "JPEG",
            quality=95
        )

        try:
            os.remove(temp_path)
        except:
            pass

        return True

    except Exception as e:

        print("Cover error:", e)

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

        return False


# =========================================================
# متادیتای MP3
# =========================================================

def set_mp3_metadata(
    audio_path,
    title,
    singer,
    cover_path=None
):

    try:

        try:
            audio = MP3(audio_path, ID3=ID3)

        except Exception:
            audio = MP3(audio_path)

        try:
            audio.add_tags()
        except:
            pass

        tags = audio.tags

        if tags is None:
            audio.add_tags()
            tags = audio.tags

        # عنوان
        if title:
            tags.delall("TIT2")
            tags.add(
                TIT2(
                    encoding=3,
                    text=title
                )
            )

        # خواننده
        if singer:
            tags.delall("TPE1")
            tags.add(
                TPE1(
                    encoding=3,
                    text=singer
                )
            )

        # کاور
        if cover_path and os.path.exists(cover_path):

            with open(
                cover_path,
                "rb"
            ) as f:

                cover_data = f.read()

            tags.delall("APIC")

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

        return True

    except Exception as e:

        print("Metadata error:", e)

        return False


# =========================================================
# تغییر نام آهنگ
# =========================================================

def safe_filename(name):

    if not name:
        return "song"

    name = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        name
    )

    name = name.strip()

    if not name:
        name = "song"

    return name


# =========================================================
# ارسال مستقیم آهنگ به همه
# =========================================================

async def broadcast_music(
    audio_path,
    caption,
    inline_keypad
):

    users = get_users_by_activity()

    print("Broadcast music:", users)

    # -----------------------------------------
    # اول مالک
    # -----------------------------------------

    try:

        await bot.send_music(
            chat_id=OWNER_ID,
            path=audio_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        print("Music sent to owner")

    except Exception as e:

        print("Owner music error:", e)

    # -----------------------------------------
    # بعد کاربران
    # -----------------------------------------

    for chat_id in users:

        if chat_id == OWNER_ID:
            continue

        try:

            await bot.send_music(
                chat_id=chat_id,
                path=audio_path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Music sent:",
                chat_id
            )

        except Exception as e:

            print(
                "Music error:",
                chat_id,
                e
            )

        await asyncio.sleep(0.3)


# =========================================================
# ارسال مستقیم ویس به همه
# =========================================================

async def broadcast_voice(
    audio_path,
    caption,
    inline_keypad
):

    users = get_users_by_activity()

    print("Broadcast voice:", users)

    # مالک
    try:

        await bot.send_voice(
            chat_id=OWNER_ID,
            path=audio_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        print("Voice sent to owner")

    except Exception as e:

        print("Owner voice error:", e)

    # کاربران
    for chat_id in users:

        if chat_id == OWNER_ID:
            continue

        try:

            await bot.send_voice(
                chat_id=chat_id,
                path=audio_path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Voice sent:",
                chat_id
            )

        except Exception as e:

            print(
                "Voice error:",
                chat_id,
                e
            )

        await asyncio.sleep(0.3)


# =========================================================
# ارسال مستقیم بنر به همه
# =========================================================

async def broadcast_banner(
    image_path,
    caption,
    inline_keypad
):

    users = get_users_by_activity()

    print("Broadcast banner:", users)

    # مالک
    try:

        await bot.send_image(
            chat_id=OWNER_ID,
            path=image_path,
            text=caption,
            inline_keypad=inline_keypad
        )

        print("Banner sent to owner")

    except Exception as e:

        print("Owner banner error:", e)

    # کاربران
    for chat_id in users:

        if chat_id == OWNER_ID:
            continue

        try:

            await bot.send_image(
                chat_id=chat_id,
                path=image_path,
                text=caption,
                inline_keypad=inline_keypad
            )

            print(
                "Banner sent:",
                chat_id
            )

        except Exception as e:

            print(
                "Banner error:",
                chat_id,
                e
            )

        await asyncio.sleep(0.3)


# =========================================================
# پایان ساخت بنر
# =========================================================

async def finish_banner(chat_id):

    state = user_states.get(chat_id)

    if not state:
        return

    image_path = state.get("image_path")
    caption = state.get("caption", DEFAULT_CAPTION)

    button_text = state.get("button_text")

    inline_keypad = None

    if button_text:
        inline_keypad = make_glass_button(
            button_text
        )

    # -----------------------------------------
    # ارسال
    # -----------------------------------------

    if image_path and os.path.exists(image_path):

        await broadcast_banner(
            image_path,
            caption,
            inline_keypad
        )

    else:

        # اگر تصویر انتخاب نشده باشد
        users = get_users_by_activity()

        try:

            await bot.send_message(
                chat_id=OWNER_ID,
                text=caption,
                inline_keypad=inline_keypad
            )

        except Exception as e:
            print("Owner text error:", e)

        for user_id in users:

            if user_id == OWNER_ID:
                continue

            try:

                await bot.send_message(
                    chat_id=user_id,
                    text=caption,
                    inline_keypad=inline_keypad
                )

            except Exception as e:

                print(
                    "Text broadcast error:",
                    user_id,
                    e
                )

            await asyncio.sleep(0.3)

    # -----------------------------------------
    # پاک کردن فایل
    # -----------------------------------------

    if image_path:

        try:

            if os.path.exists(image_path):
                os.remove(image_path)

        except:
            pass

    user_states.pop(chat_id, None)

    # -----------------------------------------
    # پایان
    # -----------------------------------------

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text="✅"
        )

    except:
        pass


# =========================================================
# پایان آهنگ
# =========================================================

async def finish_music(chat_id):

    state = user_states.get(chat_id)

    if not state:
        return

    audio_path = state.get("audio_path")
    cover_path = state.get("cover_path")

    title = state.get("title")
    singer = state.get("singer")

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    button_text = state.get("button_text")

    # -----------------------------------------
    # متادیتا
    # -----------------------------------------

    if audio_path and os.path.exists(audio_path):

        set_mp3_metadata(
            audio_path,
            title,
            singer,
            cover_path
        )

        # تغییر نام
        if title:

            new_name = (
                safe_filename(title)
                + ".mp3"
            )

            new_path = os.path.join(
                DOWNLOAD_DIR,
                new_name
            )

            # اگر همان فایل نبود
            try:

                if os.path.abspath(
                    new_path
                ) != os.path.abspath(
                    audio_path
                ):

                    if os.path.exists(new_path):
                        os.remove(new_path)

                    os.rename(
                        audio_path,
                        new_path
                    )

                    audio_path = new_path

            except Exception as e:

                print(
                    "Rename error:",
                    e
                )

    inline_keypad = None

    if button_text:

        inline_keypad = make_glass_button(
            button_text
        )

    # -----------------------------------------
    # ارسال مستقیم
    # -----------------------------------------

    if audio_path and os.path.exists(audio_path):

        await broadcast_music(
            audio_path,
            caption,
            inline_keypad
        )

    # -----------------------------------------
    # پاک کردن
    # -----------------------------------------

    try:

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

    except:
        pass

    try:

        if cover_path and os.path.exists(cover_path):
            os.remove(cover_path)

    except:
        pass

    user_states.pop(chat_id, None)

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text="✅"
        )

    except:
        pass


# =========================================================
# پایان ویس
# =========================================================

async def finish_voice(chat_id):

    state = user_states.get(chat_id)

    if not state:
        return

    audio_path = state.get("audio_path")

    caption = state.get(
        "caption",
        DEFAULT_CAPTION
    )

    button_text = state.get("button_text")

    inline_keypad = None

    if button_text:

        inline_keypad = make_glass_button(
            button_text
        )

    if audio_path and os.path.exists(audio_path):

        await broadcast_voice(
            audio_path,
            caption,
            inline_keypad
        )

    try:

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

    except:
        pass

    user_states.pop(chat_id, None)

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text="✅"
        )

    except:
        pass


# =========================================================
# دریافت پیام
# =========================================================

@bot.on_message()
async def handle_message(
    bot: Robot,
    message: Message
):

    chat_id = getattr(
        message,
        "chat_id",
        None
    )

    if chat_id is None:
        return

    chat_id = int(chat_id)

    text = getattr(
        message,
        "text",
        ""
    ) or ""

    text = text.strip()

    # -----------------------------------------
    # ثبت کاربر
    # -----------------------------------------

    register_user(chat_id)

    count_user_message(chat_id)

    # -----------------------------------------
    # /start
    # -----------------------------------------

    if text == "/start":

        user_states.pop(
            chat_id,
            None
        )

        await bot.send_message(
            chat_id=chat_id,
            text="سلام 👋",
            chat_keypad=main_keyboard()
        )

        return

    # -----------------------------------------
    # منوی اصلی
    # -----------------------------------------

    if text == "🖼 ساخت بنر":

        user_states[chat_id] = {
            "type": "banner",
            "step": "image"
        }

        await bot.send_message(
            chat_id=chat_id,
            text="🖼",
            chat_keypad=next_keyboard()
        )

        return

    if text == "🎵 ادیت آهنگ":

        user_states[chat_id] = {
            "type": "audio",
            "step": "url"
        }

        await bot.send_message(
            chat_id=chat_id,
            text="🎵",
            chat_keypad=next_keyboard()
        )

        return

    # -----------------------------------------
    # اگر وضعیت ندارد
    # -----------------------------------------

    if chat_id not in user_states:

        await bot.send_message(
            chat_id=chat_id,
            text="یکی از گزینه‌ها را انتخاب کن.",
            chat_keypad=main_keyboard()
        )

        return

    state = user_states[chat_id]

    step = state.get("step")

    # =====================================================
    # بنر
    # =====================================================

    if state.get("type") == "banner":

        # -----------------------------------------
        # لینک تصویر
        # -----------------------------------------

        if step == "image":

            if text == "بعدی":

                state["image_path"] = None
                state["step"] = "caption"

                await bot.send_message(
                    chat_id=chat_id,
                    text="✏️",
                    chat_keypad=next_keyboard()
                )

                return

            url = extract_url(text)

            if not url:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            image_path = os.path.join(
                DOWNLOAD_DIR,
                f"banner_{chat_id}_{int(time.time())}.jpg"
            )

            if not download_file(
                url,
                image_path,
                MAX_COVER_SIZE
            ):

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            state["image_path"] = image_path
            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text="✏️",
                chat_keypad=next_keyboard()
            )

            return

        # -----------------------------------------
        # کپشن
        # -----------------------------------------

        if step == "caption":

            if text == "بعدی":

                state["caption"] = DEFAULT_CAPTION

            else:

                state["caption"] = text

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # -----------------------------------------
        # متن دکمه
        # -----------------------------------------

        if step == "button_text":

            if text == "بعدی":

                state["button_text"] = None
                await finish_banner(chat_id)
                return

            state["button_text"] = text
            state["step"] = "button_url"

            await bot.send_message(
                chat_id=chat_id,
                text="🔗",
                chat_keypad=next_keyboard()
            )

            return

        # -----------------------------------------
        # لینک دکمه
        #
        # برای دکمه نمایشی استفاده نمی‌شود.
        # فقط برای حفظ روند قبلی، این مرحله
        # وجود ندارد و بعدی مستقیماً پایان می‌دهد.
        # -----------------------------------------

        if step == "button_url":

            # این بخش عملاً برای دکمه نمایشی استفاده نمی‌شود
            # و هر چیزی که فرستاده شود نادیده گرفته می‌شود.

            await finish_banner(chat_id)

            return

    # =====================================================
    # آهنگ / ویس
    # =====================================================

    if state.get("type") == "audio":

        # -----------------------------------------
        # لینک دانلود
        # -----------------------------------------

        if step == "url":

            url = extract_url(text)

            if not url:

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            extension = ".mp3"

            audio_path = os.path.join(
                DOWNLOAD_DIR,
                f"audio_{chat_id}_{int(time.time())}{extension}"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳"
            )

            if not download_file(
                url,
                audio_path,
                MAX_AUDIO_SIZE
            ):

                await bot.send_message(
                    chat_id=chat_id,
                    text="❌"
                )

                return

            state["audio_path"] = audio_path
            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text="✏️",
                chat_keypad=next_keyboard()
            )

            return

        # -----------------------------------------
        # کپشن
        # -----------------------------------------

        if step == "caption":

            if text == "بعدی":

                state["caption"] = DEFAULT_CAPTION

            else:

                state["caption"] = text

            state["step"] = "media_type"

            await bot.send_message(
                chat_id=chat_id,
                text="انتخاب کن:",
                chat_keypad=music_type_keyboard()
            )

            return

        # -----------------------------------------
        # انتخاب آهنگ
        # -----------------------------------------

        if step == "media_type":

            if text == "🎵 آهنگ":

                state["media_type"] = "music"
                state["step"] = "title"

                await bot.send_message(
                    chat_id=chat_id,
                    text="🎵 عنوان آهنگ:"
                )

                return

            if text == "🎤 ویس":

                state["media_type"] = "voice"
                state["step"] = "button_text"

                await bot.send_message(
                    chat_id=chat_id,
                    text="🔘",
                    chat_keypad=next_keyboard()
                )

                return

            return

        # -----------------------------------------
        # عنوان
        # -----------------------------------------

        if step == "title":

            state["title"] = text
            state["step"] = "singer"

            await bot.send_message(
                chat_id=chat_id,
                text="🎤 نام خواننده:"
            )

            return

        # -----------------------------------------
        # خواننده
        # -----------------------------------------

        if step == "singer":

            state["singer"] = text
            state["step"] = "cover"

            await bot.send_message(
                chat_id=chat_id,
                text="🖼",
                chat_keypad=next_keyboard()
            )

            return

        # -----------------------------------------
        # کاور
        # -----------------------------------------

        if step == "cover":

            if text == "بعدی":

                state["cover_path"] = None

            else:

                url = extract_url(text)

                if not url:

                    await bot.send_message(
                        chat_id=chat_id,
                        text="❌"
                    )

                    return

                cover_path = os.path.join(
                    DOWNLOAD_DIR,
                    f"cover_{chat_id}_{int(time.time())}.jpg"
                )

                if not download_cover(
                    url,
                    cover_path
                ):

                    await bot.send_message(
                        chat_id=chat_id,
                        text="❌"
                    )

                    return

                state["cover_path"] = cover_path

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text="🔘",
                chat_keypad=next_keyboard()
            )

            return

        # -----------------------------------------
        # متن دکمه شیشه‌ای
        # -----------------------------------------

        if step == "button_text":

            if text == "بعدی":

                state["button_text"] = None

            else:

                state["button_text"] = text

            # -------------------------------------
            # پایان
            # -------------------------------------

            if state.get("media_type") == "music":

                await finish_music(chat_id)

            else:

                await finish_voice(chat_id)

            return


# =========================================================
# اجرای ربات
# =========================================================

print("================================")
print("🤖 RUBKA MUSIC & BANNER BOT")
print("================================")
print("🚀 Bot is running...")

bot.run()
