# 华姐的 AI 日报

每日 AI 前沿资讯的单页站点：模型发布、政策监管、行业动态三类内容，卡片流 + 右侧「内容速览」，点开看详情，阅读记录存在本机浏览器。

## 在线访问

https://lilithwang008.github.io/huajie-ai-daily/

## 特点

- **单文件**：`index.html` 零依赖、零外部请求，图标与素材全部内嵌 base64，双击即可打开
- **两套主题**：暖色手绘纸感（默认）/ 冷色科技风，右上角一键切换，选择存入 `localStorage`
- **内容速览**：右侧栏对每条资讯做 100 字以内提炼，页面会显示实测字数
- **阅读档案**：打开即记录，支持收藏、单条删除、一键清空，仅存本机 `localStorage`
- **自适配**：桌面双栏，1080px 以下速览栏下沉，手机端单列

## 更新内容

所有资讯数据在 `index.html` 里的 `FEED.days`。要发布新一天，在数组**首位**插入一个对象即可，页面自动按最新一期渲染：

```js
FEED.days.unshift({
  date: "2026-11-13",
  label: "2026年11月13日 · 周五",
  note: "今日主线……",          // 右上角便签
  items: [
    {
      id: "唯一-id",
      cat: "model",             // model | policy | industry
      title: "标题",
      src: "来源",
      time: "11-13",
      summary: "100 字以内速览",  // 会显示字数，超过 100 会标红
      body: ["正文段落 1", "正文段落 2"],
      points: ["要点 1", "要点 2"],
      url: "原文链接"
    }
  ]
});
```

## 本地资源脚本

`assets/` 下是可复用的图像处理脚本，换图时按需重跑（需要 Python + Pillow + numpy）：

| 脚本 | 作用 |
|---|---|
| `knockout.py` | 白底图抠透明，按连通块面积判断背景（能处理被主体围住的封闭白块） |
| `build_logo.py` | 头像留白缩放 + 压缩 + 内嵌回 `index.html` |
| `build_favicon.py` | 生成 32/64/180 三档 favicon 并写入 `<head>` |

## 发布

改完 `index.html` 后执行：

```bash
python publish.py "本次改动说明"
```

脚本会用 GitHub API 建 blob / tree / commit 并更新 `main`，约 10 秒后 Pages 自动重新构建。

**为什么不用 `git push`**：本机网络代理只放行 `api.github.com`，`github.com` 的 git 协议（`git-upload-pack`）会超时。`publish.py` 走 REST API，同一套凭据更稳。

本地 `git` 只用来记录「哪些文件要发布」（`git ls-files` 决定上传清单，`.gitignore` 里排除的东西不会上传），本地提交历史与远端不必同步。

## 说明

页面为静态站点，所有数据硬编码在文件内，不采集任何用户数据。
