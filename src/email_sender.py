# Copyright (C) 2024-2026 XT32 <https://github.com/XT32/job-hunter-copilot>
#
# This file is part of Job Hunter Copilot.
#
# Job Hunter Copilot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Job Hunter Copilot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import smtplib
from email.message import EmailMessage

def send_cold_email(to_email, subject, body, attachment_path=None, smtp_config=None) -> dict:
    """Mengirim email lamaran langsung ke HRD via SMTP dengan lampiran CV"""
    smtp_config = smtp_config or {}
    server_host = smtp_config.get("host", "smtp.gmail.com")
    server_port = int(smtp_config.get("port", 465))
    sender_email = smtp_config.get("email", "")
    sender_password = smtp_config.get("password", "")
    sender_name = smtp_config.get("sender_name", "Pelamar")

    if not sender_email or not sender_password:
        return {"success": False, "message": "Email pengirim atau App Password belum disetel di pengaturan SMTP"}

    msg = EmailMessage()
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
            msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)
        except Exception as e:
            return {"success": False, "message": f"Gagal melampirkan file: {e}"}

    try:
        if server_port == 465:
            with smtplib.SMTP_SSL(server_host, server_port, timeout=15) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(server_host, server_port, timeout=15) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
        return {"success": True, "message": f"Email lamaran berhasil dikirim ke {to_email}"}
    except Exception as e:
        return {"success": False, "message": f"Gagal mengirim email: {str(e)}"}
