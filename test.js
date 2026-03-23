
    // ════════════════════════════════════════════════════════
    // STORAGE HELPERS
    // ════════════════════════════════════════════════════════
    const DB = {
      get: (k, d = {}) => { try { return JSON.parse(localStorage.getItem(k)) || d } catch(e) { return d } },
      set: (k, v) => localStorage.setItem(k, JSON.stringify(v)),
      key: (cid, fyid, type) => `inas12_${type}_${cid}_${fyid}`
    };

    // ════════════════════════════════════════════════════════
    // APP STATE
    // ════════════════════════════════════════════════════════
    let state = {
      user: null,
      theme: localStorage.getItem('inas12_theme') || 'light',
      companies: DB.get('inas12_companies', []),
      activeCompanyId: null, activeCompanyName: '—',
      activeFYId: null, activeFY: '—',
      selCompanyId: null,  // for company screen
      selPartId: null,
      selLossId: null,
      selLeaseId: null,
      profitability: true,
    };

    // ════════════════════════════════════════════════════════
    // AUTH
    // ════════════════════════════════════════════════════════
    const USERS = [{ user: 'Dev Patel', pw: 'Dev@2894' }];
    function doLogin() {
      const u = V('login-user'), p = V('login-pw');
      const found = USERS.find(x => x.user === u && x.pw === p);
      if (found) {
        state.user = u;
        $('login-page').style.display = 'none';
        $('app').style.display = 'block';
        $('sb-user').textContent = u;
        $('dash-welcome').textContent = `Welcome back, ${u}!`;
        applyTheme(state.theme);
        renderCompanies();
      } else {
        $('login-err').textContent = 'Invalid username or password.';
      }
    }
    function doLogout() {
      state.user = null;
      $('app').style.display = 'none';
      $('login-page').style.display = 'flex';
      $('login-pw').value = '';
      $('login-err').textContent = '';
    }

    // ════════════════════════════════════════════════════════
    // NAVIGATION
    // ════════════════════════════════════════════════════════
    function nav(id) {
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      $(id).classList.add('active');
      document.querySelectorAll('.nav-item').forEach(n => {
        if (n.getAttribute('onclick') === `nav('${id}')`) n.classList.add('active');
      });
      if (id === 'summary') renderSummary();
      if (id === 'journal') generateJE();
      if (id === 'flowtable') renderFlowTable();
      if (id === 'opening') loadOpeningBalance();
      if (id === 'taxrate') loadTaxRate();
      if (id === 'particulars') renderParticulars();
      if (id === 'losses') renderLosses();
      if (id === 'profitability') loadProfitability();
      if (id === 'mat') loadMat();
      if (id === 'leases') renderLeases();
      if (id === 'etr') loadETR();
    }

    // ════════════════════════════════════════════════════════
    // THEME
    // ════════════════════════════════════════════════════════
    function toggleTheme() {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      localStorage.setItem('inas12_theme', state.theme);
      applyTheme(state.theme);
    }
    function applyTheme(t) {
      document.body.setAttribute('data-theme', t);
      $('app').setAttribute('data-theme', t);
      const btn = document.querySelector('.theme-btn');
      if (btn) btn.textContent = t === 'dark' ? '☀️ Toggle Day Mode' : '🌙 Toggle Night Mode';
    }

    // ════════════════════════════════════════════════════════
    // UTILITIES
    // ════════════════════════════════════════════════════════
    function $(id) { return document.getElementById(id) }
    function V(id) { return $(id).value.trim() }
    function inr(n) {
      const neg = n < 0; n = Math.abs(n);
      let s = n.toFixed(2), [int, dec] = s.split('.');
      if (int.length > 3) {
        const last3 = int.slice(-3), rest = int.slice(0, -3);
        const grps = []; let r = rest;
        while (r.length > 2) { grps.unshift(r.slice(-2)); r = r.slice(0, -2) }
        if (r) grps.unshift(r);
        int = grps.join(',') + ',' + last3;
      }
      const res = `₹${int}.${dec}`;
      return neg ? `(${res})` : res;
    }
    function showMsg(id, text, ok = true) {
      const el = $(id); if (!el) return;
      el.className = `status-msg ${ok ? 'ok' : 'err'}`;
      el.style.display = 'inline-block';
      el.textContent = text;
      setTimeout(() => { el.style.display = 'none' }, 3000);
    }
    function ctx() { return state.activeCompanyId && state.activeFYId; }
    function needCtx() { if (!ctx()) { alert('Please set an Active Company and Financial Year first.\n(Go to Company & FY screen and click "Set Active")'); return false; } return true; }
    function updateStatusBar() {
      $('sb-company').textContent = state.activeCompanyName;
      $('sb-fy').textContent = state.activeFY;
      const rate = ctx() ? (DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'taxrate'), { rate: null }).rate) : null;
      $('sb-rate').textContent = rate ? rate + '%' : '—';
    }
    function getTaxRate() {
      if (!ctx()) return 0;
      return DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'taxrate'), { rate: 25.168 }).rate || 25.168;
    }

    // ════════════════════════════════════════════════════════
    // COMPANY & FY
    // ════════════════════════════════════════════════════════
    function saveCompanies() { DB.set('inas12_companies', state.companies); }

    function saveCompany() {
      const name = V('c-name'), pan = V('c-pan');
      if (!name) { alert('Company name is required.'); return; }
      if (state.selCompanyId) {
        const c = state.companies.find(x => x.id === state.selCompanyId);
        if (c) { c.name = name; c.pan = pan; }
      } else {
        state.companies.push({ id: Date.now(), name, pan, fys: [] });
      }
      saveCompanies(); clearCompanyForm(); renderCompanies();
      showMsg('company-msg', 'Company saved!');
    }

    function deleteCompany() {
      if (!state.selCompanyId) { alert('Select a company first.'); return; }
      if (!confirm('Delete this company and ALL data? This cannot be undone.')) return;
      state.companies = state.companies.filter(x => x.id !== state.selCompanyId);
      if (state.activeCompanyId === state.selCompanyId) { state.activeCompanyId = null; state.activeCompanyName = '—'; state.activeFYId = null; state.activeFY = '—'; }
      state.selCompanyId = null;
      saveCompanies(); renderCompanies(); updateStatusBar();
    }

    function clearCompanyForm() {
      state.selCompanyId = null;
      $('c-name').value = ''; $('c-pan').value = '';
      $('fy-tbody').innerHTML = '';
      $('fy-for-company').textContent = 'Select a company above';
      document.querySelectorAll('#company-tbody tr').forEach(r => r.classList.remove('selected'));
    }

    function renderCompanies() {
      const tb = $('company-tbody'); if (!tb) return;
      tb.innerHTML = '';
      state.companies.forEach((c, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${i + 1}</td><td>${c.name}</td><td>${c.pan || '—'}</td>
      <td><button class="btn btn-success btn-sm" onclick="setActiveCompany(${c.id})">✅ Set Active</button></td>`;
        tr.onclick = () => selectCompany(c.id, tr);
        tb.appendChild(tr);
      });
    }

    function selectCompany(id, tr) {
      state.selCompanyId = id;
      document.querySelectorAll('#company-tbody tr').forEach(r => r.classList.remove('selected'));
      tr.classList.add('selected');
      const c = state.companies.find(x => x.id === id);
      if (c) { $('c-name').value = c.name; $('c-pan').value = c.pan || ''; }
      $('fy-for-company').textContent = c ? c.name : '';
      renderFYs(id);
    }

    function renderFYs(cid) {
      const c = state.companies.find(x => x.id === cid);
      const tb = $('fy-tbody'); if (!tb || !c) return;
      tb.innerHTML = '';
      (c.fys || []).forEach(fy => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${fy.fy}</td><td>${fy.yearEnd}</td>
      <td><button class="btn btn-success btn-sm" onclick="setActiveFY(${cid},'${fy.fy}','${fy.yearEnd}')">✅ Set Active</button>
          <button class="btn btn-danger btn-sm" style="margin-left:4px" onclick="deleteFY(${cid},'${fy.fy}')">🗑</button></td>`;
        tb.appendChild(tr);
      });
    }

    function addFY() {
      if (!state.selCompanyId) { alert('Select a company first.'); return; }
      const fy = V('fy-select');
      const c = state.companies.find(x => x.id === state.selCompanyId);
      if (!c) return;
      if ((c.fys || []).find(f => f.fy === fy)) { alert(`FY ${fy} already added.`); return; }
      const yr = parseInt(fy.split('-')[0]) + 1;
      if (!c.fys) c.fys = [];
      c.fys.push({ fy, yearEnd: `31-Mar-${yr}` });
      saveCompanies(); renderFYs(state.selCompanyId);
    }

    function deleteFY(cid, fy) {
      const c = state.companies.find(x => x.id === cid);
      if (!c) return;
      c.fys = c.fys.filter(f => f.fy !== fy);
      saveCompanies(); renderFYs(cid);
    }

    function setActiveCompany(id) {
      const c = state.companies.find(x => x.id === id);
      if (!c) return;
      state.activeCompanyId = id; state.activeCompanyName = c.name;
      updateStatusBar();
      alert(`Active company set to: ${c.name}`);
    }

    function setActiveFY(cid, fy, yearEnd) {
      state.activeFYId = fy; state.activeFY = fy;
      updateStatusBar();
      alert(`Active FY set to: ${fy} (ends ${yearEnd})`);
    }

    // ════════════════════════════════════════════════════════
    // OPENING BALANCES
    // ════════════════════════════════════════════════════════
    function loadOpeningBalance() {
      if (!ctx()) return;
      const d = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'ob'), { dta: 0, dtl: 0 });
      $('ob-dta').value = d.dta; $('ob-dtl').value = d.dtl;
    }
    function saveOpeningBalance() {
      if (!needCtx()) return;
      DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'ob'),
        { dta: parseFloat($('ob-dta').value) || 0, dtl: parseFloat($('ob-dtl').value) || 0 });
      showMsg('ob-msg', 'Opening balances saved!');
    }

    // ════════════════════════════════════════════════════════
    // TAX RATE
    // ════════════════════════════════════════════════════════
    function applyPreset() {
      const v = $('tax-preset').value;
      if (v !== 'custom') $('tax-rate-val').value = v;
    }
    function loadTaxRate() {
      if (!ctx()) return;
      const d = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'taxrate'), { rate: 25.168 });
      $('tax-rate-val').value = d.rate;
    }
    function saveTaxRate() {
      if (!needCtx()) return;
      const rate = parseFloat($('tax-rate-val').value);
      if (!rate || rate <= 0 || rate >= 100) { alert('Enter a valid tax rate (0–100).'); return; }
      DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'taxrate'), { rate });
      updateStatusBar();
      showMsg('tax-msg', `Tax rate ${rate}% saved!`);
    }

    // ════════════════════════════════════════════════════════
    // PARTICULARS
    // ════════════════════════════════════════════════════════
    function getParticulars() {
      if (!ctx()) return [];
      return DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'particulars'), []);
    }
    function saveParticulars(data) {
      DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'particulars'), data);
    }
    function calcParticular() {
      const bv = parseFloat($('p-bv').value) || 0;
      const tv = parseFloat($('p-tv').value) || 0;
      const itemtype = $('p-itemtype').value;
      const difftype = $('p-difftype').value;
      const routing = $('p-routing') ? $('p-routing').value : 'P&L';
      const rate = getTaxRate();

      let td = Math.abs(bv - tv);
      let nature = '—';

      if (bv !== tv) {
        if (itemtype === 'Asset') {
          nature = bv > tv ? 'DTL' : 'DTA';
        } else {
          nature = bv > tv ? 'DTA' : 'DTL';
        }
      }

      if (difftype === 'Permanent') {
        nature = 'Permanent';
      }

      $('p-td').value = td.toFixed(2);
      $('p-nature').value = nature;
      $('p-amt').value = (nature === 'Permanent' || nature === '—') ? '0.00' : (td * rate / 100).toFixed(2);
    }
    function addParticular() {
      if (!needCtx()) return;
      const name = V('p-name'); if (!name) { alert('Description required.'); return; }
      calcParticular();
      const routing = $('p-routing') ? $('p-routing').value : 'P&L';
      const data = getParticulars();
      data.push({
        id: Date.now(), name, itemtype: V('p-itemtype'), difftype: V('p-difftype'), routing, bv: parseFloat($('p-bv').value) || 0, tv: parseFloat($('p-tv').value) || 0,
        td: parseFloat($('p-td').value) || 0, nature: V('p-nature'), amt: parseFloat($('p-amt').value) || 0
      });
      saveParticulars(data); clearParticular(); renderParticulars();
    }
    function updateParticular() {
      if (!state.selPartId) { alert('Select a row to update.'); return; }
      const data = getParticulars();
      const item = data.find(x => x.id === state.selPartId);
      if (!item) return;
      calcParticular();
      item.name = V('p-name');
      item.itemtype = V('p-itemtype');
      item.difftype = V('p-difftype');
      item.routing = $('p-routing') ? $('p-routing').value : 'P&L';
      item.bv = parseFloat($('p-bv').value) || 0;
      item.tv = parseFloat($('p-tv').value) || 0; item.td = parseFloat($('p-td').value) || 0;
      item.nature = V('p-nature'); item.amt = parseFloat($('p-amt').value) || 0;
      saveParticulars(data); clearParticular(); renderParticulars();
    }
    function deleteParticular() {
      if (!state.selPartId) { alert('Select a row to delete.'); return; }
      if (!confirm('Delete this particular?')) return;
      const data = getParticulars().filter(x => x.id !== state.selPartId);
      saveParticulars(data); state.selPartId = null; clearParticular(); renderParticulars();
    }
    function clearParticular() {
      state.selPartId = null;
      $('p-name').value = '';
      if ($('p-itemtype')) $('p-itemtype').value = 'Asset';
      if ($('p-difftype')) $('p-difftype').value = 'Temporary';
      if ($('p-routing')) $('p-routing').value = 'P&L';
      $('p-bv').value = '0'; $('p-tv').value = '0';
      $('p-td').value = '0'; $('p-amt').value = '0'; $('p-nature').value = '—';
      document.querySelectorAll('#p-tbody tr').forEach(r => r.classList.remove('selected'));
    }
    function renderParticulars() {
      const tb = $('p-tbody'); if (!tb) return;
      tb.innerHTML = '';
      let totDTA = 0, totDTL = 0;
      getParticulars().forEach((p, i) => {
        const tr = document.createElement('tr');
        let cls = 'amt-net-pos';
        let tagCls = 'tag-dta';
        let tagStyle = '';
        if (p.nature === 'DTA') { cls = 'amt-dta'; tagCls = 'tag-dta'; totDTA += p.amt; }
        else if (p.nature === 'DTL') { cls = 'amt-dtl'; tagCls = 'tag-dtl'; totDTL += p.amt; }
        else { cls = 'amt-net-neg'; tagCls = ''; tagStyle = 'background:rgba(255,255,255,0.05);color:var(--fg2);border:1px solid var(--border)'; }

        const itype = p.itemtype || 'Asset';
        const dtype = p.difftype || 'Temporary';
        const routing = p.routing || 'P&L';

        tr.innerHTML = `<td>${i + 1}</td><td>${p.name}</td><td>${itype}</td><td>${dtype}</td><td><span class="tag ${routing==='OCI'?'tag-dtl':''}">${routing}</span></td><td>${inr(p.bv)}</td><td>${inr(p.tv)}</td>
      <td>${inr(p.td)}</td><td><span class="tag ${tagCls}" style="${tagStyle}">${p.nature}</span></td>
      <td class="${cls}">${inr(p.amt)}</td>`;
        tr.onclick = () => {
          document.querySelectorAll('#p-tbody tr').forEach(r => r.classList.remove('selected'));
          tr.classList.add('selected');
          state.selPartId = p.id;
          $('p-name').value = p.name;
          if ($('p-itemtype')) $('p-itemtype').value = itype;
          if ($('p-difftype')) $('p-difftype').value = dtype;
          if ($('p-routing')) $('p-routing').value = routing;
          $('p-bv').value = p.bv; $('p-tv').value = p.tv;
          $('p-td').value = p.td; $('p-nature').value = p.nature; $('p-amt').value = p.amt;
        };
        tb.appendChild(tr);
      });
      $('p-total').innerHTML = `<span class="amt-dta">DTA: ${inr(totDTA)}</span> &nbsp; <span class="amt-dtl">DTL: ${inr(totDTL)}</span>`;
    }

    // ════════════════════════════════════════════════════════
    // LOSSES
    // ════════════════════════════════════════════════════════
    function getLosses() {
      if (!ctx()) return [];
      return DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'losses'), []);
    }
    function saveLosses(data) { DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'losses'), data); }
    function calcLoss() {
      const lt = $('l-type').value;
      let cf = parseInt($('l-cf').value) || 8;
      if (lt === 'Unabsorbed Depreciation') { cf = 99; $('l-cf').value = 99; }
      const ay = V('l-ay');
      const startYr = parseInt((ay.split(' ')[1] || '2024-25').split('-')[0]);
      const expiryYr = startYr + cf;
      $('l-expiry').value = lt === 'Unabsorbed Depreciation' ? 'Unlimited' : `AY ${expiryYr}-${String(expiryYr + 1).slice(-2)}`;
      const loss = parseFloat($('l-amt').value) || 0;
      $('l-dta').value = (loss * getTaxRate() / 100).toFixed(2);
    }
    function addLoss() {
      if (!needCtx()) return;
      calcLoss();
      const data = getLosses();
      data.push({
        id: Date.now(), ay: V('l-ay'), type: V('l-type'),
        amt: parseFloat($('l-amt').value) || 0, cf: parseInt($('l-cf').value) || 8,
        expiry: V('l-expiry'), dta: parseFloat($('l-dta').value) || 0
      });
      saveLosses(data); clearLoss(); renderLosses();
    }
    function updateLoss() {
      if (!state.selLossId) { alert('Select a row.'); return; }
      calcLoss();
      const data = getLosses();
      const item = data.find(x => x.id === state.selLossId);
      if (!item) return;
      item.ay = V('l-ay'); item.type = V('l-type'); item.amt = parseFloat($('l-amt').value) || 0;
      item.cf = parseInt($('l-cf').value) || 8; item.expiry = V('l-expiry'); item.dta = parseFloat($('l-dta').value) || 0;
      saveLosses(data); clearLoss(); renderLosses();
    }
    function deleteLoss() {
      if (!state.selLossId) { alert('Select a row.'); return; }
      if (!confirm('Delete this entry?')) return;
      saveLosses(getLosses().filter(x => x.id !== state.selLossId));
      state.selLossId = null; clearLoss(); renderLosses();
    }
    function clearLoss() {
      state.selLossId = null;
      $('l-ay').value = 'AY 2024-25'; $('l-type').value = 'Business Loss';
      $('l-amt').value = '0'; $('l-cf').value = '8'; $('l-expiry').value = ''; $('l-dta').value = '0';
      document.querySelectorAll('#l-tbody tr').forEach(r => r.classList.remove('selected'));
    }
    function renderLosses() {
      const tb = $('l-tbody'); if (!tb) return;
      tb.innerHTML = ''; let tot = 0;
      getLosses().forEach((l, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${i + 1}</td><td>${l.ay}</td><td>${l.type}</td>
      <td>${inr(l.amt)}</td><td>${l.cf}</td><td>${l.expiry}</td>
      <td class="amt-dta">${inr(l.dta)}</td>`;
        tr.onclick = () => {
          document.querySelectorAll('#l-tbody tr').forEach(r => r.classList.remove('selected'));
          tr.classList.add('selected');
          state.selLossId = l.id;
          $('l-ay').value = l.ay; $('l-type').value = l.type; $('l-amt').value = l.amt;
          $('l-cf').value = l.cf; $('l-expiry').value = l.expiry; $('l-dta').value = l.dta;
        };
        tb.appendChild(tr); tot += l.dta;
      });
      $('l-total').textContent = inr(tot);
    }

    // ════════════════════════════════════════════════════════
    // PROFITABILITY
    // ════════════════════════════════════════════════════════
    function loadProfitability() {
      if (!ctx()) return;
      const d = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'), { canProfit: true, remarks: '' });
      setProfitability(d.canProfit, false);
      $('prof-remarks').value = d.remarks || '';
    }
    function setProfitability(val, alertUser = false) {
      state.profitability = val;
      $('prof-yes-btn').className = 'toggle-opt' + (val ? ' active' : '');
      $('prof-no-btn').className = 'toggle-opt' + (!val ? ' active' : '');
      const alert = $('prof-alert');
      if (val) {
        alert.innerHTML = `<div class="alert alert-success">✅ DTA will be <strong>RECOGNISED</strong> in the Balance Sheet as a Deferred Tax Asset.</div>`;
      } else {
        alert.innerHTML = `<div class="alert alert-danger">❌ DTA on Losses/Unabsorbed Dep. will <strong>NOT be recognised</strong>. Only timing-difference DTA (from Particulars) will be recognised. Disclose unrecognised DTA in Notes.</div>`;
      }
    }
    function saveProfitability() {
      if (!needCtx()) return;
      DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'),
        { canProfit: state.profitability, remarks: V('prof-remarks') });
      showMsg('prof-msg', 'Assessment saved!');
    }

    // ════════════════════════════════════════════════════════
    // SUMMARY
    // ════════════════════════════════════════════════════════
    function calcTotals() {
      if (!ctx()) return null;
      const ob = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'ob'), { dta: 0, dtl: 0 });
      const parts = getParticulars();
      const losses = getLosses();
      const leases = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), []);
      const mat = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'mat'), { open:0, add:0, util:0, prob:true });
      const prof = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'), { canProfit: true });
      
      let partDTA_PL = 0, partDTL_PL = 0, partDTA_OCI = 0, partDTL_OCI = 0;
      parts.forEach(p => { 
        if (p.nature === 'DTA') { if(p.routing==='OCI') partDTA_OCI += p.amt; else partDTA_PL += p.amt; }
        else if (p.nature === 'DTL') { if(p.routing==='OCI') partDTL_OCI += p.amt; else partDTL_PL += p.amt; }
      });
      
      let lossDTA = prof.canProfit ? losses.reduce((s, l) => s + l.dta, 0) : 0;
      let matDTA = mat.prob ? (mat.open + mat.add - mat.util) : 0;
      let leaseDTA = 0, leaseDTL = 0;
      leases.forEach(l => { if (l.nature === 'DTA') leaseDTA += l.tax; else if(l.nature === 'DTL') leaseDTL += l.tax; });
      
      const partDTA = partDTA_PL + partDTA_OCI;
      const partDTL = partDTL_PL + partDTL_OCI;
      const closeDTA = (ob.dta || 0) + partDTA + lossDTA + matDTA + leaseDTA;
      const closeDTL = (ob.dtl || 0) + partDTL + leaseDTL;
      const net = closeDTA - closeDTL;
      
      return { openDTA: ob.dta || 0, openDTL: ob.dtl || 0, partDTA_PL, partDTA_OCI, partDTL_PL, partDTL_OCI, partDTA, partDTL, lossDTA, matDTA, leaseDTA, leaseDTL, closeDTA, closeDTL, net, profitability: prof.canProfit };
    }
    function renderSummary() {
      const t = calcTotals();
      if (!t) return;
      const netClass = t.net >= 0 ? 'net' : 'net-neg';
      const netValClass = t.net >= 0 ? 'blue' : 'red';
      $('summary-cards').innerHTML = `
    <div class="sum-card dta"><div class="sum-label">Opening DTA</div><div class="sum-val green">${inr(t.openDTA)}</div></div>
    <div class="sum-card dtl"><div class="sum-label">Opening DTL</div><div class="sum-val amber">${inr(t.openDTL)}</div></div>
    <div class="sum-card dta"><div class="sum-label">Closing DTA (Total)</div><div class="sum-val green">${inr(t.closeDTA)}</div></div>
    <div class="sum-card dtl"><div class="sum-label">Closing DTL (Total)</div><div class="sum-val amber">${inr(t.closeDTL)}</div></div>
    <div class="sum-card ${netClass}"><div class="sum-label">Net DTA / (DTL)</div><div class="sum-val ${netValClass}">${inr(t.net)}</div></div>
    <div class="sum-card"><div class="sum-label">Future Profitability</div><div class="sum-val" style="font-size:16px">${t.profitability ? '✅ DTA Recognised' : '❌ DTA Not Recognised'}</div></div>`;
      // Detail table
      const tb = $('summary-tbody'); tb.innerHTML = '';
      const addRow = (label, open, recog, type, route, close, bold = false) => {
        const cls = type === 'DTA' ? 'amt-dta' : type === 'DTL' ? 'amt-dtl' : '';
        const tag = type ? `<span class="tag tag-${type.toLowerCase()}">${type}</span>` : '';
        const rTag = route ? `<span class="tag ${route==='OCI'?'tag-dtl':''}">${route}</span>` : '';
        tb.innerHTML += `<tr class="${bold ? 'tbl-total' : ''}">
      <td>${label}</td><td>${inr(open)}</td><td class="${cls}">${inr(recog)}</td>
      <td>${tag} ${rTag}</td><td class="${cls}">${inr(close)}</td></tr>`;
      };
      addRow('Opening DTA', t.openDTA, 0, 'DTA', '', t.openDTA);
      getParticulars().filter(p => p.nature === 'DTA').forEach(p => addRow('  ' + p.name, 0, p.amt, 'DTA', p.routing||'P&L', p.amt));
      getLosses().forEach(l => addRow(`  Loss/Dep (${l.ay})`, 0, t.profitability ? l.dta : 0, 'DTA', 'P&L', t.profitability ? l.dta : 0));
      DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), []).filter(l=>l.nature==='DTA').forEach(l=>addRow(`  Lease Netting: ${l.name}`, 0, l.tax, 'DTA', 'P&L', l.tax));
      if(t.matDTA > 0) addRow('  MAT Credit Entitlement', 0, t.matDTA, 'DTA', 'P&L', t.matDTA);
      addRow('Total DTA', t.openDTA, t.closeDTA - t.openDTA, 'DTA', '', t.closeDTA, true);
      tb.innerHTML += `<tr><td colspan="5"></td></tr>`;
      addRow('Opening DTL', t.openDTL, 0, 'DTL', '', t.openDTL);
      getParticulars().filter(p => p.nature === 'DTL').forEach(p => addRow('  ' + p.name, 0, p.amt, 'DTL', p.routing||'P&L', p.amt));
      DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), []).filter(l=>l.nature==='DTL').forEach(l=>addRow(`  Lease Netting: ${l.name}`, 0, l.tax, 'DTL', 'P&L', l.tax));
      addRow('Total DTL', t.openDTL, t.closeDTL - t.openDTL, 'DTL', '', t.closeDTL, true);
      tb.innerHTML += `<tr><td colspan="5"></td></tr>`;
      const netLabel = t.net >= 0 ? 'Net DTA (Asset)' : 'Net DTL (Liability)';
      addRow(netLabel, t.openDTA - t.openDTL, 0, '', '', t.net, true);
    }
    function exportSummaryCSV() {
      const t = calcTotals(); if(!t)return;
      const cname = state.activeCompanyName || 'Company';
      const fy = state.activeFY || 'FY';
      const rows = [
        [`Company: ${cname}`, `FY: ${fy}`],
        [],
        ['Particulars', 'Opening', 'Recognised', 'Type', 'Closing'],
        ['Opening DTA', t.openDTA, 0, 'DTA', t.openDTA],
        ['Total DTA', t.openDTA, t.closeDTA - t.openDTA, 'DTA', t.closeDTA],
        ['Opening DTL', t.openDTL, 0, 'DTL', t.openDTL],
        ['Total DTL', t.openDTL, t.closeDTL - t.openDTL, 'DTL', t.closeDTL],
        ['Net DTA/(DTL)', '', '', '', t.net]
      ];
      downloadCSV(`DTA_DTL_Summary_${cname}_${fy}.csv`, rows);
    }

    // ════════════════════════════════════════════════════════
    // JOURNAL ENTRIES
    // ════════════════════════════════════════════════════════
    function generateJE() {
      const cont = $('je-container'); if (!cont) return;
      if (!ctx()) { cont.innerHTML = '<div class="alert alert-warn">⚠️ Set Active Company + FY first.</div>'; return; }
      const t = calcTotals(); if (!t) return;
      const fy = state.activeFY;
      const yr = parseInt((fy || '2024-25').split('-')[0]) + 1;
      const yeDate = `31 March ${yr}`;
      
      const movDTA = t.closeDTA - t.openDTA;
      const movDTL = t.closeDTL - t.openDTL;
      
      let entries = [];
      if (Math.abs(movDTA) > 0.001 || Math.abs(movDTL) > 0.001) {
         let plCharge = (movDTL - t.partDTL_OCI) - (movDTA - t.partDTA_OCI);
         let ociCharge = t.partDTL_OCI - t.partDTA_OCI;
         
         let rows = [];
         if (movDTA > 0) rows.push({ side:'Dr', acc:'Deferred Tax Asset A/c', amt: movDTA });
         else if (movDTA < 0) rows.push({ side:'Cr', acc:'Deferred Tax Asset A/c', amt: -movDTA });
         
         if (movDTL > 0) rows.push({ side:'Cr', acc:'Deferred Tax Liability A/c', amt: movDTL });
         else if (movDTL < 0) rows.push({ side:'Dr', acc:'Deferred Tax Liability A/c', amt: -movDTL });
         
         if (plCharge > 0) rows.push({ side:'Dr', acc:'Income Tax Expense (Deferred) - P&L', amt: plCharge });
         else if (plCharge < 0) rows.push({ side:'Cr', acc:'Income Tax Expense (Deferred) - P&L', amt: -plCharge });
         
         if (ociCharge > 0) rows.push({ side:'Dr', acc:'Deferred Tax - OCI A/c', amt: ociCharge });
         else if (ociCharge < 0) rows.push({ side:'Cr', acc:'Deferred Tax - OCI A/c', amt: -ociCharge });
         
         entries.push({
           narration: `Composite Year End Deferred Tax Entry FY ${fy}`,
           rows: rows.sort((a,b) => a.side === 'Dr' ? -1 : 1)
         });
      }

      if (!t.profitability && t.partDTA_PL + t.partDTA_OCI + getLosses().reduce((s, l) => s + l.dta, 0) > 0) {
        entries.push({ narration: `Note: DTA on Business Loss/Unabsorbed Dep NOT recognised (Para 35 – future profit not probable)`, rows: [] });
      }
      if (!entries.length) { cont.innerHTML = '<div class="alert alert-success">✅ No deferred tax movement in this FY (opening = closing).</div>'; return; }
      let html = `<div class="alert alert-info">Year-End Journal Entries as on <strong>${yeDate}</strong> — Active FY: <strong>${fy}</strong><br><em>Includes automated P&L vs OCI routing based on particulars.</em></div>`;
      entries.forEach((e, i) => {
        html += `<div class="card"><div class="card-head">Entry ${i + 1}: ${e.narration}</div>`;
        if (e.rows.length) {
          html += `<div class="tbl-wrap" style="border:none"><table class="je-table">
        <thead><tr><th>Dr/Cr</th><th>Account Head</th><th style="text-align:right">Amount (₹)</th></tr></thead><tbody>`;
          e.rows.forEach(r => {
            html += `<tr><td><strong>${r.side}</strong></td><td class="${r.side === 'Dr' ? 'dr' : 'cr'}">${r.side === 'Cr' ? '&nbsp;&nbsp;&nbsp;&nbsp;' : ''}${r.acc}</td><td class="amt">${inr(Math.abs(r.amt))}</td></tr>`;
          });
          html += `</tbody></table></div>`;
        }
        html += '</div>';
      });
      cont.innerHTML = html;
    }
    function exportJECSV() {
      if (!ctx()) return;
      const t = calcTotals();
      const cname = state.activeCompanyName || 'Company';
      const fy = state.activeFY || 'FY';
      const movDTA = t.closeDTA - t.openDTA, movDTL = t.closeDTL - t.openDTL;
      let plCharge = (movDTL - t.partDTL_OCI) - (movDTA - t.partDTA_OCI);
      let ociCharge = t.partDTL_OCI - t.partDTA_OCI;
      const rows = [
        [`Company: ${cname}`, `FY: ${fy}`],
        [],
        ['Dr/Cr', 'Account', 'Amount']
      ];
      if (movDTA > 0) rows.push(['Dr', 'Deferred Tax Asset A/c', movDTA]); else if (movDTA < 0) rows.push(['Cr', 'Deferred Tax Asset A/c', -movDTA]);
      if (movDTL > 0) rows.push(['Cr', 'Deferred Tax Liability A/c', movDTL]); else if (movDTL < 0) rows.push(['Dr', 'Deferred Tax Liability A/c', -movDTL]);
      if (plCharge > 0) rows.push(['Dr', 'Income Tax Expense (Deferred) - P&L', plCharge]); else if (plCharge < 0) rows.push(['Cr', 'Income Tax Expense (Deferred) - P&L', -plCharge]);
      if (ociCharge > 0) rows.push(['Dr', 'Deferred Tax - OCI A/c', ociCharge]); else if (ociCharge < 0) rows.push(['Cr', 'Deferred Tax - OCI A/c', -ociCharge]);
      downloadCSV(`Journal_Entries_${cname}_${fy}.csv`, rows);
    }

    // ════════════════════════════════════════════════════════
    // FLOW TABLE
    // ════════════════════════════════════════════════════════
    function renderFlowTable() {
      const tb = $('flow-tbody'); if (!tb) return;
      tb.innerHTML = '';
      if (!ctx()) { tb.innerHTML = '<tr><td colspan="6"><div class="alert alert-warn" style="margin:12px">Set Active Company + FY first.</div></td></tr>'; return; }
      $('flow-title').textContent = `${state.activeCompanyName} – FY ${state.activeFY}`;
      const ob = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'ob'), { dta: 0, dtl: 0 });
      const prof = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'), { canProfit: true });
      const mat = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'mat'), { open:0, add:0, util:0, prob:true });
      const leases = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), []);
      let rows = [];
      if(ob.dta > 0) rows.push({ name: 'Opening Balance DTA', type: 'DTA', open: ob.dta, recog: 0, rev: 0, close: ob.dta });
      if(ob.dtl > 0) rows.push({ name: 'Opening Balance DTL', type: 'DTL', open: ob.dtl, recog: 0, rev: 0, close: ob.dtl });
      // Particulars
      getParticulars().forEach(p => { rows.push({ name: p.name, type: p.nature, open: 0, recog: p.amt, rev: 0, close: p.amt }); });
      // Losses
      getLosses().forEach(l => { const dta = prof.canProfit ? l.dta : 0; rows.push({ name: `${l.type} (${l.ay})`, type: 'DTA', open: 0, recog: dta, rev: prof.canProfit ? 0 : l.dta, close: dta }); });
      // MAT
      if(mat.prob && (mat.open+mat.add-mat.util)>0) { rows.push({ name: 'MAT Credit Entitlement', type: 'DTA', open: 0, recog: mat.open+mat.add-mat.util, rev: 0, close: mat.open+mat.add-mat.util }); }
      // Leases
      leases.forEach(l => { if(l.nature!=='—') rows.push({ name: `Lease Netting: ${l.name}`, type: l.nature, open: 0, recog: l.tax, rev: 0, close: l.tax }); });
      
      if (!rows.length) { tb.innerHTML = `<tr><td colspan="6" style="padding:20px;color:var(--fg2);text-align:center">No entries found.</td></tr>`; return; }
      let totOpen = 0, totRecog = 0, totRev = 0, totClose = 0;
      rows.forEach(r => {
        const cls = r.type === 'DTA' ? 'amt-dta' : 'amt-dtl';
        tb.innerHTML += `<tr>
      <td>${r.name}</td><td><span class="tag tag-${r.type.toLowerCase()}">${r.type}</span></td>
      <td class="${cls}">${inr(r.open)}</td><td class="amt-net-pos">${inr(r.recog)}</td>
      <td class="amt-net-neg">${inr(r.rev)}</td><td class="${cls}">${inr(r.close)}</td></tr>`;
        totOpen += r.open; totRecog += r.recog; totRev += r.rev; totClose += r.close;
      });
      tb.innerHTML += `<tr class="tbl-total"><td colspan="2">TOTAL</td><td>${inr(totOpen)}</td><td>${inr(totRecog)}</td><td>${inr(totRev)}</td><td>${inr(totClose)}</td></tr>`;
    }
    function exportFlowCSV() {
      const ob = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'ob'), { dta: 0, dtl: 0 });
      const prof = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'), { canProfit: true });
      const mat = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'mat'), { open:0, add:0, util:0, prob:true });
      const leases = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), []);
      const cname = state.activeCompanyName || 'Company';
      const fy = state.activeFY || 'FY';
      const rows = [[`Company: ${cname}`, `FY: ${fy}`], [], ['Particular', 'Type', 'Opening', 'Recognised', 'Reversed', 'Closing']];
      if(ob.dta > 0) rows.push(['Opening Balance DTA', 'DTA', ob.dta, 0, 0, ob.dta]);
      if(ob.dtl > 0) rows.push(['Opening Balance DTL', 'DTL', ob.dtl, 0, 0, ob.dtl]);
      getParticulars().forEach(p => rows.push([p.name, p.nature, 0, p.amt, 0, p.amt]));
      getLosses().forEach(l => { const dta = prof.canProfit ? l.dta : 0; rows.push([`${l.type} (${l.ay})`, 'DTA', 0, dta, prof.canProfit ? 0 : l.dta, dta]); });
      if(mat.prob && (mat.open+mat.add-mat.util)>0) rows.push(['MAT Credit', 'DTA', 0, mat.open+mat.add-mat.util, 0, mat.open+mat.add-mat.util]);
      leases.forEach(l => { if(l.nature!=='—') rows.push([`Lease Netting: ${l.name}`, l.nature, 0, l.tax, 0, l.tax]); });
      downloadCSV(`DTA_DTL_Flow_Table_${cname}_${fy}.csv`, rows);
    }

    // ════════════════════════════════════════════════════════
    // MAT CREDIT (Sec 115JAA)
    // ════════════════════════════════════════════════════════
    function loadMat() {
      if (!ctx()) return;
      const d = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'mat'), { open:0, add:0, util:0, prob:true });
      $('mat-open').value = d.open; $('mat-add').value = d.add; $('mat-util').value = d.util;
      setMatProb(d.prob);
      calcMat();
    }
    function calcMat() {
      const open = parseFloat($('mat-open').value) || 0;
      const add = parseFloat($('mat-add').value) || 0;
      const util = parseFloat($('mat-util').value) || 0;
      const close = open + add - util;
      $('mat-close').value = close.toFixed(2);
      
      const isProb = $('mat-prob-yes').classList.contains('active');
      $('mat-dta').value = isProb ? close.toFixed(2) : '0.00';
    }
    function setMatProb(val) {
      $('mat-prob-yes').className = 'toggle-opt' + (val ? ' active' : '');
      $('mat-prob-no').className = 'toggle-opt' + (!val ? ' active' : '');
      calcMat();
    }
    function saveMat() {
      if (!needCtx()) return;
      calcMat();
      const obj = {
        open: parseFloat($('mat-open').value)||0, add: parseFloat($('mat-add').value)||0,
        util: parseFloat($('mat-util').value)||0, prob: $('mat-prob-yes').classList.contains('active')
      };
      DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'mat'), obj);
      showMsg('mat-msg', 'MAT Credit saved!');
    }

    // ════════════════════════════════════════════════════════
    // IND AS 116 LEASES
    // ════════════════════════════════════════════════════════
    function getLeases() {
      if (!ctx()) return [];
      return DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), []);
    }
    function saveLeases(data) { DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'leases'), data); }
    function calcLease() {
      const rou = parseFloat($('ls-rou').value)||0;
      const liab = parseFloat($('ls-liab').value)||0;
      const diff = liab - rou; // positive means Liability > Asset = DTA
      $('ls-diff').value = Math.abs(diff).toFixed(2);
      
      const rate = getTaxRate();
      const tax = Math.abs(diff) * rate / 100;
      const nature = diff > 0 ? 'DTA' : (diff < 0 ? 'DTL' : '—');
      
      $('ls-tax').value = tax.toFixed(2) + (nature !== '—' ? ' ('+nature+')' : '');
      return { diff, tax, nature };
    }
    function addLease() {
      if (!needCtx()) return;
      const name = V('ls-name'); if(!name){alert('Description required'); return;}
      const res = calcLease();
      const data = getLeases();
      data.push({
        id: Date.now(), name, rou: parseFloat($('ls-rou').value)||0, liab: parseFloat($('ls-liab').value)||0,
        diff: res.diff, tax: res.tax, nature: res.nature
      });
      saveLeases(data); clearLease(); renderLeases();
    }
    function updateLease() {
      if (!state.selLeaseId) { alert('Select a lease.'); return; }
      const res = calcLease();
      const data = getLeases();
      const item = data.find(x => x.id === state.selLeaseId);
      if (!item) return;
      item.name = V('ls-name'); item.rou = parseFloat($('ls-rou').value)||0; item.liab = parseFloat($('ls-liab').value)||0;
      item.diff = res.diff; item.tax = res.tax; item.nature = res.nature;
      saveLeases(data); clearLease(); renderLeases();
    }
    function deleteLease() {
      if (!state.selLeaseId) { alert('Select a lease.'); return; }
      if(!confirm('Delete lease?')) return;
      saveLeases(getLeases().filter(x => x.id !== state.selLeaseId));
      state.selLeaseId = null; clearLease(); renderLeases();
    }
    function clearLease() {
      state.selLeaseId = null;
      $('ls-name').value = ''; $('ls-rou').value = '0'; $('ls-liab').value = '0';
      $('ls-diff').value = '0'; $('ls-tax').value = '0';
      document.querySelectorAll('#ls-tbody tr').forEach(r => r.classList.remove('selected'));
    }
    function renderLeases() {
      const tb = $('ls-tbody'); if (!tb) return;
      tb.innerHTML = ''; let totNet = 0;
      getLeases().forEach((l, i) => {
        const tr = document.createElement('tr');
        const isDta = l.nature === 'DTA';
        totNet += (isDta ? l.tax : -l.tax);
        tr.innerHTML = `<td>${i+1}</td><td>${l.name}</td><td>${inr(l.rou)}</td><td>${inr(l.liab)}</td>
        <td>${inr(Math.abs(l.diff))}</td><td><span class="tag ${isDta?'tag-dta':'tag-dtl'}">${l.nature}</span></td>
        <td class="${isDta?'amt-dta':'amt-dtl'}">${inr(l.tax)}</td>`;
        tr.onclick = () => {
          document.querySelectorAll('#ls-tbody tr').forEach(r=>r.classList.remove('selected'));
          tr.classList.add('selected'); state.selLeaseId = l.id;
          $('ls-name').value = l.name; $('ls-rou').value = l.rou; $('ls-liab').value = l.liab; calcLease();
        };
        tb.appendChild(tr);
      });
      const fnature = totNet > 0 ? 'Net DTA' : (totNet < 0 ? 'Net DTL' : 'Nil');
      $('ls-total').innerHTML = `<span class="${totNet>=0?'amt-dta':'amt-dtl'}">${inr(Math.abs(totNet))} (${fnature})</span>`;
    }

    // ════════════════════════════════════════════════════════
    // ETR RECONCILIATION
    // ════════════════════════════════════════════════════════
    function loadETR() {
      if (!ctx()) return;
      const d = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'etr'), { pbt:0, prior:0, exempt:0, diffRate:0, others:0 });
      $('etr-pbt').value = d.pbt; $('etr-prior').value = d.prior; $('etr-exempt').value = d.exempt;
      $('etr-diff-rate').value = d.diffRate; $('etr-others').value = d.others;
      $('etr-stat-rate').value = getTaxRate().toFixed(2);
      calcETR();
    }
    function saveETR() {
      if (!needCtx()) return;
      const obj = {
        pbt: parseFloat($('etr-pbt').value)||0, prior: parseFloat($('etr-prior').value)||0,
        exempt: parseFloat($('etr-exempt').value)||0, diffRate: parseFloat($('etr-diff-rate').value)||0,
        others: parseFloat($('etr-others').value)||0
      };
      DB.set(DB.key(state.activeCompanyId, state.activeFYId, 'etr'), obj);
      showMsg('etr-msg', 'ETR Data saved!');
    }
    function calcETR() {
      const pbt = parseFloat($('etr-pbt').value)||0;
      const rate = getTaxRate();
      const theoTax = pbt * rate / 100;
      
      const tb = $('etr-tbody'); tb.innerHTML = '';
      const addR = (lab, amt) => {
        const perc = pbt ? (amt / pbt * 100).toFixed(2) : '0.00';
        tb.innerHTML += `<tr><td>${lab}</td><td style="text-align:right">${inr(amt)}</td><td style="text-align:right">${perc}%</td></tr>`;
      };

      addR('Accounting Profit Before Tax', pbt);
      addR(`Tax at Statutory Rate (${rate}%)`, theoTax);

      let adjTot = 0;
      // Permanent differences from particulars
      getParticulars().filter(p => p.difftype === 'Permanent').forEach(p => {
        const effect = p.amt; // p.amt is already tax effect
        addR(`  Permanent Diff: ${p.name}`, effect);
        adjTot += effect;
      });

      // Unrecognized DTA on losses
      const prof = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'), { canProfit: true });
      if (!prof.canProfit) {
        const lossTax = getLosses().reduce((s, l) => s + l.dta, 0);
        if (lossTax > 0) {
          addR('  Unrecognised DTA on Losses (Para 35)', lossTax);
          adjTot += lossTax;
        }
      }

      // Manual adjustments
      const prior = parseFloat($('etr-prior').value)||0;
      const exempt = parseFloat($('etr-exempt').value)||0;
      const drate = parseFloat($('etr-diff-rate').value)||0;
      const others = parseFloat($('etr-others').value)||0;

      if(prior) { addR('  Prior Period Adjustments', prior); adjTot += prior; }
      if(exempt) { addR('  Exempt Income / Non-deductible', exempt); adjTot += exempt; }
      if(drate) { addR('  Tax at different rates', drate); adjTot += drate; }
      if(others) { addR('  Other tax adjustments', others); adjTot += others; }

      const actualTax = theoTax + adjTot;
      const etrRate = pbt ? (actualTax / pbt * 100).toFixed(2) : '0.00';

      tb.innerHTML += `<tr class="tbl-total"><td>Total Tax Expense</td><td style="text-align:right">${inr(actualTax)}</td><td style="text-align:right">${etrRate}%</td></tr>`;
    }
    function exportETRCSV() {
      if (!ctx()) return;
      const cname = state.activeCompanyName || 'Company';
      const fy = state.activeFY || 'FY';
      const pbt = parseFloat($('etr-pbt').value)||0;
      const rate = getTaxRate();
      const rows = [
        [`Company: ${cname}`, `FY: ${fy}`],
        [],
        ['Particulars', 'Amount (₹)', 'Percentage (%)']
      ];
      // Simple export of the main structure
      rows.push(['Accounting Profit Before Tax', pbt, '100.00%']);
      rows.push([`Tax at Statutory Rate (${rate}%)`, pbt * rate / 100, `${rate.toFixed(2)}%`]);
      // Permanent differences 
      getParticulars().filter(p => p.difftype === 'Permanent').forEach(p => {
         rows.push([`Permanent Diff: ${p.name}`, p.amt, (p.amt/pbt*100).toFixed(2) + '%']);
      });
      const prof = DB.get(DB.key(state.activeCompanyId, state.activeFYId, 'profitability'), { canProfit: true });
      if (!prof.canProfit) {
        const lossTax = getLosses().reduce((s, l) => s + l.dta, 0);
        if (lossTax > 0) rows.push(['Unrecognised DTA on Losses (Para 35)', lossTax, (lossTax/pbt*100).toFixed(2) + '%']);
      }
      rows.push(['Prior Period Adjustments', parseFloat($('etr-prior').value)||0, ((parseFloat($('etr-prior').value)||0)/pbt*100).toFixed(2) + '%']);
      rows.push(['Exempt Income / Non-deductible', parseFloat($('etr-exempt').value)||0, ((parseFloat($('etr-exempt').value)||0)/pbt*100).toFixed(2) + '%']);
      rows.push(['Tax at different rates', parseFloat($('etr-diff-rate').value)||0, ((parseFloat($('etr-diff-rate').value)||0)/pbt*100).toFixed(2) + '%']);
      rows.push(['Other tax adjustments', parseFloat($('etr-others').value)||0, ((parseFloat($('etr-others').value)||0)/pbt*100).toFixed(2) + '%']);
      
      downloadCSV(`ETR_Reconciliation_${cname}_${fy}.csv`, rows);
    }

    // ════════════════════════════════════════════════════════
    // CSV EXPORT
    // ════════════════════════════════════════════════════════
    function downloadCSV(filename, rows) {
      const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
      const a = document.createElement('a');
      a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
      a.download = filename; a.click();
    }

    // ════════════════════════════════════════════════════════
    // INIT
    // ════════════════════════════════════════════════════════
    document.addEventListener('DOMContentLoaded', () => {
      applyTheme(state.theme);
      // Restore last active context from localStorage
      const last = DB.get('inas12_lastctx', {});
      if (last.cid) { state.activeCompanyId = last.cid; state.activeCompanyName = last.cname || '—'; }
      if (last.fyid) { state.activeFYId = last.fyid; state.activeFY = last.fy || '—'; }
      updateStatusBar();
    });
    // Persist context on changes
    const _origSetActive = setActiveCompany;
    window.setActiveCompany = function (id) { _origSetActive(id); DB.set('inas12_lastctx', { cid: state.activeCompanyId, cname: state.activeCompanyName, fyid: state.activeFYId, fy: state.activeFY }); };
    const _origSetFY = setActiveFY;
    window.setActiveFY = function (c, fy, ye) { _origSetFY(c, fy, ye); DB.set('inas12_lastctx', { cid: state.activeCompanyId, cname: state.activeCompanyName, fyid: fy, fy }); };
  