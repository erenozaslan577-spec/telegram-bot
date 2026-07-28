import logging
import json
import os
import time
import random
import html
import threading
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# --- LOGGING YAPILANDIRMASI ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- KONFİGÜRASYON ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8674816242:AAEPviDpFQxP2dCWGzB0BGg6ZAcNqQI8YT0")
ADMIN_USERNAME = "@kralinarest"
ADMIN_ID = 8674816242
BOT_USERNAME = "ChiwasIslemBot"
REQUIRED_CHANNEL = "@ChiwasDuyuru"  # Zorunlu duyuru kanalı

DATA_FILE = "users_data.json"
COUPONS_FILE = "coupons_data.json"
ORDERS_FILE = "orders_data.json"
BANNED_FILE = "banned_users.json"
REFERRAL_REWARD = 40

db_lock = threading.Lock()
rate_limit_store = {}  # Anti-spam deposu

# Conversation States
WAITING_TARGET_INFO, WAITING_DEKONT, WAITING_PROMO, WAITING_TRACKING = range(4)

# --- VERİTABANI İŞLEMLERİ (GÜVENLİ THREAD-LOCK) ---
def load_json(filepath):
    with db_lock:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"{filepath} okuma hatasi: {e}")
                return {}
        return {}

def save_json(filepath, data):
    with db_lock:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"{filepath} kayit hatasi: {e}")

def get_user_data(user_id):
    data = load_json(DATA_FILE)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "balance": 0,
            "invited_count": 0,
            "history": [],
            "last_wheel": None
        }
        save_json(DATA_FILE, data)
    return data[uid]

def update_user_data(user_id, key, value):
    data = load_json(DATA_FILE)
    uid = str(user_id)
    if uid not in data:
        get_user_data(user_id)
        data = load_json(DATA_FILE)
    data[uid][key] = value
    save_json(DATA_FILE, data)

# --- GÜVENLİK FİLTRELERİ (ANTI-SPAM & SANITIZE) ---
def sanitize_input(text: str) -> str:
    """Kullanıcı verisini XSS ve HTML Injection'a karşı temizler."""
    if not text:
        return ""
    return html.escape(text.strip())

def is_rate_limited(user_id: int, limit_seconds: float = 1.0) -> bool:
    """Buton spamını ve DDoS saldırılarını engeller."""
    now = time.time()
    last_time = rate_limit_store.get(user_id, 0)
    if now - last_time < limit_seconds:
        return True
    rate_limit_store[user_id] = now
    return False

def is_banned(user_id: int) -> bool:
    """Kullanıcının engellenip engellenmediğini kontrol eder."""
    banned = load_json(BANNED_FILE)
    return str(user_id) in banned

# --- HİZMET TANIMLARI ---
SERVICES = [
    "1. Tel No ile Tel Cokertme",
    "2. Kameraya Sizna",
    "3. Canli Konum Takibi",
    "4. Instagram Hesap Calma",
    "5. Ihbar Atma (EGM / Jandarma)",
    "6. Instagram Hesap Acma",
    "7. Deepfake Hizmeti",
    "8. Galeriye Sizna",
    "9. Telefona Tam Sizna",
    "10. WhatsApp Sizna",
    "11. Fake Numara Saglama",
    "12. Instagram Hesap Kapatma",
    "13. TikTok Hesap Kapatma",
    "14. Telegram Numara Bulma",
    "15. Ortam & Mikrofon Dinleme",
    "16. Fotograftan Sosyal Medya Bulma"
]

