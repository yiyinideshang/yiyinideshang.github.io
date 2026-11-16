# 四级词库

一个按**词族**和**易混组**组织的四级单词复习网页。一个词只存一条，关系写在数据里，视图和测验自动生成。

当前词库：**832 词**，25 个易混组，67 个词族，29 个近义组。

- 词库源文件：`words.md`（你只改这一个文件）
- 应用：`index.html` + `app.js` + `style.css`
- 进度：浏览器 `localStorage`，可导出/导入 JSON

部署后地址：

```
https://yiyinideshang.github.io/ct4/
```

手机用浏览器打开后，“添加到主屏幕”，和 App 一样。加个 service worker，地铁里没网也能背。

---

## 每天 25 分钟

- **通勤 10 分钟**：手机 → 复习 → 清到期词
- **晚上 10 分钟**：关系 → 易混擂台 → 练 2 组
- **睡前 5 分钟**：只看今天答错词的“辨析 / 记 / 错”

没有抄写环节。

---

## 词库格式（只有三条规则）

```md
career n. 职业；事业；生涯 /kəˈrɪr/ [族:care] [混:cancer,carrier]
- 辨析: career 长期职业道路｜job 具体一份工作｜profession 需专业训练
- 记: career 开头像 care（care + er），职业要用心经营。
- 错: 与 cancer 混；career 结尾 -reer，重音在后。

cancer n. 癌症 /ˈkænsər/ [混:career]
- 记: can + cer，中间是 n。
```

1. **一行一个词，词打头**。词性、中文、音标、标签都在这一行；空行分隔词条。
2. **关系用标签**：`[族:x]` 词根家族，`[混:a,b]` 易混组，`[近:a,b]` 近义组。**只写一边就行，程序自动双向补全。**
3. **`- ` 开头的行是补充**：`辨析` / `例` / `记` / `错` / `变形` / `近义` / `相似`，随便写，不影响解析。

以后加 `reserve`，只要写：

```md
reserve vt. 预订；保留 /rɪˈzɜːrv/ [混:preserve,observe]
```

它会自动出现在 `preserve` / `observe` 那一组里，不需要回头改旧笔记。

### 标签怎么写

| 标签 | 意思 | 例子 |
|---|---|---|
| `[族:spect]` | 同一词根/词缀家族 | `respect` `inspect` `prospect` |
| `[混:cancer,carrier]` | 长得像/读得像/容易混 | `career` `cancer` `carrier` |
| `[近:job,profession]` | 意思接近，需要辨析 | `career` `job` `profession` |

音标可以手写，也可以留空；留空时网页仍能用浏览器 TTS 朗读，只是不显示音标。

---

## 加词流程

1. 在 Typora 打开 `words.md`
2. 找空行，写一行词条
3. 想加关系就写 `[混:...]` / `[族:...]`，不确定就空着
4. 保存 → 双击 `上传.bat` → 等 30 秒，网页更新

网页里的 **数据 → 格式检查** 会告诉你：有多少行没解析、引用了哪些不存在的词、缺多少词性。写完扫一眼。

第 4 周做一次合并去重：

```bash
python3 tools/check.py
```

它会列出重复词头。确认后手工合并，或把重复的两行发给我。

---

## 首次部署（只做一次）

仓库已经建好：`https://github.com/yiyinideshang/ct4`

在本机执行：

```bash
cd "D:/Typora/英语/ct4"
git branch -M main
git add -A
git commit -m "init: 四级词库"
git push -u origin main
```

然后：

1. 打开 GitHub 仓库 → **Settings → Pages**
2. **Source** 选 `Deploy from a branch`
3. Branch 选 `main`，目录选 `/ (root)`
4. 保存，等 1–2 分钟
5. 打开 `https://yiyinideshang.github.io/ct4/`

> 你的 Windows `hosts` 里有 Steam++ 写的 `127.0.0.1 github.com`。推送前先打开 Steam++，或者用它自带的加速；否则 git 连不上。

---

## 更新网站

改完 `words.md` 后，双击 **`上传.bat`**。它会自动：

```
git add -A
git commit -m "update: 日期 时间"
git push origin main
```

推送成功后 30 秒左右，GitHub Pages 自动更新。手机刷新即可。

如果 `上传.bat` 报认证失败：

- 确认 Steam++ / 代理已开
- 或在 GitHub Desktop 里点一下 Push
- 或者用 `git push` 手动推

> 只改 `words.md` 不需要动版本号。改 `app.js` / `style.css` / `index.html` 时，把 `index.html` 里的 `?v=3` 和 `sw.js` 里的 `cet4-v3` 各加 1，否则手机可能继续用旧缓存。

---

## 进度备份与换设备

- **导出**：数据 → 导出 JSON，保存到网盘
- **导入**：数据 → 导入，选那个 JSON
- **换手机**：在新手机打开网页 → 导入 JSON

进度不会自动跨设备同步。推荐：**手机当主力复习设备，电脑只看词、加词**。电脑端的练习不写进度（除非你在电脑上也开始复习）。

---

## 本地预览

直接双击 `index.html`。浏览器不允许 `file://` 自动读 `words.md`，会弹一个选择框，选一次 `words.md` 就行（当前标签页会记住）。

如果要用完整功能（service worker、自动读取），在项目目录起一个本地服务器：

```bash
cd "D:/Typora/英语/ct4"
python -m http.server 8000
```

然后打开 `http://localhost:8000`。

---

## 目录

```
ct4/
├── index.html              应用入口
├── style.css               样式
├── app.js                  解析、索引、复习、测验
├── words.md                唯一词库（你编辑这个）
├── sw.js                   离线缓存
├── manifest.webmanifest    添加到主屏幕
├── icon.svg
├── 上传.bat                一键 commit + push
├── README.md
├── sources/                原始笔记备份（不进仓库）
├── 迁移报告.md              迁移时的检查报告（不进仓库）
└── tools/
    ├── migrate.py          原始 md → 词库
    ├── postprocess.py      清洗、修错、合并
    ├── enrich.py           补音标/词性（词典 API）
    └── check.py            推送前格式检查
```

`sources/`、`迁移报告.md`、`build/` 在 `.gitignore` 里，不会公开。`words.md` 会公开（GitHub Pages 要读它），别往里写私人内容。

---

## 出题逻辑

- **看中文选单词**：4 选 1，干扰项优先从同一易混组/词族/形近词里抽
- **看单词选中文**：4 个中文释义，干扰项同样来自相关词
- **听音选词**：浏览器 TTS 朗读，4 选 1
- **拼写**：中文 + 音标 + 首字母提示，键盘输入
- **语境填空**：你写了 `- 例:` 的词，才会出这类题

答对 → 盒子 +1（1/2/4/7/14 天）；答错 → 回盒子 1。每天新词上限在“复习 → 设置”里改。

---

## 4 周节奏

| 时间 | 做什么 |
|---|---|
| 第 1 天 | 迁移、去重、补音标、上线 |
| 第 2–3 天 | 分诊 300–500 词，标出认识/模糊/不认识 |
| 第 4 天起 | 每天清到期 + 易混擂台 2 组；不再加功能 |
| 每周末 | 一套真题，生词入库 |
| 第 4 周 | `tools/check.py` 合并去重一次 |

**第 3 天之后不要再改应用。** 工具只用来省时间，不要让它吃掉复习时间。
