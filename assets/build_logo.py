from PIL import Image
import io, base64, re

# 1) 图标专用：完整图缩到 90%，四周留呼吸空间
full = Image.open('assets/logo@512.png').convert('RGBA')
inner = int(512 * 0.90)
t = full.resize((inner, inner), Image.LANCZOS)
c = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
off = (512 - inner) // 2
c.paste(t, (off, off), t)
c.save('assets/logo-head@512.png')

# 2) 转 256 webp，压成 data URI
im = c.resize((256, 256), Image.LANCZOS)
buf = io.BytesIO()
im.save(buf, 'WEBP', quality=92, method=6)
data = buf.getvalue()
b64 = 'data:image/webp;base64,' + base64.b64encode(data).decode()
im.save('assets/logo-head.webp', quality=92, method=6)
print('图标 webp %.1f KB' % (len(data) / 1024))

# 3) 写回页面
HTML = 'index.html'
h = io.open(HTML, encoding='utf-8').read()
h2 = re.sub(r'src="data:image/webp;base64,[^"]*"', 'src="' + b64 + '"', h, count=1)
io.open(HTML, 'w', encoding='utf-8').write(h2)
print('页面 %.1f KB' % (len(h2.encode('utf-8')) / 1024))
