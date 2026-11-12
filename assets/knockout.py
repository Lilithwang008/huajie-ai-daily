import numpy as np
from PIL import Image, ImageFilter
from collections import deque
import os, time

SRC = r"C:\Users\Administrator\.workbuddy\clipboard-images\clipboard-2026-11-12T14-43-08-889Z-ce3b609f.jpg"
OUT_DIR = r"C:\Users\Administrator\WorkBuddy\2026-11-12-22-26-11\assets"

im = Image.open(SRC).convert("RGB")
a = np.array(im).astype(np.int16)
h, w, _ = a.shape
print("源图: %dx%d" % (w, h))

# 1) 近白像素（宽松，含抗锯齿边缘）
white = (a[:, :, 0] > 212) & (a[:, :, 1] > 212) & (a[:, :, 2] > 212)

# 2) 连通块分析：与画布边缘连通 或 面积够大的封闭白块 都算背景
#    —— 大块 = 辫子之间的缝隙；小块 = 金属高光，必须保留
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
visited = np.zeros((h, w), bool)
bg = np.zeros((h, w), bool)
AREA_MIN = 300
t0 = time.time()

ys, xs = np.nonzero(white)
for sy, sx in zip(ys.tolist(), xs.tolist()):
    if visited[sy, sx]:
        continue
    stack = [(sy, sx)]
    visited[sy, sx] = True
    pix = []
    touch = False
    while stack:
        y, x = stack.pop()
        pix.append((y, x))
        if y == 0 or x == 0 or y == h - 1 or x == w - 1:
            touch = True
        for dy, dx in DIRS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                stack.append((ny, nx))
    if touch or len(pix) >= AREA_MIN:
        for y, x in pix:
            bg[y, x] = True

print("连通块分析 %.1fs | 背景占比 %.1f%%" % (time.time() - t0, bg.mean() * 100))

# 3) alpha：背景全透明
alpha = np.where(bg, 0, 255).astype(np.uint8)

# 4) 去白边：紧贴背景的一圈按白度渐变透明
bg_img = Image.fromarray((bg * 255).astype(np.uint8), "L")
dil = np.array(bg_img.filter(ImageFilter.MaxFilter(5))) > 127
edge = dil & (~bg)
whiteness = a.min(axis=2) / 255.0
soft = np.clip((0.97 - whiteness) / 0.22, 0, 1)
alpha[edge] = (soft[edge] * 255).astype(np.uint8)

# 5) 轻微羽化
alpha_img = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.55))
alpha_img = alpha_img.point(lambda v: 0 if v < 40 else v)

out = im.convert("RGBA")
out.putalpha(alpha_img)

# 6) 裁到主体外框、补正方形
l, t, r, b = out.getbbox()
print("主体框:", (l, t, r, b), "尺寸: %dx%d" % (r - l, b - t))
pad = int(max(r - l, b - t) * 0.04)
l, t, r, b = l - pad, t - pad, r + pad, b + pad
side = max(r - l, b - t)
cx, cy = (l + r) // 2, (t + b) // 2
l2, t2 = cx - side // 2, cy - side // 2

canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(out.crop((l2, t2, l2 + side, t2 + side)), (0, 0))

os.makedirs(OUT_DIR, exist_ok=True)
canvas.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT_DIR, "logo@512.png"))
small = canvas.resize((256, 256), Image.LANCZOS)
small.save(os.path.join(OUT_DIR, "logo.png"), optimize=True)
small.save(os.path.join(OUT_DIR, "logo.webp"), quality=90, method=6)

for f in ("logo.png", "logo.webp"):
    p = os.path.join(OUT_DIR, f)
    print(f, "%.1f KB" % (os.path.getsize(p) / 1024))
