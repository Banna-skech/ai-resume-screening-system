"""分数仪表盘组件 —— 可视化展示匹配分数"""

import streamlit as st
from config.constants import DECISION_PASS, DECISION_REVIEW, DECISION_REJECT, DECISION_LABELS


def render_score_gauge(score: float, threshold_pass: float = 70.0,
                       threshold_review: float = 50.0, size: str = "normal"):
    """渲染分数仪表盘

    Args:
        score: 分数 (0-100)
        threshold_pass: 通过阈值
        threshold_review: 待定阈值
        size: "normal" | "compact"
    """
    # 根据分数决定颜色
    if score >= threshold_pass:
        color = "#22c55e"  # 绿色
        decision = DECISION_PASS
    elif score >= threshold_review:
        color = "#f59e0b"  # 黄色
        decision = DECISION_REVIEW
    else:
        color = "#ef4444"  # 红色
        decision = DECISION_REJECT

    label = DECISION_LABELS.get(decision, decision)

    if size == "compact":
        st.metric("综合评分", f"{score:.1f}", delta=label, delta_color="off")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            # 使用 st.progress 模拟仪表盘
            st.progress(score / 100.0, text=f"{score:.1f} 分")
        with col2:
            st.markdown(
                f"<h2 style='color:{color};margin:0;text-align:center;'>{label}</h2>",
                unsafe_allow_html=True,
            )


def render_dimension_bars(dimension_scores: list, show_details: bool = False):
    """渲染四维度分数条

    Args:
        dimension_scores: DimensionScore 列表
        show_details: 是否展开评分明细
    """
    from config.constants import DIMENSION_LABELS

    for ds in dimension_scores:
        dim_label = DIMENSION_LABELS.get(ds.dimension, ds.dimension)
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            st.caption(dim_label)
        with col2:
            st.progress(ds.score / 100.0, text=f"{ds.score:.0f}")
        with col3:
            st.caption(f"权重 {ds.weight:.0%}")

        if show_details and ds.details:
            for detail in ds.details:
                icon = {"positive": "✅", "negative": "❌", "neutral": "➖"}.get(detail.impact, "➖")
                st.caption(f"  {icon} {detail.reason}")
