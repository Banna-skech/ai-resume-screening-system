"""批量处理器 —— 多份简历的批量 Pipeline 处理 + 进度回调"""

import logging
from pathlib import Path
from typing import Callable

from models.job_profile import JobProfile
from models.match_result import MatchResult

from pipeline.orchestrator import PipelineOrchestrator
from pipeline.exceptions import SkipResumeError

logger = logging.getLogger(__name__)

# 进度回调类型
ProgressCallback = Callable[[int, int, str, str], None]
# (current_index, total, status, message) -> None


class BatchProcessor:
    """批量简历处理器

    对多份简历文件依次运行 Pipeline，收集结果和错误。
    支持进度回调，与 Streamlit 等 UI 集成。
    """

    def __init__(self, orchestrator: PipelineOrchestrator):
        """
        Args:
            orchestrator: Pipeline 编排器实例
        """
        self.orchestrator = orchestrator

    def process(
        self,
        files: list[Path],
        job_profile: JobProfile,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[list[MatchResult], list[dict]]:
        """批量处理简历文件

        Args:
            files: 简历文件路径列表
            job_profile: 岗位画像
            progress_callback: 进度回调函数

        Returns:
            (成功结果列表, 错误列表) 的元组
            错误列表中每个元素为 {"file": 文件名, "error": 错误信息}
        """
        results: list[MatchResult] = []
        errors: list[dict] = []
        total = len(files)

        for i, file_path in enumerate(files):
            current = i + 1
            file_name = file_path.name
            status = "processing"

            if progress_callback:
                progress_callback(current, total, "processing", f"正在处理: {file_name}")

            try:
                result = self.orchestrator.process_one(file_path, job_profile)
                results.append(result)
                status = "success"

                decision_cn = {"pass": "通过", "review": "待定", "reject": "淘汰"}.get(
                    result.decision, result.decision
                )
                msg = f"✅ {file_name}: {result.candidate_name} — {result.overall_score:.1f}分 ({decision_cn})"

                if progress_callback:
                    progress_callback(current, total, "success", msg)

            except SkipResumeError as e:
                errors.append({"file": file_name, "error": str(e)})
                status = "error"

                msg = f"❌ {file_name}: {e}"
                if progress_callback:
                    progress_callback(current, total, "error", msg)

            except Exception as e:
                errors.append({"file": file_name, "error": f"未知错误: {e}"})
                status = "error"

                msg = f"❌ {file_name}: 未知错误 — {e}"
                if progress_callback:
                    progress_callback(current, total, "error", msg)

        return results, errors
