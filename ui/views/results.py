"""筛选结果页面 —— 查看、过滤、排序、反馈、导出"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path

from config.constants import (
    DECISION_PASS, DECISION_REVIEW, DECISION_REJECT, DECISION_LABELS,
    DIMENSION_LABELS,
)
from models.match_result import MatchResult
from ui.components.candidate_detail import render_candidate_detail
from ui.theme import page_header, section_label


def render():
    """渲染筛选结果页面"""
    page_header("筛选结果", "按决策、分数和姓名快速定位候选人，并保留人工复核依据。")

    results: list[MatchResult] = st.session_state.get("last_results", [])

    if not results:
        st.info("暂无筛选结果，请先在「简历筛选」页面运行批量筛选")
        return

    # ========== 过滤栏 ==========
    section_label("01", "过滤与排序")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            decision_filter = st.multiselect(
                "决策",
                options=[DECISION_PASS, DECISION_REVIEW, DECISION_REJECT],
                default=[DECISION_PASS, DECISION_REVIEW, DECISION_REJECT],
                format_func=lambda d: DECISION_LABELS.get(d, d),
                key="filter_decision",
            )
        with col2:
            min_score = st.slider(
                "最低分数",
                min_value=0,
                max_value=100,
                value=0,
                step=5,
                key="filter_score",
            )
        with col3:
            sort_by = st.selectbox(
                "排序方式",
                options=["分数降序", "分数升序", "姓名"],
                key="sort_by",
            )
        with col4:
            search_name = st.text_input("搜索姓名", key="search_name")

    # 应用过滤
    filtered = [
        r for r in results
        if r.decision in decision_filter
        and r.overall_score >= min_score
        and (not search_name or search_name.lower() in r.candidate_name.lower())
    ]

    # 排序
    if sort_by == "分数降序":
        filtered.sort(key=lambda r: r.overall_score, reverse=True)
    elif sort_by == "分数升序":
        filtered.sort(key=lambda r: r.overall_score)
    elif sort_by == "姓名":
        filtered.sort(key=lambda r: r.candidate_name)

    st.caption(f"显示 {len(filtered)} / {len(results)} 条结果")

    st.divider()

    # ========== 统计栏 ==========
    pass_count = sum(1 for r in filtered if r.decision == DECISION_PASS)
    review_count = sum(1 for r in filtered if r.decision == DECISION_REVIEW)
    reject_count = sum(1 for r in filtered if r.decision == DECISION_REJECT)

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ 通过", pass_count)
        with col2:
            st.metric("⚠️ 待定", review_count)
        with col3:
            st.metric("❌ 淘汰", reject_count)

    st.divider()

    # ========== 候选人列表 ==========
    for i, result in enumerate(filtered):
        icon = {"pass": "✅", "review": "⚠️", "reject": "❌"}.get(result.decision, "➖")

        with st.container(border=True):
            # 简要信息行
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            with col1:
                st.write(f"{icon} **{result.candidate_name}**")
                st.caption(result.resume_file)
            with col2:
                st.metric("综合", f"{result.overall_score:.0f}", label_visibility="collapsed")
            with col3:
                skills_score = _get_dimension_score(result, "skills")
                st.metric("技能", f"{skills_score:.0f}" if skills_score is not None else "-", label_visibility="collapsed")
            with col4:
                exp_score = _get_dimension_score(result, "experience")
                st.metric("经验", f"{exp_score:.0f}" if exp_score is not None else "-", label_visibility="collapsed")
            with col5:
                tag_texts = [t.tag for t in result.tags[:3]]
                st.caption(", ".join(tag_texts) if tag_texts else "无标签")

            render_candidate_detail(result, key_prefix=f"res_{i}")

            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button("👍 实际合格", key=f"fb_good_{i}"):
                    _save_feedback(result, "false_negative")
                    st.toast("已记录人工反馈")
            with col2:
                if st.button("👎 实际不合格", key=f"fb_bad_{i}"):
                    _save_feedback(result, "false_positive")
                    st.toast("已记录人工反馈")

    st.divider()

    # ========== 导出 ==========
    st.subheader("📥 导出")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 导出 Excel 报告", use_container_width=True, type="primary"):
            _export_excel(filtered)
    with col2:
        if st.button("📄 导出 JSON 数据", use_container_width=True):
            _export_json(filtered)

    # 反馈统计
    if "feedback" in st.session_state and st.session_state.feedback:
        st.divider()
        st.subheader("📈 反馈统计")
        feedback = st.session_state.feedback
        fn_count = sum(1 for f in feedback if f.get("type") == "false_negative")
        fp_count = sum(1 for f in feedback if f.get("type") == "false_positive")
        st.caption(f"误判为不合格 (假阴性): {fn_count} | 误判为合格 (假阳性): {fp_count}")


def _get_dimension_score(result: MatchResult, dimension: str) -> float | None:
    """获取指定维度的分数"""
    for ds in result.dimension_scores:
        if ds.dimension == dimension:
            return ds.score
    return None


def _save_feedback(result: MatchResult, feedback_type: str):
    """保存人工反馈"""
    if "feedback" not in st.session_state:
        st.session_state.feedback = []

    st.session_state.feedback.append({
        "candidate_name": result.candidate_name,
        "resume_file": result.resume_file,
        "overall_score": result.overall_score,
        "decision": result.decision,
        "type": feedback_type,
    })

    # 持久化到文件
    try:
        feedback_file = Path("data/feedback.json")
        feedback_file.parent.mkdir(parents=True, exist_ok=True)
        feedback_file.write_text(
            json.dumps(st.session_state.feedback, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _export_excel(results: list[MatchResult]):
    """导出 Excel 报告"""
    try:
        from services.report_generator import ReportGenerator
        rg = ReportGenerator()
        filepath = rg.generate(results)
        with open(filepath, "rb") as f:
            st.download_button(
                "📥 点击下载 Excel 报告",
                data=f.read(),
                file_name=filepath.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.success(f"报告已生成: {filepath.name}")
    except Exception as e:
        st.error(f"导出失败: {e}")


def _export_json(results: list[MatchResult]):
    """导出 JSON 数据"""
    data = [r.model_dump() for r in results]
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button(
        "📥 点击下载 JSON 数据",
        data=json_str,
        file_name="筛选结果.json",
        mime="application/json",
    )
