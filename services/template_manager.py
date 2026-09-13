"""岗位画像模板管理服务 —— JSON 文件存储的 CRUD 操作"""

import json
import logging
import uuid
from pathlib import Path

from models.job_profile import JobProfile
from config.settings import settings

logger = logging.getLogger(__name__)


class TemplateManager:
    """岗位画像模板的持久化管理

    模板以 JSON 文件形式存储在 data/templates/ 目录下。
    每个模板文件名为 {id}.json。
    """

    def __init__(self, template_dir: str | None = None):
        self.template_dir = Path(template_dir or settings.template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, template_id: str) -> Path:
        """获取模板文件路径"""
        return self.template_dir / f"{template_id}.json"

    def save(self, profile: JobProfile) -> str:
        """保存模板（新建或更新）

        Args:
            profile: 岗位画像

        Returns:
            模板 ID
        """
        if not profile.id:
            profile.id = f"job_{uuid.uuid4().hex[:8]}"

        file_path = self._file_path(profile.id)
        data = profile.model_dump()
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"模板已保存: {profile.id} ({profile.job_title})")
        return profile.id

    def load(self, template_id: str) -> JobProfile:
        """加载模板

        Args:
            template_id: 模板 ID

        Returns:
            JobProfile 实例

        Raises:
            FileNotFoundError: 模板不存在
        """
        file_path = self._file_path(template_id)
        if not file_path.exists():
            raise FileNotFoundError(f"模板不存在: {template_id}")

        data = json.loads(file_path.read_text(encoding="utf-8"))
        return JobProfile(**data)

    def list_all(self) -> list[dict]:
        """列出所有模板的摘要信息

        Returns:
            包含 id, job_title, created_at 的字典列表
        """
        templates = []
        for file_path in sorted(
            self.template_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                templates.append({
                    "id": data.get("id", file_path.stem),
                    "job_title": data.get("job_title", "未知岗位"),
                    "created_at": data.get("created_at", ""),
                    "version": data.get("version", 1),
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"模板文件损坏: {file_path.name} — {e}")
        return templates

    def delete(self, template_id: str) -> bool:
        """删除模板

        Args:
            template_id: 模板 ID

        Returns:
            是否删除成功
        """
        file_path = self._file_path(template_id)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"模板已删除: {template_id}")
            return True
        return False

    def search(self, query: str) -> list[dict]:
        """按岗位名称搜索模板

        Args:
            query: 搜索关键词

        Returns:
            匹配的模板摘要列表
        """
        all_templates = self.list_all()
        query_lower = query.lower()
        return [
            t for t in all_templates
            if query_lower in t["job_title"].lower()
        ]
