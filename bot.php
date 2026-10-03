<?php
require_once 'vendor/autoload.php';

use RubikaBot\Bot;
use RubikaBot\Filters\Filters;

$token = getenv('CEFCFD0ECUJKKLJTVKOPNCVNBUKJBVQZVJIJUQCSYCOPCUQYHFDIEHORVRRRAXCU');
$bot = new Bot($token);

// ========== تنظیمات ==========
$TARGET_CHANNEL_ID = "c0DI7gA0218940ebab512954822551df";
$OWNER_CHAT_ID = "b0FXnfh0BEu804900ee2661517d3ae60";
$OWNER_ID = "u0FXnfh0fece55a99ad52d509fb50335";
$TEMP_DIR = sys_get_temp_dir();

$BANNED_USERS = [];

// ========== /start ==========
$bot->onMessage(Filters::command('start'), function(Bot $bot, $message) {
    if (($message->chat_type ?? '') !== 'User') return;
    
    $bot->chat($message->chat_id)
        ->message("لطفا آهنگ خود را ارسال کنید📥")
        ->send();
});

// ========== هندلر اصلی ==========
$bot->onMessage(function(Bot $bot, $message) use ($TARGET_CHANNEL_ID, $OWNER_CHAT_ID, $OWNER_ID, $TEMP_DIR, &$BANNED_USERS) {
    
    $senderId = $message->sender_id ?? '';
    $chatId = $message->chat_id ?? '';
    $chatType = $message->chat_type ?? '';
    $text = trim($message->text ?? '');
    
    // ===== دستور 0 در همه جا کار می‌کند =====
    if ($text === '0') {
        $bot->chat($chatId)
            ->message(
                "🆔 chat_id: {$chatId}\n" .
                "🆔 sender_id: {$senderId}\n" .
                "📁 chat_type: {$chatType}"
            )
            ->send();
        return;
    }
    
    // ===== بقیه فقط در چت شخصی =====
    if ($chatType !== 'User') return;
    
    // بررسی بن بودن
    if (in_array($senderId, $BANNED_USERS)) return;
    
    // ===== دستورات مالک (بن/رفع) =====
    if ($senderId === $OWNER_ID && strpos($text, '=') !== false) {
        [$userId, $action] = array_map('trim', explode('=', $text, 2));
        if ($action === 'بن') {
            $BANNED_USERS[] = $userId;
            $bot->chat($OWNER_CHAT_ID)->message("✅ کاربر {$userId} مسدود شد.")->send();
            return;
        } elseif ($action === 'رفع') {
            $BANNED_USERS = array_diff($BANNED_USERS, [$userId]);
            $bot->chat($OWNER_CHAT_ID)->message("✅ کاربر {$userId} رفع مسدودی شد.")->send();
            return;
        }
    }
    
    // ===== بررسی فایل =====
    if (!isset($message->file_id)) return;
    
    $fileName = $message->file_name ?? "";
    $fileExt = strtolower(pathinfo($fileName, PATHINFO_EXTENSION));
    
    // ===== تشخیص نوع فایل =====
    // فقط فایل‌های صوتی (mp3, m4a, wav, aac, ...) مجاز هستند
    $allowedAudioExt = ['mp3', 'm4a', 'wav', 'aac', 'flac', 'wma', 'ogg', 'opus', 'amr', 'ac3', 'aiff'];
    
    // بررسی اینکه آیا فایل صوتی است یا خیر
    $isAudio = in_array($fileExt, $allowedAudioExt);
    
    // اگر ویس (ogg/opus ارسالی کاربر) یا عکس یا فیلم یا سند بود
    if (!$isAudio) {
        $bot->chat($chatId)
            ->message("لطفا فقط آهنگ بفرستید.")
            ->send();
        return;
    }
    
    // ===== فوروارد به ادمین + اطلاعات کاربر =====
    try {
        $bot->forwardFrom($chatId)
            ->messageId($message->message_id)
            ->forwardTo($OWNER_CHAT_ID)
            ->forward();
    } catch (Exception $e) {
        error_log("Forward error: " . $e->getMessage());
    }
    
    // گرفتن نام کاربری و اطلاعات کاربر
    $userInfo = null;
    try {
        $userInfo = $bot->getChat(['chat_id' => $senderId]);
    } catch (Exception $e) {
        error_log("getChat error: " . $e->getMessage());
    }
    
    $userName = $userInfo['data']['username'] ?? null;
    $firstName = $userInfo['data']['first_name'] ?? '';
    $lastName = $userInfo['data']['last_name'] ?? '';
    
    $infoText = "🆔 chat_id: {$chatId}\n";
    $infoText .= "🆔 sender_id: {$senderId}\n";
    $infoText .= "👤 نام: {$firstName} {$lastName}\n";
    if ($userName) {
        $infoText .= "🔗 یوزرنیم: @{$userName}\n";
    }
    $infoText .= "📛 نام فایل: {$fileName}";
    
    $bot->chat($OWNER_CHAT_ID)
        ->message($infoText)
        ->send();
    
    // ===== پیام به کاربر =====
    $bot->chat($chatId)
        ->message("درحال دانلود و ارسال آهنگ به کانال.")
        ->send();
    
    // ===== پردازش فایل =====
    processAudio($bot, $message, $TARGET_CHANNEL_ID, $TEMP_DIR);
});

// ========== تابع پردازش: دانلود + تبدیل به ویس + ارسال به کانال ==========
function processAudio(Bot $bot, $message, $targetChannel, $tempDir) {
    $fileId = $message->file_id;
    $chatId = $message->chat_id;
    $fileName = $message->file_name ?? "audio_" . $message->message_id;
    
    $inputPath = $tempDir . "/" . $fileName;
    $outputPath = $tempDir . "/voice_" . pathinfo($fileName, PATHINFO_FILENAME) . ".ogg";
    
    // ۱) دریافت لینک دانلود
    $fileInfo = $bot->getFile(['file_id' => $fileId]);
    $downloadUrl = $fileInfo['data']['download_url'] ?? null;
    if (!$downloadUrl) {
        $bot->chat($chatId)->message("❌ خطا در دریافت لینک فایل")->send();
        return;
    }
    
    // ۲) دانلود
    file_put_contents($inputPath, file_get_contents($downloadUrl));
    
    // ۳) تبدیل به ویس (OGG/Opus)
    $cmd = "ffmpeg -i " . escapeshellarg($inputPath) 
         . " -ac 1 -map 0:a -codec:a libopus -b:a 48k -vbr on -application voip "
         . escapeshellarg($outputPath) . " 2>&1";
    exec($cmd, $output, $returnCode);
    
    if ($returnCode !== 0 || !file_exists($outputPath)) {
        $bot->chat($chatId)->message("❌ خطا در تبدیل به ویس")->send();
        @unlink($inputPath);
        return;
    }
    
    // ۴) آپلود و ارسال به کانال
    try {
        $bot->chat($targetChannel)
            ->file($outputPath)
            ->sendFile();
        
        $bot->chat($chatId)
            ->message("✅ آهنگ به صورت ویس به کانال ارسال شد.")
            ->send();
    } catch (Exception $e) {
        $bot->chat($chatId)
            ->message("❌ خطا در ارسال به کانال: " . $e->getMessage())
            ->send();
    }
    
    // ۵) پاکسازی
    @unlink($inputPath);
    @unlink($outputPath);
}

$bot->run();
