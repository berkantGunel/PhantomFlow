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
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Sütun ismiyle erişim için
        return conn
    except Exception as e:
        import sys
        print(f"[FATAL DB ERROR] SQLite connect failed on {DB_PATH}. Details: {e}", file=sys.stderr)
        raise


def init_db():
    """
    Veritabanını başlat.
    Eğer price_history tablosu yoksa oluşturur.
    """
    conn = get_connection()
    try:
        # Tabloyu oluştur veya güncelle (sütunlar yoksa ekle)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ca TEXT NOT NULL,
                name TEXT NOT NULL,
                price_usd REAL NOT NULL,
                volume_24h REAL DEFAULT 0,
                liquidity_usd REAL DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Mevcut tabloya yeni sütunları ekle (eğer önceden varsa)
        try:
            conn.execute("ALTER TABLE price_history ADD COLUMN volume_24h REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Sütun zaten var
            
        try:
            conn.execute("ALTER TABLE price_history ADD COLUMN liquidity_usd REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Sütun zaten var

        # Sorguları hızlandırmak için CA üzerine indeks
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ca_timestamp
            ON price_history (ca, timestamp DESC)
        """)
        conn.commit()
        print("[DB] Veritabanı başlatıldı ve şema güncellendi.")
    except Exception as e:
        print(f"[DB] Veritabanı başlatma hatası: {e}")
    finally:
        conn.close()


def save_price(ca: str, name: str, price_usd: float, volume_24h: float = 0, liquidity_usd: float = 0):
    """
    Token verilerini veritabanına ekle.
    """
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO price_history (ca, name, price_usd, volume_24h, liquidity_usd, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (ca, name, price_usd, volume_24h, liquidity_usd, now)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] Veri kaydetme hatası ({name}): {e}")
    finally:
        conn.close()


def get_last_data(ca: str) -> Optional[dict]:
    """
    Belirtilen token'ın veritabanındaki son verilerini (fiyat, hacim, likidite) döndür.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT price_usd, volume_24h, liquidity_usd FROM price_history WHERE ca = ? ORDER BY id DESC LIMIT 1",
            (ca,)
        ).fetchone()
        if row:
            return {
                "price_usd": row["price_usd"],
                "volume_24h": row["volume_24h"],
                "liquidity_usd": row["liquidity_usd"]
            }
        return None
    except Exception as e:
        print(f"[DB] Son veri sorgulama hatası ({ca}): {e}")
        return None
    finally:
        conn.close()
