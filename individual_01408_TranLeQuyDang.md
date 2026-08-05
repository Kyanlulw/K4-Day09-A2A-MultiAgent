# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Tran Le Quy Dang |
| MSSV            | 01408       |
| Khóa/Lớp        | K4         |
| Vai trò chính   | Data Loading, LangGraph Orchestration & Coordinator Agent |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Data Loader | `tools/data_loader.py` | CSV Olist dataset | `OlistDataLoader` object | Hoàn thành |
| LangGraph Workflow | `graph.py` / `build_graph()` | `CaseState` | Compiled Workflow | Hoàn thành |
| Coordinator Agent | `graph.py` / `coordinator_start_node` | `CaseState` với order_id | `investigation_plan`, `order_data` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Hỗ trợ cấu hình LLM API | Nguyen Van Quy (LLM Client) | Cấu hình thành công API và error handling |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng luồng Graph | `graph.py` | `workflow.invoke()` chạy qua 7 nodes | Log console khi chạy `main.py` |
| Load Data tối ưu | `data_loader.py` | Dữ liệu được load 1 lần vào memory | In thời gian chạy load file |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Điều phối thành công chu trình xử lý của một khiếu nại (case) từ Coordinator -> Policy -> Verifier thông qua state dùng chung `CaseState`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống cần một luồng điều phối trạng thái (state) chung giữa các agents và khả năng truy xuất dữ liệu từ các file CSV lớn của Olist một cách nhanh chóng để LLM không bị nghẽn ở khâu đọc dữ liệu.

### Cách triển khai
Sử dụng `StateGraph` từ thư viện LangGraph để định nghĩa các edges tuần tự. Các biến dùng chung được khai báo qua `CaseState` (TypedDict). Dữ liệu CSV được load một lần duy nhất lúc khởi tạo qua pandas và lưu trong bộ nhớ.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | `case_id`, `order_id`                  |
| Output                  | `CaseState` cập nhật qua từng node     |
| Module phụ thuộc        | Các Agents do Bạch và Quý viết         |
| Module sử dụng output   | Toàn bộ pipeline trong `main.py`       |
| Điều kiện lỗi cần xử lý | Xử lý khi order_id không tồn tại trong dataset |

### Cách xác minh

```bash
python main.py
```

- **Kết quả mong đợi:** Pipeline load data, sau đó tuần tự chạy qua Coordinator -> các agents -> Verifier mà không bị break graph.
- **Kết quả thực tế:** Pass các cases trơn tru.
- **Artifact/log:** Console log hiển thị `[Main] LangGraph workflow compiled`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Load dữ liệu Olist cho mỗi agent chạy độc lập.
- **Các phương án đã cân nhắc:** 1) Load lại data ở từng agent. 2) Load 1 lần truyền object qua State.
- **Phương án đã chọn:** Load 1 lần ở `main.py` và truyền object `OlistDataLoader` vào `CaseState`.
- **Lý do:** Trade-off về memory và latency. Tuy tốn RAM lúc đầu nhưng latency lúc query trong các node agent giảm xuống mức thấp nhất.
- **Bằng chứng quyết định phù hợp:** Mỗi case mất <1s xử lý phần dữ liệu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Graph bị lỗi không map được state khi các node trả về dictionary thiếu key.
- **Lệnh hoặc bước tái hiện:** Chạy `workflow.invoke()`
- **Nguyên nhân gốc:** `TypedDict` yêu cầu strict typing nhưng một số node agent trả về None hoặc thiếu key.
- **Cách xử lý:** Thêm `total=False` vào khai báo `CaseState` và xử lý logic kiểm tra `None` ở các node nhận.
- **Cách xác minh sau khi sửa:** Chạy lại `main.py` không còn văng exception KeyError.
- **Điều học được:** Khai báo StateGraph trong LangGraph cần sự linh hoạt nếu các agent không phải lúc nào cũng populate tất cả fields.

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

**Họ và tên:** Tran Le Quy Dang
**Ngày xác nhận:** 2026-08-05
