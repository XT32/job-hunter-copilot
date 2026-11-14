TEMPLATES = {
    "formal": """Yth. Tim Rekrutmen {company},

Sehubungan dengan dibukanya lowongan pekerjaan untuk posisi {role} di {company}, saya menulis surat lamaran ini untuk menyatakan ketertarikan saya terhadap kesempatan tersebut.

Saya merupakan lulusan di bidang {major} dengan fokus keahlian pada {skills}. Berbekal pengalaman serta pemahaman mendalam yang saya miliki, saya yakin dapat beradaptasi dengan cepat dan memberikan kontribusi nyata bagi pencapaian target tim di {company}.

Terima kasih atas waktu dan perhatian Bapak/Ibu. Besar harapan saya untuk dapat mendiskusikan kualifikasi saya lebih lanjut dalam sesi wawancara.

Hormat saya,
{applicant_name}
{contact_info}""",

    "fresh_grad": """Halo Tim HR {company},

Perkenalkan saya {applicant_name}, lulusan baru di bidang {major}. Melalui surat ini, saya ingin mengajukan lamaran untuk posisi {role} di {company}.

Selama masa studi dan berbagai proyek praktis yang saya jalani, saya telah mengasah kemampuan dalam {skills}. Saya terbiasa memecahkan masalah secara analitis, bekerja dalam tim, dan memiliki antusiasme tinggi untuk terus belajar di lingkungan kerja yang dinamis.

Saya sangat antusias dengan kesempatan untuk bertumbuh bersama {company}. Terima kasih banyak atas pertimbangan Bapak/Ibu.

Salam hangat,
{applicant_name}
{contact_info}""",

    "magang": """Yth. Tim Pembina Magang {company},

Saya {applicant_name}, mengajukan diri untuk mengikuti Program Pemagangan pada posisi {role} di {company}.

Dengan latar belakang pendidikan di bidang {major}, saya memiliki ketertarikan besar untuk mempraktikkan kompetensi saya dalam {skills} langsung di industri nyata. Saya siap berkomitmen penuh, mematuhi seluruh tata tertib pemagangan, dan menyelesaikan setiap tugas dengan penuh tanggung jawab.

Terima kasih atas kesempatan yang diberikan oleh {company}.

Hormat saya,
{applicant_name}
{contact_info}"""
}

def generate_cover_letter(role, company, profile=None, preset="formal") -> str:
    profile = profile or {}
    template = TEMPLATES.get(preset, TEMPLATES["formal"])
    
    applicant_name = profile.get("applicant_name", "Pelamar")
    major = profile.get("field_or_major", "Pendidikan Terkait")
    skills = ", ".join(profile.get("target_keywords", ["Bidang Terkait"]))
    contact = profile.get("contact_info", "")

    return template.format(
        applicant_name=applicant_name,
        company=company,
        role=role,
        major=major,
        skills=skills,
        contact_info=contact
    )
