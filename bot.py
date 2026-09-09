import os
import requests
import gdown
from urllib.parse import urlparse
import mimetypes
from rubka import Robot, Message, InlineBuilder

TOKEN = "CDIBFG0LOWKACQPCLOMUZYMXHATMXOPJXNOZEJVDBLAGQYTOWBOQRTZWGHZPQTLS"
DOWNLOAD_FOLDER = "./downloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

bot = Robot(token=TOKEN)

# دیکشنری برای ذخیره موقت اطلاعات کاربر
user_data = {}

def get_file_type(content_type, url):
    if content_type and 'audio' in content_type:
        return 'audio'
    elif content_type and 'image' in content_type:
        return 'image'
    elif content_type and 'video' in content_type:
        return 'video'
    
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.opus']:
        return 'audio'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return 'image'
    elif ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.3gp']:
        return 'video'
    return 'document'

def download_file(url, output_path):
    if 'drive.google.com' in url or 'docs.google.com' in url:
        gdown.download(url, output_path, quiet=True, fuzzy=True)
        return True
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return True

@bot.on_message()
async def handle_message(bot: Robot, message: Message):
    print(f"📩 پیام جدید: {message.text}")
    
    if not message.text:
        return
    
    words = message.text.split()
    url = None
    for word in words:
        if word.startswith('http://') or word.startswith('https://'):
            url = word
            break
    
    if not url:
        await message.reply("❌ لینکی پیدا نشد! لطفاً یه لینک معتبر بفرستید.")
        return
    
    # ذخیره لینک برای کاربر
    user_data[message.chat_id] = url
    
    # ساخت دکمه‌های انتخاب
    keypad = InlineBuilder()
    keypad.add_row()
    keypad.add_button("🎵 آهنگ (با پلیر)", "music")
    keypad.add_button("🎤 ویس", "voice")
    
    await message.reply(
        "🎵 فایل صوتی شناسایی شد!\n"
        "لطفاً نحوه ارسال رو انتخاب کن:",
        keypad=keypad
    )

@bot.on_callback()
async def handle_callback(bot: Robot, message: Message, query):
    chat_id = message.chat_id
    
    if chat_id not in user_data:
        await message.reply("❌ لینکی پیدا نشد! لطفاً دوباره لینک رو بفرست.")
        return
    
    url = user_data[chat_id]
    selected = query.data
    
    await message.reply(f"⏳ در حال دانلود فایل...")
    
    try:
        # تشخیص نوع فایل
        response = requests.head(url, timeout=10, allow_redirects=True)
        content_type = response.headers.get('content-type', '')
        file_type = get_file_type(content_type, url)
        
        # ساخت اسم فایل
        filename = os.path.basename(urlparse(url).path) or 'file'
        if not os.path.splitext(filename)[1]:
            ext = mimetypes.guess_extension(content_type.split(';')[0]) or ''
            filename += ext
        
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        await message.reply(f"📥 دانلود: {filename}")
        download_file(url, output_path)
        
        # ارسال بر اساس انتخاب کاربر
        with open(output_path, 'rb') as f:
            if selected == "music":
                await bot.send_music(
                    chat_id=chat_id, 
                    music=f, 
                    caption=f"🎵 {filename}"
                )
            else:  # voice
                await bot.send_voice(
                    chat_id=chat_id, 
                    voice=f, 
                    caption=f"🎤 {filename}"
                )
        
        os.remove(output_path)
        await message.reply("✅ ارسال شد!")
        
        # پاک کردن اطلاعات کاربر
        del user_data[chat_id]
        
    except Exception as e:
        await message.reply(f"❌ خطا: {str(e)}")

if __name__ == "__main__":
    print("🤖 ربات دانلودر صوتی روشن شد...")
    print("⏳ منتظر دریافت لینک...")
    bot.run()
