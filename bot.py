import os
import subprocess
import requests
import tempfile
from rubka import Robot, Message

# ========== تنظیمات ==========
BOT_TOKEN = "CEFCFD0ECUJKKLJTVKOPNCVNBUKJBVQZVJIJUQCSYCOPCUQYHFDIEHORVRRRAXCU"
TARGET_CHANNEL_ID = "c0DI7gA0218940ebab512954822551df"
OWNER_CHAT_ID = "b0FXnfh0BEu804900ee2661517d3ae60"
OWNER_ID = "u0FXnfh0fece55a99ad52d509fb50335"

API_BASE = f"https://botapi.rubika.ir/v3/{BOT_TOKEN}"

TEMP_DIR = tempfile.mkdtemp(prefix="rubika_voice_")
BANNED_USERS = set()

SUPPORTED_AUDIO_EXTENSIONS = (
    '.mp3', '.m4a', '.wav', '.aac', '.flac', '.wma', '.ogg',
    '.opus', '.amr', '.ac3', '.aiff', '.alac', '.ape'
)

bot = Robot(token=BOT_TOKEN)


# ========== دریافت لینک دانلود مستقیم ==========
def get_download_url(file_id):
    try:
        resp = requests.post(
            f"{API_BASE}/getFile",
            json={"file_id": file_id},
            timeout=30
        )
        data = resp.json()
        if data.get("status") == "OK":
            d = data.get("data", {})
            return d.get("download_url") or d.get("file_url") or d.get("url")
    except Exception as e:
        print(f"❌ خطا در get_download_url: {e}")
    return None


def get_file_attr(file_obj, name, default=None):
    return getattr(file_obj, name, default)


def is_audio_file(message: Message):
    if not hasattr(message, 'file') or not message.file:
        return False
    file_obj = message.file
    name = (get_file_attr(file_obj, 'file_name', default='') or '').lower()
    return any(name.endswith(ext) for ext in SUPPORTED_AUDIO_EXTENSIONS)


def is_private_chat(message: Message):
    raw = getattr(message, "raw_data", None) or {}
    return raw.get("sender_type", "") == "User"


# ========== تبدیل به ویس (OGG/Opus) ==========
def convert_to_voice(input_path):
    output_path = os.path.splitext(input_path)[0] + "_voice.ogg"

    if not os.path.exists(input_path):
        print(f"❌ فایل ورودی وجود ندارد: {input_path}")
        return None

    print(f"📁 فایل ورودی: {input_path} | حجم: {os.path.getsize(input_path)} بایت")

    try:
        result = subprocess.run([
            "ffmpeg", "-i", input_path,
            "-ac", "1",
            "-map", "0:a",
            "-codec:a", "libopus",
            "-b:a", "48k",
            "-vbr", "on",
            "-application", "voip",
            "-y", "-loglevel", "error",
            output_path
        ], check=True, capture_output=True, timeout=180)

        if os.path.exists(output_path):
            print(f"✅ تبدیل موفق | حجم خروجی: {os.path.getsize(output_path)} بایت")
            return output_path
        else:
            print(f"❌ فایل خروجی ساخته نشد")
            return None

    except FileNotFoundError:
        print("❌ ffmpeg نصب نیست. با دستور apt-get install ffmpeg نصبش کن")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ خطای ffmpeg:")
        print(f"   {e.stderr.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        print(f"❌ خطا در تبدیل: {type(e).__name__}: {e}")
        return None


# ========== آپلود و ارسال به کانال ==========
async def upload_voice_and_send(file_path, chat_id):
    try:
        result = await bot.get_upload_url("Voice")
        print(f"📥 get_upload_url(Voice): {result}")

        upload_url = None
        if isinstance(result, dict):
            upload_url = (
                result.get("data", {}).get("upload_url")
                or result.get("upload_url")
                or result.get("url")
            )
        elif isinstance(result, str):
            upload_url = result

        if not upload_url:
            print(f"❌ upload_url نگرفت: {result}")
            return False

        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "audio/ogg")}
            up_resp = requests.post(upload_url, files=files, timeout=180)

        up_result = up_resp.json()
        print(f"📥 upload response: {up_result}")

        file_id = (
            up_result.get("data", {}).get("file_id")
            or up_result.get("file_id")
        )
        if not file_id:
            print(f"❌ file_id نگرفت")
            return False

        try:
            send_resp = await bot.send_voice(chat_id=chat_id, file_id=file_id)
        except AttributeError:
            send_resp = await bot.send_file(chat_id=chat_id, file_id=file_id, type="Voice")

        print(f"📤 send_voice: {send_resp}")
        return send_resp.get("status") == "OK"
    except Exception as e:
        print(f"❌ خطا در upload_voice_and_send: {e}")
        return False


