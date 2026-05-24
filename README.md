# 智能学习助手 — Smart Tutor

高等教育个性化学习智能体系统

## 项目简介

本项目是**软件杯**参赛作品，基于大模型技术构建多智能体系统，
为学生打造专属的 Python 程序设计个性化学习助手。

系统通过多智能体协作，实现：
- 对话式学习画像自主构建（6 维度）
- 5 种多模态学习资源自动生成
- 个性化学习路径规划与资源推送
- 智能辅导答疑（加分项）
- 学习效果评估（加分项）

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit | Python Web UI 框架 |
| 后端 | FastAPI | 异步 REST API |
| 多智能体 | LangGraph | 智能体编排框架 |
| 数据库 | SQLite + ChromaDB | 关系 + 向量检索 |
| 大模型 | 科大讯飞星火 v3.5 | 内容生成与对话 |
| AI 辅助 | Claude Code | 代码辅助开发 |

> **注意**：开发过程使用了 Anthropic Claude Code 作为 AI 辅助编程工具，
> 负责代码生成、架构设计、调试辅助。核心业务逻辑由团队成员主导设计。

## 快速开始

### 环境要求
- Python 3.10+
- Windows / macOS / Linux

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置讯飞星火 API
1. 前往 [讯飞开放平台](https://console.xfyun.cn/) 注册并创建应用
2. 获取 APP_ID, API_KEY, API_SECRET
3. 设置环境变量：

```bash
# Windows CMD
set SPARK_APP_ID=你的APP_ID
set SPARK_API_KEY=你的API_KEY
set SPARK_API_SECRET=你的API_SECRET

# Windows PowerShell
$env:SPARK_APP_ID="你的APP_ID"
$env:SPARK_API_KEY="你的API_KEY"
$env:SPARK_API_SECRET="你的API_SECRET"
```

### 启动后端
```bash
uvicorn backend.main:app --reload --port 8000
```

### 启动前端（新终端）
```bash
streamlit run app.py
```

### 访问
- 前端：http://localhost:8501
- 后端 API 文档：http://localhost:8000/docs

## 项目结构

```
smart-tutor/
├── app.py                    # Streamlit 前端入口
├── backend/
│   ├── main.py               # FastAPI 应用入口
│   ├── agents/               # LangGraph 智能体
│   ├── api/                  # REST API 路由
│   ├── db/                   # 数据库模型
│   ├── llm/                  # 大模型封装
│   └── utils/                # 工具函数
├── knowledge_base/           # Python 课程知识库
├── requirements.txt
└── README.md
```

## 团队分工

- 成员 A：后端 + AI 核心（FastAPI、多智能体、讯飞 API）
- 成员 B：前端 + 交互体验（Streamlit、UI 美化）
- 成员 C：知识库 + 学习路径 + 测试

## 开发进度

- [x] 第 1 周：项目初始化 + 最小原型
- [ ] 第 2 周：画像系统 + 基础对话
- [ ] 第 3 周：多智能体资源生成
- [ ] 第 4 周：学习路径 + 推送
- [ ] 第 5 周：加分项 + 打磨
- [ ] 第 6 周：文档 + 视频 + 提交

## 开源声明

本项目使用了以下开源工具和框架：
- [FastAPI](https://github.com/tiangolo/fastapi) — MIT License
- [Streamlit](https://github.com/streamlit/streamlit) — Apache 2.0 License
- [LangGraph](https://github.com/langchain-ai/langgraph) — MIT License
- [ChromaDB](https://github.com/chroma-core/chroma) — Apache 2.0 License
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) — MIT License

AI 辅助开发工具：
- [Anthropic Claude Code](https://www.anthropic.com/claude) — AI 编程助手

本项目严格遵循上述所有开源协议的条款。
