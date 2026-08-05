from typing import Any

from tools.llm_client import ask_llm


CUSTOMER_AGENT_PROMPT = """
Bạn là Customer Investigation Agent cho khiếu nại Olist.

Chỉ sử dụng dữ liệu được cung cấp.
Không bịa dữ kiện và không suy luận ngoài dữ liệu.

Nhiệm vụ:
- Lấy customer_unique_id từ customer record.
- Báo cáo customer_id và order_id hiện tại.
- Chỉ nêu facts về customer có thể kiểm chứng.

Không được:
- Quyết định primary issue.
- Đề xuất refund.
- Chỉ định bên chịu trách nhiệm.
- Tạo ra related_order_id không có trong input.

Trả về JSON đúng schema:

{
  "customer_unique_id": "string hoặc null",
  "current_order_id": "string hoặc null",
  "customer_id": "string hoặc null",
  "evidence_summary": ["fact có căn cứ từ context"]
}
"""


def run_customer_agent(
    case_context: dict[str, Any],
) -> dict[str, Any]:
    """Gửi phần customer context cho LLM."""

    payload = {
        "case": case_context["case"],
        "order": case_context["order"],
        "customer": case_context["customer"],
    }

    return ask_llm(CUSTOMER_AGENT_PROMPT, payload)