"""首页仪表盘 —— 统计概览"""

import streamlit as st
import pandas as pd

from config.constants import DECISION_PASS, DECISION_REVIEW, DECISION_REJECT, DECISION_LABELS
from ui.theme import page_header


def render():
    """渲染首页"""
    page_header("AI 简历筛选系统", "把岗位画像、批量筛选和人工复核集中在一个工作台中。")

    # 统计卡片
    history = st.session_state.get("history", [])
    last_results = st.session_state.get("last_results", [])

    total_processed = len(history)
    pass_count = sum(1 for r in history if r.get("decision") == DECISION_PASS)
    review_count = sum(1 for r in history if r.get("decision") == DECISION_REVIEW)
    reject_count = sum(1 for r in history if r.get("decision") == DECISION_REJECT)

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("已处理简历", total_processed)
        with col2:
            pass_rate = f"{pass_count / total_processed * 100:.0f}%" if total_processed > 0 else "—"
            st.metric("通过率", pass_rate)
        with col3:
            st.metric("待审简历", review_count)
        with col4:
            st.metric("已淘汰", reject_count)

    if total_processed == 0:
        st.info("👋 欢迎使用 AI 简历筛选系统！先创建岗位画像，再上传简历开始筛选。")

        st.markdown("""
        ### 🚀 快速开始
        1. **岗位画像** → 粘贴 JD，AI 自动生成结构化岗位画像
        2. **简历筛选** → 上传简历文件，批量运行 AI 筛选
        3. **筛选结果** → 查看评分、标签，导出 Excel 报告
        """)
        return

    # 决策分布饼图
    st.subheader("📊 决策分布")
    if total_processed > 0:
        chart_data = pd.DataFrame({
            "决策": [DECISION_LABELS[d] for d in [DECISION_PASS, DECISION_REVIEW, DECISION_REJECT]],
            "数量": [pass_count, review_count, reject_count],
            "颜色": ["#22c55e", "#f59e0b", "#ef4444"],
        })
        st.bar_chart(chart_data.set_index("决策")["数量"], horizontal=True)

    # 最近活动
    st.subheader("🕐 最近处理")
    if history:
        # 显示最近 20 条
        recent = sorted(history, key=lambda r: r.get("processed_at", ""), reverse=True)[:20]
        for r in recent:
            decision = r.get("decision", DECISION_REVIEW)
            icon = {"pass": "✅", "review": "⚠️", "reject": "❌"}.get(decision, "➖")
            score = r.get("overall_score", 0)
            name = r.get("candidate_name", "未知")
            file_name = r.get("resume_file", "")
            st.caption(f"{icon} {name}（{file_name}）— {score:.1f} 分")
    else:
        st.info("暂无处理记录")

    # 快速操作
    st.subheader("⚡ 快速操作")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 创建新岗位画像", use_container_width=True):
            st.session_state.nav_page = "📝 岗位画像"
            st.rerun()
    with col2:
        if st.button("📤 上传简历筛选", use_container_width=True):
            st.session_state.nav_page = "📤 简历筛选"
            st.rerun()
