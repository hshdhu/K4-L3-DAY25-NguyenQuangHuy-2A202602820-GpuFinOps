# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,636  
**Projected savings:** $12,497  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,202 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cleanest region: europe-north1

_Figures are June-2026 as-of snapshots; re-baseline before acting._

## Phạm vi và giả định

Dữ liệu synthetic seed cố định từ data/generate.py; giá và carbon là snapshot minh họa của lab, không phải báo giá thị trường. M2 là một ngày traffic, M3/M5 dùng tháng 30 ngày; extension carbon dùng days thực tế trong CSV.
Tổng M5 giữ cách cộng bốn đòn bẩy của lab. Telemetry chưa liên kết job_id nên right-sizing và idle có thể chồng lấn purchasing; đây là tiềm năng dự kiến, chưa phải tiết kiệm thực thu. Hạ GPU cần kiểm tra VRAM và benchmark throughput/latency.

## Inference: từng bước trên cùng số token

| Bước | USD/ngày | USD/1M-token | Giảm so bước trước USD |
|---|---:|---:|---:|
| baseline | 48.8742 | 6.4880 | 0.0000 |
| cascade | 11.4756 | 1.5234 | 37.3985 |
| cache_no_write | 10.2792 | 1.3645 | 1.1965 |
| batch_no_write | 8.4846 | 1.1263 | 1.7946 |
| with_write | 8.8170 | 1.1704 | -0.3323 |

## Extension 3: cache có phí ghi

CSV không có prefix_id hoặc reads/write. Giả định mỗi prefix có 5 reads; phí ghi tăng thêm 1,25 lần giá input, phân bổ đều trên reads. Không giảm phí ghi theo batch; giữ nguyên token/output/model route. Không tính storage TTL vì thiếu dữ liệu.
Hòa vốn: reads = write_rate / [input_rate × (1 − 0,10)]. Ngưỡng 1,3889 reads cho realtime và 2,7778 cho batch (tiết kiệm đọc bị nhân 0,50). Chỉ bật cache khi vượt ngưỡng; ngưỡng bằng nhau thì tắt.

| Reads giả định | Cache | USD/ngày sau gate + write | USD/1M-token |
|---:|---|---:|---:|
| 1 | Tắt | 9.6586 | 1.2822 |
| 5 | Bật | 8.8170 | 1.1704 |

Trước tính phí ghi: $8.4846/ngày; sau: $8.8170/ngày. Phí ghi làm tăng $0.3323/ngày. Insight: cache không miễn phí; một read chưa bù chi phí ghi, năm reads vẫn tiết kiệm. M4 dùng cùng hàm tính giá để phân bổ phí ghi theo team.

## Extension 5: Carbon-aware Scheduling

Wh = watts catalog × GPU-hours. Giữ nguyên lượng công việc, watts, số GPU; dùng days thực tế. Đây là mô hình điện GPU theo công suất catalog, chưa gồm PUE/CPU/network hoặc rework Spot. Giả định vùng đích có GPU tương đương, đáp ứng residency và latency. Chi phí điện là thành phần minh họa, không cộng vào GPU bill hoặc savings M5.

| Job | GPU-hours | Wh | us-east-1 gCO2e | europe-north1 gCO2e | Giảm gCO2e |
|---|---:|---:|---:|---:|---:|
| job-train-llm | 2240 | 1568000 | 595840.00 | 47040.00 | 548800.00 |
| job-train-embed | 200 | 80000 | 30400.00 | 2400.00 | 28000.00 |
| job-finetune | 36 | 25200 | 9576.00 | 756.00 | 8820.00 |
| job-dev-sandbox | 352 | 52800 | 20064.00 | 1584.00 | 18480.00 |
| job-batch-eval | 90 | 63000 | 23940.00 | 1890.00 | 22050.00 |

