"""候选人详情面板组件 —— 展开显示单个候选人的完整评估信息"""

import streamlit as st
import pandas as pd

from models.match_result import MatchResult
from ui.components.score_card import render_score_gauge, render_dimension_bars


def render_candidate_detail(result: MatchResult, key_prefix: str = ""):
    """渲染候选人详情面板

    Args:
        result: 匹配结果
        key_prefix: 组件 key 前缀（避免 Streamlit 重复 key 冲突）
    """
    with st.expander(f"{result.candidate_name} — {result.overall_score:.1f} 分", expanded=False):
        col1, col2 = st.columns([1, 2])

        with col1:
            # 基本信息
            st.markdown("#### 基本信息")
            st.write(f"**文件:** {result.resume_file}")
            st.write(f"**岗位画像ID:** {result.job_profile_id}")

            # 分数仪表盘
            st.markdown("#### 综合评分")
            render_score_gauge(result.overall_score, size="normal")

        with col2:
            # 四维度评分
            st.markdown("#### 维度评分")
            if result.dimension_scores:
                render_dimension_bars(result.dimension_scores, show_details=True)
            else:
                st.info("暂无维度评分详情")

        # 标签
        st.markdown("#### 标签")
        if result.tags:
            cols = st.columns(4)
            for i, tag in enumerate(result.tags):
                col_idx = i % 4
                with cols[col_idx]:
                    color = "green" if tag.match else "red"
                    st.markdown(
                        f":{color}[{'✅' if tag.match else '❌'} {tag.tag}]"
                        f" *{tag.category}*",
                    )
                    if tag.detail:
                        st.caption(tag.detail)
        else:
            st.info("暂无标签")

        # LLM 评语
        if result.llm_explanation:
            st.markdown("#### HR 评语")
            st.info(result.llm_explanation)

        # 决策说明
        if result.decision_reason:
            st.caption(f"决策说明: {result.decision_reason}")

        # 原始 JSON（审计用）
        if result.raw_response:
            with st.expander("原始数据 (JSON)", expanded=False):
                st.code(result.raw_response, language="json")
