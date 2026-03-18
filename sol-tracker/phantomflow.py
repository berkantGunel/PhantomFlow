#!/usr/bin/env python3
# phantomflow.py — PhantomFlow İnteraktif Yönetim Shell'i
# Token ekleme/silme, fiyat takibi, bot yönetimi tek yerden.

import json
import os
import sys
import signal
import subprocess
import sqlite3
from datetime import datetime

# ─── Renkler ───────────────────────────────────────────────
class Colors:
    """Terminal renk kodları"""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Ana renkler
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

    # Arka plan
    BG_DARK = "\033[48;5;235m"

    @staticmethod
    def colored(text, color):
        return f"{color}{text}{Colors.RESET}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.RESET}"

    @staticmethod
    def success(text):
        return f"{Colors.GREEN}✓ {text}{Colors.RESET}"

    @staticmethod
    def error(text):
        return f"{Colors.RED}✗ {text}{Colors.RESET}"

    @staticmethod
    def warning(text):
        return f"{Colors.YELLOW}⚠ {text}{Colors.RESET}"

    @staticmethod
    def info(text):
        return f"{Colors.CYAN}ℹ {text}{Colors.RESET}"


# ─── Yollar ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DB_PATH = os.path.join(BASE_DIR, "price_history.db")


# ─── Yardımcı Fonksiyonlar ─────────────────────────────────

def load_config():
    """config.json dosyasını yükle."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(Colors.error("config.json bulunamadı!"))
        return None
    except json.JSONDecodeError:
        print(Colors.error("config.json geçersiz format!"))
        return None


def save_config(config):
    """config.json dosyasını kaydet."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(Colors.error(f"Config kaydetme hatası: {e}"))
        return False


def fetch_token_info(ca):
    """DexScreener API'den token bilgisini çek."""
    import requests
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        pairs = data.get("pairs", [])
        if not pairs:
            return None

        pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        base = pair.get("baseToken", {})
        price_change = pair.get("priceChange", {})

        return {
            "name": base.get("name", "Bilinmiyor"),
            "symbol": base.get("symbol", "?"),
            "price_usd": float(pair.get("priceUsd", 0) or 0),
            "price_change_5m": float(price_change.get("m5", 0) or 0),
            "price_change_1h": float(price_change.get("h1", 0) or 0),
            "price_change_24h": float(price_change.get("h24", 0) or 0),
            "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
            "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
            "market_cap": float(pair.get("marketCap", 0) or 0),
            "dex": pair.get("dexId", "?"),
        }
    except Exception as e:
        print(Colors.error(f"API hatası: {e}"))
        return None


def format_price(price):
    """Fiyatı okunabilir formatta göster."""
    if price >= 1:
        return f"${price:,.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.10f}"


def format_number(value):
    """Büyük sayıları kısalt."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:,.1f}K"
    else:
        return f"${value:,.0f}"


def format_change(change):
    """Yüzde değişimi renkli göster."""
    if change > 0:
        return Colors.colored(f"+{change:.2f}%", Colors.GREEN)
    elif change < 0:
        return Colors.colored(f"{change:.2f}%", Colors.RED)
    else:
        return Colors.colored(f"{change:.2f}%", Colors.DIM)


def get_db_connection():
    """SQLite bağlantısı."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_bot_running():
    """Bot'un çalışıp çalışmadığını kontrol et."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python3.*main.py"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split('\n')
        # Kendi PID'imizi çıkar
        my_pid = str(os.getpid())
        running_pids = [p for p in pids if p and p != my_pid]
        return len(running_pids) > 0
    except Exception:
        return False


def clear_screen():
    """Ekranı temizle."""
    os.system("clear" if os.name != "nt" else "cls")


# ─── Banner ────────────────────────────────────────────────

def print_banner():
    """Başlangıç banner'ını göster."""
    banner = f"""
{Colors.MAGENTA}{Colors.BOLD}
    ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
    ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
    ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
    ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
    ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
{Colors.RESET}
    {Colors.CYAN}{Colors.BOLD}  ███████╗██╗      ██████╗ ██╗    ██╗
    {Colors.CYAN}  ██╔════╝██║     ██╔═══██╗██║    ██║
    {Colors.CYAN}  █████╗  ██║     ██║   ██║██║ █╗ ██║
    {Colors.CYAN}  ██╔══╝  ██║     ██║   ██║██║███╗██║
    {Colors.CYAN}  ██║     ███████╗╚██████╔╝╚███╔███╔╝
    {Colors.CYAN}  ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝{Colors.RESET}

    {Colors.DIM}Solana Token Fiyat Takip Sistemi{Colors.RESET}
    {Colors.DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}
"""
    print(banner)


