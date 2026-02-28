"""
QRコード生成ユーティリティ
URL → PIL Image
"""

from PIL import Image


def generate_qr(url: str, size_px: int = 300) -> Image.Image:
    """
    URL から QR コードを生成して PIL Image で返す。
    url が空の場合はグレーのプレースホルダーを返す。
    """
    if not url or not url.strip():
        return _placeholder_qr(size_px)

    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url.strip())
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.convert("RGB")
        img = img.resize((size_px, size_px), Image.NEAREST)
        return img
    except Exception as e:
        print(f"QR生成エラー: {e}")
        return _placeholder_qr(size_px)


def _placeholder_qr(size_px: int) -> Image.Image:
    """URL未設定時のグレープレースホルダー"""
    img = Image.new("RGB", (size_px, size_px), color=(210, 210, 210))
    # 簡易QR風パターン（格子）
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    cell = size_px // 10
    for i in range(0, size_px, cell * 2):
        for j in range(0, size_px, cell * 2):
            d.rectangle([i, j, i + cell, j + cell], fill=(160, 160, 160))
    return img
