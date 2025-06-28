"""LLM Task Framework.

A generic framework for building LLM-powered task execution systems
with built-in MCP server interface and pluggable task implementations.
"""

from .__version__ import __version__

# Import core protocols
from .core.protocols import (
    ServiceConnectionError,
    ServiceContainer,
    ServiceContainerError,
    ServiceNotAvailableError,
)

# Import service containers and utilities
from .services import (
    RedisServiceContainer,
    ServiceRegistry,
    get_service_registry,
    get_services_config,
)

__all__ = [
    "__version__",
    # Core protocols
    "ServiceContainer",
    "ServiceContainerError",
    "ServiceConnectionError",
    "ServiceNotAvailableError",
    # Service containers
    "RedisServiceContainer",
    "ServiceRegistry",
    "get_service_registry",
    "get_services_config",
]
