"""Tải model skin cancer thật từ repo DACS_5_AI_SkinCancer.

Mặc định ghi đè file `data/skin_cancer_model.h5` (placeholder hiện tại).
Nếu repo gốc thay đổi đường dẫn, bạn có thể truyền --url khác.

Cách chạy:
    python scripts/download_skin_model.py

LƯU Ý PHÁP LÝ:
- Repo gốc (https://github.com/kunn157/DACS_5_AI_SkinCancer) public nhưng
  KHÔNG có LICENSE file → mặc định "all rights reserved" theo GitHub.
- Sử dụng cho mục đích học tập / dự án cá nhân thường được tolerate, nhưng
  để an toàn với buổi bảo vệ tốt nghiệp:
    1. Liên hệ tác giả qua GitHub Issue/Email xin phép có ghi credit, HOẶC
    2. Tự train model riêng bằng `scripts/train_skin_cancer.py` trên dataset
       HAM10000 (license CC BY-NC-SA 4.0, miễn phí cho học thuật).
"""

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path


DEFAULT_URL = 'https://github.com/kunn157/DACS_5_AI_SkinCancer/raw/main/models/model.h5'
OUTPUT_PATH = Path(__file__).resolve().parent.parent / 'data' / 'skin_cancer_model.h5'


def download_with_progress(url, dest):
    """Download URL -> dest với progress bar đơn giản."""

    def _hook(block_num, block_size, total_size):
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        pct = min(downloaded * 100 / total_size, 100)
        mb_done = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        bar = '#' * int(pct / 2)
        sys.stdout.write(f'\r[{bar:<50}] {pct:5.1f}%  {mb_done:6.1f}/{mb_total:6.1f} MB')
        sys.stdout.flush()

    print(f'[i] Downloading: {url}')
    urllib.request.urlretrieve(url, dest, reporthook=_hook)
    sys.stdout.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=DEFAULT_URL,
                        help='URL trực tiếp tới file .h5 (mặc định: repo DACS_5_AI_SkinCancer)')
    parser.add_argument('--output', default=str(OUTPUT_PATH),
                        help=f'Đường dẫn lưu file (mặc định: {OUTPUT_PATH})')
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Backup file cũ nếu có (placeholder)
    if output_path.exists():
        backup = output_path.with_suffix('.h5.backup')
        shutil.copy2(output_path, backup)
        print(f'[i] Đã backup file cũ -> {backup}')

    try:
        download_with_progress(args.url, output_path)
    except Exception as e:
        print(f'[!] Download thất bại: {e}')
        print(f'[!] Bạn có thể tải thủ công tại: {args.url}')
        print(f'[!] Sau đó copy vào: {output_path}')
        sys.exit(1)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f'[OK] Saved {size_mb:.1f} MB -> {output_path}')

    # Quick verify model load được
    try:
        os_env_set = False
        try:
            import os
            os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
            os_env_set = True
        except Exception:
            pass

        import tensorflow as tf
        model = tf.keras.models.load_model(output_path, compile=False)
        print(f'[OK] Verify: input_shape={model.input_shape}, output_shape={model.output_shape}')
        if model.output_shape[-1] != 7:
            print(f'[!] Cảnh báo: model output {model.output_shape[-1]} class, không phải 7. '
                  f'Đảm bảo dùng model đúng cho HAM10000.')
    except ImportError:
        print('[i] (Bỏ qua verify - tensorflow chưa cài)')
    except Exception as e:
        print(f'[!] Không load được file: {e}')
        print(f'[!] Có thể file download bị lỗi hoặc URL không phải .h5 thật.')


if __name__ == '__main__':
    main()
