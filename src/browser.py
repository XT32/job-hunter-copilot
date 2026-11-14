import os
import random
import time

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_browser_data")

# Flag hemat RAM dan stealth untuk laptop spek standar / rendah
BROWSER_ARGS = [
    # Hemat memori & CPU
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--renderer-process-limit=2",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=TranslateUI,OptimizationHints,MediaRouter",
    "--disable-sync",
    # Stealth: hilangkan watermark otomasi
    "--disable-blink-features=AutomationControlled",
]

def get_browser_context(playwright_instance, headless=False, slow_mo=150):
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    # Deteksi channel browser lokal jika ada (menghemat resource jika ada Chrome/Edge)
    channel = None
    for ch in ["chrome", "msedge"]:
        try:
            test = playwright_instance.chromium.launch(channel=ch, headless=True)
            test.close()
            channel = ch
            break
        except Exception:
            continue

    kwargs = {
        "user_data_dir": USER_DATA_DIR,
        "headless": headless,
        "slow_mo": slow_mo,
        "args": BROWSER_ARGS,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    if channel:
        kwargs["channel"] = channel

    context = playwright_instance.chromium.launch_persistent_context(**kwargs)
    
    # Injeksi stealth script ke setiap halaman yang terbuka
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.chrome = {
            runtime: {}
        };
    """)
    
    return context

def human_delay(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))
