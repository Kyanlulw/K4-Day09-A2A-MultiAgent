import json
from pathlib import Path

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

    # Duyệt từng case để tạo hồ sơ dữ liệu chung cho các LLM agent ở bước sau.
    for case in cases:
        # build_case_context chỉ lấy và chuyển đổi dữ liệu thô:
        # order, items, payments, customer và products.
        context = build_case_context(case, loader)

        # Các dòng dưới đây chỉ kiểm tra dữ liệu đã nạp; không suy luận policy.
        print(f"\nCase: {context['case']['case_id']}")
        print(f"Order exists: {context['order'] is not None}")
        print(f"Items: {len(context['items'])}")
        print(f"Payments: {len(context['payments'])}")
        print(f"Products: {len(context['products'])}")


if __name__ == "__main__":
    main()
