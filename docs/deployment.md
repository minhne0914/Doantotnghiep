# Deploy Medic lên web

Tài liệu này dành cho cách deploy thực tế bằng Docker trên VPS. Cách này phù hợp với dự án hiện tại vì app dùng Django ASGI, WebSocket chat/realtime notification, MySQL và Redis.

## 1. Chuẩn bị

- Một repository GitHub đã push code mới nhất.
- Một VPS Ubuntu 22.04/24.04, tối thiểu 2 CPU, 4 GB RAM. Nếu bật TensorFlow/AI nhiều, nên dùng 4 CPU, 8 GB RAM.
- Một domain, ví dụ `medic-demo.com`.
- Docker và Docker Compose trên VPS.

## 2. Cấu hình domain

Trong trang quản lý DNS của domain, tạo:

```text
A     @      <IP_VPS>
A     www    <IP_VPS>
```

Chờ DNS cập nhật vài phút đến vài giờ.

## 3. Clone code trên server

```bash
git clone <GITHUB_REPO_URL> medic
cd medic
```

## 4. Tạo file môi trường production

```bash
cp .env.production.example .env
```

Mở `.env` và sửa tối thiểu các dòng sau:

```env
DJANGO_SECRET_KEY=<secret-key-mạnh>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=medic-demo.com,www.medic-demo.com,<IP_VPS>
DJANGO_CSRF_TRUSTED_ORIGINS=https://medic-demo.com,https://www.medic-demo.com

MYSQL_ROOT_PASSWORD=<mật-khẩu-root-mysql>
DB_PASSWORD=<mật-khẩu-db-app>

EMAIL_HOST_USER=<email-gửi-thông-báo>
EMAIL_HOST_PASSWORD=<app-password-email>
DEFAULT_FROM_EMAIL=Medic <noreply@medic-demo.com>

GEMINI_API_KEY=<key-nếu-có>
```

Tạo secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Build và chạy Docker

```bash
docker compose up -d --build
```

Container web sẽ tự chạy:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
daphne -b 0.0.0.0 -p 8000 mlhospital.asgi:application
```

Kiểm tra log:

```bash
docker compose logs -f web
```

Tạo tài khoản admin nếu chưa seed dữ liệu:

```bash
docker compose exec web python manage.py createsuperuser
```

Nếu muốn tạo dữ liệu demo tốt nghiệp:

```bash
docker compose exec web python manage.py seed_graduation_data --reset
```

## 6. Cấu hình Nginx reverse proxy

Cài Nginx:

```bash
sudo apt update
sudo apt install -y nginx
```

Tạo file `/etc/nginx/sites-available/medic`:

```nginx
server {
    listen 80;
    server_name medic-demo.com www.medic-demo.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Bật site:

```bash
sudo ln -s /etc/nginx/sites-available/medic /etc/nginx/sites-enabled/medic
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Bật HTTPS

Cài Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d medic-demo.com -d www.medic-demo.com
```

Sau khi HTTPS chạy ổn, giữ các biến này trong `.env`:

```env
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
USE_FORWARDED_PROTO=True
```

## 8. Kiểm tra sau deploy

```bash
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py test appoinment home
```

Kiểm tra thủ công trên trình duyệt:

- Đăng nhập admin.
- Đăng nhập bệnh nhân mẫu.
- Đặt lịch khám.
- Mở chat bệnh nhân-bác sĩ.
- Mở chatbot Medic AI.
- Upload ảnh sàng lọc AI nếu có model.
- Kiểm tra trang quản trị và danh sách bác sĩ.

## 9. Lưu ý production

- Không đưa `.env`, `db.sqlite3`, `media/`, backup database lên GitHub.
- Nên backup MySQL định kỳ.
- Với demo tốt nghiệp, Docker Compose hiện để `CELERY_TASK_ALWAYS_EAGER=True` để giảm số service cần vận hành. Khi chạy production thật lâu dài, nên tách thêm Celery worker và Celery beat.
- Media upload đang lưu trong volume Docker `media`. Nếu deploy lâu dài, nên dùng S3/Cloudinary hoặc backup volume đều đặn.
- WebSocket cần Nginx có header `Upgrade` và `Connection "upgrade"` như cấu hình ở trên.

