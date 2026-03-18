# fetcher.py — DexScreener API'den fiyat verisi çekme
# Ücretsiz API, key gerekmez.
# Hata durumunda None döndürür, botu durdurmaz.

from typing import Optional

import requests

# DexScreener API endpoint'i
DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens/{ca}"

# İstek zaman aşımı (saniye)
REQUEST_TIMEOUT = 15


def fetch_token_data(ca: str) -> Optional[dict]:
    """
    DexScreener API'den token verisini çek.

    Dönüş değeri (dict):
        - price_usd: float — Güncel fiyat (USD)
        - price_change_5m: float — 5 dakikalık değişim (%)
        - price_change_1h: float — 1 saatlik değişim (%)
        - price_change_24h: float — 24 saatlik değişim (%)
        - volume_24h: float — 24 saatlik işlem hacmi (USD)
        - liquidity_usd: float — Toplam likidite (USD)
        - dex_url: str — Phantom üzerinde işlem linki

    Hata durumunda None döndürür.
    """
    try:
        url = DEXSCREENER_URL.format(ca=ca)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()

        # API "pairs" listesi döndürür, en yüksek likiditeye sahip pair'i seç
        pairs = data.get("pairs")
        if not pairs:
            print(f"[FETCHER] Token için pair bulunamadı: {ca[:12]}...")
            return None

        # En yüksek likiditeye sahip pair'i seç
        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))

        # Fiyat değişim verilerini güvenli şekilde al
        price_change = pair.get("priceChange", {})

        result = {
            "price_usd": float(pair.get("priceUsd", 0) or 0),
            "price_change_5m": float(price_change.get("m5", 0) or 0),
            "price_change_1h": float(price_change.get("h1", 0) or 0),
            "price_change_24h": float(price_change.get("h24", 0) or 0),
            "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
            "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
            "dex_url": f"https://trade.phantom.com/token/{ca}"
        }

        return result

    except requests.exceptions.Timeout:
        print(f"[FETCHER] Zaman aşımı hatası: {ca[:12]}...")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[FETCHER] Bağlantı hatası: {ca[:12]}...")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[FETCHER] HTTP hatası ({e.response.status_code}): {ca[:12]}...")
        return None
    except (ValueError, KeyError, TypeError) as e:
        print(f"[FETCHER] Veri ayrıştırma hatası: {e}")
        return None
    except Exception as e:
        print(f"[FETCHER] Beklenmeyen hata: {e}")
        return None
