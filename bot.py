import os
import json
import asyncio

from rubka import Robot, Message
from rubka.keypad import ChatKeypadBuilder
from rubka.button import InlineBuilder


# =========================================================
# TOKEN
# =========================================================

TOKEN = "CEAAAB0RWZIWOUPRPFBKFTVBCQDUFDUDWVFDDITXAVUWMJKFVLJITFGUBBVEPCHH"


# =========================================================
# BOT
# =========================================================

bot = Robot(
    token=TOKEN,
    parse_mode="HTML"
)


# =========================================================
# FILES
# =========================================================

USERS_FILE = "users.json"


# =========================================================
# USER DATABASE
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

        print("❌ خطا در خواندن users.json:", e)

    return []


def save_users(users):

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

        print("❌ خطا در ذخیره کاربران:", e)


def add_user(chat_id):

    chat_id = str(chat_id)

    users = load_users()

    if chat_id not in users:

        users.append(chat_id)

        save_users(users)

        print("👤 کاربر جدید:", chat_id)


# =========================================================
# USER STATES
# =========================================================

states = {}


def set_state(chat_id, data):

    states[str(chat_id)] = data


def get_state(chat_id):

    return states.get(str(chat_id))


def clear_state(chat_id):

    states.pop(str(chat_id), None)


# =========================================================
# MAIN CHAT KEYBOARD
# =========================================================

def main_keyboard():

    builder = ChatKeypadBuilder()

    keypad = (
        builder
        .row(
            builder.button(
                id="make_banner",
                text="🖼 ساخت بنر"
            ),
            builder.button(
                id="edit_music",
                text="🎵 ادیت آهنگ"
            )
        )
        .build()
    )

    return keypad


# =========================================================
# GLASS BUTTON
# =========================================================

def make_glass_button(button_text, button_url):

    if not button_text:
        return None

    if not button_url:
        return None

    try:

        builder = InlineBuilder()

        keypad = (
            builder
            .row(
                builder.button_link(
                    id="glass_button",
                    title=button_text,
                    url=button_url
                )
            )
            .build()
        )

        return keypad

    except Exception as e:

        print("❌ خطا در ساخت دکمه شیشه‌ای:", e)

        return None


# =========================================================
# SEND TO ALL USERS
# =========================================================

async def broadcast(send_function):

    users = load_users()

    print()
    print("=" * 50)
    print("📢 BROADCAST")
    print("👥 USERS:", len(users))
    print("=" * 50)

    success = 0
    failed = 0

    for chat_id in users:

        try:

            await send_function(chat_id)

            success += 1

            print(
                f"✅ {chat_id}"
            )

        except Exception as e:

            failed += 1

            print(
                f"❌ {chat_id} -> {repr(e)}"
            )

        await asyncio.sleep(0.2)

    print("=" * 50)
    print(
        f"📊 SUCCESS: {success} | FAILED: {failed}"
    )
    print("=" * 50)

    return success, failed


# =========================================================
# START
# =========================================================

@bot.on_message(commands=["start"])
async def start(bot: Robot, message: Message):

    chat_id = str(message.chat_id)

    add_user(chat_id)

    clear_state(chat_id)

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🤖 <b>پنل مدیریت</b>\n\n"
            "یکی از گزینه‌های زیر را انتخاب کن:"
        ),
        chat_keypad=main_keyboard(),
        chat_keypad_type="New"
    )


# =========================================================
# MAIN MESSAGE HANDLER
# =========================================================