# ─── Menü Komutları ────────────────────────────────────────

def show_menu():
    """Ana menüyü göster."""
    config = load_config()
    token_count = len(config["tokens"]) if config else 0
    bot_status = Colors.colored("● ÇALIŞIYOR", Colors.GREEN) if is_bot_running() else Colors.colored("● DURDU", Colors.RED)

    print(f"\n  {Colors.BOLD}┌─────────────────────────────────────────────┐{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.CYAN}PhantomFlow Yönetim Paneli{Colors.RESET}                  {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  Bot: {bot_status}    Token: {Colors.YELLOW}{token_count}{Colors.RESET}                  {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}├─────────────────────────────────────────────┤{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}                                             {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}1{Colors.RESET} │ 📊 Anlık Fiyatları Görüntüle            {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}2{Colors.RESET} │ ➕ Yeni Token Ekle                      {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}3{Colors.RESET} │ ❌ Token Sil / Takibi Bırak             {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}4{Colors.RESET} │ 📋 Takip Edilen Token'ları Listele      {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}5{Colors.RESET} │ 📈 Fiyat Geçmişi                        {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}6{Colors.RESET} │ ⚙️  Ayarları Düzenle                     {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}7{Colors.RESET} │ 🚀 Bot'u Başlat                         {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}8{Colors.RESET} │ 🛑 Bot'u Durdur                         {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}9{Colors.RESET} │ 📄 Bot Loglarını Görüntüle              {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}  {Colors.GREEN}0{Colors.RESET} │ 🚪 Çıkış                                {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}│{Colors.RESET}                                             {Colors.BOLD}│{Colors.RESET}")
    print(f"  {Colors.BOLD}└─────────────────────────────────────────────┘{Colors.RESET}")


def cmd_view_prices():
    """1 — Tüm token'ların anlık fiyatlarını göster."""
    config = load_config()
    if not config or not config["tokens"]:
        print(Colors.warning("Takip edilen token yok."))
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}📊 Anlık Fiyatlar{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 70}{Colors.RESET}")

    for token in config["tokens"]:
        print(f"\n  {Colors.DIM}Sorgulanıyor: {token['name']}...{Colors.RESET}", end="\r")
        info = fetch_token_info(token["ca"])

        if info is None:
            print(f"  {Colors.error(token['name'] + ': Veri alınamadı')}")
            continue

        # Başlık satırı
        print(f"  {Colors.BOLD}{Colors.MAGENTA}{'─' * 50}{Colors.RESET}")
        print(f"  {Colors.BOLD}{Colors.WHITE}  {info['symbol']} — {info['name']}{Colors.RESET}")
        print(f"  {Colors.BOLD}{Colors.MAGENTA}{'─' * 50}{Colors.RESET}")

        # Fiyat
        print(f"  💰 Fiyat:      {Colors.BOLD}{format_price(info['price_usd'])}{Colors.RESET}")

        # Değişimler
        print(f"  📊 5dk:        {format_change(info['price_change_5m'])}")
        print(f"  📊 1 Saat:     {format_change(info['price_change_1h'])}")
        print(f"  📊 24 Saat:    {format_change(info['price_change_24h'])}")

        # Likidite ve hacim
        print(f"  💧 Likidite:   {Colors.YELLOW}{format_number(info['liquidity_usd'])}{Colors.RESET}")
        print(f"  📦 Hacim 24s:  {Colors.YELLOW}{format_number(info['volume_24h'])}{Colors.RESET}")

        # Market cap
        if info['market_cap'] > 0:
            print(f"  🏦 MCap:       {Colors.YELLOW}{format_number(info['market_cap'])}{Colors.RESET}")

        # DEX ve Link
        print(f"  🔗 DEX:        {info['dex']}")
        print(f"  🌐 {Colors.CYAN}https://trade.phantom.com/token/{token['ca']}{Colors.RESET}")

        # Eşikler
        print(f"  ⚠️  Alert:      ↑{token.get('alert_up', 5)}% / ↓{token.get('alert_down', 5)}%")

    print(f"\n  {Colors.DIM}{'━' * 70}{Colors.RESET}")
    print(f"  {Colors.DIM}Son güncelleme: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")


