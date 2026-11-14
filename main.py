import json
import os
import sys
import time
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
            "slow_mo_ms": 200
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        return default_config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def print_banner():
    banner_text = """[bold cyan]
   ████████╗ ██████╗ ██████╗     ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗ 
   ╚══██╔══╝██╔═══██╗██╔══██╗    ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
      ██║   ██║   ██║██████╔╝    ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝
      ██║   ██║   ██║██╔══██╗    ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
      ██║   ╚██████╔╝██████╔╝    ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║
      ╚═╝    ╚═════╝ ╚═════╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    [/bold cyan]
    [bold yellow]🤖 Auto Job Search & Copilot Application Tool | 100% Free & Open Source[/bold yellow]
    """
    console.print(banner_text)

def run_copilot():
    cfg = load_config()
    keyword = cfg.get("keyword", "Python Developer")

    console.print(Panel(f"[bold green]Mempersiapkan browser untuk pencarian: [yellow]'{keyword}'[/yellow]...[/bold green]", title="🚀 Mode Copilot"))
    console.print("[dim]Sedang membuka Chrome dengan sesi tersimpan... Mohon tunggu.[/dim]")

    with sync_playwright() as p:
        context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 200))
        page = context.new_page()
        hunter = GlintsHunter(page, cfg)

        try:
            console.print("[cyan][*] Mencari lowongan di Glints...[/cyan]")
            jobs = hunter.search_jobs(keyword)

            if not jobs:
                console.print("[yellow][!] Tidak ada lowongan baru ditemukan (atau semua sudah pernah dievaluasi sebelumnya).[/yellow]")
                context.close()
                return

            console.print(f"[bold green][✓] Ditemukan {len(jobs)} lowongan baru yang siap dievaluasi![/bold green]\n")

            for idx, job in enumerate(jobs, start=1):
                info_text = f"""[bold white]Posisi[/bold white]     : [bold cyan]{job['title']}[/bold cyan]
[bold white]Perusahaan[/bold white] : [bold magenta]{job['company']}[/bold magenta]
[bold white]Gaji[/bold white]       : [green]{job['salary']}[/green]
[bold white]URL[/bold white]        : [link={job['url']}]{job['url']}[/link]"""

                console.print(Panel(info_text, title=f"🎯 Lowongan [{idx}/{len(jobs)}]"))

                # Toggle pilihan manual
                choice = Prompt.ask(
                    "[bold yellow]Tindakan[/bold yellow]",
                    choices=["y", "s", "o", "q"],
                    default="y",
                    show_choices=False,
                    console=console
                )
                # Keterangan:
                # y = Lamar
                # s = Skip
                # o = Buka halaman di browser dulu
                # q = Keluar

                if choice == "q":
                    console.print("[yellow][*] Sesi Copilot dihentikan oleh pengguna.[/yellow]")
                    break
                
                elif choice == "s":
                    record_job(job["url"], job["title"], job["company"], status="skipped")
                    console.print("[dim italic][-] Lowongan dilewati dan dicatat ke riwayat.[/dim italic]\n")
                    continue

                elif choice == "o":
                    console.print("[cyan][*] Membuka halaman detail di browser...[/cyan]")
                    page.goto(job["url"], wait_until="domcontentloaded")
                    # Tanyakan lagi setelah melihat
                    second_choice = Prompt.ask("Setelah melihat, mau dilamar? (y/s)", choices=["y", "s"], default="y")
                    if second_choice == "s":
                        record_job(job["url"], job["title"], job["company"], status="skipped")
                        continue

                # Eksekusi Lamaran
                console.print("[bold cyan][+] Mengeksekusi proses lamaran di browser...[/bold cyan]")
                result = hunter.inspect_and_apply(job["url"])

                if result["status"] == "success":
                    record_job(job["url"], job["title"], job["company"], status="applied")
                    console.print("[bold green][✓] Sukses! Lamaran berhasil dikirim.[/bold green]\n")
                
                elif result["status"] == "manual_action_needed":
                    console.print(f"[bold yellow][!] {result['message']}[/bold yellow]")
                    Prompt.ask("Selesaikan pengisian di browser, lalu tekan ENTER di sini jika sudah beres")
                    record_job(job["url"], job["title"], job["company"], status="applied", notes="Manual submission completed")
                    console.print("[green][✓] Dicatat sebagai berhasil dilamar.[/green]\n")

                elif result["status"] == "already_applied":
                    record_job(job["url"], job["title"], job["company"], status="applied", notes="Already applied earlier")
                    console.print("[yellow][-] Info: Lowongan ini ternyata sudah pernah dilamar sebelumnya.[/yellow]\n")

                else:
                    console.print(f"[red][x] Gagal apply: {result['message']}[/red]\n")

                # Jeda manusiawi antar lamaran
                human_delay(cfg.get("min_delay_sec", 2), cfg.get("max_delay_sec", 4))

        except Exception as e:
            console.print(f"[bold red][ERROR] Terjadi kendala: {e}[/bold red]")
        finally:
            console.print("[dim]Menutup sesi browser...[/dim]")
            context.close()

