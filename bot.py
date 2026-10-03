import os
import time
import datetime
import subprocess
import requests
import tempfile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TPE1, TIT2, ID3NoHeaderError

# ========== تنظیمات ==========
BOT_TOKEN = "CEFCFD0ECUJKKLJTVKOPNCVNBUKJBVQZVJIJUQCSYCOPCUQYHFDIEHORVRRRAXCU"
TARGET_CHANNEL_ID = "c0DI7gA0218940ebab512954822551df"
OWNER_ID = "u0FXnfh0fece55a99ad52d509fb50335"
OWNER_CHAT_ID = "b0FXnfh0BEu804900ee2661517d3ae60"
NEW_ARTIST = "@Black_list_remix"
COVER_URL = "https://cdn.imgurl.ir/uploads/s93695_ab8b9c87-0990-4beb-bfaa-cd1bf842caf7.png"
CHANNEL_USERNAME = "@Black_list_remix"
OWNER_USERNAME = "@reza_127_s"
API_BASE = f"https://botapi.rubika.ir/v3/{BOT_TOKEN}"
# ==========================

TEMP_DIR = tempfile.mkdtemp(prefix="rubika_audio_")
PHOTO_PATH = os.path.join(TEMP_DIR, "cover.png")
PHOTO_BYTES = None
PHOTO_FILE_ID = None
PROCESSED_IDS = set()
STARTED_USERS = set()
BANNED_USERS = set()

SUPPORTED_AUDIO_EXTENSIONS = (
    '.mp3', '.aac', '.wma', '.flac', '.ac3', '.ogg', '.m4a',
    '.wav', '.opus', '.aiff', '.alac', '.ape', '.amr'
)


def api_call(method, data=None):
    try:
        resp = requests.post(f"{API_BASE}/{method}", json=data or {}, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"❌ خطا در {method}: {e}")
        return {}


def load_photo_once():
    global PHOTO_BYTES
    if PHOTO_BYTES is not None:
        return PHOTO_BYTES
    try:
        resp = requests.get(COVER_URL, timeout=30)
        resp.raise_for_status()
        PHOTO_BYTES = resp.content
        with open(PHOTO_PATH, "wb") as f:
            f.write(PHOTO_BYTES)
        print("✅ عکس دانلود شد")
        return PHOTO_BYTES
    except Exception as e:
        print(f"❌ خطا در دانلود عکس: {e}")
        return None


def upload_photo_once():
    global PHOTO_FILE_ID
    if PHOTO_FILE_ID:
        return PHOTO_FILE_ID
    if not os.path.exists(PHOTO_PATH):
        return None
    try:
        req = api_call("requestSendFile", {"type": "Image"})
        upload_url = req.get("data", {}).get("upload_url")
        if not upload_url:
            return None
        with open(PHOTO_PATH, "rb") as f:
            files = {"file": ("cover.png", f, "image/png")}
            up = requests.post(upload_url, files=files, timeout=60)
        file_id = up.json().get("data", {}).get("file_id")
        if file_id:
            PHOTO_FILE_ID = file_id
            print("✅ عکس آپلود شد")
        return file_id
    except Exception as e:
        print(f"❌ خطا در آپلود عکس: {e}")
        return None


def extract_file_info(msg):
    file_inline = msg.get("file_inline")
    if file_inline:
        return {
            "file_id": file_inline.get("file_id"),
            "file_name": file_inline.get("file_name") or file_inline.get("name") or "",
            "mime": file_inline.get("mime") or "",
        }
    file_data = msg.get("file")
    if file_data:
        return {
            "file_id": file_data.get("file_id"),
            "file_name": file_data.get("file_name") or file_data.get("name") or "",
            "mime": file_data.get("mime") or "",
        }
    return None


def is_audio_file(file_info):
    if not file_info:
        return False
    name = (file_info.get("file_name") or "").lower()
    mime = (file_info.get("mime") or "").lower()
    if name.endswith(SUPPORTED_AUDIO_EXTENSIONS):
        return True
    if "audio" in mime or "music" in mime:
        return True
    return False


def convert_to_mp3(input_path):
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
        ], check=True, capture_output=True, timeout=180)
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"❌ خطا در تبدیل: {e}")
        return None


def change_metadata(file_path):
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
        if PHOTO_BYTES:
            audio.tags.delall("APIC")
            audio.tags.add(APIC(
                encoding=3, mime="image/png",
                type=3, desc="Cover", data=PHOTO_BYTES
            ))
        audio.save(v2_version=3)
        return True
    except Exception as e:
        print(f"خطا در متادیتا: {e}")
        return False


