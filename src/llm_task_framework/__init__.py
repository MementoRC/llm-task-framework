"""LLM Task Framework.

A generic framework for building LLM-powered task execution systems 
with built-in MCP server interface and pluggable task implementations.
"""

from .core.facade import TaskFramework
from .core.models.config import TaskConfig
from .core.registry import TaskRegistry
from .__version__ import __version__

__all__ = [
    "__version__",
    "TaskFramework", 
    "TaskConfig",
    "TaskRegistry",
]
