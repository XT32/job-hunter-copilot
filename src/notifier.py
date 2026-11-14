import json
import urllib.parse
import urllib.request

def send_telegram_alert(title, company, url, platform="Glints", salary="Tidak dicantumkan", bot_token="", chat_id=""):
    """Mengirimkan notifikasi penemuan loker cocok ke Telegram pribadi pengguna via bot gratis"""
    if not bot_token or not chat_id:
        return False

    message = (
        f"🎯 *Lowongan Cocok Baru Ditemukan!*\n\n"
        f"📌 *Posisi:* {title}\n"
        f"🏢 *Perusahaan:* {company}\n"
        f"💰 *Gaji:* {salary}\n"
        f"🌐 *Platform:* {platform}\n\n"
        f"🔗 [Klik untuk Buka Loker]({url})"
    )

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        print(f"[!] Info Notifier: Gagal kirim Telegram ({e})")
        return False
