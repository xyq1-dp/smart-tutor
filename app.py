"""
Streamlit 前端 — 个性化学习智能助手
"""

import json
import streamlit as st
import requests
import sys
import os

# 将 backend 加入 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

st.set_page_config(
    page_title="智能学习助手",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === 自定义样式 ===
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.8rem;
        margin-bottom: 0.5rem;
    }
    .user-message {
        background: #e8f0fe;
    }
    .assistant-message {
        background: #f5f5f5;
    }
    .resource-card {
        border: 1px solid #e0e0e0;
        border-radius: 0.8rem;
        padding: 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.2s;
    }
    .resource-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #667eea;
    }
    .profile-tag {
        display: inline-block;
        background: #e8f0fe;
        color: #1967d2;
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        margin: 0.1rem;
    }
</style>
""", unsafe_allow_html=True)


# === 侧边栏 — 学习画像面板 ===
with st.sidebar:
    st.markdown('<div class="main-header">🎓 智能学习助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Python 程序设计基础</div>', unsafe_allow_html=True)

    st.divider()

    # 用户身份
    user_id = st.text_input("👤 用户ID", value="student_01", key="user_id_input")

    st.divider()

    # 学习画像展示
    st.subheader("📋 学习画像")

    backend_ok = False
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=2)
        backend_ok = resp.status_code == 200
    except requests.ConnectionError:
        backend_ok = False

    if backend_ok:
        st.info("✅ 后端已连接")
    else:
        st.warning("⚠️ 后端未启动")

    # 从后端加载画像数据
    profile_dims = [
        ("知识基础", "未知"),
        ("学习目标", "未设定"),
        ("认知风格", "未设定"),
        ("学习节奏", "正常"),
        ("薄弱点", "待检测"),
        ("兴趣方向", "待检测"),
    ]

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

    with st.expander("查看画像详情", expanded=False):
        cols = st.columns(2)
        for i, (label, value) in enumerate(profile_dims):
            with cols[i % 2]:
                st.markdown(f"**{label}**")
                st.markdown(f'<span class="profile-tag">{value}</span>',
                          unsafe_allow_html=True)

    st.divider()

    # 学习路径导航（从后端加载）
    st.subheader("🗺️ 学习路径")
    chapters = [
        ("01", "Python 基础语法", "⬜"),
        ("02", "流程控制", "⬜"),
        ("03", "函数与模块", "⬜"),
        ("04", "数据结构", "⬜"),
        ("05", "面向对象编程", "⬜"),
        ("06", "综合项目实战", "⬜"),
    ]
    if backend_ok:
        try:
            path_resp = requests.get(f"{BACKEND_URL}/api/path/default", timeout=5)
            if path_resp.status_code == 200:
                path_data = path_resp.json()
                chapters = [
                    (f"0{s['order']}", s["title"], "⬜")
                    for s in path_data.get("stages", [])
                ]
        except (requests.ConnectionError, requests.Timeout):
            pass

    for num, title, status in chapters:
        st.markdown(f"**{num}** {title} {status}")


# === 主面板 ===
tab_chat, tab_resources, tab_path = st.tabs(["💬 对话学习", "📚 学习资源", "🗺️ 学习路径"])

# --- 对话学习 Tab ---
with tab_chat:
    st.markdown("### 与你的专属学习助手对话")

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
            st.markdown(msg["content"])

    # 接收用户输入
    if prompt := st.chat_input("输入你的问题或回复..."):
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 调用后端
        with st.chat_message("assistant"):
            if backend_ok:
                try:
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[:-1]
                    ][-20:]  # 最近 20 条

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
                                        break
                                    elif data.get("content"):
                                        full_response += data["content"]
                                        placeholder.markdown(full_response + "▌")
                                except json.JSONDecodeError:
                                    pass

                        placeholder.markdown(full_response)
                    else:
                        full_response = f"抱歉，后端返回了错误（{resp.status_code}）。"
                        st.error(full_response)
                except requests.ConnectionError:
                    full_response = "⚠️ 后端服务未启动，请先运行 `python -m backend.main`"
                    st.warning(full_response)
                except requests.Timeout:
                    full_response = "⏱️ 请求超时，请稍后重试。"
                    st.error(full_response)
            else:
                full_response = (
                    f"⚠️ 后端服务离线模式。\n\n"
                    f"你说：「{prompt}」\n\n"
                    f"请先启动后端服务：`uvicorn backend.main:app --reload`\n"
                    f"然后刷新页面。"
                )
                st.warning(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()


# --- 学习资源 Tab ---
with tab_resources:
    st.markdown("### 📚 个性化学习资源")

    resource_types = [
        ("📄", "课程讲解文档", "根据你的知识水平定制的详细讲解"),
        ("🧠", "知识点思维导图", "用Mermaid格式生成的思维导图"),
        ("✏️", "练习题目", "自适应难度的练习题"),
        ("📚", "拓展阅读材料", "精选的进阶学习资料"),
        ("💻", "代码实操案例", "带注释的实战代码示例"),
    ]

    for emoji, name, desc in resource_types:
        with st.container():
            st.markdown(f"""
            <div class="resource-card">
                <strong>{emoji} {name}</strong><br>
                <small style="color:#888;">{desc}</small>
            </div>
            """, unsafe_allow_html=True)

    st.info("💡 在对话 Tab 中告诉助手你想学习什么，系统将为你生成以上 5 种资源。")


# --- 学习路径 Tab ---
with tab_path:
    st.markdown("### 🗺️ 你的个性化学习路径")

    if backend_ok:
        try:
            resp = requests.get(f"{BACKEND_URL}/api/path/default", timeout=5)
            if resp.status_code == 200:
                path_data = resp.json()
                st.markdown(f"**课程：{path_data['course']}**")

                for stage in path_data["stages"]:
                    with st.container():
                        progress = "⬜" if stage["order"] > 1 else "🟢"
                        st.markdown(f"""
                        <div class="resource-card">
                            <strong>{progress} 阶段 {stage['order']}：{stage['title']}</strong>
                            <span style="float:right;color:#888;">预计 {stage['estimated_hours']}h</span><br>
                            <small>{' · '.join(stage['topics'])}</small>
                        </div>
                        """, unsafe_allow_html=True)
        except requests.ConnectionError:
            st.warning("⚠️ 后端未连接")
    else:
        st.warning("请启动后端服务查看学习路径。")
