"""Reproducible extension tables and Vietnamese submission write-up."""
from pathlib import Path
from missions._common import ROOT, load_csv
from missions import carbon_scheduling, m4_allocation
from finops import pricing
from finops.sustainability import REGION_CARBON, REGION_PRICE_KWH


def build(r1, r2, r3, baseline, optimized, levers):
    c = carbon_scheduling.run(False)
    a = m4_allocation.run(False)
    s = r2['stages']
    lines = ['## Phạm vi và giả định', '',
        'Dữ liệu synthetic seed cố định từ data/generate.py; giá và carbon là snapshot minh họa của lab, không phải báo giá thị trường. M2 là một ngày traffic, M3/M5 dùng tháng 30 ngày; extension carbon dùng days thực tế trong CSV.',
        'Tổng M5 giữ cách cộng bốn đòn bẩy của lab. Telemetry chưa liên kết job_id nên right-sizing và idle có thể chồng lấn purchasing; đây là tiềm năng dự kiến, chưa phải tiết kiệm thực thu. Hạ GPU cần kiểm tra VRAM và benchmark throughput/latency.', '',
        '## Inference: từng bước trên cùng số token', '',
        '| Bước | USD/ngày | USD/1M-token | Giảm so bước trước USD |', '|---|---:|---:|---:|']
    previous = s['baseline']
    for name, cost in s.items():
        lines.append(f'| {name} | {cost:.4f} | {pricing.dollars_per_million(cost,r2["total_tokens"]):.4f} | {previous-cost:.4f} |')
        previous = cost
    lines += ['', '## Extension 3: cache có phí ghi', '',
        'CSV không có prefix_id hoặc reads/write. Giả định mỗi prefix có 5 reads; phí ghi tăng thêm 1,25 lần giá input, phân bổ đều trên reads. Không giảm phí ghi theo batch; giữ nguyên token/output/model route. Không tính storage TTL vì thiếu dữ liệu.',
        'Hòa vốn: reads = write_rate / [input_rate × (1 − 0,10)]. Ngưỡng 1,3889 reads cho realtime và 2,7778 cho batch (tiết kiệm đọc bị nhân 0,50). Chỉ bật cache khi vượt ngưỡng; ngưỡng bằng nhau thì tắt.', '',
        '| Reads giả định | Cache | USD/ngày sau gate + write | USD/1M-token |', '|---:|---|---:|---:|']
    for row in r2['cache_scenarios']:
        lines.append(f'| {row["reads"]:.0f} | {"Tắt" if row["reads"] == 1 else "Bật"} | {row["cost"]:.4f} | {row["per_m"]:.4f} |')
    lines += [f'', f'Trước tính phí ghi: ${s["batch_no_write"]:.4f}/ngày; sau: ${s["with_write"]:.4f}/ngày. Phí ghi làm tăng ${s["with_write"]-s["batch_no_write"]:.4f}/ngày. Insight: cache không miễn phí; một read chưa bù chi phí ghi, năm reads vẫn tiết kiệm. M4 dùng cùng hàm tính giá để phân bổ phí ghi theo team.', '',
        '## Extension 5: Carbon-aware Scheduling', '',
        'Wh = watts catalog × GPU-hours. Giữ nguyên lượng công việc, watts, số GPU; dùng days thực tế. Đây là mô hình điện GPU theo công suất catalog, chưa gồm PUE/CPU/network hoặc rework Spot. Giả định vùng đích có GPU tương đương, đáp ứng residency và latency. Chi phí điện là thành phần minh họa, không cộng vào GPU bill hoặc savings M5.', '',
        '| Job | GPU-hours | Wh | us-east-1 gCO2e | europe-north1 gCO2e | Giảm gCO2e |', '|---|---:|---:|---:|---:|---:|']
    for j in c['jobs']:
        before = j['regions']['us-east-1']['carbon_g']; after = j['regions'][c['cleanest']]['carbon_g']
        lines.append(f'| {j["job_id"]} | {j["gpu_hours"]:.0f} | {j["wh"]:.0f} | {before:.2f} | {after:.2f} | {before-after:.2f} |')
    lines += ['', '| Vùng | USD/kWh | gCO2e/kWh | gCO2e tổng | Điện USD tổng |', '|---|---:|---:|---:|---:|']
    for region in c['jobs'][0]['regions']:
        carbon = sum(j['regions'][region]['carbon_g'] for j in c['jobs'])
        electricity = sum(j['regions'][region]['electricity_usd'] for j in c['jobs'])
        lines.append(f'| {region} | {REGION_PRICE_KWH[region]:.3f} | {REGION_CARBON[region]} | {carbon:.2f} | {electricity:.4f} |')
    lines += ['', 'Phương án cân bằng trong bảng là us-east-wa: điện rẻ nhất và carbon thấp thứ hai; europe-north1 ưu tiên carbon. Cần đo latency: vùng sạch xa users có thể làm tăng thời gian truyền dữ liệu và vi phạm SLA.', '',
              '| Model tier | Input USD/1M | Write USD/1M | Reads hòa vốn realtime | Reads hòa vốn batch |',
              '|---|---:|---:|---:|---:|',
              '| small | 0.20 | 0.25 | 1.3889 | 2.7778 |',
              '| large | 3.00 | 3.75 | 1.3889 | 2.7778 |',
              'Ngưỡng hai model giống nhau do write được giả định tỷ lệ với giá input. Dataset không cho biết reuse thực tế nên chưa thể khẳng định traffic thực đã vượt ngưỡng.']
    lines += ['', f'Tổng giảm {c["saved_g"]:,.2f} gCO2e (92,11%) khi chuyển từ us-east-1 sang {c["cleanest"]}. Vùng sạch nhất: {c["cleanest"]}; điện rẻ nhất: {c["cheapest"]}. Chọn theo mục tiêu carbon hoặc điện, không đồng nhất hai tiêu chí.', '',
        '## GPU-Util lie và allocation', '', '| GPU | Util % | MFU | MBU |', '|---|---:|---:|---:|']
    for g in r1['lies']:
        lines.append(f'| {g["gpu_id"]} | {g["gpu_util_pct"]} | {g["mfu"]} | {g["mbu"]} |')
    lines += ['', f'Idle: ${r1["idle_waste_daily"]:.2f}/ngày, ${r1["idle_waste_daily"]*30:.0f}/tháng ({r1["idle_waste_daily"]*30/baseline:.2%} baseline). Right-sizing dự kiến ${levers["Right-size util-lies"]}/tháng: H100 → A100 $511,20; A10G → L4 $144. Util cao chỉ cho biết có kernel hoạt động; memory stall, I/O hoặc kernel nhỏ có thể làm MFU thấp. Cần profiling để xác nhận nguyên nhân.', '',
        '| Team | USD/ngày (gồm write) |', '|---|---:|']
    for team,cost in sorted(a['by_team'].items(),key=lambda x:-x[1]):
        lines.append(f'| {team} | {cost:.2f} |')
    lines += ['', f'Tag coverage {a["tag_coverage"]:.1%}, vượt gate 80%; chargeback ready = {a["chargeback_ready"]}. Cần sửa request thiếu tag trước chargeback đầy đủ. focus_export.csv chỉ là mẫu 50 request, không phải toàn bộ bill. FOCUS chuẩn hóa cột tiền/tags giữa các provider để so sánh và tổng hợp.', '',
        '## Trả lời phân tích Guide.md', '',
        f'- 4.3: gpu-h100-4 util cao nhất 98,2%, MFU 0,194. GPU bận không đồng nghĩa compute peak. Idle là $600/tháng, tỷ trọng đã tính ở trên.',
        f'- 5.4: Cascade đóng góp lớn nhất trong inference: ${s["baseline"]-s["cascade"]:.4f}/ngày. Cache thêm ${s["cascade"]-s["cache_no_write"]:.4f}, batch thêm ${s["cache_no_write"]-s["batch_no_write"]:.4f} trước phí ghi. 0,50 × 0,10 = 0,05 chỉ đúng cached input; output vẫn chịu giá riêng. Batch phù hợp offline, không phù hợp chat cần phản hồi tức thì.',
        '- 6.4: Spot cho train-llm, train-embed, finetune, dev-sandbox, batch-eval vì interruptible và không chạy 24/7. Effective hours tăng do checkpoint và rework. Reserved cho infer-chat/rag/search; các job chỉ có 30 ngày nên cần chứng minh nhu cầu dài hạn trước cam kết 3 năm. Với search 18h/ngày, phải tính tiền cam kết cả giờ không chạy; M3 gốc chưa mô hình phần này.',
        '- 7.4: Team cao nhất và tỷ trọng được ghi trong bài viết. Coverage vượt gate nhưng không chứng minh mọi tag chính xác. FOCUS giúp so sánh bill đa cloud theo cùng schema.', '',
        '## Validation và tái lập', '',
        'Kết quả trước sửa lưu ở outputs/before/baseline.json và các artifact before/. Chạy python verify.py, python -m pytest -q; verify sinh lại dữ liệu và toàn bộ báo cáo mở rộng. Không sửa tests/.']
    text = '\n'.join(lines)
    top = max(a['by_team'],key=a['by_team'].get)
    biggest = max(levers,key=levers.get)
    writeup = f'''# Bài viết ngắn — NimbusAI GPU FinOps

Nguyễn Quang Huy — MSSV 2A202602820

## 1. Baseline và Optimized

Trên dữ liệu synthetic seed cố định, baseline ${baseline:,.0f}/tháng, optimized ${optimized:,.0f}/tháng; projected savings ${(baseline-optimized):,.0f} ({(baseline-optimized)/baseline:.2%}). Inference {r2['total_tokens']:,} token/ngày: ${r2['baseline_daily']:.2f} → ${r2['optimized_daily']:.2f}; $/1M-token {r2['baseline_per_m']:.3f} → {r2['optimized_per_m']:.3f}. M2 sau tính phí ghi khác bản gốc $8,48/ngày. M3 và M5 quy đổi tháng 30 ngày; carbon dùng ngày job thực tế.

## 2. Đóng góp từng đòn bẩy

{biggest} lớn nhất: ${levers[biggest]:,}/tháng vì baseline GPU workloads lớn hơn nhiều API traffic. Purchasing tiết kiệm {r3['savings_pct']}%; inference tiết kiệm {r2['savings_pct']}%. Cascade là nguồn giảm lớn nhất trong M2; cache và batch tiếp tục giảm bill theo thứ tự, phí ghi cache làm tăng nhẹ chi phí. Bảng từng bước và bốn khoản savings nằm trong report.md.

## 3. GPU-Util Lie

H100-4 util 98,2% nhưng MFU 19,4%; A10G-1 util 96,9% nhưng MFU 26,8%. Kernel có thể bận với memory stall/I/O chứ không đạt compute peak. Hạ H100→A100 và A10G→L4 có tiềm năng $655/tháng; tắt 8 giờ idle/ngày của H100-5 tiết kiệm $600/tháng. Chưa có VRAM/throughput benchmark nên đây là giả thuyết. Telemetry không nối với job_id; tổng lab có khả năng cộng trùng purchasing, right-sizing và idle. Không coi ước tính này là khoản tiền đã thu hồi.

## 4. Hai extension

**Cache có phí ghi:** thêm cache_is_worth_it và cache_break_even_reads; gate trước cache, dùng chung hàm tính tiền cho M2/M4. Giả định incremental write 1,25× input, 5 reads/prefix, không giảm write theo batch. Hòa vốn 1,3889 reads realtime và 2,7778 batch. Một read: tắt cache; năm reads: bật. Trước ghi ${s['batch_no_write']:.4f}/ngày; sau ${s['with_write']:.4f}. Token/output/model route giữ nguyên. CSV thiếu prefix/read count nên cần đo hit rate và TTL thực tế trước áp dụng.

**Carbon scheduling:** thêm mission carbon_scheduling, tích hợp bảng vào M5. Wh bằng watts catalog nhân GPU-hours, chỉ job interruptible; cùng lượng công việc, ngày thực tế. Chuyển us-east-1→europe-north1 giảm {c['saved_g']:,.2f} gCO2e (92,11%). europe-north1 sạch nhất nhưng us-east-wa điện rẻ nhất. Đây là điện GPU theo công suất catalog, thiếu PUE và rework; không cộng điện vào bill thuê GPU. Cần kiểm tra GPU availability, dữ liệu và SLA trước chuyển vùng.

## 5. Ba hành động đầu tiên

1. Đo chất lượng và latency cascade trên tập đánh giá; bật cache có gate theo reuse thực tế và batch cho offline. Purchasing là khoản lớn nhất, nhưng phải xác minh thời hạn nhu cầu trước reserved 3 năm, checkpoint trước Spot.
2. Profiling hai util-lies, đo VRAM và benchmark GPU thay thế; tự động tắt idle và nối telemetry với job_id để loại cộng trùng savings.
3. Thiết lập owner/team/project bắt buộc và budget cảnh báo; lập lịch job interruptible ở vùng sạch nếu đáp ứng SLA. Team {top} đang cao nhất ${a['by_team'][top]:.2f}/ngày (~{a['by_team'][top]/sum(a['by_team'].values()):.1%}); coverage {a['tag_coverage']:.1%} qua gate 80%, vẫn cần sửa tag thiếu và phân bổ nốt.

Bảng đo chi tiết: outputs/report.md; bản trước sửa: outputs/before/. Giá/carbon là giả định lab, không phải giá thị trường hiện tại.
'''
    Path(ROOT,'outputs','writeup.md').write_text(writeup,encoding='utf-8')
    return text
