import os
import random
import time
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_browser_data")

def get_browser_context(playwright_instance, headless=False, slow_mo=200):
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--no-sandbox"
    ]
    
    context = playwright_instance.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=headless,
        slow_mo=slow_mo,
        viewport=None,  # Gunakan window maximize
        args=args,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    
    return context

def human_delay(min_sec=2, max_sec=4):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
