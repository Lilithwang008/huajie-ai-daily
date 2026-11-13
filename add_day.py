# -*- coding: utf-8 -*-
"""
把新一天的资讯插入 index.html 的 FEED.days（保留全部历史，不覆盖旧数据）。

用法：
    python add_day.py data/new-day.json

JSON 格式：
{
  "date": "2026-11-13",
  "label": "2026年11月13日 · 周五",
  "updated": "08:30",
  "note": "今日主线落在算力：大厂资本开支再上台阶。",
  "highlight": "算力",
  "items": [
    {
      "id": "unique-slug",
      "cat": "model",              // model | policy | industry
      "time": "11-13",
      "hot": false,                // 可选，最多一条 true
      "title": "标题，建议 ≤30 字",
      "summary": "100 字以内的核心摘要（去空白后计）",
      "body": ["正文段落 1", "正文段落 2"],
      "points": ["要点 1", "要点 2"],
      "source": "来源名",
      "url": "https://原文链接"
    }
  ]
}

校验不通过会直接退出并说明原因，不会写出半成品。
同一天重复运行 = 替换当天那一期，不会插入重复的一期。
"""
import io
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, 'index.html')
CATS = {'model', 'policy', 'industry'}
REQUIRED = ('id', 'cat', 'time', 'title', 'summary', 'body', 'points', 'source', 'url')


def cnlen(s):
    return len(re.sub(r'\s', '', s))


def norm(s):
    """标题去重用的归一化：去空白与常见标点。"""
    return re.sub(r'[\s，。、：；？！""''《》（）,.:;?!—|_-]', '', s).lower()


def validate(day):
    errs = []
    for k in ('date', 'label', 'updated', 'note', 'items'):
        if k not in day:
            errs.append('缺少顶层字段 %s' % k)
    if errs:
        return errs

    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day['date']):
        errs.append('date 必须是 YYYY-MM-DD')
    if not re.fullmatch(r'\d{2}:\d{2}', day['updated']):
        errs.append('updated 必须是 HH:MM')
    items = day['items']
    if not isinstance(items, list) or not (5 <= len(items) <= 15):
        errs.append('items 必须是 5-15 条，当前 %s' % (len(items) if isinstance(items, list) else '非数组'))

    cats, ids, titles = set(), set(), set()
    hot = 0
    for n, it in enumerate(items if isinstance(items, list) else [], 1):
        tag = '第 %d 条' % n
        for k in REQUIRED:
            if k not in it or it[k] in ('', [], None):
                errs.append('%s 缺字段 %s' % (tag, k))
        if not errs or all(not e.startswith(tag) for e in errs):
            if it.get('cat') not in CATS:
                errs.append('%s cat 非法：%s' % (tag, it.get('cat')))
            cats.add(it.get('cat'))
            if it.get('id') in ids:
                errs.append('%s id 重复：%s' % (tag, it.get('id')))
            ids.add(it.get('id'))
            t = norm(it.get('title', ''))
            if t in titles:
                errs.append('%s 标题与本期内重复' % tag)
            titles.add(t)
            u = it.get('url', '')
            if not re.match(r'^https?://', u):
                errs.append('%s url 不是 http(s) 链接' % tag)
            L = cnlen(it.get('summary', ''))
            if L > 100:
                errs.append('%s 摘要 %d 字，超过 100 字上限' % (tag, L))
            if len(it.get('title', '')) > 42:
                errs.append('%s 标题过长（%d 字）' % (tag, len(it['title'])))
            if not isinstance(it.get('body'), list) or len(it['body']) < 2:
                errs.append('%s body 至少 2 段' % tag)
            if not isinstance(it.get('points'), list) or len(it['points']) < 2:
                errs.append('%s points 至少 2 条' % tag)
        if it.get('hot'):
            hot += 1
    if hot > 1:
        errs.append('hot 头条最多 1 条，当前 %d 条' % hot)
    if len(cats) < 2:
        errs.append('三类资讯至少覆盖 2 类，当前只有 %s' % (','.join(sorted(cats)) or '无'))
    if 'highlight' in day and day['highlight'] and day['highlight'] not in day['note']:
        errs.append('highlight「%s」不在 note 里' % day['highlight'])
    return errs


def first_day_span(s, start):
    """定位 days 数组里第一个对象的 [起, 止)；跳过字符串与注释中的括号。"""
    i = s.find('{', start)
    if i < 0:
        raise ValueError('找不到 days 数组的第一个对象')
    depth, j = 0, i
    quote, esc = None, False
    while j < len(s):
        ch = s[j]
        if quote:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == quote:
                quote = None
            j += 1
            continue
        if ch in '"\'`':
            quote = ch
        elif ch == '/' and s[j:j + 2] == '//':
            k = s.find('\n', j)
            j = (k + 1) if k >= 0 else len(s)
            continue
        elif ch == '/' and s[j:j + 2] == '/*':
            k = s.find('*/', j)
            j = (k + 2) if k >= 0 else len(s)
            continue
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1
    raise ValueError('days 第一个对象的花括号不配对')


