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

def test_telegram_connection(bot_token="", chat_id=""):
    """Menguji koneksi bot Telegram dengan mengirim pesan tes sambutan"""
    bot_token = (bot_token or "").strip()
    chat_id = str(chat_id or "").strip()

    if not bot_token or not chat_id:
        return {"success": False, "message": "Bot Token dan Chat ID wajib diisi."}

    message = (
        "🤖 *Tes Koneksi loker-cli Berhasil!*\n\n"
        "Halo! Bot Telegram kamu sudah terhubung dengan aplikasi *loker-cli*.\n"
        "Setiap kali ada lowongan pekerjaan atau magang yang cocok dengan profil kamu, "
        "notifikasi instan akan otomatis dikirimkan ke chat ini.\n\n"
        "🚀 _Selamat berburu loker impian!_"
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
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                return {"success": True, "message": "Pesan tes berhasil dikirim ke Telegram kamu! Silakan cek chat bot."}
            return {"success": False, "message": f"Telegram merespons dengan status HTTP {response.status}"}
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            error_body = ""

        if e.code == 401 or "Unauthorized" in error_body:
            return {"success": False, "message": "Bot Token tidak valid (Unauthorized). Periksa kembali token dari @BotFather."}
        if "chat not found" in error_body:
            return {"success": False, "message": "Chat ID tidak ditemukan. Pastikan kamu sudah klik tombol START di bot Telegram kamu!"}
        return {"success": False, "message": f"Gagal mengirim pesan: HTTP {e.code} ({e.reason})"}
    except Exception as e:
        return {"success": False, "message": f"Kendala koneksi ke server Telegram: {str(e)}"}