@bot.on_message()
async def handler(bot: Robot, message: Message):

    chat_id = str(message.chat_id)

    add_user(chat_id)

    text = getattr(message, "text", None)

    if not text:
        return

    text = text.strip()

    # =====================================================
    # ساخت بنر
    # =====================================================

    if text == "🖼 ساخت بنر":

        set_state(
            chat_id,
            {
                "type": "banner",
                "step": "image"
            }
        )

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🖼 <b>ساخت بنر</b>\n\n"
                "مرحله ۱ از ۴\n\n"
                "لینک مستقیم تصویر را بفرست.\n\n"
                "برای رد کردن:\n"
                "<code>بعدی</code>"
            )
        )

        return


    # =====================================================
    # ادیت آهنگ
    # =====================================================

    if text == "🎵 ادیت آهنگ":

        set_state(
            chat_id,
            {
                "type": "music",
                "step": "url"
            }
        )

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🎵 <b>ادیت آهنگ</b>\n\n"
                "مرحله ۱ از ۸\n\n"
                "لینک مستقیم فایل آهنگ را بفرست.\n\n"
                "برای رد کردن:\n"
                "<code>بعدی</code>"
            )
        )

        return


    # =====================================================
    # GET STATE
    # =====================================================

    state = get_state(chat_id)

    if not state:
        return


    # =====================================================
    # BANNER
    # =====================================================

    if state["type"] == "banner":

        step = state["step"]


        # -------------------------------------------------
        # IMAGE
        # -------------------------------------------------

        if step == "image":

            if text == "بعدی":
                state["image"] = None
            else:
                state["image"] = text

            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "📝 <b>مرحله ۲ از ۴</b>\n\n"
                    "کپشن بنر را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # CAPTION
        # -------------------------------------------------

        if step == "caption":

            state["caption"] = (
                ""
                if text == "بعدی"
                else text
            )

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔘 <b>مرحله ۳ از ۴</b>\n\n"
                    "متن دکمه شیشه‌ای را بفرست.\n\n"
                    "مثلاً:\n"
                    "<code>🌐 ورود به سایت</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # BUTTON TEXT
        # -------------------------------------------------

        if step == "button_text":

            state["button_text"] = (
                None
                if text == "بعدی"
                else text
            )

            state["step"] = "button_url"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔗 <b>مرحله ۴ از ۴</b>\n\n"
                    "لینک دکمه را بفرست.\n\n"
                    "مثلاً:\n"
                    "<code>https://example.com</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # BUTTON URL + SEND
        # -------------------------------------------------

        if step == "button_url":

            state["button_url"] = (
                None
                if text == "بعدی"
                else text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳ بنر آماده شد. در حال ارسال برای همه کاربران..."
            )

            image = state.get("image")
            caption = state.get("caption", "")
            button_text = state.get("button_text")
            button_url = state.get("button_url")

            inline_keypad = make_glass_button(
                button_text,
                button_url
            )


            async def send_banner(user_id):

                # اگر تصویر داریم
                if image:

                    await bot.send_image(
                        chat_id=user_id,
                        path=image,
                        text=caption,
                        inline_keypad=inline_keypad
                    )

                # اگر تصویر رد شده
                else:

                    await bot.send_message(
                        chat_id=user_id,
                        text=caption or "🖼 بنر",
                        inline_keypad=inline_keypad
                    )


            try:

                success, failed = await broadcast(
                    send_banner
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ <b>بنر برای همه ارسال شد.</b>\n\n"
                        f"👥 ارسال موفق: {success}\n"
                        f"❌ ناموفق: {failed}"
                    ),
                    chat_keypad=main_keyboard(),
                    chat_keypad_type="New"
                )

            except Exception as e:

                print("❌ BANNER ERROR:", repr(e))

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ خطا در ارسال بنر:\n\n"
                        f"<code>{e}</code>"
                    ),
                    chat_keypad=main_keyboard(),
                    chat_keypad_type="New"
                )

            clear_state(chat_id)

            return


    # =====================================================
    # MUSIC
    # =====================================================

    if state["type"] == "music":

        step = state["step"]


        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        if step == "url":

            state["url"] = (
                None
                if text == "بعدی"
                else text
            )

            state["step"] = "caption"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "📝 <b>مرحله ۲ از ۸</b>\n\n"
                    "کپشن آهنگ را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # CAPTION
        # -------------------------------------------------

        if step == "caption":

            state["caption"] = (
                ""
                if text == "بعدی"
                else text
            )

            state["step"] = "type"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎧 <b>مرحله ۳ از ۸</b>\n\n"
                    "نوع محتوا را بفرست:\n\n"
                    "🎵 آهنگ\n"
                    "🎙 ویس"
                )
            )

            return


        # -------------------------------------------------
        # TYPE
        # -------------------------------------------------

        if step == "type":

            if text not in [
                "🎵 آهنگ",
                "🎙 ویس"
            ]:

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ گزینه نامعتبر.\n\n"
                        "فقط بنویس:\n"
                        "🎵 آهنگ\n"
                        "یا\n"
                        "🎙 ویس"
                    )
                )

                return

            state["media_type"] = text

            state["step"] = "song_name"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎼 <b>مرحله ۴ از ۸</b>\n\n"
                    "نام آهنگ را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # SONG NAME
        # -------------------------------------------------

        if step == "song_name":

            state["song_name"] = (
                ""
                if text == "بعدی"
                else text
            )

            state["step"] = "singer"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🎤 <b>مرحله ۵ از ۸</b>\n\n"
                    "نام خواننده را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # SINGER
        # -------------------------------------------------

        if step == "singer":

            state["singer"] = (
                ""
                if text == "بعدی"
                else text
            )

            state["step"] = "cover"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🖼 <b>مرحله ۶ از ۸</b>\n\n"
                    "لینک کاور را بفرست.\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # COVER
        # -------------------------------------------------

        if step == "cover":

            state["cover"] = (
                None
                if text == "بعدی"
                else text
            )

            state["step"] = "button_text"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔘 <b>مرحله ۷ از ۸</b>\n\n"
                    "متن دکمه شیشه‌ای را بفرست.\n\n"
                    "مثلاً:\n"
                    "<code>🌐 سایت</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # BUTTON TEXT
        # -------------------------------------------------

        if step == "button_text":

            state["button_text"] = (
                None
                if text == "بعدی"
                else text
            )

            state["step"] = "button_url"

            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔗 <b>مرحله ۸ از ۸</b>\n\n"
                    "لینک دکمه را بفرست.\n\n"
                    "مثلاً:\n"
                    "<code>https://example.com</code>\n\n"
                    "یا <code>بعدی</code>."
                )
            )

            return


        # -------------------------------------------------
        # FINAL MUSIC
        # -------------------------------------------------

        if step == "button_url":

            state["button_url"] = (
                None
                if text == "بعدی"
                else text
            )

            await bot.send_message(
                chat_id=chat_id,
                text="⏳ اطلاعات آهنگ دریافت شد. در حال ارسال برای همه کاربران..."
            )

            music_url = state.get("url")
            caption = state.get("caption", "")
            media_type = state.get("media_type")
            song_name = state.get("song_name", "")
            singer = state.get("singer", "")
            cover = state.get("cover")
            button_text = state.get("button_text")
            button_url = state.get("button_url")


            # -------------------------------------------------
            # FINAL CAPTION
            # -------------------------------------------------

            final_caption = caption

            if song_name:

                final_caption += (
                    "\n\n🎵 <b>آهنگ:</b> "
                    + song_name
                )

            if singer:

                final_caption += (
                    "\n🎤 <b>خواننده:</b> "
                    + singer
                )


            # -------------------------------------------------
            # GLASS BUTTON
            # -------------------------------------------------

            inline_keypad = make_glass_button(
                button_text,
                button_url
            )


            # -------------------------------------------------
            # SEND MUSIC
            # -------------------------------------------------

            async def send_music(user_id):

                # اگر URL داریم، از خود URL استفاده می‌کنیم
                if music_url:

                    if media_type == "🎵 آهنگ":

                        await bot.send_music(
                            chat_id=user_id,
                            path=music_url,
                            text=final_caption,
                            inline_keypad=inline_keypad
                        )

                    else:

                        await bot.send_voice(
                            chat_id=user_id,
                            path=music_url,
                            text=final_caption,
                            inline_keypad=inline_keypad
                        )

                else:

                    await bot.send_message(
                        chat_id=user_id,
                        text=final_caption or "🎵 آهنگ",
                        inline_keypad=inline_keypad
                    )


            try:

                success, failed = await broadcast(
                    send_music
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "✅ <b>آهنگ برای همه ارسال شد.</b>\n\n"
                        f"👥 ارسال موفق: {success}\n"
                        f"❌ ناموفق: {failed}"
                    ),
                    chat_keypad=main_keyboard(),
                    chat_keypad_type="New"
                )

            except Exception as e:

                print("❌ MUSIC ERROR:")
                print(repr(e))

                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ خطا در ارسال آهنگ:\n\n"
                        f"<code>{e}</code>"
                    ),
                    chat_keypad=main_keyboard(),
                    chat_keypad_type="New"
                )

            clear_state(chat_id)

            return


# =========================================================
# RUN
# =========================================================

print("=" * 60)
print("🤖 RUBIKA MUSIC + BANNER BOT")
print("=" * 60)
print("📦 Rubka")
print("🚀 Bot is running...")
print("=" * 60)

bot.run()
