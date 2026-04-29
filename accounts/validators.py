"""Validators dùng chung cho dự án Medic.

Tập trung tại đây để các app (accounts, appoinment, home) có thể tái sử dụng
thay vì lặp logic kiểm tra file/ảnh ở nhiều chỗ.
"""

import os
import re

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


# Định dạng ảnh hợp lệ cho avatar / ảnh hồ sơ
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_CONTENT_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
}

# 5 MB ảnh là quá đủ cho avatar
DEFAULT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024

# Số điện thoại Việt Nam: bắt đầu bằng 0 hoặc +84, độ dài 9–11 chữ số sau prefix.
PHONE_NUMBER_RE = re.compile(r'^(\+?84|0)\d{9,10}$')


@deconstructible
class FileSizeValidator:
    """Kiểm tra kích thước file upload (đơn vị: bytes).

    Dùng được cho ImageField/FileField:
        image = models.ImageField(validators=[FileSizeValidator(5 * 1024 * 1024)])
    """

    message = _('File vượt quá giới hạn dung lượng cho phép (%(limit_mb).1f MB).')
    code = 'file_too_large'

    def __init__(self, max_bytes=DEFAULT_IMAGE_MAX_BYTES):
        self.max_bytes = int(max_bytes)

    def __call__(self, value):
        size = getattr(value, 'size', None)
        if size is None:
            return
        if size > self.max_bytes:
            raise ValidationError(
                self.message,
                code=self.code,
                params={'limit_mb': self.max_bytes / (1024 * 1024)},
            )

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_bytes == other.max_bytes


@deconstructible
class ImageContentTypeValidator:
    """Kiểm tra MIME type & extension cho ImageField.

    Mặc định chỉ chấp nhận JPG/PNG/WEBP để tránh upload file thực thi (.exe, .svg với JS, ...).
    """

    message = _('Chỉ chấp nhận ảnh định dạng JPG/PNG/WEBP.')
    code = 'invalid_image_type'

    def __init__(self, allowed_content_types=None, allowed_extensions=None):
        self.allowed_content_types = set(allowed_content_types or ALLOWED_IMAGE_CONTENT_TYPES)
        self.allowed_extensions = {ext.lower() for ext in (allowed_extensions or ALLOWED_IMAGE_EXTENSIONS)}

    def __call__(self, value):
        name = getattr(value, 'name', '') or ''
        ext = os.path.splitext(name)[1].lower()
        if ext and ext not in self.allowed_extensions:
            raise ValidationError(self.message, code=self.code)

        # content_type chỉ có khi đang upload (UploadedFile); với file đã lưu thì bỏ qua.
        content_type = getattr(value, 'content_type', None)
        if content_type and content_type.lower() not in self.allowed_content_types:
            raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return (
            isinstance(other, ImageContentTypeValidator)
            and self.allowed_content_types == other.allowed_content_types
            and self.allowed_extensions == other.allowed_extensions
        )


def validate_phone_number(value):
    """Kiểm tra định dạng số điện thoại Việt Nam (cho phép +84 hoặc 0)."""

    if not value:
        return
    cleaned = value.strip().replace(' ', '').replace('-', '')
    if not PHONE_NUMBER_RE.match(cleaned):
        raise ValidationError(
            _('Số điện thoại không hợp lệ. Ví dụ hợp lệ: 0901234567 hoặc +84901234567.'),
            code='invalid_phone',
        )


# Bộ validator gọn cho ImageField của model
def get_avatar_validators(max_bytes=DEFAULT_IMAGE_MAX_BYTES):
    return [
        FileSizeValidator(max_bytes=max_bytes),
        ImageContentTypeValidator(),
    ]