def view_history():
    hist = load_history()
    applied = hist.get("applied", [])
    skipped = hist.get("skipped", [])

    table = Table(title="📊 Riwayat Lowongan Pekerjaan", show_header=True, header_style="bold magenta")
    table.add_column("No", style="dim", width=4)
    table.add_column("Posisi", style="cyan")
    table.add_column("Perusahaan", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Waktu", style="dim")

    count = 1
    for item in applied[-15:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[green]Dilamar[/green]", item.get("timestamp", "-"))
        count += 1

    for item in skipped[-10:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[red]Dilewati[/red]", item.get("timestamp", "-"))
        count += 1

    console.print(table)
    console.print(f"\n[bold]Total Dilamar: [green]{len(applied)}[/green] | Total Dilewati: [red]{len(skipped)}[/red][/bold]\n")

def settings_menu():
    cfg = load_config()
    console.print("\n[bold cyan]⚙️ Pengaturan Saat Ini:[/bold cyan]")
    console.print(f"1. Kata Kunci (Keyword) : [yellow]{cfg.get('keyword')}[/yellow]")
    console.print(f"2. Auto Skip Duplikat    : [yellow]{cfg.get('auto_skip_already_seen')}[/yellow]")
    
    if Confirm.ask("\nApakah kamu ingin mengubah kata kunci pencarian?"):
        new_kw = Prompt.ask("Masukkan kata kunci baru", default=cfg.get("keyword"))
        cfg["keyword"] = new_kw
        save_config(cfg)
        console.print("[bold green][✓] Pengaturan berhasil disimpan![/bold green]\n")

def main_menu():
    while True:
        print_banner()
        console.print("[bold white]PILIHAN MENU:[/bold white]")
        console.print("[1] 🚀 [bold green]Jalankan Copilot[/bold green] (Cari & Toggle Lamar)")
        console.print("[2] 📊 [bold cyan]Lihat Riwayat Lamaran[/bold cyan]")
        console.print("[3] ⚙️  [bold yellow]Ubah Pengaturan[/bold yellow] (Kata Kunci / Preferensi)")
        console.print("[4] 🚪 [bold red]Keluar[/bold red]")
        
        choice = Prompt.ask("\nPilih menu [1-4]", choices=["1", "2", "3", "4"], default="1")
        
        if choice == "1":
            run_copilot()
            Prompt.ask("\nTekan ENTER untuk kembali ke menu utama")
        elif choice == "2":
            view_history()
            Prompt.ask("\nTekan ENTER untuk kembali ke menu utama")
        elif choice == "3":
            settings_menu()
            Prompt.ask("\nTekan ENTER untuk kembali ke menu utama")
        elif choice == "4":
            console.print("\n[bold cyan]Terima kasih telah menggunakan Job Hunter Copilot! Semoga segera dapat pekerjaan impian! 🚀[/bold cyan]\n")
            sys.exit(0)

if __name__ == "__main__":
    main_menu()
