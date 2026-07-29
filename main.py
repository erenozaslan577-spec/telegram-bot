import logging
import json
import os
import time
import html
import threading
import random
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8674816242:AAFyfHCoSRwJv_bJ8ffzsTDL83h3BaEfyVo")
ADMIN_USERNAME = "@kralinarest"
ADMIN_ID = int(os.getenv("ADMIN_ID", "8932488958"))
BOT_USERNAME = "ChiwasIslenBot"
REQUIRED_CHANNEL = "@ChiwasDuyuru"

DATA_FILE = "users_data.json"
COUPONS_FILE = "coupons_data.json"
ORDERS_FILE = "orders_data.json"
BANNED_FILE = "banned_users.json"
REFERRAL_REWARD = 40

db_lock = threading.Lock()
rate_limit_store = {}

# Conversation States
WAITING_TARGET_INFO, WAITING_DEKONT, WAITING_PROMO, WAITING_TRACKING = range(4)

# --- VERİTABANI İŞLEMLERİ ---
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
            logging.error(f"{filepath} kayit hatasi: {e}")def get_user_data(user_id):
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

# --- GÜVENLİK FİLTRELERİ ---
def sanitize_input(text: str) -> str:
    if not text:
        return ""
    return html.escape(text.strip())

def is_rate_limited(user_id: int, limit_seconds: float = 1.0) -> bool:
    now = time.time()
    last_time = rate_limit_store.get(user_id, 0)
    if now - last_time < limit_seconds:
        return True
    rate_limit_store[user_id] = now
    return False

def is_banned(user_id: int) -> bool:
    banned = load_json(BANNED_FILE)
    return str(user_id) in banned

# --- HİZMET TANIMLARI ---
SERVICES = [
    "1. Tel No ile Tel Cokartme",
    "2. Kameraya Sizma",
    "3. Canli Konum Takibi",
    "4. Instagram Hesap Calma",
    "5. Ihbar Atma (EGM / Jandarma)",
    "6. Instagram Hesap Acma",
    "7. Deepfake Hizmeti",
    "8. Galeriye Sizma",
    "9. Telefona Tam Sizma",
    "10. WhatsApp Sizma",
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
}def calculate_price(count, express=False):
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

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Hizmet Seç & Sepet Oluştur", callback_data="select_services")],
        [InlineKeyboardButton("💳 Bakiye / Ödeme Yap", callback_data="purchase"), InlineKeyboardButton("📜 Hizmet Rehberi", callback_data="guide")],
        [InlineKeyboardButton("🎰 Günlük Şans Çarkı", callback_data="daily_wheel"), InlineKeyboardButton("🎟 Promo Kod", callback_data="use_promo")],
        [InlineKeyboardButton("👥 Referans / Arkadaşını Getir", callback_data="referral"), InlineKeyboardButton("🔍 Müşteri Yorumları", callback_data="reviews")],
        [InlineKeyboardButton("🛡 Güvenlik & Garanti", callback_data="guarantee"), InlineKeyboardButton("❓ SSS & Bilgi", callback_data="faq")],
        [InlineKeyboardButton("👤 Profilim & Geçmiş", callback_data="profile"), InlineKeyboardButton("📍 Sipariş Takip", callback_data="track_order")],
        [InlineKeyboardButton("💬 Canlı Destek & İletişim", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ])