# ========== /start ==========
@bot.on_message(commands=["start"])
async def start_handler(bot: Robot, message: Message):
    if not is_private_chat(message):
        return
    await bot.send_message(
        chat_id=message.chat_id,
        text="لطفا آهنگ خود را ارسال کنید📥"
    )


# ========== هندلر اصلی ==========
@bot.on_message()
async def main_handler(bot: Robot, message: Message):
    sender_id = message.sender_id or ""
    chat_id = message.chat_id or ""
    text = (message.text or "").strip()

    # دستور 0
    if text == "0":
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"🆔 chat_id: {chat_id}\n"
                f"🆔 sender_id: {sender_id}\n"
                f"📁 sender_type: {(message.raw_data or {}).get('sender_type')}"
            )
        )
        return

    if not is_private_chat(message):
        return

    if sender_id in BANNED_USERS:
        return

    # دستورات مالک
    if sender_id == OWNER_ID and "=" in text:
        parts = text.split("=", 1)
        if len(parts) == 2:
            user_id, action = parts[0].strip(), parts[1].strip()
            if action == "بن":
                BANNED_USERS.add(user_id)
                await bot.send_message(OWNER_CHAT_ID, f"✅ کاربر {user_id} مسدود شد.")
                return
            elif action == "رفع":
                BANNED_USERS.discard(user_id)
                await bot.send_message(OWNER_CHAT_ID, f"✅ کاربر {user_id} رفع مسدودی شد.")
                return

    if not hasattr(message, 'file') or not message.file:
        return

    if not is_audio_file(message):
        await bot.send_message(chat_id=chat_id, text="لطفا فقط آهنگ بفرستید.")
        return

    file_obj = message.file
    file_name = get_file_attr(file_obj, 'file_name', default='') or f"audio_{message.message_id}.mp3"
    file_id = get_file_attr(file_obj, 'file_id', default=None)

    if not file_id:
        await bot.send_message(chat_id=chat_id, text="❌ خطا در شناسایی فایل")
        return

    # فوروارد به ادمین
    try:
        await bot.forward_message(
            from_chat_id=chat_id,
            message_id=message.message_id,
            to_chat_id=OWNER_CHAT_ID
        )
    except Exception as e:
        print(f"⚠️ خطا در فوروارد: {e}")

    # اطلاعات کاربر
    info_text = (
        f"🆔 chat_id: {chat_id}\n"
        f"🆔 sender_id: {sender_id}\n"
        f"📛 نام فایل: {file_name}"
    )
    await bot.send_message(chat_id=OWNER_CHAT_ID, text=info_text)

    await bot.send_message(
        chat_id=chat_id,
        text="درحال دانلود و ارسال آهنگ به کانال."
    )

    await process_audio(bot, message, file_id, file_name, TARGET_CHANNEL_ID)


# ========== پردازش ==========
async def process_audio(bot: Robot, message: Message, file_id: str, file_name: str, target_channel: str):
    chat_id = message.chat_id
    input_path = os.path.join(TEMP_DIR, file_name)
    voice_path = None

    try:
        download_url = get_download_url(file_id)
        if not download_url:
            await bot.send_message(chat_id, "❌ خطا در دریافت لینک فایل")
            return

        r = requests.get(download_url, timeout=180)
        with open(input_path, "wb") as f:
            f.write(r.content)

        print(f"✅ دانلود موفق: {len(r.content)} بایت")

        voice_path = convert_to_voice(input_path)
        if not voice_path:
            await bot.send_message(chat_id, "❌ خطا در تبدیل به ویس")
            return

        success = await upload_voice_and_send(voice_path, target_channel)
        if success:
            await bot.send_message(chat_id, "✅ آهنگ به صورت ویس به کانال ارسال شد.")
        else:
            await bot.send_message(chat_id, "❌ خطا در ارسال به کانال")

    except Exception as e:
        print(f"❌ خطای پردازش: {e}")
        await bot.send_message(chat_id, f"❌ خطا: {e}")
    finally:
        for p in [input_path, voice_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass


# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات در حال اجراست...")
    bot.run()
