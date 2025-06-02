import logging
import asyncio
import json
import os
import aiohttp
import sqlite3
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter
import psutil
import logging.handlers

TOKEN = "KENDİ BOT TOKENİNİZİ GİRİN."
ADMIN_ID = KENDİ TELEGRAM IDNİZİ GİRİN
CHECK_API = "KENDİ CHECK APİNİZİ GİRİN." #GEN KARTLARA KARŞIT LOGLAMA VAR. GEN KART SOKANLARI LİVE.TXT DOSYASINDAN TESPİT EDEBİLİR AYRI ŞEKİLDE BANLAYABİLİRSİNİZ 000 GİBİ CVVLERİ OTOMATİK BANLIYOR.
REQUIRED_CHANNELS = ["@k4be4duyuru", "@wazebiola", "@darqgrup", "@k4be4"]
DATABASE_FILE = "users.db"
LIVE_FILE_PATH = "live.txt"
BOT_USERNAME = "K4be4checkerbot"
DAILY_CHECK_LIMIT = 5
CHECK_COOLDOWN_NORMAL = 3
CHECK_COOLDOWN_VIP = 0
RATE_LIMIT_PER_MINUTE = 10
CAPTCHA_TIMEOUT = 300

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

error_logger = logging.getLogger("error_logger")
error_handler = logging.handlers.RotatingFileHandler(
    "errors.log", maxBytes=5*1024*1024, backupCount=5
)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)

