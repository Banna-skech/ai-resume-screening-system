"""岗位画像管理页面 —— 创建、编辑、保存、加载岗位画像模板"""

import streamlit as st

from models.job_profile import JobProfile
from services.template_manager import TemplateManager
from config.settings import settings
from ui.theme import page_header, section_label


@st.cache_data(ttl=10, show_spinner=False)
def _list_templates_cached(template_dir: str) -> list[dict]:
    """缓存模板摘要，避免模板管理页每次交互都扫描磁盘。"""
    return TemplateManager(template_dir).list_all()


def render():
    """渲染岗位画像页面"""
    page_header("岗位画像管理", "将 JD 转成可复用的结构化筛选标准，生成后可人工校准。")

    # 初始化 template manager
    if "template_manager" not in st.session_state:
        st.session_state.template_manager = TemplateManager()

    tm = st.session_state.template_manager

    tab1, tab2 = st.tabs(["✨ 创建岗位画像", "📂 模板管理"])

    # ========== Tab 1: 创建岗位画像 ==========
    with tab1:
        section_label("01", "创建岗位画像")

        jd_text = st.text_area(
            "将岗位描述的完整文本粘贴到此处",
            height=300,
            placeholder="例如：\n\n岗位名称：高级 Python 开发工程师\n\n岗位职责：\n1. 负责后端服务架构设计与开发\n2. ...\n\n任职要求：\n1. 本科及以上学历，计算机相关专业\n2. 5年以上 Python 开发经验\n3. 熟悉 Django/FastAPI 等主流框架\n...",
            key="jd_input",
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            generate_btn = st.button(
                "🤖 生成岗位画像",
                type="primary",
                disabled=not jd_text or len(jd_text) < 50,
                use_container_width=True,
            )
        with col2:
            if len(jd_text) < 50 and jd_text:
                st.caption(f"当前已输入 {len(jd_text)} 字，建议至少 50 字以获得更准确的画像")

        if generate_btn:
            _generate_profile(jd_text)

        # 如果 session 中有当前画像，显示可编辑表单
        if "current_profile" in st.session_state:
            st.divider()
            section_label("02", "确认并编辑画像")
            _render_profile_editor(st.session_state.current_profile)

    # ========== Tab 2: 模板管理 ==========
    with tab2:
        st.subheader("已保存的岗位模板")
        templates = _list_templates_cached(str(tm.template_dir))

        if not templates:
            st.info("暂无保存的模板，请先在「创建岗位画像」中生成并保存")
            return

        search_query = st.text_input("🔍 搜索模板", key="tpl_search")
        if search_query:
            templates = tm.search(search_query)
            st.caption(f"找到 {len(templates)} 个匹配模板")

        for tpl in templates:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{tpl['job_title']}**")
                st.caption(f"ID: {tpl['id']} | 创建: {tpl['created_at'][:10]}")
            with col2:
                if st.button("📋 加载", key=f"load_{tpl['id']}"):
                    profile = tm.load(tpl["id"])
                    st.session_state.current_profile = profile
                    st.success(f"已加载: {profile.job_title}")
                    st.rerun()
            with col3:
                if st.button("🗑️ 删除", key=f"del_{tpl['id']}"):
                    tm.delete(tpl["id"])
                    st.cache_data.clear()
                    st.success(f"已删除: {tpl['job_title']}")
                    st.rerun()
            with col4:
                # 设为当前筛选使用的画像
                if st.button("✅ 选用", key=f"use_{tpl['id']}"):
                    profile = tm.load(tpl["id"])
                    st.session_state.active_profile_id = profile.id
                    st.session_state.active_profile = profile
                    st.success(f"已设为当前筛选画像: {profile.job_title}")


def _generate_profile(jd_text: str):
    """调用 Agent 生成岗位画像"""
    # 获取 API key
    api_key = st.session_state.get("api_key", settings.deepseek_api_key)
    if not api_key:
        st.error("请先在「系统设置」中配置 API Key")
        return

    try:
        from agents.job_profile_agent import JobProfileAgent

        agent = JobProfileAgent(
            api_key=api_key,
            base_url=st.session_state.get("base_url", settings.deepseek_base_url),
            model=st.session_state.get("model", settings.deepseek_model),
            temperature=float(st.session_state.get("temperature", settings.deepseek_temperature)),
        )

        with st.spinner("正在分析岗位描述，生成结构化画像..."):
            profile = agent.generate(jd_text)

        st.session_state.current_profile = profile
        st.success(f"✅ 岗位画像生成完成: {profile.job_title}")

    except Exception as e:
        st.error(f"生成失败: {e}")


def _render_profile_editor(profile: JobProfile):
    """渲染岗位画像的可编辑表单"""
    pid = profile.id  # 用画像 ID 作为 key 前缀，确保切换画像时重建所有 widget

    # 岗位名称
    profile.job_title = st.text_input("岗位名称", value=profile.job_title, key=f"edit_title_{pid}")

    # 硬性要求
    with st.expander(f"🔴 硬性要求 ({len(profile.hard_requirements)} 项)", expanded=True):
        for i, hr in enumerate(profile.hard_requirements):
            col1, col2, col3, col4 = st.columns([2, 4, 1, 1])
            with col1:
                cat_options = ["education", "years_of_experience", "certification", "other"]
                cat_idx = cat_options.index(hr.category) if hr.category in cat_options else 3
                hr.category = st.selectbox(
                    "类别",
                    cat_options,
                    index=cat_idx,
                    key=f"hr_cat_{pid}_{i}",
                    label_visibility="collapsed",
                )
            with col2:
                hr.requirement = st.text_input("要求", value=hr.requirement, key=f"hr_req_{pid}_{i}", label_visibility="collapsed")
            with col3:
                hr.is_mandatory = st.checkbox("必须", value=hr.is_mandatory, key=f"hr_mand_{pid}_{i}")
            with col4:
                if st.button("✕", key=f"hr_del_{pid}_{i}"):
                    profile.hard_requirements.pop(i)
                    st.rerun()

        if st.button("+ 添加硬性要求", key=f"add_hr_{pid}"):
            from models.job_profile import HardRequirement
            profile.hard_requirements.append(HardRequirement(category="other", requirement="", is_mandatory=False))
            st.rerun()

    # 核心技能
    with st.expander(f"🟡 核心技能 ({len(profile.core_skills)} 项)", expanded=True):
        for i, sk in enumerate(profile.core_skills):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                sk.name = st.text_input("技能", value=sk.name, key=f"sk_name_{pid}_{i}", label_visibility="collapsed")
            with col2:
                prof_options = ["了解", "熟悉", "掌握", "精通"]
                prof_idx = prof_options.index(sk.proficiency) if sk.proficiency in prof_options else 1
                sk.proficiency = st.selectbox(
                    "熟练度",
                    prof_options,
                    index=prof_idx,
                    key=f"sk_prof_{pid}_{i}",
                    label_visibility="collapsed",
                )
            with col3:
                sk.weight = st.number_input("权重", value=float(sk.weight), min_value=1.0, max_value=3.0, step=0.5, key=f"sk_w_{pid}_{i}", label_visibility="collapsed")
            with col4:
                if st.button("✕", key=f"sk_del_{pid}_{i}"):
                    profile.core_skills.pop(i)
                    st.rerun()

        if st.button("+ 添加核心技能", key=f"add_skill_{pid}"):
            from models.job_profile import CoreSkill
            profile.core_skills.append(CoreSkill(name="", proficiency="熟悉", weight=1.0))
            st.rerun()

    # 项目经验要求
    with st.expander(f"🟢 项目经验要求 ({len(profile.project_experience)} 项)", expanded=False):
        for i, pe in enumerate(profile.project_experience):
            pe.domain = st.text_input("领域", value=pe.domain, key=f"pe_domain_{pid}_{i}")
            pe.description = st.text_area("描述", value=pe.description, key=f"pe_desc_{pid}_{i}", height=80)
            skills_str = st.text_input("所需技能（逗号分隔）", value=", ".join(pe.required_skills), key=f"pe_skills_{pid}_{i}")
            pe.required_skills = [s.strip() for s in skills_str.split(",") if s.strip()]
            if st.button("删除此项目经验", key=f"pe_del_{pid}_{i}"):
                profile.project_experience.pop(i)
                st.rerun()

        if st.button("+ 添加项目经验", key=f"add_pe_{pid}"):
            from models.job_profile import ProjectExperience
            profile.project_experience.append(ProjectExperience(domain="", description="", required_skills=[]))
            st.rerun()

    # 行业背景
    with st.expander("🏭 行业背景", expanded=False):
        if profile.industry_background is None:
            from models.job_profile import IndustryBackground
            profile.industry_background = IndustryBackground(industry="", preferred_subfields=[], importance="nice_to_have")

        ib = profile.industry_background
        ib.industry = st.text_input("行业", value=ib.industry, key=f"ib_industry_{pid}")
        subfields_str = st.text_input("细分领域（逗号分隔）", value=", ".join(ib.preferred_subfields), key=f"ib_subfields_{pid}")
        ib.preferred_subfields = [s.strip() for s in subfields_str.split(",") if s.strip()]
        imp_options = ["required", "preferred", "nice_to_have"]
        imp_idx = imp_options.index(ib.importance) if ib.importance in imp_options else 1
        ib.importance = st.selectbox(
            "重要程度",
            imp_options,
            index=imp_idx,
            key=f"ib_importance_{pid}",
        )

    # 保存按钮
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("💾 保存模板", type="primary", use_container_width=True, key=f"save_{pid}"):
            profile.version += 1
            tid = st.session_state.template_manager.save(profile)
            st.cache_data.clear()
            st.session_state.active_profile_id = tid
            st.session_state.active_profile = profile
            st.success(f"模板已保存: {profile.job_title} (ID: {tid})")
    with col2:
        st.caption("保存后可在「简历筛选」页面中选用此模板进行批量筛选")
