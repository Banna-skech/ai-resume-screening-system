"""共享的 Streamlit 视觉主题与轻量 UI 辅助函数。"""

from __future__ import annotations

import streamlit as st


def inject_global_css() -> None:
    """注入全局样式，集中维护颜色、间距和常用组件外观。"""
    st.markdown(
        """
        <style>
        :root {
            --hr-ink: #152238;
            --hr-muted: #64748b;
            --hr-brand: #2563eb;
            --hr-brand-dark: #1d4ed8;
            --hr-soft: #eff6ff;
            --hr-border: #e2e8f0;
            --hr-success: #059669;
            --hr-warning: #d97706;
            --hr-danger: #dc2626;
        }

        .stApp { background: #f8fafc; color: var(--hr-ink); }
        [data-testid="stHeader"] { background: rgba(248, 250, 252, 0.88); }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f1f3d 0%, #162b50 100%);
            border-right: 0;
        }
        [data-testid="stSidebar"] * { color: #e5edf9; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { color: #ffffff; }
        [data-testid="stSidebar"] hr { border-color: rgba(226, 232, 240, 0.18); }
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .hr-brand {
            display: flex; align-items: center; gap: 12px; padding: 6px 0 14px;
        }
        .hr-brand-mark {
            width: 38px; height: 38px; border-radius: 12px; display: grid;
            place-items: center; background: linear-gradient(135deg, #60a5fa, #2563eb);
            color: white; font-size: 20px; box-shadow: 0 8px 22px rgba(37, 99, 235, .28);
        }
        .hr-brand-title { font-size: 16px; font-weight: 700; letter-spacing: .02em; }
        .hr-brand-subtitle { margin-top: 2px; font-size: 11px; opacity: .7; }

        .hr-page-kicker {
            color: var(--hr-brand); font-size: 12px; font-weight: 700;
            letter-spacing: .08em; text-transform: uppercase; margin-bottom: 4px;
        }
        .hr-page-caption { color: var(--hr-muted); margin: -10px 0 20px; font-size: 14px; }
        .hr-section-label {
            display: flex; align-items: center; gap: 8px; margin: 18px 0 10px;
            color: var(--hr-ink); font-size: 16px; font-weight: 700;
        }
        .hr-section-label span {
            display: inline-grid; place-items: center; width: 24px; height: 24px;
            border-radius: 8px; background: var(--hr-soft); color: var(--hr-brand);
            font-size: 12px; font-weight: 800;
        }
        .hr-stepper {
            display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 18px;
        }
        .hr-step {
            display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px;
            border: 1px solid var(--hr-border); border-radius: 999px; background: white;
            color: var(--hr-muted); font-size: 12px; font-weight: 600;
        }
        .hr-step.active { border-color: #bfdbfe; background: var(--hr-soft); color: var(--hr-brand-dark); }
        .hr-step.done { border-color: #a7f3d0; background: #ecfdf5; color: var(--hr-success); }
        .hr-step b { font-size: 11px; }

        [data-testid="stMetric"] {
            border: 1px solid var(--hr-border); border-radius: 14px; padding: 14px 16px;
            background: #ffffff; box-shadow: 0 4px 16px rgba(15, 23, 42, .04);
        }
        [data-testid="stMetricLabel"] { color: var(--hr-muted); }
        [data-testid="stMetricValue"] { color: var(--hr-ink); }
        [data-testid="stButton"] > button {
            border-radius: 10px; font-weight: 650; min-height: 40px;
            transition: transform .12s ease, box-shadow .12s ease;
        }
        [data-testid="stButton"] > button:hover {
            transform: translateY(-1px); box-shadow: 0 6px 16px rgba(15, 23, 42, .10);
        }
        [data-testid="stTabs"] button { font-weight: 650; }
        [data-testid="stExpander"] {
            border-color: var(--hr-border); border-radius: 12px; background: white;
        }
        [data-testid="stFileUploaderDropzone"] {
            border: 1.5px dashed #93c5fd; background: #f8fbff; border-radius: 14px;
        }
        .hr-card {
            border: 1px solid var(--hr-border); border-radius: 14px; padding: 16px;
            background: #fff; box-shadow: 0 4px 16px rgba(15, 23, 42, .04);
        }
        .hr-muted { color: var(--hr-muted); font-size: 13px; }
        .hr-note {
            padding: 10px 12px; border-radius: 10px; background: var(--hr-soft);
            color: #1e40af; font-size: 13px;
        }
        @media (max-width: 768px) {
            .hr-stepper { gap: 6px; }
            .hr-step { width: 100%; justify-content: center; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, caption: str, kicker: str = "HR WORKSPACE") -> None:
    """渲染统一的页面标题区。"""
    st.markdown(f'<div class="hr-page-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="hr-page-caption">{caption}</div>', unsafe_allow_html=True)


def section_label(number: str, title: str) -> None:
    st.markdown(
        f'<div class="hr-section-label"><span>{number}</span>{title}</div>',
        unsafe_allow_html=True,
    )


def stepper(active: int, labels: list[str]) -> None:
    parts = []
    for i, label in enumerate(labels, start=1):
        state = "done" if i < active else "active" if i == active else ""
        parts.append(f'<div class="hr-step {state}"><b>{i:02d}</b>{label}</div>')
    st.markdown(f'<div class="hr-stepper">{"".join(parts)}</div>', unsafe_allow_html=True)