| Vùng | USD/kWh | gCO2e/kWh | gCO2e tổng | Điện USD tổng |
|---|---:|---:|---:|---:|
| us-east-1 | 0.120 | 380 | 679820.00 | 214.6800 |
| us-west-2 | 0.070 | 120 | 214680.00 | 125.2300 |
| europe-north1 | 0.090 | 30 | 53670.00 | 161.0100 |
| europe-central2 | 0.180 | 660 | 1180740.00 | 322.0200 |
| us-east-wa | 0.055 | 90 | 161010.00 | 98.3950 |

Phương án cân bằng trong bảng là us-east-wa: điện rẻ nhất và carbon thấp thứ hai; europe-north1 ưu tiên carbon. Cần đo latency: vùng sạch xa users có thể làm tăng thời gian truyền dữ liệu và vi phạm SLA.

| Model tier | Input USD/1M | Write USD/1M | Reads hòa vốn realtime | Reads hòa vốn batch |
|---|---:|---:|---:|---:|
| small | 0.20 | 0.25 | 1.3889 | 2.7778 |
| large | 3.00 | 3.75 | 1.3889 | 2.7778 |
Ngưỡng hai model giống nhau do write được giả định tỷ lệ với giá input. Dataset không cho biết reuse thực tế nên chưa thể khẳng định traffic thực đã vượt ngưỡng.

Tổng giảm 626,150.00 gCO2e (92,11%) khi chuyển từ us-east-1 sang europe-north1. Vùng sạch nhất: europe-north1; điện rẻ nhất: us-east-wa. Chọn theo mục tiêu carbon hoặc điện, không đồng nhất hai tiêu chí.

## GPU-Util lie và allocation

| GPU | Util % | MFU | MBU |
|---|---:|---:|---:|
| gpu-h100-4 | 98.2 | 0.194 | 0.207 |
| gpu-a10g-1 | 96.9 | 0.268 | 0.302 |

Idle: $20.00/ngày, $600/tháng (2.21% baseline). Right-sizing dự kiến $655/tháng: H100 → A100 $511,20; A10G → L4 $144. Util cao chỉ cho biết có kernel hoạt động; memory stall, I/O hoặc kernel nhỏ có thể làm MFU thấp. Cần profiling để xác nhận nguyên nhân.

| Team | USD/ngày (gồm write) |
|---|---:|
| assistant | 2.77 |
| search | 2.51 |
| eval | 1.81 |
| rag | 1.73 |

Tag coverage 91.8%, vượt gate 80%; chargeback ready = True. Cần sửa request thiếu tag trước chargeback đầy đủ. focus_export.csv chỉ là mẫu 50 request, không phải toàn bộ bill. FOCUS chuẩn hóa cột tiền/tags giữa các provider để so sánh và tổng hợp.

## Trả lời phân tích Guide.md

- 4.3: gpu-h100-4 util cao nhất 98,2%, MFU 0,194. GPU bận không đồng nghĩa compute peak. Idle là $600/tháng, tỷ trọng đã tính ở trên.
- 5.4: Cascade đóng góp lớn nhất trong inference: $37.3985/ngày. Cache thêm $1.1965, batch thêm $1.7946 trước phí ghi. 0,50 × 0,10 = 0,05 chỉ đúng cached input; output vẫn chịu giá riêng. Batch phù hợp offline, không phù hợp chat cần phản hồi tức thì.
- 6.4: Spot cho train-llm, train-embed, finetune, dev-sandbox, batch-eval vì interruptible và không chạy 24/7. Effective hours tăng do checkpoint và rework. Reserved cho infer-chat/rag/search; các job chỉ có 30 ngày nên cần chứng minh nhu cầu dài hạn trước cam kết 3 năm. Với search 18h/ngày, phải tính tiền cam kết cả giờ không chạy; M3 gốc chưa mô hình phần này.
- 7.4: Team cao nhất và tỷ trọng được ghi trong bài viết. Coverage vượt gate nhưng không chứng minh mọi tag chính xác. FOCUS giúp so sánh bill đa cloud theo cùng schema.

## Validation và tái lập

Kết quả trước sửa lưu ở outputs/before/baseline.json và các artifact before/. Chạy python verify.py, python -m pytest -q; verify sinh lại dữ liệu và toàn bộ báo cáo mở rộng. Không sửa tests/.