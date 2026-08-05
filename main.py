import json
from pathlib import Path

from agents.customer_agent import run_customer_agent
from agents.delivery_agent import run_delivery_agent
from agents.order_product_agent import run_order_product_agent
from agents.payment_agent import run_payment_agent
from agents.policy_agent import run_policy_agent

# Hàm này chỉ gom dữ liệu đã tra cứu thành một context JSON-compatible.
# Nó không phân loại khiếu nại hoặc đưa ra quyết định nghiệp vụ.
from tools.case_context_builder import build_case_context
# DataLoader đọc 9 CSV một lần và cung cấp các hàm tra cứu theo ID.
from tools.data_loader import DataLoader


# Lấy đúng thư mục chứa file main.py, không phụ thuộc terminal đang đứng ở đâu.
PROJECT_ROOT = Path(__file__).parent
# Đường dẫn đến dữ liệu nguồn và các case đầu vào.
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"


def load_all_cases(input_dir: Path) -> list[dict]:
    """Đọc toàn bộ EC_XXX.json theo thứ tự tên file ổn định."""
    cases = []

    # glob tìm các file EC_001.json ... EC_050.json.
    # sorted đảm bảo thứ tự xử lý luôn giống nhau giữa các lần chạy.
    for case_path in sorted(input_dir.glob("EC_*.json")):
        # Input sử dụng UTF-8 vì có nội dung tiếng Việt.
        with case_path.open("r", encoding="utf-8") as file:
            cases.append(json.load(file))

    return cases


def main() -> None:
    # Nạp toàn bộ 9 CSV đúng một lần. Không nạp lại cho từng case.
    loader = DataLoader(DATA_DIR)

    # Đọc toàn bộ 50 case JSON vào bộ nhớ.
    cases = load_all_cases(INPUT_DIR)

    print(f"Loaded {len(cases)} cases.")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Duyệt từng case để tạo hồ sơ dữ liệu chung cho các LLM agent ở bước sau.
    for case in cases:
        # build_case_context chỉ lấy và chuyển đổi dữ liệu thô:
        # order, items, payments, customer và products.
        context = build_case_context(case, loader)

        # Customer Agent gọi Groq bằng API key trong .env.
        # Agent chỉ trích xuất facts về khách hàng, không ra quyết định policy.
        customer_result = run_customer_agent(context)

        # Order & Product Agent trích xuất item, seller, product và category facts.
        # Agent này cũng không phân loại khiếu nại hoặc tính refund.
        order_product_result = run_order_product_agent(context)

        # Payment Agent only reconciles provided monetary facts.
        payment_result = run_payment_agent(context)

        # Delivery Agent analyses the supplied timestamp and handoff facts.
        delivery_result = run_delivery_agent(context)
        final_output = run_policy_agent(
            context, customer_result, order_product_result, payment_result, delivery_result
        )
        output_path = OUTPUT_DIR / f"{context['case']['case_id']}.json"
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(final_output, file, ensure_ascii=False, indent=2)

        # Các dòng dưới đây chỉ kiểm tra dữ liệu đã nạp; không suy luận policy.
        print(f"\nCase: {context['case']['case_id']}")
        print(f"Order exists: {context['order'] is not None}")
        print(f"Items: {len(context['items'])}")
        print(f"Payments: {len(context['payments'])}")
        print(f"Products: {len(context['products'])}")
        print("Customer Agent result:")
        print(json.dumps(customer_result, ensure_ascii=False, indent=2))
        print("Order & Product Agent result:")
        print(json.dumps(order_product_result, ensure_ascii=False, indent=2))
        print("Payment Agent result:")
        print(json.dumps(payment_result, ensure_ascii=False, indent=2))
        print("Delivery Agent result:")
        print(json.dumps(delivery_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
