# Smart Tutor 系统全貌分析

> 写于 F1-F5 全部完成后。本文档面向团队成员，事无巨细地拆解每个模块的真实运作方式、模块间的协同关系、以及当前的实际优劣势。

---

## 一、技术底座

### 1. 大模型层 — `backend/llm/spark.py`

整个系统的"大脑"。封装了科大讯飞星火 Ultra 32K 的 WebSocket 调用。

- `spark_chat_stream()` — 流式输出，每收到一个 token 就 yield，支撑前端的逐字打字效果
- `spark_chat()` — 非流式聚合版，给画像提取/评估等后台非流式任务用
- 鉴权用 HMAC-SHA256 签名，每次连接动态生成

**实际地位**：系统中所有"智能"行为的唯一来源。画像提取、资源生成、路径规划、辅导答疑、学习评估——全部是同一套 API 配不同的 prompt 模板。所谓"多智能体"，本质是 prompt engineering 的分层封装，而非独立的 AI 模型。

### 2. 数据层 — `backend/db/models.py` + `backend/db/vector_store.py`

#### SQLite（5 张表）

| 表 | 用途 | 关键字段 |
|---|---|---|
| `users` | 用户身份 | id, name, major, created_at |
| `user_profiles` | 6 维度画像 | knowledge_level, learning_goal, cognitive_style, pace, weak_points(JSON), interest_areas(JSON) |
| `chat_history` | 对话全记录 | user_id, role, content, created_at |
| `learning_behaviors` | 行为埋点 | user_id, behavior_type, detail(JSON), created_at |
| `assessment_records` | 评估快照 | user_id, dimensions(JSON), overall_score, summary, suggestions, weak_points_change(JSON), created_at |

行为类型枚举：`chat`、`tutor_question`、`resource_generate`、`resource_view`、`path_view`、`path_plan`。

#### ChromaDB 向量库

- Embedding 模型：`paraphrase-multilingual-MiniLM-L12-v2`（SentenceTransformer）
- 用途：把知识库文档按段落切片存入，资源生成时做 RAG 检索增强
- 隐患：如果 sentence-transformers 未正确安装，embedding 静默失败，检索返回空列表，系统不会报错提示

---

## 二、智能体层 — 5 个 Agent 逐个解剖

### Agent 1：ProfileAgent — `backend/agents/profile_agent.py`

**职责**：从对话历史中自动提取 6 个维度的学生画像。

**工作方式**：
- 每次对话结束后，把最近 20 轮对话喂给 LLM，要求输出 JSON
- 6 个维度：知识基础（beginner/medium/advanced）、学习目标（文本描述）、认知风格（visual/textual/hands-on）、学习节奏（fast/normal/slow）、薄弱点（列表）、兴趣方向（列表）
- 附带置信度分数（0~1），低于 0.5 的结果不写入数据库
- 支持单维度增量更新（`update_profile_dimension()`），但当前主流程未调用

**协同位置**：所有其他 Agent 都依赖画像。路径规划用它调整阶段顺序和优先级，资源生成用它控制内容难度，辅导用它定制回复话术，评估用它做前后对比基线。

**当前局限**：
- 每次只取最近 20 轮对话，没有长期记忆——学生一个月前说的"我想做游戏开发"会被遗忘
- 画像提取在对话结束后异步进行，用户看不到提取过程
- 旧值直接覆盖，没有画像变更历史

---

### Agent 2：ResourceAgent — `backend/agents/resource_agent.py`

**职责**：按 5 种专用 prompt 模板生成个性化学习材料。

**5 种资源及其策略**：

| 类型 | 标识 | Prompt 策略 | 输出格式 |
|---|---|---|---|
| 课程讲解文档 | `doc` | 按学生水平调整难度，末尾给 3 个思考题 | Markdown |
| 知识点思维导图 | `mindmap` | 固定 Mermaid mindmap 语法模板 | Mermaid |
| 自适应练习题 | `exercise` | 3 道选择 + 2 道代码，三级难度递进，针对薄弱点出题 | JSON |
| 拓展阅读材料 | `reading` | 3-5 个资源推荐（书籍/博客/视频），按难度排序，附链接 | Markdown |
| 代码实操案例 | `practice` | 真实编程场景 + 注释完整代码 + 扩展挑战 | Markdown（含 Python 代码块） |

