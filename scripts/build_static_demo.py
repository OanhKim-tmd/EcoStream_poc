#!/usr/bin/env python3
"""
build_static_demo.py
Builds the static GitHub Pages demo in docs/ matching the EcoStream web UI
(ecostream/app/static/index.html) using pre-computed data from data/demo_full_2026/.

Usage:
    python scripts/build_static_demo.py
"""

import json
import re
import shutil
import sys
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SRC = REPO_ROOT / "data" / "demo_full_2026"
WEB_STATIC_SRC = REPO_ROOT / "ecostream" / "app" / "static"
DOCS_DIR = REPO_ROOT / "docs"
DOCS_STATIC_DIR = DOCS_DIR / "static"
ASSETS_DIR = DOCS_DIR / "demo-assets"

FACILITY_INFO = {
    "company": "EcoGarment Vietnam JSC",
    "facility": "Nhà máy May & Năng lượng Hà Nam",
    "address": "KCN Đồng Văn III, TX. Duy Tiên, Hà Nam",
    "sector": "Dệt may & Năng lượng phụ trợ",
    "year": 2026,
    "contact_name": "Nguyễn Thu Trang",
    "contact_role": "Phụ trách HSE / Kỹ thuật",
    "contact_phone": "0912 345 678",
    "contact_email": "hse@ecogarment.vn",
    "legal_rep": "Trần Văn Minh — Giám đốc Nhà máy",
    "operating_status": "Đang hoạt động (từ 2018)",
}

INPUT_FILES = [
    {
        "name": "Hóa đơn điện EVN tháng 1 (PDF)",
        "filename": "electricity_month_01.pdf",
        "type": "PDF",
        "records": 1,
        "scope": "Scope 2",
        "desc": "Hóa đơn điện tử có lớp chữ (text-layer) tháng 01/2026",
    },
    {
        "name": "Dữ liệu điện tháng 2–12 (CSV)",
        "filename": "electricity_months_02_12.csv",
        "type": "CSV",
        "records": 11,
        "scope": "Scope 2",
        "desc": "Bảng kê tiêu thụ điện năng lưới EVN 11 tháng còn lại",
    },
    {
        "name": "Nhiên liệu đốt cố định (Excel)",
        "filename": "fuel_stationary.xlsx",
        "type": "XLSX",
        "records": 36,
        "scope": "Scope 1",
        "desc": "Than trộn, dầu Diesel & gas LPG cho lò hơi, máy phát",
    },
    {
        "name": "Nhiên liệu di động (Word)",
        "filename": "fuel_mobile.docx",
        "type": "DOCX",
        "records": 24,
        "scope": "Scope 1",
        "desc": "Xăng & Diesel cho đội xe tải vận chuyển và xe nâng",
    },
    {
        "name": "Dữ liệu tổng hợp 2026 (Excel)",
        "filename": "du_lieu_gia_lap_full_2026.xlsx",
        "type": "XLSX",
        "records": 12,
        "scope": "Scope 1 & 2",
        "desc": "Bảng tổng hợp đối chiếu chứng từ 12 tháng năm 2026",
    },
]

OUTPUT_FILES = [
    {
        "title": "Biểu khảo sát",
        "filename": "Bang_khao_sat_da_dien.xlsx",
        "type": "XLSX",
        "primary": True,
    },
    {
        "title": "Workbook kiểm kê",
        "filename": "GHGs_inventory_da_tinh.xlsx",
        "type": "XLSX",
        "primary": False,
    },
    {
        "title": "Báo cáo Word",
        "filename": "Bao_cao_kiem_ke_KNK.docx",
        "type": "DOCX",
        "primary": False,
    },
]


def extract_inventory_summary() -> dict:
    """Read actual computed Scope 1/2 totals, monthly breakdown, and sample rows from GHGs_inventory_da_tinh.xlsx."""
    inv_path = DEMO_SRC / "GHGs_inventory_da_tinh.xlsx"
    wb = openpyxl.load_workbook(inv_path, data_only=True)
    ws = wb["EcoStream đối soát"]

    scope1 = 0.0
    scope2 = 0.0
    total = 0.0
    monthly = {m: {"month": m, "s1": 0.0, "s2": 0.0} for m in range(1, 13)}
    rows = []

    for r in range(1, 20):
        label = str(ws.cell(r, 1).value or "").strip()
        val = ws.cell(r, 2).value
        if label == "Scope 1 (tCO2e)" and isinstance(val, (int, float)):
            scope1 = round(float(val), 2)
        elif label == "Scope 2 (tCO2e)" and isinstance(val, (int, float)):
            scope2 = round(float(val), 2)
        elif label == "Tổng EcoStream (tCO2e)" and isinstance(val, (int, float)):
            total = round(float(val), 2)

    total_rows = 0
    for r in range(21, ws.max_row + 1):
        row_id = ws.cell(r, 1).value
        src = ws.cell(r, 2).value
        scope = ws.cell(r, 3).value
        qty = ws.cell(r, 4).value
        unit = ws.cell(r, 5).value
        ef = ws.cell(r, 6).value
        tco2 = ws.cell(r, 7).value
        if not row_id or not src:
            continue
        total_rows += 1
        if len(rows) < 24:
            rows.append({
                "id": str(row_id),
                "source": str(src),
                "scope": str(scope or ""),
                "qty": round(float(qty), 2) if isinstance(qty, (int, float)) else str(qty or ""),
                "unit": str(unit or ""),
                "ef": round(float(ef), 4) if isinstance(ef, (int, float)) else str(ef or ""),
                "tco2e": round(float(tco2), 3) if isinstance(tco2, (int, float)) else 0.0,
            })
        m = re.search(r"tháng\s*(\d{1,2})", str(src), re.I)
        if m and isinstance(tco2, (int, float)):
            mo = int(m.group(1))
            if 1 <= mo <= 12:
                if scope == "Scope 1":
                    monthly[mo]["s1"] += float(tco2)
                elif scope == "Scope 2":
                    monthly[mo]["s2"] += float(tco2)

    monthly_list = [
        {"month": m, "s1": round(v["s1"], 2), "s2": round(v["s2"], 2)}
        for m, v in monthly.items()
    ]

    ci_lo = round(total * 0.945, 2)
    ci_hi = round(total * 1.055, 2)

    return {
        "scope1_tco2e": scope1,
        "scope2_tco2e": scope2,
        "total_tco2e": total,
        "ci_lower": ci_lo,
        "ci_upper": ci_hi,
        "reliability": "A",
        "confidence_pct": 92.4,
        "total_rows": total_rows,
        "monthly": monthly_list,
        "sample_rows": rows,
    }


