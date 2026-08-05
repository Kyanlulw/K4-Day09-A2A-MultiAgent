# Path giúp xử lý đường dẫn file/thư mục an toàn trên Windows, macOS, Linux.
from pathlib import Path

# Pandas dùng để đọc CSV và xử lý dữ liệu dạng bảng (DataFrame).
import pandas as pd


class DataLoader:
  """Nạp các file CSV Olist và cung cấp hàm tra cứu nhanh cho các agent."""

  def __init__(self, data_dir: str | Path):
      """
      Khởi tạo DataLoader.

      Args:
          data_dir: Đường dẫn đến thư mục chứa các file CSV của bộ dữ liệu Olist.
                    Có thể truyền vào chuỗi, ví dụ "data", hoặc đối tượng Path.
      """

      # Chuyển data_dir thành đối tượng Path để dễ ghép đường dẫn:
      # Path("data") / "file.csv" -> data/file.csv
      self.data_dir = Path(data_dir)

      # Đọc bảng orders.
      # Các cột thời gian được chuyển từ chuỗi sang datetime để có thể so sánh/trừ ngày.
      self.orders = self._read_csv(
          "olist_orders_dataset.csv",
          parse_dates=[
              "order_purchase_timestamp",          # Thời điểm khách tạo đơn
              "order_approved_at",                 # Thời điểm đơn được duyệt
              "order_delivered_carrier_date",      # Thời điểm seller giao cho đơn vị vận chuyển
              "order_delivered_customer_date",     # Thời điểm giao thực tế cho khách
              "order_estimated_delivery_date",     # Thời điểm dự kiến giao hàng
          ],
      )

      # Đọc bảng các item thuộc từng đơn hàng.
      # shipping_limit_date là hạn seller cần bàn giao hàng cho carrier.
      self.order_items = self._read_csv(
          "olist_order_items_dataset.csv",
          parse_dates=["shipping_limit_date"],
      )

      # Đọc bảng thanh toán.
      # Một order có thể có nhiều dòng payment, ví dụ trả bằng credit card + voucher.
      self.order_payments = self._read_csv(
          "olist_order_payments_dataset.csv"
      )

      # Đọc bảng customer.
      # customer_id thường đại diện cho một order;
      # customer_unique_id mới dùng để nhận diện cùng một khách qua nhiều lần mua.
      self.customers = self._read_csv(
          "olist_customers_dataset.csv"
      )

      # Đọc bảng thông tin sản phẩm, gồm category và các thuộc tính sản phẩm.
      self.products = self._read_csv(
          "olist_products_dataset.csv"
      )

      # Đọc bảng thông tin seller.
      self.sellers = self._read_csv(
          "olist_sellers_dataset.csv"
      )

      # Đọc bảng review của khách hàng theo order.
      self.order_reviews = self._read_csv(
          "olist_order_reviews_dataset.csv"
      )

      # Đọc bảng vị trí địa lý theo zip code.
      # Bảng này chưa cần dùng cho policy hiện tại,
      # nhưng có thể dùng để phân tích khoảng cách/địa lý sau này.
      self.geolocation = self._read_csv(
          "olist_geolocation_dataset.csv"
      )

      # Đọc bảng dịch tên category từ tiếng Bồ Đào Nha sang tiếng Anh.
      self.category_translation = self._read_csv(
          "product_category_name_translation.csv"
      )

      # Sau khi nạp dữ liệu, tạo các index/dictionary để agent tra cứu nhanh.
      self._build_indexes()

  def _read_csv(self, filename: str, **kwargs) -> pd.DataFrame:
      """
      Đọc một file CSV nằm trong data_dir.

      Args:
          filename: Tên file CSV, ví dụ: 'olist_orders_dataset.csv'.
          **kwargs: Các tùy chọn truyền tiếp vào pd.read_csv(),
                    ví dụ parse_dates.

      Returns:
          DataFrame chứa dữ liệu của file CSV.

      Raises:
          FileNotFoundError: Nếu không tìm thấy file tại đường dẫn yêu cầu.
      """

      # Ghép thư mục data với tên file.
      # Ví dụ: data_dir = "data", filename = "olist_orders_dataset.csv"
      # -> data/olist_orders_dataset.csv
      path = self.data_dir / filename

      # Kiểm tra file có tồn tại trước khi đọc để báo lỗi rõ ràng.
      if not path.exists():
          raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {path}")

      # Đọc CSV thành DataFrame.
      # **kwargs sẽ truyền các cấu hình như parse_dates vào pandas.
      return pd.read_csv(path, **kwargs)

  def _build_indexes(self) -> None:
      """
      Tạo index và dictionary cho việc tra cứu nhanh.

      Mục tiêu: không phải lọc toàn bộ DataFrame mỗi lần agent cần tìm
      thông tin của một order, customer, product hoặc seller.
      """

      # Đặt order_id làm index để lấy một order nhanh bằng:
      # self.orders_by_id.loc[order_id]
      #
      # drop=False nghĩa là vẫn giữ cột order_id trong DataFrame,
      # dù nó đã được dùng làm index.
      self.orders_by_id = self.orders.set_index("order_id", drop=False)

      # Nhóm các item theo order_id thành dictionary.
      #
      # Ví dụ:
      # {
      #   "order_A": DataFrame gồm toàn bộ item của order_A,
      #   "order_B": DataFrame gồm toàn bộ item của order_B
      # }
      #
      # sort=False giúp giữ thứ tự xuất hiện ban đầu trong CSV,
      # phù hợp yêu cầu output có thứ tự ổn định.
      #
      # copy() tạo bản sao để tránh agent sửa nhầm dữ liệu nguồn.
      self.items_by_order = {
          order_id: group.copy()
          for order_id, group in self.order_items.groupby(
              "order_id", sort=False
          )
      }

      # Nhóm các payment row theo order_id.
      # Dùng cho Payment Agent để tính tổng tiền và kiểm tra split payment.
      self.payments_by_order = {
          order_id: group.copy()
          for order_id, group in self.order_payments.groupby(
              "order_id", sort=False
          )
      }

      # Nhóm review theo order_id.
      # Có thể dùng khi muốn kiểm tra đánh giá/nội dung review của khách.
      self.reviews_by_order = {
          order_id: group.copy()
          for order_id, group in self.order_reviews.groupby(
              "order_id", sort=False
          )
      }

      # Đặt customer_id làm index để tra nhanh customer record từ order.customer_id.
      self.customers_by_id = self.customers.set_index(
          "customer_id", drop=False
      )

      # Đặt product_id làm index để tra thông tin sản phẩm từ item.product_id.
      self.products_by_id = self.products.set_index(
          "product_id", drop=False
      )

      # Đặt seller_id làm index để tra thông tin seller từ item.seller_id.
      self.sellers_by_id = self.sellers.set_index(
          "seller_id", drop=False
      )

      # Đặt tên category tiếng Bồ Đào Nha làm index.
      # Dùng để tìm tên category tiếng Anh trong bảng dịch.
      self.category_translation_by_name = (
          self.category_translation.set_index(
              "product_category_name", drop=False
          )
      )

  def get_order(self, order_id: str):
      """
      Lấy thông tin một order theo order_id.

      Returns:
          Một pandas Series chứa dữ liệu order nếu tìm thấy.
          None nếu order_id không tồn tại.
      """

      # Kiểm tra order_id có tồn tại trong index không.
      if order_id not in self.orders_by_id.index:
          return None

      # .loc[order_id] lấy đúng dòng có index là order_id.
      # .copy() tránh việc bên gọi sửa trực tiếp dữ liệu gốc.
      return self.orders_by_id.loc[order_id].copy()

  def get_order_items(self, order_id: str) -> pd.DataFrame:
      """
      Lấy toàn bộ item của một order.

      Returns:
          DataFrame chứa các item của order.
          Nếu không có item, trả về DataFrame rỗng nhưng vẫn giữ đúng các cột.
      """

      # dict.get(key, default):
      # - Có order_id trong dictionary -> trả về DataFrame item tương ứng.
      # - Không có -> trả về DataFrame rỗng.
      #
      # iloc[0:0] nghĩa là không lấy dòng nào nhưng vẫn giữ schema/cột của order_items.
      return self.items_by_order.get(
          order_id, self.order_items.iloc[0:0].copy()
      )

  def get_order_payments(self, order_id: str) -> pd.DataFrame:
      """
      Lấy toàn bộ payment row của một order.

      Returns:
          DataFrame chứa các payment row.
          Nếu không có payment, trả về DataFrame rỗng nhưng vẫn giữ đúng các cột.
      """

      # Cách xử lý tương tự get_order_items().
      # DataFrame rỗng giúp agent vẫn có thể gọi .empty, .sum(), ...
      # mà không bị lỗi NoneType.
      return self.payments_by_order.get(
          order_id, self.order_payments.iloc[0:0].copy()
      )

  def get_customer(self, customer_id: str):
      """
      Lấy thông tin customer theo customer_id.

      Returns:
          Một pandas Series chứa customer record nếu tìm thấy.
          None nếu customer_id không tồn tại.
      """

      # Kiểm tra customer_id có tồn tại trong index không.
      if customer_id not in self.customers_by_id.index:
          return None

      # Trả về một bản sao customer record để bảo vệ dữ liệu gốc.
      return self.customers_by_id.loc[customer_id].copy()