**防幻觉**：`doc` 类型生成后额外调一次 LLM 做事实核查（`verify_against_knowledge_base()`），有问题自动替换修正版。其他类型不做此检查以节省 API 调用成本。

---

### Agent 3：PathAgent — `backend/agents/path_agent.py`

**职责**：根据画像生成 6 阶段个性化学习路径（对应知识库 6 章）。

**工作方式**：
- 把画像 5 个维度填入 prompt → LLM 输出 JSON
- JSON 包含：起始点、每阶段标题/知识点列表/建议学时/优先级(high/medium/low)/学习建议、总学时、周计划
- `adjust_path_by_progress()` 接受已完成知识点 + 评估结果，重新规划路径

**协同位置**：路径 API 调用时会先查评估表，把评估中的薄弱点和专注主题注入画像，让路径规划感知学生当前实际状态而非仅依赖初始画像。

---

### Agent 4：TutorAgent — `backend/agents/tutor_agent.py`

**职责**：五段式结构化辅导答疑。

**触发条件（两个同时满足）**：
1. 学生画像已建立（`learning_goal` 不为空）
2. 消息含知识提问关键词（什么/怎么/如何/为什么/解释/讲解/区别/代码/原理/报错/不会/帮我/教我... 共 22 个关键词，或以 `?`/`？` 结尾）

**五段式输出结构**：
1. 📖 **概念讲解** — 通俗解释 + 生活类比，难度根据画像中的知识基础动态调整
2. 🧠 **图解** — Mermaid 语法（优先 mindmap 其次 flowchart），前端自动渲染为可视化图表
3. 💻 **代码示例** — 至少 1 个完整可运行的 Python 代码 + 注释
4. ✏️ **练习题** — 1 道选择或填空题 + 答案 + 解析，针对薄弱点出题
5. ⚠️ **常见错误** — 1-2 个初学者易错点 + 错误原因 + 正确做法

**与普通对话的区别**：普通对话是 assistant 自由回复，辅导模式强制五段式结构。prompt 中注入了学生完整画像信息。

---

### Agent 5：EvaluationAgent — `backend/agents/evaluation_agent.py`

**职责**：综合多源数据做多维度学习效果评估。

**输入数据源（5 个维度交叉分析）**：
1. 学生画像（当前水平基线）
2. 行为埋点汇总（总行为次数、类型分布、最近活跃时间、接触过的知识点）
3. 最近 10 轮对话摘要
4. 学习路径进度（哪些阶段已接触）
5. 上次评估结果（用于趋势对比）

**输出维度**：
- 知识掌握度（score 0-100 + level + 评语）
- 学习投入度（score 0-100 + level + 评语）
- 学习进度（score 0-100 + 评语）
- 薄弱点列表（当前仍需加强的知识点）
- 强项列表（已掌握较好的方面）
- 综合分（overall_score 0-100）
- 综合评语（summary，2-3 句话）
- 学习建议（immediate 本周建议 + short_term 两周目标 + focus_topics 重点主题）
- 路径调整建议（should_adjust + reason + recommended_order）

---

## 三、编排层 — `backend/agents/orchestrator.py`

**职责**：串联 Profile → RAG 检索 → 逐个生成 5 种资源 → 汇总返回。

**完整流程**：
1. 读用户画像，解析 JSON 字符串字段（weak_points, interest_areas）
2. 调用 ChromaDB 检索相关知识片段（增强 prompt 的事实准确性）
3. 逐个调用 ResourceAgent 生成 5 种资源（串行执行，避免讯飞 API 并发限流）
4. `doc` 和 `reading` 类型自动追加 AI 来源声明（`add_citations()`）
5. 通过 `asyncio.Queue` 实时推送进度事件给前端（SSE 流式）

**为什么串行而不是并行**：讯飞 API 有并发限制，5 个请求同时发出会被限流拒绝。

---

## 四、API 层 — 4 个路由模块

