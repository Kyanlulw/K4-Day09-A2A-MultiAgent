# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Pham Viet Bach |
| MSSV            | 01410       |
| Khóa/Lớp        | K4         |
| Vai trò chính   | Deterministic Agents (Customer, Order, Payment, Delivery) & Tracing |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Customer Agent | `agents/customer_agent.py` | `order_id`, `data_loader` | Customer History JSON | Hoàn thành |
| Order & Product Agent | `agents/order_product_agent.py` | `order_id`, `data_loader` | Order Items JSON | Hoàn thành |
| Payment Agent | `agents/payment_agent.py` | `order_id`, `data_loader`, `expected_total` | Reconciled Payments JSON | Hoàn thành |
| Delivery Agent | `agents/delivery_agent.py` | `order_id`, `data_loader`, `items_raw` | Delivery Variance JSON | Hoàn thành |
| Trace Writer | `trace_writer.py` | `trace_steps` list | Ghi file `trace.jsonl` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Sửa lỗi mapping trong Graph | Tran Le Quy Dang (Graph) | Map đúng các biến Output của Deterministic Agents vào CaseState |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Trích xuất logic giao hàng | `delivery_agent.py` | Tính được độ trễ logistics vs người bán | Check logs khi chạy |
| Reconcile payments | `payment_agent.py` | Đối chiếu item_total + freight_total với payments | File `trace.jsonl` |
| Ghi file trace JSONL | `trace_writer.py` | Output ra file `trace.jsonl` chuẩn định dạng | Đọc file `trace.jsonl` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
File `trace.jsonl` lưu trữ toàn bộ các bước tính toán và xử lý logic của các agents dưới dạng JSONL, phục vụ cho quá trình đánh giá pipeline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
LLM thường gặp ảo giác (hallucination) nếu tự thực hiện các phép toán đối chiếu tổng tiền thanh toán hoặc ngày tháng giao hàng. Cần xây dựng các Python agents (Deterministic Agents) thay LLM tính toán chính xác tuyệt đối.

### Cách triển khai
Viết các function riêng rẽ. Thay vì dùng Prompt, sử dụng Pandas Dataframe để filter `order_id`, `groupby` và `sum()` cho Payment. Với Delivery, chuyển đổi các string datetime sang format của Python để so sánh sự chênh lệch giờ giấc giữa `order_delivered_carrier_date` và `shipping_limit_date`.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | `order_id` truyền từ State             |
| Output                  | Dictionary với kết quả tính toán cụ thể|
| Module phụ thuộc        | Data Loader do Đăng viết               |
| Module sử dụng output   | Policy Agent do Quý viết (để áp rule)  |
| Điều kiện lỗi cần xử lý | Xử lý khi order không có payment hoặc chưa có ngày giao hàng |

### Cách xác minh

```bash
python main.py
```

- **Kết quả mong đợi:** Trace file ghi đầy đủ output của 4 Deterministic Agents.
- **Kết quả thực tế:** 50 cases đều pass khâu check toán học.
- **Artifact/log:** Xem nội dung file `trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Ghi log quá trình xử lý để debug.
- **Các phương án đã cân nhắc:** 1) Print ra màn hình. 2) Dùng module `logging` lưu file .log. 3) Ghi JSONL qua class TraceWriter.
- **Phương án đã chọn:** Dùng `TraceWriter` ghi định dạng JSONL.
- **Lý do:** Trade-off về readability. Định dạng JSONL giúp lưu log có cấu trúc (structured log) từng case một trên 1 dòng, tiện cho việc phân tích và parse lại bằng code sau này.
- **Bằng chứng quyết định phù hợp:** File `trace.jsonl` ra output rất gọn gàng và dễ đọc bằng machine.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lỗi phép trừ ngày tháng `TypeError: can't subtract offset-naive and offset-aware datetimes` trong DeliveryAgent.
- **Lệnh hoặc bước tái hiện:** Chạy test với một số order bị thiếu `order_delivered_customer_date`.
- **Nguyên nhân gốc:** Pandas đọc dữ liệu ngày tháng lúc thì dạng chuỗi, lúc thì dạng NaT hoặc thiếu timezone.
- **Cách xử lý:** Sử dụng `pd.to_datetime(..., errors='coerce')` và ép chuẩn xử lý timezone cho các trường datetime trong `delivery_agent.py`.
- **Cách xác minh sau khi sửa:** Chạy lại `main.py` không còn văng exception tính toán.
- **Điều học được:** Khi tính toán datetime từ dữ liệu thực tế, cần phải handle luôn các trường hợp rác hoặc thiếu dữ liệu (missing values).

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

[Mẫu câu hỏi không liên quan đến project E-commerce, sinh viên tự điền nếu có yêu cầu của môn học]

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Pham Viet Bach
**Ngày xác nhận:** 2026-08-05
