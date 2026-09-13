"""系统设置页面 —— API 配置、评分阈值、维度权重"""

import streamlit as st

from config.settings import settings
from ui.theme import page_header


def render():
    """渲染系统设置页面"""
    page_header("系统设置", "管理 API、评分阈值和权重；保存后才会应用到后续筛选任务。")

    # ========== API 配置 ==========
    st.header("🔑 DeepSeek API 配置")
    with st.expander("API 设置", expanded=True):
        api_key = st.text_input(
            "API Key",
            value=st.session_state.get("api_key", settings.deepseek_api_key),
            type="password",
            help="DeepSeek API Key，从 https://platform.deepseek.com 获取",
            key="settings_api_key",
        )
        base_url = st.text_input(
            "Base URL",
            value=st.session_state.get("base_url", settings.deepseek_base_url),
            help="API 端点地址",
            key="settings_base_url",
        )
        model = st.text_input(
            "模型名称",
            value=st.session_state.get("model", settings.deepseek_model),
            help="推荐 deepseek-chat",
            key="settings_model",
        )
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=0.5,
            value=float(st.session_state.get("temperature", settings.deepseek_temperature)),
            step=0.05,
            help="越低越稳定，越高越有创意。简历解析建议 0.0~0.1",
            key="settings_temperature",
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🧪 测试连接", key="test_api"):
                _test_connection(api_key, base_url, model)
        with col2:
            if st.button("💾 保存 API 配置到 Session", key="save_api"):
                _save_api_config(api_key, base_url, model, temperature)
                st.success("API 配置已保存到当前会话")

    # ========== 评分阈值 ==========
    st.header("📊 评分阈值")
    with st.expander("阈值设置", expanded=False):
        pass_threshold = st.slider(
            "通过阈值 (≥此分进入面试池)",
            min_value=0,
            max_value=100,
            value=int(st.session_state.get("pass_threshold", settings.pass_threshold)),
            step=5,
            key="settings_pass_threshold",
        )
        review_threshold = st.slider(
            "待定阈值 (≥此分进入人工复核，低于此分淘汰)",
            min_value=0,
            max_value=100,
            value=int(st.session_state.get("review_threshold", settings.review_threshold)),
            step=5,
            key="settings_review_threshold",
        )
        hard_penalty = st.slider(
            "硬性要求扣分 (每项不满足扣分)",
            min_value=0,
            max_value=30,
            value=int(st.session_state.get("hard_penalty", settings.hard_requirement_penalty)),
            step=5,
            key="settings_hard_penalty",
        )

        if review_threshold >= pass_threshold:
            st.warning("待定阈值应低于通过阈值！")

        if st.button("💾 保存阈值到 Session", key="save_thresholds"):
            st.session_state.pass_threshold = float(pass_threshold)
            st.session_state.review_threshold = float(review_threshold)
            st.session_state.hard_penalty = float(hard_penalty)
            st.success("阈值已保存")

    # ========== 维度权重 ==========
    st.header("⚖️ 评分维度权重")
    with st.expander("权重设置", expanded=False):
        st.caption("四个维度的权重之和应等于 100%")

        col1, col2 = st.columns(2)
        with col1:
            w_skills = st.slider(
                "技能匹配",
                min_value=0,
                max_value=100,
                value=int(st.session_state.get("w_skills", settings.weight_skills * 100)),
                step=5,
                format="%d%%",
                key="settings_w_skills",
            )
            w_experience = st.slider(
                "经验匹配",
                min_value=0,
                max_value=100,
                value=int(st.session_state.get("w_experience", settings.weight_experience * 100)),
                step=5,
                format="%d%%",
                key="settings_w_experience",
            )
        with col2:
            w_background = st.slider(
                "背景匹配",
                min_value=0,
                max_value=100,
                value=int(st.session_state.get("w_background", settings.weight_background * 100)),
                step=5,
                format="%d%%",
                key="settings_w_background",
            )
            w_intention = st.slider(
                "意向匹配",
                min_value=0,
                max_value=100,
                value=int(st.session_state.get("w_intention", settings.weight_intention * 100)),
                step=5,
                format="%d%%",
                key="settings_w_intention",
            )

        total = w_skills + w_experience + w_background + w_intention
        if total != 100:
            st.warning(f"⚠️ 权重之和为 {total}%，建议调整为 100%")

        if st.button("💾 保存权重到 Session", key="save_weights"):
            st.session_state.w_skills = w_skills
            st.session_state.w_experience = w_experience
            st.session_state.w_background = w_background
            st.session_state.w_intention = w_intention
            st.success("权重已保存")

    # ========== 数据管理 ==========
    st.header("🗂️ 数据管理")
    with st.expander("数据操作", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 清空当前会话数据", key="clear_session"):
                keys_to_clear = ["last_results", "history", "feedback", "current_profile"]
                for k in keys_to_clear:
                    if k in st.session_state:
                        del st.session_state[k]
                st.success("会话数据已清空")
        with col2:
            st.caption(f"模板目录: `{settings.template_dir}`")
            st.caption(f"报告目录: `{settings.report_dir}`")


def _save_api_config(api_key: str, base_url: str, model: str, temperature: float):
    """保存 API 配置到 session_state"""
    st.session_state.api_key = api_key
    st.session_state.base_url = base_url
    st.session_state.model = model
    st.session_state.temperature = temperature


def _test_connection(api_key: str, base_url: str, model: str):
    """测试 DeepSeek API 连接"""
    if not api_key:
        st.error("请先填写 API Key")
        return

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        with st.spinner("正在测试连接..."):
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )
        st.success(f"✅ 连接成功！模型: {model}")
    except Exception as e:
        st.error(f"❌ 连接失败: {e}")
