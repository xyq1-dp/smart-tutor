# 赛题需求对照表 & 实现追踪

> 本文件是赛题功能的**唯一真相来源**。每项功能必须在此记录实现状态。
> 修改任何功能前，先更新此文件的状态。

---

## 一、基本功能需求

### F1. 对话式学习画像自主构建 ✅ 基础完成，待完善

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 自然语言对话构建画像（非表单） | ✅ 已实现 | `app.py` 聊天 Tab、`backend/api/chat.py` | Streamlit 聊天界面 + 后端流式对话 |
| 自动抽取特征（专业、学习目标、学习历史） | ✅ 已实现 | `backend/agents/profile_agent.py` | `extract_profile_from_chat()` 通过 LLM 自动抽取 |
| 不少于 6 个画像维度 | ✅ 已定义 | `backend/api/chat.py:16-23` | 知识基础、学习目标、认知风格、学习节奏、薄弱点、兴趣方向 |
| 画像随学随新（动态更新） | ✅ 已实现 | `backend/agents/profile_agent.py` | `update_profile_dimension()` 支持单维度增量更新 |
| 画像持久化存储 | ✅ 已实现 | `backend/db/models.py` | `user_profiles` 表，JSON 字段存储 |

| 前端画像面板加载真实数据 | ✅ 已实现 | `app.py` + `backend/api/chat.py` | `GET /api/profile/{user_id}/dimensions` |

---

### F2. 多智能体协同的资源生成 ✅ 已完成

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| "多智能体"架构设计 | ✅ 框架已搭 | `backend/agents/orchestrator.py` | LangGraph 编排，5 个智能体角色定义 |
| 不同角色智能体协作 | ✅ 框架已搭 | `backend/agents/` 目录 | ProfileAgent / ResourceAgent / PathAgent |
| 至少 5 种资源类型 | ✅ 已定义 | `backend/agents/resource_agent.py` | doc / mindmap / exercise / reading / practice |
| ① 专业课程讲解文档 | ✅ prompt 已写 | `resource_agent.py:16-28` | 含代码示例、思考题 |
| ② 知识点思维导图 | ✅ prompt 已写 | `resource_agent.py:30-40` | Mermaid mindmap 格式 |
| ③ 不同类型练习题目 | ✅ prompt 已写 | `resource_agent.py:42-64` | 3 选择 + 2 代码题，三级难度 |
| ④ 拓展阅读材料 | ✅ prompt 已写 | `resource_agent.py:66-79` | 书籍/博客/视频/文档推荐 |
| ⑤ 代码实操案例 | ✅ prompt 已写 | `resource_agent.py:81-95` | 真实场景 + 注释代码 + 扩展挑战 |
| 多模态视频/动画 | ⏳ 待实现 | — | 第 5 周加分项，调用讯飞多模态 API |

---

### F3. 个性化学习路径规划和资源推送 ✅ 已完成

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 整合多智能体生成资源 | ⏳ 待实现 | `backend/agents/orchestrator.py` | 需完成 LangGraph 编排流 |
| 分析学生画像 → 路径规划 | ✅ 已实现 | `backend/agents/path_agent.py` | `plan_learning_path()` 依画像生成 JSON 路径 |
| 明确学习步骤和顺序 | ✅ 已实现 | `backend/api/path.py` | `GET /api/path/default` 返回 6 阶段路径 |
| 路径动态调整 | ✅ 已实现 | `backend/agents/path_agent.py` | `adjust_path_by_progress()` |
| 精准推送（文档/视频/题库/实操） | ✅ 已实现 | `backend/agents/orchestrator.py` | 根据画像+知识库检索精准推送 |
| 前端路径可视化 | ✅ 已实现 | `app.py` 学习路径 Tab | 时间线可视化，动态加载，重新规划 |

---

### F4. 智能辅导（可选加分项）✅ 已完成

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 即时答疑解惑 | ✅ 已实现 | `backend/agents/tutor_agent.py` | 自动检测知识提问，切换辅导模式 |
| 文字解答 | ✅ 已实现 | `backend/agents/tutor_agent.py` | 📖 概念讲解 — 通俗解释+类比 |
| 图解说明 | ✅ 已实现 | `backend/agents/tutor_agent.py` | 🧠 Mermaid 思维导图自动生成 |
| 代码示例 | ✅ 已实现 | `backend/agents/tutor_agent.py` | 💻 完整可运行代码+注释 |
| 练习题 | ✅ 已实现 | `backend/agents/tutor_agent.py` | ✏️ 针对性练习+答案解析 |
| 常见错误提醒 | ✅ 已实现 | `backend/agents/tutor_agent.py` | ⚠️ 初学者易错点+正确做法 |
| 前端 Mermaid 渲染 | ✅ 已实现 | `app.py` | Mermaid.js CDN 注入，自动图表渲染 |
| 自动触发检测 | ✅ 已实现 | `backend/api/chat.py` | 检测知识提问关键词 + 画像存在 → 自动切换 |

