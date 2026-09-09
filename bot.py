import os
import json
import asyncio
import aiohttp

from rubka import Robot, Message
from rubka.button import InlineBuilder


# =========================================================
# تنظیمات
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"

bot = Robot(
    token=TOKEN,
    parse_mode="HTML"
)

USERS_FILE = "users.json"


# =========================================================
# مدیریت کاربران
# =========================================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                users,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        print("❌ خطا در ذخیره کاربران:", e)


def add_user(chat_id):
    users = load_users()

    chat_id = str(chat_id)

    if chat_id not in users:
        users.append(chat_id)
        save_users(users)
        print("👤 کاربر جدید:", chat_id)


# =========================================================
# وضعیت کاربران
# =========================================================

states = {}


def get_state(chat_id):
    return states.get(str(chat_id))


def set_state(chat_id, state):
    states[str(chat_id)] = state


def clear_state(chat_id):
    states.pop(str(chat_id), None)


# =========================================================
# کیبورد اصلی
# =========================================================

def main_keyboard():
    return {
        "rows": [
            {
                "buttons": [
                    {
                        "id": "send_banner",
                        "type": "Simple",
                        "button_text": "🖼 ارسال بنر"
                    },
                    {
                        "id": "send_music",
                        "type": "Simple",
                        "button_text": "🎵 ارسال آهنگ"
                    }
                ]
            }
        ]
    }


# =========================================================
# ساخت دکمه شیشه‌ای
# =========================================================

def make_glass_button(title, url):
    """
    دکمه شیشه‌ای Link
    """

    if not title or title == "بعدی":
        return None

    if not url or url == "بعدی":
        return None

    return {
        "rows": [
            {
                "buttons": [
                    {
                        "id": "glass_button",
                        "type": "Link",
                        "button_text": title,
                        "button_link": {
                            "type": "url",
                            "link_url": url
                        }
                    }
                ]
            }
        ]
    }


# =========================================================
# دانلود فایل
# =========================================================

async def download_file(url, filename):
    try:

        print("⬇️ دانلود:")
        print(url)

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as response:

                if response.status != 200:
                    print("❌ HTTP:", response.status)
                    return None

                data = await response.read()

                with open(filename, "wb") as f:
                    f.write(data)

        print("✅ دانلود شد:", filename)

        return filename

    except Exception as e:

        print("❌ خطا در دانلود:", e)

        return None


# =========================================================
# ارسال به همه کاربران
# =========================================================

async def broadcast_message(send_function):

    users = load_users()

    print("📢 تعداد کاربران:", len(users))

    success = 0
    failed = 0

    for chat_id in users:

        try:

            await send_function(chat_id)

            success += 1

            await asyncio.sleep(0.15)

        except Exception as e:

            failed += 1

            print(
                "❌ ارسال نشد:",
                chat_id,
                repr(e)
            )

    print("📢 ارسال تمام شد")
    print("✅ موفق:", success)
    print("❌ ناموفق:", failed)

    return success, failed


# =========================================================
# /start
# =========================================================

@bot.on_message(commands=["start"])
async def start(bot: Robot, message: Message):

    chat_id = message.chat_id

    add_user(chat_id)

    clear_state(chat_id)

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🤖 <b>پنل ارسال محتوا</b>\n\n"
            "از منوی زیر یکی از گزینه‌ها را انتخاب کن:"
        ),
        reply_markup=main_keyboard()
    )


# =========================================================
# انتخاب ارسال بنر
# =========================================================

