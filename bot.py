import os
import time
import requests
import tempfile

# ========== تنظیمات ==========
BOT_TOKEN = "CEFCFD0ECUJKKLJTVKOPNCVNBUKJBVQZVJIJUQCSYCOPCUQYHFDIEHORVRRRAXCU"
OWNER_ID = "u0FXnfh0fece55a99ad52d509fb50335"
OWNER_CHAT_ID = "b0FXnfh0BEu804900ee2661517d3ae60"
API_BASE = f"https://botapi.rubika.ir/v3/{BOT_TOKEN}"
# ==========================

TEMP_DIR = tempfile.mkdtemp(prefix="rubika_uploader_")
PROCESSED_IDS = set()

EXTENSION_TO_TYPE = {
    '.jpg': 'Image', '.jpeg': 'Image', '.png': 'Image', '.gif': 'Image', '.webp': 'Image',
    '.mp4': 'Video', '.mov': 'Video', '.avi': 'Video', '.mkv': 'Video',
    '.mp3': 'Music', '.m4a': 'Music', '.wav': 'Music', '.aac': 'Music', '.flac': 'Music',
    '.ogg': 'Voice', '.opus': 'Voice',
    '.pdf': 'File', '.doc': 'File', '.docx': 'File', '.zip': 'File', '.rar': 'File',
    '.txt': 'File', '.apk': 'File', '.exe': 'File', '.xlsx': 'File', '.pptx': 'File',
}


def api_call(method, data=None):
    try:
        resp = requests.post(f"{API_BASE}/{method}", json=data or {}, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"❌ خطا در {method}: {e}")
        return {}


def extract_file_info(msg):
    file_data = msg.get("file") or msg.get("file_inline")
    if not file_data:
        return None
    return {
        "file_id": file_data.get("file_id"),
        "file_name": file_data.get("file_name") or file_data.get("name") or "",
        "mime": file_data.get("mime") or "",
        "size": file_data.get("size") or 0,
    }


def get_file_type(file_info):
    name = (file_info.get("file_name") or "").lower()
    mime = (file_info.get("mime") or "").lower()
    for ext, ftype in EXTENSION_TO_TYPE.items():
        if name.endswith(ext):
            return ftype
    if "image" in mime:
        return "Image"
    if "video" in mime:
        return "Video"
    if "audio" in mime:
        return "Music"
    return "File"


def handle_upload(chat_id, message_id, file_info):
    file_id = file_info.get("file_id")
    file_name = file_info.get("file_name") or f"file_{message_id}"
    file_type = get_file_type(file_info)

    print(f"📁 فایل دریافتی: {file_name} | نوع: {file_type}")

    status = api_call("sendMessage", {
        "chat_id": chat_id,
        "text": "⬇️ در حال دریافت فایل...",
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
        # ۱. دریافت لینک دانلود از روبیکا
        file_data = api_call("getFile", {"file_id": file_id})
        download_url = (file_data.get("data", {}).get("download_url")
                        or file_data.get("data", {}).get("file_url")
                        or file_data.get("data", {}).get("url"))

        if not download_url:
            edit_status("❌ خطا در دریافت لینک فایل")
            return

        # ۲. دانلود فایل
        edit_status("⬇️ در حال دانلود فایل...")
        r = requests.get(download_url, timeout=180)
        r.raise_for_status()
        file_bytes = r.content
        print(f"✅ دانلود موفق: {len(file_bytes)} بایت")

        # ۳. دریافت لینک آپلود جدید
        edit_status("📤 در حال آپلود مجدد...")
        req = api_call("requestSendFile", {"type": file_type})
        upload_url = req.get("data", {}).get("upload_url")

        if not upload_url:
            edit_status("❌ خطا در دریافت لینک آپلود")
            return

        # ۴. آپلود فایل به روبیکا
        files = {"file": (file_name, file_bytes, "application/octet-stream")}
        up_resp = requests.post(upload_url, files=files, timeout=180)
        up_result = up_resp.json()

        new_file_id = (up_result.get("data", {}).get("file_id")
                       or up_result.get("file_id"))

        if not new_file_id:
            edit_status("❌ خطا در آپلود فایل")
            return

        print(f"✅ آپلود موفق: {new_file_id}")

        # ۵. دریافت لینک دانلود جدید
        edit_status("🔗 در حال دریافت لینک دانلود...")
        final_data = api_call("getFile", {"file_id": new_file_id})
        final_url = (final_data.get("data", {}).get("download_url")
                     or final_data.get("data", {}).get("file_url")
                     or final_data.get("data", {}).get("url"))

        if not final_url:
            edit_status("❌ خطا در دریافت لینک دانلود")
            return

        # ۶. ارسال پیام با لینک به صورت دکمه
        size_mb = len(file_bytes) / (1024 * 1024)

        # دکمه اینلاین برای لینک
        inline_keypad = {
            "rows": [
                {
                    "buttons": [
                        {
                            "id": "download_link",
                            "type": "Simple",
                            "button_text": "🔗 لینک دانلود",
                            "url": final_url
                        }
                    ]
                }
            ]
        }

        result_text = (
            f"✅ فایل با موفقیت آپلود شد!\n\n"
            f"📛 نام فایل: {file_name}\n"
            f"📦 حجم: {size_mb:.2f} مگابایت"
        )

        api_call("sendMessage", {
            "chat_id": chat_id,
            "text": result_text,
            "inline_keypad": inline_keypad,
            "reply_to_message_id": message_id
        })

        # حذف پیام وضعیت
        if status_id:
            api_call("deleteMessage", {
                "chat_id": chat_id,
                "message_id": status_id
            })

    except Exception as e:
        print(f"❌ خطای پردازش: {e}")
        edit_status(f"❌ خطا: {e}")


def main_loop():
    offset_id = None
    print("🤖 ربات آپلودر در حال اجراست...")

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

                # فقط پیام‌های جدید
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

                print(f"📩 پیام | chat_id={chat_id} | text={text!r} | file={bool(file_info)}")

                # دستور /start
                if text == "/start":
                    api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": "لطفا چیزی ارسال کنید"
                    })
                    continue

                # دستور 0
                if text == "0":
                    api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": f"🆔 chat_id: {chat_id}\n🆔 sender_id: {sender_id}"
                    })
                    continue

                # فایل دریافت شد
                if file_info:
                    handle_upload(chat_id, message_id, file_info)
                    continue

                # پیام متنی بدون فایل
                if text and not file_info:
                    api_call("sendMessage", {
                        "chat_id": chat_id,
                        "text": "لطفا چیزی ارسال کنید",
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
    main_loop()
