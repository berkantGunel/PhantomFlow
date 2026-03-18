# main.py — Solana Token Tracker Bot giriş noktası
# Config'i yükler, DB'yi başlatır, Telegram'a bilgi gönderir ve zamanlayıcıyı başlatır.

import json
import os
import sys

from db import init_db
from notifier import send_startup_message
from scheduler import start_scheduler


def load_config() -> dict:
    """
    config.json dosyasını yükle ve doğrula.
    Dosya bulunamazsa veya hatalıysa programı durdurur.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    if not os.path.exists(config_path):
        print("[HATA] config.json bulunamadı!")
        print(f"       Beklenen konum: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[HATA] config.json geçersiz JSON formatı: {e}")
        sys.exit(1)

    # Zorunlu alanları kontrol et
    if "tokens" not in config or not config["tokens"]:
        print("[HATA] config.json'da 'tokens' listesi boş veya eksik!")
        sys.exit(1)

    if "telegram" not in config:
        print("[HATA] config.json'da 'telegram' ayarları eksik!")
        sys.exit(1)

    telegram = config["telegram"]
    if not telegram.get("bot_token") or telegram["bot_token"] == "BOT_TOKEN_BURAYA":
        print("[HATA] Telegram bot_token ayarlanmamış!")
        print("       config.json'daki 'bot_token' alanını doldurun.")
        sys.exit(1)

    if not telegram.get("chat_id") or telegram["chat_id"] == "CHAT_ID_BURAYA":
        print("[HATA] Telegram chat_id ayarlanmamış!")
        print("       config.json'daki 'chat_id' alanını doldurun.")
        sys.exit(1)

    # Token'ları doğrula
    for i, token in enumerate(config["tokens"]):
        if not token.get("ca") or token["ca"] == "SOLANA_CONTRACT_ADDRESS":
            print(f"[HATA] Token #{i+1}: Contract address (ca) ayarlanmamış!")
            sys.exit(1)
        if not token.get("name") or token["name"] == "TOKEN_ADI":
            print(f"[UYARI] Token #{i+1}: İsim verilmemiş, CA adresi kullanılacak.")
            token["name"] = token["ca"][:12] + "..."

        # Varsayılan eşik değerleri
        token.setdefault("alert_up", 5)
        token.setdefault("alert_down", 5)

    config.setdefault("interval_minutes", 5)

    return config


def main():
    """Ana fonksiyon — botu başlatır."""
    print("=" * 50)
    print("  🔍 Solana Token Tracker Bot")
    print("=" * 50)

    # 1. Config'i yükle
    print("\n[1/4] Config yükleniyor...")
    config = load_config()
    token_count = len(config["tokens"])
    interval = config["interval_minutes"]
    print(f"       ✓ {token_count} token bulundu")
    print(f"       ✓ Kontrol aralığı: {interval} dakika")

    # 2. Veritabanını başlat
    print("\n[2/4] Veritabanı başlatılıyor...")
    init_db()
    print("       ✓ Veritabanı hazır")

    # 3. Takip edilen token'ları listele
    print("\n[3/4] Takip edilen token'lar:")
    for token in config["tokens"]:
        print(f"       • {token['name']} — ↑{token['alert_up']}% / ↓{token['alert_down']}%")

    # 4. Telegram'a başlangıç mesajı gönder
    print("\n[4/4] Telegram'a başlangıç mesajı gönderiliyor...")
    import os
    from dotenv import load_dotenv
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    send_startup_message(bot_token, chat_id, token_count)

    # 5. Zamanlayıcıyı başlat
    print("\n" + "=" * 50)
    print("  ✅ Bot aktif! Çıkmak için Ctrl+C")
    print("=" * 50 + "\n")
    scheduler = start_scheduler(config)
    
    # 6. Telegram İnteraktif Botu Başlat (ana threadi bloke eder)
    from telegram_handler import run_telegram_bot
    try:
        run_telegram_bot(bot_token)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\n[MAIN] Bot tamamen durduruldu.")

if __name__ == "__main__":
    main()
