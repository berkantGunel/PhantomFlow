import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from fetcher import fetch_token_data
from tracker import format_price

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "bot.log")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def is_authorized(update: Update) -> bool:
    """Sadece bizim izin verdiğimiz (config'teki) grupta çalışmasını sağlayan güvenlik kilidi"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return str(update.effective_chat.id) == str(os.getenv("TELEGRAM_CHAT_ID"))

def format_number(value: float) -> str:
    """Büyük sayıları okunabilir formata çevirir"""
    if value >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:,.1f}K"
    return f"{value:,.0f}"

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    text = (
        "🤖 <b>PhantomFlow İnteraktif Bot</b>\n\n"
        "Kullanabileceğiniz komutlar:\n"
        "📊 /fiyat - Anlık fiyatları göster\n"
        "📋 /liste - Takip edilenleri listele\n"
        "➕ /ekle CA_ADRESI - Yeni token ekle\n"
        "❌ /sil SIRA_NO - Token sil\n"
        "📄 /log - Son bot loglarını göster"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def fiyat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    config = load_config()
    if not config["tokens"]:
        await update.message.reply_text("Hiç token takip edilmiyor.\n\n💡 <i>Yeni bir token eklemek için:</i>\n<code>/ekle CA_ADRESI</code>", parse_mode="HTML")
        return
        
    lines = ["📊 <b>Anlık Fiyat & Durum Raporu</b>\n"]
    for t in config["tokens"]:
        data = fetch_token_data(t["ca"])
        if data:
            price_str = format_price(data['price_usd'])
            change_5m = f"{data['price_change_5m']:+.2f}%"
            change_1h = f"{data['price_change_1h']:+.2f}%"
            change_24h = f"{data['price_change_24h']:+.2f}%"
            likidite = format_number(data['liquidity_usd'])
            hacim = format_number(data['volume_24h'])
            link = data['dex_url']
            
            lines.append(f"🔹 <b>{t['name']}</b>")
            lines.append(f"💰 Fiyat: <code>${price_str}</code>")
            lines.append(f"📈 5dk: <b>{change_5m}</b> | 1s: {change_1h} | 24s: {change_24h}")
            lines.append(f"💧 Likidite: ${likidite} | 📦 Hacim: ${hacim}")
            lines.append(f"🔗 <a href=\"{link}\">Phantom'da İşlem Yap</a>\n")
        else:
            lines.append(f"🔹 <b>{t['name']}</b>: Veri alınamadı ⚠️\n")
            
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)

async def liste_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    config = load_config()
    if not config["tokens"]:
        await update.message.reply_text("Takip edilen token yok.\n\n💡 <i>Şununla ekleyebilirsiniz:</i>\n<code>/ekle CA_ADRESI</code>", parse_mode="HTML")
        return
        
    lines = ["📋 <b>Takip Edilen Token'lar</b>\n"]
    for i, t in enumerate(config["tokens"], 1):
        lines.append(f"<b>{i}. {t['name']}</b>")
        lines.append(f"   <code>{t['ca']}</code>")
        
    lines.append("\n💡 <b>İpuçları:</b>")
    lines.append("➕ <i>Yeni coin eklemek için:</i>\n   <code>/ekle CA_ADRESI</code>")
    lines.append("❌ <i>Takipten çıkarmak için:</i>\n   <code>/sil SIRA_NO</code> (Örn: <code>/sil 1</code>)")
    
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def ekle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        await update.message.reply_text("Kullanım: <code>/ekle CA_ADRESI</code>", parse_mode="HTML")
        return
        
    ca = context.args[0]
    config = load_config()
    
    if any(t["ca"].lower() == ca.lower() for t in config["tokens"]):
        await update.message.reply_text("Bu token zaten takipte! ℹ️")
        return
        
    try:
        resp = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{ca}", timeout=10).json()
        pairs = resp.get("pairs", [])
        if not pairs:
            await update.message.reply_text("Token DexScreener'da bulunamadı. Lütfen adresi kontrol edin.")
            return
            
        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        name = pair.get("baseToken", {}).get("symbol", "BILINMIYOR").upper()
        
        config["tokens"].append({
            "name": name,
            "ca": ca,
            "alert_up": 5.0,
            "alert_down": 5.0
        })
        save_config(config)
        await update.message.reply_text(f"✅ <b>{name}</b> başarıyla eklendi!\nFiyat: ${format_price(float(pair.get('priceUsd', 0)))}\n\n<i>Bot arka planda her 5 dakikada bir kontrol edecek. Liste için /liste yazabilirsiniz.</i>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Eklerken bir hata oluştu: {e}")

async def sil_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        await update.message.reply_text("Kullanım: <code>/sil SIRA_NO</code>\nSilinecek numara için önce /liste yazın.", parse_mode="HTML")
        return
        
    try:
        idx = int(context.args[0]) - 1
        config = load_config()
        if 0 <= idx < len(config["tokens"]):
            removed = config["tokens"].pop(idx)
            save_config(config)
            await update.message.reply_text(f"❌ <b>{removed['name']}</b> takipten çıkarıldı ve listeden silindi.\n\nGüncel listeyi /liste ile görebilirsiniz.", parse_mode="HTML")
        else:
            await update.message.reply_text("Listede böyle bir numara yok, kontrol edip tekrar deneyin.")
    except ValueError:
        await update.message.reply_text("Lütfen geçerli bir sayı (rakam) girin.")

async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not os.path.exists(LOG_PATH):
        await update.message.reply_text("Henüz okunacak bir log dosyası oluşmamış.")
        return
        
    with open(LOG_PATH, "r") as f:
        lines = f.readlines()
        
    recent = lines[-20:] # Son 20 satır
    html_log = "".join(recent).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    await update.message.reply_text(f"<pre>{html_log[-3800:]}</pre>", parse_mode="HTML")

async def yardim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    text = (
        "🤖 <b>PhantomFlow Bot - Yardım Menüsü</b>\n\n"
        "Kullanabileceğiniz tüm komutlar ve açıklamaları:\n\n"
        "📊 <b>/fiyat</b>\n"
        "├ Takip edilen tüm tokenların güncel fiyat, değişim yüzdesi, hacim ve likidite bilgilerini anında getirir.\n\n"
        "📋 <b>/liste</b>\n"
        "├ Botun arka planda her 5 dakikada bir kontrol ettiği tokenları sıra numaralarıyla beraber listeler.\n\n"
        "➕ <b>/ekle CA_ADRESI</b>\n"
        "├ Sisteme yeni token eklemenizi sağlar. Contract Address (CA) girmeniz yeterlidir.\n"
        "└ Örn: <code>/ekle 8E4hs...</code>\n\n"
        "❌ <b>/sil SIRA_NO</b>\n"
        "├ Bir tokenı takipten çıkarır. Sıra no için önce /liste komutuna bakabilirsiniz.\n"
        "└ Örn: <code>/sil 1</code> (1. sıradaki tokenı siler)\n\n"
        "📄 <b>/log</b>\n"
        "├ Botun arka plandaki işlemlerini, aldığı hataları ve günlüğünün son 20 satırını ekrana basar.\n\n"
        "💡 <i>Kısa menüyü görmek için /start komutunu kullanabilirsiniz.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

def run_telegram_bot(bot_token: str):
    """Event Loop oluşturup Telegram uygulamasını ayağa kaldırır."""
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
        
    app = ApplicationBuilder().token(bot_token).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("fiyat", fiyat_cmd))
    app.add_handler(CommandHandler("liste", liste_cmd))
    app.add_handler(CommandHandler("ekle", ekle_cmd))
    app.add_handler(CommandHandler("sil", sil_cmd))
    app.add_handler(CommandHandler("log", log_cmd))
    app.add_handler(CommandHandler("yardim", yardim_cmd))
    
    print("\n[TELEGRAM] 📱 Telefından interaktif komut modülü aktif! (/start, /fiyat, /ekle...)")
    app.run_polling()
