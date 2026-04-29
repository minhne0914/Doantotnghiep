# Scripts

## Cách lấy file `data/skin_cancer_model.h5`

Có 3 cách (xếp theo thứ tự khuyến nghị cho buổi bảo vệ tốt nghiệp):

### Cách 1 (Recommended): Tự train model riêng từ HAM10000

Xem phần `train_skin_cancer.py` bên dưới. An toàn về bản quyền 100%.

### Cách 2: Tải nhanh từ repo public

```
python scripts/download_skin_model.py
```

Script tự động tải file `model.h5` từ repo `kunn157/DACS_5_AI_SkinCancer`,
backup placeholder hiện tại, và verify model load được.

**Lưu ý**: Repo public nhưng không có LICENSE → cần ghi credit nguồn trong báo cáo.

### Cách 3: Test integration với placeholder

```
python scripts/create_placeholder_model.py
```

Tạo file `.h5` với kiến trúc đúng (75x100x3 → 7 class) nhưng **chưa train**
(weights random). Chỉ dùng để verify Django integration trước khi có model thật.

---

## train_skin_cancer.py

Train CNN phân loại 7 loại tổn thương da trên dataset HAM10000.

### Tải dataset HAM10000

Có 2 cách lấy dataset (~5 GB):

**A. Kaggle (dễ nhất):**
1. Tạo tài khoản Kaggle, vào https://www.kaggle.com/datasets/kmader/skin-cancer-mnist-ham10000
2. Click "Download" → giải nén vào thư mục `HAM10000/`

**B. Kaggle API (cho Colab):**
```bash
pip install kaggle
# Upload kaggle.json (lấy từ Kaggle account settings)
kaggle datasets download -d kmader/skin-cancer-mnist-ham10000
unzip -q skin-cancer-mnist-ham10000.zip -d HAM10000
```

Sau giải nén, thư mục phải có:
```
HAM10000/
  HAM10000_metadata.csv
  HAM10000_images_part_1/   (5000 ảnh .jpg)
  HAM10000_images_part_2/   (5015 ảnh .jpg)
```

### Chạy training

**Trên Google Colab (khuyến nghị, GPU miễn phí):**
1. Tạo notebook mới, đổi runtime sang GPU (Runtime → Change runtime type → T4 GPU)
2. Upload file `train_skin_cancer.py` lên Colab
3. Chạy:
```python
!pip install tensorflow scikit-learn pandas pillow matplotlib
!python train_skin_cancer.py --data-dir HAM10000 --epochs 30 --batch-size 32
```
Thời gian: ~30-60 phút trên GPU T4.

**Trên máy local (CPU - chậm):**
```bash
python scripts/train_skin_cancer.py --data-dir ./HAM10000 --epochs 30
```
Thời gian: ~6-10 giờ trên CPU.

### Output

- `skin_cancer_model.h5` — file model để deploy
- `training_history.csv` — log accuracy/loss qua từng epoch (vẽ đồ thị)
- `confusion_matrix.png` — ma trận nhầm lẫn (chèn vào báo cáo)
- `metrics.json` — tóm tắt số liệu test

### Deploy vào dự án Medic

Sau khi train xong, copy file:

```bash
cp skin_cancer_model.h5 D:/doanhieu/doanhieu/data/
```

Restart Django server. Tính năng `/skin_cancer/` sẽ tự load model qua `@lru_cache`.

### Lưu ý cho báo cáo tốt nghiệp

- Dataset HAM10000 license: **CC BY-NC-SA 4.0** - được dùng cho mục đích học thuật, phi thương mại.
- Khi viết báo cáo, cite nguồn dataset:
  > Tschandl, P., Rosendahl, C. & Kittler, H. The HAM10000 dataset: a large
  > collection of multi-source dermatoscopic images of common pigmented skin
  > lesions. Sci. Data 5, 180161 (2018).
- Test accuracy thường đạt 75-82% với CNN nhỏ; với MobileNetV2/EfficientNet có thể lên 88-92%.
