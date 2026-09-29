/**
 * EcoStream Live Multi-Agent Workflow Monitor
 * Pure JavaScript Real-Time Polling & Reactive UI Controller
 */

// Global State
let activeRunId = null;
let pollingInterval = 3; // default seconds
let isPollingActive = true;
let pollTimer = null;
let currentRunData = null;
let runsCache = [];

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initPollSpeedSelector();
    initPathInputListener();
    loadRunsList();
    startPollingLoop();
});

// ---------------------------------------------------------------------------
// 1. Polling & Connection Management
// ---------------------------------------------------------------------------

function initPollSpeedSelector() {
    const select = document.getElementById('pollIntervalSelect');
    if (select) {
        select.addEventListener('change', (e) => {
            pollingInterval = parseInt(e.target.value, 10) || 3;
            document.getElementById('pollStatusMsg').innerText = `Đang tự động cập nhật mỗi ${pollingInterval} giây...`;
            restartPollingLoop();
        });
    }
}

function initPathInputListener() {
    const input = document.getElementById('runPathInput');
    if (input) {
        input.addEventListener('change', (e) => {
            let val = e.target.value.trim();
            if (val) {
                // Strip "runs/" prefix if entered
                val = val.replace(/^runs[\\\/]/, '').replace(/[\\\/]$/, '');
                activeRunId = val;
                updateActiveRunBadge(activeRunId);
                fetchRunData(true);
            }
        });
    }
}

function togglePolling() {
    isPollingActive = !isPollingActive;
    const btn = document.getElementById('btnTogglePolling');
    const icon = document.getElementById('pollIcon');
    const text = document.getElementById('pollText');
    const dot = document.getElementById('pollingPulseDot');

    if (isPollingActive) {
        btn.className = "px-3 py-1.5 rounded-xl text-xs font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 transition flex items-center gap-1.5 shadow-2xs";
        icon.innerText = "⏸";
        text.innerText = "Tự Động Quét (Bật)";
        dot.className = "w-2 h-2 rounded-full bg-emerald-500 pulse-active";
        document.getElementById('pollStatusMsg').innerText = `Đang tự động cập nhật mỗi ${pollingInterval} giây...`;
        startPollingLoop();
    } else {
        btn.className = "px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 transition flex items-center gap-1.5 shadow-2xs";
        icon.innerText = "▶";
        text.innerText = "Tự Động Quét (Tắt)";
        dot.className = "w-2 h-2 rounded-full bg-slate-400";
        document.getElementById('pollStatusMsg').innerText = `Tự động quét đang tạm dừng.`;
        clearInterval(pollTimer);
    }
}

function startPollingLoop() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
        if (isPollingActive) {
            fetchRunData(false);
        }
    }, pollingInterval * 1000);
}

function restartPollingLoop() {
    if (isPollingActive) {
        startPollingLoop();
    }
}

function setConnectionStatus(online, msg = 'Đang kết nối') {
    const chip = document.getElementById('connStatus');
    const text = document.getElementById('connStatusText');
    if (online) {
        chip.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200";
        text.innerText = msg;
    } else {
        chip.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200";
        text.innerText = "Mất kết nối";
    }
}

// ---------------------------------------------------------------------------
// 2. Runs Discovery & Selection
// ---------------------------------------------------------------------------

async function loadRunsList() {
    try {
        const res = await fetch('/api/orchestrator/runs');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        runsCache = data.runs || [];

        const select = document.getElementById('runSelect');
        const datalist = document.getElementById('runsDatalist');
        select.innerHTML = '';
        datalist.innerHTML = '';

        if (runsCache.length === 0) {
            select.innerHTML = '<option value="">-- Không tìm thấy phiên chạy nào trong runs/ --</option>';
            return;
        }

        runsCache.forEach((r, idx) => {
            const opt = document.createElement('option');
            opt.value = r.run_id;
            const phase = r.phase || (r.state ? r.state.phase : 'UNKNOWN');
            const pct = r.progress_pct !== undefined ? `${Math.round(r.progress_pct)}%` : '';
            opt.innerText = `${r.run_id} [${phase} ${pct}]`;
            select.appendChild(opt);

            const dlOpt = document.createElement('option');
            dlOpt.value = r.run_id;
            datalist.appendChild(dlOpt);
        });

        // Default to first run if not set
        if (!activeRunId && runsCache.length > 0) {
            activeRunId = runsCache[0].run_id;
            select.value = activeRunId;
            document.getElementById('runPathInput').value = activeRunId;
            updateActiveRunBadge(activeRunId);
            fetchRunData(true);
        }
    } catch (err) {
        console.error('Error loading runs list:', err);
        setConnectionStatus(false, 'Lỗi kết nối máy chủ');
    }
}