def to_js(v, level, nl):
    """输出与页面现有风格一致的对象字面量：key 不加引号。"""
    pad = '  ' * level
    if isinstance(v, dict):
        if not v:
            return '{}'
        parts = []
        for k, x in v.items():
            key = k if re.fullmatch(r'[A-Za-z_$][\w$]*', k) else json.dumps(k, ensure_ascii=False)
            parts.append(pad + '  ' + key + ': ' + to_js(x, level + 1, nl))
        return '{' + nl + (',' + nl).join(parts) + nl + pad + '}'
    if isinstance(v, list):
        if not v:
            return '[]'
        parts = [pad + '  ' + to_js(x, level + 1, nl) for x in v]
        return '[' + nl + (',' + nl).join(parts) + nl + pad + ']'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if v is None:
        return 'null'
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False).replace('</', '<\\/')


def js_object(day, nl):
    lines = to_js(day, 1, nl).splitlines()
    # 首行 4 空格（对齐 days 里的对象），其余行补 2 空格
    return nl.join(['    ' + lines[0]] + ['  ' + ln for ln in lines[1:]])


def escape_note(day):
    note = day['note']
    hi = day.get('highlight') or ''
    if hi and hi in note:
        a, b = note.split(hi, 1)
        esc = lambda x: x.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return '%s<b>%s</b>%s' % (esc(a), esc(hi), esc(b))
    return note.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def main():
    if len(sys.argv) < 2:
        sys.exit('用法：python add_day.py data/new-day.json')
    src = sys.argv[1]
    if not os.path.isabs(src):
        src = os.path.join(ROOT, src)
    day = json.load(io.open(src, encoding='utf-8'))

    errs = validate(day)
    if errs:
        print('校验未通过，未改动任何文件：')
        for e in errs:
            print('  - ' + e)
        sys.exit(1)

    html = io.open(HTML, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in html else '\n'   # 保持文件原本的换行风格
    # 锚到 days: [ 所在行的行尾，让 arr_start 落在下一行行首
    m = re.search(r'(const FEED\s*=\s*\{\s*updated:\s*"[^"]*",\s*days:\s*\[[ \t]*\r?\n)', html)
    if not m:
        raise ValueError('找不到 FEED.days 起始位置')
    arr_start = m.end()

    # 历史去重：标题 / url / id
    old_titles = {norm(x) for x in re.findall(r'\btitle:\s*"([^"]*)"', html)}
    old_urls = set(re.findall(r'\burl:\s*"([^"]*)"', html))
    old_ids = set(re.findall(r'^\s*id:\s*"([^"]+)"', html, re.M))
    # 同一天重跑时，排除当前 days[0] 自己，否则会被判成「与历史重复」
    same_day = re.search(r'\bdate:\s*"([^"]+)"', html[arr_start:arr_start + 400])
    own_titles, own_urls, own_ids = set(), set(), set()
    a = b = None
    if same_day and same_day.group(1) == day['date']:
        a, b = first_day_span(html, arr_start)
        own_titles = {norm(x) for x in re.findall(r'\btitle:\s*"([^"]*)"', html[a:b])}
        own_urls = set(re.findall(r'\burl:\s*"([^"]*)"', html[a:b]))
        own_ids = set(re.findall(r'^\s*id:\s*"([^"]+)"', html[a:b], re.M))
    dup_t = [it['title'] for it in day['items']
             if norm(it['title']) in old_titles - own_titles]
    dup_u = [it['id'] for it in day['items'] if it['url'] in old_urls - own_urls]
    dup_i = [it['id'] for it in day['items'] if it['id'] in old_ids - own_ids]
    if dup_t or dup_u or dup_i:
        print('与历史内容重复，未改动任何文件：')
        for t in dup_t:
            print('  - 标题重复：' + t)
        for i in sorted(set(dup_u + dup_i)):
            print('  - id/链接重复：' + i)
        sys.exit(1)

    obj = js_object(day, nl)
    mode = ''
    if a is not None:
        # 把原对象前的缩进规范成 4 空格，再接上不带首行缩进的新对象
        head = re.sub(r'[ \t]+$', '    ', html[:a])
        html = head + obj.lstrip() + html[b:]
        mode = '替换当天'
    else:
        html = html[:arr_start] + obj + ',' + nl + html[arr_start:]
        mode = '新增一期'

    html = re.sub(r'(const FEED\s*=\s*\{\s*updated:\s*")[^"]*(")',
                  lambda x: x.group(1) + day['updated'] + x.group(2), html, count=1)
    html = re.sub(r'(<div class="mast-note">).*?(</div>)',
                  lambda x: x.group(1) + escape_note(day) + x.group(2),
                  html, count=1, flags=re.S)

    io.open(HTML, 'w', encoding='utf-8', newline='').write(html)
    c = {k: sum(1 for i in day['items'] if i['cat'] == k) for k in ('model', 'policy', 'industry')}
    print('%s：%s（%s）' % (mode, day['date'], day['label']))
    print('本期 %d 条 · 模型 %d / 政策 %d / 行业 %d' % (len(day['items']), c['model'], c['policy'], c['industry']))
    print('摘要最长 %d 字' % max(cnlen(i['summary']) for i in day['items']))
    print('FEED.updated = %s' % day['updated'])
    print('历史共 %d 期' % len(re.findall(r'^[ \t]+date:\s*"\d{4}-\d{2}-\d{2}"', html, re.M)))
    print('文件 %.1f KB' % (len(html.encode('utf-8')) / 1024))


if __name__ == '__main__':
    main()
