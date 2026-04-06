# Medic Django Project

Du an nay la mot he thong Django cho dat lich kham, EMR, thong bao realtime/email/SMS va cac tinh nang ML screening.

## Chay nhanh

1. Tao file `.env` tu [`.env.example`](/D:/doanhieu/doanhieu/.env.example).
   Django da duoc cap nhat de tu dong nap file `.env` nay khi khoi dong.
2. Dung virtualenv da chuan hoa:

```powershell
D:\doanhieu\doanhieu\.venv-runtime\Scripts\Activate.ps1
```

3. Cai dependencies neu may ban chua co:

```powershell
python -m pip install -r requirements.txt
```

4. Apply migration:

```powershell
python manage.py migrate
```

5. Chay test:

```powershell
python manage.py test
```

6. Chay server:

```powershell
python manage.py runserver 127.0.0.1:8000
```

## Dich vu di kem

- Local debug mac dinh khong can Redis. Project se dung `CHANNEL_LAYER_BACKEND=inmemory` va `CELERY_TASK_ALWAYS_EAGER=True` khi `USE_REDIS_SERVICES=False`.
- Redis chi can chay neu ban muon dung Celery, email reminder, SMS queue va Channels realtime theo kieu production-like.
- Gemini chat can `GEMINI_API_KEY`. SDK dang dung la `google-genai`.

## Bien moi truong quan trong

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `USE_REDIS_SERVICES`
- `EMAIL_*`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CHANNEL_LAYER_BACKEND`
- `CHANNEL_REDIS_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `TWILIO_*`

## Ghi chu

- Virtualenv cu `.venv/` trong repo da hong interpreter; moi huong dan chay nen dung `.venv-runtime/`.
- Neu ban muon tao lai virtualenv moi, xem [install_guide.md](/D:/doanhieu/doanhieu/install_guide.md).
