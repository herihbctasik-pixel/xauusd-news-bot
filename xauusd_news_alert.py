"""
XAUUSD News Alert Bot
======================
Sistem otomasi untuk mengirim alert Telegram setiap ada berita ekonomi
berdampak tinggi yang relevan dengan XAUUSD (Gold/USD).

CARA SETUP:
1. Buat bot Telegram:
   - Chat ke @BotFather di Telegram -> /newbot -> ikuti instruksi
   - Simpan TOKEN yang diberikan
2. Dapatkan CHAT_ID Anda:
   - Chat sembarang pesan ke bot Anda
   - Buka: https://api.telegram.org/bot<TOKEN>/getUpdates
   - Cari "chat":{"id": ...} -> itu CHAT_ID Anda
3. Install dependency:
   pip install requests schedule feedparser --break-system-packages
4. Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di bawah
5. Jalankan: python xauusd_news_alert.py
   (atau pasang sebagai cron job / Task Scheduler agar jalan terus)

SUMBER DATA:
- Kalender ekonomi ForexFactory (gratis, tidak perlu API key)
  https://nfs.faireconomy.media/ff_calendar_thisweek.xml
"""

import requests
import schedule
import time
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# ============ KONFIGURASI (ISI INI) ============
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Jam pengiriman ringkasan berita harian (format 24 jam, waktu lokal server/PC Anda)
DAILY_SUMMARY_TIME = "07:00"

# Menit sebelum rilis berita untuk kirim reminder
REMINDER_MINUTES_BEFORE = 30

# Kata kunci event yang relevan dengan pergerakan Gold (selain filter currency=USD & impact=High)
GOLD_RELEVANT_KEYWORDS = [
    "non-farm", "nfp", "cpi", "inflation", "interest rate", "fomc",
    "fed", "gdp", "unemployment", "pmi", "retail sales",
    "consumer confidence", "ppi", "jobless claims"
]

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
# ==================================================


def send_telegram(message: str):
    """Kirim pesan ke Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        print(f"[{datetime.now()}] Alert terkirim.")
    except Exception as e:
        print(f"[{datetime.now()}] Gagal kirim Telegram: {e}")


def fetch_calendar():
    """Ambil kalender ekonomi mingguan dan filter event high-impact yang relevan Gold."""
    try:
        resp = requests.get(CALENDAR_URL, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"[{datetime.now()}] Gagal ambil kalender: {e}")
        return []

    events = []
    for event in root.findall("event"):
        currency = event.findtext("currency", "")
        impact = event.findtext("impact", "")
        title = event.findtext("title", "")
        date = event.findtext("date", "")
        time_ = event.findtext("time", "")

        if currency != "USD" or impact != "High":
            continue

        title_lower = title.lower()
        if not any(kw in title_lower for kw in GOLD_RELEVANT_KEYWORDS):
            continue

        events.append({
            "title": title,
            "date": date,
            "time": time_,
            "impact": impact,
            "currency": currency
        })
    return events


def send_daily_summary():
    """Kirim ringkasan berita hari ini yang relevan XAUUSD."""
    events = fetch_calendar()
    today_str = datetime.now().strftime("%m-%d-%Y")

    today_events = [e for e in events if e["date"] == today_str]

    if not today_events:
        msg = "📊 <b>XAUUSD News Update</b>\nTidak ada berita high-impact relevan Gold hari ini."
    else:
        msg = "📊 <b>XAUUSD News Update Hari Ini</b>\n\n"
        for e in today_events:
            msg += f"🔴 <b>{e['time']}</b> — {e['title']} ({e['currency']}, {e['impact']})\n"
        msg += "\n⚠️ Hindari entry 15-30 menit sebelum/sesudah rilis, spread bisa melebar."

    send_telegram(msg)


def check_upcoming_reminders():
    """Cek apakah ada event dalam waktu dekat (dijalankan tiap beberapa menit)."""
    events = fetch_calendar()
    now = datetime.now()
    today_str = now.strftime("%m-%d-%Y")

    for e in events:
        if e["date"] != today_str or not e["time"] or e["time"] in ("All Day", "Tentative"):
            continue
        try:
            event_time = datetime.strptime(f"{e['date']} {e['time']}", "%m-%d-%Y %I:%M%p")
        except ValueError:
            continue

        minutes_left = (event_time - now).total_seconds() / 60
        if 0 <= minutes_left <= REMINDER_MINUTES_BEFORE:
            msg = (f"⏰ <b>Reminder: {e['title']}</b>\n"
                   f"Rilis dalam ~{int(minutes_left)} menit ({e['time']})\n"
                   f"Currency: {e['currency']} | Impact: {e['impact']}\n"
                   f"⚠️ Pertimbangkan tutup posisi scalping atau kurangi lot sebelum rilis.")
            send_telegram(msg)


def main():
    print("XAUUSD News Alert Bot berjalan...")
    send_telegram("✅ Bot alert XAUUSD aktif dan siap mengirim update berita.")

    send_daily_summary()
    check_upcoming_reminders()


if __name__ == "__main__":
    main()