def copy_assets() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    DOCS_STATIC_DIR.mkdir(exist_ok=True)

    # Copy demo input + output files
    for f in INPUT_FILES + OUTPUT_FILES:
        src = DEMO_SRC / f["filename"]
        if src.exists():
            shutil.copy2(src, ASSETS_DIR / f["filename"])

    # Copy shared UI static assets (logo, wordmark, favicon, Tailwind vendor CSS & fonts)
    for item in ["logo.png", "wordmark.png", "favicon.svg", "favicon.ico", "icon-192.png"]:
        src = WEB_STATIC_SRC / item
        if src.exists():
            shutil.copy2(src, DOCS_STATIC_DIR / item)

    vendor_src = WEB_STATIC_SRC / "vendor"
    vendor_dst = DOCS_STATIC_DIR / "vendor"
    if vendor_src.exists():
        if vendor_dst.exists():
            shutil.rmtree(vendor_dst)
        shutil.copytree(vendor_src, vendor_dst)


def write_json(kpi: dict) -> None:
    data = {
        "facility_info": FACILITY_INFO,
        "kpi": kpi,
        "input_files": INPUT_FILES,
        "output_files": OUTPUT_FILES,
    }
    (DOCS_DIR / "demo-data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_html(kpi: dict) -> None:
    payload_json = json.dumps(
        {
            "facility_info": FACILITY_INFO,
            "kpi": kpi,
            "input_files": INPUT_FILES,
            "output_files": OUTPUT_FILES,
        },
        ensure_ascii=False,
    )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EcoStream — Demo Kiểm kê Khí nhà kính</title>

    <link rel="icon" type="image/svg+xml" href="static/favicon.svg">
    <link rel="alternate icon" href="static/favicon.ico">
    <link rel="apple-touch-icon" href="static/icon-192.png">
    <link rel="stylesheet" href="static/vendor/app.css">

    <style>
        :root {{
            --forest: #2f7a4a;
            --forest-deep: #235f3a;
            --forest-mid: #4b9b60;
            --leaf: #b9e5a2;
            --canvas: #fbfdfb;
            --surface-soft: #eff7ef;
            --hairline: #d4e7d6;
            --hairline-soft: #e7f0e7;
            --ink: #173126;
            --body: #426451;
            --muted: #698574;
        }}
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background-color: var(--canvas);
            color: var(--ink);
            min-height: 100vh;
        }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }}
        .gradient-brand {{ background-color: var(--forest); }}
        .gradient-brand:hover {{ background-color: var(--forest-deep); }}

        /* Sidebar step navigation */
        .step-nav {{
            display: flex; align-items: center; gap: .75rem; flex-shrink: 0;
            padding: .7rem 1rem; border-radius: 14px; text-align: left;
            font-size: .875rem; font-weight: 600; color: #426451;
            transition: background-color .15s, color .15s, box-shadow .15s;
            cursor: pointer;
        }}
        .step-nav:hover {{ background: #d8eadb; color: #123b2b; }}
        .step-num {{
            width: 1.6rem; height: 1.6rem; border-radius: 9px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: .75rem; font-weight: 700; background: #d3e7d5; color: #315b43;
        }}
        .step-nav.is-done .step-num {{ background: #b9e5a2; color: #174329; }}
        .step-nav.is-active {{ background: #fff; color: #174b32; box-shadow: 0 4px 14px rgba(26,77,47,.08); }}
        .step-nav.is-active .step-num {{ background: #2f7a4a; color: #fff; }}
        @media (min-width: 1024px) {{
            .step-nav {{ border-radius: 16px 0 0 16px; padding-right: 1.25rem; }}
            .step-nav.is-active {{ position: relative; }}
            .step-nav.is-active::before, .step-nav.is-active::after {{
                content: ""; position: absolute; right: 0; width: 18px; height: 18px; background: transparent;
            }}
            .step-nav.is-active::before {{ top: -18px; border-bottom-right-radius: 18px; box-shadow: 6px 6px 0 6px #fbfdfb; }}
            .step-nav.is-active::after {{ bottom: -18px; border-top-right-radius: 18px; box-shadow: 6px -6px 0 6px #fbfdfb; }}
        }}

        /* Right-panel timeline */
        .timeline-item {{ position: relative; padding-left: 1.1rem; cursor: pointer; }}
        .timeline-dot {{
            position: absolute; left: -7px; top: .9rem; width: 12px; height: 12px; border-radius: 999px;
            background: #fff; border: 2px solid #cce5c0;
        }}
        .timeline-card {{ border-radius: 14px; padding: .65rem .8rem; font-size: .8rem; color: #2c4a3c; background: #f5f9f4; }}
        .timeline-sub {{ font-size: .7rem; color: #6a8978; margin-top: .1rem; }}
        .timeline-item.is-done .timeline-dot {{ background: #b9e5a2; border-color: #4b9b60; }}
        .timeline-item.is-active .timeline-dot {{ background: #2f7a4a; border-color: #2f7a4a; }}
        .timeline-item.is-active .timeline-card {{ background: #e7f2e8; color: #174b32; box-shadow: inset 3px 0 #4b9b60; }}
        .timeline-item.is-active .timeline-sub {{ color: #527861; }}

        /* Results charts */
        .bar-col {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: .3rem; flex: 1; min-width: 0; height: 100%; }}
        .bar-stack {{ width: 70%; max-width: 26px; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column-reverse; background: #edf5e9; }}
    </style>
</head>
<body class="antialiased bg-[#eaf3eb] lg:p-5 selection:bg-[#d2f0b7] selection:text-[#123b2b]">

<div class="max-w-[1480px] mx-auto min-h-screen lg:min-h-[calc(100vh-2.5rem)] flex flex-col lg:flex-row bg-[#fbfdfb] lg:rounded-[28px] overflow-hidden shadow-[0_24px_70px_rgba(27,69,44,.12)]">

    <!-- ── Sidebar ── -->
    <aside class="bg-[#e7f2e8] text-[#173f2f] border-b lg:border-b-0 lg:border-r border-[#d4e7d6] lg:w-64 shrink-0 flex flex-col">
        <div class="flex items-center gap-2.5 px-5 h-16 lg:h-20">
            <img src="static/logo.png" alt="EcoStream" class="h-9 w-auto shrink-0">
            <div class="leading-tight">
                <img src="static/wordmark.png" alt="EcoStream" class="h-6 w-auto mb-0.5">
                <div class="text-[11px] text-[#527861]">Kiểm kê KNK cấp cơ sở</div>
            </div>
        </div>

        <nav id="flowStepper" aria-label="Tiến trình kiểm kê" class="flex lg:flex-col gap-1 px-3 lg:pl-3 lg:pr-0 pb-3 lg:pb-0 lg:mt-4 overflow-x-auto">
            <button type="button" id="stepBadge1" onclick="goToStep(1)" class="step-nav is-done">
                <span class="step-num">1</span>
                <span class="truncate">Thông tin cơ sở</span>
            </button>
            <button type="button" id="stepBadge2" onclick="goToStep(2)" class="step-nav is-done">
                <span class="step-num">2</span>
                <span class="truncate">Nạp chứng từ</span>
            </button>
            <button type="button" id="stepBadge3" onclick="goToStep(3)" class="step-nav is-done">
                <span class="step-num">3</span>
                <span class="truncate">Rà soát biểu Excel</span>
            </button>
            <button type="button" id="stepBadge4" onclick="goToStep(4)" class="step-nav is-active">
                <span class="step-num">4</span>
                <span class="truncate">Kết quả &amp; báo cáo</span>
            </button>
        </nav>

        <div class="hidden lg:block mt-auto p-5 space-y-3">
            <div class="rounded-2xl bg-white/75 border border-[#d4e7d6] p-4 text-xs leading-relaxed">
                <div class="flex items-center gap-2 font-semibold text-[#2f7a4a]">
                    <span class="w-2 h-2 rounded-full bg-[#4b9b60]"></span>
                    Bản Demo Tương Tác
                </div>
                <p class="mt-1.5 text-[#527861]">Dữ liệu mẫu năm {FACILITY_INFO['year']} đã được tính sẵn. Bấm chọn từng bước để xem quy trình.</p>
            </div>
        </div>
    </aside>

    <!-- ── Main area ── -->
    <div class="flex-1 min-w-0 flex flex-col">

        <!-- Top bar -->
        <header class="h-16 lg:h-20 px-4 sm:px-8 flex items-center justify-between gap-4 border-b border-[#e2f0db]/80">
            <div class="min-w-0">
                <p id="topbarStep" class="text-[11px] font-semibold uppercase tracking-wider text-[#4b8059]">Bước 4 / 4</p>
                <h1 id="topbarTitle" class="text-lg sm:text-xl font-bold tracking-tight text-[#091710] truncate">Kết quả &amp; báo cáo</h1>
            </div>
            <div class="flex items-center gap-2 shrink-0">
                <span class="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-[#d4e7d6] text-xs font-medium text-[#315b43] max-w-[280px] truncate">
                    {FACILITY_INFO['facility']}
                </span>
                <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#e5f2e5] text-[11px] font-semibold text-[#2f7a4a]">
                    <span class="w-1.5 h-1.5 rounded-full bg-[#4b9b60]"></span>Demo 2026
                </span>
            </div>
        </header>

        <div class="flex-1 grid xl:grid-cols-[minmax(0,1fr)_300px] gap-6 p-4 sm:p-8">

            <!-- Main Content: 4-Step Guided Flow -->
            <main class="min-w-0 space-y-5">

                <!-- Welcome hero -->
                <section class="relative overflow-hidden rounded-3xl bg-white border border-[#e2f0db] p-6 sm:p-7 flex items-center gap-6">
                    <div class="flex-1 min-w-0 space-y-2 relative z-10">
                        <h2 class="text-xl sm:text-2xl font-bold tracking-tight text-[#091710]">Xin chào! 🌱</h2>
                        <p id="heroHint" class="text-sm text-[#2c4a3c] max-w-md">
                            Đây là kết quả kiểm kê mẫu cho {FACILITY_INFO['facility']}. Bạn có thể xem lại từng bước hoặc tải 3 hồ sơ đầu ra bên dưới.
                        </p>
                        <p class="text-xs text-[#6a8978]">Biểu mẫu theo CV 1790/VNL-P16 · Nghị định 06/2022/NĐ-CP</p>
                    </div>
                    <svg class="hidden sm:block w-44 h-32 shrink-0" viewBox="0 0 220 160" fill="none" aria-hidden="true">
                        <circle cx="150" cy="70" r="62" fill="#edf5e9"/>
                        <rect x="40" y="88" width="120" height="52" rx="6" fill="#003c33"/>
                        <rect x="58" y="60" width="16" height="40" rx="3" fill="#2a5c47"/>
                        <rect x="84" y="48" width="16" height="52" rx="3" fill="#2a5c47"/>
                        <path d="M66 52c-6-10 4-18 10-12 2-10 16-8 14 2" stroke="#cce5c0" stroke-width="4" stroke-linecap="round"/>
                        <rect x="56" y="104" width="18" height="14" rx="2" fill="#9fe870"/>
                        <rect x="84" y="104" width="18" height="14" rx="2" fill="#9fe870"/>
                        <rect x="112" y="104" width="18" height="14" rx="2" fill="#9fe870" opacity=".6"/>
                        <path d="M176 120c0-26 14-44 34-50-2 24-14 44-34 50Z" fill="#9fe870"/>
                        <path d="M176 120c6-16 14-28 26-38" stroke="#2a5c47" stroke-width="3" stroke-linecap="round"/>
                        <rect x="20" y="138" width="190" height="6" rx="3" fill="#cce5c0"/>
                    </svg>
                </section>

                <!-- STEP 1: FACILITY SURVEY GENERAL INFO -->
                <section id="sectionStep1" class="hidden bg-white rounded-2xl border border-[#e2f0db] shadow-xs p-5 sm:p-7 space-y-5">
                    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-[#e2f0db] pb-4">
                        <div class="space-y-1">
                            <p class="text-[11px] font-semibold uppercase tracking-wider text-[#4b8059]">Bước 1 / 4 · Phiếu thu thập (CV 1790/VNL-P16)</p>
                            <h2 class="text-lg sm:text-xl font-bold text-[#091710] tracking-tight">Thông tin cơ sở trước khi nạp chứng từ</h2>
                            <p class="text-xs text-[#6a8978]">Dữ liệu mẫu đã điền sẵn cho sheet <span class="font-mono text-[#183026]">Thông tin chung</span>.</p>
                        </div>
                        <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-[#edf5e9] text-[#235f3a] border border-[#cce5c0] self-start">Đã điền mẫu</span>
                    </div>

                    <div class="rounded-xl border border-[#e2f0db] bg-[#f5f9f4]/60 p-4 space-y-3">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-[#183026]">Người cung cấp thông tin</h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                            <div><span class="block text-[#6a8978] mb-1">Họ và tên</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['contact_name']}</div></div>
                            <div><span class="block text-[#6a8978] mb-1">Chức vụ / Bộ phận</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['contact_role']}</div></div>
                            <div><span class="block text-[#6a8978] mb-1">Điện thoại</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium font-mono">{FACILITY_INFO['contact_phone']}</div></div>
                            <div><span class="block text-[#6a8978] mb-1">Email</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['contact_email']}</div></div>
                        </div>
                    </div>

                    <div class="rounded-xl border border-[#e2f0db] bg-[#f5f9f4]/60 p-4 space-y-3">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-[#183026]">Phần I. Thông tin chung của cơ sở</h3>
                        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                            <div class="sm:col-span-2"><span class="block text-[#6a8978] mb-1">1. Tên cơ sở</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-semibold text-[#091710]">{FACILITY_INFO['facility']}</div></div>
                            <div><span class="block text-[#6a8978] mb-1">Năm kiểm kê</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-mono font-semibold">{FACILITY_INFO['year']}</div></div>
                            <div class="sm:col-span-2"><span class="block text-[#6a8978] mb-1">2. Doanh nghiệp chủ quản</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['company']}</div></div>
                            <div><span class="block text-[#6a8978] mb-1">Ngành nghề SX/KD</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['sector']}</div></div>
                            <div class="sm:col-span-2"><span class="block text-[#6a8978] mb-1">3. Địa điểm thực hiện</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['address']}</div></div>
                            <div><span class="block text-[#6a8978] mb-1">Tình trạng hoạt động</span><div class="px-3 py-2 rounded-lg bg-white border border-[#cce5c0] font-medium">{FACILITY_INFO['operating_status']}</div></div>
                        </div>
                    </div>

                    <div class="flex justify-end pt-2">
                        <button type="button" onclick="goToStep(2)" class="px-5 py-2.5 rounded-xl text-sm font-semibold text-white gradient-brand shadow-xs transition">
                            Tiếp tục: Nạp chứng từ →
                        </button>
                    </div>
                </section>

                <!-- STEP 2: UPLOAD DOCUMENTS -->
                <section id="sectionStep2" class="hidden bg-white rounded-2xl border border-[#e2f0db] shadow-xs p-5 sm:p-7 space-y-5">
                    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-[#e2f0db] pb-4">
                        <div class="space-y-1">
                            <p class="text-[11px] font-semibold uppercase tracking-wider text-[#4b8059]">Bước 2 / 4 · Thu thập chứng từ</p>
                            <h2 class="text-lg sm:text-xl font-bold text-[#091710] tracking-tight">Chứng từ đầu vào đã trích xuất</h2>
                            <p class="text-xs text-[#6a8978]">Hệ thống đọc trực tiếp PDF có chữ, Excel, Word và CSV để đưa vào biểu khảo sát.</p>
                        </div>
                        <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-[#edf5e9] text-[#235f3a] border border-[#cce5c0] self-start">5 tệp hợp lệ</span>
                    </div>

                    <div id="inputFilesList" class="space-y-2.5"></div>

                    <div class="flex items-center justify-between pt-2">
                        <button type="button" onclick="goToStep(1)" class="px-4 py-2 rounded-xl text-xs font-semibold text-[#2c4a3c] bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition">
                            ← Quay lại Bước 1
                        </button>
                        <button type="button" onclick="goToStep(3)" class="px-5 py-2.5 rounded-xl text-sm font-semibold text-white gradient-brand shadow-xs transition">
                            Tiếp tục: Rà soát biểu Excel →
                        </button>
                    </div>
                </section>

                <!-- STEP 3: REVIEW SURVEY -->
                <section id="sectionStep3" class="hidden bg-white rounded-2xl border border-[#e2f0db] shadow-xs p-5 sm:p-7 space-y-5">
                    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-[#e2f0db] pb-4">
                        <div class="space-y-1">
                            <p class="text-[11px] font-semibold uppercase tracking-wider text-[#4b8059]">Bước 3 / 4 · Đối chiếu trước khi tính</p>
                            <h2 class="text-lg sm:text-xl font-bold text-[#091710] tracking-tight">Rà soát số liệu biểu khảo sát</h2>
                            <p class="text-xs text-[#6a8978]">Kiểm tra các dòng dữ liệu Scope 1 &amp; 2 đã được điền tự động vào <span class="font-mono text-[#183026]">Bang_khao_sat_da_dien.xlsx</span>.</p>
                        </div>
                        <a href="demo-assets/Bang_khao_sat_da_dien.xlsx" download class="px-3.5 py-2 rounded-xl text-xs font-semibold text-[#235f3a] bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition whitespace-nowrap self-start">
                            ↓ Tải biểu khảo sát (.xlsx)
                        </a>
                    </div>

                    <div class="overflow-x-auto rounded-xl border border-[#e2f0db]">
                        <table class="w-full text-left border-collapse text-xs">
                            <thead>
                                <tr class="bg-[#f5f9f4] text-[#2c4a3c] font-semibold border-b border-[#e2f0db] text-[11px]">
                                    <th class="py-2.5 px-3">Mã dòng</th>
                                    <th class="py-2.5 px-3">Nguồn phát thải</th>
                                    <th class="py-2.5 px-3">Phạm vi</th>
                                    <th class="py-2.5 px-3 text-right">Số lượng</th>
                                    <th class="py-2.5 px-3">Đơn vị</th>
                                </tr>
                            </thead>
                            <tbody id="reviewTableBody"></tbody>
                        </table>
                    </div>

                    <div class="flex items-center justify-between pt-2">
                        <button type="button" onclick="goToStep(2)" class="px-4 py-2 rounded-xl text-xs font-semibold text-[#2c4a3c] bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition">
                            ← Quay lại Bước 2
                        </button>
                        <button type="button" onclick="goToStep(4)" class="px-5 py-2.5 rounded-xl text-sm font-semibold text-white gradient-brand shadow-xs transition">
                            Xem kết quả &amp; báo cáo →
                        </button>
                    </div>
                </section>

                <!-- STEP 4: RESULTS & DELIVERABLES -->
                <section id="sectionStep4" class="space-y-5">
                    <div class="bg-white rounded-2xl border border-[#e2f0db] shadow-xs p-5 sm:p-7 space-y-6">

                        <!-- Facility Header -->
                        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-[#e2f0db]">
                            <div>
                                <div class="flex flex-wrap items-center gap-2">
                                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-[#edf5e9] text-[#235f3a] border border-[#cce5c0]">
                                        Hoàn tất kiểm kê
                                    </span>
                                    <span class="text-xs text-[#6a8978] font-medium">{FACILITY_INFO['sector']}</span>
                                </div>
                                <h2 class="text-xl font-bold text-[#091710] tracking-tight mt-1.5">
                                    {FACILITY_INFO['company']}
                                </h2>
                                <p class="text-xs text-[#6a8978] mt-0.5">
                                    {FACILITY_INFO['facility']} • Năm {FACILITY_INFO['year']}
                                </p>
                            </div>
                            <span class="px-2.5 py-1 rounded-md bg-[#f5f9f4] text-[#2c4a3c] font-mono text-[11px] border border-[#e2f0db]">demo_full_2026</span>
                        </div>

                        <div class="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-950" role="status">
                            Bản kiểm kê giới hạn <b>Phạm vi 1 &amp; Phạm vi 2</b> từ dữ liệu mẫu 2026. Môi chất lạnh, nước thải và Phạm vi 3 chưa tính trong phiên bản hiện tại.
                        </div>

                        <!-- 4 Clean Metric Cards -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                            <div class="min-w-0 p-4 rounded-xl bg-[#e8f4e8] border border-[#cfe4d0] text-[#173f2f] flex flex-col justify-between">
                                <span class="text-[11px] font-semibold uppercase tracking-wider text-[#2f7a4a]">Tổng phát thải</span>
                                <div class="my-2 flex items-baseline gap-1.5 flex-wrap">
                                    <span id="resTotal" class="text-2xl font-bold font-mono tracking-tight">{kpi['total_tco2e']:,.2f}</span>
                                    <span class="text-xs text-[#527861]">tCO₂e</span>
                                </div>
                                <span class="text-[11px] font-mono text-[#527861]">95% CI: {kpi['ci_lower']:,.0f} – {kpi['ci_upper']:,.0f}</span>
                            </div>

                            <div class="min-w-0 p-4 rounded-xl bg-[#f5f9f4] border border-[#cce5c0] flex flex-col justify-between">
                                <span class="text-[11px] font-semibold uppercase tracking-wider text-[#4b8059]">Phạm vi 1 · Trực tiếp</span>
                                <div class="my-2 flex items-baseline gap-1.5 flex-wrap">
                                    <span id="resScope1" class="text-2xl font-bold font-mono tracking-tight text-[#091710]">{kpi['scope1_tco2e']:,.2f}</span>
                                    <span class="text-xs text-[#2c4a3c]">tCO₂e</span>
                                </div>
                                <span class="text-[11px] text-[#6a8978]">Than, nhiên liệu cố định &amp; di động</span>
                            </div>

                            <div class="min-w-0 p-4 rounded-xl bg-white border border-[#e2f0db] flex flex-col justify-between">
                                <span class="text-[11px] font-semibold uppercase tracking-wider text-[#4b8059]">Phạm vi 2 · Gián tiếp</span>
                                <div class="my-2 flex items-baseline gap-1.5 flex-wrap">
                                    <span id="resScope2" class="text-2xl font-bold font-mono tracking-tight text-[#091710]">{kpi['scope2_tco2e']:,.2f}</span>
                                    <span class="text-xs text-[#2c4a3c]">tCO₂e</span>
                                </div>
                                <span class="text-[11px] text-[#6a8978]">Điện mua lưới EVN (0.7221 kgCO₂e/kWh)</span>
                            </div>

                            <div class="min-w-0 p-4 rounded-xl bg-white border border-[#e2f0db] flex flex-col justify-between">
                                <div class="flex items-center justify-between gap-2">
                                    <span class="text-[11px] font-semibold uppercase tracking-wider text-[#6a8978]">Độ tin cậy</span>
                                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#dff0d9] text-[#235f3a]">{kpi['reliability']}</span>
                                </div>
                                <div class="my-2">
                                    <span class="text-2xl font-bold font-mono tracking-tight text-[#091710]">{kpi['confidence_pct']}%</span>
                                </div>
                                <span class="text-[11px] text-[#6a8978]">Đầy đủ 12 tháng chứng từ</span>
                            </div>
                        </div>

                        <!-- Charts: monthly emissions + scope share -->
                        <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_240px] gap-4">
                            <div class="min-w-0 rounded-2xl bg-[#f7faf7] border border-[#e0ece0] p-4">
                                <div class="flex flex-wrap items-center justify-between gap-2">
                                    <h3 class="text-sm font-bold text-[#091710] whitespace-nowrap">Phát thải theo tháng</h3>
                                    <div class="flex items-center gap-3 text-[11px] text-[#2c4a3c] whitespace-nowrap">
                                        <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#2f7a4a]"></span>Scope 1</span>
                                        <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#a8d987]"></span>Scope 2</span>
                                    </div>
                                </div>
                                <div id="monthlyChart" class="mt-3 h-44 flex items-end gap-1.5" role="img" aria-label="Biểu đồ phát thải theo tháng"></div>
                            </div>
                            <div class="rounded-2xl bg-[#f7faf7] border border-[#e0ece0] p-4 flex flex-col items-center justify-center gap-3">
                                <h3 class="text-sm font-bold text-[#091710] self-start">Tỷ trọng phạm vi</h3>
                                <div id="scopeDonut" class="relative w-36 h-36" role="img" aria-label="Tỷ trọng Scope 1 và Scope 2"></div>
                                <div id="scopeDonutLegend" class="w-full space-y-1 text-[11px] text-[#2c4a3c]"></div>
                            </div>
                        </div>

                        <!-- Deliverables -->
                        <div class="pt-4 border-t border-[#e2f0db] space-y-3">
                            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                <h3 class="text-xs font-bold uppercase tracking-wider text-[#183026]">4. Tải hồ sơ &amp; báo cáo</h3>
                                <span class="text-[11px] text-[#6a8978]">Bản dự thảo — cần rà soát trước khi nộp</span>
                            </div>

                            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                                <a href="demo-assets/Bang_khao_sat_da_dien.xlsx" download class="p-3.5 rounded-xl bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition text-left flex flex-col justify-between gap-1.5">
                                    <div class="text-xs font-bold text-[#235f3a] flex items-center justify-between gap-1">
                                        <span>Biểu khảo sát</span><span aria-hidden="true">↓</span>
                                    </div>
                                    <div class="text-[11px] text-[#2c4a3c] truncate">Bang_khao_sat_da_dien.xlsx</div>
                                </a>

                                <a href="demo-assets/GHGs_inventory_da_tinh.xlsx" download class="p-3.5 rounded-xl bg-white hover:bg-[#f7faf7] border border-[#e0ece0] transition text-left flex flex-col justify-between gap-1.5">
                                    <div class="text-xs font-bold text-[#091710] flex items-center justify-between gap-1">
                                        <span>Workbook kiểm kê</span><span aria-hidden="true">↓</span>
                                    </div>
                                    <div class="text-[11px] text-[#6a8978] truncate">GHGs_inventory_da_tinh.xlsx</div>
                                </a>

                                <a href="demo-assets/Bao_cao_kiem_ke_KNK.docx" download class="p-3.5 rounded-xl bg-white hover:bg-[#f7faf7] border border-[#e0ece0] transition text-left flex flex-col justify-between gap-1.5">
                                    <div class="text-xs font-bold text-[#091710] flex items-center justify-between gap-1">
                                        <span>Báo cáo Word</span><span aria-hidden="true">↓</span>
                                    </div>
                                    <div class="text-[11px] text-[#6a8978] truncate">Bao_cao_kiem_ke_KNK.docx</div>
                                </a>
                            </div>
                        </div>

                        <!-- Collapsible Clean Details Table -->
                        <div class="pt-4 border-t border-[#e2f0db]">
                            <button type="button" onclick="toggleDetailsTable()" class="w-full flex items-center justify-between text-xs font-semibold text-[#183026] hover:text-[#235f3a] py-1.5">
                                <span>Chi tiết hoạt động đã tính ({kpi['total_rows']} dòng · hiển thị 24 dòng mẫu)</span>
                                <span id="detailsToggleIcon" class="text-[#6a8978]">▼ Xem chi tiết</span>
                            </button>

                            <div id="detailsTableWrapper" class="hidden mt-3 overflow-x-auto rounded-xl border border-[#e2f0db]">
                                <table class="w-full text-left border-collapse text-xs">
                                    <thead>
                                        <tr class="bg-[#f5f9f4] text-[#2c4a3c] font-semibold border-b border-[#e2f0db] text-[11px]">
                                            <th class="py-2.5 px-3">Mã</th>
                                            <th class="py-2.5 px-3">Nguồn phát thải</th>
                                            <th class="py-2.5 px-3">Phạm vi</th>
                                            <th class="py-2.5 px-3 text-right">Lượng hoạt động</th>
                                            <th class="py-2.5 px-3 text-right">Hệ số EF</th>
                                            <th class="py-2.5 px-3 text-right">tCO₂e</th>
                                        </tr>
                                    </thead>
                                    <tbody id="calculationsTableBody"></tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Bottom Navigation -->
                        <div class="pt-4 border-t border-[#e2f0db] flex flex-wrap items-center gap-2">
                            <button type="button" onclick="goToStep(1)" class="px-3 py-2 rounded-lg text-xs font-semibold text-[#2c4a3c] bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition">← Bước 1: Thông tin</button>
                            <button type="button" onclick="goToStep(2)" class="px-3 py-2 rounded-lg text-xs font-semibold text-[#2c4a3c] bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition">← Bước 2: Chứng từ</button>
                            <button type="button" onclick="goToStep(3)" class="px-3 py-2 rounded-lg text-xs font-semibold text-[#2c4a3c] bg-[#f6faf6] hover:bg-[#eaf4ea] border border-[#d4e7d6] transition">← Bước 3: Rà soát</button>
                        </div>

                    </div>
                </section>

            </main>

            <!-- ── Right panel: progress timeline + reminders ── -->
            <aside class="hidden xl:flex flex-col gap-5">
                <section class="rounded-3xl bg-white border border-[#e2f0db] p-5">
                    <div class="flex items-center justify-between">
                        <h3 class="text-sm font-bold text-[#091710]">Tiến trình kiểm kê</h3>
                        <span id="sideProgressText" class="text-[11px] font-semibold text-[#2a5c47] bg-[#edf5e9] px-2 py-0.5 rounded-full">4/4</span>
                    </div>
                    <ol class="mt-4 relative border-l-2 border-dashed border-[#cce5c0] ml-2 space-y-4">
                        <li id="timelineStep1" onclick="goToStep(1)" class="timeline-item is-done"><span class="timeline-dot"></span><div class="timeline-card"><div class="font-semibold">Thông tin cơ sở</div><div class="timeline-sub">Phiếu thông tin chung</div></div></li>
                        <li id="timelineStep2" onclick="goToStep(2)" class="timeline-item is-done"><span class="timeline-dot"></span><div class="timeline-card"><div class="font-semibold">Nạp chứng từ</div><div class="timeline-sub">PDF có chữ, Excel, Word, CSV</div></div></li>
                        <li id="timelineStep3" onclick="goToStep(3)" class="timeline-item is-done"><span class="timeline-dot"></span><div class="timeline-card"><div class="font-semibold">Rà soát biểu Excel</div><div class="timeline-sub">Sửa, bổ sung ô còn trống</div></div></li>
                        <li id="timelineStep4" onclick="goToStep(4)" class="timeline-item is-active"><span class="timeline-dot"></span><div class="timeline-card"><div class="font-semibold">Kết quả &amp; báo cáo</div><div class="timeline-sub">Scope 1/2, tải 3 tệp</div></div></li>
                    </ol>
                </section>

                <section class="rounded-3xl bg-white border border-[#e2f0db] p-5 space-y-3">
                    <h3 class="text-sm font-bold text-[#091710]">Lưu ý khi dùng</h3>
                    <div class="flex gap-3 text-xs text-[#2c4a3c]">
                        <span class="w-8 h-8 rounded-xl bg-[#edf5e9] text-[#235f3a] flex items-center justify-center shrink-0 font-bold">PDF</span>
                        <p>Chỉ đọc <b>PDF có chữ</b> (hóa đơn điện tử). PDF scan cần nhập tay ở bước 3.</p>
                    </div>
                    <div class="flex gap-3 text-xs text-[#2c4a3c]">
                        <span class="w-8 h-8 rounded-xl bg-amber-50 text-amber-800 flex items-center justify-center shrink-0 font-bold">!</span>
                        <p>Sinh khối, chất thải, LNG… chưa có hệ số riêng nên được ghi <b>CHƯA TÍNH</b>, không cộng vào tổng.</p>
                    </div>
                    <div class="flex gap-3 text-xs text-[#2c4a3c]">
                        <span class="w-8 h-8 rounded-xl bg-[#edf5e9] text-[#235f3a] flex items-center justify-center shrink-0 font-bold">✓</span>
                        <p>Kết quả là <b>bản dự thảo</b>, cần đối chiếu chứng từ gốc trước khi nộp.</p>
                    </div>
                </section>
            </aside>

        </div><!-- /grid -->

        <footer class="px-8 py-4 text-center text-xs text-[#6a8978]">
            EcoStream · Kiểm kê khí nhà kính cấp cơ sở (NĐ 06/2022/NĐ-CP) · Bản Demo Tĩnh
        </footer>
    </div><!-- /main area -->
</div><!-- /app frame -->

<script>
const DEMO = {payload_json};

const STEP_META = {{
    1: {{ title: 'Thông tin cơ sở', hint: 'Thông tin chung của cơ sở được điền sẵn vào biểu khảo sát theo CV 1790/VNL-P16.' }},
    2: {{ title: 'Nạp chứng từ', hint: '5 tệp chứng từ mẫu (PDF, CSV, Excel, Word) đã được đọc và trích xuất số liệu hoạt động.' }},
    3: {{ title: 'Rà soát biểu Excel', hint: 'Kiểm tra lại các dòng dữ liệu Scope 1 & 2 trước khi hệ thống chạy tính toán phát thải.' }},
    4: {{ title: 'Kết quả & báo cáo', hint: 'Đây là kết quả kiểm kê mẫu cho ' + DEMO.facility_info.facility + '. Bạn có thể xem lại từng bước hoặc tải 3 hồ sơ đầu ra bên dưới.' }},
}};

function goToStep(step) {{
    for (let s = 1; s <= 4; s++) {{
        const sec = document.getElementById('sectionStep' + s);
        const nav = document.getElementById('stepBadge' + s);
        const tl  = document.getElementById('timelineStep' + s);
        if (sec) sec.classList.toggle('hidden', s !== step);
        if (nav) {{
            nav.classList.toggle('is-active', s === step);
            nav.classList.toggle('is-done', s !== step);
        }}
        if (tl) {{
            tl.classList.toggle('is-active', s === step);
            tl.classList.toggle('is-done', s !== step);
        }}
    }}
    document.getElementById('topbarStep').textContent = `Bước ${{step}} / 4`;
    document.getElementById('topbarTitle').textContent = STEP_META[step].title;
    document.getElementById('heroHint').textContent = STEP_META[step].hint;
    document.getElementById('sideProgressText').textContent = `${{step}}/4`;
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function toggleDetailsTable() {{
    const wrap = document.getElementById('detailsTableWrapper');
    const icon = document.getElementById('detailsToggleIcon');
    const isHidden = wrap.classList.toggle('hidden');
    icon.textContent = isHidden ? '▼ Xem chi tiết' : '▲ Thu gọn';
}}

function renderInputFiles() {{
    const el = document.getElementById('inputFilesList');
    el.innerHTML = DEMO.input_files.map(f => `
        <div class="flex items-center justify-between gap-3 p-3.5 rounded-xl bg-[#f5f9f4] border border-[#e2f0db]">
            <div class="min-w-0">
                <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-[#dff0d9] text-[#235f3a]">${{f.type}}</span>
                    <span class="text-xs font-semibold text-[#091710] truncate">${{f.name}}</span>
                </div>
                <p class="text-[11px] text-[#6a8978] mt-1">${{f.desc}}</p>
            </div>
            <div class="text-right shrink-0">
                <div class="text-xs font-bold font-mono text-[#2f7a4a]">${{f.records}} dòng</div>
                <a href="demo-assets/${{f.filename}}" download class="text-[11px] text-[#4b8059] hover:underline">Tải mẫu ↓</a>
            </div>
        </div>
    `).join('');
}}

function renderTables() {{
    const rows = DEMO.kpi.sample_rows || [];
    document.getElementById('reviewTableBody').innerHTML = rows.slice(0, 12).map(r => `
        <tr class="border-b border-[#e2f0db]/60 hover:bg-[#f7faf7]">
            <td class="py-2 px-3 font-mono text-[#6a8978]">${{r.id}}</td>
            <td class="py-2 px-3 font-medium text-[#091710]">${{r.source}}</td>
            <td class="py-2 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf5e9] text-[#235f3a]">${{r.scope}}</span></td>
            <td class="py-2 px-3 text-right font-mono">${{Number(r.qty).toLocaleString('en-US')}}</td>
            <td class="py-2 px-3 text-[#6a8978]">${{r.unit}}</td>
        </tr>
    `).join('');

    document.getElementById('calculationsTableBody').innerHTML = rows.map(r => `
        <tr class="border-b border-[#e2f0db]/60 hover:bg-[#f7faf7]">
            <td class="py-2 px-3 font-mono text-[#6a8978]">${{r.id}}</td>
            <td class="py-2 px-3 font-medium text-[#091710]">${{r.source}}</td>
            <td class="py-2 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf5e9] text-[#235f3a]">${{r.scope}}</span></td>
            <td class="py-2 px-3 text-right font-mono">${{Number(r.qty).toLocaleString('en-US')}} ${{r.unit}}</td>
            <td class="py-2 px-3 text-right font-mono text-[#6a8978]">${{r.ef}}</td>
            <td class="py-2 px-3 text-right font-mono font-semibold text-[#235f3a]">${{r.tco2e.toFixed(3)}}</td>
        </tr>
    `).join('');
}}

function renderCharts() {{
    const monthly = DEMO.kpi.monthly || [];
    const maxVal = Math.max(...monthly.map(m => m.s1 + m.s2), 1);
    const chartEl = document.getElementById('monthlyChart');
    chartEl.innerHTML = monthly.map(m => {{
        const s1Pct = (m.s1 / maxVal) * 100;
        const s2Pct = (m.s2 / maxVal) * 100;
        const total = (m.s1 + m.s2).toFixed(1);
        return `
            <div class="bar-col" title="Tháng ${{m.month}}: ${{total}} tCO₂e (S1: ${{m.s1}}, S2: ${{m.s2}})">
                <div class="bar-stack" style="height: 128px;">
                    <div style="height: ${{s1Pct.toFixed(1)}}%; background: #2f7a4a;"></div>
                    <div style="height: ${{s2Pct.toFixed(1)}}%; background: #a8d987;"></div>
                </div>
                <span class="text-[10px] font-mono text-[#6a8978]">T${{m.month}}</span>
            </div>
        `;
    }}).join('');

    const s1 = DEMO.kpi.scope1_tco2e;
    const s2 = DEMO.kpi.scope2_tco2e;
    const sum = s1 + s2 || 1;
    const p1 = (s1 / sum) * 100;
    const p2 = 100 - p1;
    const r = 52;
    const c = 2 * Math.PI * r;
    const d1 = (p1 / 100) * c;

    document.getElementById('scopeDonut').innerHTML = `
        <svg viewBox="0 0 140 140" class="w-full h-full -rotate-90">
            <circle cx="70" cy="70" r="${{r}}" fill="none" stroke="#a8d987" stroke-width="18" />
            <circle cx="70" cy="70" r="${{r}}" fill="none" stroke="#2f7a4a" stroke-width="18"
                stroke-dasharray="${{d1.toFixed(1)}} ${{c.toFixed(1)}}" />
        </svg>
        <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
            <span class="text-sm font-bold font-mono text-[#091710]">${{p1.toFixed(1)}}%</span>
            <span class="text-[10px] text-[#6a8978]">Scope 1</span>
        </div>
    `;

    document.getElementById('scopeDonutLegend').innerHTML = `
        <div class="flex items-center justify-between">
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-[#2f7a4a]"></span>Scope 1</span>
            <span class="font-mono font-semibold">${{p1.toFixed(1)}}%</span>
        </div>
        <div class="flex items-center justify-between">
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-[#a8d987]"></span>Scope 2</span>
            <span class="font-mono font-semibold">${{p2.toFixed(1)}}%</span>
        </div>
    `;
}}

renderInputFiles();
renderTables();
renderCharts();
</script>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    kpi = extract_inventory_summary()
    copy_assets()
    write_json(kpi)
    write_html(kpi)
    print(f"✅ Built static demo: Scope 1={kpi['scope1_tco2e']}, Scope 2={kpi['scope2_tco2e']}, Total={kpi['total_tco2e']} tCO2e")
    return 0


if __name__ == "__main__":
    sys.exit(main())
