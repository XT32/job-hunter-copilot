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
from src.config import load_config, save_config

console = Console()

def print_header():
    cfg = load_config()
    profile = cfg.get("profile", {})
    keywords = ", ".join(profile.get("target_keywords", []))
    exp = profile.get("experience_level", "all")
    major = profile.get("field_or_major", "-")

    console.print("\n[bold white]loker-cli[/bold white] [dim]v1.1.0 — Tool Bantu Review & Lamar Pekerjaan[/dim]")
    console.print(f"[dim]Profil/Jurusan: [cyan]{major}[/cyan] | Level: [cyan]{exp}[/cyan] | Target: [cyan]{keywords}[/cyan][/dim]")
    console.print("[dim]" + "─" * 65 + "[/dim]\n")

def run_job_flow():
    cfg = load_config()
    profile = cfg.get("profile", {})
    target_kws = profile.get("target_keywords", ["Software Engineer"])

    console.print(f"[*] Menyiapkan browser untuk target: {', '.join(target_kws)}...")

    with sync_playwright() as p:
        context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
        page = context.new_page()
        hunter = GlintsHunter(page, cfg)

        try:
            console.print("[*] Mengambil daftar lowongan yang sesuai kriteria profil...")
            jobs = hunter.search_jobs()

            if not jobs:
                console.print("[yellow][-] Tidak ada lowongan baru yang cocok dengan kriteria profil kamu saat ini.[/yellow]")
                context.close()
                return

            console.print(f"[green][+] Ditemukan {len(jobs)} lowongan cocok yang siap ditinjau.[/green]\n")

            for idx, job in enumerate(jobs, start=1):
                info_text = (
                    f"[bold white]{job['title']}[/bold white]\n"
                    f"Perusahaan : {job['company']}\n"
                    f"Gaji       : {job['salary']}\n"
                    f"Tautan     : {job['url']}"
                )
                console.print(Panel(info_text, title=f"Lowongan {idx}/{len(jobs)}", expand=False))

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
                    record_job(job["url"], job["title"], job["company"], status="skipped", notes="Dilewati manual")
                    console.print("[dim][-] Dilewati.[/dim]\n")
                    continue

                elif choice == "o":
                    console.print("[*] Membuka halaman detail di browser...")
                    page.goto(job["url"], wait_until="domcontentloaded")
                    second_choice = Prompt.ask("Lamar lowongan ini? (y/s)", choices=["y", "s"], default="y")
                    if second_choice == "s":
                        record_job(job["url"], job["title"], job["company"], status="skipped", notes="Dilewati setelah ditinjau")
                        continue

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
    table.add_column("Keterangan", style="dim")

    count = 1
    for item in applied[-15:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[green]Dilamar[/green]", item.get("notes", "-"))
        count += 1

    for item in skipped[-10:]:
        table.add_row(str(count), item.get("title", "-"), item.get("company", "-"), "[red]Dilewati[/red]", item.get("notes", "-"))
        count += 1

    console.print(table)
    console.print(f"[dim]Total Dilamar: {len(applied)} | Total Dilewati: {len(skipped)}[/dim]\n")

def settings_menu():
    cfg = load_config()
    profile = cfg.get("profile", {})
    
    console.print("\n[bold]Pengaturan Profil Pencari Kerja:[/bold]")
    console.print(f"1. Bidang/Jurusan      : [cyan]{profile.get('field_or_major', '-')}[/cyan]")
    console.print(f"2. Kata Kunci Target   : [cyan]{', '.join(profile.get('target_keywords', []))}[/cyan]")
    console.print(f"3. Level Pengalaman    : [cyan]{profile.get('experience_level', 'all')}[/cyan]")
    console.print(f"4. Kata Kunci Terlarang: [cyan]{', '.join(profile.get('blacklist_keywords', [])[:4])}...[/cyan]")

    if Confirm.ask("\nApakah kamu ingin mengubah profil/target loker?"):
        major = Prompt.ask("Masukkan bidang/jurusan kamu", default=profile.get("field_or_major", "Teknik Informatika"))
        keywords_input = Prompt.ask(
            "Masukkan kata kunci target (pisahkan dengan koma)",
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
    while True:
        print_header()
        console.print("[1] Jalankan Review & Lamar (Glints)")
        console.print("[2] Cek Riwayat Lamaran")
        console.print("[3] Atur Profil & Kata Kunci Jurusan")
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