SERVICE_DETAILS = {
    0: "Target cihazın şebeke ve sistem bağlantısını devre dışı bırakır.",
    1: "Cihaz kamerasında anlık görüntü/canlı yayın erişimi sağlar.",
    2: "GPS üzerinden nokta atışı canlı konum tespiti yapar.",
    3: "Hedef Instagram hesabına erişim ve kontrol imkanı sunar.",
    4: "Resmi makamlara anonim ve takip edilemez ihbar iletimi sağlar.",
    5: "Kapatılmış Instagram hesaplarını tekrar açar.",
    6: "Yapay zeka ile ses ve yüz verisi içerik üretir.",
    7: "Hedef telefonun galeri klasörlerine tam erişim sağlar.",
    8: "Cihazın tüm kontrolünü ve dosyalarını uzaktan erişime açar.",
    9: "WhatsApp mesajlaşmaları ve medya geçmişini aktarır.",
    10: "İstediğiniz ülke koduna sahip anonim numara sağlar.",
    11: "Hedef Instagram hesabını kalıcı kapatır.",
    12: "Target TikTok hesabını erişime kapatır.",
    13: "Telegram kullanıcı adından bağlı numarayı bulur.",
    14: "Cihaz mikrofonunu canlı ve gizli olarak aktifleştirir.",
    15: "Yüz tarama ve yapay zeka algoritması ile fotoğraf üzerinden tüm aktif sosyal medya hesaplarını bulur."
}

def calculate_price(count, express=False):
    if count == 0:
        base = 0
    elif count == 1:
        base = 1000
    elif count == 2:
        base = 1800
    elif count == 3:
        base = 3200
    elif count in [4, 5]:
        base = 4200
    else:
        base = 4200 + (count - 5) * 800
    return base + (300 if (express and base > 0) else 0)

async def check_channel_membership(user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return True

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str, reply_markup=None):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Admin bildirim hatasi: {e}")

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Hizmet Seç & Sepet Oluştur", callback_data="select_services")],
        [InlineKeyboardButton("💳 Bakiye / Ödeme Yap", callback_data="purchase"), InlineKeyboardButton("📜 Hizmet Rehberi & Detaylar", callback_data="catalog")],
        [InlineKeyboardButton("🎰 Günlük Şans Çarkı", callback_data="daily_wheel"), InlineKeyboardButton("🎟️ Promo Kod Kullan", callback_data="use_promo")],
        [InlineKeyboardButton("🎁 Referans / Arkadaşını Getir", callback_data="referral"), InlineKeyboardButton("🔍 Sipariş Sorgula", callback_data="track_order")],
        [InlineKeyboardButton("🛡 Güvenlik & Garanti", callback_data="guarantee"), InlineKeyboardButton("💬 Müşteri Yorumları", callback_data="reviews")],
        [InlineKeyboardButton("👤 Profilim & Geçmiş", callback_data="profile"), InlineKeyboardButton("❓ SSS & Bilgi", callback_data="faq")],
        [InlineKeyboardButton("💬 Canlı Destek & İletişim", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ])

def get_welcome_text(first_name):
    return (
        f"👑 <b>CHIWAS VIP SERVICES - RESMİ OTOMASYON BOTU</b>\n"
        f"-----------------------------------------\n"
        f"👋 Hoş Geldiniz, Sayın <b>{first_name}</b>!\n\n"
        f"🔒 <b>%100 Anonimlik & VIP Güvenlik Kalkanı</b>\n"
        f"🛡 Tüm işlemleriniz 256-Bit uçtan uca şifreleme altındadır.\n\n"
        f"🔥 <b>GÜNCEL FIRSAT:</b> 3 ve üzeri işlem alımlarında VIP indirim!\n"
        f"🎁 <b>ARKADAŞINI GETİR:</b> Davet ettiğin her arkadaşın için anında +{REFERRAL_REWARD} TL kazan!\n\n"
        f"👇 İşlem yapmak için aşağıdaki menüyü kullanabilirsiniz:"
    )

