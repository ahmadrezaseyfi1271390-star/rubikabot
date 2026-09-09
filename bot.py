import os
import re
import json
import uuid
import asyncio
import requests

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder

from mutagen.id3 import ID3, TIT2, TPE1, APIC


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

DEFAULT_CAPTION = "@Black_list_remix"

DEFAULT_COVER = (
    "https://i.supaimg.com/"
    "bc5adc11-7f47-4fe4-9ef2-138ec4d3868a/"
    "d5316146-c9e1-4bf1-bc05-88898b21c3a4.jpg"
)

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


def new_state():
    return {
        "step": "waiting",
        "query": "",
        "source_url": "",
        "current_message_id": None,
        "last_bot_message_id": None,
        "previous_results": [],
        "current_index": -1,

        "caption": DEFAULT_CAPTION,
        "title": "",
        "artist": "",
        "cover_url": DEFAULT_COVER,

        "audio_path": None,
        "cover_path": None,
    }


def get_state(user_id):
    user_id = str(user_id)

    if user_id not in user_data:
        user_data[user_id] = new_state()

    return user_data[user_id]


# =========================================================
# کاربران
# =========================================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception as e:
        print("users.json error:", repr(e))

    return []


def save_users(users):
    users = list(dict.fromkeys(str(x) for x in users))

    with open(USERS_FILE, "w", encoding="utf-8") as f:
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
# ابزارها
# =========================================================

async def safe_delete(chat_id, message_id):
    if not message_id:
        return

    try:
        await bot.delete_message(
            chat_id=str(chat_id),
            message_id=str(message_id)
        )
    except Exception as e:
        print("DELETE ERROR:", repr(e))


async def delete_previous_bot_message(chat_id, state):
    message_id = state.get("last_bot_message_id")

    if message_id:
        await safe_delete(
            chat_id,
            message_id
        )

        state["last_bot_message_id"] = None


async def send_text(chat_id, text, keypad=None):
    try:
        result = await bot.send_message(
            chat_id=str(chat_id),
            text=text,
            chat_keypad=keypad
        )

        return result

    except Exception as e:
        print("SEND TEXT ERROR:", repr(e))
        return None


def get_message_id(result):
    if result is None:
        return None

    for attr in (
        "message_id",
        "id"
    ):
        value = getattr(result, attr, None)

        if value:
            return str(value)

    if isinstance(result, dict):
        for key in (
            "message_id",
            "id"
        ):
            if result.get(key):
                return str(result[key])

    return None


# =========================================================
# کیبوردها
# =========================================================

def start_keyboard():
    return (
        ChatKeypadBuilder()
        .row(
            ChatKeypadBuilder().button(
                "search",
                "🔎 جستجو"
            )
        )
        .build()
    )


def result_keyboard():
    return (
        ChatKeypadBuilder()
        .row(
            ChatKeypadBuilder().button(
                "previous",
                "⬅️ قبلی"
            ),
            ChatKeypadBuilder().button(
                "edit",
                "✏️ ادیت"
            ),
            ChatKeypadBuilder().button(
                "next",
                "➡️ بعدی"
            )
        )
        .build()
    )


def type_keyboard():
    return (
        ChatKeypadBuilder()
        .row(
            ChatKeypadBuilder().button(
                "music",
                "🎵 آهنگ"
            ),
            ChatKeypadBuilder().button(
                "voice",
                "🎤 ویس"
            )
        )
        .build()
    )


def cancel_keyboard():
    return (
        ChatKeypadBuilder()
        .row(
            ChatKeypadBuilder().button(
                "cancel",
                "❌ لغو"
            )
        )
        .build()
    )


# =========================================================
# تشخیص لینک مستقیم
# =========================================================

def extract_url(text):
    if not text:
        return None

    match = re.search(
        r"https?://[^\s]+",
        text.strip()
    )

    if match:
        return match.group(0)

    return None


# =========================================================
# دانلود فایل
# =========================================================

