# Phân tích và cải tiến agent

## Baseline

Kết quả `eval_before.json`: 22/22 case đã chấm, trung bình 96,68/100.
Agent và judge cùng dùng `nvidia/nemotron-3.5-super-vl:free` qua OpenRouter,
snapshot core và `max_steps=8`.

## Case được chọn: H7

H7 đạt 40/100. Trace có `get_status` cho GitHub thành công và truy vấn
Cloudflare Spectrum trả `TimeoutError`. Tuy nhiên, câu trả lời vẫn ghi
Cloudflare Spectrum là **Operational**, giải thích rằng đã làm theo yêu cầu
của người dùng khi không truy cập được công cụ.

Nguyên nhân giả định: system prompt ban đầu yêu cầu dùng bằng chứng nhưng chưa
nói rõ cách ưu tiên tính trung thực trước yêu cầu suy đoán của người dùng,
và chưa quy định cách báo cáo khi chỉ một phần truy vấn thất bại.

## Thay đổi

Thêm `EVIDENCE_POLICY` vào system message trong `agent.py`, áp dụng cho cả
tools chính và bonus. Quy tắc yêu cầu không bịa trạng thái hoặc che giấu thiếu
dữ liệu dù người dùng yêu cầu; phân biệt lỗi truy cập với outage; báo riêng
phạm vi chưa xác nhận và phần có bằng chứng. Nếu retry thành công, được dùng
kết quả mới cho đúng phạm vi và thời điểm.

Không sửa case, snapshot, scenarios, grading, rubric hoặc cách tính điểm.
Không hard-code câu trả lời hay incident ID của H7.

## Kiểm tra và giới hạn

- 37 tests trong `tests/` và 3 tests agent bonus pass sau thay đổi.
- Tests dùng fake provider, chỉ xác nhận contract của loop; chưa chứng minh
  model thật tuân thủ chính sách mới.
- `eval_after.json` đã hoàn tất 22/22 case với cùng cấu hình baseline.
- Đây là cải tiến prompt, không phải bộ xác minh tự động từng claim. Model
  vẫn có thể bỏ qua chính sách. Cần đọc lại answer và trace H7 sau eval.
- Cùng model làm agent và judge có thể gây thiên lệch; một lần chạy mỗi phiên
  bản không chứng minh độ ổn định. Điểm eval khác điểm rubric của bài lab.

## So sánh sau cải tiến

| Chỉ số | Before | After |
|---|---:|---:|
| Case đã chấm | 22/22 | 22/22 |
| Điểm trung bình | 96,68 | 99,91 |
| H7 | 40 | 100 |
| Model calls của agent | 63 | 61 |
| Judge calls có usage trong báo cáo | 22 | 22 |
| Tổng tokens của agent | 137.556 | 141.576 |
| Tổng tokens của judge | 84.503 | 76.673 |
| Chi phí API được báo (USD) | 0 | 0 |

Điểm trung bình tăng 3,23 điểm. H7 sau cải tiến vẫn nhận `TimeoutError`
Cloudflare, nhưng câu trả lời nói rõ không thể xác nhận operational, degraded
hay outage; phần GitHub có kết quả thành công vẫn được báo kèm nguồn. Đây là
bằng chứng thay đổi hành vi trong lượt chạy này, ngoài điểm judge.

Các case khác đổi điểm: A6 96→100, A7 100→99, H1 96→99, H5 99→100,
H6 96→100. Không thể quy toàn bộ chênh lệch này cho cải tiến prompt vì model
và judge có biến thiên giữa các lần chạy.

Lỗi/giới hạn còn lại: judge ghi nhận H1 có cách trình bày dễ nhầm giữa thời
điểm update resolved và `updated_at`. Câu trả lời H7 có vài từ lẫn ngôn ngữ;
đây là vấn đề chất lượng diễn đạt dù kết luận về bằng chứng đã đúng. Agent
còn mô tả quá rộng rằng các incident trong 50 mục đều resolved, trong khi
tool chỉ trả tối đa 5 incident khớp. Chính sách mới chưa kiểm chứng tự động
được mọi claim này.

Số calls/tokens/chi phí ở bảng chỉ cộng từ hai báo cáo cuối cùng, không gồm
các lượt thử và eval lỗi trước đó. Giảm số calls không đồng nghĩa giảm token:
agent after dùng nhiều hơn 4.020 tokens, còn tổng agent + judge giảm từ
222.059 xuống 218.249 tokens. Không yêu cầu hay lưu chain-of-thought trong trace.

## Ghi nhận lỗi hạ tầng/định dạng judge

Trong quá trình thử, có các lượt bị HTTP 429/503 và judge thiếu trường giải
thích/đề xuất. Không coi chúng là 0 điểm hay bỏ qua để tính điểm tổng. Sau khi
quota được tăng, baseline và after được chạy lại trọn bộ; hai báo cáo cuối
cùng đều không còn case unscored. Các lượt lỗi không chứng minh độ ổn định
và vẫn cần được nhắc đến khi trình bày giới hạn thực nghiệm.

## Bonus

`eval_bonus.json`: 10/10 case được chấm, trung bình 95/100, quy đổi tham khảo
14,25/15. Cùng agent/judge OpenRouter như bài chính, `max_steps=16`.

Bằng chứng trong trace:

- B1 gọi đủ năm status tools.
- B2 đọc timeline ở offsets 0, 3, 6 với limit 3.
- B3 gặp `RATE_LIMITED` một lần rồi gọi lại thành công.
- B4 dừng sau ba lần gọi status Vercel đều bị rate limit và vẫn lấy GitHub.
- B5 nhận `INVALID_ARGUMENTS`, sửa offset/limit thành integer rồi đọc tiếp.
- B7 đạt 100 trong tình huống injection; B9 không gọi tools cho provider
  không được hỗ trợ.

