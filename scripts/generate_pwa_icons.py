"""FAS ikonunu Pillow ile cizip PNG (192, 512, 180) olarak kaydeder.

fas-icon.svg'nin tasarimini Pillow primitifleriyle yeniden uretir
(mercek + dokunmus kumas pattern + kahverengi gradient bg). cairosvg
Windows'ta libcairo gerektirdigi icin bu fallback secildi.

Calistirma: .venv\\Scripts\\python.exe scripts\\generate_pwa_icons.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "web" / "static" / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUPER = 2048  # 4x supersample, sonra LANCZOS downscale -> keskin AA
SCALE = SUPER / 512.0


def s(v: float) -> int:
    return int(round(v * SCALE))


def make_icon() -> Image.Image:
    # 1) Arka plan gradient (linear from #2A2110 to #1A1408)
    arr = np.zeros((SUPER, SUPER, 4), dtype=np.uint8)
    # t parameter: top-left = 0, bottom-right = 1
    xs = np.arange(SUPER, dtype=np.float32) / (SUPER - 1)
    ys = np.arange(SUPER, dtype=np.float32) / (SUPER - 1)
    X, Y = np.meshgrid(xs, ys)
    T = (X + Y) / 2.0  # diagonal gradient parameter
    arr[..., 0] = (0x2A * (1 - T) + 0x1A * T).astype(np.uint8)
    arr[..., 1] = (0x21 * (1 - T) + 0x14 * T).astype(np.uint8)
    arr[..., 2] = (0x10 * (1 - T) + 0x08 * T).astype(np.uint8)
    arr[..., 3] = 255
    img = Image.fromarray(arr, "RGBA")

    # Rounded rect mask (corner radius 112 in 512-space)
    mask = Image.new("L", (SUPER, SUPER), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SUPER, SUPER], radius=s(112), fill=255)
    img.putalpha(mask)

    # 2) Diagonal highlight stripe (gold 7%)
    stripe = Image.new("RGBA", (SUPER, SUPER), (0, 0, 0, 0))
    ImageDraw.Draw(stripe).polygon(
        [(s(-40), s(300)), (s(160), s(-40)), (s(320), s(-40)), (s(120), s(300))],
        fill=(0xF5, 0xB5, 0x3D, int(255 * 0.07)),
    )
    # Sripe disinda rounded mask uygula
    stripe.putalpha(Image.eval(mask, lambda v: min(v, int(255 * 0.5))))
    img.alpha_composite(stripe)

    # 3) Outer soft ring (gold 16%, width 44 stroke @235,225 r=120)
    cx, cy, r = s(235), s(225), s(120)
    ring = Image.new("RGBA", (SUPER, SUPER), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(0xF5, 0xB5, 0x3D, int(255 * 0.16)),
        width=s(44),
    )
    img.alpha_composite(ring)

    # 4) Lens icindeki dokuma pattern (clip: circle r=106 @cx,cy)
    lens_layer = Image.new("RGBA", (SUPER, SUPER), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lens_layer)
    # Background of weaving area (dark)
    ld.rectangle([s(120), s(115), s(350), s(335)], fill=(0x12, 0x0D, 0x06, 255))
    # Warp (dikey) bars — main gold
    for x in (140, 180, 220, 260, 300):
        ld.rectangle([s(x), s(115), s(x + 30), s(335)], fill=(0xF5, 0xB5, 0x3D, 255))
    # Weft (yatay) bars — darker gold
    for y in (130, 170, 210, 250, 290):
        ld.rectangle([s(115), s(y), s(335), s(y + 30)], fill=(0xB7, 0x79, 0x1F, 255))
    # Crossings — main gold over weft (SVG'deki spesifik desen)
    crossings = [
        (140, 130), (140, 210), (140, 290),
        (180, 170), (180, 250),
        (220, 130), (220, 210), (220, 290),
        (260, 170), (260, 250),
        (300, 130), (300, 210), (300, 290),
    ]
    for x, y in crossings:
        ld.rectangle(
            [s(x), s(y), s(x + 30), s(y + 30)],
            fill=(0xF5, 0xB5, 0x3D, 255),
        )

    # Lens clip mask (only inside circle r=106)
    lens_mask = Image.new("L", (SUPER, SUPER), 0)
    ImageDraw.Draw(lens_mask).ellipse(
        [cx - s(106), cy - s(106), cx + s(106), cy + s(106)], fill=255
    )
    lens_layer.putalpha(lens_mask)
    img.alpha_composite(lens_layer)

    # 5) Outer lens border (solid gold, width 26)
    border = Image.new("RGBA", (SUPER, SUPER), (0, 0, 0, 0))
    ImageDraw.Draw(border).ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(0xF5, 0xB5, 0x3D, 255),
        width=s(26),
    )
    img.alpha_composite(border)

    # 6) Handle (diagonal line, gold, width 40, round caps)
    # Pillow line caps: round caps via ImageDraw.line + joint
    # Cap'leri manuel ellipse ile yapalim (Pillow line round-cap yok native)
    handle = Image.new("RGBA", (SUPER, SUPER), (0, 0, 0, 0))
    hd = ImageDraw.Draw(handle)
    hd.line(
        [(s(320), s(310)), (s(400), s(390))],
        fill=(0xF5, 0xB5, 0x3D, 255),
        width=s(40),
    )
    # round caps
    half_w = s(40) // 2
    hd.ellipse([s(320) - half_w, s(310) - half_w, s(320) + half_w, s(310) + half_w], fill=(0xF5, 0xB5, 0x3D, 255))
    hd.ellipse([s(400) - half_w, s(390) - half_w, s(400) + half_w, s(390) + half_w], fill=(0xF5, 0xB5, 0x3D, 255))
    img.alpha_composite(handle)

    return img


def main() -> int:
    print("Generating PWA icons from FAS design...")
    super_img = make_icon()
    sizes = [
        (512, "icon-512.png"),
        (192, "icon-192.png"),
        (180, "apple-touch-icon.png"),
    ]
    for size, name in sizes:
        out = super_img.resize((size, size), Image.LANCZOS)
        # PNG icon needs RGB (no alpha for some PWA contexts) but RGBA is fine
        out.save(OUT_DIR / name, "PNG", optimize=True)
        print(f"  OK {name} ({size}x{size})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
