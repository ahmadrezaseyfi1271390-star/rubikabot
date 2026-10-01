import os
import datetime
import subprocess
import requests
import tempfile
from rubka import Robot
from rubka.context import Message
from rubka.keypad import InlineBuilder
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TPE1, TIT2, ID3NoHeaderError

# ========== تنظیمات ==========
BOT_TOKEN = "CFDFIH0FZUNOCNJHQVSUBRNZUBZJYFLXIOXEUSPJLEXBZBJQOPBZKSGWEXQTISIH"
TARGET_CHANNEL_ID = "c0BOd3T06238bac25a0a403752367011"
NEW_ARTIST = "@Black_list_remix"
NEW_COVER_URL = "https://cdn.imgurl.ir/uploads/s93695_ab8b9c87-0990-4beb-bfaa-cd1bf842caf7.png"
CHANNEL_USERNAME = "@Black_list_remix"
OWNER_USERNAME = "@reza_127_s"
# ==========================

bot = Robot(BOT_TOKEN)
TEMP_DIR = tempfile.mkdtemp(prefix="rubika_audio_")
WELCOME_PHOTO_PATH = os.path.join(TEMP_DIR, "welcome_cover.png")
COVER_CACHE = None

SUPPORTED_AUDIO_EXTENSIONS = (
    '.mp3', '.aac', '.wma', '.flac', '.ac3', '.ogg', '.m4a',
    '.wav', '.opus', '.aiff', '.alac', '.ape', '.amr'
)


def ensure_welcome_photo():
    if os.path.exists(WELCOME_PHOTO_PATH):
        return WELCOME_PHOTO_PATH
    try:
        resp = requests.get(NEW_COVER_URL, timeout=30)
        resp.raise_for_status()
        with open(WELCOME_PHOTO_PATH, "wb") as f:
            f.write(resp.content)
        print("✅ عکس خوش‌آمدگویی دانلود شد")
        return WELCOME_PHOTO_PATH
    except Exception as e:
        print(f"❌ خطا در دانلود عکس: {e}")
        return None


def get_cover_bytes():
    global COVER_CACHE
    if COVER_CACHE is not None:
        return COVER_CACHE
    try:
        resp = requests.get(NEW_COVER_URL, timeout=30)
        resp.raise_for_status()
        COVER_CACHE = resp.content
        print("✅ عکس کاور دانلود شد")
        return COVER_CACHE
    except Exception as e:
        print(f"❌ خطا در دانلود کاور: {e}")
        return None


def is_audio_file(message: Message) -> bool:
    if not message.file:
        return False
    file_type = getattr(message.file, "type", "")
    if file_type not in ("Music", "Voice", "Audio"):
        return False
    name = getattr(message.file, "name", "").lower()
    mime = getattr(message.file, "mime", "").lower()
    if name.endswith(SUPPORTED_AUDIO_EXTENSIONS):
        return True
    if "audio" in mime or "music" in mime:
        return True
    return False


def convert_to_mp3(input_path: str) -> str:
    output_path = os.path.splitext(input_path)[0] + "_converted.mp3"
    try:
        import imageio_ffmpeg
        ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_cmd = "ffmpeg"
    try:
        subprocess.run([
            ffmpeg_cmd, "-i", input_path,
            "-acodec", "libmp3lame", "-ab", "128k",
            "-vn", "-y", "-loglevel", "error",
            output_path
        ], check=True, capture_output=True, timeout=120)
        if os.path.exists(output_path):
            print("✅ تبدیل به MP3 موفق")
            return output_path
        return None
    except Exception as e:
        print(f"❌ خطا در تبدیل: {e}")
        return None


def change_metadata(file_path: str) -> bool:
    try:
        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()
        if audio.tags is None:
            audio.add_tags()
        audio.tags.add(TPE1(encoding=3, text=NEW_ARTIST))
        title_tag = audio.tags.get("TIT2")
        if title_tag and "@" in str(title_tag):
            audio.tags.add(TIT2(encoding=3, text=NEW_ARTIST))
        cover_data = get_cover_bytes()
        if cover_data:
            audio.tags.delall("APIC")
            audio.tags.add(APIC(
                encoding=3, mime="image/png",
                type=3, desc="Cover", data=cover_data
            ))
        audio.save(v2_version=3)
        return True
    except Exception as e:
        print(f"خطا در متادیتا: {e}")
        return False


