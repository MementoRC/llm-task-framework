"""Core framework components."""

from .protocols import (
    TaskExtractor,
    TaskAnalyzer,
    TaskSuggester,
    TaskApplier,
    TaskInput,
    TaskResult,
)
from .models.config import TaskConfig
from .facade import TaskFramework
from .registry import TaskRegistry

__all__ = [
    "TaskExtractor",
    "TaskAnalyzer",
    "TaskSuggester",
    "TaskApplier",
    "TaskInput",
    "TaskResult",
    "TaskConfig",
    "TaskFramework",
    "TaskRegistry",
]
