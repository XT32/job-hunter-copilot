"""
Mode CLI interaktif telah dinonaktifkan (UI-First Mode).
Menjalankan file ini akan langsung membuka Web Dashboard di http://127.0.0.1:5000.
"""
import sys
from web_app import start_server


def main():
    print("[i] Mode Terminal CLI telah dinonaktifkan (UI-First Mode).")
    print("[*] Membuka Web Dashboard di http://127.0.0.1:5000 ...")
    start_server(port=5000, auto_open=True)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n[i] Server dihentikan oleh pengguna.")
        sys.exit(0)
