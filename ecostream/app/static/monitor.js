/**
 * EcoStream Workflow Monitor
 * Real-Time Polling & Reactive UI Controller
 */

let activeRunId = null;
let pollingInterval = 3;
let isPollingActive = true;
let pollTimer = null;
let currentRunData = null;
let runsCache = [];

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
            document.getElementById('pollStatusMsg').innerText = `Tự động cập nhật mỗi ${pollingInterval} giây`;
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
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold text-[#003c33] bg-[#edf5e9] hover:bg-[#dff4cc] border border-[#cce5c0] transition inline-flex items-center gap-1.5";
        icon.innerText = "||";
        text.innerText = "Tự động (Bật)";
        dot.className = "w-2 h-2 rounded-full bg-[#003c33]";
        document.getElementById('pollStatusMsg').innerText = `Tự động cập nhật mỗi ${pollingInterval} giây`;
        startPollingLoop();
    } else {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold text-[#2c4a3c] bg-[#f5f9f4] hover:bg-[#edf5e9] border border-[#cce5c0] transition inline-flex items-center gap-1.5";
        icon.innerText = ">";
        text.innerText = "Tự động (Tắt)";
        dot.className = "w-2 h-2 rounded-full bg-[#6a8978]";
        document.getElementById('pollStatusMsg').innerText = "Đã tạm dừng tự động quét";
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
    const dot = chip ? chip.querySelector('span') : null;
    if (online) {
        chip.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-[#edf5e9] text-[#003c33] border border-[#cce5c0]";
        if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-[#003c33]";
        text.innerText = msg;
    } else {
        chip.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-red-50 text-red-700 border border-red-200";
        if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-red-600";
        text.innerText = "Mất kết nối";
    }
}

// ---------------------------------------------------------------------------
// 2. Runs Discovery & Selection
// ---------------------------------------------------------------------------

async function loadRunsList() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const orgFilter = urlParams.get('org_id');
        const endpoint = orgFilter ? `/api/orchestrator/runs?org_id=${encodeURIComponent(orgFilter)}` : '/api/orchestrator/runs';
        const res = await fetch(endpoint);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        runsCache = data.runs || [];

        const select = document.getElementById('runSelect');
        const datalist = document.getElementById('runsDatalist');
        select.innerHTML = '';
        datalist.innerHTML = '';

        if (runsCache.length === 0) {
            select.innerHTML = '<option value="">-- Không tìm thấy phiên nào trong runs/ --</option>';
            return;
        }

        runsCache.forEach((r) => {
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

        if (!activeRunId && runsCache.length > 0) {
            activeRunId = runsCache[0].run_id;
            select.value = activeRunId;
            document.getElementById('runPathInput').value = activeRunId;
            updateActiveRunBadge(activeRunId);
            fetchRunData(true);
        }
    } catch (err) {
        console.error('Error loading runs list:', err);
        setConnectionStatus(false, 'Lỗi kết nối');
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
                document.getElementById('pollStatusMsg').innerText = `Phiên ${activeRunId} chưa tồn tại`;
            }
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        currentRunData = data;
        setConnectionStatus(true, 'Đã đồng bộ');

        const now = new Date();
        document.getElementById('lastUpdatedTime').innerText = now.toLocaleTimeString('vi-VN');

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

    document.getElementById('lifecyclePhaseChip').innerText = phase;
    document.getElementById('progressPctText').innerText = `${pct}%`;
    document.getElementById('lifecycleProgressBar').style.width = `${pct}%`;

    if (data.index) {
        document.getElementById('runCompanyDisplay').innerText = data.index.company_name || '--';
        document.getElementById('runFacilityDisplay').innerText = data.index.facility_name || '--';
        document.getElementById('runYearDisplay').innerText = data.index.reporting_year || '2026';
    } else {
        document.getElementById('runCompanyDisplay').innerText = data.run_id || '--';
        document.getElementById('runFacilityDisplay').innerText = 'Phiên khảo sát';
    }

    const PHASES_ORDER = ['INITIALIZED', 'INGESTED', 'INDEXED', 'SUBAGENTS_EXTRACTING', 'CALCULATING', 'SYNTHESIZING', 'COMPLETED'];
    const currentIdx = PHASES_ORDER.indexOf(phase);

    function updateCard(cardId, badgeId, detailId, targetIdx, activeLabel, doneLabel) {
        const card = document.getElementById(cardId);
        const badge = document.getElementById(badgeId);
        const detail = document.getElementById(detailId);
        if (!card || !badge || !detail) return;

        if (currentIdx > targetIdx || phase === 'COMPLETED') {
            card.className = "p-3 rounded-xl border border-[#cce5c0] bg-[#edf5e9]/70 flex flex-col justify-between transition";
            badge.className = "w-2 h-2 rounded-full bg-[#003c33]";
            detail.className = "text-[10px] font-mono text-[#003c33] font-semibold truncate";
            detail.innerText = doneLabel;
        } else if (currentIdx === targetIdx) {
            card.className = "p-3 rounded-xl border border-amber-300 bg-amber-50 flex flex-col justify-between transition";
            badge.className = "w-2 h-2 rounded-full bg-amber-500";
            detail.className = "text-[10px] font-mono text-amber-800 font-semibold truncate";
            detail.innerText = activeLabel;
        } else {
            card.className = "p-3 rounded-xl border border-[#e2f0db] bg-[#f5f9f4]/60 flex flex-col justify-between transition opacity-65";
            badge.className = "w-2 h-2 rounded-full bg-[#cce5c0]";
            detail.className = "text-[10px] font-mono text-[#6a8978] truncate";
            detail.innerText = "Chờ";
        }
    }

    updateCard('stepCard-ingestion', 'stepBadge-ingestion', 'stepDetail-ingestion', 1, 'Đang đọc...', 'Hoàn tất');
    updateCard('stepCard-discovery', 'stepBadge-discovery', 'stepDetail-discovery', 2, 'Đang phân loại...', 'Hoàn tất');
    updateCard('stepCard-subagents', 'stepBadge-subagents', 'stepDetail-subagents', 3, 'Đang trích xuất...', 'Hoàn tất');
    updateCard('stepCard-math', 'stepBadge-math', 'stepDetail-math', 4, 'Đang tính...', 'Hoàn tất');
    updateCard('stepCard-synthesis', 'stepBadge-synthesis', 'stepDetail-synthesis', 5, 'Đang xuất...', 'Hoàn tất');
}

function renderSubagentsGrid(data) {
    const intermediate = data.intermediate || {};
    const scope1 = intermediate.scope1 || [];
    const scope2 = intermediate.scope2 || [];
    const scope3 = intermediate.scope3 || [];
    const mitigation = intermediate.mitigation || [];

    function setAgentBadge(elemId, records, isCompleted) {
        const badge = document.getElementById(elemId);
        if (!badge) return;
        if (records.length > 0 || isCompleted) {
            badge.className = "px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf5e9] text-[#003c33] border border-[#cce5c0]";
            badge.innerText = `${records.length} mục`;
        } else {
            badge.className = "px-2 py-0.5 rounded text-[10px] font-semibold bg-[#f5f9f4] text-[#6a8978]";
            badge.innerText = "Chờ";
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
        countBadge.innerText = `${deliverables.length} tệp sẵn sàng`;
    }

    function setupDeliverable(statusId, linkId, btnPreviewId, targetName) {
        const found = deliverables.find(d => d.filename === targetName);
        const statusElem = document.getElementById(statusId);
        const linkElem = document.getElementById(linkId);
        const btnPreview = btnPreviewId ? document.getElementById(btnPreviewId) : null;
        if (!statusElem) return;

        if (found) {
            statusElem.className = "px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf5e9] text-[#003c33] border border-[#cce5c0]";
            statusElem.innerText = `${Math.round(found.size_bytes / 1024)} KB`;

            if (linkElem) {
                linkElem.href = found.url;
                linkElem.className = linkElem.className.replace('opacity-40 pointer-events-none', '').trim();
            }
            if (btnPreview) {
                btnPreview.disabled = false;
            }
        } else {
            statusElem.className = "px-2 py-0.5 rounded text-[10px] font-semibold bg-white text-[#6a8978] border border-[#e2f0db]";
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
        btn.className = "tab-btn px-3 py-1.5 rounded-lg text-xs font-semibold transition text-[#2c4a3c] hover:bg-[#edf5e9] inline-flex items-center gap-1.5";
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.add('hidden');
    });

    const activeBtn = document.getElementById(`btnTab-${tabId}`);
    if (activeBtn) {
        activeBtn.className = "tab-btn px-3 py-1.5 rounded-lg text-xs font-semibold transition bg-[#003c33] text-white inline-flex items-center gap-1.5";
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

    document.getElementById('statePhaseBadge').innerText = state.phase || '--';
    document.getElementById('stateRunId').innerText = state.run_id || '--';
    document.getElementById('stateStartTime').innerText = state.start_time || '--';
    document.getElementById('stateEndTime').innerText = state.end_time || '--';
    document.getElementById('stateProgressPct').innerText = `${Math.round(state.progress_pct || 0)}%`;

    const routingList = document.getElementById('sheetRoutingList');
    const tasks = index.tasks || index.routing_tasks || [];
    if (tasks.length > 0) {
        document.getElementById('sheetCountBadge').innerText = `${tasks.length} mục`;
        routingList.innerHTML = tasks.map(t => {
            const sheetLabel = t.sheet_name ? `Sheet: ${t.sheet_name}` : (t.source_file || t.description || 'Mục dữ liệu');
            const agentLabel = t.target_agent || t.assigned_subagent || '--';
            const desc = t.description ? `<div class="text-[10px] text-[#6a8978]">${t.description}</div>` : '';
            return `
            <div class="p-2 rounded-lg bg-white border border-[#e2f0db] flex items-center justify-between">
                <div>
                    <span class="font-semibold text-[#091710] text-xs">${sheetLabel}</span>
                    ${desc}
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf5e9] text-[#003c33] border border-[#cce5c0] whitespace-nowrap ml-2">${agentLabel}</span>
            </div>
            `;
        }).join('');
    } else {
        document.getElementById('sheetCountBadge').innerText = '0 mục';
        routingList.innerHTML = '<div class="text-[#6a8978]">Chưa có thông tin định tuyến</div>';
    }

    const scope1 = intermediate.scope1 || [];
    const tc1 = document.getElementById('tabCount-scope1');
    if (tc1) tc1.innerText = scope1.length;
    const s1Body = document.getElementById('tableScope1Body');
    if (s1Body) {
        if (scope1.length > 0) {
            s1Body.innerHTML = scope1.map(r => {
                const conf = r.quality?.composite_score ? Math.round(r.quality.composite_score * 100) + '%' : (r.confidence_score ? Math.round(r.confidence_score * 100) + '%' : '95%');
                return `
                <tr class="hover:bg-[#f5f9f4] transition">
                    <td class="p-3 font-semibold text-[#091710]">${r.description || r.fuel_type || r.activity_type || '--'}</td>
                    <td class="p-3 text-[#2c4a3c] font-sans">${r.category || r.equipment_category || 'Cố định / di động'}</td>
                    <td class="p-3 text-[#091710] font-semibold font-mono">${Number(r.quantity || r.original_quantity || 0).toLocaleString()}</td>
                    <td class="p-3 text-[#6a8978] font-mono">${r.unit || r.original_unit || '--'}</td>
                    <td class="p-3 text-[#003c33] font-semibold font-mono">${Number(r.quantity || r.standard_quantity || 0).toLocaleString()} ${r.unit || r.standard_unit || 'kg'}</td>
                    <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf5e9] text-[#003c33]">${conf}</span></td>
                </tr>
                `;
            }).join('');
        } else {
            s1Body.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-[#6a8978] font-sans">Chưa có dữ liệu Scope 1</td></tr>';
        }
    }

    const scope2 = intermediate.scope2 || [];
    const tc2 = document.getElementById('tabCount-scope2');
    if (tc2) tc2.innerText = scope2.length;
    const s2Body = document.getElementById('tableScope2Body');
    if (s2Body) {
        if (scope2.length > 0) {
            s2Body.innerHTML = scope2.map(r => {
                const isInterpolated = r.is_interpolated || r.interpolated || (r.measurement_type && r.measurement_type.includes('Estimated')) || (r.evidence?.extraction_method === 'INTERPOLATED');
                const conf = r.quality?.composite_score ? Math.round(r.quality.composite_score * 100) + '%' : (r.confidence_score ? Math.round(r.confidence_score * 100) + '%' : '90%');
                const periodOrMonth = r.date || r.billing_month || r.period || r.description || '--';
                const kwhVal = r.quantity || r.active_energy_kwh || r.kwh || 0;
                const meterOrDoc = r.supplier || r.meter_id || r.customer_code || r.evidence?.source_document || 'EVN';
                return `
                <tr class="hover:bg-[#f5f9f4] transition ${isInterpolated ? 'bg-amber-50/40' : ''}">
                    <td class="p-3 font-semibold text-[#091710]">${periodOrMonth}</td>
                    <td class="p-3 font-semibold font-mono ${isInterpolated ? 'text-amber-800' : 'text-[#091710]'}">${Number(kwhVal).toLocaleString()}</td>
                    <td class="p-3 text-[#6a8978] text-[11px] font-mono">${r.unit || 'kWh'}</td>
                    <td class="p-3 text-[#2c4a3c]">${meterOrDoc}</td>
                    <td class="p-3">${isInterpolated ? '<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-900 border border-amber-200">Nội suy</span>' : '<span class="text-[#6a8978] font-sans">Hóa đơn EVN</span>'}</td>
                    <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold ${isInterpolated ? 'bg-amber-100 text-amber-900' : 'bg-[#edf5e9] text-[#003c33]'}">${conf}</span></td>
                </tr>
                `;
            }).join('');
        } else {
            s2Body.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-[#6a8978] font-sans">Chưa có dữ liệu Scope 2</td></tr>';
        }
    }

    const queries = intermediate.queries || data.queries || [];
    const assumptions = intermediate.assumptions || data.assumptions || [];
    const tcLogs = document.getElementById('tabCount-logs');
    if (tcLogs) tcLogs.innerText = queries.length + assumptions.length;
    document.getElementById('queryLogCount').innerText = `${queries.length} mục`;
    document.getElementById('assumptionLogCount').innerText = `${assumptions.length} mục`;

    const qBody = document.getElementById('tableQueryLogBody');
    if (qBody) {
        if (queries.length > 0) {
            qBody.innerHTML = queries.map(q => `
                <tr class="hover:bg-amber-50/40 transition">
                    <td class="p-3 font-mono font-semibold text-amber-900">${q.query_id || '--'}</td>
                    <td class="p-3 text-[#2c4a3c] font-medium">${q.scope || '--'}</td>
                    <td class="p-3 text-[#091710]">${q.detected_issue || q.description || q.issue || '--'}</td>
                    <td class="p-3 text-[#6a8978]">${q.action_taken || q.provisional_action || '--'}</td>
                    <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-900">${q.status || 'Tạm tính'}</span></td>
                </tr>
            `).join('');
        } else {
            qBody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-[#6a8978]">Không có truy vấn bất thường</td></tr>';
        }
    }

    const aBody = document.getElementById('tableAssumptionLogBody');
    if (aBody) {
        if (assumptions.length > 0) {
            aBody.innerHTML = assumptions.map(a => `
                <tr class="hover:bg-[#f5f9f4] transition">
                    <td class="p-3 font-mono font-semibold text-[#091710]">${a.assumption_id || '--'}</td>
                    <td class="p-3 text-[#2c4a3c] font-medium">${a.parameter_name || a.scope || '--'}</td>
                    <td class="p-3 text-[#091710]">${a.justification || a.rule_applied || `${a.assumed_value} ${a.assumed_unit}`}</td>
                    <td class="p-3 font-mono font-semibold text-red-700">-${((a.confidence_penalty || 0.1) * 100).toFixed(0)}%</td>
                    <td class="p-3 font-mono font-semibold text-amber-800">+${a.uncertainty_markup_pct || 15}%</td>
                </tr>
            `).join('');
        } else {
            aBody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-[#6a8978]">Không có giả định nào</td></tr>';
        }
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
            viewer.innerText = `// Tệp ${filename} chưa tồn tại.`;
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
        alert('Đã sao chép nội dung JSON.');
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
        content.innerText = "Chưa thể xem trước báo cáo.";
    }
}

function closeMarkdownModal() {
    const modal = document.getElementById('mdPreviewModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}
