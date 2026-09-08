import os
import requests
import gdown
from urllib.parse import urlparse
import mimetypes
from rubka import Robot, Message

TOKEN = "CDIBFG0LOWKACQPCLOMUZYMXHATMXOPJXNOZEJVDBLAGQYTOWBOQRTZWGHZPQTLS"
DOWNLOAD_FOLDER = "./downloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

bot = Robot(token=TOKEN)

def detect_file_type(content_type, url):
    """تشخیص نوع فایل بر اساس محتوا و پسوند"""
    
    # لیست پسوندهای صوتی
    audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.opus', '.wma']
    # لیست پسوندهای تصویری
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg', '.ico']
    # لیست پسوندهای ویدیویی
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.3gp', '.m4v', '.webm']
    
    # بررسی از روی content-type
    if content_type:
        if 'audio' in content_type:
            return 'audio'
        elif 'image' in content_type:
            return 'image'
        elif 'video' in content_type:
            return 'video'
    
    # بررسی از روی پسوند فایل
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1].lower()
    
    if extension in audio_extensions:
        return 'audio'
    elif extension in image_extensions:
        return 'image'
    elif extension in video_extensions:
        return 'video'
    
    return 'document'

def download_file(url, output_path):
    """دانلود فایل از لینک"""
    
    # اگر لینک گوگل درایو بود
    if 'drive.google.com' in url or 'docs.google.com' in url:
        try:
            gdown.download(url, output_path, quiet=True, fuzzy=True)
            return True
        except Exception as e:
            raise Exception(f"خطا در دانلود از گوگل‌درایو: {e}")
    
    # دانلود معمولی با requests
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # تشخیص نوع فایل
        content_type = response.headers.get('content-type', '')
        file_type = detect_file_type(content_type, url)
        
        # تنظیم پسوند مناسب
        extension = os.path.splitext(urlparse(url).path)[1]
        if not extension:
            extension = mimetypes.guess_extension(content_type.split(';')[0]) or ''
        
        if extension and not output_path.endswith(extension):
            output_path += extension
        
        # دانلود فایل
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
        
    except Exception as e:
        raise Exception(f"خطا در دانلود فایل: {e}")

@bot.on_message()
async def handle_link(bot: Robot, message: Message):
    # بررسی وجود لینک در پیام
    if not message.text:
        return
    
    # استخراج لینک از پیام
    words = message.text.split()
    url = None
    
    for word in words:
        if word.startswith('http://') or word.startswith('https://'):
            url = word
            break
    
    if not url:
        return
    
    await message.reply_text(f"⏳ در حال پردازش لینک...\n📎 {url[:50]}...")
    
    try:
        # تشخیص نوع فایل قبل از دانلود
        response = requests.head(url, timeout=10, allow_redirects=True)
        content_type = response.headers.get('content-type', '')
        file_type = detect_file_type(content_type, url)
        
        # پیام مناسب بر اساس نوع فایل
        type_names = {
            'audio': '🎵 فایل صوتی',
            'image': '🖼️ تصویر',
            'video': '🎬 ویدیو',
            'document': '📄 فایل'
        }
        
        await message.reply_text(f"📥 شناسایی شد: {type_names.get(file_type, 'فایل')}\n⏳ در حال دانلود...")
        
        # مسیر ذخیره فایل
        filename = os.path.basename(urlparse(url).path) or 'downloaded_file'
        if not os.path.splitext(filename)[1]:
            ext = mimetypes.guess_extension(content_type.split(';')[0]) or ''
            filename += ext
        
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # دانلود فایل
        download_file(url, output_path)
        
        # ارسال فایل بر اساس نوع
        with open(output_path, 'rb') as f:
            if file_type == 'audio':
                await bot.send_audio(
                    chat_id=message.chat_id, 
                    audio=f, 
                    caption=f"🎵 فایل صوتی\n📎 {filename}"
                )
            elif file_type == 'image':
                await bot.send_image(
                    chat_id=message.chat_id, 
                    image=f, 
                    caption=f"🖼️ تصویر\n📎 {filename}"
                )
            elif file_type == 'video':
                await bot.send_video(
                    chat_id=message.chat_id, 
                    video=f, 
                    caption=f"🎬 ویدیو\n📎 {filename}"
                )
            else:
                await bot.send_document(
                    chat_id=message.chat_id, 
                    document=f, 
                    caption=f"📄 فایل\n📎 {filename}"
                )
        
        # پاک کردن فایل بعد از ارسال
        os.remove(output_path)
        await message.reply_text("✅ فایل با موفقیت ارسال شد!")
        
    except Exception as e:
        await message.reply_text(f"❌ خطا: {str(e)}")

if __name__ == "__main__":
    print("🤖 ربات دانلودر روشن شد...")
    print(f"📁 پوشه دانلود: {os.path.abspath(DOWNLOAD_FOLDER)}")
    print("📩 هر لینکی رو براش بفرستید، فایل رو دانلود و ارسال میکنه")
    print("=" * 50)
    bot.run()
