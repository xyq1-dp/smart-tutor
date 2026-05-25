"""
Streamlit 前端 — 个性化学习智能助手
"""

import json
import re
import streamlit as st
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

# === Mermaid 渲染工具 ===
MERMAID_TPL = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>body{{margin:0;padding:12px;background:#fafafa;}} .mermaid{{text-align:center;}}</style>
</head><body>
<div class="mermaid">{code}</div>
<script>mermaid.initialize({{startOnLoad:true,theme:'default'}});</script>
</body></html>"""


def _render_markdown(content: str):
    """渲染 Markdown，自动处理 Mermaid 图表"""
    # 查找 mermaid 代码块
    pattern = r'```mermaid\s*\n(.*?)```'
    mermaid_blocks = list(re.finditer(pattern, content, re.DOTALL))

    if not mermaid_blocks:
        st.markdown(content)
        return

    # 拆分渲染
    last_end = 0
    for match in mermaid_blocks:
        # 渲染前面的普通 markdown
        before = content[last_end:match.start()].strip()
        if before:
            st.markdown(before)

        # 渲染 Mermaid 图
        mermaid_code = match.group(1).strip()
        try:
            import streamlit.components.v1 as components
            html = MERMAID_TPL.format(code=mermaid_code)
            components.html(html, height=300, scrolling=True)
        except Exception:
            st.code(mermaid_code, language="mermaid")

        last_end = match.end()

    # 渲染剩余内容
    after = content[last_end:].strip()
    if after:
        st.markdown(after)

st.set_page_config(
    page_title="智能学习助手",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === 自定义样式 ===
st.markdown("""
<style>
    /* ===== 全局 ===== */
    .main-header {
        font-size: 1.7rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        color: #999;
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
    }

    /* ===== 画像维度卡片 ===== */
    .profile-card {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.45rem 0.6rem;
        margin-bottom: 0.35rem;
        border-radius: 0.5rem;
        font-size: 0.85rem;
        transition: all 0.2s;
    }
    .profile-card.filled {
        background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
        border-left: 3px solid #4caf50;
    }
    .profile-card.empty {
        background: #fafafa;
        border-left: 3px solid #ddd;
        color: #aaa;
    }
    .profile-card .icon {
        font-size: 1rem;
        width: 1.4rem;
        text-align: center;
    }
    .profile-card .label {
        font-weight: 600;
        color: #444;
        min-width: 3.2rem;
    }
    .profile-card.empty .label {
        color: #bbb;
    }
    .profile-card .value {
        color: #333;
        flex: 1;
        text-align: right;
    }
    .profile-card.empty .value {
        color: #ccc;
    }

    /* ===== 模式徽章 ===== */
    .mode-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }
    .mode-badge.profile {
        background: #fff3e0;
        color: #e65100;
        border: 1px solid #ffcc80;
    }
    .mode-badge.teaching {
        background: #e8f5e9;
        color: #2e7d32;
        border: 1px solid #a5d6a7;
    }

    /* ===== 学习路径步骤条（侧边栏） ===== */
    .path-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0;
        font-size: 0.82rem;
    }
    .path-dot {
        width: 0.6rem;
        height: 0.6rem;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .path-dot.done { background: #4caf50; }
    .path-dot.current { background: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.25); }
    .path-dot.pending { background: #ddd; }

    /* ===== 资源卡片 ===== */
    .resource-card {
        border: 1px solid #e8e8e8;
        border-radius: 0.75rem;
        padding: 1.1rem 1rem;
        margin-bottom: 0.6rem;
        transition: all 0.25s;
        cursor: pointer;
        background: #fff;
    }
    .resource-card:hover {
        box-shadow: 0 6px 20px rgba(102,126,234,0.12);
        border-color: #667eea;
        transform: translateY(-1px);
    }
    .resource-card .r-icon {
        font-size: 1.6rem;
        margin-bottom: 0.3rem;
    }
    .resource-card .r-title {
        font-weight: 650;
        font-size: 0.95rem;
        margin-bottom: 0.15rem;
    }
    .resource-card .r-desc {
        font-size: 0.8rem;
        color: #999;
    }
    .resource-card .r-badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 0.7rem;
        font-size: 0.72rem;
        font-weight: 600;
        margin-top: 0.4rem;
    }
    .badge-doc { background: #e3f2fd; color: #1565c0; }
    .badge-mindmap { background: #f3e5f5; color: #7b1fa2; }
    .badge-exercise { background: #fff3e0; color: #e65100; }
    .badge-reading { background: #e8f5e9; color: #2e7d32; }
    .badge-practice { background: #fce4ec; color: #c62828; }

    /* ===== 聊天消息增强 ===== */
    .extract-hint {
        font-size: 0.75rem;
        color: #999;
        margin-top: 0.5rem;
        padding: 0.4rem 0.7rem;
        background: #fafafa;
        border-radius: 0.4rem;
        border: 1px dashed #e0e0e0;
    }
    .extract-hint strong {
        color: #667eea;
    }

    /* ===== 学习路径时间线 ===== */
    .timeline-stage {
        display: flex;
        gap: 1rem;
        margin-bottom: 0.5rem;
    }
    .timeline-line {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex-shrink: 0;
    }
    .timeline-circle {
        width: 1rem;
        height: 1rem;
        border-radius: 50%;
        border: 2px solid #ddd;
        background: #fff;
        flex-shrink: 0;
        margin-top: 0.25rem;
    }
    .timeline-circle.active {
        border-color: #667eea;
        background: #667eea;
    }
    .timeline-circle.done {
        border-color: #4caf50;
        background: #4caf50;
    }
    .timeline-bar {
        width: 2px;
        flex: 1;
        background: #eee;
        min-height: 1.5rem;
    }
    .timeline-bar.done {
        background: #4caf50;
    }
    .timeline-body {
        flex: 1;
        padding-bottom: 1rem;
    }
    .timeline-body h4 {
        margin: 0;
        font-size: 0.95rem;
    }
    .timeline-body .topics {
        font-size: 0.8rem;
        color: #888;
        margin-top: 0.15rem;
    }
    .timeline-body .hours {
        font-size: 0.75rem;
        color: #aaa;
    }

    /* ===== 进度环 ===== */
    .progress-ring {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.6rem 0.8rem;
        background: #f9f9ff;
        border-radius: 0.6rem;
        margin-bottom: 0.8rem;
    }
    .progress-ring .big-num {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* ===== 连接状态 ===== */
    .conn-dot {
        display: inline-block;
        width: 0.5rem;
        height: 0.5rem;
        border-radius: 50%;
        margin-right: 0.3rem;
    }
    .conn-dot.on { background: #4caf50; }
    .conn-dot.off { background: #f44336; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# === 侧边栏 ===
# ============================================================
with st.sidebar:
    st.markdown('<div class="main-header">🎓 智能学习助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Python 程序设计基础</div>', unsafe_allow_html=True)

    # 用户身份
    user_id = st.text_input("👤 用户ID", value="student_01", key="user_id_input",
                             label_visibility="collapsed")

    st.divider()

    # ---- 后端连接检查 ----
    backend_ok = False
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=2)
        backend_ok = resp.status_code == 200
    except requests.ConnectionError:
        backend_ok = False

    if backend_ok:
        st.markdown(
            '<span class="conn-dot on"></span><span style="font-size:0.78rem;color:#666;">后端已连接</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="conn-dot off"></span><span style="font-size:0.78rem;color:#c62828;">后端未启动</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ---- 学习画像 ----
    st.subheader("📋 学习画像")

    # 维度图标映射
    DIM_ICONS = {
        "知识基础": "📖",
        "学习目标": "🎯",
        "认知风格": "🧩",
        "学习节奏": "⚡",
        "薄弱点": "🔍",
        "兴趣方向": "💡",
    }
    DIM_EMPTY = {
        "知识基础": "未知",
        "学习目标": "未设定",
        "认知风格": "未设定",
        "学习节奏": "正常",
        "薄弱点": "待检测",
        "兴趣方向": "待检测",
    }

    # 加载画像
    profile_dims = []
    if backend_ok:
        try:
            dims_resp = requests.get(
                f"{BACKEND_URL}/api/profile/{user_id}/dimensions", timeout=5
            )
            if dims_resp.status_code == 200:
                data = dims_resp.json()
                profile_dims = [
                    (d["label"], d["value"]) for d in data.get("dimensions", [])
                ]
        except (requests.ConnectionError, requests.Timeout):
            pass

    if not profile_dims:
        profile_dims = [(k, v) for k, v in DIM_EMPTY.items()]

    # 判断画像是否"有价值"（已从对话中提取过）
    has_real_profile = any(
        v not in ("未知", "未设定", "待检测", "", "beginner", "normal")
        for _, v in profile_dims
    )

    # 画像模式徽章
    if has_real_profile:
        st.markdown(
            '<div class="mode-badge teaching">🧠 个性化教学模式</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mode-badge profile">🔍 画像收集模式</div>',
            unsafe_allow_html=True,
        )

    # 展示每个维度
    for label, value in profile_dims:
        is_filled = value not in ("未知", "未设定", "待检测", "", "beginner", "normal")
        # 列表类维度特殊处理
        if value in ("[]", "待检测"):
            is_filled = False
        css_class = "filled" if is_filled else "empty"
        icon = DIM_ICONS.get(label, "📌")
        st.markdown(
            f'<div class="profile-card {css_class}">'
            f'<span class="icon">{icon}</span>'
            f'<span class="label">{label}</span>'
            f'<span class="value">{value}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ---- 学习评估 ----
    st.subheader("📊 学习评估")

    # 加载评估数据
    assessment_data = None
    if backend_ok and has_real_profile:
        try:
            assess_resp = requests.get(
                f"{BACKEND_URL}/api/assessment/{user_id}", timeout=10
            )
            if assess_resp.status_code == 200:
                assess_json = assess_resp.json()
                if assess_json.get("has_assessment"):
                    assessment_data = assess_json["assessment"]
        except (requests.ConnectionError, requests.Timeout):
            pass

    if assessment_data:
        overall = assessment_data.get("overall_score", 0)
        st.markdown(
            f'<div class="progress-ring">'
            f'<span class="big-num">{overall}</span>'
            f'<span style="color:#666;font-size:0.8rem;">综合评分 / 100</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        # 三维度简版
        dims = assessment_data.get("dimensions", {})
        if isinstance(dims, str):
            try:
                dims = json.loads(dims)
            except (json.JSONDecodeError, ValueError):
                dims = {}
        dim_labels = [
            ("knowledge_mastery", "知识掌握", "📖"),
            ("engagement", "学习投入", "🔥"),
            ("progress", "学习进度", "📈"),
        ]
        for key, label, icon in dim_labels:
            d = dims.get(key, {})
            if isinstance(d, dict):
                score = d.get("score", 0)
            else:
                score = 0
            bar_color = "#4caf50" if score >= 70 else "#fb8c00" if score >= 40 else "#f44336"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:0.5rem;'
                f'padding:0.2rem 0;font-size:0.8rem;">'
                f'<span>{icon}</span><span style="width:3.5rem;">{label}</span>'
                f'<span style="flex:1;background:#eee;border-radius:4px;height:6px;">'
                f'<span style="display:block;width:{score}%;background:{bar_color};'
                f'height:6px;border-radius:4px;"></span></span>'
                f'<span style="width:2rem;text-align:right;">{score}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.caption(assessment_data.get("summary", "")[:80] + "...")

        # 触发新评估按钮
        if st.button("🔄 重新评估", use_container_width=True, key="sidebar_reeval"):
            with st.spinner("评估中..."):
                try:
                    r = requests.post(
                        f"{BACKEND_URL}/api/assessment/evaluate",
                        json={"user_id": user_id},
                        timeout=120,
                    )
                    if r.status_code == 200:
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "评估失败"))
                except Exception as e:
                    st.error(f"请求失败: {str(e)}")
    else:
        if has_real_profile:
            st.markdown(
                '<span style="font-size:0.78rem;color:#999;">尚未评估，点击下方按钮开始</span>',
                unsafe_allow_html=True,
            )
            if st.button("📊 开始评估", use_container_width=True, key="sidebar_eval"):
                with st.spinner("正在分析学习数据..."):
                    try:
                        r = requests.post(
                            f"{BACKEND_URL}/api/assessment/evaluate",
                            json={"user_id": user_id},
                            timeout=120,
                        )
                        if r.status_code == 200:
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "评估失败"))
                    except Exception as e:
                        st.error(f"请求失败: {str(e)}")
        else:
            st.markdown(
                '<span style="font-size:0.78rem;color:#ccc;">先建立画像后可评估</span>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ---- 学习路径导航 ----
    st.subheader("🗺️ 学习路径")

    path_is_personalized = False
    chapters = []
    if backend_ok:
        try:
            path_resp = requests.get(f"{BACKEND_URL}/api/path/{user_id}", timeout=10)
            if path_resp.status_code == 200:
                path_data = path_resp.json()
                path_is_personalized = path_data.get("personalized", False)
                chapters = [
                    (f"0{s['order']}", s["title"],
                     "current" if s["order"] == 1 else "pending")
                    for s in path_data.get("stages", [])
                ]
        except (requests.ConnectionError, requests.Timeout):
            pass

    if path_is_personalized:
        st.markdown(
            '<span style="font-size:0.72rem;color:#4caf50;">✨ 已根据画像定制</span>',
            unsafe_allow_html=True,
        )

    if not chapters:
        chapters = [
            ("01", "Python 基础语法", "pending"),
            ("02", "流程控制", "pending"),
            ("03", "函数与模块", "pending"),
            ("04", "数据结构", "pending"),
            ("05", "面向对象编程", "pending"),
            ("06", "综合项目实战", "pending"),
        ]
    else:
        # 根据实际进度调整状态：priority=done → status=done
        chapters = [
            (num, title, "done" if status == "done" else status)
            for num, title, status in chapters
        ]

    for num, title, status in chapters:
        dot_class = {"done": "done", "current": "current", "pending": "pending"}
        st.markdown(
            f'<div class="path-item">'
            f'<span class="path-dot {dot_class.get(status, "pending")}"></span>'
            f'<span style="color:#888;font-size:0.75rem;width:1.4rem;">{num}</span>'
            f'<span style="color:{"#333" if status != "pending" else "#bbb"};font-size:0.82rem;">{title}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# === 主面板 ===
# ============================================================
tab_chat, tab_resources, tab_path = st.tabs(
    ["💬 对话学习", "📚 学习资源", "🗺️ 学习路径"]
)

# ============================================================
# --- 对话学习 Tab ---
# ============================================================
with tab_chat:
    # 顶部模式提示
    if has_real_profile:
        st.markdown(
            '<div class="mode-badge teaching">🧠 个性化教学模式 — 根据你的画像定制回复</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mode-badge profile">🔍 画像收集模式 — 告诉我你的学习情况，我会逐步了解你</div>',
            unsafe_allow_html=True,
        )

    # 初始化聊天记录
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 你好！我是你的 Python 学习助手。\n\n"
                    "我会通过聊天了解你的学习情况，为你定制个性化的学习方案。\n\n"
                    "让我们开始吧——**你之前学过编程吗？是什么样的基础？**"
                ),
            }
        ]

    # 展示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            _render_markdown(msg["content"])

    # 接收用户输入
    if prompt := st.chat_input("输入你的问题或回复..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            if backend_ok:
                try:
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[:-1]
                    ][-20:]

                    resp = requests.post(
                        f"{BACKEND_URL}/api/chat",
                        json={
                            "message": prompt,
                            "user_id": user_id,
                            "history": history,
                        },
                        stream=True,
                        timeout=60,
                    )

                    if resp.status_code == 200:
                        full_response = ""
                        placeholder = st.empty()
                        is_tutor = False

                        for line in resp.iter_lines():
                            if not line:
                                continue
                            line = line.decode("utf-8")
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if data.get("error"):
                                        full_response = data["error"]
                                        placeholder.error(full_response)
                                    elif data.get("done"):
                                        is_tutor = data.get("tutor_mode", False)
                                        break
                                    elif data.get("content"):
                                        full_response += data["content"]
                                        placeholder.markdown(full_response + "▌")
                                except json.JSONDecodeError:
                                    pass

                        placeholder.markdown(full_response)

                        # 辅导模式提示 + 资源联动入口
                        if is_tutor:
                            st.markdown(
                                '<div class="extract-hint" style="border-color:#667eea;background:#f5f7ff;">'
                                '🧑‍🏫 <strong>辅导模式</strong> · 已根据你的画像生成结构化答疑</div>',
                                unsafe_allow_html=True,
                            )
                            # 检测知识点，提供资源直达入口
                            detected_topic = None
                            for kw in ["列表推导", "列表", "字典推导", "字典", "集合", "元组",
                                        "函数", "lambda", "装饰器", "类", "继承", "多态",
                                        "异常处理", "异常", "文件操作", "文件", "模块",
                                        "循环", "条件判断", "字符串", "面向对象"]:
                                if kw in prompt:
                                    detected_topic = kw
                                    break
                            if not detected_topic:
                                detected_topic = prompt[:20]
                            if st.button(f"📚 为「{detected_topic}」生成学习资料",
                                         key=f"resource_cta_{len(st.session_state.messages)}"):
                                st.session_state.pending_resource_topic = detected_topic
                                st.info(f"已选择「{detected_topic}」，切换到 📚 学习资源 Tab 即可自动填充")

                        # 画像提取提示
                        if not has_real_profile:
                            st.markdown(
                                '<div class="extract-hint">'
                                '🔍 系统正在从对话中了解你的学习情况，'
                                '侧边栏画像将<strong>自动更新</strong></div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        full_response = f"抱歉，后端返回了错误（{resp.status_code}）。"
                        st.error(full_response)
                except requests.ConnectionError:
                    full_response = "⚠️ 后端服务未启动，请先运行 `uvicorn backend.main:app --port 8001`"
                    st.warning(full_response)
                except requests.Timeout:
                    full_response = "⏱️ 请求超时，请稍后重试。"
                    st.error(full_response)
            else:
                full_response = (
                    "⚠️ 后端服务离线模式。\n\n"
                    "请先启动后端服务：`uvicorn backend.main:app --port 8001`\n"
                    "然后刷新页面。"
                )
                st.warning(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()


# ============================================================
# --- 学习资源 Tab ---
# ============================================================
with tab_resources:
    st.markdown("### 📚 个性化学习资源")

    RESOURCE_INFO = {
        "doc": ("📄", "课程讲解文档", "badge-doc"),
        "mindmap": ("🧠", "知识点思维导图", "badge-mindmap"),
        "exercise": ("✏️", "自适应练习题", "badge-exercise"),
        "reading": ("📚", "拓展阅读材料", "badge-reading"),
        "practice": ("💻", "代码实操案例", "badge-practice"),
    }

    # ---- 资源生成操作区 ----
    # 检查是否有从聊天联动过来的待处理主题
    pending_topic = st.session_state.pop("pending_resource_topic", None)
    if pending_topic:
        st.session_state.resource_topic = pending_topic

    col_topic, col_btn = st.columns([3, 1])
    with col_topic:
        topic = st.text_input(
            "知识点主题",
            placeholder="例如：Python 列表推导式、函数参数、面向对象...",
            key="resource_topic",
        )
    with col_btn:
        st.write("")  # 对齐
        generate_btn = st.button("🚀 生成资源", type="primary", use_container_width=True,
                                  disabled=not backend_ok or not topic.strip())

    # ---- 类型预览卡片 ----
    with st.expander("📋 支持的资源类型", expanded=not topic.strip()):
        type_cols = st.columns(5)
        for i, (rtype, (emoji, name, badge_class)) in enumerate(RESOURCE_INFO.items()):
            with type_cols[i]:
                st.markdown(f"""
                <div class="resource-card" style="text-align:center;">
                    <div class="r-icon">{emoji}</div>
                    <div class="r-title">{name}</div>
                    <span class="r-badge {badge_class}">{rtype}</span>
                </div>
                """, unsafe_allow_html=True)

    # ---- 生成资源 ----
    if generate_btn and topic.strip():
        st.divider()
        st.markdown(f"#### 🔄 正在为 **「{topic}」** 生成资源...")

        progress_bar = st.progress(0, text="准备中...")
        status_area = st.empty()

        # 用于存放已生成资源内容的容器
        result_containers = {
            rtype: st.empty() for rtype in RESOURCE_INFO
        }

        try:
            resp = requests.post(
                f"{BACKEND_URL}/api/resource/generate",
                json={
                    "topic": topic,
                    "user_id": user_id,
                    "resource_types": list(RESOURCE_INFO.keys()),
                },
                stream=True,
                timeout=300,
            )

            if resp.status_code == 200:
                generated_count = 0
                total_count = 5
                current_type = None
                full_result = None

                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            stage = event.get("stage", "")

                            if stage == "kb_search":
                                status_area.info(f"🔍 {event.get('message', '')}")

                            elif stage == "agent_start":
                                current_type = event.get("type", "")
                                info = RESOURCE_INFO.get(current_type, ("", "", ""))
                                status_area.info(f"⏳ 正在生成：{info[0]} {info[1]}...")

                            elif stage == "agent_done":
                                generated_count += 1
                                pct = int(generated_count / total_count * 100)
                                progress_bar.progress(
                                    pct, text=f"已完成 {generated_count}/{total_count}"
                                )
                                status_area.success(
                                    f"✅ 已完成：{event.get('type', '')}"
                                )

                            elif stage == "agent_error":
                                status_area.warning(
                                    f"⚠️ {event.get('type', '')} 生成失败: {event.get('error', '')}"
                                )

                            elif stage == "result":
                                full_result = event.get("data", {})
                                progress_bar.progress(100, text="全部完成！")

                            elif event.get("done"):
                                break

                        except json.JSONDecodeError:
                            pass

                # 展示生成的资源
                if full_result and full_result.get("resources"):
                    st.success(f"✅ 已为「{topic}」生成 {len(full_result['resources'])} 个资源！")

                    for rtype, content in full_result["resources"].items():
                        emoji, name, badge_class = RESOURCE_INFO.get(rtype, ("📌", rtype, ""))
                        with st.expander(f"{emoji} {name}", expanded=False):
                            _render_markdown(content)

                elif full_result and full_result.get("errors"):
                    st.error(f"生成过程中出现错误：{full_result['errors']}")
                else:
                    st.warning("未能获取资源结果，请重试。")

            else:
                st.error(f"后端返回错误（{resp.status_code}）")

        except requests.ConnectionError:
            st.error("⚠️ 后端未连接，请启动后端服务。")
        except requests.Timeout:
            st.error("⏱️ 生成超时，请尝试更小的知识点范围。")
        except Exception as e:
            st.error(f"生成失败：{str(e)}")


# ============================================================
# --- 学习路径 Tab ---
# ============================================================
with tab_path:
    st.markdown("### 🗺️ 你的个性化学习路径")

    # 加载路径状态
    if "path_data" not in st.session_state:
        st.session_state.path_data = None

    if backend_ok:
        # "重新规划"按钮
        col1, col2 = st.columns([3, 1])
        with col2:
            regenerate = st.button("🔄 重新规划", use_container_width=True,
                                    disabled=not has_real_profile)

        if regenerate:
            with st.spinner("正在根据你的画像重新规划学习路径..."):
                try:
                    r = requests.post(
                        f"{BACKEND_URL}/api/path/plan",
                        json={"user_id": user_id},
                        timeout=60,
                    )
                    if r.status_code == 200:
                        st.session_state.path_data = r.json()
                        st.rerun()
                    else:
                        st.error(f"规划失败：{r.json().get('detail', '未知错误')}")
                except Exception as e:
                    st.error(f"请求失败：{str(e)}")

        # 加载路径数据
        if st.session_state.path_data is None:
            try:
                resp = requests.get(f"{BACKEND_URL}/api/path/{user_id}", timeout=10)
                if resp.status_code == 200:
                    st.session_state.path_data = resp.json()
            except (requests.ConnectionError, requests.Timeout):
                pass

        path_data = st.session_state.path_data
        if path_data:
            stages = path_data.get("stages", [])
            is_personalized = path_data.get("personalized", False)
            starting_point = path_data.get("starting_point", "")
            total_hours = path_data.get("total_estimated_hours", 42)
            weekly_plan = path_data.get("weekly_plan", "")

            # 显示评估摘要（如有）
            assess_summary = path_data.get("assessment_summary")
            if assess_summary:
                score = assess_summary.get("overall_score", 0)
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#e8f5e9,#f1f8e9);'
                    f'border-radius:0.6rem;padding:0.8rem 1rem;margin-bottom:0.8rem;">'
                    f'<span style="font-weight:600;">📊 最新评估综合分：{score}/100</span>'
                    f'<span style="font-size:0.78rem;color:#666;margin-left:0.5rem;">'
                    f'{assess_summary.get("summary", "")[:60]}...</span></div>',
                    unsafe_allow_html=True,
                )

            with col1:
                if is_personalized:
                    st.markdown(
                        f'<span style="font-size:0.9rem;color:#4caf50;">'
                        f'✨ 已根据你的画像定制 · 建议从 <strong>{starting_point}</strong> 开始</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<span style="font-size:0.85rem;color:#888;">'
                        f'使用默认路径 · 在聊天中建立画像后可个性化定制</span>',
                        unsafe_allow_html=True,
                    )

            # 顶部总览
            completed = sum(1 for s in stages if s.get("priority") == "done")
            total = len(stages)
            pct = int(completed / total * 100) if total > 0 else 0

            st.markdown(
                f'<div class="progress-ring">'
                f'<span class="big-num">{pct}%</span>'
                f'<span style="color:#666;font-size:0.85rem;">'
                f'共 {total} 个阶段 · 预计 {total_hours} 小时</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 每周计划
            if weekly_plan:
                st.caption(f"📅 {weekly_plan}")

            # 时间线展示
            PRIORITY_COLORS = {"high": "#e53935", "medium": "#fb8c00", "low": "#43a047"}
            for i, stage in enumerate(stages):
                order = stage.get("order", i + 1)
                title = stage.get("title", "")
                topics = stage.get("topics", [])
                hours = stage.get("estimated_hours", 0)
                priority = stage.get("priority", "medium")
                tips = stage.get("tips", "")

                if priority == "done":
                    circle = "done"
                    bar = "done"
                elif order == 1:
                    circle = "active"
                    bar = ""
                else:
                    circle = ""
                    bar = ""

                priority_color = PRIORITY_COLORS.get(priority, "#888")

                st.markdown(f"""
                <div class="timeline-stage">
                    <div class="timeline-line">
                        <div class="timeline-circle {circle}"></div>
                        <div class="timeline-bar {bar}"></div>
                    </div>
                    <div class="timeline-body">
                        <h4>
                            阶段 {order}：{title}
                            <span style="font-size:0.72rem;color:{priority_color};margin-left:0.5rem;">
                                {'🔴 重点' if priority == 'high' else '🟠 中等' if priority == 'medium' else '🟢 了解'}
                            </span>
                        </h4>
                        <div class="topics">{' · '.join(topics)}</div>
                        <div class="hours">⏱ 预计 {hours} 小时{f' · 💡 {tips}' if tips else ''}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.warning("请启动后端服务查看学习路径。")
    else:
        st.warning("请启动后端服务查看学习路径。")