function onRunSelectChange() {
    const select = document.getElementById('runSelect');
    if (select.value) {
        activeRunId = select.value;
        document.getElementById('runPathInput').value = activeRunId;
        updateActiveRunBadge(activeRunId);
        fetchRunData(true);
    }
}

function updateActiveRunBadge(runId) {
    const badge = document.getElementById('activeRunBadge');
    if (badge) {
        badge.innerText = runId || 'Chưa chọn';
    }
}

// ---------------------------------------------------------------------------
// 3. Fetch Single Run Data & Render Reactive UI
// ---------------------------------------------------------------------------

async function fetchRunData(isManual = false) {
    if (!activeRunId) return;

    try {
        const res = await fetch(`/api/orchestrator/runs/${encodeURIComponent(activeRunId)}`);
        if (!res.ok) {
            if (res.status === 404) {
                document.getElementById('pollStatusMsg').innerText = `Run ${activeRunId} chưa tồn tại hoặc đang khởi tạo...`;
            }
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        currentRunData = data;
        setConnectionStatus(true, 'Trực tuyến • Đã đồng bộ');

        // Update timestamp
        const now = new Date();
        document.getElementById('lastUpdatedTime').innerText = now.toLocaleTimeString('vi-VN');

        // Render sections
        renderLifecycleStepper(data);
        renderSubagentsGrid(data);
        renderDeliverables(data);
        renderIntermediateTabs(data);

    } catch (err) {
        console.warn('Fetch error:', err);
        if (isManual) {
            setConnectionStatus(false, 'Lỗi nạp dữ liệu');
        }
    }
}

// ---------------------------------------------------------------------------
// 4. Stepper & Lifecycle Renderer
// ---------------------------------------------------------------------------

function renderLifecycleStepper(data) {
    const state = data.state || {};
    const phase = state.phase || 'INITIALIZED';
    const pct = Math.round(state.progress_pct || 0);

    // Header metadata
    document.getElementById('lifecyclePhaseChip').innerText = phase;
    document.getElementById('progressPctText').innerText = `${pct}%`;
    document.getElementById('lifecycleProgressBar').style.width = `${pct}%`;

    if (data.index) {
        document.getElementById('runCompanyDisplay').innerText = data.index.company_name || 'EcoGarment Vietnam JSC';
        document.getElementById('runFacilityDisplay').innerText = data.index.facility_name || 'Nhà máy Hà Nam';
        document.getElementById('runYearDisplay').innerText = data.index.reporting_year || '2026';
    }

    // Set step badge statuses
    const PHASES_ORDER = ['INITIALIZED', 'INGESTED', 'INDEXED', 'SUBAGENTS_EXTRACTING', 'CALCULATING', 'SYNTHESIZING', 'COMPLETED'];
    const currentIdx = PHASES_ORDER.indexOf(phase);

    function updateCard(cardId, badgeId, detailId, targetIdx, activeLabel, doneLabel) {
        const card = document.getElementById(cardId);
        const badge = document.getElementById(badgeId);
        const detail = document.getElementById(detailId);

        if (currentIdx > targetIdx || phase === 'COMPLETED') {
            card.className = "p-3.5 rounded-xl border border-emerald-300 bg-emerald-50/70 flex flex-col justify-between transition shadow-2xs";
            badge.className = "w-2.5 h-2.5 rounded-full bg-emerald-600";
            detail.className = "text-[10px] font-mono text-emerald-800 font-bold truncate";
            detail.innerText = doneLabel;
        } else if (currentIdx === targetIdx) {
            card.className = "p-3.5 rounded-xl border border-amber-400 bg-amber-50/70 flex flex-col justify-between transition shadow-xs";
            badge.className = "w-2.5 h-2.5 rounded-full bg-amber-500 pulse-active";
            detail.className = "text-[10px] font-mono text-amber-800 font-bold truncate";
            detail.innerText = activeLabel;
        } else {
            card.className = "p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between transition opacity-60";
            badge.className = "w-2.5 h-2.5 rounded-full bg-slate-300";
            detail.className = "text-[10px] font-mono text-slate-500 truncate";
            detail.innerText = "Chờ bắt đầu";
        }
    }

    updateCard('stepCard-ingestion', 'stepBadge-ingestion', 'stepDetail-ingestion', 1, 'Đang phân giải...', '✓ Hoàn tất Ingestion');
    updateCard('stepCard-discovery', 'stepBadge-discovery', 'stepDetail-discovery', 2, 'Đang catalog...', '✓ Hoàn tất Schema Discovery');
    updateCard('stepCard-subagents', 'stepBadge-subagents', 'stepDetail-subagents', 3, 'Đang chạy 4 tác tử...', '✓ Hoàn tất trích xuất');
    updateCard('stepCard-math', 'stepBadge-math', 'stepDetail-math', 4, 'Đang tính toán...', '✓ Hoàn tất Math & 95% CI');
    updateCard('stepCard-synthesis', 'stepBadge-synthesis', 'stepDetail-synthesis', 5, 'Đang xuất bản...', '✓ Hoàn tất Báo cáo');
}

function renderSubagentsGrid(data) {
    const intermediate = data.intermediate || {};
    const scope1 = intermediate.scope1 || [];
    const scope2 = intermediate.scope2 || [];
    const scope3 = intermediate.scope3 || [];
    const mitigation = intermediate.mitigation || [];

    function setAgentBadge(elemId, records, isCompleted) {
        const badge = document.getElementById(elemId);
        if (records.length > 0 || isCompleted) {
            badge.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300";
            badge.innerText = `Hoàn tất (${records.length} mục)`;
        } else {
            badge.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-600";
            badge.innerText = "Pending";
        }
    }

    const isPhaseDone = (data.state && data.state.phase === 'COMPLETED');
    setAgentBadge('agentStatus-scope1', scope1, isPhaseDone);
    setAgentBadge('agentStatus-scope2', scope2, isPhaseDone);
    setAgentBadge('agentStatus-scope3', scope3, isPhaseDone);
    setAgentBadge('agentStatus-mitigation', mitigation, isPhaseDone);
}

// ---------------------------------------------------------------------------
// 5. Deliverables Panel Renderer
// ---------------------------------------------------------------------------

function renderDeliverables(data) {
    const deliverables = data.deliverables || [];
    const countBadge = document.getElementById('deliverablesCountBadge');
    if (countBadge) {
        countBadge.innerText = `${deliverables.length} file sẵn sàng`;
    }

    function setupDeliverable(statusId, linkId, btnPreviewId, targetName) {
        const found = deliverables.find(d => d.filename === targetName);
        const statusElem = document.getElementById(statusId);
        const linkElem = document.getElementById(linkId);
        const btnPreview = btnPreviewId ? document.getElementById(btnPreviewId) : null;

        if (found) {
            statusElem.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300";
            statusElem.innerText = `Sẵn sàng (${Math.round(found.size_bytes / 1024)} KB)`;

            if (linkElem) {
                linkElem.href = found.url;
                linkElem.className = linkElem.className.replace('opacity-40 pointer-events-none', '').trim();
            }
            if (btnPreview) {
                btnPreview.disabled = false;
            }
        } else {
            statusElem.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-600";
            statusElem.innerText = "Đang chờ";
            if (linkElem && !linkElem.className.includes('opacity-40')) {
                linkElem.className += " opacity-40 pointer-events-none";
            }
            if (btnPreview) {
                btnPreview.disabled = true;
            }
        }
    }

    setupDeliverable('delivStatus-md', 'delivLink-md', 'delivBtn-md-preview', 'Bao_cao_kiem_ke_va_giam_nhe_KNK.md');
    setupDeliverable('delivStatus-html', 'delivLink-html', null, 'Bao_cao_kiem_ke_va_giam_nhe_KNK.html');
    setupDeliverable('delivStatus-docx', 'delivLink-docx', null, 'Bao_cao_Mau02_ND06.docx');
    setupDeliverable('delivStatus-pdf', 'delivLink-pdf', null, 'Bao_cao_kiem_ke_va_giam_nhe_KNK.pdf');
}

// ---------------------------------------------------------------------------
// 6. Intermediate Tabs & Data Table Renderers
// ---------------------------------------------------------------------------

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.className = "tab-btn px-3 py-2 rounded-xl text-xs font-bold transition text-slate-600 hover:bg-slate-100 flex items-center gap-1.5";
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.add('hidden');
    });

    const activeBtn = document.getElementById(`btnTab-${tabId}`);
    if (activeBtn) {
        activeBtn.className = "tab-btn px-3 py-2 rounded-xl text-xs font-bold transition bg-emerald-800 text-white shadow-xs flex items-center gap-1.5";
    }
    const activePanel = document.getElementById(`tabContent-${tabId}`);
    if (activePanel) {
        activePanel.classList.remove('hidden');
    }

    if (tabId === 'tabRawJson') {
        loadRawFileContent();
    }
}