**实现机制**：
- 当学生有画像且提问包含知识关键词（什么/怎么/如何/为什么/解释/代码...）时，自动切换为辅导模式
- 辅导模式使用专用 system prompt，要求 LLM 按五段式结构输出
- 前端 `_render_markdown()` 自动检测 Mermaid 代码块并注入 mermaid.js 渲染

---

### F5. 学习效果评估（可选加分项）✅ 已完成

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 跟踪学习行为/练习/资源使用 | ✅ 已实现 | `backend/db/models.py` | `learning_behaviors` 表 + `record_behavior()` 记录聊天/资源生成/路径查看 |
| 行为埋点自动收集 | ✅ 已实现 | `backend/api/chat.py`, `resource.py`, `path.py` | 各 API 自动记录行为（chat/tutor_question/resource_generate/path_view/path_plan） |
| 大模型多维度评估 | ✅ 已实现 | `backend/agents/evaluation_agent.py` | 3 维度（知识掌握/学习投入/学习进度）+ 综合分 + 学习建议 |
| 评估持久化存储 | ✅ 已实现 | `backend/db/models.py` | `assessment_records` 表，支持历史查询 |
| 评估 API | ✅ 已实现 | `backend/api/assessment.py` | `POST /assessment/evaluate` 触发评估，`GET /assessment/{user_id}` 获取结果 |
| 根据评估动态调整推送和学习计划 | ✅ 已实现 | `backend/api/path.py` | 路径规划自动注入评估数据（薄弱点/专注主题/知识掌握分） |
| 前端评估面板 | ✅ 已实现 | `app.py` 侧边栏 + 路径 Tab | 综合分 + 三维度进度条 + 摘要 + 触发重新评估按钮 |

---

## 二、非功能性需求

### NF1. 界面与交互

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 界面美观大方、简洁明了 | ✅ 已完成 | `app.py` | CSS 注入，渐变标题，卡片化布局 |
| 流式输出 | ✅ 已实现 | `app.py` + `backend/api/chat.py` | SSE 流式，逐字显示 |
| Markdown 渲染 | ✅ 已实现 | `app.py` | `st.markdown()` 渲染 |
| 多模态内容卡片化展示 | ✅ 已完成 | `app.py` 资源 Tab | 5 种资源卡片 |
| 无明显功能与界面错误 | 🔄 需持续验证 | — | 每个功能开发后需回归测试 |

### NF2. 开源声明

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 标注开源项目名称、来源、协议 | ✅ 已完成 | `README.md` 底部 | FastAPI/MIT, Streamlit/Apache2.0, LangGraph/MIT, ChromaDB/Apache2.0 |
| 标注 AI 工具使用 | ✅ 已完成 | `README.md` 底部 | 注明使用 Claude Code 辅助开发 |

### NF3. 防幻觉与内容安全

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 生成内容无事实性错误 | ✅ 已实现 | `backend/utils/anti_hallucination.py` | LLM 自检 + 知识库比对 + Python AST 语法校验 |
| 无敏感违规信息 | ✅ 已实现 | `backend/utils/safety.py` | 敏感词过滤 + Prompt Injection 检测 |

### NF4. 响应性能

| 子要求 | 状态 | 实现位置 | 备注 |
|--------|------|----------|------|
| 响应时间合理 | ✅ 已实现 | `backend/api/chat.py` | 使用 SSE 流式，避免等待 |
| 生成进度追踪 | 🔄 部分实现 | `app.py` 聊天 Tab | 流式逐字显示（自然提供进度感） |
| 避免长时间白屏 | ✅ 已实现 | `app.py` | 流式 + 占位符动画 |

---

## 三、提交物要求

| 提交物 | 状态 | 负责 | 备注 |
|--------|------|------|------|
| 演示 PPT | ⏳ | 全员 | 第 6 周 |
| 可运行源码 | 🔄 | 全员 | 持续开发中 |
| 数据集/知识库 | 🔄 | 成员 C | 第 1-2 周 |
| 演示视频（7 分钟内） | ⏳ | B + C | 第 6 周 |
| 系统开发说明书 | ⏳ | 成员 C | 第 6 周 |
| 测试说明书 | ⏳ | 成员 C | 第 6 周 |
| AI Coding 工具说明 | ✅ | — | README 已注明 |

---

## 四、知识库进度

| 章节 | 内容文档 | 题库 |
|------|---------|------|
| 第 1 章 Python 基础语法 | ✅ 已完成 | ✅ 3 题 |
| 第 2 章 流程控制 | ✅ 已完成 | ✅ 3 题 |
| 第 3 章 函数与模块 | ✅ 已完成 | ✅ 3 题 |
| 第 4 章 数据结构 | ✅ 已完成 | ✅ 3 题 |
| 第 5 章 面向对象编程 | ✅ 已完成 | ✅ 3 题 |
| 第 6 章 综合项目实战 | ✅ 已完成 | ✅ 3 题 |

---

## 图例

| 符号 | 含义 |
|------|------|
| ✅ | 已完成 |
| 🚧 | 部分完成/框架已搭建 |
| ⏳ | 未开始 |
| 🔄 | 持续进行中 |
