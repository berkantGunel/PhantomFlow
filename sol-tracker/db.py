# db.py — SQLite veritabanı işlemleri
# Fiyat geçmişini saklamak ve sorgulamak için kullanılır.

import sqlite3
import os
from datetime import datetime
from typing import Optional

# Veritabanı dosyasının yolu (bu dosyanın bulunduğu klasörde oluşturulur)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_history.db")


def get_connection():
    """SQLite bağlantısı oluştur ve döndür."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Sütun ismiyle erişim için
    return conn


def init_db():
    """
    Veritabanını başlat.
    Eğer price_history tablosu yoksa oluşturur.
    """
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ca TEXT NOT NULL,
                name TEXT NOT NULL,
                price_usd REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        # Sorguları hızlandırmak için CA üzerine indeks
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ca_timestamp
            ON price_history (ca, timestamp DESC)
        """)
        conn.commit()
        print("[DB] Veritabanı başlatıldı.")
    except Exception as e:
        print(f"[DB] Veritabanı başlatma hatası: {e}")
    finally:
        conn.close()


def save_price(ca: str, name: str, price_usd: float):
    """
    Fiyat kaydını veritabanına ekle.
    Her kontrol döngüsünde çağrılır.
    """
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO price_history (ca, name, price_usd, timestamp) VALUES (?, ?, ?, ?)",
            (ca, name, price_usd, now)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] Fiyat kaydetme hatası ({name}): {e}")
    finally:
        conn.close()


def get_last_price(ca: str) -> Optional[float]:
    """
    Belirtilen token'ın veritabanındaki son fiyatını döndür.
    Eğer daha önce kayıt yoksa None döndürür (ilk çalışma durumu).
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT price_usd FROM price_history WHERE ca = ? ORDER BY id DESC LIMIT 1",
            (ca,)
        ).fetchone()
        if row:
            return row["price_usd"]
        return None
    except Exception as e:
        print(f"[DB] Son fiyat sorgulama hatası ({ca}): {e}")
        return None
    finally:
        conn.close()
