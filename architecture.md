# Architecture: Multi-Agent E-commerce Dispute Resolution

## Sơ đồ Agent

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
│                                                              │
│  ┌──────────────┐                                            │
│  │  START        │                                            │
│  └──────┬───────┘                                            │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Coordinator Agent │  Nhận case, tra cứu order, dispatch   │
│  │ (coordinator.py)  │  Access: orders CSV                    │
│  └──────┬───────────┘                                        │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Customer Agent    │  Xác định customer identity, history  │
│  │ (customer_agent)  │  Access: customers, orders CSVs       │
│  └──────┬───────────┘                                        │
│         ▼                                                    │
│  ┌──────────────────────┐                                    │
│  │ Order & Product Agent │  Items, sellers, products, cats   │
│  │ (order_product_agent) │  Access: items, products, sellers │
│  └──────┬───────────────┘                                    │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Payment Agent     │  Reconciliation & payment types       │
│  │ (payment_agent)   │  Access: payments CSV                 │
│  └──────┬───────────┘                                        │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Delivery Agent    │  Delivery variance, seller handoff    │
│  │ (delivery_agent)  │  Access: orders, items CSVs           │
│  └──────┬───────────┘                                        │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Policy Agent      │  EC_POLICY_V2 classification          │
│  │ (policy_agent)    │  Access: all agent results            │
│  └──────┬───────────┘                                        │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │ Verifier Agent    │  Schema validation, limit checks      │
│  │ (verifier_agent)  │  Access: all agent results            │
│  └──────┬───────────┘                                        │
│         ▼                                                    │
│  ┌──────────────┐                                            │
│  │  END (output) │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

## Vai trò từng Agent

| Agent | Vai trò | Quyền truy cập dữ liệu | Handoff |
|-------|---------|------------------------|---------|
| **Coordinator** | Nhận case input, tra cứu order trong dataset, khởi tạo flow | `orders` | → Customer |
| **Customer** | Xác định `customer_unique_id`, tìm lịch sử order | `customers`, `orders` | → Order & Product |
| **Order & Product** | Liệt kê items, sellers, products, categories; tính `expected_total` | `order_items`, `products`, `sellers`, `category_translation` | → Payment |
| **Payment** | Tổng hợp payment rows, đối soát `expected_total` vs `payment_total` | `order_payments` | → Delivery |
| **Delivery** | Tính `delivery_variance_hours`, `handoff_variance_hours` per seller | `orders` (timestamps), `order_items` (shipping_limit) | → Policy |
| **Policy** | Áp dụng EC_POLICY_V2: classify issue, assign responsibility, actions | Kết quả tất cả agents trên | → Verifier |
| **Verifier** | Validate schema, enforce limits (5 items, 3 sellers...), ghi output | Kết quả policy + tất cả agents | → END (file output) |

## Luồng Handoff

1. **Coordinator** nhận `EC_XXX.json`, extract `claimed_order_id`, tra cứu orders CSV
2. **Customer Agent** nhận `order_id` → tìm `customer_unique_id` → query lịch sử → trả `customer_result`
3. **Order & Product Agent** nhận `order_id` → join items + products + sellers → trả `order_product_result`
4. **Payment Agent** nhận `order_id` + `expected_total` từ Order Agent → đối soát → trả `payment_result`
5. **Delivery Agent** nhận `order_id` + `items_raw` → tính variance → trả `delivery_result`
6. **Policy Agent** nhận tất cả results → áp dụng rules theo priority → trả classification
7. **Verifier Agent** nhận mọi thứ → validate → ghi JSON output

## State Management

Sử dụng **LangGraph TypedDict State** làm shared memory:

```python
class CaseState(TypedDict):
    case_id: str
    order_id: str
    data_loader: OlistDataLoader
    order_data: dict
    customer_result: dict
    order_product_result: dict
    payment_result: dict
    delivery_result: dict
    policy_result: dict
    output: dict
    trace_steps: list
```

Mỗi node đọc state cần thiết, ghi kết quả của mình vào state, rồi LangGraph tự động chuyển sang node tiếp theo.

## Technology Stack

- **Orchestration**: LangGraph StateGraph
- **Data Processing**: pandas (load CSV 1 lần, index O(1))
- **Tracing**: Custom JSONL writer
- **Runtime**: Python 3.10+
