---
name: ecostream
description: Kiểm kê khí nhà kính cấp cơ sở (Scope 1/2) từ chứng từ: tạo biểu khảo sát, tính phát thải, xuất workbook kiểm kê và báo cáo Word dự thảo.
user-invocable: true
disable-model-invocation: false
---

# EcoStream: luồng khảo sát Scope 1/2

Đọc chứng từ có lớp chữ (Excel, Word, CSV, PDF), tạo biểu khảo sát, tính phát thải Scope 1 và 2 từ biểu đã rà soát, rồi xuất workbook kiểm kê và báo cáo Word dự thảo. Không dùng AI bên ngoài; phép tính là tất định.

## Cách dùng
- `/ecostream --demo`: chạy dữ liệu mẫu `data/samples/input.xlsx`.
- `/ecostream --input <file_or_dir> --company "Tên" --facility "Nhà máy" --year 2026`: chạy trên chứng từ thật.
- `/ecostream --run-id <run_id> --reviewed <Bang_khao_sat.xlsx>`: tính lại sau khi đã rà soát biểu.

## Quy trình
1. Phân tích tham số từ lệnh gọi.
2. Chạy đúng một lệnh:
   ```bash
   python -m ecostream --demo
   python -m ecostream --input $ARGUMENTS
   python -m ecostream --run-id <run_id> --reviewed <file>
   ```
3. Kiểm tra ba tệp trong `runs/<run_id>/deliverables/`:
   - `Bang_khao_sat_da_dien.xlsx`
   - `GHGs_inventory_da_tinh.xlsx`
   - `Bao_cao_kiem_ke_KNK.docx`
4. Trình bày tổng Scope 1, Scope 2, tổng và mức độ tin cậy, cùng toàn bộ cảnh báo trong kết quả. Scope 3 nằm ngoài phạm vi và phải được nêu rõ là chưa tính.
