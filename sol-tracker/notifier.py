# notifier.py — Telegram bildirim gönderme
# python-telegram-bot kütüphanesi (async, v20+) kullanır.
# Hata olursa botu durdurmaz, sadece hata loglar.

import asyncio
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode

from tracker import format_price


def send_alert(bot_token: str, chat_id: str, alert: dict):
    """
    Alert bilgisini Telegram'a gönder.
    Senkron wrapper — async fonksiyonu çağırır.
    """
    try:
        asyncio.run(_send_alert_async(bot_token, chat_id, alert))
    except RuntimeError:
        # Zaten çalışan bir event loop varsa (APScheduler içinde olabilir)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_send_alert_async(bot_token, chat_id, alert))
        else:
            loop.run_until_complete(_send_alert_async(bot_token, chat_id, alert))
    except Exception as e:
        print(f"[NOTIFIER] Alert gönderme hatası: {e}")


async def _send_alert_async(bot_token: str, chat_id: str, alert: dict):
    """Telegram'a alert mesajı gönder (async)."""
    try:
        bot = Bot(token=bot_token)

        # Yön simgesi ve başlık
        if alert["direction"] == "up":
            emoji = "🚀"
            direction_text = "YÜKSELDİ"
        else:
            emoji = "🔻"
            direction_text = "DÜŞTÜ"

        # Fiyat ve değişim formatla
        price_str = format_price(alert["price_usd"])
        change_str = f"{alert['percent_change']:+.2f}%"

        # 1 saatlik ve 24 saatlik değişim
        change_1h = f"{alert['price_change_1h']:+.1f}%"
        change_24h = f"{alert['price_change_24h']:+.1f}%"

        # Likidite ve hacim formatla
        liquidity_str = _format_number(alert["liquidity_usd"])
        volume_str = _format_number(alert["volume_24h"])

        # Zaman damgası
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Mesaj oluştur
        message = (
            f"{emoji} <b>{alert['name']} {direction_text}!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Fiyat: <code>${price_str}</code>\n"
            f"📈 Değişim: <b>{change_str}</b>\n"
            f"⏱ 1s: {change_1h}  |  24s: {change_24h}\n"
            f"💧 Likidite: ${liquidity_str}\n"
            f"📦 Hacim 24s: ${volume_str}\n"
            f"🔗 <a href=\"{alert['dex_url']}\">Phantom'da Görüntüle</a>\n"
            f"⏰ {timestamp}"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        print(f"[NOTIFIER] Alert gönderildi: {alert['name']} {direction_text}")

    except Exception as e:
        print(f"[NOTIFIER] Telegram mesaj gönderme hatası: {e}")


def send_startup_message(bot_token: str, chat_id: str, token_count: int):
    """Bot başladığında Telegram'a bilgi mesajı gönder."""
    try:
        asyncio.run(_send_startup_async(bot_token, chat_id, token_count))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_send_startup_async(bot_token, chat_id, token_count))
        else:
            loop.run_until_complete(_send_startup_async(bot_token, chat_id, token_count))
    except Exception as e:
        print(f"[NOTIFIER] Başlangıç mesajı gönderme hatası: {e}")


async def _send_startup_async(bot_token: str, chat_id: str, token_count: int):
    """Başlangıç mesajını Telegram'a gönder (async)."""
    try:
        bot = Bot(token=bot_token)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = (
            f"✅ <b>Bot başlatıldı!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 {token_count} token takip ediliyor\n"
            f"⏰ {timestamp}"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
        print("[NOTIFIER] Başlangıç mesajı gönderildi.")
    except Exception as e:
        print(f"[NOTIFIER] Başlangıç mesajı hatası: {e}")


def send_error_message(bot_token: str, chat_id: str, error_text: str):
    """Hata durumunda Telegram'a bildirim gönder."""
    try:
        asyncio.run(_send_error_async(bot_token, chat_id, error_text))
    except Exception as e:
        print(f"[NOTIFIER] Hata mesajı gönderme hatası: {e}")


async def _send_error_async(bot_token: str, chat_id: str, error_text: str):
    """Hata mesajını Telegram'a gönder (async)."""
    try:
        bot = Bot(token=bot_token)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = (
            f"⚠️ <b>Bot Hatası</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"❌ {error_text}\n"
            f"⏰ {timestamp}"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"[NOTIFIER] Hata bildirimi gönderme hatası: {e}")


def _format_number(value: float) -> str:
    """Büyük sayıları okunabilir formatta göster (ör: 1.2M, 45.2K)."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:,.1f}K"
    else:
        return f"{value:,.0f}"
