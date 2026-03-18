# scheduler.py — Zamanlayıcı modülü
# APScheduler ile belirli aralıklarla tüm tokenları kontrol eder.
# interval_minutes değeri config.json'dan okunur.

import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from tracker import check_token
from notifier import send_alert, send_error_message


def _check_all_tokens(tokens: list, bot_token: str, chat_id: str):
    """
    Tüm token'ları sırayla kontrol et.
    Alert oluşanları Telegram'a gönder.
    """
    print(f"\n[SCHEDULER] --- Kontrol döngüsü başladı ({len(tokens)} token) ---")

    for token_config in tokens:
        try:
            alert = check_token(token_config)
            if alert:
                send_alert(bot_token, chat_id, alert)
        except Exception as e:
            error_msg = f"{token_config['name']}: {str(e)}"
            print(f"[SCHEDULER] Token kontrol hatası — {error_msg}")
            try:
                send_error_message(bot_token, chat_id, error_msg)
            except Exception:
                pass  # Hata bildiriminde de hata olursa sessizce geç

        # API rate limit'e takılmamak için token'lar arası kısa bekleme
        time.sleep(2)

    print("[SCHEDULER] --- Kontrol döngüsü tamamlandı ---\n")


def start_scheduler(config: dict):
    """
    Zamanlayıcıyı başlat ve çalışır tut.
    config.json'daki interval_minutes değerini kullanır.
    """
    tokens = config["tokens"]
    interval = config.get("interval_minutes", 5)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    print(f"[SCHEDULER] Zamanlayıcı başlatılıyor — {interval} dakika aralıkla.")

    # İlk çalıştırma: Hemen kontrol et
    print("[SCHEDULER] İlk kontrol başlatılıyor...")
    _check_all_tokens(tokens, bot_token, chat_id)

    # APScheduler ile periyodik kontrol
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=_check_all_tokens,
        trigger=IntervalTrigger(minutes=interval),
        args=[tokens, bot_token, chat_id],
        id="token_check",
        name="Token Fiyat Kontrolü",
        replace_existing=True,
        max_instances=1  # Aynı anda birden fazla çalışmayı engelle
    )

    scheduler.start()
    print(f"[SCHEDULER] Zamanlayıcı aktif — her {interval} dakikada bir kontrol yapılacak.")
    
    return scheduler
