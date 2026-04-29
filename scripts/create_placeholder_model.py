"""Tạo file model.h5 placeholder để test tích hợp.

Model này có đúng kiến trúc input/output (shape 75x100x3 -> 7-class softmax)
nhưng KHÔNG được train - random weights. Dùng để verify Django integration
trước khi có model thật từ HAM10000.

Sau khi train model thật bằng `train_skin_cancer.py`, ghi đè file này lên
`data/skin_cancer_model.h5`.

Cách chạy:
    python scripts/create_placeholder_model.py
"""

import os
from pathlib import Path

# Tắt log GPU verbose
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

import tensorflow as tf
from tensorflow.keras import layers, models


IMG_HEIGHT = 75
IMG_WIDTH = 100
NUM_CLASSES = 7

OUTPUT_PATH = Path(__file__).resolve().parent.parent / 'data' / 'skin_cancer_model.h5'


def build_placeholder_model():
    """CNN nhỏ giống kiến trúc trong train_skin_cancer.py - chỉ chưa train."""
    inp = layers.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))
    x = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(inp)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Flatten()(x)
    x = layers.Dense(64, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    out = layers.Dense(NUM_CLASSES, activation='softmax')(x)

    model = models.Model(inp, out, name='skin_cancer_placeholder')
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy'],
    )
    return model


def main():
    print('[i] Building placeholder skin cancer model...')
    model = build_placeholder_model()
    model.summary()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(OUTPUT_PATH)
    print(f'[OK] Saved placeholder model to: {OUTPUT_PATH}')
    print(f'[!]  Lưu ý: model này CHƯA train, dự đoán sẽ random.')
    print(f'[!]  Dùng để verify integration. Train thật bằng scripts/train_skin_cancer.py.')


if __name__ == '__main__':
    main()