MESSAGES = {
    "tr": {
        "welcome": (
            "🎉 𝐊𝟒𝐁𝐄 𝐂𝐇𝐄𝐂𝐊𝐄𝐑'e hoş geldin!\n"
            "@k4be4 ve @k4be4duyuru kanallarına katıl. 🔐 Doğrulama bu doğrulamayı yapınca tekrar /start veriniz.\n"
            "📩 İletişim: @serkancobanexee\n"
            "Başlamak için: /help\n"
            "Dil seç: /language"
        ),
        "card_missing": "❌ Kart bilgisi eksik! Örnek: /check 4921307029421135|12|2025|714",
        "invalid_format": "❌ Geçersiz format! Örnek: /check 4921307029421135|12|2025|714",
        "checking": "🔍 Kontrol ediliyor: {card} ({current}/{total})",
        "live": "🤍 𝐋𝐈̇𝐕𝐄 ⚡\n━━━━━━━━━━━━━\n[ϟ] Cc: {card}\n[ϟ] Durum: Onaylandı 🤍\n[ϟ] Tür: {card_type}\n[ϟ] Banka: {bank_name} - 🇹🇷\n[ϟ] Ülke: {country}\n[ϟ] Süre: {duration}s\n[ϟ] Tarih: {time}\n[ϟ] Kullanıcı: {vip_status}\n━━━━━━━━━━━━━\n👨‍💻 @serkancobanexee",
        "declined": "🖤 𝐃𝐄𝐂𝐋𝐈̇𝐍𝐄 🖤 \n━━━━━━━━━━━━━\n[ϟ] Cc: {card}\n[ϟ] Durum: Reddedildi ❌\n[ϟ] Tür: {card_type}\n[ϟ] Banka: {bank_name} - 🇹🇷\n[ϟ] Ülke: {country}\n[ϟ] Süre: {duration}s\n[ϟ] Tarih: {time}\n[ϟ] Kullanıcı: {vip_status}\n━━━━━━━━━━━━━\n👨‍💻 @serkancobanexee",
        "api_error": "❌ API hatası: {error}",
        "general_error": "❌ Hata: {error}",
        "admin_only": "🔒 Bu komut sadece admin için!",
        "check_again": "🔄 Tekrar Kontrol Et",
        "quick_actions": "🚀 Hızlı İşlemler",
        "new_card": "➕ Yeni kart: /check <kart_no>|<ay>|<yıl>|<cvv>",
        "channel_error": "❌ Kanallara katılmadın! Katıl ve /start ile devam et.",
        "channel_success": "✅ Kanallara katıldın! Dil seç: /language",
        "join_channel_k4be4duyuru": "📢 @k4be4duyuru'ya Katıl",
        "join_channel_wazebiola": "📢 @wazebiola'ya Katıl",
        "join_channel_darqgrup": "📢 @darqgrup'a Katıl",
        "join_channel_k4be4": "📢 @k4be4'e Katıl",
        "check_membership": "✅ Katıldım, Kontrol Et",
        "language_select": "🌐 Dil seç:\nMevcut: {lang}",
        "language_tr": "🇹🇷 Türkçe",
        "language_en": "🇬🇧 English",
        "language_changed": "✅ Dil: {lang}",
        "masscheck_prompt": "📋 Kartları satır satır gir (max 25):\nÖrnek:\n4921307029421135|12|2025|714",
        "masscheck_limit": "❌ Maks 25 kart! {count} kart girdin.",
        "masscheck_start": "🔍 Toplu kontrol başlıyor ({count} kart)...",
        "masscheck_done": "✅ Toplu kontrol bitti! Sonuçlar: sonuclar.txt",
        "check_cooldown_msg": "⏳ {seconds}s bekle!",
        "banned_message": "🚫 Banlandın! Sebep: {reason}\n📩 Destek: @serkancobanexee",
        "no_checks_left": "❌ Günlük limit doldu! VIP al: @serkancobanexee",
        "user_info": (
            "📊 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐁𝐢𝐥𝐠𝐢𝐥𝐞𝐫𝐢\n"
            "🏆 𝐕𝐈𝐏: {vip_status}\n"
            "📅 𝐊𝐚𝐭ı𝐥ı𝐦: {days} gün\n"
            "🔍 𝐓𝐨𝐩𝐥𝐚𝐦 𝐊𝐨𝐧𝐭𝐫𝐨𝐥: {total_checks}\n"
            "📈 𝐊𝐚𝐥𝐚𝐧 𝐊𝐨𝐧𝐭𝐫𝐨𝐥: {remaining_checks}\n"
            "💰 𝐊𝐫𝐞𝐝𝐢𝐥𝐞𝐫: {credits}\n"
            "🌟 𝐏𝐮𝐚𝐧: {points}"
        ),
        "price_list": (
            "💰 **VIP Fiyatları**\n"
            "📅 Günlük: 100₺\n"
            "📆 Haftalık: 250₺\n"
            "🗓 Aylık: 500₺\n"
            "📆 Yıllık: 1.000₺\n"
            "♾ Sınırsız: 1.500₺\n"
            "📩 Satın al: @serkancobanexee"
        ),
        "leaderboard": "🏆 𝐋𝐢𝐝𝐞𝐫 𝐓𝐚𝐛𝐥𝐨𝐬𝐮\n{leaderboard}",
        "no_users": "❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐲𝐨𝐤!",
        "daily_bonus": "🎁 𝐆𝐮̈𝐧𝐥𝐮̈𝐤 𝐛𝐨𝐧𝐮𝐬 𝐚𝐥ı𝐧𝐝ı! 𝐊𝐚𝐥𝐚𝐧: {checks}",
        "daily_cooldown": "⏳ 𝐆𝐮̈𝐧𝐥𝐮̈𝐤 𝐛𝐨𝐧𝐮𝐬 𝐚𝐥ı𝐧𝐝ı! 𝐘𝐚𝐫ı𝐧 𝐝𝐞𝐧𝐞.",
        "report_usage": "📩 Kullanım: /report <mesaj>",
        "report_sent": "✅ Rapor gönderildi!",
        "report_received": "📩 Rapor\n👤 Kullanıcı: {user_id}\n💬 Mesaj: {message}",
        "stats": (
            "📊 𝐁𝐨𝐭 𝐈̇𝐬𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐤𝐥𝐞𝐫𝐢\n"
            "👥 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı: {user_count}\n"
            "🔍 𝐊𝐨𝐧𝐭𝐫𝐨𝐥𝐥𝐞𝐫: {total_checks}\n"
            "🏆 𝐕𝐈𝐏: {vip_count}\n"
            "💰 𝐊𝐫𝐞𝐝𝐢𝐥𝐞𝐫: {total_credits}\n"
            "🌟 𝐏𝐮𝐚𝐧𝐥𝐚𝐫: {total_points}"
        ),
        "profile_set": "✅ Profil güncellendi!\n📛 Ad: {nickname}\n📝 Bio: {bio}",
        "profile_view": (
            "🖼 𝐏𝐫𝐨𝐟𝐢𝐥 𝐊𝐚𝐫𝐭ı\n"
            "📛 𝐀𝐝: {nickname}\n"
            "📝 𝐁𝐢𝐨: {bio}\n"
            "🏆 𝐕𝐈𝐏: {vip_status}\n"
            "🌟 𝐏𝐮𝐚𝐧: {points}"
        ),
        "history_view": "📜 𝐊𝐨𝐧𝐭𝐫𝐨𝐥 𝐆𝐞𝐜̧𝐦𝐢𝐬̧𝐢\n{history}",
        "history_empty": "❌ 𝐆𝐞𝐜̧𝐦𝐢𝐬̧ 𝐛𝐨𝐬̧!",
        "history_filter": "✅ 𝐅𝐢𝐥𝐭𝐫𝐞𝐥𝐞𝐧𝐦𝐢𝐬̧ 𝐆𝐞𝐜̧𝐦𝐢𝐬̧ ({filter}):\n{history}",
        "vip_status": (
            "🏆 𝐕𝐈𝐏 𝐃𝐮𝐫𝐮𝐦𝐮\n"
            "📅 𝐓𝐮̈𝐫: {vip_status}\n"
            "⏳ 𝐁𝐢𝐭𝐢𝐬̧: {vip_expiry}\n"
            "🔍 𝐊𝐚𝐥𝐚𝐧 𝐊𝐨𝐧𝐭𝐫𝐨𝐥: {remaining_checks}\n"
            "💰 𝐊𝐫𝐞𝐝𝐢𝐥𝐞𝐫: {credits}\n"
            "🌟 𝐏𝐮𝐚𝐧: {points}"
        ),
        "setvip_usage": "📋 Kullanım: /setvip [ID/@username] [süre] [günlük|haftalık|aylık|yıllık|sınırsız]",
        "setvip_success": "✅ {user_id} için VIP: {vip_type}, Bitiş: {expiry}",
        "setvipbulk_usage": "📋 Kullanım: /setvipbulk [ID1,ID2,...] [süre] [günlük|haftalık|aylık|yıllık|sınırsız]",
        "setvipbulk_success": "✅ {count} kullanıcıya VIP ayarlandı!",
        "invite_link": (
            "📩 𝐃𝐚𝐯𝐞𝐭 𝐋𝐢𝐧𝐤𝐢\n{link}\n"
            "👥 𝐇𝐞𝐫 𝐝𝐚𝐯𝐞𝐭: +5 kredi\n"
            "🎁 𝟓 𝐝𝐚𝐯𝐞𝐭: 1 günlük VIP\n"
            "💰 𝐊𝐫𝐞𝐝𝐢𝐥𝐞𝐫𝐢𝐧: {credits}"
        ),
        "invite_credited": "🎉 @{username} 𝐝𝐚𝐯𝐞𝐭 𝐞𝐭𝐭𝐢! +𝟓 𝐤𝐫𝐞𝐝𝐢. 𝐓𝐨𝐩𝐥𝐚𝐦: {credits}",
        "inviter_credited": "🎉 @{invited_username} 𝐤𝐚𝐭ı𝐥𝐝ı! +𝟓 𝐤𝐫𝐞𝐝𝐢. 𝐓𝐨𝐩𝐥𝐚𝐦: {credits}",
        "invite_bonus": "🎁 𝟓 𝐝𝐚𝐯𝐞𝐭 𝐛𝐨𝐧𝐮𝐬𝐮: 𝟏 𝐠𝐮̈𝐧𝐥𝐮̈𝐤 𝐕𝐈𝐏!",
        "already_invited": "❌ 𝐁𝐮 𝐥𝐢𝐧𝐤𝐭𝐞𝐧 𝐤𝐚𝐭ı𝐥𝐝ı𝐧!",
        "captcha_prompt": "🔐 𝐃𝐨𝐠̆𝐫𝐮𝐥𝐚𝐦𝐚: {𝐧𝐮𝐦𝟏} + {𝐧𝐮𝐦𝟐} = ?\𝐧𝐂𝐞𝐯𝐚𝐛ı 𝐲𝐚𝐳 (𝟓𝐝𝐤 𝐬𝐮̈𝐫𝐞𝐧 𝐯𝐚𝐫).",
        "captcha_success": "✅ 𝐃𝐨𝐠̆𝐫𝐮𝐥𝐚𝐦𝐚 𝐛𝐚𝐬̧𝐚𝐫ı𝐥ı! 𝐁𝐨𝐭𝐮 𝐤𝐮𝐥𝐥𝐚𝐧𝐚𝐛𝐢𝐥𝐢𝐫𝐬𝐢𝐧.",
        "captcha_failed": "❌ 𝐘𝐚𝐧𝐥ı𝐬̧ 𝐜𝐞𝐯𝐚𝐩! 𝐓𝐞𝐤𝐫𝐚𝐫 𝐝𝐞𝐧𝐞: /𝐬𝐭𝐚𝐫𝐭",
        "captcha_timeout": "⏳ 𝐃𝐨𝐠̆𝐫𝐮𝐥𝐚𝐦𝐚 𝐬𝐮̈𝐫𝐞𝐬𝐢 𝐝𝐨𝐥𝐝𝐮! 𝐓𝐞𝐤𝐫𝐚𝐫 𝐝𝐞𝐧𝐞: /start",
        "rate_limit": "🚫 𝐂̧𝐨𝐤 𝐟𝐚𝐳𝐥𝐚 𝐢𝐬𝐭𝐞𝐤! {𝐬𝐞𝐜𝐨𝐧𝐝𝐬}𝐬 𝐛𝐞𝐤𝐥𝐞.",
        "abuse_detected": "🚨 𝐊𝐨̈𝐭𝐮̈𝐲𝐞 𝐤𝐮𝐥𝐥𝐚𝐧ı𝐦 𝐭𝐞𝐬𝐩𝐢𝐭 𝐞𝐝𝐢𝐥𝐝𝐢! 𝐆𝐞𝐜̧𝐢𝐜𝐢 𝐞𝐧𝐠𝐞𝐥𝐥𝐞𝐧𝐝𝐢𝐧.",
        "fastcheck_usage": "📋 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐦: /𝐟𝐚𝐬𝐭𝐜𝐡𝐞𝐜𝐤 <𝐤𝐚𝐫𝐭_𝐧𝐨>|<𝐚𝐲>|<𝐲ı𝐥>|<𝐜𝐯𝐯> (𝐕𝐈𝐏)",
        "fastcheck_success": "✅ 𝐇ı𝐳𝐥ı 𝐤𝐨𝐧𝐭𝐫𝐨𝐥 𝐭𝐚𝐦𝐚𝐦𝐥𝐚𝐧𝐝ı!",
        "export_success": "📄 𝐊𝐨𝐧𝐭𝐫𝐨𝐥 𝐠𝐞𝐜̧𝐦𝐢𝐬̧𝐢 𝐂𝐒𝐕 𝐨𝐥𝐚𝐫𝐚𝐤 𝐠𝐨̈𝐧𝐝𝐞𝐫𝐢𝐥𝐝𝐢!",
        "feedback_usage": "📩 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐦: /𝐟𝐞𝐞𝐝𝐛𝐚𝐜𝐤 <𝐦𝐞𝐬𝐚𝐣>",
        "feedback_sent": "✅ 𝐆𝐞𝐫𝐢 𝐛𝐢𝐥𝐝𝐢𝐫𝐢𝐦𝐢𝐧 𝐠𝐨̈𝐧𝐝𝐞𝐫𝐢𝐥𝐝𝐢!",
        "feedback_received": "📩 𝐆𝐞𝐫𝐢 𝐁𝐢𝐥𝐝𝐢𝐫𝐢𝐦\𝐧👤 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı: {𝐮𝐬𝐞𝐫_𝐢𝐝}\𝐧💬 𝐌𝐞𝐬𝐚𝐣: {message}",
        "userstats": (
            "📊 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐀𝐧𝐚𝐥𝐢𝐳𝐢: {user_id}**\n"
            "📅 𝐊𝐚𝐭ı𝐥ı𝐦: {join_date}\n"
            "🔍 𝐊𝐨𝐧𝐭𝐫𝐨𝐥𝐥𝐞𝐫: {total_checks}\n"
            "👥 𝐃𝐚𝐯𝐞𝐭𝐥𝐞𝐫: {invited_count}\n"
            "📩 𝐑𝐚𝐩𝐨𝐫𝐥𝐚𝐫: {reports}\n"
            "🌟 𝐏𝐮𝐚𝐧: {points}"
        ),
        "monitor": (
            "📊 𝐒𝐢𝐬𝐭𝐞𝐦 𝐈̇𝐳𝐥𝐞𝐦𝐞\n"
            "💾 𝐑𝐀𝐌: {ram}MB\n"
            "🖥 𝐂𝐏𝐔: {cpu}%\n"
            "💽 𝐃𝐢𝐬𝐤: {disk}%"
        ),
        "restart_success": "🔄 Bot yeniden başlatılıyor...",
        "testcheck": "✅ Test kontrol: {result}",
        "simulateerror": "🚨 Simüle edilen hata: {error}",
        "apistatus": "🌐 **API Durumu**\n{status}"
    },
    "en": {}
}