def get_welcome_text(first_name):
    return (
        f"<b>CHIWAS VIP SERVICES - RESMI OTOMASYON BOTU</b>\n"
        f"----------------------------------------\n"
        f"👋 Hoş Geldiniz, Sayın <b>{first_name}</b>\n\n"
        f"🛡 <b>%100 Anonimlik & VIP Güvenlik Kalkanı</b>\n"
        f"🔐 Tüm işlemleriniz 256-bit uçtan uca şifreleme altındadır.\n\n"
        f"🔥 <b>GÜNCEL FIRSAT:</b> 3 ve üzeri işlem alımlarında VIP indirim!\n"
        f"🎁 <b>ARKADAŞINI GETİR:</b> Davet ettiğin her arkadaşın için anında +{REFERRAL_REWARD} TL kazan!\n\n"
        f"📌 İşlem yapmak için aşağıdaki menüyü kullanabilirsiniz:"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("❌ <b>Erişiminiz Engellendi!</b>\nGüvenlik ihlali nedeniyle bota erişiminiz kısıtlanmıştır.", parse_mode="HTML")
        return

    u_data = get_user_data(user.id)
    context.user_data['cart'] = set()
    context.user_data['express'] = False

    is_member = await check_channel_membership(user.id, context)
    if not is_member:
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton("✅ Katıldım, Başlat", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"⚠️ <b>GÜVENLİK PROTOKOLÜ: KANAL KATILIMI ZORUNLUDUR</b>\n\nSisteme erişmek için resmi kanalımıza katılmış olmanız gerekmektedir.",
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
                        await context.bot.send_message(chat_id=int(inviter_id), text=f"🎉 <b>TEBRİKLER!</b>\nBir arkadaşınız davetinizle bota katıldı. Hesabınıza +{REFERRAL_REWARD} TL eklendi!", parse_mode="HTML")
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
        btn_text = f"✅ {service}" if is_selected else f"➕ {service}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{i}")])

    exp_btn = "🚀 VIP Express Mod: AKTİF (+300 TL)" if express else "⚪ Express Hızlı Teslimat Ekle (+300 TL)"
    keyboard.append([InlineKeyboardButton(exp_btn, callback_data="toggle_express")])

    count = len(cart)
    price_tl = calculate_price(count, express)
    keyboard.append([InlineKeyboardButton(f"🛒 Sepeti Onayla ({count} İşlem - {price_tl} TL)", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)# --- CONVERSATION HANDLERS ---
async def start_target_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"🎯 <b>HEDEF BİLGİSİ GİRİŞİ</b>\n----------------------------------------\nLütfen işlem yapılmasını istediğiniz <b>Target Telefon Numarasını / Kullanıcı Adını</b> yazıp gönderin:\n\n🔒 <i>Girdiğiniz tüm bilgiler şifrelenmektedir.</i>",
        parse_mode="HTML"
    )
    return WAITING_TARGET_INFO

async def receive_target_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_info = sanitize_input(update.message.text)
    context.user_data['target_info'] = target_info
    order = context.user_data.get('pending_order', {})
    final_price = order.get('final_price', 0)

    text = (
        f"💳 <b>ÖDENECEK NET TUTAR: {final_price} TL</b>\n\n"
        f"🏦 <b>IBAN İLE ÖDEME</b> (Kopyalamak için üzerlerine dokunun):\n"
        f"📍 <b>IBAN:</b> <code>TR10 0006 2000 9100 0006 9897 09</code>\n"
        f"👤 <b>Alıcı:</b> <code>Garanti Ödeme ve Elektronik Para Hizmetleri A.Ş.</code>\n"
        f"💬 <b>Açıklama:</b> <code>TAW17786986257878012</code>\n\n"
        f"🛡 <b>GÜVENLİK ŞARTI:</b> Lütfen ödemeyi yaptıktan sonra <b>Ödeme Dekontunun FOTOĞRAFINI (Ekran Görüntüsü)</b> buraya gönderin."
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return WAITING_DEKONT

async def receive_dekont(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = get_user_data(user.id)
    order = context.user_data.get('pending_order', {})

    if not update.message.photo:
        await update.message.reply_text("⚠️ <b>GÜVENLİK UYARISI:</b> Sadece ödeme dekontunun <b>FOTOĞRAFINI</b> kabul ediyoruz.", parse_mode="HTML")
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
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_json(ORDERS_FILE, orders)

    order_summary = f"{count} İşlem ({final_price} TL) - KOD: #{track_code}"
    history = u_data.get("history", [])
    history.append(order_summary)

    if used_discount > 0:
        u_data["balance"] = max(0, u_data.get("balance", 0) - used_discount)

    update_user_data(user.id, "history", history)
    if used_discount > 0:
        update_user_data(user.id, "balance", u_data["balance"])

    admin_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Onayla", callback_data=f"adm_approve_{user.id}_{track_code}"), InlineKeyboardButton("❌ Reddet", callback_data=f"adm_reject_{user.id}_{track_code}")],
        [InlineKeyboardButton("🚫 Kullanıcıyı Banla", callback_data=f"adm_quickban_{user.id}")]
    ])

    admin_msg = (
        f"🚨 <b>YENİ DEKONT BİLDİRİMİ!</b>\n----------------------------------------\n"
        f"👤 <b>Müşteri:</b> {sanitize_input(user.first_name)} (@{user.username})\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🏷 <b>Takip Kodu:</b> <code>{track_code}</code>\n"
        f"🎯 <b>Hedef Bilgi:</b> <code>{target_info}</code>\n"
        f"💰 <b>Beklenen Tutar:</b> <b>{final_price} TL</b>"
    )

    photo_file_id = update.message.photo[-1].file_id
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=admin_msg, reply_markup=admin_markup, parse_mode="HTML")

    await update.message.reply_text(
        f"✅ <b>SİPARİŞİNİZ ALINDI!</b>\n----------------------------------------\n📋 Sipariş Takip Kodunuz: <code>{track_code}</code>\n\nDekontunuz kontrol edildikten sonra işleminiz başlatılacaktır.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def start_use_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🎟 <b>PROMO KOD GİRİŞİ</b>\n----------------------------------------\nLütfen kupon kodunuzu yazıp gönderin:", parse_mode="HTML")
    return WAITING_PROMO

