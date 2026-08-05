# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Nguyen Van Quy |
| MSSV            | 01508       |
| Khóa/Lớp        | K4         |
| Vai trò chính   | Policy Agent, Verifier Agent, LLM API Integration |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| LLM Client | `tools/llm_client.py` | Prompt từ hệ thống | LLM Response (JSON) | Hoàn thành |
| Policy Agent | `agents/policy_agent.py` | State từ các Deterministic Agents | Policy Classification JSON | Hoàn thành |
| Verifier Agent | `agents/verifier_agent.py` | JSON Output cuối cùng | Đánh giá tính chuẩn xác của Output | Hoàn thành |
| Test LLM API | `test_groq.py` | API Call đơn giản | Xác nhận API hoạt động | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Sửa lỗi Prompt Engineering | Tran Le Quy Dang (Coordinator) | Tinh chỉnh prompt để LLM luôn trả về JSON hợp lệ |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Viết LLM wrapper | `llm_client.py` | Hàm `llm_json_call` hỗ trợ retry | Chạy test API không bị sập khi Rate Limit |
| Phân loại case bằng LLM | `policy_agent.py` | LLM suy luận ra `primary_issue` | Check kết quả ở file `trace.jsonl` |
| Verifier LLM | `verifier_agent.py` | Review quality của final JSON | Log in ra chất lượng `is_valid` từ LLM |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Tích hợp thành công Groq API (Llama-3.1-8b) với khả năng nhận diện rate-limit và tự động backoff retry, giúp hệ thống không bị crash khi xử lý hàng loạt 50 cases liên tục.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Việc gọi API LLM từ các nhà cung cấp (OpenRouter, Groq) dễ bị nghẽn do giới hạn Rate Limit (429). Ngoài ra, các model có thể trả về định dạng rác thay vì JSON thuần túy, làm vỡ pipeline.

### Cách triển khai
Viết wrapper API sử dụng thư viện `openai` chuẩn. Có tính năng retry với exponential backoff khi gặp lỗi 429. Hàm `llm_json_call` ép model trả về JSON và tự động sửa lỗi parse JSON thông thường (regex trích xuất từ dấu ngoặc `{...}`). Trong Policy và Verifier, truyền toàn bộ context vào LLM và dùng Zero-shot Prompting với format strict JSON.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | System Prompt, User Prompt             |
| Output                  | Chuỗi JSON hợp lệ (dict trong python)  |
| Module phụ thuộc        | API Groq / vLLM                        |
| Module sử dụng output   | LangGraph (điều hướng state tiếp theo) |
| Điều kiện lỗi cần xử lý | Xử lý Rate Limit 429 và JSON Decode Error |

### Cách xác minh

```bash
python test_groq.py
```

- **Kết quả mong đợi:** Gọi thành công API Groq Llama 3.1 8B.
- **Kết quả thực tế:** Trả về response đúng định dạng mà không gặp lỗi.
- **Artifact/log:** Xem file `trace.jsonl` phần `PolicyAgent` và `VerifierAgent` có output rõ ràng.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn LLM Model để xử lý 50 cases nhanh nhất.
- **Các phương án đã cân nhắc:** 1) Dùng vLLM local qua Kaggle. 2) Dùng OpenRouter API. 3) Dùng Groq API.
- **Phương án đã chọn:** Dùng Groq API với `llama-3.1-8b-instant`.
- **Lý do:** Trade-off về cost và speed. Groq cung cấp tốc độ phản hồi tính bằng mili giây so với Kaggle tunnel (rất chậm và mất ổn định), giúp pipeline hoàn thành xử lý đa luồng cho 50 cases siêu tốc.
- **Bằng chứng quyết định phù hợp:** Toàn bộ pipeline chạy mượt mà trong chưa đầy 1 phút.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** LLM trả lời "Sure, here is your JSON..." thay vì chỉ trả về code JSON, gây ra lỗi `JSONDecodeError`.
- **Lệnh hoặc bước tái hiện:** `json.loads(llm_response)`
- **Nguyên nhân gốc:** Model Llama 3.1 đôi khi quá "lịch sự" (chatty) dù đã chỉ định `response_format={"type": "json_object"}`.
- **Cách xử lý:** Trong hàm `llm_json_call`, bổ sung cơ chế fallback dùng `raw.find('{')` và `raw.rfind('}')` để cắt xén và trích xuất đúng nội dung JSON nếu lệnh `json.loads` mặc định thất bại.
- **Cách xác minh sau khi sửa:** Các hàm `llm_json_call` không còn văng exception kể cả khi LLM chèn text rác vào đầu cuối.
- **Điều học được:** Không bao giờ tin tưởng tuyệt đối vào output của LLM. Luôn phải có Regex parser để bọc hậu cho việc trích xuất JSON.

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

**Họ và tên:** Nguyen Van Quy
**Ngày xác nhận:** 2026-08-05
