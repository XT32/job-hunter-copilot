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

import re


class ScreeningAutoFiller:
    def __init__(self, page, defaults=None):
        self.page = page
        self.defaults = defaults or {
            "expected_salary": "6000000",
            "notice_period": "Immediately",
            "years_of_experience": "1",
            "education_level": "S1",
            "willing_to_wfo": True,
            "willing_to_relocate": True,
            "domicile": "Jakarta",
            "custom_qa": [],
        }
        self.last_unanswered = []

    def _record_unanswered(self, question_text: str, field_type: str = "text"):
        if not question_text:
            return
        clean = re.sub(r"\s+", " ", question_text).strip()
        if not clean or len(clean) < 3:
            return
        for item in self.last_unanswered:
            q = item.get("question", "") if isinstance(item, dict) else str(item)
            if clean in q or q in clean:
                return
        words = [
            w for w in re.findall(r"[a-zA-Z0-9]{3,}", clean.lower())
            if w not in {"apa", "apakah", "berapa", "kapan", "dimana", "mohon", "silakan", "input", "wajib", "select", "pilih", "anda"}
        ]
        suggested_kw = words[0] if words else clean[:15].strip()
        self.last_unanswered.append({
            "question": clean[:100],
            "type": field_type,
            "suggested_keyword": suggested_kw,
        })

    def _safe_attr(self, el, name: str) -> str:
        try:
            val = el.get_attribute(name)
            return val.strip() if isinstance(val, str) else ""
        except Exception:
            return ""

    def _safe_text(self, el) -> str:
        try:
            txt = el.inner_text()
            return txt.strip() if isinstance(txt, str) else ""
        except Exception:
            return ""

    def _get_question_context(self, el) -> str:
        """Mengambil teks pertanyaan/label yang terkait dengan elemen form."""
        parts = [
            self._safe_attr(el, "aria-label"),
            self._safe_attr(el, "placeholder"),
            self._safe_attr(el, "name"),
            self._safe_attr(el, "id"),
        ]
        try:
            el_id = self._safe_attr(el, "id")
            if el_id:
                lbl = self.page.locator(f"label[for='{el_id}']").first
                if lbl.is_visible(timeout=200):
                    parts.append(self._safe_text(lbl))
        except Exception:
            pass

        try:
            parent_label = el.locator("xpath=ancestor::*[self::fieldset or self::label or contains(@data-automation, 'question') or contains(@class, 'question')][1]").first
            if parent_label.is_visible(timeout=200):
                parts.append(self._safe_text(parent_label))
        except Exception:
            pass

        return " ".join(p for p in parts if p).lower()

    def _match_custom_qa(self, question_text: str):
        custom_qa = self.defaults.get("custom_qa") or []
        q_lower = question_text.lower()
        for item in custom_qa:
            if not isinstance(item, dict):
                continue
            kw = str(item.get("keyword", "")).strip().lower()
            ans = str(item.get("answer", "")).strip()
            if kw and ans and kw in q_lower:
                return ans
        return None

    def _resolve_answer_for_question(self, question_text: str):
        q = question_text.lower()
        custom = self._match_custom_qa(q)
        if custom is not None:
            return custom

        if any(k in q for k in ["gaji", "salary", "upah", "penghasilan", "expected pay", "compensation"]):
            return str(self.defaults.get("expected_salary", "6000000"))

        if any(k in q for k in ["pengalaman", "experience", "tahun kerja", "years"]):
            return str(self.defaults.get("years_of_experience", "1"))

        if any(k in q for k in ["domisili", "kota", "lokasi", "tinggal", "location", "city", "alamat"]):
            return str(self.defaults.get("domicile", "Jakarta"))

        if any(k in q for k in ["notice", "mulai bekerja", "bergabung", "kapan bisa", "availability", "start work"]):
            return str(self.defaults.get("notice_period", "Immediately"))

        if any(k in q for k in ["pendidikan", "education", "gelar", "lulusan", "degree", "ijazah"]):
            return str(self.defaults.get("education_level", "S1"))

        if any(k in q for k in ["bersedia", "willing", "siap", "wfo", "shift", "lembur", "relokasi", "relocate", "travel", "perjalanan dinas"]):
            return "Ya" if self.defaults.get("willing_to_wfo", True) else "Tidak"

        return None

    def _pick_best_select_option(self, select_el, target_answer: str) -> bool:
        try:
            options = select_el.locator("option").all()
            if not options:
                return False

            ans_lower = str(target_answer).lower().strip()
            best_val = None

            # 1. Cocokkan langsung atau sinonim (Ya/Yes, Segera/Immediately, S1/Sarjana)
            synonyms = [ans_lower]
            if ans_lower in ("ya", "yes", "true", "bersedia"):
                synonyms.extend(["ya", "yes", "bersedia", "iya", "setuju"])
            elif ans_lower in ("immediately", "segera"):
                synonyms.extend(["segera", "immediately", "langsung", "kurang dari", "less than", "0"])
            elif ans_lower in ("s1", "sarjana"):
                synonyms.extend(["s1", "sarjana", "bachelor", "strata 1"])
            elif ans_lower in ("d3", "diploma"):
                synonyms.extend(["d3", "diploma"])
            elif ans_lower in ("sma", "smk", "sma/smk"):
                synonyms.extend(["sma", "smk", "high school", "slta"])

            for opt in options:
                val = self._safe_attr(opt, "value")
                txt = self._safe_text(opt).lower()
                if not val and not txt:
                    continue
                if any(s in txt for s in synonyms):
                    best_val = val or self._safe_text(opt)
                    break

            # 2. Jika target angka (tahun pengalaman atau gaji), cocokkan rentang angka
            if best_val is None and ans_lower.isdigit():
                num = int(ans_lower)
                for opt in options:
                    val = self._safe_attr(opt, "value")
                    txt = self._safe_text(opt).lower()
                    if not val:
                        continue
                    nums = [int(n) for n in re.findall(r"\d+", txt)]
                    if len(nums) == 1 and nums[0] == num:
                        best_val = val
                        break
                    if len(nums) >= 2 and nums[0] <= num <= nums[1]:
                        best_val = val
                        break
                    if ("lebih dari" in txt or "more than" in txt or "+" in txt) and nums and num >= nums[0]:
                        best_val = val
                        break
                    if ("kurang dari" in txt or "less than" in txt) and nums and num <= nums[0]:
                        best_val = val
                        break

            if best_val is not None:
                select_el.select_option(value=best_val)
                return True
        except Exception:
            pass
        return False

    def auto_fill_form(self) -> int:
        """Mendeteksi dan mengisi otomatis pertanyaan screening umum (input, select, radio, textarea)."""
        filled_count = 0
        self.last_unanswered = []

        try:
            # 1. Pertahankan kompatibilitas selector spesifik untuk input gaji/pengalaman/domisili
            salary_inputs = self.page.locator("input[placeholder*='gaji' i], input[placeholder*='salary' i], input[name*='salary' i], input[name*='gaji' i], input[aria-label*='gaji' i]").all()
            for inp in salary_inputs:
                try:
                    if inp.is_visible(timeout=250) and not inp.input_value():
                        inp.fill(str(self.defaults.get("expected_salary", "6000000")))
                        filled_count += 1
                except Exception:
                    pass

            exp_inputs = self.page.locator("input[placeholder*='pengalaman' i], input[placeholder*='experience' i], input[name*='year' i]").all()
            for inp in exp_inputs:
                try:
                    if inp.is_visible(timeout=250) and not inp.input_value():
                        inp.fill(str(self.defaults.get("years_of_experience", "1")))
                        filled_count += 1
                except Exception:
                    pass

            dom_inputs = self.page.locator("input[placeholder*='domisili' i], input[placeholder*='kota' i], input[placeholder*='lokasi' i]").all()
            for inp in dom_inputs:
                try:
                    if inp.is_visible(timeout=250) and not inp.input_value():
                        inp.fill(str(self.defaults.get("domicile", "Jakarta")))
                        filled_count += 1
                except Exception:
                    pass

            # 2. Scan input teks/angka & textarea lainnya berdasarkan teks pertanyaan (JobStreet Wizard)
            all_inputs = self.page.locator("input[type='text'], input[type='number'], input:not([type]), textarea").all()
            for inp in all_inputs:
                try:
                    if not inp.is_visible(timeout=250):
                        continue
                    if inp.input_value().strip():
                        continue
                    q_text = self._get_question_context(inp)
                    ans = self._resolve_answer_for_question(q_text)
                    if ans is not None:
                        inp.fill(str(ans))
                        filled_count += 1
                    elif self._safe_attr(inp, "required") != "" or "*" in q_text:
                        self._record_unanswered(q_text or "Pertanyaan teks wajib", "text")
                except Exception:
                    pass

            # 3. Scan dropdown <select>
            selects = self.page.locator("select").all()
            for sel in selects:
                try:
                    if not sel.is_visible(timeout=250):
                        continue
                    current_val = sel.input_value()
                    q_text = self._get_question_context(sel)
                    ans = self._resolve_answer_for_question(q_text)
                    if ans is not None and (not current_val or current_val == ""):
                        if self._pick_best_select_option(sel, ans):
                            filled_count += 1
                        else:
                            self._record_unanswered(q_text or "Pilihan dropdown wajib", "select")
                    elif not current_val:
                        self._record_unanswered(q_text or "Pilihan dropdown belum dipilih", "select")
                except Exception:
                    pass

            # 4. Scan radio button per grup pertanyaan (fieldset / radiogroup)
            groups = self.page.locator("fieldset, [role='radiogroup']").all()
            handled_radio_names = set()
            for grp in groups:
                try:
                    if not grp.is_visible(timeout=250):
                        continue
                    radios = grp.locator("input[type='radio']").all()
                    if not radios:
                        continue
                    if any(r.is_checked() for r in radios):
                        for r in radios:
                            n = self._safe_attr(r, "name")
                            if n:
                                handled_radio_names.add(n)
                        continue

                    grp_text = self._safe_text(grp).lower()
                    target_ans = self._resolve_answer_for_question(grp_text)
                    if target_ans is None and self.defaults.get("willing_to_wfo", True):
                        target_ans = "Ya"

                    clicked = False
                    if target_ans:
                        ans_l = str(target_ans).lower()
                        candidates = [ans_l]
                        if ans_l in ("ya", "yes", "true", "bersedia"):
                            candidates.extend(["ya", "yes", "bersedia", "setuju", "iya"])
                        elif ans_l in ("immediately", "segera"):
                            candidates.extend(["segera", "immediately", "langsung"])

                        for r in radios:
                            n = self._safe_attr(r, "name")
                            if n:
                                handled_radio_names.add(n)
                            r_id = self._safe_attr(r, "id")
                            r_val = self._safe_attr(r, "value").lower()
                            lbl_txt = ""
                            if r_id:
                                lbl_txt = self._safe_text(grp.locator(f"label[for='{r_id}']").first).lower()
                            if not lbl_txt:
                                lbl_txt = self._safe_text(r.locator("xpath=ancestor::label[1]").first).lower()
                            combined = f"{r_val} {lbl_txt}"
                            if any(c in combined for c in candidates):
                                try:
                                    r.check(force=True)
                                except Exception:
                                    if r_id:
                                        grp.locator(f"label[for='{r_id}']").first.click()
                                    else:
                                        r.click(force=True)
                                filled_count += 1
                                clicked = True
                                break

                    if not clicked:
                        self._record_unanswered(grp_text.splitlines()[0] if grp_text else "Pilihan radio", "radio")
                except Exception:
                    pass

            # 5. Fallback radio 'Ya/Yes' yang tidak berada di dalam fieldset
            if self.defaults.get("willing_to_wfo", True):
                yes_radios = self.page.locator("input[type='radio'][value*='yes' i], input[type='radio'][value*='ya' i]").all()
                for opt in yes_radios:
                    try:
                        r_name = self._safe_attr(opt, "name")
                        if r_name and r_name in handled_radio_names:
                            continue
                        if opt.is_visible() and not opt.is_checked():
                            opt.check(force=True)
                            filled_count += 1
                    except Exception:
                        pass

        except Exception as e:
            print(f"[!] Info auto-fill screening: {e}")

        return filled_count