# --- KULLANICI BAŞLANGIÇ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Ban Kontrolü
    if is_banned(user.id):
        await update.message.reply_text("❌ <b>Erişiminiz Engellendi!</b>\nGüvenlik ihlali nedeniyle bota erişiminiz kısıtlanmıştır.", parse_mode="HTML")
        return

    u_data = get_user_data(user.id)
    context.user_data['cart'] = set()
    context.user_data['express'] = False

    # Force Join Kontrolü
    is_member = await check_channel_membership(user.id, context)
    if not is_member:
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton("✅ Katıldım, Başlat", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"⚠️ <b>GÜVENLİK PROTOKOLÜ: KANAL KATILIMI ZORUNLUDUR</b>\n\n"
            f"Sisteme erişmek için resmi kanalımıza katılmış olmanız gerekmektedir.",
            reply_markup=btn,
            parse_mode="HTML"
        )
        return

    if context.args and len(context.args) > 0:
        ref_code = context.args[0]
        try:
            inviter_id = ref_code.replace("CHW-", "")
            if inviter_id != str(user.id):
                all_data = load_json(DATA_FILE)
                if inviter_id in all_data and f"ref_{user.id}" not in u_data:
                    inviter_data = all_data[inviter_id]
                    inviter_data["balance"] = inviter_data.get("balance", 0) + REFERRAL_REWARD
                    inviter_data["invited_count"] = inviter_data.get("invited_count", 0) + 1
                    save_json(DATA_FILE, all_data)
                    update_user_data(user.id, f"ref_{user.id}", True)
                    try:
                        await context.bot.send_message(
                            chat_id=int(inviter_id),
                            text=f"🎉 <b>TEBRİKLER!</b>\nBir arkadaşınız davetinizle bota katıldı.\n🎁 Hesabınıza <b>+{REFERRAL_REWARD} TL</b> eklendi!",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Referans hatasi: {e}")

    await update.message.reply_text(get_welcome_text(sanitize_input(user.first_name)), reply_markup=get_main_keyboard(), parse_mode="HTML")

def build_service_keyboard(cart, express):
    keyboard = []
    if len(cart) == len(SERVICES):
        keyboard.append([InlineKeyboardButton("❌ Tüm Seçimleri Temizle", callback_data="select_none")])
    else:
        keyboard.append([InlineKeyboardButton("⚡ Tüm Hizmetleri Seç (Mega Paket)", callback_data="select_all")])

    for i, service in enumerate(SERVICES):
        is_selected = i in cart
        btn_text = f"✅ {service}" if is_selected else f"🔹 {service}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{i}")])

    exp_btn = "🚀 VIP Express Mod: AKTİF (+300 TL)" if express else "⚪ Express Hızlı Teslimat Ekle (+300 TL)"
    keyboard.append([InlineKeyboardButton(exp_btn, callback_data="toggle_express")])

    count = len(cart)
    price_tl = calculate_price(count, express)
    keyboard.append([InlineKeyboardButton(f"🛒 Sepeti Onayla ({count} İşlem - {price_tl} TL)", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# --- ADMİN GÜVENLİK & YÖNETİM KOMUTLARI ---
async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: <code>/ban &lt;user_id&gt;</code>", parse_mode="HTML")
        return
    target_id = context.args[0]
    banned = load_json(BANNED_FILE)
    banned[target_id] = str(datetime.now())
    save_json(BANNED_FILE, banned)
    await update.message.reply_text(f"🚫 <code>{target_id}</code> ID'li kullanıcı başarıyla BANLANDI.", parse_mode="HTML")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: <code>/unban &lt;user_id&gt;</code>", parse_mode="HTML")
        return
    target_id = context.args[0]
    banned = load_json(BANNED_FILE)
    if target_id in banned:
        del banned[target_id]
        save_json(BANNED_FILE, banned)
        await update.message.reply_text(f"✅ <code>{target_id}</code> ID'li kullanıcının banı kaldırıldı.", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Kullanıcı banlı değil.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    admin_text = (
        "👑 <b>CHIWAS ADVANCED YÖNETİCİ & GÜVENLİK PANELİ</b>\n"
        "-----------------------------------------\n"
        "📊 <code>/istatistik</code> - Sistem istatistikleri.\n"
        "📢 <code>/duyuru &lt;mesaj&gt;</code> - Toplu duyuru.\n"
        "💳 <code>/bakiye_ekle &lt;user_id&gt; &lt;miktar&gt;</code> - Bakiye yükle.\n"
        "🔻 <code>/bakiye_sil &lt;user_id&gt; &lt;miktar&gt;</code> - Bakiye düş.\n"
        "🚫 <code>/ban &lt;user_id&gt;</code> - Kullanıcıyı bota engelle.\n"
        "✅ <code>/unban &lt;user_id&gt;</code> - Engeli kaldır.\n"
        "🎟️ <code>/kod_olustur &lt;KOD&gt; &lt;TUTAR&gt; &lt;LIMIT&gt;</code> - Promo kod.\n"
        "📈 <code>/durum_guncelle &lt;TAKIP_KODU&gt; &lt;YUZDE&gt; &lt;MESAJ&gt;</code> - Sipariş güncelle."
    )
    await update.message.reply_text(admin_text, parse_mode="HTML")

# --- CONVERSATION HANDLERS ---
async def start_target_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 <b>HEDEF BİLGİSİ GİRİŞİ</b>\n-----------------------------------------\n"
        "Lütfen işlem yapılmasını istediğiniz <b>Target Telefon Numarasını / Kullanıcı Adını</b> yazıp gönderin:\n\n"
        "🔒 <i>Girdiğiniz tüm bilgiler şifrelenmektedir.</i>",
        parse_mode="HTML"
    )
    return WAITING_TARGET_INFO

async def receive_target_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_info = sanitize_input(update.message.text)
    context.user_data['target_info'] = target_info

    order = context.user_data.get('pending_order', {})
    final_price = order.get('final_price', 0)

    text = (
        f"💳 <b>ÖDENECEK NET TUTAR:</b> {final_price} TL\n\n"
        f"💳 <b>İBAN İLE ÖDEME</b> <i>(Kopyalamak için üzerlerine dokunun)</i>\n"
        f"🏦 <b>İBAN:</b> <code>TR100006200091000006969709</code>\n"
        f"👤 <b>Alıcı:</b> <code>Garanti Odeme ve Elektronik Para Hizmetleri A.Ş.</code>\n"
        f"📌 <b>Açıklama:</b> <code>TAMI7786986257878012</code>\n\n"
        f"📸 <b>GÜVENLİK ŞARTI:</b> Lütfen ödemeyi yaptıktan sonra <b>Ödeme Dekontunun FOTOĞRAFINI (Ekran Görüntüsü)</b> buraya gönderin."
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return WAITING_DEKONT

async def receive_dekont(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = get_user_data(user.id)
    order = context.user_data.get('pending_order', {})

    # Fotoğraf Zorunluluğu Kontrolü (Güvenlik Kalkanı)
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ <b>GÜVENLİK UYARISI:</b> Sadece ödeme dekontunun <b>FOTOĞRAFINI</b> kabul ediyoruz. Metin kabul edilmez. Lütfen fotoğraf gönderin!",
            parse_mode="HTML"
        )
        return WAITING_DEKONT

    count = order.get('count', 0)
    final_price = order.get('final_price', 0)
    services = order.get('services', [])
    used_discount = order.get('used_discount', 0)
    target_info = context.user_data.get('target_info', 'Belirtilmedi')

    track_code = f"CHW-{random.randint(10000, 99999)}"

    orders = load_json(ORDERS_FILE)
    orders[track_code] = {
        "user_id": user.id,
        "services": services,
        "price": final_price,
        "target_info": target_info,
        "percent": "10",
        "status_text": "Ödeme & Dekont Doğrulanıyor",
        "date": str(datetime.now().strftime("%Y-%m-%d %H:%M"))
    }
    save_json(ORDERS_FILE, orders)

    order_summary = f"{count if count > 0 else 1} İşlem ({final_price} TL) - KOD: #{track_code}"
    history = u_data.get("history", [])
    history.append(order_summary)

    if used_discount > 0:
        u_data["balance"] = max(0, u_data.get("balance", 0) - used_discount)

    update_user_data(user.id, "history", history)
    if used_discount > 0:
        update_user_data(user.id, "balance", u_data["balance"])

    admin_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Onayla", callback_data=f"adm_approve_{user.id}_{track_code}"),
            InlineKeyboardButton("❌ Reddet", callback_data=f"adm_reject_{user.id}_{track_code}"),
            InlineKeyboardButton("🚫 Kullanıcıyı Banla", callback_data=f"adm_quickban_{user.id}")
        ]
    ])

    admin_msg = (
        f"🚨 <b>YENİ DEKONT & SİPARİŞ BİLDİRİMİ!</b>\n-----------------------------------------\n"
        f"👤 <b>Müşteri:</b> {sanitize_input(user.first_name)} (@{user.username})\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🔍 <b>Takip Kodu:</b> <code>#{track_code}</code>\n"
        f"🎯 <b>Hedef Bilgi:</b> <code>{target_info}</code>\n"
        f"🛒 <b>Sepet:</b>\n" + ("\n".join(services) if services else "Özel İşlem") + "\n\n"
        f"💰 <b>Beklenen Tutar:</b> {final_price} TL"
    )

    photo_file_id = update.message.photo[-1].file_id
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=admin_msg, reply_markup=admin_markup, parse_mode="HTML")

    await update.message.reply_text(
        f"✅ <b>SİPARİŞİNİZ ALINDI!</b>\n-----------------------------------------\n"
        f"📌 <b>Sipariş Takip Kodunuz:</b> <code>{track_code}</code>\n\n"
        f"Dekontunuz finans ekibimize iletildi. Kontrol edildikten sonra işleminiz başlatılacaktır.\n"
        f"Durumunuzu <b>'🔍 Sipariş Sorgula'</b> butonundan anlık takip edebilirsiniz.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

    return ConversationHandler.END

async def start_use_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🎟️ <b>PROMO KOD GİRİŞİ</b>\n-----------------------------------------\nLütfen kupon kodunuzu yazıp gönderin:",
        parse_mode="HTML"
    )
    return WAITING_PROMO

