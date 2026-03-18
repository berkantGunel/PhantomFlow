# tracker.py — Fiyat değişim hesaplama ve eşik kontrolü
# Son fiyatla karşılaştırma yaparak alert oluşturur.

from typing import Optional

from db import get_last_price, save_price
from fetcher import fetch_token_data


def check_token(token_config: dict) -> Optional[dict]:
    """
    Tek bir token'ı kontrol et.

    İşlem sırası:
    1. DexScreener'dan güncel veriyi çek
    2. DB'den son kaydedilen fiyatı al
    3. Yüzde değişimi hesapla
    4. Eşik aşıldıysa alert dict'i döndür
    5. Fiyatı DB'ye kaydet

    Args:
        token_config: config.json'daki token objesi
            - name: Token adı
            - ca: Contract address
            - alert_up: Yükseliş eşiği (%)
            - alert_down: Düşüş eşiği (%)

    Returns:
        Alert dict'i veya None (eşik aşılmadıysa / hata varsa)
    """
    name = token_config["name"]
    ca = token_config["ca"]
    alert_up = token_config.get("alert_up", 5)
    alert_down = token_config.get("alert_down", 5)

    # 1. Güncel veriyi çek
    data = fetch_token_data(ca)
    if data is None:
        print(f"[TRACKER] {name}: Veri alınamadı, atlanıyor.")
        return None

    current_price = data["price_usd"]
    if current_price <= 0:
        print(f"[TRACKER] {name}: Geçersiz fiyat ({current_price}), atlanıyor.")
        return None

    # 2. DB'den son fiyatı al
    last_price = get_last_price(ca)

    # 3. Fiyatı DB'ye kaydet (her durumda)
    save_price(ca, name, current_price)

    # 4. İlk çalışma kontrolü — DB boşsa sadece kaydet, alert gönderme
    if last_price is None:
        print(f"[TRACKER] {name}: İlk kayıt yapıldı — ${format_price(current_price)}")
        return None

    # 5. Yüzde değişim hesapla
    percent_change = ((current_price - last_price) / last_price) * 100

    # 6. Eşik kontrolü
    if percent_change >= alert_up:
        # Yükseliş alert'i
        return _build_alert(
            name=name,
            ca=ca,
            direction="up",
            current_price=current_price,
            percent_change=percent_change,
            data=data
        )
    elif percent_change <= -alert_down:
        # Düşüş alert'i
        return _build_alert(
            name=name,
            ca=ca,
            direction="down",
            current_price=current_price,
            percent_change=percent_change,
            data=data
        )

    # Eşik aşılmadı
    print(f"[TRACKER] {name}: ${format_price(current_price)} (Değişim: {percent_change:+.2f}%) — Eşik aşılmadı.")
    return None


def _build_alert(name: str, ca: str, direction: str, current_price: float,
                 percent_change: float, data: dict) -> dict:
    """Alert bilgilerini içeren dict oluştur."""
    return {
        "name": name,
        "ca": ca,
        "direction": direction,
        "price_usd": current_price,
        "percent_change": percent_change,
        "price_change_1h": data["price_change_1h"],
        "price_change_24h": data["price_change_24h"],
        "volume_24h": data["volume_24h"],
        "liquidity_usd": data["liquidity_usd"],
        "dex_url": data["dex_url"]
    }


def format_price(price: float) -> str:
    """
    Fiyatı okunabilir formatta döndür.
    Çok küçük fiyatlar için bilimsel gösterim yerine tam gösterim kullanır.
    """
    if price >= 1:
        return f"{price:,.4f}"
    elif price >= 0.0001:
        return f"{price:.6f}"
    else:
        # Çok küçük fiyatlar için (meme coin'ler)
        return f"{price:.10f}"
