# Bài viết ngắn — NimbusAI GPU FinOps

Nguyễn Quang Huy — MSSV 2A202602820

## 1. Baseline và Optimized

Trên dữ liệu synthetic seed cố định, baseline $27,133/tháng, optimized $14,636/tháng; projected savings $12,497 (46.06%). Inference 7,533,027 token/ngày: $48.87 → $8.82; $/1M-token 6.488 → 1.170. M2 sau tính phí ghi khác bản gốc $8,48/ngày. M3 và M5 quy đổi tháng 30 ngày; carbon dùng ngày job thực tế.

## 2. Đóng góp từng đòn bẩy

Purchasing (spot/reserved) lớn nhất: $10,040/tháng vì baseline GPU workloads lớn hơn nhiều API traffic. Purchasing tiết kiệm 39.1%; inference tiết kiệm 82.0%. Cascade là nguồn giảm lớn nhất trong M2; cache và batch tiếp tục giảm bill theo thứ tự, phí ghi cache làm tăng nhẹ chi phí. Bảng từng bước và bốn khoản savings nằm trong report.md.

## 3. GPU-Util Lie

H100-4 util 98,2% nhưng MFU 19,4%; A10G-1 util 96,9% nhưng MFU 26,8%. Kernel có thể bận với memory stall/I/O chứ không đạt compute peak. Hạ H100→A100 và A10G→L4 có tiềm năng $655/tháng; tắt 8 giờ idle/ngày của H100-5 tiết kiệm $600/tháng. Chưa có VRAM/throughput benchmark nên đây là giả thuyết. Telemetry không nối với job_id; tổng lab có khả năng cộng trùng purchasing, right-sizing và idle. Không coi ước tính này là khoản tiền đã thu hồi.

## 4. Hai extension

**Cache có phí ghi:** thêm cache_is_worth_it và cache_break_even_reads; gate trước cache, dùng chung hàm tính tiền cho M2/M4. Giả định incremental write 1,25× input, 5 reads/prefix, không giảm write theo batch. Hòa vốn 1,3889 reads realtime và 2,7778 batch. Một read: tắt cache; năm reads: bật. Trước ghi $8.4846/ngày; sau $8.8170. Token/output/model route giữ nguyên. CSV thiếu prefix/read count nên cần đo hit rate và TTL thực tế trước áp dụng.

**Carbon scheduling:** thêm mission carbon_scheduling, tích hợp bảng vào M5. Wh bằng watts catalog nhân GPU-hours, chỉ job interruptible; cùng lượng công việc, ngày thực tế. Chuyển us-east-1→europe-north1 giảm 626,150.00 gCO2e (92,11%). europe-north1 sạch nhất nhưng us-east-wa điện rẻ nhất. Đây là điện GPU theo công suất catalog, thiếu PUE và rework; không cộng điện vào bill thuê GPU. Cần kiểm tra GPU availability, dữ liệu và SLA trước chuyển vùng.

## 5. Ba hành động đầu tiên

1. Đo chất lượng và latency cascade trên tập đánh giá; bật cache có gate theo reuse thực tế và batch cho offline. Purchasing là khoản lớn nhất, nhưng phải xác minh thời hạn nhu cầu trước reserved 3 năm, checkpoint trước Spot.
2. Profiling hai util-lies, đo VRAM và benchmark GPU thay thế; tự động tắt idle và nối telemetry với job_id để loại cộng trùng savings.
3. Thiết lập owner/team/project bắt buộc và budget cảnh báo; lập lịch job interruptible ở vùng sạch nếu đáp ứng SLA. Team assistant đang cao nhất $2.77/ngày (~31.4%); coverage 91.8% qua gate 80%, vẫn cần sửa tag thiếu và phân bổ nốt.

Bảng đo chi tiết: outputs/report.md; bản trước sửa: outputs/before/. Giá/carbon là giả định lab, không phải giá thị trường hiện tại.