| 路由模块 | 端点 | 功能 | 特性 |
|---|---|---|---|
| `chat.py` | `POST /api/chat` | SSE 流式对话 | 安全过滤→画像提取→行为埋点→引用声明 |
| | `GET /api/profile/{id}` | 完整画像 JSON | |
| | `GET /api/profile/{id}/dimensions` | 6 维度简化版 | 前端侧边栏用 |
| `resource.py` | `POST /api/resource/generate` | SSE 流式资源生成 | 安全过滤→编排器→进度事件→行为埋点 |
| | `GET /api/resource/types` | 5 种资源类型定义 | |
| | `POST /api/resource/generate_single` | 单资源非流式 | |
| `path.py` | `GET /api/path/{id}` | 个性化路径 | 自动注入评估结果 |
| | `POST /api/path/plan` | 强制重新规划 | |
| | `GET /api/path/default` | 兜底默认路径 | 无画像时使用 |
| `assessment.py` | `POST /api/assessment/evaluate` | 触发 LLM 评估 | 持久化到 assessment_records |
| | `GET /api/assessment/{id}` | 最新评估结果 | |
| | `GET /api/assessment/{id}/history` | 评估历史列表 | |

**安全机制（已接入主流程）**：
- 所有用户输入经 `safety.py` 检查：敏感词匹配 + Prompt Injection 正则（忽略.*指令 / ignore.*instruction 等），不通过返回 HTTP 422
- 辅导模式回复自动追加 "本内容由 AI 生成，已通过知识库校验。如有疑问，请参考原课程教材。"
- 资源生成 `doc`/`reading` 类型自动追加引用声明
- `doc` 类型生成后额外做 LLM 事实核查

---

## 五、前端层 — `app.py`

**页面布局**：左侧边栏（固定 350px） + 右侧 3 个 Tab

### 侧边栏（从上到下）

1. **用户 ID 输入框** — 默认 `student_01`，切换用户即切换画像
2. **后端连接状态** — 绿色圆点 = 已连接，红色 = 未启动
3. **📋 学习画像面板** — 6 维度卡片
   - 已填充（绿色左边框 + 渐绿背景）
   - 未填充（灰色左边框 + 浅灰背景）
   - 模式徽章：画像收集模式（橙色）/ 个性化教学模式（绿色）
4. **📊 学习评估面板**
   - 有评估：综合分大字 + 三维度进度条（知识掌握📖/学习投入🔥/学习进度📈）+ 摘要 + 重新评估按钮
   - 无评估：开始评估按钮
   - 无画像：灰色提示文字
5. **🗺️ 学习路径导航** — 阶段圆点列表
   - 绿色实心 = 已完成
   - 紫色发光 = 当前位置
   - 灰色空心 = 待开始
   - 已定制标注 "✨ 已根据画像定制"

### Tab 1：💬 对话学习

- 顶部模式提示（画像收集 or 个性化教学）
- 聊天消息区：每条消息调用 `_render_markdown()`
  - 普通 Markdown → `st.markdown()`
  - Mermaid 代码块 → `st.components.v1.html()` 嵌入 mermaid.js CDN 渲染为可视化图表
- 输入框 `st.chat_input()`
- SSE 流式接收：逐 token 更新 placeholder，打字机效果
- 辅导模式触发后显示蓝色提示条 "🧑‍🏫 辅导模式 · 已根据你的画像生成结构化答疑"
- 画像未建立时每条回复下方显示提示 "🔍 系统正在从对话中了解你的学习情况"

### Tab 2：📚 学习资源

- 5 种资源类型卡片预览（图标 + 名称 + 类型标签）
- 知识点输入框 + 生成按钮
- 生成中：进度条 + 状态文字（检索中→生成中→已完成）
- 生成后：可展开的资源面板，每个资源用 `_render_markdown()` 渲染

### Tab 3：🗺️ 学习路径

- 评估摘要条（如有）：综合分 + 评语摘要
- 顶部总览：完成百分比 + 总阶段数 + 总学时
- 周计划文字
- 时间线可视化：
  - 每阶段：紫色圆点 + 阶段标题 + 优先级标签（🔴重点 / 🟠中等 / 🟢了解）
  - 知识点列表 + 建议学时 + 学习建议
- 重新规划按钮（需画像已建立）

---

## 六、用户完整使用链路

### 场景：一个大一新生从零开始

#### 第 1 次对话（画像收集模式）

```
用户输入："我学过一点 C 语言，想学 Python 做数据分析"
    ↓
safety.check_content() → 通过
    ↓
_build_system_prompt() → 检测到无画像 → 返回"画像收集模式"系统提示词
    ↓
讯飞星火 API 流式回复（引导用户继续聊学习情况、偏好等）
    ↓
extract_profile_from_chat() → 从对话提取画像 → 置信度 > 0.5 → 写入 user_profiles
    ↓
record_behavior() → behavior_type="chat"
    ↓
前端侧边栏画像卡片：部分从灰色变绿色
```

