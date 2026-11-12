# -*- coding: utf-8 -*-
"""
由 assets/logo@512.png（已抠好的透明图）生成 favicon，并写回 index.html。

设计：米色纸底圆角方块 + 机甲头像特写
  - 裁掉四周 10%：只留头肩，16/32px 下帽子与蓝眼睛才看得清
  - 圆角半径 22%，内边距 4.5%，8 倍超采样后缩放，边缘干净不带锯齿
  - 调色板量化（32px=96色 / 64px=128色）把体积从 10KB 压到 2.5KB

用法：改 NEED 里的尺寸或 CUT/PAD/RADIUS 后直接 python assets/build_favicon.py
"""
import io
import os
import re
import base64
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets', 'logo@512.png')
HTML = os.path.join(ROOT, 'index.html')

PAPER = (246, 241, 227, 255)   # 同 --paper
CUT = 0.10                     # 四周各裁掉的比例
PAD = 0.045                    # 图标内容与圆角方块边缘的间距
RADIUS = 0.22                  # 圆角半径占边长比例
SS = 8                         # 超采样倍数

# 尺寸 -> 量化色数（None = 不量化）
NEED = [(32, 96), (64, 128), (180, 192)]


def make(src, size):
    s = size * SS
    canvas = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=int(s * RADIUS), fill=PAPER)
    box = (int(512 * CUT), int(512 * CUT), int(512 * (1 - CUT)), int(512 * (1 - CUT)))
    head = src.crop(box)
    inner = int(s * (1 - PAD * 2))
    t = head.resize((inner, inner), Image.LANCZOS)
    off = (s - inner) // 2
    canvas.paste(t, (off, off), t)
    return canvas.resize((size, size), Image.LANCZOS)


def main():
    src = Image.open(SRC).convert('RGBA')
    blobs = {}
    for size, ncol in NEED:
        im = make(src, size)
        q = im.quantize(colors=ncol, method=Image.FASTOCTREE) if ncol else im
        buf = io.BytesIO()
        q.save(buf, 'PNG', optimize=True)
        blobs[size] = buf.getvalue()
        # 直接存量化后的 P 模式，转 RGBA 会把体积放大好几倍
        q.save(os.path.join(ROOT, 'assets', 'favicon-%d.png' % size), optimize=True)
        print('%dpx PNG: %.2f KB' % (size, len(blobs[size]) / 1024))

    # 内联 32 / 64，180 留给 apple-touch-icon 走外链
    tags = ''.join(
        '<link rel="icon" type="image/png" sizes="%dx%d" href="data:image/png;base64,%s">\n'
        % (s, s, base64.b64encode(blobs[s]).decode())
        for s in (32, 64)
    )
    tags += '<link rel="apple-touch-icon" href="assets/favicon-180.png">\n'

    html = io.open(HTML, encoding='utf-8').read()
    html = re.sub(r'<link rel="icon"[^>]*>\n', '', html)
    html = re.sub(r'<link rel="apple-touch-icon"[^>]*>\n', '', html)
    # 锚在 </head> 上，改站名也不影响
    anchor = '</head>'
    assert anchor in html, '未找到 </head>'
    html = html.replace(anchor, tags + anchor, 1)
    io.open(HTML, 'w', encoding='utf-8').write(html)
    print('已写回 index.html，总 %.1f KB' % (len(html.encode('utf-8')) / 1024))


if __name__ == '__main__':
    main()
