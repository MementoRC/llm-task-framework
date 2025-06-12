"""Core framework components."""

from .protocols import (
    TaskAnalyzer,
    TaskApplier,
    TaskExtractor,
    TaskInput,
    TaskResult,
    TaskSuggester,
)

__all__ = [
    "TaskExtractor",
    "TaskAnalyzer",
    "TaskSuggester",
    "TaskApplier",
    "TaskInput",
    "TaskResult",
]
