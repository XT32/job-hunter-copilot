import json
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from playwright.sync_api import sync_playwright

from src.browser import get_browser_context, human_delay
from src.glints import GlintsHunter
from src.storage import record_job, load_history

console = Console()
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "keyword": "Python Developer",
            "country": "ID",
            "min_delay_sec": 2,
            "max_delay_sec": 4,
            "auto_skip_already_seen": True,
            "slow_mo_ms": 150
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        return default_config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def print_header():
    cfg = load_config()
    console.print("\n[bold white]loker-cli[/bold white] [dim]v1.0.0 — Tool Bantu Review & Lamar Pekerjaan[/dim]")
    console.print(f"[dim]Kata Kunci Aktif: [cyan]{cfg.get('keyword')}[/cyan] | Platform: [cyan]Glints ID[/cyan][/dim]")
    console.print("[dim]" + "─" * 60 + "[/dim]\n")

def run_job_flow():
    cfg = load_config()
    keyword = cfg.get("keyword", "Python Developer")

    console.print(f"[*] Menyiapkan browser (kata kunci: '{keyword}')...")

    with sync_playwright() as p:
        context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
        page = context.new_page()
        hunter = GlintsHunter(page, cfg)

        try:
            console.print("[*] Mengambil daftar lowongan dari Glints...")
            jobs = hunter.search_jobs(keyword)

            if not jobs:
                console.print("[yellow][-] Tidak ada lowongan baru yang ditemukan (atau sudah pernah ditinjau semua).[/yellow]")
                context.close()
                return

            console.print(f"[green][+] Ditemukan {len(jobs)} lowongan baru untuk ditinjau.[/green]\n")

            for idx, job in enumerate(jobs, start=1):
                info_text = (
                    f"[bold white]{job['title']}[/bold white]\n"
                    f"Perusahaan : {job['company']}\n"
                    f"Gaji       : {job['salary']}\n"
                    f"Tautan     : {job['url']}"
                )
                console.print(Panel(info_text, title=f"Lowongan {idx}/{len(jobs)}", expand=False))

                # Pilihan interaktif
                choice = Prompt.ask(
                    "Pilihan ([bold green]y[/bold green]=Lamar, [bold yellow]s[/bold yellow]=Lewati, [bold cyan]o[/bold cyan]=Buka di browser, [bold red]q[/bold red]=Berhenti)",
                    choices=["y", "s", "o", "q"],
                    default="y",
                    show_choices=False
                )

                if choice == "q":
                    console.print("[*] Proses dihentikan pengguna.")
                    break
                
                elif choice == "s":
                    record_job(job["url"], job["title"], job["company"], status="skipped")
                    console.print("[dim][-] Dilewati.[/dim]\n")
                    continue

                elif choice == "o":
                    console.print("[*] Membuka halaman detail di browser...")
                    page.goto(job["url"], wait_until="domcontentloaded")
                    second_choice = Prompt.ask("Lamar lowongan ini? (y/s)", choices=["y", "s"], default="y")
                    if second_choice == "s":
                        record_job(job["url"], job["title"], job["company"], status="skipped")
                        continue

                # Proses lamar
                console.print("[*] Mengeksekusi tombol lamar...")
                result = hunter.inspect_and_apply(job["url"])

                if result["status"] == "success":
                    record_job(job["url"], job["title"], job["company"], status="applied")
                    console.print("[green][OK] Lamaran terkirim.[/green]\n")
                
                elif result["status"] == "manual_action_needed":
                    console.print(f"[yellow][!] {result['message']}[/yellow]")
                    Prompt.ask("Silakan isi form di layar browser, lalu tekan ENTER di sini jika sudah")
                    record_job(job["url"], job["title"], job["company"], status="applied", notes="Diselesaikan manual")
                    console.print("[green][OK] Dicatat ke riwayat.[/green]\n")

                elif result["status"] == "external_link":
                    console.print(f"[yellow][!] {result['message']}[/yellow]")
                    record_job(job["url"], job["title"], job["company"], status="skipped", notes="Link eksternal")
                    console.print("[dim][-] Dicatat sebagai tautan eksternal.[/dim]\n")

                elif result["status"] == "already_applied":
                    record_job(job["url"], job["title"], job["company"], status="applied", notes="Sudah pernah dilamar")
                    console.print("[yellow][-] Lowongan sudah pernah dilamar sebelumnya.[/yellow]\n")

                else:
                    console.print(f"[red][ERR] {result['message']}[/red]\n")

                human_delay(cfg.get("min_delay_sec", 2), cfg.get("max_delay_sec", 4))

        except Exception as e:
            console.print(f"[red][ERROR] Kendala runtime: {e}[/red]")
        finally:
            context.close()

def view_history():
    hist = load_history()
    applied = hist.get("applied", [])
    skipped = hist.get("skipped", [])

    table = Table(title="Riwayat Lamaran", show_header=True)
    table.add_column("No", style="dim", width=4)
    table.add_column("Posisi", style="white")
    table.add_column("Perusahaan", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Tanggal", style="dim")

    count = 1
    for item in applied[-15:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[green]Dilamar[/green]", item.get("timestamp", "-"))
        count += 1

    for item in skipped[-10:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[red]Dilewati[/red]", item.get("timestamp", "-"))
        count += 1

    console.print(table)
    console.print(f"[dim]Total Dilamar: {len(applied)} | Total Dilewati: {len(skipped)}[/dim]\n")

def settings_menu():
    cfg = load_config()
    console.print(f"Kata Kunci saat ini: [cyan]{cfg.get('keyword')}[/cyan]")
    if Confirm.ask("Ganti kata kunci pencarian?"):
        new_kw = Prompt.ask("Masukkan kata kunci baru", default=cfg.get("keyword"))
        cfg["keyword"] = new_kw
        save_config(cfg)
        console.print("[green][OK] Kata kunci diperbarui.[/green]\n")

def main():
    while True:
        print_header()
        console.print("[1] Jalankan Review & Lamar (Glints)")
        console.print("[2] Cek Riwayat Lamaran")
        console.print("[3] Ganti Kata Kunci / Pengaturan")
        console.print("[4] Keluar")
        
        choice = Prompt.ask("\nPilih menu", choices=["1", "2", "3", "4"], default="1")
        
        if choice == "1":
            run_job_flow()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "2":
            view_history()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "3":
            settings_menu()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "4":
            console.print("[dim]Sampai jumpa.[/dim]\n")
            sys.exit(0)

if __name__ == "__main__":
    main()
