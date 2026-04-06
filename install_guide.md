# Huong Dan Cai Dat Va Chay Du An

Tai lieu nay da duoc cap nhat theo trang thai codebase ngay 06/04/2026 va su dung virtualenv chuan hoa `.venv-runtime`.

## 1. Yeu cau

- Windows + PowerShell
- Python 3.10.x
- Redis neu ban muon dung notification queue va websocket theo cau hinh production-like
- Ket noi Internet khi can cai package

## 2. Virtualenv chuan hoa

Neu repo da co san `.venv-runtime`, ban co the dung lai truc tiep:

```powershell
Set-Location D:\doanhieu\doanhieu
.venv-runtime\Scripts\Activate.ps1
python -V
```

Neu can tao moi:

```powershell
Set-Location D:\doanhieu\doanhieu
C:\Users\Admin\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv-runtime
.venv-runtime\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Cau hinh bien moi truong

Tao file `.env` tu `.env.example`:

```powershell
Copy-Item .env.example .env
```

Gia tri toi thieu de chay local:

```env
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
USE_REDIS_SERVICES=False
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
CHANNEL_LAYER_BACKEND=inmemory
CELERY_TASK_ALWAYS_EAGER=True
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

Ghi chu:

- File `.env` nay da duoc `settings.py` tu dong nap khi app khoi dong.
- `CHANNEL_LAYER_BACKEND=inmemory` phu hop khi ban khong muon chay Redis local.
- `CELERY_TASK_ALWAYS_EAGER=True` phu hop cho local/debug don gian.
- Muon dung chat Gemini thi dien `GEMINI_API_KEY`.

## 4. Migration

```powershell
python manage.py migrate
```

Neu can tao admin:

```powershell
python manage.py createsuperuser
```

## 5. Chay test

```powershell
python manage.py test
```

Trang thai da xac minh:

- Test suite hien tai pass `13/13`
- `python manage.py check` pass
- Boot server va goi HTTP local tra `200`

## 6. Chay server

```powershell
python manage.py runserver 127.0.0.1:8000
```

Neu cong `8000` dang ban:

```powershell
python manage.py runserver 127.0.0.1:8001
```

## 7. Redis, Celery, Channels

Neu ban muon chay theo mode day du hon:

```env
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
CELERY_TASK_ALWAYS_EAGER=False
CHANNEL_LAYER_BACKEND=redis
CHANNEL_REDIS_URL=redis://127.0.0.1:6379/2
```

Va mo them terminal:

```powershell
.venv-runtime\Scripts\Activate.ps1
celery -A mlhospital worker -l info
```

## 8. Gemini chat

Project da duoc doi tu SDK cu `google-generativeai` sang SDK moi `google-genai`, vi SDK moi cai duoc chung voi stack `tensorflow/protobuf` hien tai.

Can cau hinh:

```env
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Neu de trong `GEMINI_API_KEY`, giao dien chat van mo duoc nhung API chat se tra loi `503` voi thong bao chua cau hinh.

## 9. Loi thuong gap

1. `python` khong chay trong virtualenv
   Dung truc tiep `D:\doanhieu\doanhieu\.venv-runtime\Scripts\python.exe`.

2. Websocket/Celery loi ket noi Redis
   Kiem tra Redis dang chay, hoac doi local env sang:
   `USE_REDIS_SERVICES=False`
   `CHANNEL_LAYER_BACKEND=inmemory`
   `CELERY_TASK_ALWAYS_EAGER=True`

3. Chat Gemini loi
   Kiem tra `GEMINI_API_KEY` hop le va outbound network duoc phep.

4. Cong `8000` da duoc dung
   Chuyen sang cong khac, vi du:
   `python manage.py runserver 127.0.0.1:8001`
