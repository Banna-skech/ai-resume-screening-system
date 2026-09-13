"""简历上传与批量筛选页面"""

import streamlit as st
from pathlib import Path
from datetime import datetime

from config.settings import settings
from config.constants import SUPPORTED_RESUME_FORMATS, DECISION_PASS, DECISION_REVIEW, DECISION_REJECT

from services.template_manager import TemplateManager
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.batch_processor import BatchProcessor
from ui.theme import page_header, section_label, stepper


@st.cache_data(ttl=10, show_spinner=False)
def _list_templates_cached(template_dir: str) -> list[dict]:
    """缓存模板摘要，避免每次控件交互都扫描磁盘。"""
    return TemplateManager(template_dir).list_all()


@st.cache_resource(show_spinner=False)
def _get_orchestrator_cached(
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    weights: tuple[float, float, float, float],
) -> PipelineOrchestrator:
    """缓存当前配置下的 Agent，避免每次 Streamlit 重跑重复初始化客户端。"""
    from agents.resume_parsing_agent import ResumeParsingAgent
    from agents.tag_matching_agent import TagMatchingAgent

    base_kwargs = {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
    }
    return PipelineOrchestrator(
        resume_agent=ResumeParsingAgent(**base_kwargs),
        match_agent=TagMatchingAgent(**base_kwargs),
        dimension_weights={
            "skills": weights[0],
            "experience": weights[1],
            "background": weights[2],
            "intention": weights[3],
        },
    )


def render():
    """渲染简历上传与筛选页面"""
    page_header("简历筛选", "选择岗位画像、上传候选人简历，并实时查看批量处理进度。")

    if st.session_state.get("screening_running"):
        active_step = 3
    elif st.session_state.get("resume_uploader"):
        active_step = 3
    elif st.session_state.get("active_profile"):
        active_step = 2
    else:
        active_step = 1
    stepper(active_step, ["选择岗位画像", "上传简历文件", "开始筛选"])

    # ========== Step 1: 选择岗位画像 ==========
    section_label("01", "选择岗位画像")

    if "template_manager" not in st.session_state:
        st.session_state.template_manager = TemplateManager()
    tm = st.session_state.template_manager
    templates = _list_templates_cached(str(tm.template_dir))

    if "active_profile" not in st.session_state and templates:
        # 自动加载第一个模板
        try:
            profile = tm.load(templates[0]["id"])
            st.session_state.active_profile = profile
            st.session_state.active_profile_id = profile.id
        except Exception:
            pass

    col1, col2 = st.columns([2, 1])
    with col1:
        if templates:
            tpl_options = {f"{t['job_title']} ({t['id']})": t["id"] for t in templates}
            selected_label = st.selectbox(
                "选择已保存的岗位画像模板",
                options=list(tpl_options.keys()),
                index=None,
                placeholder="选择一个模板...",
                key="select_template",
            )
            if selected_label:
                tpl_id = tpl_options[selected_label]
                if st.session_state.get("active_profile_id") != tpl_id:
                    profile = tm.load(tpl_id)
                    st.session_state.active_profile = profile
                    st.session_state.active_profile_id = tpl_id
        else:
            st.warning("暂无保存的岗位画像模板，请先在「岗位画像」页面创建并保存模板")

    with col2:
        if st.session_state.get("active_profile"):
            profile = st.session_state.active_profile
            st.info(f"**当前画像:** {profile.job_title}\n\n"
                    f"硬性要求: {len(profile.hard_requirements)} 项\n\n"
                    f"核心技能: {len(profile.core_skills)} 项")
        else:
            # 快速输入 JD
            with st.expander("⚡ 快速创建画像"):
                quick_jd = st.text_area("粘贴 JD", height=150, key="quick_jd")
                if st.button("生成并选用", key="quick_gen") and quick_jd:
                    _quick_create_profile(quick_jd)

    st.divider()

    # ========== Step 2: 上传简历 ==========
    section_label("02", "上传简历文件")

    uploaded_files = st.file_uploader(
        f"支持格式: {', '.join(SUPPORTED_RESUME_FORMATS)}",
        type=[fmt.lstrip(".") for fmt in SUPPORTED_RESUME_FORMATS],
        accept_multiple_files=True,
        key="resume_uploader",
    )

    if uploaded_files:
        st.caption(f"已选择 {len(uploaded_files)} 个文件")
        # 显示文件列表
        for f in uploaded_files:
            size_kb = len(f.getvalue()) / 1024
            st.text(f"  📄 {f.name} ({size_kb:.1f} KB)")

    st.divider()

    # ========== Step 3: 开始筛选 ==========
    section_label("03", "开始筛选")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_btn = st.button(
            "🚀 开始 AI 筛选",
            type="primary",
            disabled=(
                not uploaded_files
                or not st.session_state.get("active_profile")
            ),
            use_container_width=True,
        )
    with col2:
        export_after = st.checkbox("完成后自动导出 Excel", value=True)

    if start_btn:
        _run_batch_screening(uploaded_files, export_after)

    # 如果已有结果，显示摘要
    if "last_results" in st.session_state and "last_errors" in st.session_state:
        results = st.session_state.last_results
        errors = st.session_state.last_errors

        st.divider()
        st.subheader("📊 本次筛选结果")

        col1, col2, col3, col4 = st.columns(4)
        pass_count = sum(1 for r in results if r.decision == DECISION_PASS)
        review_count = sum(1 for r in results if r.decision == DECISION_REVIEW)
        reject_count = sum(1 for r in results if r.decision == DECISION_REJECT)

        with col1:
            st.metric("总计", len(results) + len(errors))
        with col2:
            st.metric("✅ 通过", pass_count)
        with col3:
            st.metric("⚠️ 待定", review_count)
        with col4:
            st.metric("❌ 淘汰", reject_count)

        if errors:
            st.warning(f"⚠️ {len(errors)} 个文件处理失败")
            with st.expander("查看错误详情"):
                for err in errors:
                    st.caption(f"❌ {err['file']}: {err['error']}")

        # 跳转到结果页查看详情
        if st.button("📋 查看详细结果", use_container_width=True):
            st.session_state.nav_page = "📊 筛选结果"
            st.rerun()