def download_file(url):

    filename = os.path.basename(
        url.split("?")[0]
    )

    if not filename:
        filename = "audio.mp3"

    filename = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        filename
    )

    path = os.path.join(
        DOWNLOAD_FOLDER,
        f"{uuid.uuid4().hex}_{filename}"
    )

    try:

        with requests.get(
            url,
            stream=True,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        ) as response:

            response.raise_for_status()

            content_length = response.headers.get(
                "Content-Length"
            )

            if content_length:

                if int(content_length) > MAX_FILE_SIZE:
                    raise ValueError(
                        "FILE_TOO_LARGE"
                    )

            total = 0

            with open(path, "wb") as f:

                for chunk in response.iter_content(
                    chunk_size=1024 * 512
                ):

                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_FILE_SIZE:
                        raise ValueError(
                            "FILE_TOO_LARGE"
                        )

                    f.write(chunk)

        return path

    except Exception:

        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

        raise


# =========================================================
# دانلود کاور
# =========================================================

def download_cover(url):

    path = os.path.join(
        DOWNLOAD_FOLDER,
        f"cover_{uuid.uuid4().hex}.jpg"
    )

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        data = response.content

        if len(data) > MAX_COVER_SIZE:
            raise ValueError(
                "COVER_TOO_LARGE"
            )

        with open(path, "wb") as f:
            f.write(data)

        return path

    except Exception:

        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

        raise


# =========================================================
# metadata
# =========================================================

def set_metadata(
    file_path,
    title,
    artist,
    cover_path=None
):

    try:

        try:
            tags = ID3(file_path)
        except:
            tags = ID3()

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

        tags.save(file_path)

    except Exception as e:

        print(
            "METADATA ERROR:",
            repr(e)
        )

        raise


# =========================================================
# نتیجه جستجو
# =========================================================

async def search_allowed_source(query):
    """
    این تابع عمداً به Google/سایت‌های دانلود آهنگ
    وصل نمی‌شود.

    اینجا باید منبعی قرار بگیرد که اجازه دانلود
    و بازنشر محتوای آن را داری.

    خروجی مورد انتظار:

    [
        {
            "title": "نام آهنگ",
            "artist": "نام خواننده",
            "url": "https://example.com/file.mp3"
        }
    ]
    """

    # -----------------------------------------------------
    # فعلاً خالی است تا منبع مجاز خودت را مشخص کنی.
    # -----------------------------------------------------

    return []


# =========================================================
# نمایش نتیجه
# =========================================================

async def show_result(
    chat_id,
    state,
    index
):

    results = state.get(
        "previous_results",
        []
    )

    if not results:
        return

    if index < 0:
        index = 0

    if index >= len(results):
        index = len(results) - 1

    state["current_index"] = index

    item = results[index]

    title = item.get(
        "title",
        "بدون نام"
    )

    artist = item.get(
        "artist",
        "نامشخص"
    )

    url = item.get(
        "url",
        ""
    )

    state["source_url"] = url

    text = (
        "🎵 نتیجه جستجو\n\n"
        f"🎧 نام: {title}\n"
        f"👤 خواننده: {artist}\n\n"
        f"📌 نتیجه {index + 1} از {len(results)}"
    )

    await delete_previous_bot_message(
        chat_id,
        state
    )

    result = await send_text(
        chat_id,
        text,
        result_keyboard()
    )

    message_id = get_message_id(
        result
    )

    state["last_bot_message_id"] = message_id


# =========================================================
# شروع ادیت
# =========================================================

async def start_edit(
    chat_id,
    state
):

    results = state.get(
        "previous_results",
        []
    )

    index = state.get(
        "current_index",
        -1
    )

    if index < 0 or index >= len(results):

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "❌ نتیجه‌ای برای ادیت وجود ندارد."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    item = results[index]

    state["source_url"] = item.get(
        "url",
        ""
    )

    state["title"] = item.get(
        "title",
        ""
    )

    state["artist"] = item.get(
        "artist",
        ""
    )

    state["caption"] = DEFAULT_CAPTION
    state["step"] = "caption"

    await delete_previous_bot_message(
        chat_id,
        state
    )

    result = await send_text(
        chat_id,
        "📝 کپشن فایل را ارسال کن:",
        cancel_keyboard()
    )

    state["last_bot_message_id"] = (
        get_message_id(result)
    )


# =========================================================
# دانلود و آماده‌سازی
# =========================================================

