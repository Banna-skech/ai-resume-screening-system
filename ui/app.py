"""AI 简历筛选系统 —— Streamlit 主入口"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保模块导入正确
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from ui.theme import inject_global_css

# 页面配置
st.set_page_config(
    page_title="AI 简历筛选系统",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ========== 侧边栏导航 ==========
st.sidebar.markdown(
    '<div class="hr-brand"><div class="hr-brand-mark">✓</div>'
    '<div><div class="hr-brand-title">AI 简历筛选</div>'
    '<div class="hr-brand-subtitle">Recruiting workspace</div></div></div>',
    unsafe_allow_html=True,
)

# 导航
st.sidebar.markdown("---")

# 用 session_state 管理当前页面，支持从其他页面跳转
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "🏠 首页"

page = st.sidebar.radio(
    "导航",
    options=["🏠 首页", "📝 岗位画像", "📤 简历筛选", "📊 筛选结果", "⚙️ 系统设置"],
    index=["🏠 首页", "📝 岗位画像", "📤 简历筛选", "📊 筛选结果", "⚙️ 系统设置"].index(st.session_state.nav_page)
    if st.session_state.nav_page in ["🏠 首页", "📝 岗位画像", "📤 简历筛选", "📊 筛选结果", "⚙️ 系统设置"]
    else 0,
    label_visibility="collapsed",
)

# 同步 radio 选择到 session_state
if page != st.session_state.nav_page:
    st.session_state.nav_page = page
    st.rerun()

# API 状态指示器
st.sidebar.markdown("---")
api_key = st.session_state.get("api_key", "")
if api_key:
    st.sidebar.success("🔑 API 已配置")
else:
    st.sidebar.warning("⚠️ 请先配置 API Key")

# 当前画像状态
if st.session_state.get("active_profile"):
    profile = st.session_state.active_profile
    st.sidebar.info(f"📌 当前画像: {profile.job_title}")
elif st.session_state.get("active_profile_id"):
    st.sidebar.info(f"📌 画像 ID: {st.session_state.active_profile_id}")

# ========== 页面路由 ==========
if page == "🏠 首页":
    from ui.views.dashboard import render
    render()

elif page == "📝 岗位画像":
    from ui.views.job_profile import render
    render()

elif page == "📤 简历筛选":
    from ui.views.resume_upload import render
    render()

elif page == "📊 筛选结果":
    from ui.views.results import render
    render()

elif page == "⚙️ 系统设置":
    from ui.views.settings import render
    render()

# ========== 页脚 ==========
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 | Made for HR")