def upload_and_send(file_path, chat_id):
    try:
        req = api_call("requestSendFile", {"type": "Music"})
        upload_url = req.get("data", {}).get("upload_url")
        if not upload_url:
            print("❌ upload_url نگرفت")
            return False
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "audio/mpeg")}
            up_resp = requests.post(upload_url, files=files, timeout=180)
        file_id = up_resp.json().get("data", {}).get("file_id")
        if not file_id:
            print(f"❌ file_id نگرفت: {up_resp.text[:200]}")
            return False
        send_resp = api_call("sendFile", {
            "chat_id": chat_id,
            "file_id": file_id,
            "type": "Music"
        })
        print(f"📤 sendFile: {send_resp}")
        return send_resp.get("status") == "OK"
    except Exception as e:
        print(f"❌ خطا در upload_and_send: {e}")
        return False


def owner_send(text):
    return api_call("sendMessage", {
        "chat_id": OWNER_CHAT_ID,
        "text": text
    })


def handle_ban(text):
    if "=" not in text:
        return False
    parts = text.split("=", 1)
    if len(parts) != 2:
        return False
    user_id = parts[0].strip()
    action = parts[1].strip()
    if action == "بن":
        BANNED_USERS.add(user_id)
        owner_send(f"✅ کاربر {user_id} مسدود شد.")
        return True
    elif action == "رفع":
        BANNED_USERS.discard(user_id)
        owner_send(f"✅ کاربر {user_id} رفع مسدودی شد.")
        return True
    return False


