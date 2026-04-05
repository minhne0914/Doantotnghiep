   # Hướng Dẫn Cài Đặt và Chạy Dự Án (Từ A-Z)

Tài liệu này tổng hợp toàn bộ các bước cần thiết để thiết lập môi trường, cài đặt thư viện, cấu hình cơ sở dữ liệu và khởi chạy dự án *Django Machine Health Prediction Website*.

---

## 1. Yêu Cầu Hệ Thống (Môi trường)
- *python -m venv venv
- **MySQL/MariaDB:** Yêu cầu cài đặt XAMPP, WAMP hoặc MySQL Server độc lập để chạy Database.

---

## 2. Cài Đặt Thư Viện (Packages)

Mở Terminal / Command Prompt tại thư mục dự án (nơi chứa file `manage.py`) và chạy câu lệnh sau để cài đặt toàn bộ các thư viện cần dùng cho cả web (appoinment/accounts) và AI (home):

```bash
pip install django numpy pandas scikit-learn Pillow tensorflow mysqlclient
```

*Trong đó:*
- `django`: Bộ web framework chính.
- `numpy`, `pandas`, `scikit-learn`, `Pillow`, `tensorflow`: Dùng cho Machine Learning và chẩn đoán bệnh tật (ung thư, tiểu đường, viêm phổi,...).
- `mysqlclient`: Driver để Django kết nối mượt mà với CSDL MySQL (Nếu gặp lỗi khi cài mysqlclient trên Windows, bạn có thể cân nhắc dùng `pymysql` như một giải pháp thay thế tạm thời).

---

## 3. Thiết Lập Cơ Sở Dữ Liệu (Database MySQL)

Ứng dụng đang cấu hình kết nối tới MySQL với tên CSDL là `db_healthcare`, user `root` và mật khẩu để trống.

**Bước 3.1: Mở Server MySQL**
Bật XAMPP hoặc WAMP Control Panel, nhấn **Start** ở module MySQL.

**Bước 3.2: Tạo Database trống**
- Truy cập vào **phpMyAdmin**: [http://localhost/phpmyadmin](http://localhost/phpmyadmin)
- Bấm vào mục **New** (Tạo mới) ở thanh bên trái.
- Nhập tên CSDL là: `db_healthcare`
- Chọn bảng mã (Collation): `utf8mb4_unicode_ci` (hoặc để mặc định).
- Nhấn nút **Create** (Tạo).

**Bước 3.3: Chạy Migrations tạo cấu trúc bảng**
Quay trở lại Terminal/CMD tại thư mục dự án, chạy lần lượt hai lệnh sau:

```bash
python manage.py makemigrations
```
*(Lệnh này đọc các models và lên lịch khởi tạo các bảng SQL).*

```bash
python manage.py migrate
```
*(Lệnh này chính thức đổ các bảng như user, appointment vào MySQL).*

---

## 4. Khởi Tạo Tài Khoản Quản Trị Hệ Thống (Superuser)

Để đăng nhập vào trang Admin của Django và quản lý dữ liệu gốc, bạn cần tạo một tài khoản Superuser. Ở Terminal, chạy lệnh:

```bash
python manage.py createsuperuser
```
Làm theo các bước trên màn hình:
- Nhập **Email**: (ví dụ: `admin@gmail.com` - do project cấu hình dùng email thay cho username)
- Nhập **Password**: (Mật khẩu khi gõ sẽ bị ẩn đi, cứ nhập và nhấn Enter)
- Nhập lại Password để xác nhận.

---

## 5. Chạy Dự Án

Khi Database và thư viện đã sẵn sàng, hãy khởi động server nội bộ bằng lệnh:

```bash
python manage.py runserver
```

**Hoàn thành!** Bây giờ bạn có thể trải nghiệm website:
- **Trang chính (Dự đoán bệnh, Đặt lịch):** Mở trình duyệt và truy cập `http://localhost:8000/`
- **Trang Quản trị (Admin):** Truy cập `http://localhost:8000/admin/` (Đăng nhập bằng email và pass vừa tạo ở Bước 4).

---

## ⚙️ Xử lý lỗi thường gặp (Troubleshooting)

1. **Lỗi `ModuleNotFoundError: No module named '...'` khi chạy server:**
   - Nghĩa là bạn cài thiếu thư viện. Hãy kiểm tra lại câu lệnh ở Bước 2 hoặc cài đặt riêng thư viện bị báo thiếu (ví dụ: `pip install django-crispy-forms` nếu có).

2. **Lỗi `django.db.utils.OperationalError: (1049, "Unknown database 'db_healthcare'")`:**
   - Bạn quên thực hiện Bước 3.2. Hãy mở phpMyAdmin và tạo database `db_healthcare` trước khi chạy `migrate`.

3. **Lỗi mô hình `h5` không load được (`ImportError` hoặc liên quan đến Keras):**
   - Đảm bảo bạn đã cài `tensorflow`. Nếu phiên bản tensorflow quá mới không tương thích với file h5 cũ, bạn hãy cài lại phiên bản thấp hơn: `pip install tensorflow==2.10.0` (tùy thuộc vào version lúc training mô hình).