#### 第 2-3 次对话（画像逐步完善）

- 每次对话后画像增量更新，各维度逐渐填满
- 侧边栏从 "🔍 画像收集模式" 切换为 "🧠 个性化教学模式"

#### 第 4 次对话（触发辅导模式）

```
用户输入："列表推导式怎么用？"
    ↓
safety.check_content() → 通过
    ↓
_is_tutor_question("列表推导式怎么用？") → 含 "怎么" 关键词 → True
has_profile → True → is_tutor_mode = True
    ↓
build_tutor_prompt() → 五段式 system prompt + 画像信息注入
    ↓
讯飞星火返回结构化答疑（📖概念+🧠图解+💻代码+✏️练习+⚠️纠错）
    ↓
_render_markdown() → 检测到 Mermaid 代码块 → 调用 mermaid.js 渲染为思维导图
    ↓
add_citations() → 追加 "本内容由 AI 生成..."
    ↓
record_behavior() → behavior_type="tutor_question", topics=["列表"]
    ↓
extract_profile_from_chat() → 画像更新（薄弱点/知识基础可能有变化）
```

#### 用户去资源 Tab 生成材料

```
输入知识点 "列表推导式" → 点击生成
    ↓
safety.check_content("列表推导式") → 通过
    ↓
orchestrator 启动：
  Stage 1: ChromaDB 检索 "列表推导式" → 找到知识库相关段落
  Stage 2: 串行调用 5 个 ResourceAgent
    - DocAgent: 生成讲解文档（含思考题）
    - MindmapAgent: 生成 Mermaid 思维导图
    - ExerciseAgent: 生成 3 选+2 码练习题
    - ReadingAgent: 推荐书籍/博客/视频
    - PracticeAgent: 生成实操案例代码
  Stage 3: doc/reading 追加 AI 声明
    ↓
前端 SSE 接收进度事件 → 进度条实时更新 → 5 个资源卡片可展开查看
    ↓
record_behavior() → behavior_type="resource_generate", topic="列表推导式"
```

#### 用户查看学习路径

```
GET /api/path/student_01
    ↓
读画像 + 最新评估 → plan_learning_path(enriched_profile)
    ↓
返回 6 阶段路径 JSON（起始点、学时、优先级、学习建议）
    ↓
前端时间线渲染：6 阶段、优先级标注、周计划
    ↓
record_behavior() → behavior_type="path_view"
```

#### 用户触发学习评估

```
侧边栏点击 "📊 开始评估"
    ↓
POST /api/assessment/evaluate
    ↓
evaluate_learning() 收集：
  - 画像（当前水平基线）
  - 最近 100 条行为埋点
  - 行为统计汇总（类型分布、活跃度、接触知识点）
  - 最近 30 条对话记录
  - 学习路径进度
  - 上次评估结果（如存在）
    ↓
全部喂给 LLM 做多维度分析 → JSON 结果
    ↓
save_assessment() → 写入 assessment_records
    ↓
前端侧边栏刷新：综合分 + 三维度进度条 + 摘要
    ↓
下次查看学习路径时 → 自动注入评估结果 → 路径可能被调整
```

---

## 七、实际优劣势分析

### 真正有价值的地方

1. **全链路自动化画像构建** — 用户不需要填任何表单，聊天过程中系统自动了解你。6 个维度覆盖了学习者的核心特征，且每个维度都有明确的后续用途（不是收集了就放着）

2. **五段式辅导结构** — 概念→图解→代码→练习→纠错，这个顺序符合认知负荷理论和刻意练习原则。不是泛泛地回答，而是强制 LLM 按教学逻辑输出

3. **Mermaid 可视化直接渲染** — 聊天里生成的思维导图不用跳转到其他页面，在当前对话流中就能看到图形化的知识结构

4. **评估 → 路径的闭环** — 评估结果不是孤立的数字，而是自动反哺到学习路径规划中。学生薄弱的地方在路径中被标记为高优先级

5. **所有行为被追踪** — 聊天、资源生成、路径查看全部有埋点，评估智能体可以基于真实行为数据而非空泛的猜测来分析学生

### 当前短板（按严重程度排序）