def cmd_add_token():
    """2 — Yeni token ekle."""
    config = load_config()
    if not config:
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}➕ Yeni Token Ekle{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 50}{Colors.RESET}")

    # CA adresi al
    ca = input(f"\n  {Colors.YELLOW}Contract Address (CA):{Colors.RESET} ").strip()
    if not ca:
        print(Colors.warning("İptal edildi."))
        return

    # Zaten var mı kontrol et
    for t in config["tokens"]:
        if t["ca"].lower() == ca.lower():
            print(Colors.warning(f"Bu token zaten takip ediliyor: {t['name']}"))
            return

    # DexScreener'dan bilgi çek
    print(f"  {Colors.DIM}DexScreener'dan bilgi çekiliyor...{Colors.RESET}")
    info = fetch_token_info(ca)

    if info is None:
        print(Colors.error("Token bulunamadı! CA adresini kontrol edin."))
        return

    # Token bilgilerini göster
    print(f"\n  {Colors.GREEN}Token bulundu:{Colors.RESET}")
    print(f"  📛 İsim:      {Colors.BOLD}{info['name']} ({info['symbol']}){Colors.RESET}")
    print(f"  💰 Fiyat:     {format_price(info['price_usd'])}")
    print(f"  💧 Likidite:  {format_number(info['liquidity_usd'])}")
    print(f"  📦 Hacim 24s: {format_number(info['volume_24h'])}")
    print(f"  🔗 DEX:       {info['dex']}")

    # İsim sor (otomatik öneri)
    suggested_name = info["symbol"].upper()
    name_input = input(f"\n  {Colors.YELLOW}Token adı [{suggested_name}]:{Colors.RESET} ").strip()
    name = name_input if name_input else suggested_name

    # Eşik değerleri
    try:
        up_input = input(f"  {Colors.YELLOW}Yükseliş alert eşiği % [5]:{Colors.RESET} ").strip()
        alert_up = float(up_input) if up_input else 5.0

        down_input = input(f"  {Colors.YELLOW}Düşüş alert eşiği % [5]:{Colors.RESET} ").strip()
        alert_down = float(down_input) if down_input else 5.0
    except ValueError:
        print(Colors.warning("Geçersiz değer, varsayılan %5 kullanılacak."))
        alert_up = 5.0
        alert_down = 5.0

    # Onay iste
    print(f"\n  {Colors.BOLD}Eklenecek token:{Colors.RESET}")
    print(f"  📛 {name} | ↑{alert_up}% / ↓{alert_down}%")
    confirm = input(f"\n  {Colors.YELLOW}Onaylıyor musunuz? [E/h]:{Colors.RESET} ").strip().lower()

    if confirm in ("h", "hayir", "n", "no"):
        print(Colors.warning("İptal edildi."))
        return

    # Config'e ekle
    new_token = {
        "name": name,
        "ca": ca,
        "alert_up": alert_up,
        "alert_down": alert_down
    }
    config["tokens"].append(new_token)

    if save_config(config):
        print(Colors.success(f"{name} başarıyla eklendi!"))
        if is_bot_running():
            print(Colors.info("Değişikliklerin geçerli olması için botu yeniden başlatın. (8 → 7)"))
    else:
        print(Colors.error("Token eklenemedi!"))


