"""Pipeline 自定义异常"""


class PipelineError(Exception):
    """Pipeline 异常基类"""
    pass


class RetryableError(PipelineError):
    """LLM API 临时性错误，可重试"""
    pass


class SkipResumeError(PipelineError):
    """当前简历处理失败，跳过继续处理下一份"""
    pass


class PipelineAbort(PipelineError):
    """严重错误，需要终止整个 Pipeline"""
    pass
