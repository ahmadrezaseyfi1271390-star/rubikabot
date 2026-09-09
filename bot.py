import os
import requests
import gdown
from urllib.parse import urlparse
import mimetypes
from rubpy import Bot, Message

TOKEN = "CDIBFG0LOWKACQPCLOMUZYMXHATMXOPJXNOZEJVDBLAGQYTOWBOQRTZWGHZPQTLS"
DOWNLOAD_FOLDER = "./downloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

bot = Bot(token=TOKEN)

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
async def handle_message(message: Message):
    if not message.text:
        return
    
    # پیدا کردن لینک در پیام
    words = message.text.split()
    url = None
    for word in words:
        if word.startswith('http://') or word.startswith('https://'):
            url = word
            break
    
    if not url:
        return
    
    # پیام در حال دانلود
    await message.reply("⏳ در حال دانلود فایل...")
    
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
        
        # دانلود
        await message.reply(f"📥 دانلود: {filename}")
        download_file(url, output_path)
        
        # ارسال بر اساس نوع
        if file_type == 'audio':
            await bot.send_audio(
                chat_id=message.chat_id, 
                audio=output_path, 
                caption=filename
            )
        elif file_type == 'image':
            await bot.send_photo(
                chat_id=message.chat_id, 
                photo=output_path, 
                caption=filename
            )
        elif file_type == 'video':
            await bot.send_video(
                chat_id=message.chat_id, 
                video=output_path, 
                caption=filename
            )
        else:
            await bot.send_document(
                chat_id=message.chat_id, 
                document=output_path, 
                caption=filename
            )
        
        os.remove(output_path)
        await message.reply("✅ ارسال شد!")
        
    except Exception as e:
        await message.reply(f"❌ خطا: {str(e)}")

if __name__ == "__main__":
    print("🤖 ربات دانلودر روشن شد...")
    print("⏳ منتظر دریافت لینک...")
    bot.run()