def _quick_create_profile(jd_text: str):
    """快速创建岗位画像（不使用完整编辑器）"""
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
        )

        with st.spinner("正在分析 JD..."):
            profile = agent.generate(jd_text)

        st.session_state.active_profile = profile
        st.session_state.active_profile_id = profile.id
        st.success(f"✅ 画像已创建: {profile.job_title}")

        # 也保存到模板，并使摘要缓存立即失效
        tm = st.session_state.get("template_manager") or TemplateManager()
        st.session_state.template_manager = tm
        tm.save(profile)
        _list_templates_cached.clear()

    except Exception as e:
        st.error(f"创建失败: {e}")


def _run_batch_screening(uploaded_files, export_after: bool):
    """执行批量筛选"""
    api_key = st.session_state.get("api_key", settings.deepseek_api_key)
    if not api_key:
        st.error("请先在「系统设置」中配置 API Key")
        return

    job_profile = st.session_state.get("active_profile")
    if not job_profile:
        st.error("请先选择岗位画像")
        return

    # 保存上传文件到临时目录
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_paths = []
    for uf in uploaded_files:
        file_path = upload_dir / uf.name
        file_path.write_bytes(uf.getvalue())
        file_paths.append(file_path)

    # 初始化 Agent（按当前配置缓存，避免页面重跑重复创建客户端）
    base_url = st.session_state.get("base_url", settings.deepseek_base_url)
    model = st.session_state.get("model", settings.deepseek_model)
    temperature = float(st.session_state.get("temperature", settings.deepseek_temperature))
    weights = (
        st.session_state.get("w_skills", 35) / 100.0,
        st.session_state.get("w_experience", 30) / 100.0,
        st.session_state.get("w_background", 20) / 100.0,
        st.session_state.get("w_intention", 15) / 100.0,
    )

    try:
        orchestrator = _get_orchestrator_cached(
            api_key, base_url, model, temperature, weights
        )

        batch = BatchProcessor(orchestrator)

        # 进度显示
        st.session_state.screening_running = True
        progress_bar = st.progress(0, text="准备处理...")
        status_area = st.empty()

        def progress_callback(current: int, total: int, status: str, message: str):
            progress_bar.progress(current / total, text=f"{current}/{total}")
            if status == "success":
                status_area.success(message)
            elif status == "error":
                status_area.error(message)
            else:
                status_area.info(message)

        # 执行批量处理
        results, errors = batch.process(file_paths, job_profile, progress_callback)
        st.session_state.screening_running = False

        progress_bar.empty()

        # 存入 session
        st.session_state.last_results = results
        st.session_state.last_errors = errors

        # 更新历史
        if "history" not in st.session_state:
            st.session_state.history = []
        for r in results:
            st.session_state.history.append({
                "decision": r.decision,
                "overall_score": r.overall_score,
                "candidate_name": r.candidate_name,
                "resume_file": r.resume_file,
                "processed_at": datetime.now().isoformat(),
            })

        # 导出 Excel
        if export_after and results:
            _export_excel(results)

        st.rerun()

    except Exception as e:
        st.session_state.screening_running = False
        st.error(f"筛选过程出错: {e}")
        import traceback
        st.code(traceback.format_exc())


def _export_excel(results: list):
    """导出 Excel 报告"""
    try:
        from services.report_generator import ReportGenerator
        rg = ReportGenerator()
        filepath = rg.generate(results)
        st.session_state.last_report_path = str(filepath)

        # 提供下载
        with open(filepath, "rb") as f:
            st.download_button(
                "📥 下载 Excel 报告",
                data=f.read(),
                file_name=filepath.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    except ImportError:
        st.warning("报告生成模块尚未就绪，请在 Phase 5 完成后使用")
    except Exception as e:
        st.warning(f"报告生成失败: {e}")