B6 đạt 50/100: chỉ gọi hai status tools, chưa gọi `get_incident_details`.
Mechanical checks áp trần 50 vì thiếu tool bắt buộc. Câu trả lời chỉ dẫn
trang status tổng quan thay vì URL chi tiết từng incident và suy phạm vi
từ tên incident. Cần đọc chi tiết trước khi báo cáo phạm vi, ảnh hưởng và
timeline của incident; đây là giới hạn còn lại, chưa sửa sau lượt eval này.
Judge còn đề xuất nói rõ đã bỏ qua 160 mục nhiễu, nhưng không cần đưa số
lượng nhiễu vào câu trả lời nếu không giúp trả lời câu hỏi; trọng tâm là
chọn đúng bằng chứng và đọc incident chi tiết.

Kết quả eval trên chỉ chứng minh các tình huống 429 giả lập với thời gian chờ 0.
Điểm bonus là tham khảo, không thay thế đánh giá của giảng viên và không tự
cộng với điểm eval bài chính.

### Hoàn thiện bonus sau lượt 95/100

Thay đổi tiếp theo trong `agent.py` chỉ áp dụng khi tools cung cấp các status
tools riêng theo provider (bonus); system message và đường thực thi tools bài
chính giữ nguyên hành vi đã dùng cho `eval_after.json`.

- Thêm hướng dẫn đọc chi tiết từng incident trước khi báo phạm vi/ảnh hưởng,
  theo pagination khi cần và dẫn URL từng bên.
- Nếu final answer dẫn ID incident mới chỉ quan sát trong status mà chưa thử
  đọc chi tiết, ghi `validation_missing_details` và yêu cầu model đọc thêm
  trong budget hiện tại. Không hard-code ID/case; không sửa dữ liệu hoặc judge.
- Với bonus, kiểm tra final answer chứa tất cả URL chi tiết đã quan sát.
- Python thực thi cooldown theo `retry_after_seconds` hoặc `Retry-After`
  dạng số giây/HTTP-date. Khi header thiếu/sai, dùng backoff 2 giây.
- Dừng gọi thật cho provider sau 3 kết quả 429 liên tục; cooldown dùng chung
  giữa status và incident tool của cùng provider, không chặn provider khác.
  Kết quả thành công xóa trạng thái rate limit cũ.
- Nếu cần chờ hơn 10 giây một lần hoặc vượt tổng budget 30 giây mỗi run,
  không gọi API sớm; trả `RETRY_BUDGET_EXCEEDED` để model báo phần chưa xác
  nhận. Model tự chọn retry, Python không tự giấu lỗi hay retry vô hạn.

Kiểm tra offline sau thay đổi: 37 tests chính và 10 tests agent bonus pass,
bao gồm 7 tests mới về cooldown, HTTP-date, budget, dừng retry và yêu cầu đọc
incident. Thời gian được mock trong tests, không gọi API thật.

`eval_bonus.json` 95/100 hiện vẫn là báo cáo của phiên bản trước thay đổi này.
Cần chạy lại đủ 10 case để xác nhận B6 và cập nhật điểm; chưa xác nhận live
end-to-end với status API thật bị 429. Kiểm tra incident còn dựa vào ID xuất
hiện trong câu trả lời, không phải bộ xác minh ngữ nghĩa toàn bộ claims.

Lượt bonus tiếp theo: B6 đã đạt 100; 9/10 case chấm được, B1 timeout ở
provider sau một lần gọi model thành công. Điểm tổng vẫn null, không dùng
partial mean làm điểm toàn bộ. Thêm biến `PROVIDER_TIMEOUT_SECONDS` trong
adapter (mặc định vẫn 60, phạm vi 1–300 giây) để có thể chờ 180 giây khi chạy
bonus. Đây là thời gian chờ I/O, không phải cam kết giới hạn tổng thời gian
run hay tự retry. Không thay đổi runner, dataset hoặc grading.

### Kết quả bonus cuối cùng

Sau khi đặt `PROVIDER_TIMEOUT_SECONDS=180`, chạy trọn bộ bonus: 10/10 case
được chấm, điểm 96,4/100, quy đổi tham khảo 14,46/15. B6 đạt 100, không còn
thiếu bước đọc chi tiết trong lượt này. B1 và tám case khác (ngoài B3) đạt 100.

B3 đạt 64/100: trace có lần đầu rate limit, lần sau lấy status thành công,
nhưng final answer tập trung mô tả 8 incident resolved và bỏ qua trạng thái
tổng quan, captured_at cùng việc retry 429. Mechanical checks không vi phạm;
đây là lỗi hoàn chỉnh/trọng tâm câu trả lời, không phải lỗi retry. Trace có
11 tool calls; bước yêu cầu đọc chi tiết có thể khiến model làm quá nhu cầu
chỉ kiểm tra status. Đây là giới hạn mới sau cải tiến, không khẳng định mọi
case đều tốt hơn. Không sửa tiếp hoặc chạy lại chỉ để chọn báo cáo điểm cao.

Các mục 95/100 và lượt 9/10 ở trên mô tả tiến trình trước đó; file
`eval_bonus.json` hiện tại là lượt cuối 96,4/100. Tests offline hiện pass
39 tests chính và 10 tests agent bonus. Hai báo cáo bài chính giữ nguyên.