def cmd_remove_token():
    """3 — Token sil / takibi bırak."""
    config = load_config()
    if not config or not config["tokens"]:
        print(Colors.warning("Takip edilen token yok."))
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}❌ Token Sil{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 50}{Colors.RESET}\n")

    # Token listesini göster
    for i, token in enumerate(config["tokens"], 1):
        print(f"  {Colors.GREEN}{i}{Colors.RESET} │ {Colors.BOLD}{token['name']}{Colors.RESET}")
        print(f"    {Colors.DIM}{token['ca'][:20]}...{Colors.RESET}")

    # Seçim al
    try:
        choice = input(f"\n  {Colors.YELLOW}Silmek istediğiniz token numarası (0 = iptal):{Colors.RESET} ").strip()
        idx = int(choice)
    except ValueError:
        print(Colors.warning("Geçersiz seçim."))
        return

    if idx == 0:
        print(Colors.warning("İptal edildi."))
        return

    if idx < 1 or idx > len(config["tokens"]):
        print(Colors.error("Geçersiz numara!"))
        return

    # Onay
    token = config["tokens"][idx - 1]
    confirm = input(f"\n  {Colors.RED}{token['name']}{Colors.RESET} silinecek. Emin misiniz? [e/H]: ").strip().lower()

    if confirm not in ("e", "evet", "y", "yes"):
        print(Colors.warning("İptal edildi."))
        return

    removed = config["tokens"].pop(idx - 1)
    if save_config(config):
        print(Colors.success(f"{removed['name']} silindi!"))
        if is_bot_running():
            print(Colors.info("Değişikliklerin geçerli olması için botu yeniden başlatın. (8 → 7)"))


def cmd_list_tokens():
    """4 — Takip edilen token'ları listele."""
    config = load_config()
    if not config or not config["tokens"]:
        print(Colors.warning("Takip edilen token yok."))
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}📋 Takip Edilen Token'lar{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 60}{Colors.RESET}")

    header = f"  {'#':<4} {'İsim':<12} {'Alert ↑':<10} {'Alert ↓':<10} {'CA'}"
    print(f"  {Colors.BOLD}{Colors.DIM}{header}{Colors.RESET}")
    print(f"  {Colors.DIM}{'─' * 60}{Colors.RESET}")

    for i, token in enumerate(config["tokens"], 1):
        ca_short = token['ca'][:16] + "..." + token['ca'][-6:]
        print(
            f"  {Colors.GREEN}{i:<4}{Colors.RESET}"
            f"{Colors.BOLD}{token['name']:<12}{Colors.RESET}"
            f"{Colors.GREEN}↑{token.get('alert_up', 5)}%{Colors.RESET}{'':>6}"
            f"{Colors.RED}↓{token.get('alert_down', 5)}%{Colors.RESET}{'':>6}"
            f"{Colors.DIM}{ca_short}{Colors.RESET}"
        )

    print(f"\n  {Colors.DIM}Kontrol aralığı: {config.get('interval_minutes', 5)} dakika{Colors.RESET}")


def cmd_price_history():
    """5 — Fiyat geçmişini göster."""
    config = load_config()
    if not config or not config["tokens"]:
        print(Colors.warning("Takip edilen token yok."))
        return

    conn = get_db_connection()
    if not conn:
        print(Colors.warning("Veritabanı henüz oluşturulmamış. Botu en az bir kez çalıştırın."))
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}📈 Fiyat Geçmişi{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 50}{Colors.RESET}\n")

    # Token seçimi
    for i, token in enumerate(config["tokens"], 1):
        print(f"  {Colors.GREEN}{i}{Colors.RESET} │ {token['name']}")

    print(f"  {Colors.GREEN}0{Colors.RESET} │ Tümü")

    try:
        choice = int(input(f"\n  {Colors.YELLOW}Token seçin:{Colors.RESET} ").strip())
    except ValueError:
        print(Colors.warning("Geçersiz seçim."))
        conn.close()
        return

    # Kaç kayıt gösterilsin
    try:
        limit_input = input(f"  {Colors.YELLOW}Kaç kayıt? [10]:{Colors.RESET} ").strip()
        limit = int(limit_input) if limit_input else 10
    except ValueError:
        limit = 10

    print()

    if choice == 0:
        # Tüm token'lar
        tokens_to_show = config["tokens"]
    elif 1 <= choice <= len(config["tokens"]):
        tokens_to_show = [config["tokens"][choice - 1]]
    else:
        print(Colors.error("Geçersiz seçim!"))
        conn.close()
        return

    for token in tokens_to_show:
        rows = conn.execute(
            "SELECT price_usd, timestamp FROM price_history WHERE ca = ? ORDER BY id DESC LIMIT ?",
            (token["ca"], limit)
        ).fetchall()

        print(f"  {Colors.BOLD}{Colors.MAGENTA}{'─' * 45}{Colors.RESET}")
        print(f"  {Colors.BOLD}  {token['name']}{Colors.RESET}  ({len(rows)} kayıt)")
        print(f"  {Colors.BOLD}{Colors.MAGENTA}{'─' * 45}{Colors.RESET}")

        if not rows:
            print(f"  {Colors.DIM}  Henüz kayıt yok.{Colors.RESET}")
            continue

        print(f"  {'Tarih':<22} {'Fiyat':<20} {'Değişim'}")
        print(f"  {Colors.DIM}{'─' * 45}{Colors.RESET}")

        prev_price = None
        # Cronolojik sırala (eskiden yeniye)
        for row in reversed(rows):
            price = row["price_usd"]
            timestamp = row["timestamp"]

            if prev_price is not None and prev_price > 0:
                change = ((price - prev_price) / prev_price) * 100
                change_str = format_change(change)
            else:
                change_str = Colors.colored("  —", Colors.DIM)

            print(f"  {Colors.DIM}{timestamp}{Colors.RESET}  {format_price(price):<18}  {change_str}")
            prev_price = price

    conn.close()


