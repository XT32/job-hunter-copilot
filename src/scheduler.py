import threading
import time
from src.notifier import send_telegram_alert

class AutoHuntScheduler:
    def __init__(self, hunter_map, config_loader):
        self.hunter_map = hunter_map
        self.config_loader = config_loader
        self.running = False
        self.thread = None
        self.last_run = None
        self.total_discovered = 0

    def start(self, interval_minutes=120):
        if self.running:
            return False

        self.running = True
        def loop():
            while self.running:
                cfg = self.config_loader()
                tg_cfg = cfg.get("telegram", {})
                
                print("\n[⏰ Scheduler] Memulai pemindaian otomatis di latar belakang...")
                self.last_run = time.strftime("%Y-%m-%d %H:%M:%S")

                # Scan platform
                for p_name, (HunterClass, label) in self.hunter_map.items():
                    if not self.running:
                        break
                    try:
                        # Di background scheduler kita hanya deteksi lowongan baru
                        print(f"[⏰ Scheduler] Memindai {label}...")
                    except Exception as e:
                        print(f"[!] Scheduler error ({label}): {e}")

                # Tidur selama interval_minutes
                for _ in range(interval_minutes * 60):
                    if not self.running:
                        break
                    time.sleep(1)

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        return True

    def get_status(self):
        return {
            "active": self.running,
            "last_run": self.last_run or "Belum pernah berjalan",
            "total_discovered": self.total_discovered
        }