def handle_start(chat_id, message_id):
    welcome_text = (
        "سلام و درود👋\n"
        "برای ارسال آهنگ شما به کانال باید  فایل آهنگ رو فقط به صورت mp3 ارسال کنید."
    )

    chat_keypad = {
        "rows": [
            {"buttons": [{"id": "contact_owner_btn", "type": "Simple",
                          "button_text": "📞 ارتباط با مالک"}]}
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

    if PHOTO_FILE_ID:
        result = api_call("sendFile", {
            "chat_id": chat_id,
            "file_id": PHOTO_FILE_ID,
            "type": "Image",
            "text": welcome_text,
            "chat_keypad_type": "New",
            "chat_keypad": chat_keypad,
        })
        print(f"📤 sendFile(start): {result}")
        if result.get("status") != "OK":
            r2 = api_call("sendFile", {
                "chat_id": chat_id,
                "file_id": PHOTO_FILE_ID,
                "type": "Image",
                "text": welcome_text,
            })
            r3 = api_call("sendMessage", {
                "chat_id": chat_id,
                "text": "👇",
                "chat_keypad_type": "New",
                "chat_keypad": chat_keypad,
            })
            print(f"📤 fallback: {r2} | {r3}")
        return

    result = api_call("sendMessage", {
        "chat_id": chat_id,
        "text": welcome_text,
        "chat_keypad_type": "New",
        "chat_keypad": chat_keypad,
    })
    print(f"📤 sendMessage(start): {result}")


def handle_audio(chat_id, message_id, file_info):
    file_name = file_info.get("file_name") or f"audio_{message_id}.mp3"
    file_id = file_info.get("file_id")
    local_path = os.path.join(TEMP_DIR, file_name)
    mp3_path = local_path

    status = api_call("sendMessage", {
        "chat_id": chat_id,
        "text": "⬇️ در حال دانلود فایل...",
        "reply_to_message_id": message_id
    })
    status_id = status.get("data", {}).get("message_id")

    def edit_status(text):
        if status_id:
            api_call("editMessageText", {
                "chat_id": chat_id,
                "message_id": status_id,
                "text": text
            })

    try:
        file_data = api_call("getFile", {"file_id": file_id})
        download_url = (file_data.get("data", {}).get("download_url")
                        or file_data.get("data", {}).get("file_url")
                        or file_data.get("data", {}).get("url"))
        if not download_url:
            edit_status("❌ خطا در دریافت لینک فایل")
            return

        r = requests.get(download_url, timeout=180)
        with open(local_path, "wb") as f:
            f.write(r.content)

        ext = os.path.splitext(file_name)[1].lower()
        if ext != '.mp3':
            edit_status("⚙️ در حال تبدیل فرمت به MP3...")
            converted = convert_to_mp3(local_path)
            if converted:
                mp3_path = converted
                if os.path.exists(local_path):
                    os.remove(local_path)
            else:
                edit_status("❌ خطا در تبدیل فرمت")
                return

        edit_status("⚙️ در حال پردازش و تغییر متادیتا...")
        change_metadata(mp3_path)

        success = upload_and_send(mp3_path, TARGET_CHANNEL_ID)

        if success:
            edit_status("✅ آهنگ با موفقیت به کانال ارسال شد.")
        else:
            edit_status("❌ خطا در ارسال به کانال")

    except Exception as e:
        print(f"❌ خطای پردازش: {e}")
        edit_status(f"❌ خطا: {e}")
    finally:
        for p in [mp3_path, local_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass


def main_loop():
    offset_id = None
    print("🤖 ربات در حال اجراست...")

    while True:
        try:
            data = {"limit": 50}
            if offset_id:
                data["offset_id"] = offset_id

            resp = api_call("getUpdates", data)
            if resp.get("status") != "OK":
                time.sleep(0.3)
                continue

            updates = resp.get("data", {}).get("updates", [])
            new_offset = resp.get("data", {}).get("next_offset_id")
            if new_offset:
                offset_id = new_offset

            now = time.time()

            for upd in updates:
                if upd.get("type") != "NewMessage":
                    continue

                msg = upd.get("new_message", {})
                chat_id = upd.get("chat_id")
                message_id = msg.get("message_id")
                text = (msg.get("text") or "").strip()
                sender_type = msg.get("sender_type", "")
                sender_id = msg.get("sender_id", "")

                try:
                    msg_time = float(msg.get("time", 0))
                except (ValueError, TypeError):
                    msg_time = 0

                if msg_time > 1e12:
                    msg_time = msg_time / 1000

                if msg_time and (now - msg_time) > 3:
                    continue

                if sender_type != "User":
                    continue

                if message_id in PROCESSED_IDS:
                    continue
                PROCESSED_IDS.add(message_id)

                file_info = extract_file_info(msg)

                print(f"📩 پیام | chat_id={chat_id} | sender_id={sender_id} | text={text!r} | file={bool(file_info)}")

                # ===== کاربر بن‌شده — فقط با sender_id =====
                if sender_id in BANNED_USERS:
                    print(f"🚫 کاربر بن‌شده | sender_id={sender_id}")
                    continue

                # ===== دستور بن/رفع (فقط مالک) =====
                if sender_id == OWNER_ID and "=" in text:
                    if handle_ban(text):
                        continue

                # دستور 0
                if text == "0":
                    api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": f"🆔 chat_id: {chat_id}\n🆔 sender_id: {sender_id}"
                    })
                    continue

                # /start
                if text == "/start":
                    if chat_id in STARTED_USERS:
                        continue
                    STARTED_USERS.add(chat_id)
                    handle_start(chat_id, message_id)
                    continue

                # دکمه ارتباط با مالک
                if text == "📞 ارتباط با مالک":
                    api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": (
                            "سلام دوست من.\n"
                            "برای دریافت اطلاعات بیشتر همینطور همکاری و تبلیغات "
                            "میتونی به مالک پیام بدی.\n"
                            "توجه داشته باش که تبلیغات هم در ربات و هم در کانال گذاشته میشود.\n"
                            f"{OWNER_USERNAME}"
                        ),
                        "reply_to_message_id": message_id
                    })
                    continue

                # آهنگ
                if file_info and is_audio_file(file_info):
                    owner_send(
                        f"🎵 آهنگ جدید\n"
                        f"👤 chat_id: {chat_id}\n"
                        f"🆔 sender_id: {sender_id}\n"
                        f"📛 نام فایل: {file_info.get('file_name', '?')}"
                    )
                    fwd = api_call("forwardMessage", {
                        "from_chat_id": chat_id,
                        "message_id": message_id,
                        "to_chat_id": OWNER_CHAT_ID
                    })
                    print(f"📨 forward: {fwd}")
                    handle_audio(chat_id, message_id, file_info)
                    continue

                # فایل غیرصوتی
                if file_info:
                    api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": (
                            "دوست گرامی.\n"
                            "این ربات فقط برای ارسال موزیک و آهنگ میباشد "
                            "لطفا فایل های mp3 ، ogg ،... بفرستید."
                        ),
                        "reply_to_message_id": message_id
                    })

        except KeyboardInterrupt:
            print("🛑 متوقف شد")
            break
        except Exception as e:
            print(f"❌ خطای حلقه: {e}")
            time.sleep(0.5)

        time.sleep(0.3)


if __name__ == "__main__":
    load_photo_once()
    upload_photo_once()
    main_loop()
