import os, re

p = '/home/oanh/cccccccccccccc/ecostream/app/static/index.html'
with open(p, 'r', encoding='utf-8') as f: c = f.read()

# Left Nav
c = c.replace('📚</span>\n                        Nội quy kiểm kê', 'Nội Quy Kiểm Kê (Guidelines)')
c = c.replace('⚖️</span>\n                        Hệ số phát thải', 'Hệ Số Phát Thải (Emission Factors)')
c = c.replace('⚡</span>\n                        Kiểm thử tự động', 'Kiểm Thử Tự Động (Auto-benchmark)')
c = c.replace('🧮</span>\n                        Kiểm kê & Tính toán', 'Kiểm Kê & Tính Toán (Carbon Accounting)')
c = c.replace('📡</span>\n                        Live Monitor', 'Giám Sát Trực Tiếp (Live Monitor)')

# Buttons
c = c.replace('📤 Tải Lên Chứng Từ / Excel Mới', 'Tải Lên Chứng Từ Mới (Upload Documents)')
c = c.replace('🚀 Khởi Chạy Pipeline Đa Tác Tử', 'Tính Toán Lượng Phát Thải (Calculate Emissions)')

# Tabs
c = c.replace('📊 Kiểm Kê Khí Nhà Kính & Bằng Chứng', 'Bảng Kiểm Kê & Bằng Chứng (Inventory & Evidence)')
c = c.replace('🔍 Dấu Vết Kiểm Toán (Query & Assumption Logs)', 'Dấu Vết Kiểm Toán (Audit Logs)')

# Remove emoji tags in pills
c = re.sub(r'<span class="text-lg">.*?</span>', '', c)
c = c.replace('<span>📄</span>', '')
c = c.replace('🏢 Cơ Sở Kiểm Kê & Giảm Nhẹ Trọng Điểm', 'Cơ Sở Trọng Điểm (Target Facility)')
c = c.replace('✨ Mẹo', 'Mẹo (Tip)')
c = c.replace('✅</span> 1. Phạm vi tính toán hiện tại', '1. Phạm vi tính toán hiện tại (Calculation Scope)')
c = c.replace('🛡️</span> 2. Bảo mật dữ liệu & PII Masking', '2. Bảo mật dữ liệu (Data Security & Masking)')
c = c.replace('⚙️</span> 3. Quy trình tính toán kiểm chứng', '3. Quy trình tính toán kiểm chứng (Audit Tracking)')
c = c.replace('📤</span>', '')
c = re.sub(r'<span class="text-4xl mb-3 block">.*?</span>', '', c)

with open(p, 'w', encoding='utf-8') as f: f.write(c)
print("UI patched")