async def receive_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    code = sanitize_input(update.message.text).upper()

    coupons = load_json(COUPONS_FILE)
    if code in coupons:
        c = coupons[code]
        if str(user.id) in c.get("used_by", []):
            await update.message.reply_text("❌ Bu kuponu daha önce kullandınız!", reply_markup=get_main_keyboard())
        elif len(c.get("used_by", [])) >= c.get("limit", 0):
            await update.message.reply_text("❌ Kuponun kullanım limiti dolmuştur!", reply_markup=get_main_keyboard())
        else:
            amount = c.get("amount", 0)
            u_data = get_user_data(user.id)
            u_data["balance"] = u_data.get("balance", 0) + amount
            c.setdefault("used_by", []).append(str(user.id))
            save_json(COUPONS_FILE, coupons)
            update_user_data(user.id, "balance", u_data["balance"])
            await update.message.reply_text(f"🎉 <b>TEBRİKLER!</b>\nHesabınıza <b>+{amount} TL</b> eklendi!", reply_markup=get_main_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Geçersiz veya süresi dolmuş promo kod!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def start_track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 <b>SİPARİŞ SORGULAMA</b>\n----------------------------------------\nLütfen <b>Takip Kodunuzu</b> yazıp gönderin (Örn: CHW-12345):", parse_mode="HTML")
    return WAITING_TRACKING

async def receive_track_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = sanitize_input(update.message.text.strip().upper())
    orders = load_json(ORDERS_FILE)
    if code in orders:
        ord_info = orders[code]
        status_msg = (
            f"📊 <b>SİPARİŞ DETAYLARI: #{code}</b>\n----------------------------------------\n"
            f"📅 <b>Tarih:</b> {ord_info.get('date', 'N/A')}\n"
            f"🎯 <b>Hedef:</b> <code>{ord_info.get('target_info', 'Gizli')}</code>\n"
            f"📊 <b>İlerleme:</b> %{ord_info.get('percent', '0')}\n"
            f"📌 <b>Durum:</b> {ord_info.get('status_text', 'İşleniyor')}"
        )
        await update.message.reply_text(status_msg, reply_markup=get_main_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Girilen takip koduna ait sipariş bulunamadı!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ İşlem iptal edildi.", reply_markup=get_main_keyboard())
    return ConversationHandler.END# --- BUTON TIKLAMA HANDLER ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    data = query.data

    if is_banned(user.id):
        await query.answer("❌ Engellendiniz!", show_alert=True)
        return

    if is_rate_limited(user.id):
        await query.answer("⚠️ Lütfen çok hızlı tıklamayın!", show_alert=True)
        return

    await query.answer()

    cart = context.user_data.setdefault('cart', set())
    express = context.user_data.setdefault('express', False)

    if data == "back_main":
        await query.edit_message_text(get_welcome_text(sanitize_input(user.first_name)), reply_markup=get_main_keyboard(), parse_mode="HTML")

    elif data == "check_join":
        is_member = await check_channel_membership(user.id, context)
        if is_member:
            await query.edit_message_text(get_welcome_text(sanitize_input(user.first_name)), reply_markup=get_main_keyboard(), parse_mode="HTML")
        else:
            await query.answer("❌ Kanala henüz katılmadınız!", show_alert=True)

    elif data == "select_services":
        await query.edit_message_text("🛠 <b>HİZMET SEÇİM PANELİ</b>\n\nLütfen paketlerinizi belirleyin:", reply_markup=build_service_keyboard(cart, express), parse_mode="HTML")

    elif data.startswith("toggle_"):
        if data == "toggle_express":
            context.user_data['express'] = not express
        else:
            idx = int(data.split("_")[1])
            if idx in cart:
                cart.remove(idx)
            else:
                cart.add(idx)
        await query.edit_message_text("🛠 <b>HİZMET SEÇİM PANELİ</b>\n\nLütfen paketlerinizi belirleyin:", reply_markup=build_service_keyboard(cart, context.user_data['express']), parse_mode="HTML")

    elif data == "select_all":
        context.user_data['cart'] = set(range(len(SERVICES)))
        await query.edit_message_text("🛠 <b>HİZMET SEÇİM PANELİ</b>\n\nLütfen paketlerinizi belirleyin:", reply_markup=build_service_keyboard(context.user_data['cart'], express), parse_mode="HTML")

    elif data == "select_none":
        context.user_data['cart'] = set()
        await query.edit_message_text("🛠 <b>HİZMET SEÇİM PANELİ</b>\n\nLütfen paketlerinizi belirleyin:", reply_markup=build_service_keyboard(set(), express), parse_mode="HTML")

    elif data == "checkout":
        if not cart:
            await query.answer("⚠️ Lütfen en az 1 hizmet seçin!", show_alert=True)
            return

        selected_services = [SERVICES[i] for i in sorted(list(cart))]
        count = len(selected_services)
        raw_price = calculate_price(count, express)

        u_data = get_user_data(user.id)
        balance = u_data.get('balance', 0)

        discount_applied = min(balance, raw_price)
        final_price = raw_price - discount_applied

        context.user_data['pending_order'] = {
            'count': count,
            'services': selected_services,
            'raw_price': raw_price,
            'used_discount': discount_applied,
            'final_price': final_price
        }

        summary_text = (
            f"🛒 <b>SEPET ÖZETİ</b>\n----------------------------------------\n"
            f"• " + "\n• ".join(selected_services) + "\n\n"
            f"⚡ <b>Express Teslimat:</b> {'EVET (+300 TL)' if express else 'HAYIR'}\n"
            f"💰 <b>Tutar:</b> {raw_price} TL\n"
            f"🎁 <b>Kullanılan Bakiye İndirimi:</b> -{discount_applied} TL\n"
            f"💵 <b>Ödenecek Net Tutar:</b> <b>{final_price} TL</b>\n\n"
            f"İşleme devam etmek istiyor musunuz?"
        )

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Siparişi Tamamla & Öde", callback_data="proceed_target")],
            [InlineKeyboardButton("✏️ Sepeti Düzenle", callback_data="select_services")]
        ])
        await query.edit_message_text(summary_text, reply_markup=btn, parse_mode="HTML")

    elif data == "purchase":
        text = (
            f"💳 <b>BAKİYE YÜKLE & DİREKT ÖDEME</b>\n----------------------------------------\n"
            f"📍 <b>IBAN:</b> <code>TR10 0006 2000 9100 0006 9897 09</code>\n"
            f"👤 <b>Alıcı:</b> <code>Garanti Ödeme ve Elektronik Para Hizmetleri A.Ş.</code>\n"
            f"💬 <b>Açıklama:</b> <code>TAW17786986257878012</code>\n\n"
            f"Ödeme yaptıktan sonra dekontunuzu Destek ekibimize iletebilirsiniz."
        )
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "guide":
        text = f"📜 <b>HİZMET KATALOĞU</b>\n----------------------------------------\n\n"
        for i, name in enumerate(SERVICES):
            text += f"<b>{name}</b>\n<i>└ {SERVICE_DETAILS.get(i, 'Açıklama yok.')}</i>\n\n"
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "daily_wheel":
        u_data = get_user_data(user.id)
        last_wheel = u_data.get("last_wheel")
        now = datetime.now()

        if last_wheel:
            last_date = datetime.strptime(last_wheel, "%Y-%m-%d %H:%M:%S")
            if now - last_date < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_date)
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await query.answer(f"⏳ Çarkı tekrar çevirmek için {hours}s {minutes}dk beklemelisiniz!", show_alert=True)
                return

        reward = random.choice([50, 100, 150, 200, 250])
        u_data["balance"] = u_data.get("balance", 0) + reward
        u_data["last_wheel"] = now.strftime("%Y-%m-%d %H:%M:%S")

        update_user_data(user.id, "balance", u_data["balance"])
        update_user_data(user.id, "last_wheel", u_data["last_wheel"])

        text = f"🎰 <b>GÜNLÜK ŞANS ÇARKI!</b>\n----------------------------------------\n🎉 Çarktan <b>+{reward} TL</b> bakiye kazandınız!\n💰 Yeni Bakiyeniz: <b>{u_data['balance']} TL</b>"
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "referral":
        u_data = get_user_data(user.id)
        ref_link = f"https://t.me/{BOT_USERNAME}?start=CHW-{user.id}"
        text = (
            f"👥 <b>REFERANS SİSTEMİ</b>\n----------------------------------------\n"
            f"Davet ettiğiniz her kullanıcı için <b>+{REFERRAL_REWARD} TL</b> kazanın!\n\n"
            f"👥 Toplam Davet: <b>{u_data.get('invited_count', 0)} Kişi</b>\n"
            f"💰 Kazanç: <b>{u_data.get('invited_count', 0) * REFERRAL_REWARD} TL</b>\n\n"
            f"🔗 <b>Davet Linkiniz:</b>\n<code>{ref_link}</code>"
        )
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "reviews":
        text = "💬 <b>MÜŞTERİ YORUMLARI</b>\n----------------------------------------\n⭐ <b>B***n:</b> <i>'Instagram alma işlemi 15 dakikada bitti.'</i>\n⭐ <b>A***k:</b> <i>'Canlı konum tespiti %100 doğru verdi.'</i>"
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Duyuru Kanalı", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "guarantee":
        text = "🛡 <b>GÜVENLİK & GARANTİ</b>\n----------------------------------------\n🔒 <b>Gizlilik:</b> Loglar otomatik silinir.\n💎 <b>İade:</b> Başarısız işlemlerde tam iade yapılır."
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "faq":
        text = "❓ <b>SIKÇA SORULAN SORULAR</b>\n----------------------------------------\n❓ <b>İşlem süresi ne kadar?</b>\nC: Standart 1-3 saat, VIP Express 15-30 dakikadır."
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data == "profile":
        u_data = get_user_data(user.id)
        history = u_data.get("history", [])
        hist_text = "\n".join([f"• {h}" for h in history[-5:]]) if history else "Sipariş yok."
        text = f"👤 <b>MÜŞTERİ PROFİLİ</b>\n----------------------------------------\n🆔 <b>ID:</b> <code>{user.id}</code>\n💰 <b>Bakiye:</b> <b>{u_data.get('balance', 0)} TL</b>\n\n📜 <b>Geçmiş:</b>\n{hist_text}"
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    elif data.startswith("adm_"):
        if user.id != ADMIN_ID:
            return
        parts = data.split("_")
        action = parts[1]

        if action == "approve":
            target_uid = int(parts[2])
            t_code = parts[3]
            orders = load_json(ORDERS_FILE)
            if t_code in orders:
                orders[t_code]["status_text"] = "İşleme Alındı"
                orders[t_code]["percent"] = "50"
                save_json(ORDERS_FILE, orders)
            try:
                await context.bot.send_message(chat_id=target_uid, text=f"✅ <code>{t_code}</code> kodlu siparişiniz onaylandı ve başlatıldı.", parse_mode="HTML")
            except Exception:
                pass
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ <b>ONAYLANDI</b>")

        elif action == "reject":
            target_uid = int(parts[2])
            t_code = parts[3]
            orders = load_json(ORDERS_FILE)
            if t_code in orders:
                orders[t_code]["status_text"] = "Reddedildi"
                save_json(ORDERS_FILE, orders)
            try:
                await context.bot.send_message(chat_id=target_uid, text=f"❌ <code>{t_code}</code> sipariş ödemesi reddedildi.", parse_mode="HTML")
            except Exception:
                pass
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ <b>REDDEDİLDİ</b>")

        elif action == "quickban":
            target_uid = int(parts[2])
            banned = load_json(BANNED_FILE)
            banned[str(target_uid)] = True
            save_json(BANNED_FILE, banned)
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n🚫 <b>KULLANICI ENGELLENDİ!</b>")# --- ADMİN KOMUTLARI ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    all_users = load_json(DATA_FILE)
    all_orders = load_json(ORDERS_FILE)
    panel_text = f"👑 <b>ADMİN PANELİ</b>\n----------------------------------------\n👥 Müşteri: <code>{len(all_users)}</code>\n📦 Sipariş: <code>{len(all_orders)}</code>\n\n<b>Komutlar:</b>\n/bakiye_ekle ID TUTAR\n/durum KOD YUZDE\n/duyuru Mesaj\n/ban ID\n/unban ID\n/addcoupon KOD MIKTAR LIMIT"
    await update.message.reply_text(panel_text, parse_mode="HTML")

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_uid = context.args[0]
        amount = int(context.args[1])
        data = load_json(DATA_FILE)
        if target_uid in data:
            data[target_uid]["balance"] = data[target_uid].get("balance", 0) + amount
            save_json(DATA_FILE, data)
            await update.message.reply_text(f"✅ <code>{target_uid}</code> hesabına <b>+{amount} TL</b> eklendi.", parse_mode="HTML")
            try:
                await context.bot.send_message(chat_id=int(target_uid), text=f"🎉 Hesabınıza <b>+{amount} TL</b> bakiye yüklendi!", parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        await update.message.reply_text("⚠️ Kullanım: <code>/bakiye_ekle ID TUTAR</code>", parse_mode="HTML")

async def admin_update_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        track_code = context.args[0].upper()
        percent = context.args[1]
        orders = load_json(ORDERS_FILE)
        if track_code in orders:
            orders[track_code]["percent"] = percent
            orders[track_code]["status_text"] = f"İşlem Devam Ediyor (%{percent})"
            save_json(ORDERS_FILE, orders)
            await update.message.reply_text(f"✅ <code>{track_code}</code> %{percent} yapıldı.", parse_mode="HTML")
            try:
                await context.bot.send_message(chat_id=orders[track_code]["user_id"], text=f"🔄 Siparişiniz %{percent} seviyesine ulaştı.", parse_mode="HTML")
            except Exception:
                pass
    except Exception:
        await update.message.reply_text("⚠️ Kullanım: <code>/durum CHW-12345 50</code>", parse_mode="HTML")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    if not msg:
        return
    users = load_json(DATA_FILE)
    success = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 <b>DUYURU:</b> {msg}", parse_mode="HTML")
            success += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ {success} kişiye atıldı.", parse_mode="HTML")

async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_uid = context.args[0]
        banned = load_json(BANNED_FILE)
        banned[str(target_uid)] = True
        save_json(BANNED_FILE, banned)
        await update.message.reply_text(f"🚫 {target_uid} banlandı.", parse_mode="HTML")
    except Exception:
        pass

async def admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_uid = context.args[0]
        banned = load_json(BANNED_FILE)
        if str(target_uid) in banned:
            del banned[str(target_uid)]
            save_json(BANNED_FILE, banned)
            await update.message.reply_text(f"✅ {target_uid} ban kaldırıldı.", parse_mode="HTML")
    except Exception:
        pass

async def admin_add_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        code = context.args[0].upper()
        amount = int(context.args[1])
        limit = int(context.args[2])
        coupons = load_json(COUPONS_FILE)
        coupons[code] = {"amount": amount, "limit": limit, "used_by": []}
        save_json(COUPONS_FILE, coupons)
        await update.message.reply_text(f"🎟 <code>{code}</code> kuponu oluşturuldu.", parse_mode="HTML")
    except Exception:
        pass

# --- UYGULAMA BAŞLATICI ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    target_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_target_info, pattern="^proceed_target$")],
        states={
            WAITING_TARGET_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_info)],
            WAITING_DEKONT: [MessageHandler(filters.PHOTO, receive_dekont)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )

    promo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_use_promo, pattern="^use_promo$")],
        states={WAITING_PROMO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo)]},
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )

    tracking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_track_order, pattern="^track_order$")],
        states={WAITING_TRACKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_track_code)]},
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("bakiye_ekle", admin_add_balance))
    app.add_handler(CommandHandler("durum", admin_update_status))
    app.add_handler(CommandHandler("duyuru", admin_broadcast))
    app.add_handler(CommandHandler("ban", admin_ban_user))
    app.add_handler(CommandHandler("unban", admin_unban_user))
    app.add_handler(CommandHandler("addcoupon", admin_add_coupon))

    app.add_handler(target_conv)
    app.add_handler(promo_conv)
    app.add_handler(tracking_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