# ========== هندلر /start ==========
@bot.on_message(commands=["start"])
async def start_handler(bot: Robot, message: Message):
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y/%m/%d")

    welcome_text = (
        "سلام و درود👋\n"
        "برای ارسال آهنگ شما به کانال باید  فایل آهنگ رو فقط به صورت mp3 ارسال کنید."
    )

    builder = InlineBuilder()
    inline_keypad = builder.row(
        builder.button_simple("time_btn", f"🕐 {time_str}")
    ).row(
        builder.button_simple("date_btn", f"📅 {date_str}")
    ).row(
        builder.button_link("channel_btn", f"📢 {CHANNEL_USERNAME}", "https://rubika.ir/Black_list_remix")
    ).row(
        builder.button_simple("contact_owner_btn", "📞 ارتباط با مالک")
    ).build()

    try:
        if os.path.exists(WELCOME_PHOTO_PATH):
            await bot.send_image(
                chat_id=message.chat_id,
                path=WELCOME_PHOTO_PATH,
                text=welcome_text,
                inline_keypad=inline_keypad
            )
        else:
            await bot.send_message(
                chat_id=message.chat_id,
                text=welcome_text,
                inline_keypad=inline_keypad
            )
    except Exception as e:
        print(f"خطا در پیام خوش‌آمد: {e}")


# ========== هندلر کلیک روی دکمه ارتباط با مالک ==========
@bot.on_message(filters=lambda m: getattr(m, "aux_data", None) and getattr(m.aux_data, "button_id", "") == "contact_owner_btn")
async def contact_owner_handler(bot: Robot, message: Message):
    owner_text = (
        "سلام دوست من.\n"
        "برای دریافت اطلاعات بیشتر همینطور همکاری و تبلیغات میتونی به مالک پیام بدی.\n"
        "توجه داشته باش که تبلیغات هم در ربات و هم در کانال گذاشته میشود.\n"
        f"{OWNER_USERNAME}"
    )
    try:
        await bot.send_message(
            chat_id=message.chat_id,
            text=owner_text
        )
    except Exception as e:
        print(f"خطا در ارسال پیام مالک: {e}")


# ========== هندلر اصلی: همه پیام‌ها ==========
@bot.on_message()
async def handle_all_messages(bot: Robot, message: Message):
    print(f"🔍 پیام دریافت شد | chat_id={message.chat_id}")

    if is_audio_file(message):
        await handle_audio(bot, message)
    elif message.file:
        try:
            await message.reply(
                "دوست گرامی.\n"
                "این ربات فقط برای ارسال موزیک و آهنگ میباشد لطفا فایل های mp3 ، ogg ،... بفرستید."
            )
        except Exception as e:
            print(f"خطا در ارسال راهنما: {e}")


async def handle_audio(bot: Robot, message: Message):
    file_data = message.file
    file_name = getattr(file_data, "name", f"audio_{message.message_id}")
    local_path = os.path.join(TEMP_DIR, file_name)

    status_msg = await message.reply("⬇️ در حال دانلود فایل...")

    try:
        print(f"در حال دانلود: {file_name}")
        file_id = getattr(file_data, "id", None)
        bot.download_file(file_id, save_as=local_path)

        ext = os.path.splitext(file_name)[1].lower()
        mp3_path = local_path

        if ext != '.mp3':
            await bot.edit_message_text(
                chat_id=message.chat_id,
                msg_id=status_msg.message_id,
                text="⚙️ در حال تبدیل فرمت به MP3..."
            )
            converted = convert_to_mp3(local_path)
            if converted:
                mp3_path = converted
                if os.path.exists(local_path):
                    os.remove(local_path)
            else:
                await bot.edit_message_text(
                    chat_id=message.chat_id,
                    msg_id=status_msg.message_id,
                    text="❌ خطا در تبدیل فرمت. لطفاً فایل MP3 بفرستید."
                )
                if os.path.exists(local_path):
                    os.remove(local_path)
                return

        await bot.edit_message_text(
            chat_id=message.chat_id,
            msg_id=status_msg.message_id,
            text="⚙️ در حال پردازش و تغییر متادیتا..."
        )
        change_metadata(mp3_path)

        print("در حال ارسال به کانال...")
        await bot.send_music(
            chat_id=TARGET_CHANNEL_ID,
            path=mp3_path,
            performer=NEW_ARTIST
        )

        await bot.edit_message_text(
            chat_id=message.chat_id,
            msg_id=status_msg.message_id,
            text="✅ آهنگ با موفقیت به کانال ارسال شد."
        )

        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        if os.path.exists(local_path):
            os.remove(local_path)

    except Exception as e:
        print(f"خطای پردازش: {e}")
        try:
            await bot.edit_message_text(
                chat_id=message.chat_id,
                msg_id=status_msg.message_id,
                text=f"❌ خطا در پردازش فایل: {e}"
            )
        except Exception:
            pass
        if os.path.exists(local_path):
            os.remove(local_path)


# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات در حال اجراست...")
    ensure_welcome_photo()
    get_cover_bytes()
    bot.run()
