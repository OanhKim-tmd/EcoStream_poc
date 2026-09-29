---
name: mitigation
description: Generate Decree 06/2022/NĐ-CP Mẫu 02 GHG Mitigation Plan & Results and Quota Compliance Report.
user-invocable: true
disable-model-invocation: false
---

# Báo Cáo Kế Hoạch & Kết Quả Giảm Nhẹ Phát Thải KNK (Mẫu số 02 Phụ lục III NĐ 06/2022/NĐ-CP)

Evaluate facility-level mitigation projects, calculate baseline emissions ($PT_{CS}$), actual emissions ($PT$), emission reductions ($GPT = PT_{CS} - PT$), and compare against allocated carbon quotas.

## Usage
- `/mitigation --demo`
- `/mitigation --input data/samples/input.xlsx`
- `/mitigation --run-id <run_id>`

## Procedure
1. Execute the pipeline:
   ```bash
   python -m ecostream.cli $ARGUMENTS
   ```
2. Display the Mẫu 02 table with columns:
   - STT, Tên biện pháp giảm nhẹ, Lĩnh vực
   - $PT_{CS}$ (Phát thải cơ sở), $PT$ (Phát thải thực tế), $GPT$ (Mức giảm phát thải)
   - Tỷ lệ giảm (%), Phương pháp đo đếm giám sát
3. Display the Quota balance profile ($Quota_{alloc}$, Net compliance emissions, Quota balance surplus/deficit).
