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
from src.maganghub import MagangHubHunter
from src.dealls import DeallsHunter
from src.storage import record_job, load_history, update_job_status, export_history_to_csv
from src.config import load_config, save_config
from src.cover_letter import generate_cover_letter
from src.email_sender import send_cold_email

console = Console()

def check_first_run_onboarding():
    cfg = load_config()
    profile = cfg.get("profile", {})
    if profile.get("field_or_major") == "Teknik Informatika" and not os.path.exists(os.path.join(os.path.dirname(__file__), "data", "history.json")):
        console.print("[bold yellow]Selamat datang di loker-cli![/bold yellow]")
        console.print("[dim]Mari sesuaikan dulu profil jurusan dan target loker kamu:[/dim]\n")
        
        major = Prompt.ask("1. Bidang/jurusan kamu", default="Akuntansi")
        keywords = Prompt.ask("2. Kata kunci target (pisahkan koma)", default="Staff Akuntansi, Finance")
        exp = Prompt.ask("3. Level pengalaman kamu", choices=["fresh_graduate", "junior", "mid", "senior", "all"], default="fresh_graduate")
        
        profile["field_or_major"] = major
        profile["target_keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]
        profile["experience_level"] = exp
        cfg["profile"] = profile
        save_config(cfg)
        console.print("\n[green][OK] Profil berhasil disesuaikan![/green]\n")

def print_header():
    cfg = load_config()
    profile = cfg.get("profile", {})
    keywords = ", ".join(profile.get("target_keywords", []))
    exp = profile.get("experience_level", "all")
    major = profile.get("field_or_major", "-")

    console.print("\n[bold white]loker-cli[/bold white] [dim]v1.4.0 — Multi-Platform Career & Internship Assistant[/dim]")
    console.print(f"[dim]Profil: [cyan]{major}[/cyan] ({exp}) | Target: [cyan]{keywords}[/cyan][/dim]")
    console.print("[dim]" + "─" * 72 + "[/dim]\n")

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
            console.print(f"[*] Memindai lowongan di {platform_name}...")
            jobs = hunter.search_jobs()

            if not jobs:
                console.print(f"[yellow][-] Tidak ada lowongan baru di {platform_name} yang cocok dengan kriteria profil saat ini.[/yellow]")
                context.close()
                return

            console.print(f"[green][+] Ditemukan {len(jobs)} lowongan cocok di {platform_name}.[/green]\n")

            for idx, job in enumerate(jobs, start=1):
                info_text = (
                    f"[bold white]{job['title']}[/bold white]\n"
                    f"Perusahaan : {job['company']}\n"
                    f"Gaji/Uang  : {job['salary']}\n"
                    f"Tautan     : {job['url']}"
                )
                console.print(Panel(info_text, title=f"Lowongan {idx}/{len(jobs)} ({platform_name})", expand=False))

                choice = Prompt.ask(
                    "Pilihan ([bold green]y[/bold green]=Lamar, [bold yellow]s[/bold yellow]=Lewati, [bold cyan]o[/bold cyan]=Buka detail, [bold magenta]c[/bold magenta]=Cover Letter, [bold red]q[/bold red]=Berhenti)",
                    choices=["y", "s", "o", "c", "q"],
                    default="y",
                    show_choices=False
                )

                if choice == "q":
                    console.print("[*] Sesi dihentikan.")
                    break
                
                elif choice == "c":
                    letter = generate_cover_letter(job["title"], job["company"], profile, preset="formal")
                    console.print("\n[bold cyan]Surat Lamaran (Cover Letter) Otomatis:[/bold cyan]")
                    console.print(Panel(letter, expand=False))
                    continue_choice = Prompt.ask("Ingin langsung melamar sekarang? (y/s)", choices=["y", "s"], default="y")
                    if continue_choice == "s":
                        record_job(job["url"], job["title"], job["company"], status="skipped", notes="Dilewati setelah cek cover letter")
                        continue

                elif choice == "s":
                    record_job(job["url"], job["title"], job["company"], status="skipped", notes=f"Dilewati manual ({platform_name})")
                    console.print("[dim][-] Dilewati.[/dim]\n")
                    continue

                elif choice == "o":
                    console.print("[*] Membuka halaman di browser...")
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

                else:
                    console.print(f"[red][ERR] {result['message']}[/red]\n")

                human_delay(cfg.get("min_delay_sec", 2), cfg.get("max_delay_sec", 4))

        except Exception as e:
            console.print(f"[red][ERROR] Kendala runtime: {e}[/red]")
        finally:
            context.close()

def direct_email_menu():
    cfg = load_config()
    smtp_cfg = cfg.get("smtp", {})
    profile = cfg.get("profile", {})

    console.print("\n[bold cyan]Kirim Lamaran Langsung ke Email HRD (Cold Email):[/bold cyan]")
    to_email = Prompt.ask("Email HRD tujuan")
    company = Prompt.ask("Nama Perusahaan tujuan")
    role = Prompt.ask("Posisi yang dilamar")
    subject = f"Lamaran Pekerjaan: {role} - {profile.get('applicant_name', 'Pelamar')}"

    body = generate_cover_letter(role, company, profile, preset="formal")
    console.print("\n[bold]Isi Email yang Akan Dikirim:[/bold]")
    console.print(Panel(body, title=subject, expand=False))

    if Confirm.ask("Kirim email sekarang beserta CV?"):
        cv_path = smtp_cfg.get("cv_path", "attachments/CV.pdf")
        res = send_cold_email(to_email, subject, body, attachment_path=cv_path, smtp_config=smtp_cfg)
        if res["success"]:
            record_job(f"mailto:{to_email}", role, company, status="applied", notes="Cold Email Langsung")
            console.print(f"[green][OK] {res['message']}[/green]\n")
        else:
            console.print(f"[red][x] {res['message']}[/red]\n")

def kanban_menu():
    hist = load_history()
    applied = hist.get("applied", [])
    interview = hist.get("interview", [])
    offering = hist.get("offering", [])
    rejected = hist.get("rejected", [])

    table = Table(title="Papan Pelacak Lamaran (Pipeline)", show_header=True)
    table.add_column("Status", style="bold")
    table.add_column("Jumlah", style="cyan")
    table.add_column("Keterangan", style="dim")

    table.add_row("[green]Terkirim (Applied)[/green]", str(len(applied)), "Lamaran berhasil terkirim")
    table.add_row("[yellow]Interview[/yellow]", str(len(interview)), "Mendapat panggilan wawancara")
    table.add_row("[bold green]Offering[/bold green]", str(len(offering)), "Menerima tawaran pekerjaan")
    table.add_row("[red]Ditolak[/red]", str(len(rejected)), "Tidak lolos seleksi")

    console.print(table)

    if Confirm.ask("\nPerbarui status salah satu lamaran?"):
        target_url = Prompt.ask("Masukkan URL / Email lamaran yang ingin diubah")
        new_stat = Prompt.ask("Status baru", choices=["applied", "interview", "offering", "rejected"])
        notes = Prompt.ask("Catatan perkembangan")
        if update_job_status(target_url, new_stat, notes):
            console.print("[green][OK] Status berhasil diperbarui![/green]\n")
        else:
            console.print("[red][x] URL tidak ditemukan dalam riwayat.[/red]\n")

    if Confirm.ask("Unduh seluruh riwayat ke file CSV/Excel?"):
        path = export_history_to_csv()
        console.print(f"[green][OK] File diekspor ke: {path}[/green]\n")

def settings_menu():
    cfg = load_config()
    profile = cfg.get("profile", {})
    screening = cfg.get("screening_defaults", {})
    
    console.print("\n[bold]Pengaturan Profil & Auto-Fill Screening:[/bold]")
    console.print(f"1. Bidang/Jurusan      : [cyan]{profile.get('field_or_major', '-')}[/cyan]")
    console.print(f"2. Kata Kunci Target   : [cyan]{', '.join(profile.get('target_keywords', []))}[/cyan]")
    console.print(f"3. Level Pengalaman    : [cyan]{profile.get('experience_level', 'all')}[/cyan]")
    console.print(f"4. Ekspektasi Gaji     : [cyan]Rp {screening.get('expected_salary', '6000000')}[/cyan]")

    if Confirm.ask("\nApakah kamu ingin mengubah data profil ini?"):
        major = Prompt.ask("Bidang/jurusan kamu", default=profile.get("field_or_major", "Akuntansi"))
        keywords_input = Prompt.ask("Kata kunci target (pisahkan koma)", default=", ".join(profile.get("target_keywords", ["Staff"])))
        exp = Prompt.ask("Level pengalaman", choices=["fresh_graduate", "junior", "mid", "senior", "all"], default=profile.get("experience_level", "junior"))
        salary = Prompt.ask("Ekspektasi gaji default (angka)", default=str(screening.get("expected_salary", "6000000")))

        profile["field_or_major"] = major
        profile["target_keywords"] = [k.strip() for k in keywords_input.split(",") if k.strip()]
        profile["experience_level"] = exp
        screening["expected_salary"] = salary
        
        cfg["profile"] = profile
        cfg["screening_defaults"] = screening
        save_config(cfg)
        console.print("[green][OK] Pengaturan diperbarui.[/green]\n")

def main():
    check_first_run_onboarding()
    while True:
        print_header()
        console.print("[1] Review & Lamar di [bold cyan]Glints Indonesia[/bold cyan]")
        console.print("[2] Review & Lamar di [bold magenta]JobStreet Indonesia (SEEK)[/bold magenta]")
        console.print("[3] Cari Program Magang di [bold green]MagangHub Kemnaker[/bold green]")
        console.print("[4] Review & Lamar di [bold yellow]Dealls Jobs Indonesia[/bold yellow]")
        console.print("[5] Kirim Lamaran Langsung ke Email HRD (Cold Email)")
        console.print("[6] Pelacak Lamaran (Pipeline Status & Ekspor CSV)")
        console.print("[7] Atur Profil & Gaji Default")
        console.print("[8] Keluar")
        
        choice = Prompt.ask("\nPilih menu", choices=["1", "2", "3", "4", "5", "6", "7", "8"], default="1")
        
        if choice == "1":
            run_hunter_session(GlintsHunter, "Glints")
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "2":
            run_hunter_session(JobstreetHunter, "JobStreet")
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "3":
            run_hunter_session(MagangHubHunter, "MagangHub")
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "4":
            run_hunter_session(DeallsHunter, "Dealls")
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "5":
            direct_email_menu()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "6":
            kanban_menu()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "7":
            settings_menu()
            Prompt.ask("\nTekan ENTER untuk kembali")
        elif choice == "8":
            console.print("[dim]Sampai jumpa.[/dim]\n")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Dibatalkan oleh pengguna. Sampai jumpa.[/dim]\n")
        sys.exit(0)