user_cooldowns = {}
check_cooldowns = {}
rate_limits = {}
captcha_data = {}
BIN_DATA = {'default': {'type': 'Unknown', 'name': 'Unknown', 'country': 'Unknown'}}

def init_database():
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    language TEXT DEFAULT 'tr',
                    join_date TEXT,
                    total_checks INTEGER DEFAULT 0,
                    daily_checks INTEGER DEFAULT 0,
                    last_check_date TEXT,
                    last_daily TEXT,
                    vip_type TEXT DEFAULT 'none',
                    vip_expiry TEXT,
                    nickname TEXT DEFAULT '',
                    bio TEXT DEFAULT '',
                    check_history TEXT DEFAULT '[]',
                    credits INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    invited_by INTEGER,
                    invited_users TEXT DEFAULT '[]',
                    reports TEXT DEFAULT '[]'
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id INTEGER PRIMARY KEY,
                    reason TEXT,
                    ban_date TEXT
                )
            ''')
            conn.commit()
        logger.info("Veritabanı başlatıldı.")
    except Exception as e:
        logger.error(f"Veritabanı hatası: {str(e)}")

def load_user_data(user_id):
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = c.fetchone()
            if user:
                return {
                    "user_id": user[0],
                    "username": user[1],
                    "language": user[2],
                    "join_date": user[3],
                    "total_checks": user[4],
                    "daily_checks": user[5],
                    "last_check_date": user[6],
                    "last_daily": user[7],
                    "vip_type": user[8],
                    "vip_expiry": user[9],
                    "nickname": user[10],
                    "bio": user[11],
                    "check_history": json.loads(user[12]) if user[12] else [],
                    "credits": user[13],
                    "points": user[14],
                    "invited_by": user[15],
                    "invited_users": json.loads(user[16]) if user[16] else [],
                    "reports": json.loads(user[17]) if user[17] else []
                }
    except Exception as e:
        logger.error(f"Kullanıcı verisi yükleme hatası: {str(e)}")
    return None

def save_user_data(user_data):
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO users (
                    user_id, username, language, join_date, total_checks, daily_checks,
                    last_check_date, last_daily, vip_type, vip_expiry, nickname, bio,
                    check_history, credits, points, invited_by, invited_users, reports
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data["user_id"], user_data["username"], user_data["language"],
                user_data["join_date"], user_data["total_checks"], user_data["daily_checks"],
                user_data["last_check_date"], user_data["last_daily"], user_data["vip_type"],
                user_data["vip_expiry"], user_data["nickname"], user_data["bio"],
                json.dumps(user_data["check_history"]), user_data["credits"], user_data["points"],
                user_data["invited_by"], json.dumps(user_data["invited_users"]),
                json.dumps(user_data["reports"])
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Kullanıcı verisi kaydetme hatası: {str(e)}")

def get_banned_users():
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT user_id FROM banned_users')
            return set(row[0] for row in c.fetchall())
    except Exception as e:
        logger.error(f"Ban listesi yükleme hatası: {str(e)}")
        return set()

def is_gen_cvv(cvv: str) -> bool:
    try:
        cvv_num = int(cvv)
        return cvv_num in [0, 1]
    except ValueError:
        return False

def get_bin_info(card: str) -> dict:
    try:
        bin_number = card.split("|")[0][:6]
        return BIN_DATA.get(bin_number, BIN_DATA['default'])
    except (IndexError, AttributeError):
        logger.warning(f"Geçersiz kart formatı: {card}")
        return BIN_DATA['default']

def get_user_language(user_id: int) -> str:
    user = load_user_data(user_id)
    return user["language"] if user else "tr"

def is_vip_valid(user_id: int) -> bool:
    user = load_user_data(user_id)
    if not user:
        return False
    vip_type = user.get("vip_type", "none")
    vip_expiry = user.get("vip_expiry")
    if vip_type == "none":
        return False
    if vip_type == "unlimited":
        return True
    if vip_expiry:
        try:
            expiry_date = datetime.strptime(vip_expiry, "%Y-%m-%d")
            return datetime.now() <= expiry_date
        except ValueError:
            return False
    return False

def get_remaining_checks(user_id: int) -> int:
    user = load_user_data(user_id)
    if not user:
        return 0
    if is_vip_valid(user_id) or user_id == ADMIN_ID:
        return float("inf")
    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("last_check_date") != today:
        user["daily_checks"] = 0
        user["last_check_date"] = today
        save_user_data(user)
    return max(0, DAILY_CHECK_LIMIT - user.get("daily_checks", 0))

def deduct_check(user_id: int, amount: int):
    user = load_user_data(user_id)
    if not user:
        return
    if not is_vip_valid(user_id):
        user["daily_checks"] += amount
    user["total_checks"] += amount
    user["points"] += amount
    user["last_check_date"] = datetime.now().strftime("%Y-%m-%d")
    save_user_data(user)

async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> tuple[bool, str]:
    if user_id == ADMIN_ID:
        return True, ""
    failed_channels = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                failed_channels.append(channel)
        except Exception as e:
            failed_channels.append(channel)
            logger.warning(f"Kanal üyeliği kontrolü hatası: {str(e)}")
    return not failed_channels, ", ".join(failed_channels)

def add_user_to_list(user_id: int, username=None):
    user = load_user_data(user_id)
    if not user:
        user = {
            "user_id": user_id,
            "username": username,
            "language": "tr",
            "join_date": datetime.now().strftime("%Y-%m-%d"),
            "total_checks": 0,
            "daily_checks": 0,
            "last_check_date": None,
            "last_daily": None,
            "vip_type": "none",
            "vip_expiry": None,
            "nickname": "",
            "bio": "",
            "check_history": [],
            "credits": 0,
            "points": 0,
            "invited_by": None,
            "invited_users": [],
            "reports": []
        }
        save_user_data(user)
        logger.info(f"Yeni kullanıcı: {user_id}")

async def ban_user(user_id: int, reason: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO banned_users (user_id, reason, ban_date) VALUES (?, ?, ?)',
                      (user_id, reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        lang = get_user_language(user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=MESSAGES[lang]["banned_message"].format(reason=reason)
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚫 Kullanıcı Banlandı\nID: {user_id}\nSebep: {reason}"
        )
    except Exception as e:
        error_logger.error(f"Ban bildirimi hatası: {str(e)}")

async def report_critical_error(context, error, user_id, command):
    error_msg = (
        f"🚨 Kritik Hata\n"
        f"Kullanıcı: {user_id}\n"
        f"Komut: {command}\n"
        f"Hata: {str(error)}\n"
        f"Zaman: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    )
    error_logger.error(error_msg)
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=error_msg)
    except Exception as e:
        error_logger.error(f"Admin'e hata bildirimi hatası: {str(e)}")

def rate_limit_check(user_id: int) -> tuple[bool, int]:
    current_time = int(datetime.now().timestamp())
    if user_id not in rate_limits:
        rate_limits[user_id] = []
    rate_limits[user_id] = [t for t in rate_limits[user_id] if current_time - t < 60]
    if len(rate_limits[user_id]) >= RATE_LIMIT_PER_MINUTE:
        return False, 60 - (current_time - rate_limits[user_id][0])
    rate_limits[user_id].append(current_time)
    return True, 0

def abuse_check(user_id: int, command: str) -> bool:
    if user_id == ADMIN_ID:
        return False
    current_time = int(datetime.now().timestamp())
    if user_id not in user_cooldowns:
        user_cooldowns[user_id] = []
    user_cooldowns[user_id] = [t for t in user_cooldowns[user_id] if current_time - t < 10]
    if command == "/check" and len(user_cooldowns[user_id]) >= 20:
        return True
    user_cooldowns[user_id].append(current_time)
    return False

def ban_check(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        banned_users = get_banned_users()
        if user_id in banned_users:
            lang = get_user_language(user_id)
            await update.message.reply_text(MESSAGES[lang]["banned_message"].format(reason="Bilinmiyor"))
            return
        return await func(update, context)
    return wrapped

def channel_required(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = get_user_language(user_id)
        username = update.effective_user.username
        add_user_to_list(user_id, username)
        is_member, error_msg = await check_channel_membership(context, user_id)
        if not is_member:
            keyboard = [
                [InlineKeyboardButton(MESSAGES[lang][f"join_channel_{ch[1:]}"], url=f"https://t.me/{ch[1:]}")]
                for ch in REQUIRED_CHANNELS
            ] + [[InlineKeyboardButton(MESSAGES[lang]["check_membership"], callback_data="check_membership")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                MESSAGES[lang]["channel_error"] + f"\nHatalar: {error_msg}",
                reply_markup=reply_markup
            )
            return
        return await func(update, context)
    return wrapped

def restricted(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = get_user_language(user_id)
        if user_id != ADMIN_ID:
            await update.message.reply_text(MESSAGES[lang]["admin_only"])
            return
        return await func(update, context)
    return wrapped

def captcha_required(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = get_user_language(user_id)
        current_time = int(datetime.now().timestamp())
        if user_id not in captcha_data:
            num1, num2 = random.randint(1, 10), random.randint(1, 10)
            captcha_data[user_id] = {
                "answer": num1 + num2,
                "timestamp": current_time
            }
            await update.message.reply_text(
                MESSAGES[lang]["captcha_prompt"].format(num1=num1, num2=num2)
            )
            return
        if current_time - captcha_data[user_id]["timestamp"] > CAPTCHA_TIMEOUT:
            del captcha_data[user_id]
            await update.message.reply_text(MESSAGES[lang]["captcha_timeout"])
            return
        return await func(update, context)
    return wrapped

@channel_required
@ban_check
@captcha_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    lang = get_user_language(user_id)
    add_user_to_list(user_id, username)

    args = context.args
    inviter_id = None
    if args and args[0].startswith("ref_"):
        try:
            inviter_id = int(args[0].split("_")[1])
        except (IndexError, ValueError):
            inviter_id = None

    if inviter_id and inviter_id != user_id:
        user = load_user_data(user_id)
        inviter = load_user_data(inviter_id)
        if inviter and user_id not in inviter["invited_users"]:
            user["credits"] += 5
            user["invited_by"] = inviter_id
            inviter["credits"] += 5
            inviter["invited_users"].append(user_id)
            if len(inviter["invited_users"]) % 5 == 0:
                inviter["vip_type"] = "daily"
                inviter["vip_expiry"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                await context.bot.send_message(
                    chat_id=inviter_id,
                    text=MESSAGES[lang]["invite_bonus"]
                )
            save_user_data(user)
            save_user_data(inviter)
            await update.message.reply_text(
                MESSAGES[lang]["invite_credited"].format(
                    username=inviter["username"] or f"User{inviter_id}",
                    credits=user["credits"]
                )
            )
            await context.bot.send_message(
                chat_id=inviter_id,
                text=MESSAGES[lang]["inviter_credited"].format(
                    invited_username=username or f"User{user_id}",
                    credits=inviter["credits"]
                )
            )
        else:
            await update.message.reply_text(MESSAGES[lang]["already_invited"])

    await update.message.reply_text(MESSAGES[lang]["welcome"])

@channel_required
@ban_check
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]["language_tr"], callback_data="lang_tr")],
        [InlineKeyboardButton(MESSAGES[lang]["language_en"], callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        MESSAGES[lang]["language_select"].format(lang="Türkçe" if lang == "tr" else "English"),
        reply_markup=reply_markup
    )

@channel_required
@ban_check
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    current_time = int(datetime.now().timestamp())

    allowed, wait_time = rate_limit_check(user_id)
    if not allowed:
        await update.message.reply_text(MESSAGES[lang]["rate_limit"].format(seconds=wait_time))
        return

    if abuse_check(user_id, "/check"):
        await ban_user(user_id, "Kötüye kullanım", context)
        await update.message.reply_text(MESSAGES[lang]["abuse_detected"])
        return

    cooldown = CHECK_COOLDOWN_NORMAL if not (is_vip_valid(user_id) or user_id == ADMIN_ID) else CHECK_COOLDOWN_VIP
    if user_id in check_cooldowns and current_time < check_cooldowns[user_id]:
        await update.message.reply_text(MESSAGES[lang]["check_cooldown_msg"].format(
            seconds=check_cooldowns[user_id] - current_time))
        return

    remaining_checks = get_remaining_checks(user_id)
    if remaining_checks <= 0:
        await update.message.reply_text(MESSAGES[lang]["no_checks_left"], parse_mode="HTML")
        return

    try:
        args = context.args
        if not args or len(args) < 1:
            await update.message.reply_text(MESSAGES[lang]["card_missing"])
            return
        card = args[0].strip()
        if card.count("|") != 3:
            await update.message.reply_text(MESSAGES[lang]["invalid_format"])
            return
        card_parts = card.split("|")
        if len(card_parts) != 4 or not all(card_parts):
            await update.message.reply_text(MESSAGES[lang]["invalid_format"])
            return
        if is_gen_cvv(card_parts[3]):
            await ban_user(user_id, "CVV 000/001 kullanımı", context)
            return
        logger.info(f"Kullanıcı {user_id} kart kontrolü: {card}")

        async with aiohttp.ClientSession() as session:
            await process_single_check(update, context, card, lang, user_id, session)
        deduct_check(user_id, 1)
        check_cooldowns[user_id] = current_time + cooldown
    except Exception as e:
        await report_critical_error(context, e, user_id, "/check")
        await update.message.reply_text(MESSAGES[lang]["general_error"].format(error=str(e)))

async def process_single_check(update, context, card, lang, user_id, session):
    status_message = await update.message.reply_text(
        MESSAGES[lang]["checking"].format(card=card, current=1, total=1)
    )
    try:
        result = "declined"
        async with session.get(CHECK_API.format(card), timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                result = "live" if data.get("message") == "Abonelik Başarılı" else "declined"
            else:
                raise Exception(f"API hata kodu: {response.status}")
        bin_info = get_bin_info(card)
        duration = 0.5
        vip_status = "VIP" if is_vip_valid(user_id) else "Normal"
        if user_id == ADMIN_ID:
            vip_status = "Admin"
        status = (MESSAGES[lang]["live"] if result == "live" else MESSAGES[lang]["declined"]).format(
            card=card,
            card_type=bin_info['type'],
            bank_name=bin_info['name'],
            country=bin_info['country'],
            time=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            duration=duration,
            vip_status=vip_status
        )
        if result == "live":
            with open(LIVE_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(card + "\n")
        keyboard = [
            [InlineKeyboardButton(MESSAGES[lang]["check_again"], callback_data="check_again")],
            [InlineKeyboardButton(MESSAGES[lang]["quick_actions"], callback_data="quick_actions")]
        ]
        await status_message.edit_text(status, reply_markup=InlineKeyboardMarkup(keyboard))

        user = load_user_data(user_id)
        if not user:
            raise Exception("Kullanıcı verisi yüklenemedi")
        user["check_history"] = [{"card": card, "result": result}] + user["check_history"][:49]
        save_user_data(user)
    except Exception as e:
        await report_critical_error(context, e, user_id, "process_single_check")
        await status_message.edit_text(MESSAGES[lang]["general_error"].format(error=str(e)))
        logger.error(f"process_single_check hatası: {str(e)}")

@channel_required
@ban_check
async def masscheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    current_time = int(datetime.now().timestamp())

    allowed, wait_time = rate_limit_check(user_id)
    if not allowed:
        await update.message.reply_text(MESSAGES[lang]["rate_limit"].format(seconds=wait_time))
        return

    text = update.message.text
    cards_input = text[len("/masscheck"):].strip()
    cards = [card.strip() for card in cards_input.split("\n") if card.strip()]

    if cards and any(card.count("|") == 3 for card in cards):
        if any(is_gen_cvv(card.split("|")[3]) for card in cards if card.count("|") == 3):
            await ban_user(user_id, "CVV 000/001 kullanımı", context)
            return
        required_checks = len([card for card in cards if card.count("|") == 3])
        if required_checks > get_remaining_checks(user_id):
            await update.message.reply_text(MESSAGES[lang]["no_checks_left"], parse_mode="HTML")
            return
        async with aiohttp.ClientSession() as session:
            await process_mass_check(update, context, cards, lang, user_id, session)
        deduct_check(user_id, required_checks)
        user = load_user_data(user_id)
        user["check_history"] = [{"card": c, "result": "pending"} for c in cards[:5]] + user["check_history"][:45]
        save_user_data(user)
        cooldown = CHECK_COOLDOWN_NORMAL if not (is_vip_valid(user_id) or user_id == ADMIN_ID) else CHECK_COOLDOWN_VIP
        check_cooldowns[user_id] = current_time + (cooldown * required_checks)
    else:
        await update.message.reply_text(MESSAGES[lang]["masscheck_prompt"])
        context.user_data["awaiting_masscheck"] = True

async def process_mass_check(update, context, cards, lang, user_id, session):
    if len(cards) > 25:
        await update.message.reply_text(MESSAGES[lang]["masscheck_limit"].format(count=len(cards)))
        return
    if not cards:
        await update.message.reply_text(MESSAGES[lang]["card_missing"])
        return
    status_message = await update.message.reply_text(
        MESSAGES[lang]["masscheck_start"].format(count=len(cards))
    )
    results = []
    live_cards = []
    cooldown = CHECK_COOLDOWN_NORMAL if not (is_vip_valid(user_id) or user_id == ADMIN_ID) else CHECK_COOLDOWN_VIP
    for index, card in enumerate(cards, 1):
        if card.count("|") != 3:
            continue
        try:
            async with session.get(CHECK_API.format(card), timeout=30) as response:
                result = "declined"
                if response.status == 200:
                    data = await response.json()
                    result = "live" if data.get("message") == "Abonelik Başarılı" else "declined"
                else:
                    raise Exception(f"API hata kodu: {response.status}")
            bin_info = get_bin_info(card)
            vip_status = "VIP" if is_vip_valid(user_id) else "Normal"
            if user_id == ADMIN_ID:
                vip_status = "Admin"
            status = (MESSAGES[lang]["live"] if result == "live" else MESSAGES[lang]["declined"]).format(
                card=card,
                card_type=bin_info['type'],
                bank_name=bin_info['name'],
                country=bin_info['country'],
                time=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                duration=0.5,
                vip_status=vip_status
            )
            if result == "live":
                live_cards.append(card)
            results.append(status)
            user = load_user_data(user_id)
            user["check_history"] = [{"card": card, "result": result}] + user["check_history"][:49]
            save_user_data(user)
            await status_message.edit_text(
                MESSAGES[lang]["checking"].format(card=card, current=index, total=len(cards))
            )
            if cooldown > 0:
                await asyncio.sleep(cooldown)
        except Exception as e:
            await report_critical_error(context, e, user_id, "process_mass_check")
            results.append(MESSAGES[lang]["general_error"].format(error=str(e)))
            logger.error(f"process_mass_check hatası: {str(e)}")

    with open("sonuclar.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    await context.bot.send_document(chat_id=user_id, document=open("sonuclar.txt", "rb"))
    if live_cards:
        with open(LIVE_FILE_PATH, "a", encoding="utf-8") as f:
            f.write("\n".join(live_cards) + "\n")
    await status_message.edit_text(MESSAGES[lang]["masscheck_done"])

async def handle_masscheck_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not context.user_data.get("awaiting_masscheck"):
        return
    context.user_data["awaiting_masscheck"] = False
    cards_input = update.message.text.strip()
    cards = [card.strip() for card in cards_input.split("\n") if card.strip()]
    if any(is_gen_cvv(card.split("|")[3]) for card in cards if card.count("|") == 3):
        await ban_user(user_id, "CVV 000/001 kullanımı", context)
        return
    required_checks = len([card for card in cards if card.count("|") == 3])
    if required_checks > get_remaining_checks(user_id):
        await update.message.reply_text(MESSAGES[lang]["no_checks_left"], parse_mode="HTML")
        return
    async with aiohttp.ClientSession() as session:
        await process_mass_check(update, context, cards, lang, user_id, session)
    deduct_check(user_id, required_checks)
    user = load_user_data(user_id)
    user["check_history"] = [{"card": c, "result": "pending"} for c in cards[:5]] + user["check_history"][:45]
    save_user_data(user)

@channel_required
@ban_check
async def user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    vip_status = user["vip_type"].title() if is_vip_valid(user_id) else "Normal"
    join_date = datetime.strptime(user["join_date"], "%Y-%m-%d")
    days = (datetime.now() - join_date).days
    await update.message.reply_text(
        MESSAGES[lang]["user_info"].format(
            vip_status=vip_status,
            days=days,
            total_checks=user["total_checks"],
            remaining_checks="Sınırsız" if is_vip_valid(user_id) else get_remaining_checks(user_id),
            credits=user["credits"],
            points=user["points"]
        )
    )

@channel_required
@ban_check
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    vip_status = user["vip_type"].title() if is_vip_valid(user_id) else "Normal"
    vip_expiry = user["vip_expiry"] or "Yok"
    if user["vip_type"] == "unlimited":
        vip_expiry = "Sınırsız"
    await update.message.reply_text(
        MESSAGES[lang]["vip_status"].format(
            vip_status=vip_status,
            vip_expiry=vip_expiry,
            remaining_checks="Sınırsız" if is_vip_valid(user_id) else get_remaining_checks(user_id),
            credits=user["credits"],
            points=user["points"]
        )
    )

@channel_required
@restricted
async def setvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if len(context.args) < 3:
        await update.message.reply_text(MESSAGES[lang]["setvip_usage"])
        return
    try:
        target = context.args[0]
        duration = int(context.args[1])
        unit = context.args[2].lower()
        if duration <= 0:
            await update.message.reply_text("❌ Süre pozitif olmalı!")
            return
        if unit not in ["günlük", "haftalık", "aylık", "yıllık", "sınırsız"]:
            await update.message.reply_text(MESSAGES[lang]["setvip_usage"])
            return
        if target.startswith("@"):
            target_id = (await context.bot.get_chat(target)).id
        else:
            target_id = int(target)
        user = load_user_data(target_id)
        if not user:
            await update.message.reply_text("❌ Kullanıcı bulunamadı!")
            return
        vip_type_map = {
            "𝐠𝐮̈𝐧𝐥𝐮̈𝐤": "daily",
            "𝐡𝐚𝐟𝐭𝐚𝐥ı𝐤": "weekly",
            "𝐚𝐲𝐥ı𝐤": "monthly",
            "𝐲ı𝐥𝐥ı𝐤": "yearly",
            "𝐬ı𝐧ı𝐫𝐬ı𝐳": "unlimited"
        }
        durations = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365, "unlimited": None}
        vip_type = vip_type_map[unit]
        user["vip_type"] = vip_type
        if vip_type != "unlimited":
            user["vip_expiry"] = (datetime.now() + timedelta(days=durations[vip_type] * duration)).strftime("%Y-%m-%d")
        else:
            user["vip_expiry"] = None
        save_user_data(user)
        expiry = "Sınırsız" if vip_type == "unlimited" else user["vip_expiry"]
        await update.message.reply_text(
            MESSAGES[lang]["setvip_success"].format(
                user_id=target_id,
                vip_type=f"{duration} {unit.title()}",
                expiry=expiry
            )
        )
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎉 VIP güncellendi: {duration} {unit.title()}, Bitiş: {expiry}"
        )
    except Exception as e:
        await report_critical_error(context, e, user_id, "/setvip")
        await update.message.reply_text(MESSAGES[lang]["general_error"].format(error=str(e)))

@channel_required
@restricted
async def setvipbulk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if len(context.args) < 3:
        await update.message.reply_text(MESSAGES[lang]["setvipbulk_usage"])
        return
    try:
        target_ids = context.args[0].split(",")
        duration = int(context.args[1])
        unit = context.args[2].lower()
        if duration <= 0:
            await update.message.reply_text("❌ 𝐒𝐮̈𝐫𝐞 𝐩𝐨𝐳𝐢𝐭𝐢𝐟 𝐨𝐥𝐦𝐚𝐥ı!")
            return
        if unit not in ["günlük", "haftalık", "aylık", "yıllık", "sınırsız"]:
            await update.message.reply_text(MESSAGES[lang]["setvipbulk_usage"])
            return
        vip_type_map = {
            "𝐠𝐮̈𝐧𝐥𝐮̈𝐤": "daily",
            "𝐡𝐚𝐟𝐭𝐚𝐥ı𝐤": "weekly",
            "𝐚𝐲𝐥ı𝐤": "monthly",
            "𝐲ı𝐥𝐥ı𝐤": "yearly",
            "𝐬ı𝐧ı𝐫𝐬ı𝐳": "unlimited"
        }
        durations = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365, "unlimited": None}
        vip_type = vip_type_map[unit]
        count = 0
        for target in target_ids:
            try:
                if target.startswith("@"):
                    target_id = (await context.bot.get_chat(target)).id
                else:
                    target_id = int(target)
                user = load_user_data(target_id)
                if user:
                    user["vip_type"] = vip_type
                    if vip_type != "unlimited":
                        user["vip_expiry"] = (datetime.now() + timedelta(days=durations[vip_type] * duration)).strftime("%Y-%m-%d")
                    else:
                        user["vip_expiry"] = None
                    save_user_data(user)
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"🎉 VIP güncellendi: {duration} {unit.title()}"
                    )
                    count += 1
            except:
                continue
        await update.message.reply_text(MESSAGES[lang]["setvipbulk_success"].format(count=count))
    except Exception as e:
        await report_critical_error(context, e, user_id, "/setvipbulk")
        await update.message.reply_text(MESSAGES[lang]["general_error"].format(error=str(e)))

@channel_required
@ban_check
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT user_id, username, nickname, points FROM users ORDER BY points DESC LIMIT 10')
            users = c.fetchall()
        if not users:
            await update.message.reply_text(MESSAGES[lang]["no_users"])
            return
        leaderboard = [
            f"{i+1}. {row[2] or row[1] or f'User{row[0]}'} - {row[3]} puan"
            for i, row in enumerate(users)
        ]
        await update.message.reply_text(MESSAGES[lang]["leaderboard"].format(leaderboard="\n".join(leaderboard)))
    except Exception as e:
        logger.error(f"Lider tablosu hatası: {str(e)}")

@channel_required
@ban_check
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    if user["last_daily"] == today:
        await update.message.reply_text(MESSAGES[lang]["daily_cooldown"])
        return
    user["daily_checks"] = 0
    user["last_daily"] = today
    save_user_data(user)
    await update.message.reply_text(MESSAGES[lang]["daily_bonus"].format(checks=get_remaining_checks(user_id)))

@channel_required
@ban_check
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not context.args:
        await update.message.reply_text(MESSAGES[lang]["report_usage"])
        return
    message = " ".join(context.args)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    user["reports"].append({"message": message, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    save_user_data(user)
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=MESSAGES[lang]["report_received"].format(user_id=user_id, message=message)
    )
    await update.message.reply_text(MESSAGES[lang]["report_sent"])

@channel_required
@ban_check
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*), SUM(total_checks), COUNT(*), SUM(credits), SUM(points) FROM users')
            stats = c.fetchone()
            user_count, total_checks, _, total_credits, total_points = stats
            c.execute('SELECT COUNT(*) FROM users WHERE vip_type != "none" AND (vip_expiry IS NULL OR vip_expiry > ?)',
                      (datetime.now().strftime("%Y-%m-%d"),))
            vip_count = c.fetchone()[0]
        await update.message.reply_text(
            MESSAGES[lang]["stats"].format(
                user_count=user_count,
                total_checks=total_checks or 0,
                vip_count=vip_count,
                total_credits=total_credits or 0,
                total_points=total_points or 0
            )
        )
    except Exception as e:
        logger.error(f"𝐈̇𝐬𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐤 𝐡𝐚𝐭𝐚𝐬ı: {str(e)}")

@channel_required
@restricted
async def duyuru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = update.message.text[len("/duyuru"):].strip()
    if not text:
        await update.message.reply_text("📋 Kullanım: /duyuru <mesaj>")
        return
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT user_id FROM users')
            users = c.fetchall()
        sent_count = 0
        for (uid,) in users:
            if uid == user_id or uid in get_banned_users():
                continue
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent_count += 1
                await asyncio.sleep(0.1)
            except:
                continue
        await update.message.reply_text(f"✅ Duyuru gönderildi: {sent_count} kullanıcı")
    except Exception as e:
        error_logger.error(f"Duyuru hatası: {str(e)}")

@channel_required
@ban_check
async def fiyatlistesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(MESSAGES[lang]["price_list"], parse_mode="HTML")

@channel_required
@restricted
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if len(context.args) != 1:
        await update.message.reply_text("📋 Kullanım: /unban [ID]")
        return
    try:
        target_id = int(context.args[0])
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM banned_users WHERE user_id = ?', (target_id,))
            conn.commit()
        await update.message.reply_text(f"✅ Kullanıcı {target_id} banı kaldırıldı.")
        await context.bot.send_message(
            chat_id=target_id,
            text="🎉 Banın kaldırıldı! Botu kullanabilirsin."
        )
    except Exception as e:
        error_logger.error(f"Unban hatası: {str(e)}")

@channel_required
@restricted
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if len(context.args) != 1:
        await update.message.reply_text("📋 Kullanım: /ban [ID veya @username]")
        return
    try:
        target = context.args[0]
        if target.startswith("@"):
            target_id = (await context.bot.get_chat(target)).id
        else:
            target_id = int(target)
        if target_id == ADMIN_ID:
            await update.message.reply_text("❌ Admin banlanamaz!")
            return
        await ban_user(target_id, "Admin tarafından ban", context)
        await update.message.reply_text(f"✅ Kullanıcı {target_id} banlandı.")
    except Exception as e:
        error_logger.error(f"Ban hatası: {str(e)}")

@channel_required
@restricted
async def debug_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    for channel in REQUIRED_CHANNELS:
        try:
            chat = await context.bot.get_chat(channel)
            bot_member = await context.bot.get_chat_member(chat_id=channel, user_id=context.bot.id)
            await update.message.reply_text(
                f"📢 Kanal: {channel}\n"
                f"ID: {chat.id}\n"
                f"Link: {channel[1:]}\n"
                f"Durum: {bot_member.status}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Kanal {channel} hata: {str(e)}")

@channel_required
@ban_check
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            MESSAGES[lang]["profile_view"].format(
                nickname=user["nickname"] or "Yok",
                bio=user["bio"] or "Yok",
                vip_status=user["vip_type"].title() if is_vip_valid(user_id) else "Normal",
                points=user["points"]
            )
        )
    else:
        text = " ".join(args)
        nickname = text
        bio = ""
        if "bio:" in text.lower():
            nickname, bio = text.split("bio:", 1)
            nickname = nickname.strip()
            bio = bio.strip()
        user["nickname"] = nickname
        user["bio"] = bio
        save_user_data(user)
        await update.message.reply_text(
            MESSAGES[lang]["profile_set"].format(
                nickname=nickname or "Yok",
                bio=bio or "Yok"
            )
        )

@channel_required
@ban_check
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    filter_type = context.args[0].lower() if context.args else None
    history = user["check_history"]
    if not history:
        await update.message.reply_text(MESSAGES[lang]["history_empty"])
        return
    if filter_type in ["live", "declined"]:
        filtered = [h for h in history if h.get("result") == filter_type]
        if not filtered:
            await update.message.reply_text(f"❌ {filter_type.title()} kart bulunamadı!")
            return
        history_text = "\n".join([f"{h['card']} ({h['result']})" for h in filtered])
        await update.message.reply_text(
            MESSAGES[lang]["history_filter"].format(
                filter=filter_type.title(),
                history=history_text
            )
        )
    else:
        history_text = "\n".join([f"{h['card']} ({h['result']})" for h in history])
        await update.message.reply_text(
            MESSAGES[lang]["history_view"].format(history=history_text)
        )

@channel_required
@ban_check
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    invite_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    await update.message.reply_text(
        MESSAGES[lang]["invite_link"].format(
            link=invite_link,
            credits=user["credits"]
        )
    )

@channel_required
@ban_check
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton("📚 𝐓𝐞𝐦𝐞𝐥 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫", callback_data="help_basic")],
        [InlineKeyboardButton("🏆 𝐕𝐈𝐏 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫ı", callback_data="help_vip")],
        [InlineKeyboardButton("🔧 𝐀𝐝𝐦𝐢𝐧 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫ı", callback_data="help_admin")] if user_id == ADMIN_ID else []
    ]
    keyboard = [row for row in keyboard if row]
    await update.message.reply_text(
        "🤖 𝐁𝐨𝐭 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫ı 🤖\n"
        "Kategori seç:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@channel_required
@ban_check
async def fastcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not is_vip_valid(user_id) and user_id != ADMIN_ID:
        await update.message.reply_text("❌ 𝐁𝐮 𝐤𝐨𝐦𝐮𝐭 𝐬𝐚𝐝𝐞𝐜𝐞 𝐕𝐈𝐏 𝐢𝐜̧𝐢𝐧!")
        return
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text(MESSAGES[lang]["fastcheck_usage"])
        return
    card = args[0].strip()
    if card.count("|") != 3:
        await update.message.reply_text(MESSAGES[lang]["invalid_format"])
        return
    await update.message.reply_text(MESSAGES[lang]["fastcheck_success"])

@channel_required
@ban_check
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not is_vip_valid(user_id) and user_id != ADMIN_ID:
        await update.message.reply_text("❌ 𝐁𝐮 𝐤𝐨𝐦𝐮𝐭 𝐬𝐚𝐝𝐞𝐜𝐞 𝐕𝐈𝐏 𝐢𝐜̧𝐢𝐧!")
        return
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    with open("export.csv", "w", encoding="utf-8") as f:
        f.write("Kart,Durum\n")
        for h in user["check_history"]:
            f.write(f"{h['card']},{h['result']}\n")
    await context.bot.send_document(chat_id=user_id, document=open("export.csv", "rb"))
    await update.message.reply_text(MESSAGES[lang]["export_success"])

@channel_required
@ban_check
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not context.args:
        await update.message.reply_text(MESSAGES[lang]["feedback_usage"])
        return
    message = " ".join(context.args)
    user = load_user_data(user_id)
    if not user:
        await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐯𝐞𝐫𝐢𝐬𝐢 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
        return
    user["reports"].append({"message": message, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    save_user_data(user)
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=MESSAGES[lang]["feedback_received"].format(user_id=user_id, message=message)
    )
    await update.message.reply_text(MESSAGES[lang]["feedback_sent"])

@channel_required
@restricted
async def userstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if len(context.args) != 1:
        await update.message.reply_text("📋 Kullanım: /userstats [ID]")
        return
    try:
        target_id = int(context.args[0])
        user = load_user_data(target_id)
        if not user:
            await update.message.reply_text("❌ 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐛𝐮𝐥𝐮𝐧𝐚𝐦𝐚𝐝ı!")
            return
        await update.message.reply_text(
            MESSAGES[lang]["userstats"].format(
                user_id=target_id,
                join_date=user["join_date"],
                total_checks=user["total_checks"],
                invited_count=len(user["invited_users"]),
                reports=len(user["reports"]),
                points=user["points"]
            )
        )
    except Exception as e:
        await report_critical_error(context, e, user_id, "/userstats")
        await update.message.reply_text(MESSAGES[lang]["general_error"].format(error=str(e)))

@channel_required
@restricted
async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    memory = psutil.Process().memory_info().rss / 1024 / 1024
    cpu = psutil.cpu_percent()
    disk = psutil.disk_usage('/').percent
    await update.message.reply_text(
        MESSAGES[lang]["monitor"].format(ram=memory, cpu=cpu, disk=disk)
    )

@channel_required
@restricted
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(MESSAGES[lang]["restart_success"])
    await context.application.shutdown()
    os.execv(sys.executable, ['python'] + sys.argv)

@channel_required
@ban_check
async def testcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    result = random.choice(["live", "declined"])
    await update.message.reply_text(MESSAGES[lang]["testcheck"].format(result=result))

@channel_required
@restricted
async def simulateerror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    error = "Simüle edilen hata"
    await report_critical_error(context, error, user_id, "/simulateerror")
    await update.message.reply_text(MESSAGES[lang]["simulateerror"].format(error=error))

@channel_required
async def apistatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(CHECK_API.format("test"), timeout=5) as response:
                status = "🟢 Çalışıyor" if response.status == 200 else "🔴 Çalışmıyor"
        except:
            status = "🔴 Çalışmıyor"
    await update.message.reply_text(MESSAGES[lang]["apistatus"].format(status=status))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = get_user_language(user_id)
    if query.data == "check_membership":
        is_member, error_msg = await check_channel_membership(context, user_id)
        if is_member:
            await query.message.edit_text(MESSAGES[lang]["channel_success"])
            await language(update, context)
        else:
            keyboard = [
                [InlineKeyboardButton(MESSAGES[lang][f"join_channel_{ch[1:]}"], url=f"https://t.me/{ch[1:]}")]
                for ch in REQUIRED_CHANNELS
            ] + [[InlineKeyboardButton(MESSAGES[lang]["check_membership"], callback_data="check_membership")]]
            await query.message.edit_text(
                MESSAGES[lang]["channel_error"] + f"\nHatalar: {error_msg}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif query.data.startswith("lang_"):
        new_lang = query.data.split("_")[1]
        user = load_user_data(user_id)
        if user:
            user["language"] = new_lang
            save_user_data(user)
            await query.message.edit_text(MESSAGES[new_lang]["language_changed"].format(
                lang="Türkçe" if new_lang == "tr" else "English"))
    elif query.data == "check_again":
        await query.message.edit_text(MESSAGES[lang]["new_card"])
    elif query.data == "quick_actions":
        keyboard = [
            [InlineKeyboardButton("🔍 𝐘𝐞𝐧𝐢 𝐊𝐨𝐧𝐭𝐫𝐨𝐥", callback_data="check_again")],
            [InlineKeyboardButton("📋 𝐓𝐨𝐩𝐥𝐮 𝐊𝐨𝐧𝐭𝐫𝐨𝐥", callback_data="masscheck")],
            [InlineKeyboardButton("🏆 𝐕𝐈𝐏 𝐃𝐮𝐫𝐮𝐦𝐮", callback_data="vip")],
            [InlineKeyboardButton("📩 𝐃𝐚𝐯𝐞𝐭 𝐄𝐭", callback_data="invite")]
        ]
        await query.message.edit_text(
            MESSAGES[lang]["quick_actions"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "masscheck":
        context.user_data["awaiting_masscheck"] = True
        await query.message.edit_text(MESSAGES[lang]["masscheck_prompt"])
    elif query.data == "vip":
        await vip(update, context)
    elif query.data == "invite":
        await invite(update, context)
    elif query.data.startswith("help_"):
        category = query.data.split("_")[1]
        help_texts = {
            "basic": (
                "📚 𝐓𝐞𝐦𝐞𝐥 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫\n"
                "/start - 𝐁𝐨𝐭𝐮 𝐛𝐚𝐬̧𝐥𝐚𝐭\n"
                "/check - 𝐓𝐞𝐤 𝐤𝐚𝐫𝐭 𝐤𝐨𝐧𝐭𝐫𝐨𝐥\n"
                "/masscheck - 𝐓𝐨𝐩𝐥𝐮 𝐤𝐨𝐧𝐭𝐫𝐨𝐥\n"
                "/language - 𝐃𝐢𝐥 𝐬𝐞𝐜̧\n"
                "/help - 𝐘𝐚𝐫𝐝ı𝐦 𝐦𝐞𝐧𝐮̈𝐬𝐮̈\n"
                "/invite - 𝐃𝐚𝐯𝐞𝐭 𝐥𝐢𝐧𝐤𝐢\n"
            ),
            "vip": (
                "🏆 𝐕𝐈𝐏 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫ı\n"
                "/fastcheck - 𝐇ı𝐳𝐥ı 𝐤𝐨𝐧𝐭𝐫𝐨𝐥\n"
                "/export - 𝐆𝐞𝐜̧𝐦𝐢𝐬̧𝐢 𝐝ı𝐬̧𝐚 𝐚𝐤𝐭𝐚𝐫\n"
                "/vip - 𝐕𝐈𝐏 𝐝𝐮𝐫𝐮𝐦𝐮𝐧𝐮 𝐠𝐨̈𝐫\n"
            ),
            "admin": (
                "🔧 𝐀𝐝𝐦𝐢𝐧 𝐊𝐨𝐦𝐮𝐭𝐥𝐚𝐫ı\n"
                "/setvip - 𝐕𝐈𝐏 𝐚𝐭𝐚\n"
                "/setvipbulk - 𝐓𝐨𝐩𝐥𝐮 𝐕𝐈𝐏\n"
                "/duyuru - 𝐃𝐮𝐲𝐮𝐫𝐮 𝐠𝐨̈𝐧𝐝𝐞𝐫\n"
                "/ban - 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐛𝐚𝐧𝐥𝐚\n"
                "/unban - 𝐁𝐚𝐧 𝐤𝐚𝐥𝐝ı𝐫\n"
                "/userstats - 𝐊𝐮𝐥𝐥𝐚𝐧ı𝐜ı 𝐚𝐧𝐚𝐥𝐢𝐳𝐢\n"
                "/monitor - 𝐒𝐢𝐬𝐭𝐞𝐦 𝐢𝐳𝐥𝐞𝐦𝐞\n"
                "/restart - 𝐁𝐨𝐭𝐮 𝐲𝐞𝐧𝐢𝐝𝐞𝐧 𝐛𝐚𝐬̧𝐥𝐚𝐭\n"
            )
        }
        await query.message.edit_text(
            help_texts[category],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Geri", callback_data="help_back")]
            ])
        )
    elif query.data == "help_back":
        await help(update, context)

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if user_id not in captcha_data:
        return
    try:
        answer = int(update.message.text.strip())
        if answer == captcha_data[user_id]["answer"]:
            del captcha_data[user_id]
            await update.message.reply_text(MESSAGES[lang]["captcha_success"])
            await start(update, context)
        else:
            await update.message.reply_text(MESSAGES[lang]["captcha_failed"])
    except ValueError:
        await update.message.reply_text(MESSAGES[lang]["captcha_failed"])

async def main():
    init_database()
    logger.info("Bot başlatılıyor...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("masscheck", masscheck))
    application.add_handler(CommandHandler("language", language))
    application.add_handler(CommandHandler("user", user))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("daily", daily))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("duyuru", duyuru))
    application.add_handler(CommandHandler("fiyatlistesi", fiyatlistesi))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("debug_channel", debug_channel))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("vip", vip))
    application.add_handler(CommandHandler("setvip", setvip))
    application.add_handler(CommandHandler("setvipbulk", setvipbulk))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("fastcheck", fastcheck))
    application.add_handler(CommandHandler("export", export))
    application.add_handler(CommandHandler("feedback", feedback))
    application.add_handler(CommandHandler("userstats", userstats))
    application.add_handler(CommandHandler("monitor", monitor))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("testcheck", testcheck))
    application.add_handler(CommandHandler("simulateerror", simulateerror))
    application.add_handler(CommandHandler("apistatus", apistatus))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_masscheck_input
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^\d+$') & filters.ChatType.PRIVATE,
        handle_captcha
    ))
    application.add_handler(CallbackQueryHandler(button))

    commands = [
        BotCommand("start", "Botu başlat"),
        BotCommand("check", "Tek kart kontrol"),
        BotCommand("masscheck", "Toplu kontrol"),
        BotCommand("language", "Dil seç"),
        BotCommand("user", "Kullanıcı bilgileri"),
        BotCommand("leaderboard", "Lider tablosu"),
        BotCommand("daily", "Günlük bonus"),
        BotCommand("report", "Sorun bildir"),
        BotCommand("stats", "Bot istatistikleri"),
        BotCommand("fiyatlistesi", "VIP fiyatları"),
        BotCommand("profile", "Profil ayarla/gör"),
        BotCommand("history", "Kontrol geçmişi"),
        BotCommand("vip", "VIP durumu"),
        BotCommand("invite", "Davet linki"),
        BotCommand("help", "Yardım menüsü"),
        BotCommand("fastcheck", "Hızlı kontrol (VIP)"),
        BotCommand("export", "Geçmişi dışa aktar (VIP)"),
        BotCommand("feedback", "Geri bildirim gönder"),
        BotCommand("apistatus", "API durumu"),
    ]
    if ADMIN_ID:
        commands.extend([
            BotCommand("duyuru", "Duyuru gönder"),
            BotCommand("unban", "Ban kaldır"),
            BotCommand("ban", "Kullanıcı banla"),
            BotCommand("debug_channel", "Kanal debug"),
            BotCommand("setvip", "VIP ata"),
            BotCommand("setvipbulk", "Toplu VIP ata"),
            BotCommand("userstats", "Kullanıcı analizi"),
            BotCommand("monitor", "Sistem izleme"),
            BotCommand("restart", "Botu yeniden başlat"),
            BotCommand("simulateerror", "Hata simüle et")
        ])
    await application.bot.set_my_commands(commands)
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())