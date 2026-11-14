const CSRF_TOKEN = window.CSRF_TOKEN || (document.querySelector('meta[name="csrf-token"]') ? document.querySelector('meta[name="csrf-token"]').getAttribute('content') : "");

    // Auto-attach CSRF Token security headers to all fetch requests
    const _nativeFetch = window.fetch;
    window.fetch = function(url, options = {}) {
      options = options || {};
      options.headers = options.headers || {};
      if (options.headers instanceof Headers) {
        if (!options.headers.has('X-CSRF-Token')) {
          options.headers.set('X-CSRF-Token', CSRF_TOKEN);
        }
      } else if (Array.isArray(options.headers)) {
        options.headers.push(['X-CSRF-Token', CSRF_TOKEN]);
      } else {
        options.headers['X-CSRF-Token'] = CSRF_TOKEN;
      }
      return _nativeFetch(url, options);
    };

    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    let currentConfig = null;
    let foundJobs = [];
    let activeCLJob = null;
    let activeCVCount = 0;
    let recommendedMinSalary = 5000000;
    let logInterval = null;

    let activeManualJob = null;

    const TAB_PATH_MAP = {
      'huntTab': '/',
      'cvTab': '/cv',
      'kanbanTab': '/kanban',
      'emailTab': '/email',
      'profileTab': '/profil'
    };
    const PATH_TAB_MAP = {
      '/': 'huntTab',
      '/loker': 'huntTab',
      '/hunt': 'huntTab',
      '/cv': 'cvTab',
      '/kanban': 'kanbanTab',
      '/lamaran': 'kanbanTab',
      '/email': 'emailTab',
      '/profil': 'profileTab',
      '/pengaturan': 'profileTab',
      '/settings': 'profileTab'
    };

    function switchTab(tabId, btnEl, pushHistory = true) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

      const target = document.getElementById(tabId);
      if (target) target.classList.add('active');

      const btn = btnEl || document.querySelector(`.tab-btn[onclick*="${tabId}"]`);
      if (btn) btn.classList.add('active');

      const targetPath = TAB_PATH_MAP[tabId] || '/';
      if (pushHistory && window.location.pathname !== targetPath) {
        history.pushState({ tabId: tabId }, '', targetPath);
      }
      try {
        sessionStorage.setItem('copilot_active_tab', tabId);
      } catch (e) {}

      if (tabId === 'kanbanTab') {
        loadKanban();
        loadAnalytics();
      }
      if (tabId === 'cvTab') loadCVList();
      if (tabId === 'profileTab') checkSecurityStatus();
    }

    window.addEventListener('popstate', (e) => {
      const p = window.location.pathname.toLowerCase();
      const tabId = (e.state && e.state.tabId) || PATH_TAB_MAP[p] || 'huntTab';
      switchTab(tabId, null, false);
    });

    /* PEMULIHAN & KEAMANAN DATA */
    function renderSecurityState(sec) {
      if (!sec) return;
      const tamperBanner = document.getElementById('tamperAlertBanner');
      const legacyBanner = document.getElementById('legacyWarningBanner');
      const statusBox = document.getElementById('securityStatusBox');

      if (sec.tampered) {
        if (tamperBanner) tamperBanner.style.display = 'block';
      } else {
        if (tamperBanner) tamperBanner.style.display = 'none';
      }

      if (sec.legacy_file_warning) {
        if (legacyBanner) {
          legacyBanner.style.display = 'block';
          const txt = document.getElementById('legacyWarningText');
          if (txt) txt.innerText = 'Pengaturan Anda telah disesuaikan ke format terbaru.';
        }
      } else {
        if (legacyBanner) legacyBanner.style.display = 'none';
      }

      if (statusBox) {
        statusBox.innerHTML = sec.tampered
          ? `<div><span style="color:var(--danger); font-weight:700;">⚠️ Perlu Pemulihan Data</span><div style="color:var(--text-muted); font-size:0.8rem; margin-top:2px;">Klik tombol pulihkan untuk mengembalikan data Anda yang aman.</div></div><button class="btn btn-primary btn-sm" onclick="restoreDatabaseSnapshot()">Pulihkan Salinan Terakhir</button>`
          : `<div><span style="color:var(--success); font-weight:700;">✓ Data Tersimpan Aman</span><div style="color:var(--text-muted); font-size:0.8rem; margin-top:2px;">Data Anda disimpan secara privat di komputer ini.</div></div><button class="btn btn-secondary btn-sm" onclick="restoreDatabaseSnapshot()">Pulihkan Salinan Terakhir</button>`;
      }
    }

    async function checkSecurityStatus() {
      try {
        const res = await fetch('/api/security/status');
        const data = await res.json();
        if (data.security) renderSecurityState(data.security);
      } catch (e) {}
    }

    async function restoreDatabaseSnapshot() {
      try {
        const res = await fetch('/api/security/restore', { method: 'POST' });
        const data = await res.json();
        if (data.security) renderSecurityState(data.security);
        if (data.success) {
          alert(data.message || 'Data berhasil dipulihkan.');
          loadConfig();
          loadCVList();
          fetchLogs();
        } else {
          alert('Gagal memulihkan data: ' + (data.message || 'Terjadi kendala.'));
        }
      } catch (e) {
        alert('Gagal menghubungi server.');
      }
    }

    async function resetDatabaseViaUI() {
      if (!confirm('Apakah Anda yakin ingin mengatur ulang data ke pengaturan awal?')) return;
      try {
        const res = await fetch('/api/security/reset', { method: 'POST' });
        const data = await res.json();
        if (data.security) renderSecurityState(data.security);
        alert(data.message || 'Pengaturan berhasil dikembalikan ke awal.');
        loadConfig();
        loadCVList();
        fetchLogs();
      } catch (e) {}
    }

    async function ackLegacyWarning() {
      try {
        const res = await fetch('/api/security/ack-legacy', { method: 'POST' });
        const data = await res.json();
        if (data.security) renderSecurityState(data.security);
      } catch (e) {}
    }

    function handleApiTamperResponse(data) {
      if (data && data.tamper_alert) {
        renderSecurityState(data.security_status || { tampered: true, reason: data.error });
        alert('Pemberitahuan: Terdeteksi perubahan data yang tidak sesuai. Silakan klik tombol "Pulihkan Salinan Terakhir" pada banner di atas.');
        return true;
      }
      return false;
    }

    async function fetchLogs() {
      try {
        const res = await fetch('/api/logs');
        const logs = await res.json();
        const box = document.getElementById('terminalLogs');
        if (logs.length > 0) {
          box.innerHTML = logs.map(l => `<div class="log-entry log-${l.level}">[${l.time}] ${l.message}</div>`).join('');
          box.scrollTop = box.scrollHeight;
        }
      } catch (e) {}
    }

    function parseCustomQAText(text) {
      return text.split('\n').map(line => line.trim()).filter(Boolean).map(line => {
        const idx = line.indexOf('=');
        if (idx === -1) return null;
        return { keyword: line.slice(0, idx).trim(), answer: line.slice(idx + 1).trim() };
      }).filter(item => item && item.keyword && item.answer);
    }

    function formatCustomQAText(list) {
      if (!Array.isArray(list)) return '';
      return list.map(i => `${i.keyword} = ${i.answer}`).join('\n');
    }

    async function loadConfig() {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();
        if (handleApiTamperResponse(data)) return;
        currentConfig = data;
        const prof = currentConfig.profile || {};
        const scr = currentConfig.screening_defaults || {};
        const tg = currentConfig.telegram || {};

        document.getElementById('cfgName').value = prof.applicant_name || '';
        document.getElementById('cfgContact').value = prof.contact_info || '';
        document.getElementById('cfgMajor').value = prof.field_or_major || '';
        document.getElementById('cfgKeywords').value = (prof.target_keywords || []).join(', ');
        document.getElementById('cfgExp').value = prof.experience_level || 'fresh_graduate';
        document.getElementById('cfgLocations').value = (prof.preferred_locations || []).join(', ');
        document.getElementById('cfgWorkType').value = prof.work_type || 'all';
        document.getElementById('cfgBlacklist').value = (prof.blacklist_keywords || []).join(', ');

        document.getElementById('cfgSalary').value = scr.expected_salary || '6000000';
        document.getElementById('cfgNotice').value = scr.notice_period || 'Immediately';
        document.getElementById('cfgYears').value = scr.years_of_experience || '1';
        document.getElementById('cfgEducation').value = scr.education_level || 'S1';
        document.getElementById('cfgDomicile').value = scr.domicile || 'Jakarta';
        document.getElementById('cfgCustomQA').value = formatCustomQAText(scr.custom_qa);
        document.getElementById('cfgConfirmSubmit').checked = !!scr.confirm_before_submit;
        document.getElementById('cfgAutoSkip').checked = currentConfig.auto_skip_already_seen !== false;

        document.getElementById('cfgTgToken').value = tg.bot_token || '';
        document.getElementById('cfgTgChat').value = tg.chat_id || '';
        document.getElementById('cfgTgEnabled').checked = !!tg.enabled;

        document.getElementById('activeProfileBadge').innerText =
          `${prof.field_or_major || 'Umum'} (${prof.experience_level || 'all'})`;

        updateQuickStartChecklist();
        checkSalaryRecommendation();
      } catch (e) {
        console.error('Gagal memuat config:', e);
      }
    }

    function updateQuickStartChecklist() {
      const profEl = document.getElementById('stepProfileStatus');
      const cvEl = document.getElementById('stepCvStatus');
      if (profEl && currentConfig) {
        const prof = currentConfig.profile || {};
        const name = (prof.applicant_name || '').trim();
        const kws = prof.target_keywords || [];
        if (!name || name === 'Nama Lengkap Kamu') {
          profEl.style.color = 'var(--warning)';
          profEl.innerText = '⚠️ Nama masih default — klik Isi Profil';
        } else if (kws.length === 0) {
          profEl.style.color = 'var(--warning)';
          profEl.innerText = '⚠️ Target posisi masih kosong';
        } else {
          profEl.style.color = 'var(--success)';
          profEl.innerText = `✅ Siap (${name})`;
        }
      }
      if (cvEl) {
        if (activeCVCount > 0) {
          cvEl.style.color = 'var(--success)';
          cvEl.innerText = `✅ ${activeCVCount} file CV siap`;
        } else {
          cvEl.style.color = 'var(--warning)';
          cvEl.innerText = '⚠️ Belum ada CV PDF — unggah dulu';
        }
      }
    }

    async function checkSalaryRecommendation() {
      const loc = document.getElementById('cfgDomicile').value.trim() || 'Jakarta';
      const exp = document.getElementById('cfgExp').value;
      try {
        const res = await fetch(`/api/salary-guide?location=${encodeURIComponent(loc)}&exp=${encodeURIComponent(exp)}`);
        const guide = await res.json();
        recommendedMinSalary = guide.recommended_min;
        document.getElementById('salaryGuideText').innerHTML =
          `Rentang wajar <strong>${guide.formatted_range}</strong> (UMR ${guide.location}: Rp ${guide.umr.toLocaleString('id-ID')})`;
      } catch (e) {}
    }

    function applySalaryRecommendation() {
      document.getElementById('cfgSalary').value = recommendedMinSalary;
      alert(`Ekspektasi gaji disesuaikan ke standar minimum: Rp ${recommendedMinSalary.toLocaleString('id-ID')}`);
    }

    async function saveAllSettings() {
      const prof = {
        applicant_name: document.getElementById('cfgName').value.trim(),
        contact_info: document.getElementById('cfgContact').value.trim(),
        field_or_major: document.getElementById('cfgMajor').value.trim(),
        target_keywords: document.getElementById('cfgKeywords').value.split(',').map(s => s.trim()).filter(Boolean),
        experience_level: document.getElementById('cfgExp').value,
        preferred_locations: document.getElementById('cfgLocations').value.split(',').map(s => s.trim()).filter(Boolean),
        work_type: document.getElementById('cfgWorkType').value,
        blacklist_keywords: document.getElementById('cfgBlacklist').value.split(',').map(s => s.trim()).filter(Boolean)
      };

      const scr = {
        expected_salary: document.getElementById('cfgSalary').value.trim(),
        notice_period: document.getElementById('cfgNotice').value.trim(),
        years_of_experience: document.getElementById('cfgYears').value.trim(),
        education_level: document.getElementById('cfgEducation').value,
        domicile: document.getElementById('cfgDomicile').value.trim(),
        willing_to_wfo: true,
        willing_to_relocate: true,
        confirm_before_submit: document.getElementById('cfgConfirmSubmit').checked,
        custom_qa: parseCustomQAText(document.getElementById('cfgCustomQA').value)
      };

      const tg = {
        bot_token: document.getElementById('cfgTgToken').value.trim(),
        chat_id: document.getElementById('cfgTgChat').value.trim(),
        enabled: document.getElementById('cfgTgEnabled').checked
      };

      try {
        const res = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile: prof,
            screening_defaults: scr,
            telegram: tg,
            auto_skip_already_seen: document.getElementById('cfgAutoSkip').checked
          })
        });
        const data = await res.json();
        if (handleApiTamperResponse(data)) return;
        if (data.success) {
          alert('Semua pengaturan berhasil disimpan!');
          loadConfig();
          checkSecurityStatus();
        }
      } catch (e) {
        alert('Terjadi kesalahan saat menyimpan pengaturan.');
      }
    }

    /* MULTI-CV LOGIC */
    async function loadCVList() {
      const container = document.getElementById('cvListContainer');
      try {
        const res = await fetch('/api/cvs');
        const data = await res.json();
        const cvs = data.cvs || [];
        activeCVCount = cvs.length;
        const countSpan = document.getElementById('cvTabCount');
        if (countSpan) countSpan.innerText = activeCVCount;

        document.getElementById('activeCVBadge').innerText =
          data.active_cv ? `CV: ${data.active_cv}` : 'Belum ada CV';
        updateQuickStartChecklist();

        if (cvs.length === 0) {
          container.innerHTML = '<div style="font-size:0.85rem; color:var(--text-muted);">Belum ada file CV yang diunggah. Silakan unggah CV pertama kamu di form bawah.</div>';
          return;
        }

        container.innerHTML = cvs.map(c => `
          <div class="cv-item" style="${c.active ? 'border-color: var(--primary); background: #132337;' : ''}">
            <div>
              <div style="font-weight: 600; color: #fff;">
                📄 ${c.filename} ${c.active ? '<span class="badge" style="background:var(--primary); color:#000; margin-left:8px;">AKTIF</span>' : ''}
              </div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">${(c.size / 1024).toFixed(1)} KB</div>
            </div>
            <div style="display: flex; gap: 8px;">
              ${!c.active ? `<button class="btn btn-secondary btn-sm" onclick="setActiveCV('${c.filename}')">Jadikan Aktif</button>` : ''}
              <button class="btn btn-danger btn-sm" onclick="deleteCV('${c.filename}')">Hapus</button>
            </div>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = '<div style="color:var(--danger);">Gagal memuat daftar CV.</div>';
      }
    }

    async function setActiveCV(filename) {
      try {
        const res = await fetch('/api/set-active-cv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: filename })
        });
        const data = await res.json();
        if (data.success) {
          loadCVList();
        }
      } catch (e) {}
    }

    async function deleteCV(filename) {
      if (!confirm(`Hapus file CV '${filename}'?`)) return;
      try {
        const res = await fetch('/api/delete-cv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: filename })
        });
        const data = await res.json();
        if (data.success) {
          loadCVList();
        }
      } catch (e) {}
    }

    async function uploadCV() {
      const fileInput = document.getElementById('cvFileInput');
      const statusDiv = document.getElementById('cvUploadStatus');
      if (!fileInput.files || fileInput.files.length === 0) {
        alert('Silakan pilih file PDF CV terlebih dahulu.');
        return;
      }

      const formData = new FormData();
      formData.append('cv', fileInput.files[0]);

      statusDiv.innerHTML = '<span style="color: var(--primary);">⏳ Sedang mengunggah dan menganalisis teks CV...</span>';

      try {
        const res = await fetch('/api/upload-cv', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          statusDiv.innerHTML = `<span style="color: var(--success); font-weight: 600;">[✓] ${data.message} (${data.char_count} karakter terdeteksi).</span>`;
          fileInput.value = '';
          loadCVList();
        } else {
          statusDiv.innerHTML = `<span style="color: var(--danger);">[x] ${data.error}</span>`;
        }
      } catch (e) {
        statusDiv.innerHTML = '<span style="color: var(--danger);">[x] Gagal mengunggah file</span>';
      }
    }

    /* INTERACTIVE BROWSER & SCANNING */
    function renderBrowserBar(browser) {
      const bar = document.getElementById('activeBrowserBar');
      const completeBtn = document.getElementById('btnCompleteApplyBar');
      if (browser && browser.active) {
        const meta = browser.meta || {};
        bar.style.display = 'flex';
        if (meta.mode === 'apply_handoff') {
          document.getElementById('activeBrowserTitle').innerText = `🌐 Browser Terbuka: ${meta.title || 'Lowongan'} @ ${meta.company || ''}`;
          document.getElementById('activeBrowserSubtitle').innerText = 'Lengkapi tahap dokumen/pertanyaan/kirim di jendela browser, lalu klik "Sudah Saya Kirim" di sini.';
          completeBtn.style.display = 'inline-flex';
          activeManualJob = meta;
        } else {
          document.getElementById('activeBrowserTitle').innerText = `🔑 Browser Copilot Terbuka (${meta.label || 'Portal'})`;
          document.getElementById('activeBrowserSubtitle').innerText = 'Silakan login di jendela browser yang terbuka, lalu tutup browser saat sudah selesai.';
          completeBtn.style.display = 'none';
          activeManualJob = null;
        }
      } else {
        bar.style.display = 'none';
        activeManualJob = null;
      }
    }

    async function refreshBrowserStatus() {
      try {
        const res = await fetch('/api/browser/status');
        const data = await res.json();
        renderBrowserBar(data.browser);
      } catch (e) {}
    }

    async function openLoginBrowser() {
      const platform = document.getElementById('platformSelect').value;
      fetchLogs();
      try {
        const res = await fetch('/api/browser/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ platform: platform })
        });
        const data = await res.json();
        if (handleApiTamperResponse(data)) return;
        if (data.success) {
          renderBrowserBar(data.browser);
          fetchLogs();
        } else {
          alert('Gagal membuka browser: ' + (data.error || 'Unknown error'));
        }
      } catch (e) {
        alert('Gagal membuka jendela browser.');
      }
    }

    async function openJobInCopilotBrowser(index) {
      const job = foundJobs[index];
      const platform = document.getElementById('platformSelect').value;
      try {
        const res = await fetch('/api/browser/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ platform: platform, url: job.url, label: job.title })
        });
        const data = await res.json();
        if (data.success) {
          renderBrowserBar(data.browser);
          fetchLogs();
        }
      } catch (e) {}
    }

    async function closeActiveBrowser() {
      try {
        await fetch('/api/browser/close', { method: 'POST' });
        renderBrowserBar({ active: false });
        fetchLogs();
      } catch (e) {}
    }

    async function completeActiveBrowserApply(jobOverride) {
      const target = jobOverride || activeManualJob;
      if (!target) {
        await closeActiveBrowser();
        return;
      }
      try {
        const res = await fetch('/api/browser/complete-apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            platform: target.platform || document.getElementById('platformSelect').value,
            url: target.url,
            title: target.title,
            company: target.company
          })
        });
        const data = await res.json();
        if (handleApiTamperResponse(data)) return;
        renderBrowserBar({ active: false });
        fetchLogs();
      } catch (e) {}
    }

    async function startScan() {
      const platform = document.getElementById('platformSelect').value;
      const keywords = document.getElementById('scanKeywords').value.trim();
      const btn = document.getElementById('btnScan');
      const status = document.getElementById('scanStatus');
      const container = document.getElementById('jobsContainer');

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Sedang Mencari Lowongan...';
      status.style.display = 'block';
      status.innerText = `Sedang mencari lowongan kerja di ${platform.toUpperCase()}... Jendela peramban akan terbuka otomatis.`;
      container.innerHTML = '';

      fetchLogs();
      if (!logInterval) logInterval = setInterval(fetchLogs, 2500);

      try {
        const res = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ platform: platform, keywords: keywords || null })
        });
        const data = await res.json();
        if (handleApiTamperResponse(data)) {
          status.innerText = 'Pencarian ditunda karena data memerlukan pemulihan.';
          return;
        }

        if (data.success && data.jobs && data.jobs.length > 0) {
          foundJobs = data.jobs;
          try {
            sessionStorage.setItem('copilot_found_jobs', JSON.stringify(foundJobs));
          } catch (e) {}
          status.innerText = `Ditemukan ${foundJobs.length} lowongan yang cocok dengan profil Anda!`;
          renderJobs();
        } else {
          status.innerText = data.error
            ? `Kendala saat mencari: ${data.error}`
            : `Belum ada lowongan baru yang cocok di ${platform.toUpperCase()} saat ini.`;
        }
      } catch (e) {
        status.innerText = `Kendala koneksi saat mencari lowongan: ${e.message || 'Koneksi terputus'}`;
      } finally {
        btn.disabled = false;
        btn.innerText = '🔍 Mulai Cari Lowongan';
        clearInterval(logInterval);
        logInterval = null;
        fetchLogs();
        refreshBrowserStatus();
      }
    }

    function renderJobs() {
      const container = document.getElementById('jobsContainer');
      container.innerHTML = '';

      foundJobs.forEach((job, index) => {
        const card = document.createElement('div');
        card.className = 'job-card';
        card.id = `job-${index}`;

        const ats = job.ats || { score: 70, status: 'Sedang' };
        const atsScoreBadge = `<span class="badge badge-ats">🎯 ATS Match: ${escapeHtml(ats.score)}% (${escapeHtml(ats.status)})</span>`;

        let redFlagHtml = '';
        if (job.red_flag && job.red_flag.is_red_flag) {
          const cls = job.red_flag.risk_level === 'danger' ? 'red-flag-danger' : 'red-flag-warning';
          const safeFlags = (job.red_flag.flags || []).map(f => escapeHtml(f)).join(' • ');
          redFlagHtml = `
            <div class="red-flag-box ${cls}">
              <strong>⚠️ PERINGATAN POTENSI RED FLAG:</strong> ${safeFlags}<br>
              <span style="font-size:0.75rem; opacity:0.9;">${escapeHtml(job.red_flag.advice || '')}</span>
            </div>
          `;
        }

        const titleSafe = escapeHtml(job.title || 'Posisi');
        const companySafe = escapeHtml(job.company || 'Perusahaan');
        const salarySafe = escapeHtml(job.salary || 'Gaji/Uang saku tidak dicantumkan');
        const locSafe = escapeHtml(job.location || '');
        const matchedSkills = (ats.matched && ats.matched.length)
          ? ats.matched.map(s => escapeHtml(s)).join(', ')
          : '';

        card.innerHTML = `
          <div class="job-header">
            <div>
              <a href="${encodeURI(job.url || '#')}" target="_blank" rel="noopener noreferrer" class="job-title">${titleSafe}</a>
              <div class="job-company">${companySafe}</div>
            </div>
            ${atsScoreBadge}
          </div>
          ${redFlagHtml}
          <div class="job-badges">
            <span class="badge badge-salary">${salarySafe}</span>
            ${locSafe ? `<span class="badge">${locSafe}</span>` : ''}
            ${matchedSkills ? `<span class="badge" style="color:#38bdf8;">Keahlian Cocok: ${matchedSkills}</span>` : ''}
          </div>
          <div class="job-actions">
            <button class="btn btn-success btn-sm" onclick="applyJob(${index})">✅ Lamar Otomatis</button>
            <button class="btn btn-primary btn-sm" onclick="openJobInCopilotBrowser(${index})">🌐 Buka di Browser Copilot</button>
            <button class="btn btn-purple btn-sm" onclick="openCoverLetterModal(${index})">📄 Cover Letter</button>
            <button class="btn btn-secondary btn-sm" onclick="skipJob(${index})">⏭️ Lewati</button>
          </div>
        `;
        container.appendChild(card);
      });
    }

    async function applyJob(index) {
      const job = foundJobs[index];
      const platform = document.getElementById('platformSelect').value;
      const card = document.getElementById(`job-${index}`);

      card.style.opacity = '0.75';
      const actions = card.querySelector('.job-actions');
      actions.innerHTML = '<span style="font-size: 0.85rem; color: var(--primary);">⏳ Membuka browser & mengisi langkah lamaran...</span>';

      try {
        const res = await fetch('/api/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            platform: platform,
            url: job.url,
            title: job.title,
            company: job.company
          })
        });
        const data = await res.json();
        if (handleApiTamperResponse(data)) {
          card.style.opacity = '1';
          actions.innerHTML = `<span style="color: var(--danger); font-size: 0.85rem;">[!] Diblokir karena peringatan keamanan DB.</span>`;
          return;
        }

        if (data.rate_limited) {
          card.style.opacity = '1';
          actions.innerHTML = `<div style="color:var(--danger); font-size:0.85rem; font-weight:600;">🛑 ${escapeHtml(data.error)}</div>`;
          loadRateLimits();
          return;
        }

        renderBrowserBar(data.browser);
        fetchLogs();
        loadRateLimits();

        // Tangkapan layar kegagalan/review jika ada
        const shotBtn = data.screenshot
          ? `<a href="/api/screenshots/${encodeURIComponent(data.screenshot)}" target="_blank" class="btn btn-secondary btn-sm" style="font-size:0.75rem;">📸 Lihat Bukti Layar</a>`
          : '';

        // Tampilkan pertanyaan baru jika terdeteksi
        if (data.unanswered_questions && data.unanswered_questions.length > 0) {
          showUnansweredQuestionsModal(data.unanswered_questions);
        }

        if (data.success && data.result.status === 'success') {
          card.style.opacity = '1';
          actions.innerHTML = `<span style="color: var(--success); font-weight: 600;">[✓] Lamaran Berhasil Terkirim!</span> ${shotBtn}`;
        } else if (data.success && (data.result.status === 'manual_action_needed' || data.result.status === 'login_required')) {
          card.style.opacity = '1';
          actions.innerHTML = `
            <div style="width:100%; display:flex; flex-direction:column; gap:8px;">
              <span style="color: var(--warning); font-size: 0.85rem;">[!] ${escapeHtml(data.result.message)}</span>
              <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                <button class="btn btn-success btn-sm" onclick="markCardApplied(${index})">✅ Sudah Saya Kirim & Tutup Browser</button>
                <button class="btn btn-secondary btn-sm" onclick="applyJob(${index})">🔄 Coba Jalankan Ulang</button>
                ${shotBtn}
              </div>
            </div>
          `;
        } else {
          card.style.opacity = '1';
          const errMsg = data.result ? data.result.message : (data.error || 'Selesaikan di browser');
          actions.innerHTML = `<span style="color: var(--warning); font-size: 0.85rem;">[!] ${escapeHtml(errMsg)}</span> ${shotBtn}`;
        }
      } catch (e) {
        card.style.opacity = '1';
        actions.innerHTML = '<span style="color: var(--danger); font-size: 0.85rem;">[x] Gagal mengirim</span>';
      }
    }

    async function markCardApplied(index) {
      const job = foundJobs[index];
      const platform = document.getElementById('platformSelect').value;
      await completeActiveBrowserApply({
        platform: platform,
        url: job.url,
        title: job.title,
        company: job.company
      });
      const card = document.getElementById(`job-${index}`);
      if (card) {
        card.querySelector('.job-actions').innerHTML = '<span style="color: var(--success); font-weight: 600;">[✓] Lamaran Dicatat Terkirim!</span>';
      }
      loadRateLimits();
    }

    async function skipJob(index) {
      const job = foundJobs[index];
      const card = document.getElementById(`job-${index}`);
      card.remove();

      try {
        await fetch('/api/skip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: job.url,
            title: job.title,
            company: job.company,
            notes: 'Dilewati via Dashboard'
          })
        });
      } catch (e) {}
    }

    /* KANBAN BOARD & ANALYTICS */
    async function loadAnalytics() {
      try {
        const res = await fetch('/api/analytics');
        const stats = await res.json();
        document.getElementById('statApplied').innerText = stats.applied || 0;
        document.getElementById('statInterview').innerText = stats.interview || 0;
        document.getElementById('statOffering').innerText = stats.offering || 0;
        document.getElementById('statRejected').innerText = stats.rejected || 0;
        document.getElementById('statRate').innerText = `${stats.response_rate || 0}%`;
      } catch (e) {}
    }

    async function loadKanban() {
      try {
        const res = await fetch('/api/history');
        const hist = await res.json();

        const statuses = ['applied', 'interview', 'offering', 'rejected'];
        statuses.forEach(st => {
          const items = hist[st] || [];
          const cap = st.charAt(0).toUpperCase() + st.slice(1);
          const countEl = document.getElementById(`count${cap}`);
          if (countEl) countEl.innerText = items.length;

          const col = document.getElementById(`col${cap}`);
          col.innerHTML = '';
          items.slice(-25).reverse().forEach(item => {
            const card = document.createElement('div');
            card.className = 'kanban-card';

            const encUrl = encodeURIComponent(item.url || '');
            const encTitle = encodeURIComponent(item.title || '');
            const encCompany = encodeURIComponent(item.company || '');
            const encNotes = encodeURIComponent(item.notes || '');

            let interviewBadge = '';
            let schedBtn = '';
            if (st === 'interview') {
              const dtMatch = (item.notes || '').match(/\[Jadwal:\s*([^\]]+)\]/);
              const locMatch = (item.notes || '').match(/\[Lokasi:\s*([^\]]+)\]/);
              if (dtMatch) {
                interviewBadge = `<div style="font-size:0.75rem; color:var(--primary); margin-top:4px; font-weight:600;">📅 ${escapeHtml(dtMatch[1])}${locMatch ? ` (${escapeHtml(locMatch[1])})` : ''}</div>`;
              }
              schedBtn = `
                <div style="display:flex; gap:6px; margin-top:6px; flex-wrap:wrap;">
                  <button class="btn btn-secondary btn-sm" style="font-size:0.75rem; padding:3px 8px;" onclick="openScheduleModal('${encUrl}', '${encTitle}', '${encCompany}', '${encNotes}')">📅 Jadwalkan</button>
                  <a href="/api/job/export-ics?url=${encUrl}" class="btn btn-secondary btn-sm" style="font-size:0.75rem; padding:3px 8px;" title="Unduh file kalender .ics">📥 .ics</a>
                </div>
              `;
            }

            card.innerHTML = `
              <div class="kanban-card-title">${escapeHtml(item.title || 'Posisi')}</div>
              <div class="kanban-card-company">${escapeHtml(item.company || 'Perusahaan')}</div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(item.timestamp || '')}</div>
              ${interviewBadge}
              ${item.notes ? `<div style="font-size: 0.75rem; color: var(--warning); margin-top: 4px;">📌 ${escapeHtml(item.notes)}</div>` : ''}
              ${schedBtn}
              <select class="kanban-card-select" onchange="moveKanban('${encUrl}', this.value, '${encTitle}', '${encCompany}', '${encNotes}')">
                <option value="applied" ${st === 'applied' ? 'selected' : ''}>Terkirim</option>
                <option value="interview" ${st === 'interview' ? 'selected' : ''}>Interview</option>
                <option value="offering" ${st === 'offering' ? 'selected' : ''}>Offering</option>
                <option value="rejected" ${st === 'rejected' ? 'selected' : ''}>Ditolak</option>
              </select>
            `;
            col.appendChild(card);
          });
        });
      } catch (e) {
        console.error('Gagal memuat kanban:', e);
      }
    }

    async function moveKanban(encUrl, newStatus, encTitle = '', encCompany = '', encNotes = '') {
      const url = decodeURIComponent(encUrl);
      if (newStatus === 'interview') {
        openScheduleModal(encUrl, encTitle, encCompany, encNotes);
        return;
      }
      const note = prompt('Catatan perkembangan (opsional):');
      if (note === null) {
        loadKanban();
        return;
      }
      try {
        await fetch('/api/status-update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url, status: newStatus, notes: note })
        });
        loadKanban();
        loadAnalytics();
        fetchLogs();
      } catch (e) {}
    }

    /* KUOTA AMAN */
    async function loadRateLimits() {
      try {
        const res = await fetch('/api/rate-limits');
        const data = await res.json();
        if (data.success && data.quotas) {
          const q = data.quotas;
          const b = document.getElementById('rateLimitBadge');
          if (b) {
            const js = q.jobstreet || { hour_count: 0, hour_limit: 15, day_count: 0, day_limit: 40 };
            const remHour = Math.max(0, js.hour_limit - js.hour_count);
            b.innerText = `🛡️ Kuota Aman: ${remHour}/jam`;
            b.title = `Sisa kuota pengiriman otomatis per jam agar akun Anda aman dari pembatasan portal.`;
          }
        }
      } catch (e) {}
    }

    /* MODAL STATUS KONEKSI & BANTUAN */
    function openDiagnosticModal() {
      document.getElementById('diagnosticModal').classList.add('active');
      runDiagnosticCheck();
    }
    function closeDiagnosticModal() {
      document.getElementById('diagnosticModal').classList.remove('active');
    }
    async function runDiagnosticCheck() {
      const box = document.getElementById('diagnosticResultsBox');
      box.innerHTML = '<span class="spinner"></span> Sedang memeriksa akses ke seluruh portal kerja...';
      try {
        const res = await fetch('/api/diagnostic/health');
        const data = await res.json();
        if (data.success && data.health) {
          const h = data.health;
          const portalLabels = {
            jobstreet: 'JobStreet Indonesia',
            glints: 'Glints Indonesia',
            maganghub: 'MagangHub Kemnaker',
            dealls: 'Dealls Jobs'
          };
          let portalRows = '';
          for (const [pname, pinfo] of Object.entries(h.portals || {})) {
            const isOk = pinfo.reachable;
            const label = portalLabels[pname] || pname.toUpperCase();
            portalRows += `
              <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.06);">
                <span style="font-weight:600;">${label}</span>
                <span style="color:${isOk ? 'var(--success)' : 'var(--danger)'}; font-weight:600;">
                  ${isOk ? '✓ Lancar (Dapat Diakses)' : '✗ Sedang Gangguan'}
                </span>
              </div>
            `;
          }
          box.innerHTML = `
            <div style="font-weight:700; color:var(--primary); margin-bottom:8px;">Status Akses Portal Kerja:</div>
            ${portalRows}
            <div style="margin-top:12px; display:flex; flex-direction:column; gap:4px; font-size:0.8rem; color:var(--text-muted);">
              <div>Status Sesi Akun: ${h.browser_session?.session_cookies_present ? '✓ Akun tersimpan dan aktif' : 'Belum masuk (Gunakan tombol Masuk Akun Portal)'}</div>
              <div>Berkas CV: ${h.active_cv?.ready ? `✓ Siap (${escapeHtml(h.active_cv.filename)})` : 'Belum diunggah'}</div>
            </div>
          `;
        }
      } catch (e) {
        box.innerHTML = `<span style="color:var(--danger);">Gagal memeriksa koneksi: ${escapeHtml(e.message)}</span>`;
      }
    }

    /* INTERVIEW MODAL & SCHEDULER */
    let currentInterviewUrl = null;
    function openScheduleModal(encUrl, encTitle, encCompany, encNotes) {
      currentInterviewUrl = decodeURIComponent(encUrl);
      const title = decodeURIComponent(encTitle || '');
      const company = decodeURIComponent(encCompany || '');
      const notes = decodeURIComponent(encNotes || '');

      document.getElementById('interviewModalJobTitle').innerText = `${title} — ${company}`;

      const matchDt = notes.match(/\[Jadwal:\s*([^\]]+)\]/);
      if (matchDt) {
        document.getElementById('interviewInputDateTime').value = matchDt[1].trim();
      } else {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(10, 0, 0, 0);
        const pad = n => n < 10 ? '0' + n : n;
        const isoStr = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth()+1)}-${pad(tomorrow.getDate())}T${pad(tomorrow.getHours())}:${pad(tomorrow.getMinutes())}`;
        document.getElementById('interviewInputDateTime').value = isoStr;
      }

      const matchLoc = notes.match(/\[Lokasi:\s*([^\]]+)\]/);
      document.getElementById('interviewInputLocation').value = matchLoc ? matchLoc[1].trim() : '';

      const cleanNotes = notes.replace(/\[(Jadwal|Lokasi):[^\]]+\]/g, '').trim();
      document.getElementById('interviewInputNotes').value = cleanNotes;

      document.getElementById('interviewModal').classList.add('active');
    }

    function closeInterviewModal() {
      document.getElementById('interviewModal').classList.remove('active');
      currentInterviewUrl = null;
    }

    async function saveInterviewSchedule() {
      if (!currentInterviewUrl) return;
      const dt = document.getElementById('interviewInputDateTime').value.trim();
      const loc = document.getElementById('interviewInputLocation').value.trim();
      const notes = document.getElementById('interviewInputNotes').value.trim();

      try {
        const res = await fetch('/api/job/set-interview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: currentInterviewUrl,
            datetime: dt,
            location: loc,
            notes: notes
          })
        });
        const data = await res.json();
        if (data.success) {
          closeInterviewModal();
          loadKanban();
          loadAnalytics();
          fetchLogs();
        }
      } catch (e) {
        alert('Gagal menyimpan jadwal interview: ' + e.message);
      }
    }

    /* UNANSWERED QUESTIONS AUTO-LEARNING BANK */
    function showUnansweredQuestionsModal(questions) {
      if (!questions || !questions.length) return;
      const list = document.getElementById('qaQuestionsList');
      list.innerHTML = '';
      questions.forEach((q, idx) => {
        const row = document.createElement('div');
        row.style.background = '#0b1120';
        row.style.border = '1px solid var(--border)';
        row.style.borderRadius = '8px';
        row.style.padding = '10px 12px';

        const qText = q.question || q.keyword || 'Pertanyaan';
        const kwText = q.keyword || qText.slice(0, 15);

        row.innerHTML = `
          <div style="font-weight:600; font-size:0.85rem; color:#fff; margin-bottom:4px;">
            ❓ ${escapeHtml(qText)}
          </div>
          <div style="display:flex; gap:8px; align-items:center; margin-top:6px;">
            <input type="text" id="qaInput_${idx}" placeholder="Jawaban Anda (misal: Ya / S1 / 2 tahun)" style="flex:1; padding:6px 10px; font-size:0.85rem;">
            <button class="btn btn-primary btn-sm" onclick="saveAnswerToBank('${escapeHtml(kwText)}', '${escapeHtml(qText)}', 'qaInput_${idx}', this)">💾 Simpan</button>
          </div>
        `;
        list.appendChild(row);
      });
      document.getElementById('qaModal').classList.add('active');
    }

    function closeQaModal() {
      document.getElementById('qaModal').classList.remove('active');
    }

    async function saveAnswerToBank(keyword, question, inputId, btnEl) {
      const val = document.getElementById(inputId).value.trim();
      if (!val) {
        alert('Harap isi jawaban sebelum menyimpan.');
        return;
      }
      btnEl.disabled = true;
      btnEl.innerText = 'Menyimpan...';
      try {
        const res = await fetch('/api/qa/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            keyword: keyword || question.slice(0, 20),
            question: question,
            answer: val
          })
        });
        const data = await res.json();
        if (data.success) {
          btnEl.innerText = '✓ Tersimpan';
          btnEl.classList.remove('btn-primary');
          btnEl.classList.add('btn-success');
          loadConfig();
        } else {
          btnEl.innerText = 'Gagal';
          btnEl.disabled = false;
        }
      } catch (e) {
        btnEl.innerText = 'Error';
        btnEl.disabled = false;
      }
    }

    /* COVER LETTER MODAL */
    function openCoverLetterModal(index) {
      activeCLJob = foundJobs[index];
      document.getElementById('clTitle').innerText = `📄 Cover Letter: ${activeCLJob.title} @ ${activeCLJob.company}`;
      regenerateCoverLetter();
      document.getElementById('coverLetterModal').classList.add('active');
    }

    async function regenerateCoverLetter() {
      if (!activeCLJob) return;
      const preset = document.getElementById('clPreset').value;
      try {
        const res = await fetch('/api/cover-letter', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: activeCLJob.title, company: activeCLJob.company, preset: preset })
        });
        const data = await res.json();
        document.getElementById('clText').value = data.cover_letter;
      } catch (e) {}
    }

    function closeModal() {
      document.getElementById('coverLetterModal').classList.remove('active');
    }

    function copyCoverLetter() {
      const txt = document.getElementById('clText');
      txt.select();
      document.execCommand('copy');
      alert('Surat lamaran berhasil disalin ke clipboard!');
    }

    /* DIRECT COLD EMAIL (1-CLICK GMAIL / MAILTO / SMTP) */
    async function generateEmailDraft() {
      const role = document.getElementById('emailRole').value || 'Staff';
      const company = document.getElementById('emailCompany').value || 'Perusahaan';
      const name = document.getElementById('cfgName').value || 'Pelamar';

      document.getElementById('emailSubject').value = `Lamaran Pekerjaan: ${role} - ${name}`;
      try {
        const res = await fetch('/api/cover-letter', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: role, company: company, preset: 'formal' })
        });
        const data = await res.json();
        document.getElementById('emailBody').value = data.cover_letter;
      } catch (e) {}
    }

    function openGmailDraft() {
      const to = document.getElementById('emailTo').value.trim();
      const sub = document.getElementById('emailSubject').value.trim();
      const body = document.getElementById('emailBody').value.trim();

      if (!to || !sub || !body) {
        alert('Mohon isi alamat email tujuan, subjek, dan badan email terlebih dahulu.');
        return;
      }

      const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}&su=${encodeURIComponent(sub)}&body=${encodeURIComponent(body)}`;
      window.open(gmailUrl, '_blank');
      
      // Catat ke history pipeline
      const role = document.getElementById('emailRole').value.trim() || 'Cold Email';
      const company = document.getElementById('emailCompany').value.trim() || to;
      fetch('/api/record-manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: `mailto:${to}`,
          title: role,
          company: company,
          status: 'applied',
          notes: 'Draft Gmail Web 1-Klik'
        })
      }).catch(() => {});
    }

    function openMailtoApp() {
      const to = document.getElementById('emailTo').value.trim();
      const sub = document.getElementById('emailSubject').value.trim();
      const body = document.getElementById('emailBody').value.trim();

      if (!to || !sub || !body) {
        alert('Mohon isi alamat email tujuan, subjek, dan badan email terlebih dahulu.');
        return;
      }

      window.location.href = `mailto:${to}?subject=${encodeURIComponent(sub)}&body=${encodeURIComponent(body)}`;
    }

    function copyEmailBody() {
      const body = document.getElementById('emailBody');
      body.select();
      document.execCommand('copy');
      alert('Teks surat lamaran berhasil disalin!');
    }

    async function sendDirectEmailSMTP() {
      const to = document.getElementById('emailTo').value.trim();
      const sub = document.getElementById('emailSubject').value.trim();
      const body = document.getElementById('emailBody').value.trim();
      const statusDiv = document.getElementById('emailStatus');

      if (!to || !sub || !body) {
        alert('Mohon isi email tujuan, subjek, dan isi email terlebih dahulu.');
        return;
      }

      statusDiv.innerHTML = '<span style="color: var(--primary);">⏳ Sedang mengirim email via SMTP...</span>';

      try {
        const res = await fetch('/api/send-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to_email: to, subject: sub, body: body })
        });
        const data = await res.json();
        if (data.success) {
          statusDiv.innerHTML = `<span style="color: var(--success); font-weight:600;">[✓] ${data.message}</span>`;
        } else {
          statusDiv.innerHTML = `<span style="color: var(--danger);">[x] ${data.message} (Tip: Gunakan tombol 'Buka di Gmail Web' jika belum setup SMTP password)</span>`;
        }
      } catch (e) {
        statusDiv.innerHTML = '<span style="color: var(--danger);">[x] Gagal mengirim email via SMTP</span>';
      }
    }

    /* 1-CLICK APP UPDATE (GITHUB) */
    function openUpdateModal() {
      document.getElementById('updateModal').classList.add('active');
      checkAppUpdate(true);
    }

    function closeUpdateModal() {
      document.getElementById('updateModal').classList.remove('active');
    }

    function dismissUpdateBanner() {
      const banner = document.getElementById('updateAvailableBanner');
      if (banner) banner.style.display = 'none';
      if (window._latestRemoteSha) {
        sessionStorage.setItem('dismissed_update_sha', window._latestRemoteSha);
      }
    }

    async function checkAppUpdate(verbose = false) {
      const box = document.getElementById('updateInfoBox');
      const btnDo = document.getElementById('btnDoUpdate');
      const headerBtn = document.getElementById('btnHeaderUpdate');
      const updateDot = document.getElementById('updateDotBadge');
      const updateBtnText = document.getElementById('btnHeaderUpdateText');
      const banner = document.getElementById('updateAvailableBanner');
      const bannerSummary = document.getElementById('updateBannerSummary');

      if (verbose && box) {
        box.innerHTML = '<span style="color:var(--primary);"><span class="spinner"></span> Menghubungi GitHub untuk mengecek versi terbaru...</span>';
      }

      try {
        const res = await fetch('/api/update/check');
        const data = await res.json();
        if (!data.success) {
          if (box) box.innerHTML = `<span style="color:var(--warning);">[!] ${escapeHtml(data.error)}</span>`;
          return;
        }

        const localSha = (data.local && data.local.sha) ? data.local.sha.slice(0, 7) : 'Belum tercatat';
        const remote = data.remote || {};

        if (data.up_to_date) {
          if (box) {
            box.innerHTML = `<span style="color:var(--success); font-weight:700;">✓ Aplikasi Anda sudah versi terbaru!</span><br><span style="color:var(--text-muted); font-size:0.8rem;">Versi saat ini: ${escapeHtml(localSha)} | Terakhir di GitHub: ${escapeHtml(remote.message || '-')}</span>`;
          }
          if (btnDo) btnDo.style.display = verbose ? 'inline-flex' : 'none';
          if (updateDot) updateDot.style.display = 'none';
          if (updateBtnText) updateBtnText.innerText = '🔄 Cek Update';
          if (headerBtn) headerBtn.className = 'btn btn-secondary btn-sm';
          if (banner) banner.style.display = 'none';
        } else {
          // Ada pembaruan baru!
          window._latestRemoteSha = remote.sha || remote.short_sha;
          if (box) {
            box.innerHTML = `<span style="color:var(--primary); font-weight:700;">🚀 Pembaruan Aplikasi Tersedia!</span><br>Versi lokal: <code>${escapeHtml(localSha)}</code> &rarr; Versi terbaru di GitHub: <code>${escapeHtml(remote.short_sha || 'main')}</code><br><div style="margin-top:6px; color:#fff;"><strong>Catatan pembaruan:</strong> ${escapeHtml(remote.message || 'Perbaikan & peningkatan performa terbaru')}</div>`;
          }
          if (btnDo) btnDo.style.display = 'inline-flex';
          if (updateDot) updateDot.style.display = 'inline-block';
          if (updateBtnText) updateBtnText.innerText = '✨ Ada Update!';
          if (headerBtn) headerBtn.className = 'btn btn-primary btn-sm';

          // Tampilkan banner notifikasi jika belum ditutup di sesi ini
          const dismissedSha = sessionStorage.getItem('dismissed_update_sha');
          if (banner && dismissedSha !== window._latestRemoteSha) {
            if (bannerSummary) {
              bannerSummary.innerHTML = `<strong>${escapeHtml(remote.message || 'Pembaruan aplikasi terbaru')}</strong> &bull; Versi GitHub <code>${escapeHtml(remote.short_sha || 'main')}</code>`;
            }
            banner.style.display = 'block';
          }

          // Notifikasi browser (jika didukung)
          if (window.Notification && Notification.permission === 'granted') {
            if (!sessionStorage.getItem('notified_update_' + window._latestRemoteSha)) {
              sessionStorage.setItem('notified_update_' + window._latestRemoteSha, '1');
              try {
                new Notification('Job Hunter Copilot', {
                  body: `Pembaruan tersedia: ${remote.message || 'Versi baru siap dipasang.'}`,
                });
              } catch (e) {}
            }
          }
        }
      } catch (e) {
        if (box) box.innerHTML = '<span style="color:var(--danger);">Gagal mengecek update ke GitHub.</span>';
      }
    }

    async function applyAppUpdate() {
      const btnDo = document.getElementById('btnDoUpdate');
      const prog = document.getElementById('updateProgressBox');
      const btnRestart = document.getElementById('btnRestartApp');

      btnDo.disabled = true;
      btnDo.innerHTML = '<span class="spinner"></span> Mengunduh Update...';
      prog.style.display = 'block';
      prog.innerHTML = '<span style="color:var(--primary);">⏳ Sedang mengunduh dan memasang pembaruan dari GitHub (data CV & riwayat kamu aman)...</span>';

      try {
        const res = await fetch('/api/update/apply', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          prog.innerHTML = `<span style="color:var(--success); font-weight:700;">[✓] ${data.message}</span>`;
          btnDo.style.display = 'none';
          btnRestart.style.display = 'inline-flex';
          fetchLogs();
        } else {
          prog.innerHTML = `<span style="color:var(--danger);">[x] ${data.error}</span>`;
        }
      } catch (e) {
        prog.innerHTML = '<span style="color:var(--danger);">[x] Koneksi terputus saat memperbarui aplikasi.</span>';
      } finally {
        btnDo.disabled = false;
        btnDo.innerText = '⬇️ Update Sekarang';
      }
    }

    async function restartAppAfterUpdate() {
      const prog = document.getElementById('updateProgressBox');
      prog.innerHTML = '<span style="color:var(--primary);">🔄 Memuat ulang aplikasi... Halaman akan refresh otomatis dalam 3 detik.</span>';
      try {
        await fetch('/api/update/restart', { method: 'POST' });
      } catch (e) {}
      setTimeout(() => { window.location.reload(); }, 3000);
    }

    function initActiveTab() {
      const currentPath = window.location.pathname.toLowerCase();
      const serverInitial = document.body ? document.body.dataset.initialTab : null;
      const hash = window.location.hash.replace('#', '').toLowerCase();

      let targetTab = 'huntTab';
      if (hash === 'kanban' || hash === 'lamaran') targetTab = 'kanbanTab';
      else if (hash === 'cv') targetTab = 'cvTab';
      else if (hash === 'email') targetTab = 'emailTab';
      else if (hash === 'profile' || hash === 'profil' || hash === 'pengaturan') targetTab = 'profileTab';
      else if (PATH_TAB_MAP[currentPath]) targetTab = PATH_TAB_MAP[currentPath];
      else if (serverInitial && document.getElementById(serverInitial)) targetTab = serverInitial;
      else {
        try {
          const saved = sessionStorage.getItem('copilot_active_tab');
          if (saved && document.getElementById(saved)) targetTab = saved;
        } catch (e) {}
      }

      switchTab(targetTab, null, false);
    }

    function restoreCachedJobs() {
      try {
        const cached = sessionStorage.getItem('copilot_found_jobs');
        if (cached) {
          const parsed = JSON.parse(cached);
          if (Array.isArray(parsed) && parsed.length > 0) {
            foundJobs = parsed;
            renderJobs();
            const status = document.getElementById('scanStatus');
            if (status) {
              status.style.display = 'block';
              status.innerText = `Menampilkan ${foundJobs.length} lowongan dari pencarian terakhir.`;
            }
          }
        }
      } catch (e) {}
    }

    initActiveTab();
    restoreCachedJobs();
    checkSecurityStatus();
    loadConfig();
    loadCVList();
    fetchLogs();
    refreshBrowserStatus();
    loadRateLimits();
    checkAppUpdate(false);

    // Cek update otomatis setiap 5 menit & saat kembali membuka tab
    setInterval(() => { checkAppUpdate(false); }, 300000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        checkAppUpdate(false);
      }
    });
