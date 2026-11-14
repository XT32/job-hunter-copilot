import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from playwright.sync_api import sync_playwright

from src.browser import get_browser_context, human_delay
from src.glints import GlintsHunter
from src.jobstreet import JobstreetHunter
from src.storage import record_job, load_history, export_history_to_csv
from src.config import load_config, save_config

console = Console()

def check_first_run_onboarding():
    """Memandu pengguna baru untuk mengatur jurusan dan kata kunci target saat pertama kali buka"""
    cfg = load_config()
    profile = cfg.get("profile", {})
    if profile.get("field_or_major") == "Teknik Informatika" and not os.path.exists(os.path.join(os.path.dirname(__file__), "data", "history.json")):
        console.print("[bold yellow]Selamat datang di loker-cli![/bold yellow]")
        console.print("[dim]Mari kita sesuaikan dulu jurusan dan target pekerjaan kamu agar pencarian akurat.[/dim]\n")
        
        major = Prompt.ask("1. Masukkan bidang/jurusan kamu", default="Akuntansi")
        keywords = Prompt.ask("2. Masukkan kata kunci pekerjaan yang dicari (pisahkan koma)", default="Staff Akuntansi, Finance")
        exp = Prompt.ask("3. Tingkat pengalaman kamu", choices=["fresh_graduate", "junior", "mid", "senior", "all"], default="fresh_graduate")
        
        profile["field_or_major"] = major
        profile["target_keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]
        profile["experience_level"] = exp
        cfg["profile"] = profile
        save_config(cfg)
        console.print("\n[green][OK] Profil berhasil disesuaikan! Memulai menu utama...[/green]\n")

def print_header():
    cfg = load_config()
    profile = cfg.get("profile", {})
    keywords = ", ".join(profile.get("target_keywords", []))
    exp = profile.get("experience_level", "all")
    major = profile.get("field_or_major", "-")

    console.print("\n[bold white]loker-cli[/bold white] [dim]v1.2.0 — Multi-Platform Job Review & Apply Assistant[/dim]")
    console.print(f"[dim]Profil: [cyan]{major}[/cyan] ({exp}) | Target: [cyan]{keywords}[/cyan][/dim]")
    console.print("[dim]" + "─" * 68 + "[/dim]\n")

def run_hunter_session(HunterClass, platform_name):
    cfg = load_config()
    profile = cfg.get("profile", {})
    target_kws = profile.get("target_keywords", ["Staff"])

    console.print(f"[*] Menyiapkan browser untuk [bold cyan]{platform_name}[/bold cyan] (Target: {', '.join(target_kws)})...")

    with sync_playwright() as p:
        context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
        page = context.new_page()
        hunter = HunterClass(page, cfg)

        try:
            console.print(f"[*] Memindai lowongan di {platform_name} sesuai kriteria profil...")
            jobs = hunter.search_jobs()

            if not jobs:
                console.print(f"[yellow][-] Tidak ada lowongan baru di {platform_name} yang cocok dengan kriteria profil saat ini.[/yellow]")
                context.close()
                return

            console.print(f"[green][+] Ditemukan {len(jobs)} lowongan cocok di {platform_name} yang siap ditinjau.[/green]\n")

            for idx, job in enumerate(jobs, start=1):
                info_text = (
                    f"[bold white]{job['title']}[/bold white]\n"
                    f"Perusahaan : {job['company']}\n"
                    f"Gaji       : {job['salary']}\n"
                    f"Tautan     : {job['url']}"
                )
                console.print(Panel(info_text, title=f"Lowongan {idx}/{len(jobs)} ({platform_name})", expand=False))

                choice = Prompt.ask(
                    "Pilihan ([bold green]y[/bold green]=Lamar, [bold yellow]s[/bold yellow]=Lewati, [bold cyan]o[/bold cyan]=Buka di browser, [bold red]q[/bold red]=Berhenti)",
                    choices=["y", "s", "o", "q"],
                    default="y",
                    show_choices=False
                )

                if choice == "q":
                    console.print("[*] Sesi dihentikan oleh pengguna.")
                    break
                
                elif choice == "s":
                    record_job(job["url"], job["title"], job["company"], status="skipped", notes=f"Dilewati manual ({platform_name})")
                    console.print("[dim][-] Dilewati.[/dim]\n")
                    continue

                elif choice == "o":
                    console.print("[*] Membuka halaman detail di browser...")
                    page.goto(job["url"], wait_until="domcontentloaded")
                    second_choice = Prompt.ask("Lamar lowongan ini? (y/s)", choices=["y", "s"], default="y")
                    if second_choice == "s":
                        record_job(job["url"], job["title"], job["company"], status="skipped", notes="Dilewati setelah ditinjau")
                        continue

                console.print(f"[*] Mengeksekusi proses lamaran di {platform_name}...")
                result = hunter.inspect_and_apply(job["url"])

                if result["status"] == "success":
                    record_job(job["url"], job["title"], job["company"], status="applied", notes=f"Sukses ({platform_name})")
                    console.print("[green][OK] Lamaran terkirim.[/green]\n")
                
                elif result["status"] == "manual_action_needed":
                    console.print(f"[yellow][!] {result['message']}[/yellow]")
                    Prompt.ask("Selesaikan pengisian di layar browser, lalu tekan ENTER di sini")
                    record_job(job["url"], job["title"], job["company"], status="applied", notes=f"Diselesaikan manual ({platform_name})")
                    console.print("[green][OK] Dicatat ke riwayat.[/green]\n")

                elif result["status"] == "external_link":
                    console.print(f"[yellow][!] {result['message']}[/yellow]")
                    record_job(job["url"], job["title"], job["company"], status="skipped", notes=f"Link eksternal ({platform_name})")
                    console.print("[dim][-] Dicatat sebagai tautan eksternal.[/dim]\n")

                elif result["status"] == "already_applied":
                    record_job(job["url"], job["title"], job["company"], status="applied", notes=f"Sudah pernah dilamar ({platform_name})")
                    console.print("[yellow][-] Lowongan sudah pernah dilamar sebelumnya.[/yellow]\n")

                else:
                    console.print(f"[red][ERR] {result['message']}[/red]\n")

                human_delay(cfg.get("min_delay_sec", 2), cfg.get("max_delay_sec", 4))

        except Exception as e:
            console.print(f"[red][ERROR] Kendala runtime: {e}[/red]")
        finally:
            context.close()

def view_and_export_history():
    hist = load_history()
    applied = hist.get("applied", [])
    skipped = hist.get("skipped", [])

    table = Table(title="Riwayat Lamaran Terkini", show_header=True)
    table.add_column("No", style="dim", width=4)
    table.add_column("Posisi", style="white")
    table.add_column("Perusahaan", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Keterangan", style="dim")

    count = 1
    for item in applied[-10:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[green]Dilamar[/green]", item.get("notes", "-"))
        count += 1

    for item in skipped[-5:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[red]Dilewati[/red]", item.get("notes", "-"))
        count += 1

    console.print(table)
    console.print(f"[dim]Total Dilamar: {len(applied)} | Total Dilewati: {len(skipped)}[/dim]\n")

    if Confirm.ask("Apakah kamu ingin mengekspor seluruh riwayat ini ke file CSV/Excel?"):
        path = export_history_to_csv()
        console.print(f"[green][OK] File berhasil diekspor ke: [bold white]{path}[/bold white][/green]\n")

def settings_menu():
    cfg = load_config()
    profile = cfg.get("profile", {})
    
    console.print("\n[bold]Pengaturan Profil Pencari Kerja:[/bold]")
    console.print(f"1. Bidang/Jurusan      : [cyan]{profile.get('field_or_major', '-')}[/cyan]")
    console.print(f"2. Kata Kunci Target   : [cyan]{', '.join(profile.get('target_keywords', []))}[/cyan]")
    console.print(f"3. Level Pengalaman    : [cyan]{profile.get('experience_level', 'all')}[/cyan]")
    console.print(f"4. Kata Kunci Terlarang: [cyan]{', '.join(profile.get('blacklist_keywords', [])[:5])}...[/cyan]")

    if Confirm.ask("\nApakah kamu ingin mengubah data profil ini?"):
        major = Prompt.ask("Masukkan bidang/jurusan kamu", default=profile.get("field_or_major", "Akuntansi"))
        keywords_input = Prompt.ask(
            "Masukkan kata kunci target (pisahkan koma)",
            default=", ".join(profile.get("target_keywords", ["Staff"]))
        )
        exp = Prompt.ask(
            "Level pengalaman kamu",
            choices=["fresh_graduate", "junior", "mid", "senior", "all"],
            default=profile.get("experience_level", "junior")
        )

        profile["field_or_major"] = major
        profile["target_keywords"] = [k.strip() for k in keywords_input.split(",") if k.strip()]
        profile["experience_level"] = exp
        cfg["profile"] = profile
        save_config(cfg)
        console.print("[green][OK] Profil berhasil diperbarui.[/green]\n")

def main():
    check_first_run_onboarding()
    while True:
        print_header()
        console.print("[1] Review & Lamar di [bold cyan]Glints Indonesia[/bold cyan]")
        console.print("[2] Review & Lamar di [bold magenta]JobStreet Indonesia (SEEK)[/bold magenta]")
        console.print("[3] Cek Riwayat & Ekspor CSV")
        console.print("[4] Atur Profil & Kata Kunci Jurusan")
        console.print("[5] Keluar")
        
        choice = Prompt.ask("\nPilih menu", choices=["1", "2", "3", "4", "5"], default="1")
        
        if choice == "1":
            run_hunter_session(GlintsHunter, "Glints")
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "2":
            run_hunter_session(JobstreetHunter, "JobStreet")
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "3":
            view_and_export_history()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "4":
            settings_menu()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "5":
            console.print("[dim]Sampai jumpa.[/dim]\n")
            sys.exit(0)

if __name__ == "__main__":
    main()