@bot.on_message()
async def message_handler(bot: Robot, message: Message):

    chat_id = str(message.chat_id)

    add_user(chat_id)

    text = getattr(message, "text", None)

    if not text:
        return

    text = text.strip()

    # ---------------------------------------------
    # شروع بنر
    # ---------------------------------------------

    if text == "🖼 ارسال بنر":

        set_state(chat_id, {
            "type": "banner",
            "step": "image"
        })

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🖼 <b>مرحله ۱ از ۴</b>\n\n"
                "لینک مستقیم تصویر را ارسال کن.\n\n"
                "برای رد کردن این مرحله بنویس:\n"
                "<code>بعدی</code>"
            )
        )

        return

    # ---------------------------------------------
    # شروع آهنگ
    # ---------------------------------------------

    if text == "🎵 ارسال آهنگ":

        set_state(chat_id, {
            "type": "music",
            "step": "download_url"
        })

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🎵 <b>مرحله ۱</b>\n\n"
                "لینک مستقیم دانلود آهنگ یا فایل را بفرست.\n\n"
                "اگر فایل دانلودی نداری بنویس:\n"
                "<code>بعدی</code>"
            )
        )

        return

    # =====================================================
    # بررسی وضعیت
    # =====================================================

    state = get_state(chat_id)

    if not state:
        return

    # =====================================================
    # بنر
    # =====================================================

    if state["type"] == "banner":

        step = state["step"]

        # ---------------------------------------------
        # تصویر
        # ---------------------------------------------

        if step == "image":

            state["image_url"] = None if text == "بعدی" else text

            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "📝 <b>مرحله ۲ از ۴</b>\n\n"
                    "کپشن بنر را ارسال کن.\n\n"
                    "یا بنویس <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # کپشن
        # ---------------------------------------------

        if step == "caption":

            state["caption"] = "" if text == "بعدی" else text

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔘 <b>مرحله ۳ از ۴</b>\n\n"
                    "متن دکمه شیشه‌ای را ارسال کن.\n\n"
                    "مثلاً:\n"
                    "<code>🌐 ورود به سایت</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # متن دکمه
        # ---------------------------------------------

        if step == "button_text":

            state["button_text"] = (
                None if text == "بعدی"
                else text
            )

            state["step"] = "button_url"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔗 <b>مرحله ۴ از ۴</b>\n\n"
                    "لینک دکمه را ارسال کن.\n\n"
                    "مثلاً:\n"
                    "<code>https://example.com</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # لینک دکمه
        # ---------------------------------------------

        if step == "button_url":

            state["button_url"] = (
                None if text == "بعدی"
                else text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳ در حال آماده‌سازی بنر..."
            )

            image_url = state.get("image_url")
            caption = state.get("caption", "")
            button_text = state.get("button_text")
            button_url = state.get("button_url")

            inline_keypad = make_glass_button(
                button_text,
                button_url
            )

            async def send_banner(user_id):

                if image_url:

                    # تلاش برای ارسال URL تصویر
                    await bot.send_image(
                        chat_id=user_id,
                        image=image_url,
                        text=caption if caption else None,
                        inline_keypad=inline_keypad
                    )

                else:

                    await bot.send_message(
                        chat_id=user_id,
                        text=caption or "🖼 بنر",
                        inline_keypad=inline_keypad
                    )

            try:

                success, failed = await broadcast_message(
                    send_banner
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ <b>ارسال بنر انجام شد.</b>\n\n"
                        f"👥 موفق: {success}\n"
                        f"❌ ناموفق: {failed}"
                    ),
                    reply_markup=main_keyboard()
                )

            except Exception as e:

                print("❌ BANNER ERROR:", repr(e))

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ خطا هنگام ارسال بنر:\n\n"
                        f"<code>{e}</code>"
                    ),
                    reply_markup=main_keyboard()
                )

            clear_state(chat_id)

            return

    # =====================================================
    # آهنگ
    # =====================================================

    if state["type"] == "music":

        step = state["step"]

        # ---------------------------------------------
        # URL دانلود
        # ---------------------------------------------

        if step == "download_url":

            state["download_url"] = (
                None if text == "بعدی"
                else text
            )

            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "📝 <b>مرحله ۲</b>\n\n"
                    "کپشن آهنگ را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # کپشن
        # ---------------------------------------------

        if step == "caption":

            state["caption"] = (
                "" if text == "بعدی"
                else text
            )

            state["step"] = "media_type"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎧 <b>مرحله ۳</b>\n\n"
                    "نوع محتوا را مشخص کن:\n\n"
                    "🎵 آهنگ\n"
                    "🎙 ویس"
                )
            )

            return

        # ---------------------------------------------
        # نوع
        # ---------------------------------------------

        if step == "media_type":

            if text not in ["🎵 آهنگ", "🎙 ویس"]:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ فقط یکی از این دو گزینه را بفرست:\n\n"
                        "🎵 آهنگ\n"
                        "🎙 ویس"
                    )
                )

                return

            state["media_type"] = text

            state["step"] = "song_name"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎵 <b>مرحله ۴</b>\n\n"
                    "نام آهنگ را ارسال کن.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # نام آهنگ
        # ---------------------------------------------

        if step == "song_name":

            state["song_name"] = (
                "" if text == "بعدی"
                else text
            )

            state["step"] = "singer"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎤 <b>مرحله ۵</b>\n\n"
                    "نام خواننده را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # خواننده
        # ---------------------------------------------

        if step == "singer":

            state["singer"] = (
                "" if text == "بعدی"
                else text
            )

            state["step"] = "cover"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🖼 <b>مرحله ۶</b>\n\n"
                    "لینک کاور آهنگ را بفرست.\n\n"
                    "اگر کاور نداری <code>بعدی</code> بنویس."
                )
            )

            return

        # ---------------------------------------------
        # کاور
        # ---------------------------------------------

        if step == "cover":

            state["cover"] = (
                None if text == "بعدی"
                else text
            )

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔘 <b>مرحله ۷</b>\n\n"
                    "متن دکمه شیشه‌ای را بفرست.\n\n"
                    "مثلاً:\n"
                    "<code>🌐 سایت ما</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # متن دکمه
        # ---------------------------------------------

        if step == "button_text":

            state["button_text"] = (
                None if text == "بعدی"
                else text
            )

            state["step"] = "button_url"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔗 <b>مرحله ۸</b>\n\n"
                    "لینک دکمه را ارسال کن.\n\n"
                    "مثلاً:\n"
                    "<code>https://example.com</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return

        # ---------------------------------------------
        # URL دکمه
        # ---------------------------------------------

        if step == "button_url":

            state["button_url"] = (
                None if text == "بعدی"
                else text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳ در حال آماده‌سازی ارسال..."
            )

            download_url = state.get("download_url")
            caption = state.get("caption", "")
            media_type = state.get("media_type")
            song_name = state.get("song_name", "")
            singer = state.get("singer", "")
            cover = state.get("cover")
            button_text = state.get("button_text")
            button_url = state.get("button_url")

            inline_keypad = make_glass_button(
                button_text,
                button_url
            )

            # -----------------------------------------
            # ساخت کپشن نهایی
            # -----------------------------------------

            final_caption = caption

            if song_name:
                final_caption += (
                    f"\n\n🎵 <b>آهنگ:</b> {song_name}"
                )

            if singer:
                final_caption += (
                    f"\n🎤 <b>خواننده:</b> {singer}"
                )

            # -----------------------------------------
            # اگر URL وجود دارد دانلود کن
            # -----------------------------------------

            local_file = None

            if download_url:

                extension = ".mp3"

                if media_type == "🎙 ویس":
                    extension = ".ogg"

                local_file = (
                    f"broadcast_{chat_id}"
                    f"{extension}"
                )

                local_file = await download_file(
                    download_url,
                    local_file
                )

            # -----------------------------------------
            # تابع ارسال
            # -----------------------------------------

            async def send_music(user_id):

                # -------------------------------------
                # آهنگ
                # -------------------------------------

                if media_type == "🎵 آهنگ":

                    if local_file and os.path.exists(local_file):

                        await bot.send_music(
                            chat_id=user_id,
                            music=local_file,
                            text=final_caption,
                            inline_keypad=inline_keypad
                        )

                    elif download_url:

                        await bot.send_message(
                            chat_id=user_id,
                            text=(
                                f"🎵 {final_caption}\n\n"
                                f"🔗 {download_url}"
                            ),
                            inline_keypad=inline_keypad
                        )

                    else:

                        await bot.send_message(
                            chat_id=user_id,
                            text=final_caption or "🎵 آهنگ",
                            inline_keypad=inline_keypad
                        )

                # -------------------------------------
                # ویس
                # -------------------------------------

                else:

                    if local_file and os.path.exists(local_file):

                        await bot.send_voice(
                            chat_id=user_id,
                            voice=local_file,
                            text=final_caption,
                            inline_keypad=inline_keypad
                        )

                    elif download_url:

                        await bot.send_message(
                            chat_id=user_id,
                            text=(
                                f"🎙 {final_caption}\n\n"
                                f"🔗 {download_url}"
                            ),
                            inline_keypad=inline_keypad
                        )

                    else:

                        await bot.send_message(
                            chat_id=user_id,
                            text=final_caption or "🎙 ویس",
                            inline_keypad=inline_keypad
                        )

            # -----------------------------------------
            # ارسال
            # -----------------------------------------

            try:

                success, failed = await broadcast_message(
                    send_music
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ <b>ارسال آهنگ انجام شد.</b>\n\n"
                        f"👥 موفق: {success}\n"
                        f"❌ ناموفق: {failed}"
                    ),
                    reply_markup=main_keyboard()
                )

            except Exception as e:

                print("❌ MUSIC ERROR:")
                print(repr(e))

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ خطا هنگام ارسال آهنگ:\n\n"
                        f"<code>{e}</code>"
                    ),
                    reply_markup=main_keyboard()
                )

            # -----------------------------------------
            # حذف فایل موقت
            # -----------------------------------------

            try:

                if local_file and os.path.exists(local_file):
                    os.remove(local_file)

            except Exception:
                pass

            clear_state(chat_id)

            return


# =========================================================
# اجرای ربات
# =========================================================

print("=" * 60)
print("🤖 RUBIKA MUSIC + BANNER BOT")
print("=" * 60)
print("📦 Rubka 8.1.10")
print("🐍 Python")
print("📱 Pydroid 3")
print("=" * 60)
print("🚀 Bot is running...")
print("=" * 60)

bot.run()
