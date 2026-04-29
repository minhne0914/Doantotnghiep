"""Train CNN phân loại 7-class tổn thương da trên dataset HAM10000.

Mục đích: Tạo model `skin_cancer_model.h5` để dùng trong tính năng
home/skin_cancer_detector. Model được train từ public dataset HAM10000
(cấp phép CC BY-NC-SA 4.0) - bạn có toàn quyền sử dụng cho dự án học thuật.

Cách chạy:
    Local (CPU rất chậm, không khuyến khích):
        python scripts/train_skin_cancer.py --data-dir ./HAM10000 --epochs 30

    Google Colab (GPU miễn phí, ~30-90 phút):
        1. Upload notebook hoặc paste script vào cell
        2. Tải dataset từ Kaggle: https://www.kaggle.com/datasets/kmader/skin-cancer-mnist-ham10000
           Hoặc dùng Kaggle API:
              !pip install kaggle
              !kaggle datasets download -d kmader/skin-cancer-mnist-ham10000
              !unzip -q skin-cancer-mnist-ham10000.zip -d HAM10000
        3. Chạy: !python train_skin_cancer.py --data-dir HAM10000 --epochs 30 --batch-size 32
        4. Download `skin_cancer_model.h5` về máy → đặt vào `data/` của project Medic

Output:
    - skin_cancer_model.h5 : model cuối cùng để deploy
    - training_history.csv : log accuracy/loss qua từng epoch (vẽ đồ thị cho báo cáo)
    - confusion_matrix.png : ma trận nhầm lẫn trên tập test (chèn vào báo cáo)
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


# Thứ tự 7 class trùng với SKIN_LESION_CLASSES trong home/views.py.
# QUAN TRỌNG: giữ nguyên thứ tự này, nếu đổi phải update views.py.
LESION_CODES = ['akiec', 'bcc', 'bkl', 'df', 'nv', 'mel', 'vasc']
LESION_TO_INDEX = {code: i for i, code in enumerate(LESION_CODES)}
IMG_HEIGHT = 75
IMG_WIDTH = 100


def parse_args():
    parser = argparse.ArgumentParser(description='Train HAM10000 skin lesion classifier')
    parser.add_argument('--data-dir', required=True, help='Thư mục chứa HAM10000_metadata.csv và HAM10000_images_part_*/')
    parser.add_argument('--output', default='skin_cancer_model.h5', help='Tên file model output (.h5)')
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--learning-rate', type=float, default=1e-3)
    parser.add_argument('--val-split', type=float, default=0.15)
    parser.add_argument('--test-split', type=float, default=0.10)
    parser.add_argument('--seed', type=int, default=42)
    return parser.parse_args()


def find_image_path(data_dir: Path, image_id: str):
    """HAM10000 chia ảnh thành 2 thư mục: HAM10000_images_part_1 và part_2."""
    for sub in ('HAM10000_images_part_1', 'HAM10000_images_part_2', 'images'):
        candidate = data_dir / sub / f'{image_id}.jpg'
        if candidate.exists():
            return candidate
    # Fallback: tìm đệ quy
    matches = list(data_dir.rglob(f'{image_id}.jpg'))
    return matches[0] if matches else None


def load_dataset(data_dir: Path):
    """Đọc metadata + ảnh thành numpy arrays X (n,75,100,3), y (n,)."""
    metadata_path = data_dir / 'HAM10000_metadata.csv'
    if not metadata_path.exists():
        raise FileNotFoundError(
            f'Không tìm thấy {metadata_path}. Hãy giải nén HAM10000 đúng vào --data-dir.'
        )

    df = pd.read_csv(metadata_path)
    print(f'[i] Tổng số ảnh metadata: {len(df)}')
    print(df['dx'].value_counts())

    images = []
    labels = []
    skipped = 0
    for _, row in df.iterrows():
        path = find_image_path(data_dir, row['image_id'])
        if path is None:
            skipped += 1
            continue
        try:
            img = Image.open(path).convert('RGB').resize((IMG_WIDTH, IMG_HEIGHT))
        except Exception as e:
            print(f'  Bỏ qua {path}: {e}')
            skipped += 1
            continue
        images.append(np.asarray(img, dtype=np.float32))
        labels.append(LESION_TO_INDEX[row['dx']])

    print(f'[i] Đã load {len(images)} ảnh ({skipped} bỏ qua)')
    X = np.stack(images, axis=0)
    y = np.array(labels, dtype=np.int64)
    return X, y


def per_image_normalize(X):
    """Normalize per-image (mean/std) - giống pipeline inference trong home/views.py."""
    out = np.empty_like(X)
    for i in range(len(X)):
        m = X[i].mean()
        s = X[i].std() or 1.0
        out[i] = (X[i] - m) / s
    return out


def build_model(num_classes=7):
    """CNN nhỏ phù hợp dataset 10k ảnh. Có thể thay bằng MobileNetV2 nếu muốn cao hơn."""
    import tensorflow as tf
    from tensorflow.keras import layers, models, regularizers

    inp = layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))
    x = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(inp)
    x = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)

    x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
    x = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.30)(x)

    x = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x)
    x = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.30)(x)

    x = layers.Flatten()(x)
    x = layers.Dense(256, activation='relu', kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.50)(x)
    out = layers.Dense(num_classes, activation='softmax')(x)

    model = models.Model(inp, out, name='ham10000_cnn')
    return model


def stratified_split(X, y, val_split, test_split, seed):
    from sklearn.model_selection import train_test_split

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=val_split + test_split, stratify=y, random_state=seed
    )
    rel_test = test_split / (val_split + test_split)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=rel_test, stratify=y_temp, random_state=seed
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def compute_class_weights(y):
    """HAM10000 mất cân bằng nghiêm trọng (nv chiếm ~67%). Cần class_weight."""
    from sklearn.utils.class_weight import compute_class_weight

    classes = np.arange(len(LESION_CODES))
    weights = compute_class_weight('balanced', classes=classes, y=y)
    return {int(c): float(w) for c, w in zip(classes, weights)}


def plot_confusion(y_true, y_pred, output_path):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from sklearn.metrics import confusion_matrix
    except ImportError:
        print('[!] matplotlib/sklearn chưa cài, bỏ qua confusion matrix')
        return

    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, cmap='Blues')
    ax.set_xticks(range(len(LESION_CODES)))
    ax.set_yticks(range(len(LESION_CODES)))
    ax.set_xticklabels(LESION_CODES, rotation=45)
    ax.set_yticklabels(LESION_CODES)
    ax.set_xlabel('Predicted')
    ax.set_ylabel('True')
    ax.set_title('Confusion matrix (test set)')
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm[i, j]), ha='center', va='center',
                    color='white' if cm[i, j] > cm.max() / 2 else 'black')
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    print(f'[i] Đã lưu confusion matrix: {output_path}')


def main():
    args = parse_args()
    np.random.seed(args.seed)

    # Defer TensorFlow import để --help nhanh
    import tensorflow as tf
    tf.random.set_seed(args.seed)

    data_dir = Path(args.data_dir).expanduser().resolve()
    print(f'[i] Đọc dataset từ {data_dir}')
    X, y = load_dataset(data_dir)
    print(f'[i] Bắt đầu split (val={args.val_split}, test={args.test_split})')
    X_train, X_val, X_test, y_train, y_val, y_test = stratified_split(
        X, y, args.val_split, args.test_split, args.seed
    )

    print(f'[i] Normalize ảnh (per-image mean/std)')
    X_train = per_image_normalize(X_train)
    X_val = per_image_normalize(X_val)
    X_test = per_image_normalize(X_test)

    class_weights = compute_class_weights(y_train)
    print(f'[i] Class weights: {class_weights}')

    print('[i] Building model')
    model = build_model(num_classes=len(LESION_CODES))
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.learning_rate),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy', tf.keras.metrics.TopKCategoricalAccuracy(k=2)],
    )
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_accuracy', patience=8, restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_accuracy', factor=0.5, patience=3, min_lr=1e-6, verbose=1
        ),
        tf.keras.callbacks.CSVLogger('training_history.csv'),
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=2,
    )

    print('\n[i] Đánh giá trên test set:')
    test_loss, test_acc, *rest = model.evaluate(X_test, y_test, verbose=0)
    print(f'    Test accuracy:        {test_acc:.4f}')
    print(f'    Test top-2 accuracy:  {rest[0]:.4f}' if rest else '')
    print(f'    Test loss:            {test_loss:.4f}')

    y_pred_proba = model.predict(X_test, verbose=0)
    y_pred = y_pred_proba.argmax(axis=1)
    plot_confusion(y_test, y_pred, 'confusion_matrix.png')

    metrics_summary = {
        'test_accuracy': float(test_acc),
        'test_loss': float(test_loss),
        'classes': LESION_CODES,
        'epochs_trained': len(history.history.get('loss', [])),
        'best_val_accuracy': float(max(history.history.get('val_accuracy', [0]))),
    }
    with open('metrics.json', 'w', encoding='utf-8') as f:
        json.dump(metrics_summary, f, indent=2, ensure_ascii=False)
    print(f'[i] Metrics saved -> metrics.json')

    print(f'[i] Saving model -> {args.output}')
    model.save(args.output)
    print('[OK] Done. Copy file model + đặt vào project_medic/data/skin_cancer_model.h5')


if __name__ == '__main__':
    main()