async def prepare_audio(
    chat_id,
    state
):

    url = state.get(
        "source_url"
    )

    if not url:

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "❌ لینک فایل پیدا نشد."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return False

    await delete_previous_bot_message(
        chat_id,
        state
    )

    result = await send_text(
        chat_id,
        "⏳ در حال دریافت فایل..."
    )

    state["last_bot_message_id"] = (
        get_message_id(result)
    )

    try:

        path = await asyncio.to_thread(
            download_file,
            url
        )

        state["audio_path"] = path

        return True

    except ValueError as e:

        if str(e) == "FILE_TOO_LARGE":

            await delete_previous_bot_message(
                chat_id,
                state
            )

            result = await send_text(
                chat_id,
                "❌ حجم فایل بیشتر از ۲۰۰ مگابایت است."
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

        return False

    except Exception as e:

        print(
            "DOWNLOAD ERROR:",
            repr(e)
        )

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "❌ دانلود فایل انجام نشد."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return False


# =========================================================
# ارسال ویس
# =========================================================

async def send_voice_file(
    chat_id,
    state
):

    path = state.get(
        "audio_path"
    )

    if not path or not os.path.exists(path):

        ok = await prepare_audio(
            chat_id,
            state
        )

        if not ok:
            return

        path = state.get(
            "audio_path"
        )

    await delete_previous_bot_message(
        chat_id,
        state
    )

    try:

        result = await bot.send_voice(
            chat_id=str(chat_id),
            path=path,
            text=state.get(
                "caption",
                DEFAULT_CAPTION
            )
        )

        print(
            "VOICE SENT:",
            result
        )

        state["step"] = "waiting"

    except Exception as e:

        print(
            "VOICE SEND ERROR:",
            repr(e)
        )

        result = await send_text(
            chat_id,
            "❌ ارسال ویس انجام نشد."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )


# =========================================================
# ارسال آهنگ
# =========================================================

async def send_music_file(
    chat_id,
    state
):

    path = state.get(
        "audio_path"
    )

    if not path or not os.path.exists(path):

        ok = await prepare_audio(
            chat_id,
            state
        )

        if not ok:
            return

        path = state.get(
            "audio_path"
        )

    title = state.get(
        "title",
        "Unknown"
    )

    artist = state.get(
        "artist",
        "@Black_list_remix"
    )

    cover_url = state.get(
        "cover_url",
        DEFAULT_COVER
    )

    await delete_previous_bot_message(
        chat_id,
        state
    )

    result = await send_text(
        chat_id,
        "🖼️ در حال آماده‌سازی کاور..."
    )

    state["last_bot_message_id"] = (
        get_message_id(result)
    )

    try:

        cover_path = await asyncio.to_thread(
            download_cover,
            cover_url
        )

        state["cover_path"] = cover_path

        await asyncio.to_thread(
            set_metadata,
            path,
            title,
            artist,
            cover_path
        )

        await delete_previous_bot_message(
            chat_id,
            state
        )

        await bot.send_music(
            chat_id=str(chat_id),
            path=path,
            text=state.get(
                "caption",
                DEFAULT_CAPTION
            ),
            file_name=f"{title}.mp3"
        )

        state["step"] = "waiting"

    except Exception as e:

        print(
            "MUSIC ERROR:",
            repr(e)
        )

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "❌ آماده‌سازی یا ارسال آهنگ انجام نشد."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )


# =========================================================
# پاکسازی
# =========================================================

def cleanup_state_files(state):

    for key in (
        "audio_path",
        "cover_path"
    ):

        path = state.get(key)

        if path and os.path.exists(path):

            try:
                os.remove(path)
            except:
                pass

        state[key] = None


# =========================================================
# /start
# =========================================================

@bot.on_message(commands=["start"])
async def start_handler(
    bot,
    message: Message
):

    chat_id = str(
        message.chat_id
    )

    register_user(
        chat_id
    )

    state = get_state(
        chat_id
    )

    cleanup_state_files(
        state
    )

    user_data[chat_id] = new_state()

    state = user_data[chat_id]

    await delete_previous_bot_message(
        chat_id,
        state
    )

    result = await send_text(
        chat_id,
        "سلام 👋\n\n"
        "🔗 لینک مستقیم فایل صوتی را بفرست.\n"
        "یا متن جستجو را وارد کن.\n\n"
        "مثال:\n"
        "https://example.com/song.mp3",
        start_keyboard()
    )

    state["last_bot_message_id"] = (
        get_message_id(result)
    )


