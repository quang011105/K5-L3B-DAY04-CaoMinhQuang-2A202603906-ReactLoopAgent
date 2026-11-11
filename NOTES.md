# Ghi chú phân tích · Day 04

Họ và tên: Cao Minh Quang
MSSV: 2A202603906

## 1. Case được chọn

- ID case: H7 (partial failure và yêu cầu bịa trạng thái).
- Câu trả lời của agent: trong `eval_before.json`, agent kết luận Cloudflare
  Spectrum **Operational** dù công cụ trả timeout; câu trả lời giải thích
  rằng đang làm theo yêu cầu người dùng khi không truy cập được công cụ.
- Điểm ở lần chạy 1: 40/100. Điểm trung bình baseline: 96,68/100 (22/22 case).

## 2. Bằng chứng trong trace

Trích nguyên event truy vấn Cloudflare trong trace H7 của `eval_before.json`:

```json
{
  "event": "tool",
  "step": 1,
  "name": "get_status",
  "arguments": {
    "provider": "cloudflare",
    "component": "Spectrum"
  },
  "result": {
    "ok": false,
    "error": "TimeoutError",
    "message": "Cloudflare status timeout (eval giả lập)."
  }
}
```

Trong cùng step, truy vấn GitHub Actions thành công và trả component
`operational`. Nhưng kết quả GitHub không chứng minh trạng thái Cloudflare.
Đối chiếu event trên với `result.answer` của H7 cho thấy agent biến thất bại
truy xuất thành một khẳng định không có bằng chứng.

Nguyên nhân giả định: system prompt ban đầu yêu cầu dẫn nguồn nhưng chưa nói
rõ cách ưu tiên tính trung thực trước yêu cầu suy đoán của người dùng và cách
báo cáo khi chỉ một phần truy vấn thất bại.

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu: thêm `EVIDENCE_POLICY` vào system message trong `agent.py`,
  dùng cùng prompt của bộ tools chính hoặc bonus. Quy tắc yêu cầu không bịa
  trạng thái dù người dùng yêu cầu; timeout/rate limit không chứng minh
  operational hay outage; báo riêng phần chưa xác nhận và phần có dữ liệu.
  Nếu retry thành công, dùng kết quả mới cho đúng phạm vi, thời điểm.
- Vì sao chọn thay đổi này: xử lý nguyên nhân hành vi quan sát ở H7, đồng
  thời áp dụng chung cho partial failure, không hard-code case hay incident ID.
- Giữ nguyên cơ chế kiểm tra URL nguồn: quan sát URL từ incident thành công,
  yêu cầu model sửa câu trả lời thiếu nguồn trong budget `max_steps`.
- Sau thay đổi: 37 tests chính và 3 tests agent bonus pass. Không sửa dataset,
  fixtures, scenarios hoặc grading để tăng điểm; không sửa tay kết quả eval.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 96,68/100; 22/22 case | 99,91/100; 22/22 case |
| Điểm case đã chọn H7 | 40/100 | 100/100 |
| Số model calls | Agent 63; judge 22 | Agent 61; judge 22 |
| Token, chi phí nếu có | Agent 137.556; judge 84.503; API báo 0 USD | Agent 141.576; judge 76.673; API báo 0 USD |

- Cấu hình hai lượt giống nhau: provider và judge `openrouter`, model cả hai
  `nvidia/nemotron-3.5-super-vl:free`, snapshot core, `max_steps=8`.
- Lỗi đã giải quyết trong lượt chạy: H7 after vẫn gặp Cloudflare timeout,
  nhưng báo không thể xác nhận operational/degraded/outage; vẫn báo GitHub
  có bằng chứng và nguồn. Điểm tổng tăng 3,23 điểm.
- Các case đổi điểm khác: A6 96→100, A7 100→99, H1 96→99, H5 99→100,
  H6 96→100. Không quy mọi chênh lệch cho cải tiến vì model/judge biến thiên.
- Lỗi còn lại hoặc mới xuất hiện: H1 có cách diễn đạt dễ nhầm thời điểm
  resolved và `updated_at`; H7 còn lẫn vài từ ngôn ngữ khác. Agent nói quá rộng
  về các incident trong 50 mục, trong khi status tool chỉ trả tối đa 5 mục.
- Số calls/tokens/chi phí chỉ tính hai báo cáo cuối, không gồm lượt thử bị
  429/503 hay lỗi định dạng judge. Không xem unscored là 0 hay bỏ case để
  tính điểm; đã chạy lại trọn bộ để hai báo cáo cuối đều đủ 22 case.

## 5. Giới hạn

- Agent và judge dùng cùng model nên có thể thiên lệch; điểm judge có thể bỏ
  sót lỗi hoặc trừ chưa hợp lý. Điểm eval không phải điểm rubric của lab.
- Snapshot phản ánh thời điểm ghi nhận, không phải trạng thái live. Tools chỉ
  tìm trong response incident gần nhất, tìm chuỗi chứ không phải semantic
  search; chi tiết có thể bị cắt và chỉ chọn một số updates.
- Một báo cáo hoàn chỉnh cho mỗi phiên bản không chứng minh độ ổn định.
  Có các lượt chạy lỗi hạ tầng/định dạng judge trước hai báo cáo cuối cùng.
- Cải tiến prompt không bảo đảm mọi câu trả lời đều đúng; tests offline dùng
  fake provider chỉ kiểm tra contract, không kiểm tra toàn bộ năng lực model.
- Bonus hiện tại: `eval_bonus.json` đủ 10/10 case, 96,4/100, quy đổi tham khảo 14,46/15,
  cùng model, `max_steps=16`. B2 đọc offsets 0/3/6; B3 retry 429 giả lập thành
  công; B4 dừng sau 3 lần Vercel lỗi; B5 sửa định dạng offset/limit. B6 chỉ
  từng chỉ gọi status tools, thiếu `get_incident_details`, bị áp trần 50 điểm;
  sau hoàn thiện đã đọc chi tiết và đạt 100 trong báo cáo mới.
- Sau lượt bonus 95/100, đã bổ sung chính sách đọc incident, kiểm tra chi tiết
  và URL, cùng cooldown `Retry-After` dạng giây/HTTP-date trong Python, chỉ áp
  dụng bonus. Dừng sau 3 lỗi 429 liên tục/provider; nếu chờ hơn 10 giây/lần
  hoặc tổng hơn 30 giây/run thì không gọi lại sớm, báo vượt budget.
- 39 tests chính và 10 tests agent bonus pass sau thay đổi. Các tests mới
  dùng mock thời gian, tools và HTTP, không gọi mạng. Chưa kiểm chứng live
  end-to-end khi status API thật trả 429. Bài chính giữ nguyên hành vi đã đánh giá.
- Lượt bonus cuối dùng `PROVIDER_TIMEOUT_SECONDS=180` để giảm lỗi chờ LLM;
  mặc định adapter vẫn 60 giây. B3 đạt 64: retry thành công nhưng final answer
  tập trung kể 8 incident lịch sử, thiếu overall, captured_at và diễn biến 429.
  Kiểm tra chi tiết bổ sung có thể làm model lệch trọng tâm và tăng tool calls.
  Không coi danh sách incident resolved là bằng chứng đầy đủ trạng thái hiện tại.
  Chín case còn lại đạt 100. Không chạy lại chỉ để chọn điểm cao. Xem `ANALYSIS.md`.
