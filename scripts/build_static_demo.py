#!/usr/bin/env python3
"""
build_static_demo.py
Copies pre-computed demo data from data/demo_full_2026/ into docs/demo-assets/
and generates docs/demo-data.json + docs/index.html for GitHub Pages.

Usage:
    python scripts/build_static_demo.py
"""

import json
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SRC  = REPO_ROOT / "data" / "demo_full_2026"
DOCS_DIR  = REPO_ROOT / "docs"
ASSETS_DIR = DOCS_DIR / "demo-assets"

# ---------------------------------------------------------------------------
# Hard-coded KPIs (from actual pipeline run on demo_full_2026 data)
# Update these values after each fresh pipeline run if needed.
# ---------------------------------------------------------------------------
DEMO_KPI = {
    "company":    "Nhà máy May & Năng lượng Hà Nam — Công ty CP May mặc EcoGarment Việt Nam",
    "facility":   "KCN Đồng Văn III, TX. Duy Tiên, Hà Nam",
    "year":       2026,
    "scope1_tco2e":   48.72,
    "scope2_tco2e":  312.56,
    "total_tco2e":   361.28,
    "ci_lower":      344.10,
    "ci_upper":      378.46,
    "reliability":   "A",
    "confidence_pct": 92.4,
    "note": "Phạm vi 3 không được tính trong phiên bản hiện tại",
}

# ---------------------------------------------------------------------------
# Input files to showcase (relative to DEMO_SRC)
# ---------------------------------------------------------------------------
INPUT_FILES = [
    {
        "name": "Hóa đơn điện EVN (PDF)",
        "filename": "electricity_month_01.pdf",
        "type": "PDF",
        "icon": "⚡",
        "desc": "Hóa đơn điện tháng 1/2026 — 12 tháng được xử lý tổng hợp",
    },
    {
        "name": "Dữ liệu điện tháng 2–12 (CSV)",
        "filename": "electricity_months_02_12.csv",
        "type": "CSV",
        "icon": "📊",
        "desc": "Tiêu thụ điện tháng 2–12/2026 từ hóa đơn số hóa",
    },
    {
        "name": "Nhiên liệu cố định (Excel)",
        "filename": "fuel_stationary.xlsx",
        "type": "XLSX",
        "icon": "🔥",
        "desc": "Diesel & gas cho máy phát và lò hơi — Phạm vi 1",
    },
    {
        "name": "Nhiên liệu di động (Word)",
        "filename": "fuel_mobile.docx",
        "type": "DOCX",
        "icon": "🚛",
        "desc": "Xăng dầu xe tải & xe nâng — Phạm vi 1",
    },
    {
        "name": "Dữ liệu giả lập tổng hợp (Excel)",
        "filename": "du_lieu_gia_lap_full_2026.xlsx",
        "type": "XLSX",
        "icon": "📋",
        "desc": "Tổng hợp 12 tháng: điện, nhiên liệu, nước thải",
    },
]

# ---------------------------------------------------------------------------
# Output files (pre-computed, copied to docs/demo-assets/)
# ---------------------------------------------------------------------------
OUTPUT_FILES = [
    {
        "name": "Biểu khảo sát đã điền",
        "filename": "Bang_khao_sat_da_dien.xlsx",
        "type": "XLSX",
        "icon": "📗",
        "desc": "Mẫu khảo sát ISO 14064-1 đã điền đầy đủ",
    },
    {
        "name": "Kết quả kiểm kê GHG (Excel)",
        "filename": "GHGs_inventory_da_tinh.xlsx",
        "type": "XLSX",
        "icon": "📊",
        "desc": "Phát thải Phạm vi 1 & 2 theo tháng, có khoảng bất định",
    },
    {
        "name": "Báo cáo kiểm kê KNK (Word)",
        "filename": "Bao_cao_kiem_ke_KNK.docx",
        "type": "DOCX",
        "icon": "📄",
        "desc": "Báo cáo Mẫu 02 — theo Nghị định 06/2022/NĐ-CP",
    },
]

# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------
PIPELINE_STEPS = [
    {
        "icon": "📂",
        "title": "Nạp chứng từ",
        "desc": "OCR + trích xuất tự động từ PDF, Excel, CSV, Word",
    },
    {
        "icon": "📝",
        "title": "Điền biểu khảo sát",
        "desc": "Tự động điền Mẫu Khảo sát ISO 14064-1",
    },
    {
        "icon": "⚙️",
        "title": "Tính toán phát thải",
        "desc": "Phương pháp tất định + ước lượng khoảng bất định 95% CI",
    },
    {
        "icon": "📋",
        "title": "Xuất hồ sơ",
        "desc": "Excel kiểm kê, Báo cáo Word Mẫu 02, HTML & PDF",
    },
]


def ensure_dirs():
    DOCS_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    print(f"✅ Thư mục: {DOCS_DIR} / {ASSETS_DIR}")


def copy_assets():
    """Copy both input + output demo files into docs/demo-assets/"""
    all_files = INPUT_FILES + OUTPUT_FILES
    copied, missing = [], []
    for f in all_files:
        src = DEMO_SRC / f["filename"]
        dst = ASSETS_DIR / f["filename"]
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(f["filename"])
        else:
            missing.append(f["filename"])

    # Also copy the QR code if it exists
    qr_src = DOCS_DIR / "demo-qr.png"
    if qr_src.exists():
        print(f"  ℹ️  QR code already in docs/: {qr_src.name}")

    if missing:
        print(f"⚠️  Không tìm thấy: {missing}")
    print(f"✅ Copied {len(copied)} assets → {ASSETS_DIR}")


def write_json():
    data = {
        "kpi": DEMO_KPI,
        "input_files": INPUT_FILES,
        "output_files": OUTPUT_FILES,
        "pipeline_steps": PIPELINE_STEPS,
    }
    out = DOCS_DIR / "demo-data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ JSON: {out}")


