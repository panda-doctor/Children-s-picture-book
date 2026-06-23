# 儿童故事绘本生成器 📚

面向 3–8 岁儿童的故事绘本生成应用。输入或上传故事文本，自动分章节、调用 AI 生成插画、排版成可在线翻页阅读并导出 PDF 的电子绘本。

## ✨ 功能特性

- **故事录入**：手动输入或上传 TXT / JSON 文件，自动按章节/段落分页
- **内容安全审核**：中英文敏感词过滤与风险分级，拦截不适合儿童的内容
- **AI 插画生成**：基于章节内容生成插画（Agnes Image 2.1 Flash），支持卡通/水彩/蜡笔/扁平四种风格；**无 API 密钥时自动降级为本地占位插画**，全流程可离线跑通
- **绘本排版**：Pillow 图文混排，生成封面/正文/封底，导出 PDF
- **在线阅读**：翻页动画、键盘/触屏滑动翻页
- **语音朗读** 🔊：浏览器原生语音合成朗读当前页（适合识字少的儿童）
- **真实生成进度**：SSE 流式逐页推送插画生成进度
- **家长模式** 🔒：上传自定义文件需家长密码验证，防止儿童绕过内容审核

## 🛠 技术栈

- 后端：Python + Flask
- 图像处理：Pillow
- 图片生成：Agnes Image 2.1 Flash API
- 前端：原生 HTML/CSS/JavaScript（无框架）
- 存储：本地文件系统

## 🚀 快速开始

```bash
cd children_storybook_app

# 安装依赖
pip install -r requirements.txt

# 启动（默认 http://localhost:5000）
python app.py
```

### 环境变量（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGNES_API_KEY` | 空 | Agnes 图片生成 API 密钥；未设置时使用本地占位插画 |
| `LOCAL_IMAGE_FALLBACK` | `true` | API 失败时是否降级为本地插画 |
| `PARENT_PASSWORD` | `1234` | 家长模式密码，**生产环境请务必修改** |
| `SECRET_KEY` | 内置默认值 | Flask 会话密钥，**生产环境请务必修改** |
| `IMAGE_SIZE` | `1024x768` | 插画尺寸 |

## 🧪 测试

```bash
cd children_storybook_app
python -m unittest test_offline_flow
```

## 📁 项目结构

```
children_storybook_app/
├── app.py                  # Flask 主应用与 API 路由
├── config.py               # 配置（API、路径、家长密码等）
├── utils/
│   ├── content_filter.py   # 内容安全过滤
│   ├── story_parser.py     # 故事解析与分章节
│   ├── image_generator.py  # 插画生成（API + 本地降级）
│   └── layout_engine.py    # 绘本排版与 PDF 导出
├── templates/              # 创作 / 编辑器 / 阅读器页面
├── static/                 # CSS 与 JavaScript
└── data/                   # 运行时生成的故事、插画、绘本（不纳入版本库）
```

## ⚠️ 说明

应用核心生成流程为线性管道：内容安全 → 故事解析 → 插画生成 → 排版导出。`data/` 下的故事、插画、绘本均为运行时生成，已通过 `.gitignore` 排除。
