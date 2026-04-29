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

## Tinh nang ML screening

Medic ho tro 5 tinh nang sang loc bang AI:

| Endpoint | Mo hinh | Input |
|----------|---------|-------|
| `/diabetes/` | scikit-learn (.pkl) | 8 chi so suc khoe |
| `/breast/` | scikit-learn (.pkl) | 5 chi so te bao |
| `/heart/` | scikit-learn (.pkl) | 13 chi so tim mach |
| `/kidney/` | rule-based scoring | 6 chi so xet nghiem |
| `/pneumonia_detector/` | TensorFlow CNN (.h5) | Anh X-quang phoi |
| `/skin_cancer/` | TensorFlow CNN (.h5) | Anh ton thuong da (7 lop) |

### Tinh nang skin cancer (HAM10000)

- Phan loai 7 lop ton thuong da: `akiec, bcc, bkl, df, nv, mel, vasc`.
- Model file dat tai `data/skin_cancer_model.h5` (hoac dat ten qua `SKIN_CANCER_MODEL_FILE`).
- De tu train model rieng (tranh van de ban quyen), xem [scripts/README.md](scripts/README.md).
  Train tren Google Colab voi dataset HAM10000 mat 30-60 phut.
- Pipeline inference: resize 100x75 -> normalize per-image (mean/std) -> CNN predict.

## Ghi chu

- Virtualenv cu `.venv/` trong repo da hong interpreter; moi huong dan chay nen dung `.venv-runtime/`.
- Neu ban muon tao lai virtualenv moi, xem [install_guide.md](/D:/doanhieu/doanhieu/install_guide.md).
- Sau khi pull code moi: chay `python manage.py makemigrations && python manage.py migrate` de cap nhat `db_index` moi them vao cac model.
