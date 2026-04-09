"""Görsel sıkıştırma modülü - Pillow ile görselleri WebP formatına sıkıştırır."""

import io
from PIL import Image

MAX_DIMENSION = 2560
TARGET_SIZE_KB = 1000
MIN_QUALITY = 60


def compress_image(file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """Görseli WebP formatında sıkıştırır. (bytes, content_type) döner."""
    img = Image.open(io.BytesIO(file_bytes))

    # Çok büyük boyutları küçült (en/boy oranını koru)
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # RGBA korunur (WebP seffafligi destekler), diger modlar RGB'ye
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    output = _compress_to_target(img)
    return output.getvalue(), "image/webp"


def _compress_to_target(img: Image.Image) -> io.BytesIO:
    """Binary search ile kaliteyi ayarlayarak hedef boyuta sıkıştırır."""
    low, high = MIN_QUALITY, 90

    # Önce en yüksek kalitede dene - zaten küçükse direkt dön
    best = _save_webp(img, high)
    if len(best.getvalue()) <= TARGET_SIZE_KB * 1024:
        return best

    # Binary search
    result = best
    for _ in range(8):
        mid = (low + high) // 2
        buf = _save_webp(img, mid)
        size_kb = len(buf.getvalue()) / 1024

        if size_kb > TARGET_SIZE_KB:
            high = mid - 1
        else:
            result = buf
            low = mid + 1

        if low > high:
            break

    return result


def _save_webp(img: Image.Image, quality: int) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=4)
    buf.seek(0)
    return buf
