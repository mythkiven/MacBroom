"""从一张方形源图生成 macOS 风格 .icns。

套用标准画布比例（1024 画布、824 内容、圆角 + 留白 + 轻阴影），再用 iconutil
压成多尺寸 .icns。源图非正方形时中心裁切。

用法：
    python make_icns.py <source.png> <MacBroom.icns>
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

CANVAS = 1024
CONTENT = 824
RADIUS = 185
OFFSET = (CANVAS - CONTENT) // 2

# (像素尺寸, iconset 文件后缀)
_SPECS = [
    (16, "16x16"), (32, "16x16@2x"),
    (32, "32x32"), (64, "32x32@2x"),
    (128, "128x128"), (256, "128x128@2x"),
    (256, "256x256"), (512, "256x256@2x"),
    (512, "512x512"), (1024, "512x512@2x"),
]


def _center_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    return img.crop((left, top, left + s, top + s))


def build(src: str, out: str) -> None:
    img = _center_square(Image.open(src).convert("RGBA")).resize(
        (CONTENT, CONTENT), Image.LANCZOS
    )

    mask = Image.new("L", (CONTENT, CONTENT), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, CONTENT - 1, CONTENT - 1], radius=RADIUS, fill=255
    )
    img.putalpha(mask)

    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [OFFSET, OFFSET + 10, OFFSET + CONTENT, OFFSET + CONTENT + 10],
        radius=RADIUS, fill=(0, 0, 0, 80),
    )
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.paste(img, (OFFSET, OFFSET), img)

    base = os.path.splitext(out)[0]
    canvas.save(base + "_1024.png")

    iconset = base + ".iconset"
    os.makedirs(iconset, exist_ok=True)
    for size, name in _SPECS:
        canvas.resize((size, size), Image.LANCZOS).save(
            os.path.join(iconset, f"icon_{name}.png")
        )
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    print("wrote", out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python make_icns.py <source.png> <MacBroom.icns>")
    build(sys.argv[1], sys.argv[2])