def write_html():
    """Generate docs/index.html — the static demo page."""
    scope1 = DEMO_KPI["scope1_tco2e"]
    scope2 = DEMO_KPI["scope2_tco2e"]
    total  = DEMO_KPI["total_tco2e"]
    ci_lo  = DEMO_KPI["ci_lower"]
    ci_hi  = DEMO_KPI["ci_upper"]
    grade  = DEMO_KPI["reliability"]
    conf   = DEMO_KPI["confidence_pct"]
    year   = DEMO_KPI["year"]
    company = DEMO_KPI["company"]
    facility = DEMO_KPI["facility"]

    # --- Input file cards HTML
    def input_card(f):
        return f"""
        <div class="file-card">
          <div class="file-icon">{f['icon']}</div>
          <div class="file-info">
            <div class="file-name">{f['name']}</div>
            <div class="file-desc">{f['desc']}</div>
            <span class="file-badge">{f['type']}</span>
          </div>
        </div>"""

    input_cards = "\n".join(input_card(f) for f in INPUT_FILES)

    # --- Pipeline steps HTML
    def step_card(s, i):
        return f"""
        <div class="step-card">
          <div class="step-num">{i+1}</div>
          <div class="step-icon">{s['icon']}</div>
          <div class="step-title">{s['title']}</div>
          <div class="step-desc">{s['desc']}</div>
        </div>"""

    step_cards = "\n".join(step_card(s, i) for i, s in enumerate(PIPELINE_STEPS))

    # --- Output download buttons HTML
    def dl_btn(f):
        return f"""
        <a class="dl-btn" href="demo-assets/{f['filename']}" download>
          <span class="dl-icon">{f['icon']}</span>
          <span class="dl-info">
            <span class="dl-name">{f['name']}</span>
            <span class="dl-type">{f['type']}</span>
          </span>
          <span class="dl-arrow">↓</span>
        </a>"""

    dl_btns = "\n".join(dl_btn(f) for f in OUTPUT_FILES)

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="description" content="EcoStream — Demo kiểm kê phát thải khí nhà kính tự động cho doanh nghiệp vừa và nhỏ"/>
  <title>EcoStream — Demo Kiểm Kê KNK {year}</title>
  <link rel="icon" type="image/svg+xml" href="favicon.svg"/>
  <style>
    :root {{
      --green-dark:  #003c33;
      --green-mid:   #2c4a3c;
      --lime:        #9fe870;
      --lime-dark:   #7bc94e;
      --bg:          #f5f9f4;
      --bg2:         #e8f3e4;
      --text:        #091710;
      --text-muted:  #4a6b5a;
      --border:      #cce5c0;
      --card-bg:     #ffffff;
      --radius:      12px;
      --radius-lg:   20px;
      --shadow:      0 2px 12px rgba(0,60,51,.10);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}

    /* ---- HEADER ---- */
    header {{
      background: var(--green-dark);
      color: white;
      padding: 20px 20px 28px;
      text-align: center;
      position: relative;
    }}
    .logo-row {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      margin-bottom: 6px;
    }}
    .logo-icon {{
      width: 44px; height: 44px;
      background: var(--lime);
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 22px;
    }}
    .logo-text {{ font-size: 1.9rem; font-weight: 800; letter-spacing: -.5px; }}
    .logo-text span {{ color: var(--lime); }}
    .tagline {{ font-size: .8rem; color: #cce5c0; letter-spacing: 2px; text-transform: uppercase; }}
    .demo-badge {{
      display: inline-block;
      background: rgba(159,232,112,.18);
      border: 1px solid rgba(159,232,112,.4);
      color: var(--lime);
      border-radius: 20px;
      padding: 4px 14px;
      font-size: .75rem;
      margin-top: 10px;
      letter-spacing: .5px;
    }}
    .header-company {{
      margin-top: 14px;
      background: rgba(255,255,255,.08);
      border-radius: var(--radius);
      padding: 10px 16px;
      font-size: .85rem;
      color: #d0e8d0;
    }}
    .header-company strong {{ color: white; display: block; font-size: .95rem; }}

    /* ---- SECTION ---- */
    section {{ padding: 24px 16px; max-width: 540px; margin: 0 auto; }}
    .section-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--green-dark);
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .section-title::after {{
      content: '';
      flex: 1;
      height: 2px;
      background: var(--border);
      border-radius: 1px;
    }}

    /* ---- INPUT FILE CARDS ---- */
    .file-card {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 12px 14px;
      margin-bottom: 10px;
      box-shadow: var(--shadow);
    }}
    .file-icon {{ font-size: 1.6rem; flex-shrink: 0; margin-top: 2px; }}
    .file-name {{ font-weight: 600; font-size: .9rem; color: var(--text); }}
    .file-desc {{ font-size: .78rem; color: var(--text-muted); margin: 2px 0 6px; }}
    .file-badge {{
      background: var(--bg2);
      color: var(--green-mid);
      border-radius: 6px;
      padding: 1px 8px;
      font-size: .7rem;
      font-weight: 600;
    }}

    /* ---- PIPELINE STEPS ---- */
    .steps-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .step-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px 12px;
      text-align: center;
      position: relative;
      box-shadow: var(--shadow);
    }}
    .step-num {{
      position: absolute;
      top: -1px; left: -1px;
      background: var(--green-dark);
      color: var(--lime);
      font-size: .65rem;
      font-weight: 800;
      width: 22px; height: 22px;
      border-radius: var(--radius) 0 var(--radius) 0;
      display: flex; align-items: center; justify-content: center;
    }}
    .step-icon {{ font-size: 1.5rem; margin-bottom: 6px; }}
    .step-title {{ font-weight: 700; font-size: .85rem; color: var(--green-dark); margin-bottom: 4px; }}
    .step-desc {{ font-size: .72rem; color: var(--text-muted); line-height: 1.4; }}

    /* ---- KPI CARDS ---- */
    .kpi-main {{
      background: var(--green-dark);
      border-radius: var(--radius-lg);
      padding: 20px;
      text-align: center;
      color: white;
      margin-bottom: 10px;
      box-shadow: 0 4px 20px rgba(0,60,51,.25);
    }}
    .kpi-main-label {{ font-size: .8rem; color: #cce5c0; letter-spacing: .5px; margin-bottom: 4px; }}
    .kpi-main-value {{
      font-size: 2.6rem;
      font-weight: 800;
      color: var(--lime);
      line-height: 1;
    }}
    .kpi-main-unit {{ font-size: .9rem; color: #9ed4c0; margin: 4px 0 8px; }}
    .kpi-ci {{
      background: rgba(255,255,255,.1);
      border-radius: 8px;
      padding: 6px 12px;
      font-size: .75rem;
      color: #cce5c0;
      display: inline-block;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1.5px solid var(--border);
      border-radius: var(--radius);
      padding: 12px 8px;
      text-align: center;
      box-shadow: var(--shadow);
    }}
    .kpi-card-label {{ font-size: .7rem; color: var(--text-muted); margin-bottom: 4px; line-height: 1.3; }}
    .kpi-card-value {{ font-size: 1.25rem; font-weight: 800; color: var(--green-dark); }}
    .kpi-card-unit {{ font-size: .65rem; color: var(--text-muted); }}
    .grade-pill {{
      display: inline-block;
      background: var(--lime);
      color: var(--green-dark);
      border-radius: 20px;
      padding: 2px 14px;
      font-size: 1.1rem;
      font-weight: 800;
    }}
    .kpi-note {{
      font-size: .72rem;
      color: var(--text-muted);
      text-align: center;
      margin-top: 8px;
      font-style: italic;
    }}

    /* ---- DOWNLOAD ---- */
    .dl-btn {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: var(--card-bg);
      border: 1.5px solid var(--border);
      border-radius: var(--radius);
      padding: 13px 14px;
      margin-bottom: 9px;
      text-decoration: none;
      color: var(--text);
      box-shadow: var(--shadow);
      transition: border-color .2s, box-shadow .2s;
    }}
    .dl-btn:hover {{
      border-color: var(--lime-dark);
      box-shadow: 0 4px 16px rgba(0,60,51,.15);
    }}
    .dl-icon {{ font-size: 1.5rem; flex-shrink: 0; }}
    .dl-info {{ flex: 1; }}
    .dl-name {{ font-weight: 600; font-size: .9rem; display: block; }}
    .dl-type {{
      font-size: .7rem;
      background: var(--bg2);
      color: var(--green-mid);
      padding: 1px 7px;
      border-radius: 5px;
      font-weight: 600;
    }}
    .dl-arrow {{
      font-size: 1.2rem;
      color: var(--lime-dark);
      font-weight: 700;
    }}

    /* ---- FOOTER ---- */
    footer {{
      background: var(--green-dark);
      color: #9ed4c0;
      text-align: center;
      padding: 24px 20px;
      font-size: .8rem;
      margin-top: 10px;
    }}
    footer a {{ color: var(--lime); text-decoration: none; }}
    .footer-logo {{
      font-size: 1.2rem;
      font-weight: 800;
      color: white;
      margin-bottom: 6px;
    }}
    .footer-logo span {{ color: var(--lime); }}

    /* ---- SECTION DIVIDER ---- */
    .section-divider {{
      height: 6px;
      background: linear-gradient(90deg, var(--green-dark) 0%, var(--lime) 100%);
      opacity: .15;
    }}

    /* ---- DISCLAIMER ---- */
    .disclaimer {{
      background: #fff8e1;
      border-left: 3px solid #f59e0b;
      border-radius: 0 var(--radius) var(--radius) 0;
      padding: 10px 14px;
      font-size: .75rem;
      color: #78350f;
      margin-bottom: 10px;
    }}

    @media (max-width: 360px) {{
      .kpi-main-value {{ font-size: 2rem; }}
      .steps-grid {{ grid-template-columns: 1fr; }}
      .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="logo-row">
    <div class="logo-icon">🌱</div>
    <div class="logo-text">ECO<span>Stream</span></div>
  </div>
  <div class="tagline">Measure · Optimize · Go Greener</div>
  <div class="demo-badge">🎯 Phiên bản Demo — Dữ liệu mẫu {year}</div>
  <div class="header-company">
    <strong>{company}</strong>
    📍 {facility}
  </div>
</header>

<!-- SECTION 1: INPUT FILES -->
<section>
  <div class="section-title">📂 Chứng từ đầu vào</div>
  {input_cards}
</section>

<div class="section-divider"></div>

<!-- SECTION 2: PIPELINE -->
<section>
  <div class="section-title">⚙️ Quy trình xử lý</div>
  <div class="steps-grid">
    {step_cards}
  </div>
</section>

<div class="section-divider"></div>

<!-- SECTION 3: KPI RESULTS -->
<section>
  <div class="section-title">📈 Kết quả kiểm kê {year}</div>

  <div class="disclaimer">
    ⚠️ Dữ liệu demo — chỉ bao gồm <strong>Phạm vi 1 & 2</strong>. Phạm vi 3 không được tính trong phiên bản hiện tại.
  </div>

  <div class="kpi-main">
    <div class="kpi-main-label">TỔNG PHÁT THẢI KHÍ NHÀ KÍNH</div>
    <div class="kpi-main-value">{total:,.2f}</div>
    <div class="kpi-main-unit">tCO₂e · Phạm vi 1 + 2</div>
    <div class="kpi-ci">📊 Khoảng bất định 95% CI: {ci_lo:,.1f} – {ci_hi:,.1f} tCO₂e</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-card-label">Phạm vi 1<br/>(Phát thải trực tiếp)</div>
      <div class="kpi-card-value">{scope1:,.2f}</div>
      <div class="kpi-card-unit">tCO₂e</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-card-label">Phạm vi 2<br/>(Điện mua ngoài)</div>
      <div class="kpi-card-value">{scope2:,.2f}</div>
      <div class="kpi-card-unit">tCO₂e</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-card-label">Độ tin cậy<br/>({conf}%)</div>
      <div class="kpi-card-value"><span class="grade-pill">{grade}</span></div>
      <div class="kpi-card-unit">Hạng</div>
    </div>
  </div>
  <div class="kpi-note">* Phương pháp tất định + Monte Carlo 10,000 vòng lặp</div>
</section>

<div class="section-divider"></div>

<!-- SECTION 4: DOWNLOADS -->
<section>
  <div class="section-title">📥 Tải hồ sơ đầu ra</div>
  {dl_btns}
</section>

<!-- FOOTER -->
<footer>
  <div class="footer-logo">ECO<span>Stream</span></div>
  <p>Nền tảng kiểm kê phát thải KNK tự động cho doanh nghiệp vừa và nhỏ</p>
  <p style="margin-top:8px">
    🌐 <a href="https://ecostream.vn">ecostream.vn</a>
    &nbsp;·&nbsp;
    📧 <a href="mailto:contact@ecostream.vn">contact@ecostream.vn</a>
  </p>
  <p style="margin-top:8px; font-size:.7rem; opacity:.7">
    © {year} EcoStream · Dữ liệu demo — không dùng cho mục đích thương mại
  </p>
</footer>

</body>
</html>
"""
    out = DOCS_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ HTML: {out}")


def copy_favicon():
    """Copy favicon.svg from static/ to docs/ if exists."""
    src = REPO_ROOT / "ecostream" / "app" / "static" / "favicon.svg"
    dst = DOCS_DIR / "favicon.svg"
    if src.exists():
        shutil.copy2(src, dst)
        print(f"✅ favicon.svg → docs/")


def main():
    print(f"\n🌱 EcoStream — Build Static Demo\n{'='*40}")
    ensure_dirs()
    copy_assets()
    write_json()
    write_html()
    copy_favicon()
    print(f"\n{'='*40}")
    print(f"✅ Xong! Mở docs/index.html trong browser để kiểm tra.")
    print(f"   Hoặc push lên GitHub để tự động deploy qua GitHub Actions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
