import os
import sys
import urllib.parse
import webbrowser
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
from src.storage import record_job, load_history, update_job_status, export_history_to_csv, get_analytics_summary
from src.config import load_config, save_config
from src.cover_letter import generate_cover_letter
from src.email_sender import send_cold_email
from src.scam_detector import check_for_red_flags
from src.salary_guide import suggest_salary_range, get_umr_by_location

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

    console.print("\n[bold white]loker-cli[/bold white] [dim]v1.5.0 — Multi-Platform Career & Internship Assistant[/dim]")
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
                # Deteksi penipuan / red flag
                red_flag = check_for_red_flags(
                    title=job["title"],
                    company=job["company"],
                    description=job.get("description", ""),
                    location=job.get("location", "")
                )

                info_text = (
                    f"[bold white]{job['title']}[/bold white]\n"
                    f"Perusahaan : {job['company']}\n"
                    f"Gaji/Uang  : {job['salary']}\n"
                    f"Tautan     : {job['url']}"
                )
                console.print(Panel(info_text, title=f"Lowongan {idx}/{len(jobs)} ({platform_name})", expand=False))

                if red_flag["is_red_flag"]:
                    border_style = "red" if red_flag["risk_level"] == "danger" else "yellow"
                    flag_text = (
                        f"[bold red]⚠️ PERINGATAN POTENSI RED FLAG:[/bold red]\n"
                        f"• {chr(10).join('• ' + f for f in red_flag['flags'])}\n"
                        f"[dim]{red_flag['advice']}[/dim]"
                    )
                    console.print(Panel(flag_text, border_style=border_style, expand=False))

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
                    console.print(f"[bold green][OK] Berhasil melamar pekerjaan ini.[/bold green]\n")
                elif result["status"] == "already_applied":
                    record_job(job["url"], job["title"], job["company"], status="applied", notes="Sudah pernah dilamar")
                    console.print(f"[yellow][!] Kamu sudah pernah melamar lowongan ini sebelumnya.[/yellow]\n")
                elif result["status"] == "external_link":
                    record_job(job["url"], job["title"], job["company"], status="skipped", notes="Website karir eksternal")
                    console.print(f"[cyan][i] Lowongan mengarahkan ke website eksternal perusahaan.[/cyan]\n")
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
    console.print("\n[bold]Isi Surat Lamaran:[/bold]")
    console.print(Panel(body, title=subject, expand=False))

    console.print("\n[1] Buka Draft di [bold cyan]Gmail Web[/bold cyan] (1-Klik di Browser - Sangat Mudah)")
    console.print("[2] Buka di Aplikasi Email Default ([bold magenta]Mailto[/bold magenta])")
    console.print("[3] Kirim Otomatis via SMTP Pribadi")
    console.print("[4] Batal")

    opt = Prompt.ask("Pilih metode pengiriman", choices=["1", "2", "3", "4"], default="1")
    if opt == "1":
        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(to_email)}&su={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        console.print("[*] Membuka draf di browser Gmail kamu...")
        webbrowser.open(gmail_url)
        record_job(f"mailto:{to_email}", role, company, status="applied", notes="Draft Gmail Web")
        console.print("[green][OK] Tab Gmail terbuka! Tinggal lampirkan CV dan kirim.[/green]")

    elif opt == "2":
        mailto_url = f"mailto:{to_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        webbrowser.open(mailto_url)
        record_job(f"mailto:{to_email}", role, company, status="applied", notes="Mailto App")
        console.print("[green][OK] Aplikasi email default dibuka.[/green]")

    elif opt == "3":
        cv_path = smtp_cfg.get("cv_path", "attachments/CV.pdf")
        res = send_cold_email(to_email, subject, body, attachment_path=cv_path, smtp_config=smtp_cfg)
        if res["success"]:
            record_job(f"mailto:{to_email}", role, company, status="applied", notes="Cold Email Langsung (SMTP)")
            console.print(f"[green][OK] {res['message']}[/green]\n")
        else:
            console.print(f"[red][x] {res['message']}[/red]\n")

def kanban_menu():
    stats = get_analytics_summary()
    table = Table(title="Statistik Pelacak Lamaran Kerja (Pipeline)", expand=False)
    table.add_column("Status Tahapan", style="bold")
    table.add_column("Jumlah", justify="center")

    table.add_row("📨 Terkirim (Applied)", str(stats["applied"]))
    table.add_row("💬 Panggilan Interview", f"[yellow]{stats['interview']}[/yellow]")
    table.add_row("🏆 Offering / Diterima", f"[bold green]{stats['offering']}[/bold green]")
    table.add_row("❌ Ditolak / Gugur", f"[red]{stats['rejected']}[/red]")
    table.add_row("⏭️ Dilewati", str(stats["skipped"]))
    table.add_row("📈 Tingkat Respons (Interview Rate)", f"[bold cyan]{stats['response_rate']}%[/bold cyan]")

    console.print(table)
    
    if Confirm.ask("\nApakah kamu ingin mengekspor seluruh riwayat ke file CSV/Excel?"):
        p = export_history_to_csv()
        console.print(f"[green][OK] Data berhasil diekspor ke: {p}[/green]")

def settings_menu():
    cfg = load_config()
    profile = cfg.get("profile", {})
    screening = cfg.get("screening_defaults", {})
    domicile = screening.get("domicile", "Jakarta")
    exp = profile.get("experience_level", "fresh_graduate")

    umr_guide = suggest_salary_range(domicile, exp)
    
    console.print("\n[bold]Pengaturan Profil & Auto-Fill Screening:[/bold]")
    console.print(f"1. Bidang/Jurusan      : [cyan]{profile.get('field_or_major', '-')}[/cyan]")
    console.print(f"2. Kata Kunci Target   : [cyan]{', '.join(profile.get('target_keywords', []))}[/cyan]")
    console.print(f"3. Level Pengalaman    : [cyan]{exp}[/cyan]")
    console.print(f"4. Domisili & Standar  : [cyan]{domicile}[/cyan] (UMR: Rp {umr_guide['umr']:,})".replace(",", "."))
    console.print(f"5. Rekomendasi Gaji    : [green]{umr_guide['formatted_range']}[/green]")
    console.print(f"6. Ekspektasi Kamu     : [cyan]Rp {screening.get('expected_salary', '6000000')}[/cyan]")

    if Confirm.ask("\nApakah kamu ingin mengubah data profil ini?"):
        major = Prompt.ask("Bidang/jurusan kamu", default=profile.get("field_or_major", "Akuntansi"))
        keywords_input = Prompt.ask("Kata kunci target (pisahkan koma)", default=", ".join(profile.get("target_keywords", ["Staff"])))
        exp = Prompt.ask("Level pengalaman", choices=["fresh_graduate", "junior", "mid", "senior", "all"], default=profile.get("experience_level", "fresh_graduate"))
        dom = Prompt.ask("Kota domisili kamu", default=domicile)
        
        # Hitung UMR kota input
        new_guide = suggest_salary_range(dom, exp)
        console.print(f"[dim]Rekomendasi gaji sehat di {dom}: {new_guide['formatted_range']}[/dim]")
        salary = Prompt.ask("Ekspektasi gaji default (angka)", default=str(new_guide["recommended_min"]))

        profile["field_or_major"] = major
        profile["target_keywords"] = [k.strip() for k in keywords_input.split(",") if k.strip()]
        profile["experience_level"] = exp
        screening["expected_salary"] = salary
        screening["domicile"] = dom
        
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
        console.print("[5] Kirim Lamaran Langsung ke Email HRD (1-Click Gmail Draft / SMTP)")
        console.print("[6] Pelacak Lamaran (Pipeline Status, Analytics & Ekspor CSV)")
        console.print("[7] Atur Profil & Panduan Gaji UMR")
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
