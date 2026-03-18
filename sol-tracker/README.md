# 🔍 Solana Token Tracker Bot

Belirttiğiniz Solana token'larını düzenli aralıklarla takip eden, fiyat değişimlerinde
Telegram üzerinden bildirim gönderen Python botu.

**Özellikler:**
- ✅ Tamamen ücretsiz (DexScreener API + Telegram Bot API)
- ✅ 7/24 kesintisiz çalışma (systemd ile)
- ✅ Özelleştirilebilir eşik değerleri (her token için ayrı)
- ✅ SQLite ile fiyat geçmişi saklama
- ✅ Otomatik hata yönetimi (bot çökmez)
- ✅ Güzel formatlanmış Telegram bildirimleri

---

## 📋 İçindekiler

1. [Yerel Kurulum](#1-yerel-kurulum)
2. [Telegram Bot Kurulumu](#2-telegram-bot-kurulumu)
3. [Config Dosyası](#3-config-dosyası)
4. [Oracle Cloud Free Tier Kurulumu](#4-oracle-cloud-free-tier-kurulumu)
5. [7/24 Çalıştırma (systemd)](#5-724-çalıştırma-systemd)
6. [Bot Durumu Kontrol](#6-bot-durumu-kontrol)

---

## 1. Yerel Kurulum

### Gereksinimler
- Python 3.10 veya üzeri
- pip (Python paket yöneticisi)

### Adımlar

```bash
# 1. Proje klasörüne gir
cd sol-tracker

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. config.json dosyasını düzenle (aşağıdaki bölüme bak)
nano config.json

# 4. Botu başlat
python main.py
```

---

## 2. Telegram Bot Kurulumu

### Bot Oluşturma

1. Telegram'da **@BotFather**'ı arayın ve bir sohbet başlatın
2. `/newbot` komutunu gönderin
3. Botunuza bir isim verin (ör: "Solana Tracker Bot")
4. Botunuza bir kullanıcı adı verin (ör: "sol_tracker_123_bot")
   - Bot kullanıcı adları `bot` ile bitmek zorundadır
5. BotFather size bir **API Token** verecek. Bu token'ı kopyalayın:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
6. Bu token'ı `config.json`'daki `bot_token` alanına yapıştırın

### Chat ID Öğrenme

1. Telegram'da **@userinfobot**'u arayın ve bir sohbet başlatın
2. `/start` komutunu gönderin
3. Bot size **Chat ID**'nizi gösterecek (ör: `123456789`)
4. Bu ID'yi `config.json`'daki `chat_id` alanına yapıştırın

> **Not:** Bildirimleri almak için önce kendi botunuza (`@sol_tracker_123_bot`) gidip `/start` tuşuna basmanız gerekir!

---

## 3. Config Dosyası

`config.json` dosyasını aşağıdaki gibi düzenleyin:

```json
{
  "tokens": [
    {
      "name": "BONK",
      "ca": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
      "alert_up": 5,
      "alert_down": 5
    },
    {
      "name": "WIF",
      "ca": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
      "alert_up": 10,
      "alert_down": 10
    }
  ],
  "interval_minutes": 5,
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID_HERE"
  }
}
```

### Alan Açıklamaları

| Alan | Açıklama |
|------|----------|
| `name` | Token'ın görünen adı (bildirimde kullanılır) |
| `ca` | Solana contract adresi |
| `alert_up` | Yükseliş alert eşiği (%) — Bu yüzde aşılırsa bildirim gelir |
| `alert_down` | Düşüş alert eşiği (%) — Bu yüzde aşılırsa bildirim gelir |
| `interval_minutes` | Kontrol aralığı (dakika) |
| `bot_token` | Telegram bot API token'ı |
| `chat_id` | Telegram chat ID'niz |

> **İpucu:** Token'ların CA adreslerini [DexScreener](https://dexscreener.com/solana) veya [Phantom](https://phantom.com) üzerinden bulabilirsiniz.

---

## 4. macOS'ta Arka Planda Çalıştırma (launchd)

macOS'un yerleşik `launchd` sistemi ile bot bilgisayarınız açık olduğu sürece arka planda çalışır.
Bilgisayar yeniden başlasa bile bot otomatik olarak tekrar başlar.

### 4.1. Servisi Başlatma

```bash
# Servisi yükle ve başlat
launchctl load ~/Library/LaunchAgents/com.soltracker.bot.plist
```

> **Not:** Plist dosyası zaten oluşturuldu: `~/Library/LaunchAgents/com.soltracker.bot.plist`

### 4.2. Servisi Durdurma

```bash
# Servisi durdur ve kaldır
launchctl unload ~/Library/LaunchAgents/com.soltracker.bot.plist
```

### 4.3. Servisi Yeniden Başlatma

```bash
# Önce durdur, sonra başlat
launchctl unload ~/Library/LaunchAgents/com.soltracker.bot.plist
launchctl load ~/Library/LaunchAgents/com.soltracker.bot.plist
```

---

## 5. Bot Durumu Kontrol

```bash
# Bot çalışıyor mu?
launchctl list | grep soltracker

# Canlı log takibi (Ctrl+C ile çıkılır)
tail -f ~/Desktop/PhantomFlow/sol-tracker/bot.log

# Hata loglarını görüntüle
tail -f ~/Desktop/PhantomFlow/sol-tracker/bot_error.log

# Son 50 satır log
tail -n 50 ~/Desktop/PhantomFlow/sol-tracker/bot.log
```

---

## 📱 Bildirim Örnekleri

Bot aşağıdaki formatta bildirim gönderir:

**Yükseliş:**
```
🚀 BONK YÜKSELDİ!
━━━━━━━━━━━━━━━━━━
💰 Fiyat: $0.00001234
📈 Değişim: +7.3%
⏱ 1s: +12.1%  |  24s: -3.4%
💧 Likidite: $45.2K
📦 Hacim 24s: $120.0K
🔗 Phantom'da Görüntüle
⏰ 2025-01-15 14:32
```

**Düşüş:**
```
🔻 BONK DÜŞTÜ!
━━━━━━━━━━━━━━━━━━
💰 Fiyat: $0.00000987
📈 Değişim: -8.1%
⏱ 1s: -5.2%  |  24s: -15.3%
💧 Likidite: $38.7K
📦 Hacim 24s: $95.0K
🔗 Phantom'da Görüntüle
⏰ 2025-01-15 14:37
```

---

## 🔧 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `config.json bulunamadı` | Dosyanın `main.py` ile aynı klasörde olduğundan emin olun |
| `bot_token ayarlanmamış` | config.json'daki `bot_token` alanını BotFather'dan aldığınız token ile doldurun |
| `Telegram mesaj gönderme hatası` | Bota `/start` gönderdiğinizden emin olun |
| `Veri alınamadı` | DexScreener API'nin çalışır olduğunu kontrol edin, CA adresinin doğruluğunu kontrol edin |
| Bot hiç bildirim göndermiyor | İlk çalışmada sadece kayıt yapılır, bildirim ikinci kontrolden itibaren gelir |
| `pip install` hatası | `pip3 install --user -r requirements.txt` deneyin |

---

## 📁 Dosya Yapısı

```
sol-tracker/
├── main.py           → Giriş noktası
├── config.json       → Token listesi ve ayarlar
├── fetcher.py        → DexScreener'dan veri çekme
├── tracker.py        → Fiyat değişim hesaplama ve eşik kontrolü
├── notifier.py       → Telegram bildirim gönderme
├── scheduler.py      → APScheduler zamanlayıcı
├── db.py             → SQLite veritabanı işlemleri
├── requirements.txt  → Python bağımlılıkları
├── price_history.db  → Fiyat geçmişi (otomatik oluşturulur)
└── README.md         → Bu dosya
```

---

## 📄 Lisans

Bu proje kişisel kullanım için tasarlanmıştır.
