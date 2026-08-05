# Member Role Report - Day 9: Multi-Agent A2A

## 1. Thong tin ca nhan

| Thong tin | Noi dung |
| --- | --- |
| Ho va ten | [Dien ho va ten] |
| MSSV/MHV | [Dien MSSV/MHV] |
| Khoa/Lop | K4 |
| Vai tro chinh | Multi-agent pipeline, data reconciliation, verifier |
| Ngay hoan thanh | 2026-08-05 |

## 2. Vai tro va pham vi cong viec

| Module/deliverable | File/ham phu trach | Input nhan vao | Output ban giao | Trang thai |
| --- | --- | --- | --- | --- |
| Data Retrieval Tool | `tools/data_loader.py` | 9 CSV Olist, `claimed_order_id` | Evidence JSON cho tung case | Hoan thanh |
| Agent orchestration | `agents/coordinator.py`, `main.py` | `input/EC_XXX.json` | Dieu phoi 7 agent va ghi output | Hoan thanh |
| Domain agents | `agents/customer_agent.py`, `agents/order_product_agent.py`, `agents/payment_agent.py`, `agents/delivery_agent.py` | Evidence theo domain | Ket qua suy luan tung domain | Hoan thanh |
| Policy & verification | `agents/policy_agent.py`, `agents/verifier_agent.py` | Ket qua domain agents | Issue, refund, actions, schema check | Hoan thanh |
| Logging & metadata | `trace_writer.py`, `logging/metadata.json` | Agent prompt/response | `trace.jsonl`, metadata runtime | Hoan thanh |

## 3. Ket qua theo vai tro

| Nhiem vu da thuc hien | Artifact lien quan | Ket qua ban giao | Cach xac minh |
| --- | --- | --- | --- |
| Xay dung pipeline xu ly 50 case | `main.py` | 50 file JSON trong `output/` | Chay `python validate_outputs.py` |
| Thiet ke 7 agent | `agents/` | Coordinator, Customer, Order/Product, Payment, Delivery, Policy, Verifier | Kiem tra `logging/trace.jsonl` |
| Ap dung `EC_POLICY_V2` | `agents/policy_agent.py` | Primary issue, secondary issues, root cause, refund, actions | Phan bo issue trong validate output |
| Viet tai lieu kien truc | `architecture.md` | So do agent, handoff, quyen truy cap du lieu | Doc tai lieu tai root repo |

Output cu the: pipeline da sinh du `EC_001.json` den `EC_050.json`, trace co
350 dong tuong ung 50 case x 7 buoc, va file `output_submission.zip` chi chua
50 JSON ket qua.

## 4. Giai thich phan ky thuat da thuc hien

### Van de can giai quyet

Bai toan yeu cau dieu tra khieu nai thuong mai dien tu dua tren nhieu nguon du
lieu Olist. Mot case khong the ket luan chi tu message cua khach hang, ma phai
doi chieu order status, timestamps, seller shipping limit, items, payments,
customer history va product context.

### Cach trien khai

He thong tach thanh 7 agent. Coordinator nhan input, goi Data Retrieval Tool de
lay evidence tu CSV, sau do chuyen du lieu den cac domain agent. Moi domain
agent phan tich mot pham vi rieng:

- Customer Agent xac dinh customer identity va repeat customer.
- Order & Product Agent xac dinh item, seller, product va category.
- Payment Agent tinh doi soat tien hang, tien ship va payment.
- Delivery Agent tinh delivery variance va seller handoff variance.
- Policy Agent ap dung `EC_POLICY_V2` theo thu tu uu tien.
- Verifier Agent kiem schema, evidence, limit array va tinh nhat quan.

### Input, output va contract

| Thanh phan | Mo ta |
| --- | --- |
| Input | `input/EC_XXX.json`, gom `case_id`, message va `claimed_order_id` |
| Output | `output/EC_XXX.json` dung schema cua de bai |
| Module phu thuoc | `tools/data_loader.py`, 9 CSV trong `data/` |
| Module su dung output | `validate_outputs.py`, zip submission |
| Dieu kien loi can xu ly | Order khong co item, timestamp null, split payment, multi-seller, late delivery |

### Cach xac minh

```bash
python main.py
python validate_outputs.py
```

- Ket qua mong doi: co 50 JSON hop le trong `output/`.
- Ket qua thuc te: validation passed, 50 output JSON, 350 trace events.
- Artifact/log: `output/`, `output_submission.zip`, `logging/trace.jsonl`.

## 5. Mot quyet dinh ky thuat quan trong

- Boi canh: Neu de moi agent tu doc CSV truc tiep, luong xu ly de bi lap code,
  join sai va kho kiem chung.
- Cac phuong an da can nhac: agent doc CSV truc tiep; hoac Data Retrieval Tool
  doc CSV roi cap evidence cho agent.
- Phuong an da chon: Data Retrieval Tool doc CSV, agent chi suy luan tren
  evidence da trich xuat.
- Ly do: tach ro truy xuat du lieu va suy luan nghiep vu, de trace, de debug va
  giam false positive evidence.
- Bang chung: output validation passed cho 50 case, trace ghi ro input/output
  cua tung agent.

## 6. Mot loi/blocker da xu ly

- Trieu chung: may chay khong co lenh `python` trong PATH va khong co Ollama.
- Buoc tai hien: chay `python --version` hoac `ollama list`.
- Nguyen nhan goc: runtime/model chua duoc cau hinh tren may hien tai.
- Cach xu ly: dung Python runtime bundling cua Codex de chay pipeline; thiet ke
  LLM client ho tro `.env` de co the bat Ollama/OpenAI-compatible sau.
- Cach xac minh sau khi sua: chay duoc `main.py`, sinh du 50 output.
- Dieu hoc duoc: pipeline can co fallback de debug schema, nhung khi nop theo
  yeu cau LLM thi phai cau hinh model <=10B va chay lai de trace co
  `llm_enabled=true`.

## 7. Hieu biet ve luong end-to-end

Du lieu di tu `input/EC_XXX.json` vao Coordinator. Coordinator lay
`claimed_order_id`, goi Data Retrieval Tool de truy xuat order, customer, items,
payments, products va seller tu CSV. Cac domain agent phan tich tung phan va tra
ket qua ve Coordinator. Policy Agent ap dung `EC_POLICY_V2` de chon primary
issue, secondary issues, responsible parties, refund va actions. Verifier Agent
kiem tra schema/evidence/limit truoc khi ghi file output.

Chat luong duoc do bang viec output dung schema, issue dung policy, entity IDs
dung format, payment/delivery calculation dung, trace co du buoc handoff that.

## 8. Cam ket cua thanh vien

- [ ] Noi dung bao cao phan anh dung phan viec va muc hieu cua toi.
- [ ] Toi co the giai thich luong end-to-end, khong chi module minh phu trach.
- [ ] Toi khong ghi "da chay thanh cong" cho phan chua duoc kiem chung.
- [ ] Bao cao khong chua `.env`, API key, token hoac secret.
- [ ] Bao cao nay khong phai ban sao nguyen van cua bao cao thanh vien khac.

**Ho va ten:** [Dien ho va ten]
**Ngay xac nhan:** 2026-08-05
