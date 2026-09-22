# AI 交互式知识闯关学习平台（answer-agent）

> 把你想学的任何内容，变成一场可以互动、答题、纠错和复盘的 AI 学习闯关。
> 学习材料 → AI 出题 → 闯关答题 → 即时反馈 → 学习报告。

## ✨ 功能特性

- **核心学习闭环**：主题 / 文本 / 文本型 PDF 输入 → AI 两段式出题（知识点提取 + 题目生成）→ 逐题作答即时判分 → AI 学习报告
- **Grounded Quiz 有据出题**：每道题必须附带材料原文摘录（`source_excerpt`），服务端逐字校验，不匹配即触发降级重生成，抑制 AI 幻觉
- **三级降级可用性**：链级重试 → 减量重生成（5 题 → 3 题）→ 跨模型回退（DeepSeek 故障自动切备用模型）；报告失败退化纯规则模板，报告永不 500
- **答案不出后端**：题目下发不含答案，判分全部在服务端完成（幂等，重复提交返回首次结果）
- **学习游戏化**：经验值、连击 Combo、成就徽章、每自然月出题额度
- **SSE 流式进度**：出题全程推送 `extracting / generating / validating` 阶段事件，小程序端以 `enableChunked` 分块解析

## 🧰 技术栈

| 端 | 技术 |
|---|---|
| 前端 | Taro 4.2.1 · React 18.3.1 · TypeScript ~5.9 · Zustand 5 · 自定义轻量组件（一套代码编微信小程序 / H5） |
| 后端 | Python 3.12+ · FastAPI · Uvicorn · Pydantic v2 · SSE |
| AI 编排 | LangChain LCEL（`prompt \| llm.with_structured_output` + `with_retry` + `with_fallbacks`） |
| 主模型 | DeepSeek `deepseek-v4-flash`（langchain-deepseek 官方集成，function calling 结构化输出） |
| 备用模型 | 通义 Qwen（OpenAI 兼容端点，自动回退） |
| 存储 | 内存 TTL 结构（MVP 无数据库），材料 / 闯关 / 报告 2 小时过期 |

## 📁 项目结构

```
answer-agent/
├── client/                 # Taro 前端（小程序 + H5）
│   ├── src/pages/          # 15 个页面（上传/知识点/生成中/闯关/报告/个人中心…）
│   ├── src/services/       # 请求层 + SSE 分块解析
│   └── config/             # Taro 构建配置（designWidth 375）
└── server/                 # FastAPI 后端（TDD，pytest 覆盖）
    └── app/
        ├── chains/         # 三条 LCEL 链：提取 / 出题 / 报告
        ├── llm/            # 模型工厂（ChatDeepSeek + 回退）与用量统计
        ├── validators/     # Grounded Quiz 业务校验
        ├── services/       # 校验-重试-降级流水线、报告、游戏化
        ├── stores/         # 内存 TTL 存储
        └── api/            # 路由与 SSE
```

## 🚀 快速开始

### 1. 后端（必须先启动）

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env        # 填入 DEEPSEEK_API_KEY
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证：`http://127.0.0.1:8000/health` 返回 `{"status":"ok","llm_mode":"real",...}`

### 2. 前端 H5

```powershell
cd client
npm install
npm run dev:h5                # http://localhost:10086，/api 自动代理到 8000
```

### 3. 微信小程序

```powershell
cd client
npm run dev:weapp             # 产物输出 client/dist/
```

用微信开发者工具导入 `client/` 目录（`miniprogramRoot` 指向 `dist/`），并在「详情 → 本地设置」勾选 **不校验合法域名**。

### 4. 无 API Key 体验

`server/.env` 设 `FAKE_LLM=1`，后端使用内置样例数据装配链，无需任何 Key 即可跑通完整闭环。

> ⚠️ 修改 `.env` 后必须重启后端（配置在启动期装配）。模型名注意：DeepSeek 旧名
> `deepseek-chat` / `deepseek-reasoner` 已于 2026-07-24 停用，请使用 `deepseek-v4-flash` / `deepseek-v4-pro`。

## 🧪 测试

```powershell
cd server
.\.venv\Scripts\python -m pytest -q                 # 离线全量（FakeChatModel，不联网）
.\.venv\Scripts\python scripts\check_deepseek.py    # 模型连通性自检（配置/模型列表/结构化输出）
.\.venv\Scripts\python -m pytest -m integration -q  # 真实 API 集成测试（需 DEEPSEEK_API_KEY 环境变量）
```

## 🔌 核心接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/materials` / `/api/v1/materials/upload` | 提交文本 / 上传 PDF |
| POST | `/api/v1/quizzes/extract` | 知识点提取（SSE） |
| POST | `/api/v1/quizzes/generate` | 生成闯关（SSE） |
| POST | `/api/v1/quizzes/{quiz_id}/answers` | 提交答案（幂等，服务端判分） |
| POST | `/api/v1/reports` | 生成学习报告 |
| GET | `/api/v1/gamification/state` | 经验 / 连击 / 徽章 / 额度 |

统一错误格式 `{"code","message","detail"}`，完整契约见 `/docs`（Swagger）。

## 📌 说明

- 本项目为 MVP 阶段：无登录、无数据库（内存 TTL），仅用于学习闭环验证
- 上线前需完成：域名 ICP 备案、小程序 request 合法域名配置、AI 生成内容标识、隐私协议声明
- 未设置开源许可证：未经授权请勿复制或分发本仓库内容