1. **Agent 本质是 prompt 模板，不是真正的多智能体协同** — 5 个 Agent 之间没有推理链、没有信息传递、没有协商机制。每个 Agent 独立调一次 LLM。LangGraph 的 StateGraph 编排能力完全没有用到——orchestrator 就是一个 for 循环

2. **学习进度没有持续追踪** — 用户看了第 3 章的资源、问了第 3 章的问题，但系统不知道"你已经学完第 3 章"。`learning_progress` 表的 `status` 和 `completed_at` 字段从未被写入。下次规划路径还是从头开始

3. **画像没有长期记忆** — 每次只取最近 20 轮对话来提取画像，旧信息被覆盖。学生在首次对话中说"我想做游戏开发"，一个月后系统忘了。画像字段直接覆盖，没有变更历史

4. **对话与资源是割裂的** — 在聊天里刚讲完"列表推导式"，资源 Tab 不会自动推荐相关材料。用户需要手动切换到资源 Tab、手动输入知识点名称。这不符合自然的学习流程

5. **知识库是静态的** — 6 个 Markdown 文件 + 18 道固定题库（每章 3 题）。没有增量更新机制。ChromaDB 检索效果依赖 sentence-transformers 是否正确安装，且检索质量未经系统验证

6. **没有代码执行环境** — 练习题只能看答案、不能在线跑。辅导模式给出的代码示例，用户没法一键运行看结果。这是学 Python 最核心的需求——亲自动手写代码并看到运行结果

7. **评估质量依赖数据积累** — 新用户行为数据不足时，评估结果会比较空泛。没有"冷启动"策略

8. **所有智能体共享同一个 LLM** — 画像提取、资源生成、路径规划、辅导答疑、学习评估全部调用星火同一个 API。没有针对不同任务使用不同模型（例如评估可以用更便宜的模型，辅导可以用更强的模型）

---

## 八、文件清单

```
smart-tutor/
├── app.py                              # Streamlit 前端（单文件，~900行）
├── backend/
│   ├── main.py                         # FastAPI 入口 + 路由注册
│   ├── agents/
│   │   ├── profile_agent.py            # 画像提取（6维度 + 增量更新）
│   │   ├── resource_agent.py           # 5种资源生成（含防幻觉检查）
│   │   ├── path_agent.py               # 路径规划 + 动态调整
│   │   ├── tutor_agent.py              # 五段式辅导（提问检测 + prompt构建）
│   │   ├── evaluation_agent.py         # 多维度评估（行为+对话+画像+路径交叉分析）
│   │   └── orchestrator.py             # 资源生成编排（RAG→串行Agent→汇总）
│   ├── api/
│   │   ├── chat.py                     # 对话/画像 API（SSE流式 + 安全 + 埋点）
│   │   ├── resource.py                 # 资源生成 API（SSE流式 + 进度事件）
│   │   ├── path.py                     # 学习路径 API（评估注入）
│   │   └── assessment.py              # 评估 API（触发/查询/历史）
│   ├── db/
│   │   ├── models.py                   # SQLite 5表 + 所有CRUD函数
│   │   └── vector_store.py             # ChromaDB 向量检索
│   ├── llm/
│   │   └── spark.py                    # 讯飞星火 WebSocket/HTTP 封装
│   └── utils/
│       ├── safety.py                   # 内容安全过滤（敏感词+注入检测）
│       └── anti_hallucination.py       # 防幻觉（LLM自检+AST语法校验+引用声明）
├── knowledge_base/
│   ├── syllabus.md                     # 课程大纲（6章42学时）
│   ├── chapters/                       # 6章知识文档
│   │   ├── 01_basics.md
│   │   ├── 02_control_flow.md
│   │   ├── 03_functions.md
│   │   ├── 04_data_structures.md
│   │   ├── 05_oop.md
│   │   └── 06_projects.md
│   └── exercises/
│       └── questions.json              # 18道固定题库（每章3题）
├── data/                               # 运行时数据（自动生成）
│   ├── tutor.db                        # SQLite 数据库
│   └── chroma/                         # ChromaDB 持久化目录
├── requirements.txt
├── README.md
├── REQUIREMENTS.md                     # 赛题需求对照表
├── CLAUDE.md                           # 项目状态说明书
└── SYSTEM_ANALYSIS.md                  # 本文档
```
