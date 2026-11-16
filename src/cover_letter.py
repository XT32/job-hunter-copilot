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
{contact_info}""",

    "english_formal": """Dear Hiring Team at {company},

I am writing to express my strong interest in the {role} position currently open at {company}.

With an educational background in {major} and practical proficiency in {skills}, I have developed a strong foundation to solve complex challenges, collaborate effectively, and deliver measurable results. I am confident that my dedication and adaptability will make an immediate positive contribution to {company}.

Thank you for your time and consideration. I would welcome the opportunity to discuss my qualifications further in an interview.

Sincerely,
{applicant_name}
{contact_info}""",

    "english_fresh_grad": """Dear Hiring Manager at {company},

I am excited to submit my application for the {role} role at {company}. As a proactive graduate in {major}, I have been closely following {company}'s achievements and would love the opportunity to contribute to your mission.

Throughout my academic coursework and hands-on projects, I have developed solid skills in {skills}. I consider myself a fast learner and enthusiastic problem-solver who thrives in dynamic and collaborative environments.

Thank you for considering my application. I look forward to the possibility of discussing how my background fits your team.

Best regards,
{applicant_name}
{contact_info}""",

    "english_internship": """Dear Internship Coordinator at {company},

I am writing to express my strong interest in the {role} internship position at {company}.

As a student/graduate majoring in {major}, I have gained solid foundational skills in {skills}. I am enthusiastic about applying my knowledge in a practical work environment, learning from industry professionals, and actively contributing to your team's initiatives.

Thank you for your time and consideration. I would welcome the opportunity to discuss my qualifications further in an interview.

Sincerely,
{applicant_name}
{contact_info}"""
}


class _SafeDict(dict):
    def __missing__(self, key):
        return f"[{key}]"


def generate_cover_letter(role, company, profile=None, preset="formal") -> str:
    profile = profile or {}
    template = TEMPLATES.get(preset, TEMPLATES["formal"])

    applicant_name = profile.get("applicant_name", "Pelamar")
    major = profile.get("field_or_major", "Pendidikan Terkait")
    skills = ", ".join(profile.get("target_keywords", ["Bidang Terkait"]))
    contact = profile.get("contact_info", "")

    mapping = {
        "applicant_name": applicant_name,
        "company": company,
        "role": role,
        "major": major,
        "skills": skills,
        "contact_info": contact,
    }
    return template.format_map(_SafeDict(mapping))
