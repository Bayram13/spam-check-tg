"""CAPTCHA şəkli və variantların yaradılması."""
import os
import random
import string
import io

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Qarışıq görünməyən simvollar (0/O, 1/I/L kimi)
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 5

# Font: əvvəlcə layihə ilə gələn font, sonra sistem fontları (Render-də sistem
# fontu olmaya bilər, ona görə DejaVuSans-Bold.ttf layihəyə daxil edilib).
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_CANDIDATES = [
    os.path.join(_HERE, "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]


def _load_font(size: int):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def random_code(length: int = CODE_LEN) -> str:
    return "".join(random.choices(ALPHABET, k=length))


def make_captcha_image(text: str) -> io.BytesIO:
    """Mətni təhrif olunmuş CAPTCHA şəkli kimi qaytarır (BytesIO)."""
    w, h = 60 + 48 * len(text), 120
    img = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(img)
    font = _load_font(58)

    # Səs-küy xətləri
    for _ in range(9):
        d.line(
            [(random.randint(0, w), random.randint(0, h)) for _ in range(2)],
            fill=tuple(random.randint(120, 200) for _ in range(3)),
            width=2,
        )

    # Simvollar (hər biri fərqli mövqe/rəng/bucaqda)
    x = 25
    for ch in text:
        ch_img = Image.new("RGBA", (60, 80), (0, 0, 0, 0))
        cd = ImageDraw.Draw(ch_img)
        col = tuple(random.randint(0, 90) for _ in range(3))
        cd.text((5, 5), ch, font=font, fill=col)
        ch_img = ch_img.rotate(random.randint(-25, 25), expand=1)
        img.paste(ch_img, (x, random.randint(10, 30)), ch_img)
        x += 48

    # Nöqtəvi səs-küy
    for _ in range(int(w * h * 0.03)):
        img.putpixel(
            (random.randint(0, w - 1), random.randint(0, h - 1)),
            tuple(random.randint(100, 220) for _ in range(3)),
        )

    img = img.filter(ImageFilter.SMOOTH)

    buf = io.BytesIO()
    buf.name = "captcha.png"
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def make_options(correct: str, count: int = 4) -> list[str]:
    """Düzgün cavab + bənzər saxta variantlar (qarışdırılmış)."""
    opts = {correct}
    while len(opts) < count:
        opts.add(random_code(len(correct)))
    opts = list(opts)
    random.shuffle(opts)
    return opts
