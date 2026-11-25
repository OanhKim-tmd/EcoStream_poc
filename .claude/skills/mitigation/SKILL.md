---
name: mitigation
description: Báo cáo kế hoạch và kết quả giảm nhẹ phát thải KNK (Mẫu số 02 Phụ lục III NĐ 06/2022). Hiện chỉ có công thức, chưa có luồng nhập liệu trên CLI.
user-invocable: true
disable-model-invocation: false
---

# Mẫu số 02: giảm nhẹ phát thải KNK

Công thức tính nằm trong `ecostream/engine/mitigation_math.py`: phát thải cơ sở (PT_CS), phát thải thực tế (PT), mức giảm (GPT = PT_CS − PT) và so sánh với hạn ngạch.

**Trạng thái hiện tại:** luồng khảo sát chưa nhập và tính biện pháp giảm nhẹ. Sheet "Biện pháp giảm thiểu" chỉ được đọc và ghi nguyên văn. Skill này không chạy được trên CLI, vì pipeline multi-agent đã bị gỡ.

## Khi làm tiếp
1. Thêm nguồn dữ liệu biện pháp giảm nhẹ vào biểu khảo sát.
2. Gọi `MitigationMathEngine.calculate_measure` từ `survey_pipeline.py`.
3. Đưa kết quả vào workbook và báo cáo Word theo Mẫu số 02.

Không báo cáo số giảm nhẹ hay trạng thái hạn ngạch khi chưa có dữ liệu và phương pháp được xác nhận.
