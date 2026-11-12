#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把当前目录的改动发布到 GitHub（走 REST API，不用 git push）。

为什么不用 git push：本机代理只放行 api.github.com，github.com 的 git 协议
（git-upload-pack）会超时。API 通道更快也更稳。

用法：
    python publish.py                 # 提交信息自动带时间
    python publish.py "改成自己的说明"  # 自定义提交信息

依赖：gh 已登录（gh auth status 能看到账号即可）
"""
import base64
import json
import os
import subprocess
import sys
import time

REPO = 'Lilithwang008/huajie-ai-daily'
BRANCH = 'main'
ROOT = os.path.dirname(os.path.abspath(__file__))


def gh(args, data=None):
    cmd = ['gh', 'api'] + args
    kw = {'capture_output': True, 'text': True, 'encoding': 'utf-8'}
    if data is not None:
        cmd += ['--input', '-']
        kw['input'] = json.dumps(data)
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.strip() + '\n')
        sys.exit(1)
    return json.loads(r.stdout) if r.stdout.strip() else {}


def head_sha():
    r = subprocess.run(
        ['gh', 'api', '/repos/%s/git/ref/heads/%s' % (REPO, BRANCH)],
        capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        return None                      # 分支还不存在 = 首次发布
    return json.loads(r.stdout)['object']['sha']


def tracked_files():
    out = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True,
                         text=True, encoding='utf-8').stdout
    return [f for f in out.split('\n') if f.strip()]


def bootstrap(files):
    """空仓库不能直接建 blob（API 返回 409），先用 Contents API 造一个初始提交。"""
    seed = '.gitignore' if '.gitignore' in files else files[0]
    raw = open(os.path.join(ROOT, seed), 'rb').read()
    gh(['-X', 'PUT', '/repos/%s/contents/%s' % (REPO, seed.replace('\\', '/'))], {
        'message': '初始化仓库', 'branch': BRANCH,
        'content': base64.b64encode(raw).decode()})
    print('空仓库，已用 %s 建立初始提交' % seed)


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else '更新页面 %s' % time.strftime('%Y-%m-%d %H:%M')
    files = tracked_files()
    if not files:
        sys.exit('git 里没有跟踪任何文件')

    parent = head_sha()
    if not parent:
        bootstrap(files)
        parent = head_sha()

    print('上传 %d 个文件…' % len(files))
    tree = []
    for f in files:
        raw = open(os.path.join(ROOT, f), 'rb').read()
        blob = gh(['-X', 'POST', '/repos/%s/git/blobs' % REPO],
                  {'content': base64.b64encode(raw).decode(), 'encoding': 'base64'})
        tree.append({'path': f.replace('\\', '/'), 'mode': '100644',
                     'type': 'blob', 'sha': blob['sha']})
        print('  %-32s %6.1f KB  %s' % (f, len(raw) / 1024, blob['sha'][:7]))

    t = gh(['-X', 'POST', '/repos/%s/git/trees' % REPO], {'tree': tree})
    payload = {'message': msg, 'tree': t['sha'], 'parents': [parent] if parent else []}
    c = gh(['-X', 'POST', '/repos/%s/git/commits' % REPO], payload)

    if parent:
        gh(['-X', 'PATCH', '/repos/%s/git/refs/heads/%s' % (REPO, BRANCH)],
           {'sha': c['sha'], 'force': True})
    else:
        gh(['-X', 'POST', '/repos/%s/git/refs' % REPO],
           {'ref': 'refs/heads/%s' % BRANCH, 'sha': c['sha']})

    print('\n已发布 commit %s' % c['sha'][:7])
    print('提交信息：%s' % msg)
    print('页面地址：https://lilithwang008.github.io/huajie-ai-daily/')


if __name__ == '__main__':
    main()