def cmd_settings():
    """6 — Ayarları düzenle."""
    config = load_config()
    if not config:
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}⚙️  Ayarlar{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 50}{Colors.RESET}\n")

    print(f"  {Colors.GREEN}1{Colors.RESET} │ Kontrol aralığını değiştir (şu an: {Colors.YELLOW}{config.get('interval_minutes', 5)} dk{Colors.RESET})")
    print(f"  {Colors.GREEN}2{Colors.RESET} │ Token eşik değerlerini değiştir")
    print(f"  {Colors.GREEN}3{Colors.RESET} │ Telegram ayarlarını görüntüle")
    print(f"  {Colors.GREEN}0{Colors.RESET} │ Geri dön")

    try:
        choice = int(input(f"\n  {Colors.YELLOW}Seçim:{Colors.RESET} ").strip())
    except ValueError:
        return

    if choice == 1:
        try:
            new_interval = input(f"  {Colors.YELLOW}Yeni kontrol aralığı (dakika):{Colors.RESET} ").strip()
            config["interval_minutes"] = int(new_interval)
            if save_config(config):
                print(Colors.success(f"Kontrol aralığı {new_interval} dakika olarak güncellendi."))
        except ValueError:
            print(Colors.error("Geçersiz değer!"))

    elif choice == 2:
        if not config["tokens"]:
            print(Colors.warning("Token yok."))
            return
        for i, t in enumerate(config["tokens"], 1):
            print(f"  {Colors.GREEN}{i}{Colors.RESET} │ {t['name']} (↑{t.get('alert_up', 5)}% / ↓{t.get('alert_down', 5)}%)")

        try:
            idx = int(input(f"\n  {Colors.YELLOW}Token numarası:{Colors.RESET} ").strip())
            if 1 <= idx <= len(config["tokens"]):
                token = config["tokens"][idx - 1]
                up = input(f"  {Colors.YELLOW}Yükseliş eşiği % [{token.get('alert_up', 5)}]:{Colors.RESET} ").strip()
                down = input(f"  {Colors.YELLOW}Düşüş eşiği % [{token.get('alert_down', 5)}]:{Colors.RESET} ").strip()
                if up:
                    token["alert_up"] = float(up)
                if down:
                    token["alert_down"] = float(down)
                if save_config(config):
                    print(Colors.success(f"{token['name']} eşikleri güncellendi."))
        except (ValueError, IndexError):
            print(Colors.error("Geçersiz seçim!"))

    elif choice == 3:
        tg = config.get("telegram", {})
        bot_token = tg.get("bot_token", "?")
        # Token'ı kısmen gizle
        if len(bot_token) > 10:
            masked_token = bot_token[:8] + "..." + bot_token[-4:]
        else:
            masked_token = "Ayarlanmamış"
        print(f"\n  🤖 Bot Token: {Colors.DIM}{masked_token}{Colors.RESET}")
        print(f"  💬 Chat ID:   {Colors.DIM}{tg.get('chat_id', 'Ayarlanmamış')}{Colors.RESET}")


