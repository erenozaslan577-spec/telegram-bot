import logging
import json
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging yapılandırması
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Konfigürasyon (Token ve Admin Bilgileri)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8674816242:AAEPviDpFQxP2dCWGzB0BGg6ZAcNqQI8YT0")
ADMIN_USERNAME = "@kralinarest"
ADMIN_ID = 8674816242
BOT_USERNAME = "ChiwasIslemBot"

DATA_FILE = "users_data.json"
REFERRAL_REWARD = 40

# --- VERİTABANI İŞLEMLERİ ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Data okuma hatasi: {e}")
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

# --- USER KOMUTLARI ---
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
                            text=f"🎉 TEBRİKLER!\nBir arkadaşınız davetinizle bota katıldı.\n🎁 Hesabınıza +40 TL referans bakiyesi eklendi!"
                        )
                    except Exception:
                        pass
                    await notify_admin(context, f"🎁 REFERANS KAZANCI!\nDavet Eden ID: {inviter_id}\nKatılan: {user.first_name} (@{user.username})")
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

# --- ADMINISTRATIVE KOMUTLAR ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    admin_text = (
        "👑 **CHIWAS YÖNETİCİ PANELİ**\n"
        "-----------------------------------------\n"
        "Sistem üzerinde kullanabileceğiniz yönetici komutları:\n\n"
        "📊 `/istatistik` - Genel sistem istatistiklerini gösterir.\n"
        "📢 `/duyuru <mesaj>` - Tüm kullanıcılara toplu duyuru gönderir.\n"
        "💳 `/bakiye_ekle <user_id> <miktar>` - Kullanıcıya bakiye ekler.\n"
        "🔻 `/bakiye_sil <user_id> <miktar>` - Kullanıcıdan bakiye düşer.\n"
        "🔍 `/kullanici <user_id>` - Kullanıcı detaylarını gösterir.\n"
    )
    await update.message.reply_text(admin_text, parse_mode="Markdown")

async def admin_istatistik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    all_data = load_data()
    total_users = len(all_data)
    total_balance = sum(u.get("balance", 0) for u in all_data.values())
    total_invited = sum(u.get("invited_count", 0) for u in all_data.values())
    total_orders = sum(len(u.get("history", [])) for u in all_data.values())

    msg = (
        f"📊 **CHIWAS BOT İSTATİSTİKLERİ**\n"
        f"-----------------------------------------\n"
        f"👤 Toplam Kayıtlı Kullanıcı: `{total_users}`\n"
        f"💰 Sistemdeki Toplam Bakiye: `{total_balance} TL`\n"
        f"👥 Toplam Davet Edilen Kullanıcı: `{total_invited}`\n"
        f"🛒 Toplam Tamamlanan Sipariş: `{total_orders}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_duyuru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: `/duyuru <Gönderilecek Mesaj>`", parse_mode="Markdown")
        return

    broadcast_msg = " ".join(context.args)
    all_data = load_data()
    success_count = 0
    fail_count = 0

    await update.message.reply_text("🚀 Duyuru gönderimi başlatıldı...")

    for uid in all_data.keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 **CHIWAS VIP RESMİ DUYURU**\n-----------------------------------------\n\n{broadcast_msg}",
                parse_mode="Markdown"
            )
            success_count += 1
            time.sleep(0.05)  # Telegram API limitlerine takılmamak için
        except Exception:
            fail_count += 1

    await update.message.reply_text(
        f"✅ **Duyuru Gönderimi Tamamlandı!**\n\n"
        f"Başarılı: `{success_count}`\n"
        f"Başarısız/Engellemiş: `{fail_count}`",
        parse_mode="Markdown"
    )

async def admin_bakiye_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Kullanım: `/bakiye_ekle <user_id> <miktar>`", parse_mode="Markdown")
        return

    target_id, amount_str = context.args[0], context.args[1]
    try:
        amount = int(amount_str)
        all_data = load_data()
        if target_id in all_data:
            all_data[target_id]["balance"] = all_data[target_id].get("balance", 0) + amount
            save_data(all_data)
            await update.message.reply_text(f"✅ `{target_id}` kullanıcısına **+{amount} TL** bakiye eklendi.")
            try:
                await context.bot.send_message(chat_id=int(target_id), text=f"🎁 Hesabınıza **+{amount} TL** bakiye tanımlandı!")
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ Kullanıcı bulunamadı.")
    except ValueError:
        await update.message.reply_text("⚠️ Miktar geçerli bir sayı olmalıdır.")

async def admin_bakiye_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Kullanım: `/bakiye_sil <user_id> <miktar>`", parse_mode="Markdown")
        return

    target_id, amount_str = context.args[0], context.args[1]
    try:
        amount = int(amount_str)
        all_data = load_data()
        if target_id in all_data:
            current_bal = all_data[target_id].get("balance", 0)
            all_data[target_id]["balance"] = max(0, current_bal - amount)
            save_data(all_data)
            await update.message.reply_text(f"✅ `{target_id}` kullanıcısından **-{amount} TL** bakiye düşüldü.")
        else:
            await update.message.reply_text("❌ Kullanıcı bulunamadı.")
    except ValueError:
        await update.message.reply_text("⚠️ Miktar geçerli bir sayı olmalıdır.")

async def admin_kullanici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: `/kullanici <user_id>`", parse_mode="Markdown")
        return

    target_id = context.args[0]
    all_data = load_data()
    if target_id in all_data:
        u = all_data[target_id]
        history_text = "\n".join([f"• {item}" for item in u.get("history", [])]) if u.get("history") else "Sipariş yok."
        text = (
            f"👤 **KULLANICI BİLGİSİ (`{target_id}`)**\n"
            f"-----------------------------------------\n"
            f"💰 Bakiye: `{u.get('balance', 0)} TL`\n"
            f"👥 Davet Sayısı: `{u.get('invited_count', 0)}` \n\n"
            f"📜 Sipariş Geçmişi:\n{history_text}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Kullanıcı veritabanında bulunamadı.")

# --- CALLBACK BUTON İŞLEMLERİ ---
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
        text = "🥳 VIP TARİFE VE İNDİRİM TABLOSU\n-----------------------------------------\nİstediğiniz hizmetlerin üzerine tıklayarak sepete ekleyebilirsiniz."
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
            f"💡 Bu linki arkadaşlarınıza göndererek her katılan kişi için +40 TL indirim kazan
