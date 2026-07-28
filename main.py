import logging
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "8674816242:AAEmyovk_71NPXva4ejaYmHrHPSdaeFIc_8"
ADMIN_USERNAME = "@kralinarest"
ADMIN_ID = 8674816242
BOT_USERNAME = "ChiwasIslemBot"

DATA_FILE = "users_data.json"
REFERRAL_REWARD = 40

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Save hatasi: {e}")

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "balance": 0,
            "invited_count": 0,
            "history": []
        }
        save_data(data)
    return data[uid]

def update_user_data(user_id, key, value):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        get_user_data(user_id)
        data = load_data()
    data[uid][key] = value
    save_data(data)

SERVICES = [
    "1. Tel No ile Tel Cokertme",
    "2. Kameraya Sizna",
    "3. Canli Konum Takibi",
    "4. Instagram Hesap Calma",
    "5. Ihbar Atma (EGM / Jandarma)",
    "6. Instagram Hesap Acma",
    "7. Deepfake Hizmeti",
    "8. Galeriye Sizna",
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

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logging.error(f"Admin hatasi: {e}")

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Hizmet Seç & Sepet Oluştur", callback_data="select_services")],
        [InlineKeyboardButton("💳 Bakiye / Ödeme Yap", callback_data="purchase"), InlineKeyboardButton("📜 Hizmet Rehberi & Detaylar", callback_data="catalog")],
        [InlineKeyboardButton("🎁 Referans / Arkadaşını Getir", callback_data="referral"), InlineKeyboardButton("🛡 Güvenlik & Garanti", callback_data="guarantee"), InlineKeyboardButton("💬 Müşteri Yorumları", callback_data="reviews")],
        [InlineKeyboardButton("👤 Profilim & Geçmiş", callback_data="profile"), InlineKeyboardButton("❓ SSS & Bilgi", callback_data="faq")],
        [InlineKeyboardButton("💬 Canlı Destek & İletişim", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ])

def get_welcome_text(first_name):
    return (
        f"👑 CHIWAS VIP SERVICES - RESMI OTOMASYON BOTU\n"
        f"-----------------------------------------\n"
        f"👋 Hoş Geldiniz, Sayın {first_name}!\n\n"
        f"🔒 %100 Anonimlik & Uçtan Uca Şifreli Hizmet\n"
        f"🛡 Sistemimiz üzerinden yapacağınız tüm işlemler güvence altındadır.\n\n"
        f"🔥 GÜNCEL FIRSAT: 3 ve üzeri işlem alımlarında VIP indirim!\n"
        f"🎁 ARKADAŞINI GETİR: Davet ettiğin her arkadaşın için anında +40 TL İndirim Bakiyesi kazan!\n"
        f"📊 Sistem İstatistikleri:\n"
        f"• Tamamlanan İşlem: 1,420+\n"
        f"• Müşteri Memnuniyeti: %99.8\n"
        f"• Aktif Temsilci: {ADMIN_USERNAME}\n\n"
        f"👇 İşlem yapmak için aşağıdaki menüyü kullanabilirsiniz:"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u_data = get_user_data(user.id)
    context.user_data['cart'] = set()
    context.user_data['express'] = False

    if context.args and len(context.args) > 0:
        ref_code = context.args[0]
        try:
            inviter_id = ref_code.replace("CHW-", "")
            if inviter_id != str(user.id):
                all_data = load_data()
                if inviter_id in all_data and f"ref_{user.id}" not in u_data:
                    inviter_data = all_data[inviter_id]
                    inviter_data["balance"] = inviter_data.get("balance", 0) + REFERRAL_REWARD
                    inviter_data["invited_count"] = inviter_data.get("invited_count", 0) + 1
                    save_data(all_data)
                    update_user_data(user.id, f"ref_{user.id}", True)
                    try:
                        await context.bot.send_message(
                            chat_id=int(inviter_id),
                            text=f"🎉 TEBRİKLER!\nBir arkadaşınız davetinizle bota katıldı.\n🎁 REFERANS KAZANCI! Davet Eden: {inviter_id}"
                        )
                    except Exception:
                        pass
                    await notify_admin(context, f"🎁 REFERANS KAZANCI!\nDavet Eden: {inviter_id}\nKatılan: {user.first_name} (@{user.username})")
        except Exception as e:
            logging.error(f"Referans hatasi: {e}")

    await update.message.reply_text(get_welcome_text(user.first_name), reply_markup=get_main_keyboard())

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

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    u_data = get_user_data(user.id)

    if 'cart' not in context.user_data:
        context.user_data['cart'] = set()
    if 'express' not in context.user_data:
        context.user_data['express'] = False

    cart = context.user_data['cart']
    express = context.user_data['express']
    data = query.data

    if data == "select_services":
        text = "🥳 VIP TARİFE VE İNDİRİM TABLOSU\n-----------------------------------------\n1 İşlem: 1000 TL..."
        await query.edit_message_text(text=text, reply_markup=build_service_keyboard(cart, express))

    elif data == "toggle_express":
        context.user_data['express'] = not context.user_data['express']
        express = context.user_data['express']
        count = len(cart)
        price_tl = calculate_price(count, express)
        text = f"🛠 HİZMET SEÇİM MENÜSÜ\n-----------------------------------------\n📊 Seçilen İşlem Adedi: {count}\n💰 Toplam Tutar: {price_tl} TL"
        await query.edit_message_text(text=text, reply_markup=build_service_keyboard(cart, express))

    elif data == "select_all":
        context.user_data['cart'] = set(range(len(SERVICES)))
        count = len(context.user_data['cart'])
        price_tl = calculate_price(count, express)
        text = f"🛠 HİZMET SEÇİM MENÜSÜ\n-----------------------------------------\n📊 Seçilen İşlem Adedi: {count}\n💰 Toplam Tutar: {price_tl} TL"
        await query.edit_message_text(text=text, reply_markup=build_service_keyboard(context.user_data['cart'], express))

    elif data == "select_none":
        context.user_data['cart'] = set()
        text = f"🛠 HİZMET SEÇİM MENÜSÜ\n-----------------------------------------\n📊 Seçilen İşlem Adedi: 0\n💰 Toplam Tutar: 0 TL"
        await query.edit_message_text(text=text, reply_markup=build_service_keyboard(context.user_data['cart'], express))

    elif data.startswith("toggle_"):
        idx = int(data.split("_")[1])
        if idx in cart:
            cart.remove(idx)
        else:
            cart.add(idx)
        count = len(cart)
        price_tl = calculate_price(count, express)
        text = f"🛠 HİZMET SEÇİM MENÜSÜ\n-----------------------------------------\n📊 Seçilen İşlem Adedi: {count}\n💰 Toplam Tutar: {price_tl} TL"
        await query.edit_message_text(text=text, reply_markup=build_service_keyboard(cart, express))

    elif data in ["checkout", "purchase"]:
        count = len(cart)
        base_price = calculate_price(count, express) if count > 0 else 1000
        user_bal = u_data.get("balance", 0)
        final_price = max(0, base_price - user_bal)
        used_discount = base_price - final_price

        selected_services_list = [SERVICES[i] for i in cart]
        selected_text = ""
        if count > 0:
            selected_text = "<b>🛒 Seçilen Hizmetler:</b>\n" + "\n".join([f"• {s}" for s in selected_services_list]) + "\n"
            if express:
                selected_text += "🚀 <b>VIP Express Hızlı İşlem Eklendi (+300 TL)</b>\n"
            selected_text += "\n"

        discount_text = f"🎁 <b>Referans İndirimi:</b> -{used_discount} TL\n" if used_discount > 0 else ""

        text = (
            f"💎 <b>ÖDEME YÖNTEMİ SEÇİN</b>\n"
            f"-----------------------------------------\n"
            f"{selected_text}"
            f"💵 <b>Tutar:</b> {base_price} TL\n"
            f"{discount_text}"
            f"💳 <b>ÖDENECEK NET TUTAR:</b> {final_price} TL\n\n"
            f"💳 <b>İBAN İLE ÖDEME</b> <i>(Kopyalamak için üzerlerine dokunun)</i>\n"
            f"🏦 <b>İBAN:</b> <code>TR100006200091000006969709</code>\n"
            f"👤 <b>Alıcı:</b> <code>Garanti Odeme ve Elektronik Para Hizmetleri A.Ş.</code>\n"
            f"📌 <b>Açıklama:</b> <code>TAMI7786986257878012</code>\n\n"
            f"📌 Ödemenizi tamamladıktan sonra aşağıdaki butona tıklayın."
        )

        if count > 0:
            order_summary = f"{count} İşlem ({final_price} TL)"
            history = u_data.get("history", [])
            history.append(order_summary)
            update_user_data(user.id, "history", history)
            admin_msg = f"🚨 YENİ SİPARİŞ!\n👤 Müşteri: {user.first_name} (@{user.username}) \n🆔 ID: {user.id}\n🛒 Sepet:\n" + "\n".join(selected_services_list) + f"\n💰 Tutar: {final_price} TL"
            await notify_admin(context, admin_msg)

        keyboard = [
            [InlineKeyboardButton("✅ Ödemeyi Gönderdim", callback_data="sent")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "track":
        history = u_data.get('history', [])
        if history:
            status_text = "🔎 CANLI SİPARİŞ TAKİP PANELİ\n-----------------------------------------\n" + "\n".join([f"• {item}" for item in history])
        else:
            status_text = "🔎 CANLI SİPARİŞ TAKİP PANELİ\n-----------------------------------------\n⚠️ Henüz aktif bir siparişiniz bulunmamaktadır."
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=status_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "catalog":
        text = "📜 HİZMET KATALOĞU VE DETAYLARI\n-----------------------------------------\n\n"
        for idx, name in enumerate(SERVICES):
            text += f"• <b>{name}</b>\nℹ️ {SERVICE_DETAILS[idx]}\n\n"
        keyboard = [[InlineKeyboardButton("🛠 Hemen Hizmet Seç", callback_data="select_services")], [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "referral":
        ref_code = f"CHW-{user.id}"
        ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
        invited_count = u_data.get("invited_count", 0)
        balance = u_data.get("balance", 0)
        text = (
            f"🎁 REFERANS VE ARKADAŞINI GETİR SİSTEMİ\n-----------------------------------------\n"
            f"👤 Toplam Davet Ettiğiniz Kullanıcı: {invited_count}\n"
            f"💰 Kazanılan İndirim Bakiyesi: {balance} TL\n\n"
            f"🔗 Özel Davet Bağlantınız:\n`{ref_link}`\n\n"
            f"💡 Bu linki arkadaşlarınıza göndererek her katılan kişi için +40 TL indirim kazanın!"
        )
        share_url = f"https://t.me/share/url?url={ref_link}&text=VIP%20İşlem%20Botu!"
        keyboard = [
            [InlineKeyboardButton("🚀 Davet Linkini Arkadaşına Gönder", url=share_url)],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "vip_contact":
        text = f"👑 VIP ÖZEL MÜŞTERİ TALEBİ\n-----------------------------------------\nÖzel projeleriniz ve yüksek bütçeli işlemleriniz için VIP Temsilcimiz ile iletişime geçebilirsiniz."
        keyboard = [[InlineKeyboardButton("💬 VIP Temsilciye Yaz", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")], [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "guarantee":
        text = "🛡 GÜVENLİK VE GARANTİ PROTOKOLÜ\n-----------------------------------------\n1. %100 Gizlilik Garantisi\n2. İade Hakkı\n3. Anlık İşlem Desteği"
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "reviews":
        text = "⭐ MÜŞTERİ GERİ BİLDİRİMLERİ\n-----------------------------------------\n👨‍💻 M.K.: ⭐⭐⭐⭐⭐ Mükemmel hızlı işlem!"
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "profile":
        history_list = u_data.get('history', [])
        history_text = "\n".join([f"• {item}" for item in history_list]) if history_list else "Henüz sipariş yok."
        text = f"👤 MÜŞTERİ PROFİL BİLGİLERİ\n-----------------------------------------\n🆔 Müşteri ID: {user.id}\n💰 Bakiye: {u_data.get('balance', 0)} TL\n📜 Sipariş Geçmişi:\n{history_text}"
        keyboard = [[InlineKeyboardButton("💳 Bakiye Yükle / Öde", callback_data="purchase")], [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "faq":
        text = "❓ SIKÇA SORULAN SORULAR\n-----------------------------------------\n📌 İşlem süresi ne kadar?\nİşlemleriniz sıraya alınır ve en kısa sürede tamamlanır."
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "sent":
        text = f"📩 ÖDEME BİLDİRİMİNİZ ALINDI\n-----------------------------------------\nLütfen dekontunuzu doğrudan VIP Temsilcimize iletiniz."
        await notify_admin(context, f"💰 ÖDEME BİLDİRİMİ!\nMüşteri: {user.first_name} (@{user.username})\nID: {user.id}")
        keyboard = [[InlineKeyboardButton("💬 Dekontu Temsilciye Gönder", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")], [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_main":
        await query.edit_message_text(text=get_welcome_text(user.first_name), reply_markup=get_main_keyboard())

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    print("Bot sorunsuz baslatildi...")
    app.run_polling()

if __name__ == "__main__":
    while True:
        try:
            run_bot()
        except Exception as e:
            logging.error(f"Bot baglantisi koptu/hata aldi: {e}. 10 saniye sonra tekrar deneniyor...")
            time.sleep(10)