async def receive_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    code = sanitize_input(update.message.text.strip().upper())
    coupons = load_json(COUPONS_FILE)

    if code in coupons:
        c = coupons[code]
        if str(user.id) in c.get("used_by", []):
            await update.message.reply_text("❌ Bu kitleye ait kuponu daha önce kullandınız!", reply_markup=get_main_keyboard())
        elif len(c.get("used_by", [])) >= c.get("limit", 0):
            await update.message.reply_text("❌ Kuponun kullanım limiti dolmuştur!", reply_markup=get_main_keyboard())
        else:
            amount = c.get("amount", 0)
            u_data = get_user_data(user.id)
            u_data["balance"] = u_data.get("balance", 0) + amount
            c.setdefault("used_by", []).append(str(user.id))

            save_json(COUPONS_FILE, coupons)
            update_user_data(user.id, "balance", u_data["balance"])

            await update.message.reply_text(
                f"🎉 <b>TEBRİKLER!</b>\n<code>{code}</code> kuponu kabul edildi.\nHesabınıza <b>+{amount} TL</b> eklendi!",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text("❌ Geçersiz veya süresi dolmuş promo kod!", reply_markup=get_main_keyboard())

    return ConversationHandler.END

async def start_track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔍 <b>SİPARİŞ DURUMU SORGULAMA</b>\n-----------------------------------------\nLütfen 5 haneli <b>Takip Kodunuzu</b> yazın (Örn: <code>CHW-89321</code>):",
        parse_mode="HTML"
    )
    return WAITING_TRACKING

async def receive_track_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