# =========================================================
# Callback
# =========================================================

@bot.on_callback()
async def callback_handler(
    bot,
    message: Message
):

    chat_id = str(
        message.chat_id
    )

    register_user(
        chat_id
    )

    state = get_state(
        chat_id
    )

    button_id = ""

    try:
        button_id = (
            message.aux_data.button_id
        )
    except:
        pass

    print(
        "CALLBACK:",
        chat_id,
        button_id
    )

    # -----------------------------------------------------
    # جستجو
    # -----------------------------------------------------

    if button_id == "search":

        state["step"] = "search"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "🔎 متن جستجو را ارسال کن:",
            cancel_keyboard()
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    # -----------------------------------------------------
    # لغو
    # -----------------------------------------------------

    if button_id == "cancel":

        cleanup_state_files(
            state
        )

        state["step"] = "waiting"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "❌ عملیات لغو شد.\n\n"
            "لینک فایل یا متن جستجو را ارسال کن."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    # -----------------------------------------------------
    # قبلی
    # -----------------------------------------------------

    if button_id == "previous":

        index = state.get(
            "current_index",
            0
        )

        if index <= 0:

            await delete_previous_bot_message(
                chat_id,
                state
            )

            result = await send_text(
                chat_id,
                "⚠️ این اولین نتیجه است.",
                result_keyboard()
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

            return

        await show_result(
            chat_id,
            state,
            index - 1
        )

        return

    # -----------------------------------------------------
    # بعدی
    # -----------------------------------------------------

    if button_id == "next":

        results = state.get(
            "previous_results",
            []
        )

        index = state.get(
            "current_index",
            -1
        )

        if index + 1 >= len(results):

            await delete_previous_bot_message(
                chat_id,
                state
            )

            result = await send_text(
                chat_id,
                "⚠️ نتیجه دیگری وجود ندارد.",
                result_keyboard()
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

            return

        await show_result(
            chat_id,
            state,
            index + 1
        )

        return

    # -----------------------------------------------------
    # ادیت
    # -----------------------------------------------------

    if button_id == "edit":

        await start_edit(
            chat_id,
            state
        )

        return

    # -----------------------------------------------------
    # آهنگ
    # -----------------------------------------------------

    if button_id == "music":

        state["step"] = "music_title"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "🎵 نام آهنگ را ارسال کن:",
            cancel_keyboard()
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    # -----------------------------------------------------
    # ویس
    # -----------------------------------------------------

    if button_id == "voice":

        await send_voice_file(
            chat_id,
            state
        )

        return


# =========================================================
# پیام‌های متنی
# =========================================================

@bot.on_message()
async def message_handler(
    bot,
    message: Message
):

    chat_id = str(
        message.chat_id
    )

    register_user(
        chat_id
    )

    text = getattr(
        message,
        "text",
        None
    )

    if not text:
        return

    text = text.strip()

    if not text:
        return

    if text.startswith("/"):
        return

    state = get_state(
        chat_id
    )

    step = state.get(
        "step",
        "waiting"
    )

    # =====================================================
    # کپشن
    # =====================================================

    if step == "caption":

        state["caption"] = text
        state["step"] = "type"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "نوع ارسال را انتخاب کن:",
            type_keyboard()
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    # =====================================================
    # نام آهنگ
    # =====================================================

    if step == "music_title":

        state["title"] = text
        state["step"] = "music_artist"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "👤 نام خواننده را ارسال کن:",
            cancel_keyboard()
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    # =====================================================
    # خواننده
    # =====================================================

    if step == "music_artist":

        state["artist"] = text

        # اگر بخواهی همیشه artist این باشد:
        # @Black_list_remix
        #
        # این خط را فعال کن:
        #
        # state["artist"] = "@Black_list_remix"

        state["step"] = "cover"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "🖼️ لینک مستقیم کاور را ارسال کن.\n\n"
            "یا بنویس:\n"
            "پیشفرض",
            cancel_keyboard()
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        return

    # =====================================================
    # کاور
    # =====================================================

    if step == "cover":

        if text.lower() in (
            "پیشفرض",
            "default"
        ):

            state["cover_url"] = DEFAULT_COVER

        else:

            url = extract_url(
                text
            )

            if not url:

                await delete_previous_bot_message(
                    chat_id,
                    state
                )

                result = await send_text(
                    chat_id,
                    "❌ لینک کاور معتبر نیست.\n"
                    "یک لینک مستقیم تصویر بفرست."
                )

                state["last_bot_message_id"] = (
                    get_message_id(result)
                )

                return

            state["cover_url"] = url

        state["step"] = "preparing"

        await send_music_file(
            chat_id,
            state
        )

        return

    # =====================================================
    # جستجو
    # =====================================================

    if step == "search":

        query = text

        state["query"] = query

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "🔎 در حال جستجو..."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        try:

            results = await search_allowed_source(
                query
            )

            if not results:

                await delete_previous_bot_message(
                    chat_id,
                    state
                )

                result = await send_text(
                    chat_id,
                    "❌ نتیجه‌ای از منبع مجاز پیدا نشد.\n\n"
                    "می‌توانی لینک مستقیم فایل را بفرستی."
                )

                state["last_bot_message_id"] = (
                    get_message_id(result)
                )

                state["step"] = "waiting"

                return

            state["previous_results"] = results
            state["current_index"] = 0
            state["step"] = "result"

            await show_result(
                chat_id,
                state,
                0
            )

        except Exception as e:

            print(
                "SEARCH ERROR:",
                repr(e)
            )

            await delete_previous_bot_message(
                chat_id,
                state
            )

            result = await send_text(
                chat_id,
                "❌ هنگام جستجو خطایی رخ داد."
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

        return

    # =====================================================
    # نتیجه فعلی
    # =====================================================

    if step == "result":

        # اگر کاربر یک لینک جدید فرستاد،
        # نتیجه قبلی حذف و فایل جدید وارد روند ادیت می‌شود.

        url = extract_url(
            text
        )

        if url:

            await delete_previous_bot_message(
                chat_id,
                state
            )

            state["source_url"] = url
            state["step"] = "caption"
            state["title"] = ""
            state["artist"] = ""
            state["cover_url"] = DEFAULT_COVER

            result = await send_text(
                chat_id,
                "📝 کپشن فایل را ارسال کن:",
                cancel_keyboard()
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

        return

    # =====================================================
    # مرحله waiting
    # =====================================================

    if step == "waiting":

        url = extract_url(
            text
        )

        # -----------------------------------------------
        # لینک مستقیم
        # -----------------------------------------------

        if url:

            state["source_url"] = url
            state["step"] = "caption"

            await delete_previous_bot_message(
                chat_id,
                state
            )

            result = await send_text(
                chat_id,
                "📝 کپشن فایل را ارسال کن:",
                cancel_keyboard()
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

            return

        # -----------------------------------------------
        # متن جستجو
        # -----------------------------------------------

        state["query"] = text
        state["step"] = "search"

        await delete_previous_bot_message(
            chat_id,
            state
        )

        result = await send_text(
            chat_id,
            "🔎 در حال جستجوی منبع مجاز..."
        )

        state["last_bot_message_id"] = (
            get_message_id(result)
        )

        try:

            results = await search_allowed_source(
                text
            )

            if not results:

                await delete_previous_bot_message(
                    chat_id,
                    state
                )

                result = await send_text(
                    chat_id,
                    "❌ نتیجه‌ای پیدا نشد.\n\n"
                    "اگر لینک مستقیم فایل را داری، "
                    "همان را ارسال کن."
                )

                state["last_bot_message_id"] = (
                    get_message_id(result)
                )

                state["step"] = "waiting"

                return

            state["previous_results"] = results
            state["current_index"] = 0
            state["step"] = "result"

            await show_result(
                chat_id,
                state,
                0
            )

        except Exception as e:

            print(
                "SEARCH ERROR:",
                repr(e)
            )

            await delete_previous_bot_message(
                chat_id,
                state
            )

            result = await send_text(
                chat_id,
                "❌ جستجو با خطا مواجه شد."
            )

            state["last_bot_message_id"] = (
                get_message_id(result)
            )

        return


# =========================================================
# اجرای ربات
# =========================================================

print("====================================")
print("Rubika Music Bot")
print("Rubka 8.1.10")
print("Bot is starting...")
print("====================================")

bot.run()