function renderIntermediateTabs(data) {
    const intermediate = data.intermediate || {};
    const state = data.state || {};
    const index = data.index || {};

    // 1. State & Index tab
    document.getElementById('statePhaseBadge').innerText = state.phase || '--';
    document.getElementById('stateRunId').innerText = state.run_id || '--';
    document.getElementById('stateStartTime').innerText = state.start_time || '--';
    document.getElementById('stateEndTime').innerText = state.end_time || '--';
    document.getElementById('stateProgressPct').innerText = `${Math.round(state.progress_pct || 0)}%`;

    const routingList = document.getElementById('sheetRoutingList');
    if (index.tasks && index.tasks.length > 0) {
        document.getElementById('sheetCountBadge').innerText = `${index.tasks.length} mục`;
        routingList.innerHTML = index.tasks.map(t => `
            <div class="p-2 rounded-lg bg-white border border-slate-200 flex items-center justify-between">
                <div>
                    <span class="font-bold text-slate-800">${t.sheet_or_section}</span>
                    <span class="text-slate-400 text-[10px] ml-1">(${t.estimated_records || 0} dòng)</span>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">${t.assigned_subagent}</span>
            </div>
        `).join('');
    }

    // 2. Scope 1 Table
    const scope1 = intermediate.scope1 || [];
    document.getElementById('tabCount-scope1').innerText = scope1.length;
    const s1Body = document.getElementById('tableScope1Body');
    if (scope1.length > 0) {
        s1Body.innerHTML = scope1.map(r => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3 font-bold text-slate-800">${r.fuel_type || r.activity_type || '--'}</td>
                <td class="p-3 text-slate-600 font-sans">${r.equipment_category || r.category || 'Lò hơi / Máy phát'}</td>
                <td class="p-3 text-slate-900 font-bold">${Number(r.original_quantity || r.quantity || 0).toLocaleString()}</td>
                <td class="p-3 text-slate-500">${r.original_unit || r.unit || '--'}</td>
                <td class="p-3 text-emerald-700 font-bold">${Number(r.standard_quantity || r.quantity || 0).toLocaleString()} ${r.standard_unit || 'kg'}</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">${r.confidence_score ? Math.round(r.confidence_score * 100) + '%' : '95%'}</span></td>
            </tr>
        `).join('');
    }

    // 3. Scope 2 Table
    const scope2 = intermediate.scope2 || [];
    document.getElementById('tabCount-scope2').innerText = scope2.length;
    const s2Body = document.getElementById('tableScope2Body');
    if (scope2.length > 0) {
        s2Body.innerHTML = scope2.map(r => {
            const isInterpolated = r.is_interpolated || r.interpolated || false;
            return `
            <tr class="hover:bg-slate-50 transition ${isInterpolated ? 'bg-amber-50/40' : ''}">
                <td class="p-3 font-bold text-slate-800">${r.billing_month || r.period || '--'}</td>
                <td class="p-3 font-bold ${isInterpolated ? 'text-amber-800' : 'text-slate-900'}">${Number(r.active_energy_kwh || r.kwh || 0).toLocaleString()}</td>
                <td class="p-3 text-slate-500 text-[11px]">${Number(r.normal_kwh || 0).toLocaleString()} / ${Number(r.peak_kwh || 0).toLocaleString()} / ${Number(r.off_peak_kwh || 0).toLocaleString()}</td>
                <td class="p-3 text-slate-600">${r.customer_code || r.meter_id || 'EVN-HN-01'}</td>
                <td class="p-3">${isInterpolated ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">⚠️ Nội suy (Interpolated)</span>' : '<span class="text-slate-500 font-sans">Hóa đơn EVN gốc</span>'}</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${isInterpolated ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}">${r.confidence_score ? Math.round(r.confidence_score * 100) + '%' : '90%'}</span></td>
            </tr>
        `}).join('');
    }

    // 4. Scope 3 Table
    const scope3 = intermediate.scope3 || [];
    document.getElementById('tabCount-scope3').innerText = scope3.length;
    const s3Body = document.getElementById('tableScope3Body');
    if (scope3.length > 0) {
        s3Body.innerHTML = scope3.map(r => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3 font-bold text-slate-800">${r.category || r.material_type || '--'}</td>
                <td class="p-3 text-slate-600 font-sans">${r.transport_mode || 'Vận tải đường bộ'}</td>
                <td class="p-3 font-bold text-slate-900">${r.tonne_km ? Number(r.tonne_km).toLocaleString() + ' t.km' : Number(r.spend_amount_vnd || 0).toLocaleString() + ' VND'}</td>
                <td class="p-3 text-slate-600 font-sans">${r.emission_factor_proxy || 'EXIOBASE Proxy'}</td>
                <td class="p-3 text-amber-700 font-bold font-mono">±${r.uncertainty_pct || 40}%</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 font-sans">${r.is_spend_based ? 'Ước tính chi tiêu' : 'Dữ liệu vận tải'}</span></td>
            </tr>
        `).join('');
    }

    // 5. Mitigation Table
    const mitigation = intermediate.mitigation || [];
    document.getElementById('tabCount-mitigation').innerText = mitigation.length;
    const mitBody = document.getElementById('tableMitigationBody');
    if (mitigation.length > 0) {
        mitBody.innerHTML = mitigation.map(r => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3 font-bold text-slate-800">${r.measure_id || '--'}</td>
                <td class="p-3 font-sans text-slate-700 font-medium">${r.name || r.measure_name || '--'}</td>
                <td class="p-3 text-slate-600 font-bold">${Number(r.baseline_emissions_tco2e || r.pt_cs || 0).toLocaleString()} tCO₂e</td>
                <td class="p-3 text-slate-900 font-bold">${Number(r.actual_emissions_tco2e || r.pt || 0).toLocaleString()} tCO₂e</td>
                <td class="p-3 text-emerald-700 font-bold text-sm">-${Number(r.reduction_tco2e || r.gpt || 0).toLocaleString()} tCO₂e</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">${r.status || 'Đang vận hành'}</span></td>
            </tr>
        `).join('');
    }

    // 6. Logs Table
    const queries = intermediate.queries || [];
    const assumptions = intermediate.assumptions || [];
    document.getElementById('tabCount-logs').innerText = queries.length + assumptions.length;
    document.getElementById('queryLogCount').innerText = `${queries.length} mục`;
    document.getElementById('assumptionLogCount').innerText = `${assumptions.length} mục`;

    const qBody = document.getElementById('tableQueryLogBody');
    if (queries.length > 0) {
        qBody.innerHTML = queries.map(q => `
            <tr class="hover:bg-amber-100/40 transition">
                <td class="p-3 font-mono font-bold text-amber-900">${q.query_id || '--'}</td>
                <td class="p-3 text-slate-700 font-medium">${q.domain_agent || q.scope || '--'}</td>
                <td class="p-3 text-slate-800">${q.description || q.issue || '--'}</td>
                <td class="p-3 text-slate-600">${q.provisional_action || '--'}</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900">${q.status || 'Chờ xác nhận'}</span></td>
            </tr>
        `).join('');
    }

    const aBody = document.getElementById('tableAssumptionLogBody');
    if (assumptions.length > 0) {
        aBody.innerHTML = assumptions.map(a => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3 font-mono font-bold text-slate-800">${a.assumption_id || '--'}</td>
                <td class="p-3 text-slate-700 font-medium">${a.scope || a.domain || '--'}</td>
                <td class="p-3 text-slate-800">${a.rule_applied || a.formula || '--'}</td>
                <td class="p-3 font-mono font-bold text-rose-700">-${(a.confidence_penalty * 100).toFixed(0)}%</td>
                <td class="p-3 font-mono font-bold text-amber-700">+${a.uncertainty_markup_pct || 15}%</td>
            </tr>
        `).join('');
    }
}

// ---------------------------------------------------------------------------
// 7. Raw JSON Viewer & Modal Handlers
// ---------------------------------------------------------------------------

async function loadRawFileContent() {
    if (!activeRunId) return;
    const fileSelect = document.getElementById('rawFileSelect');
    const filename = fileSelect ? fileSelect.value : 'state.json';
    const viewer = document.getElementById('rawJsonViewer');

    try {
        viewer.innerText = `// Đang nạp ${filename}...`;
        const res = await fetch(`/api/orchestrator/runs/${encodeURIComponent(activeRunId)}/intermediate/${encodeURIComponent(filename)}`);
        if (!res.ok) {
            viewer.innerText = `// Tệp ${filename} chưa tồn tại trên blackboard workspace.`;
            return;
        }
        const data = await res.json();
        viewer.innerText = JSON.stringify(data, null, 2);
    } catch (err) {
        viewer.innerText = `// Lỗi khi tải tệp: ${err.message}`;
    }
}

function copyRawJson() {
    const viewer = document.getElementById('rawJsonViewer');
    if (viewer && viewer.innerText) {
        navigator.clipboard.writeText(viewer.innerText);
        alert('Đã sao chép nội dung JSON vào clipboard!');
    }
}

function downloadJsonArtifact(filename) {
    if (!activeRunId) return;
    window.open(`/api/orchestrator/runs/${encodeURIComponent(activeRunId)}/intermediate/${encodeURIComponent(filename)}`, '_blank');
}

async function previewMarkdownReport() {
    if (!activeRunId) return;
    const modal = document.getElementById('mdPreviewModal');
    const content = document.getElementById('mdModalContent');
    const link = document.getElementById('mdModalDownloadLink');

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    content.innerText = "Đang nạp nội dung báo cáo...";
    link.href = `/api/orchestrator/runs/${encodeURIComponent(activeRunId)}/deliverables/Bao_cao_kiem_ke_va_giam_nhe_KNK.md`;

    try {
        const res = await fetch(`/api/orchestrator/runs/${encodeURIComponent(activeRunId)}/deliverables/Bao_cao_kiem_ke_va_giam_nhe_KNK.md`);
        if (!res.ok) throw new Error("Chưa tìm thấy báo cáo markdown");
        const text = await res.text();
        content.innerText = text;
    } catch (err) {
        content.innerText = "Chưa thể xem trước báo cáo. Tệp có thể đang được tạo hoặc chưa hoàn tất.";
    }
}

function closeMarkdownModal() {
    const modal = document.getElementById('mdPreviewModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}
