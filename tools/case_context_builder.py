from typing import Any

from tools.data_loader import DataLoader


def dataframe_to_records(dataframe) -> list[dict[str, Any]]:
    """Chuyển DataFrame thành list JSON-compatible."""
    if dataframe.empty:
        return []

    result = dataframe.copy()

    # Đưa datetime về string để LLM/JSON đọc được.
    for column in result.columns:
        if str(result[column].dtype).startswith("datetime"):
            result[column] = result[column].astype(str)
            result[column] = result[column].replace("NaT", None)

    return result.where(result.notna(), None).to_dict(orient="records")


def series_to_dict(series) -> dict[str, Any] | None:
    """Chuyển một dòng pandas Series thành dictionary JSON-compatible."""
    if series is None:
        return None

    result = {}

    for key, value in series.items():
        if hasattr(value, "isoformat"):
            result[key] = None if str(value) == "NaT" else str(value)
        else:
            result[key] = None if str(value) == "nan" else value

    return result


def build_case_context(
    case: dict[str, Any],
    loader: DataLoader,
) -> dict[str, Any]:
    """Tạo dữ liệu đầu vào chung cho các agent."""

    order_id = case["customer_request"]["claimed_order_id"]

    order = loader.get_order(order_id)
    items = loader.get_order_items(order_id)
    payments = loader.get_order_payments(order_id)

    customer = None
    if order is not None:
        customer = loader.get_customer(order["customer_id"])

    products = []

    for product_id in items["product_id"].dropna().unique():
        if product_id in loader.products_by_id.index:
            product = loader.products_by_id.loc[product_id]
            products.append(series_to_dict(product))

    return {
        "case": case,
        "order": series_to_dict(order),
        "items": dataframe_to_records(items),
        "payments": dataframe_to_records(payments),
        "customer": series_to_dict(customer),
        "products": products,
    }