def cmd_start_bot():
    """7 — Bot'u arka planda başlat."""
    if is_bot_running():
        print(Colors.warning("Bot zaten çalışıyor!"))
        return

    print(f"  {Colors.DIM}Bot başlatılıyor...{Colors.RESET}")
    try:
        log_file = os.path.join(BASE_DIR, "bot.log")
        err_file = os.path.join(BASE_DIR, "bot_error.log")
        main_py = os.path.join(BASE_DIR, "main.py")

        with open(log_file, "a") as out, open(err_file, "a") as err:
            proc = subprocess.Popen(
                ["python3", main_py],
                cwd=BASE_DIR,
                stdout=out,
                stderr=err,
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
        print(Colors.success(f"Bot başlatıldı! (PID: {proc.pid})"))
        print(Colors.info(f"Log dosyası: {log_file}"))
    except Exception as e:
        print(Colors.error(f"Bot başlatılamadı: {e}"))


def cmd_stop_bot():
    """8 — Bot'u durdur."""
    if not is_bot_running():
        print(Colors.warning("Bot zaten çalışmıyor."))
        return

    try:
        result = subprocess.run(
            ["pgrep", "-f", "python3.*main.py"],
            capture_output=True, text=True
        )
        pids = [p for p in result.stdout.strip().split('\n') if p and p != str(os.getpid())]

        for pid in pids:
            os.kill(int(pid), signal.SIGTERM)

        print(Colors.success("Bot durduruldu."))
    except Exception as e:
        print(Colors.error(f"Bot durdurulamadı: {e}"))


def cmd_view_logs():
    """9 — Bot loglarını göster."""
    log_file = os.path.join(BASE_DIR, "bot.log")

    if not os.path.exists(log_file):
        print(Colors.warning("Log dosyası henüz oluşturulmamış."))
        return

    print(f"\n  {Colors.BOLD}{Colors.CYAN}📄 Son Log Kayıtları{Colors.RESET}")
    print(f"  {Colors.DIM}{'━' * 60}{Colors.RESET}\n")

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            last_lines = lines[-30:] if len(lines) > 30 else lines

            for line in last_lines:
                line = line.rstrip()
                # Renklendirme
                if "[TRACKER]" in line:
                    print(f"  {Colors.CYAN}{line}{Colors.RESET}")
                elif "[NOTIFIER]" in line:
                    print(f"  {Colors.MAGENTA}{line}{Colors.RESET}")
                elif "[SCHEDULER]" in line:
                    print(f"  {Colors.YELLOW}{line}{Colors.RESET}")
                elif "[DB]" in line:
                    print(f"  {Colors.BLUE}{line}{Colors.RESET}")
                elif "HATA" in line or "hata" in line or "Error" in line:
                    print(f"  {Colors.RED}{line}{Colors.RESET}")
                elif "✅" in line or "başlatıldı" in line:
                    print(f"  {Colors.GREEN}{line}{Colors.RESET}")
                else:
                    print(f"  {Colors.DIM}{line}{Colors.RESET}")

    except Exception as e:
        print(Colors.error(f"Log okunamadı: {e}"))

    print(f"\n  {Colors.DIM}Canlı log için: tail -f {log_file}{Colors.RESET}")


# ─── Ana Shell Döngüsü ────────────────────────────────────

def main():
    """Shell'i başlat."""
    clear_screen()
    print_banner()

    # Komut haritası
    commands = {
        "1": cmd_view_prices,
        "2": cmd_add_token,
        "3": cmd_remove_token,
        "4": cmd_list_tokens,
        "5": cmd_price_history,
        "6": cmd_settings,
        "7": cmd_start_bot,
        "8": cmd_stop_bot,
        "9": cmd_view_logs,
    }

    while True:
        show_menu()

        try:
            choice = input(f"\n  {Colors.BOLD}{Colors.MAGENTA}phantom>{Colors.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {Colors.DIM}Güle güle! 👋{Colors.RESET}\n")
            break

        if choice in ("0", "q", "quit", "exit", "çıkış", "cikis"):
            print(f"\n  {Colors.DIM}Güle güle! 👋{Colors.RESET}\n")
            break
        elif choice == "clear" or choice == "cls":
            clear_screen()
            print_banner()
        elif choice in commands:
            commands[choice]()
            input(f"\n  {Colors.DIM}Devam etmek için Enter'a basın...{Colors.RESET}")
        elif choice == "":
            continue
        else:
            print(Colors.error("Geçersiz komut! 0-9 arasında bir seçim yapın."))


if __name__ == "__main__":
    main()
