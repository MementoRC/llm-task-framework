"""Service registry for managing service containers.

Provides centralized service discovery, lifecycle management, and health monitoring
for all service containers in the application.
"""

import asyncio
import logging
from typing import Any

from ..core.protocols import ServiceContainer, ServiceContainerError

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Central registry for managing service containers.

    Provides service discovery, lifecycle management, health monitoring,
    and graceful degradation for all registered service containers.
    """

    def __init__(self) -> None:
        """Initialize the service registry."""
        self._services: dict[str, ServiceContainer] = {}
        self._service_configs: dict[str, dict[str, Any]] = {}
        self._health_status: dict[str, dict[str, Any]] = {}
        self._startup_order: list[str] = []

    def register(
        self,
        service_name: str,
        container: ServiceContainer,
        config: dict[str, Any] | None = None,
        startup_priority: int = 0,
    ) -> None:
        """
        Register a service container.

        Args:
            service_name: Unique name for the service
            container: Service container instance
            config: Optional configuration for the service
            startup_priority: Priority for startup order (lower = higher priority)
        """
        if service_name in self._services:
            logger.warning(f"Service '{service_name}' is already registered, replacing")

        self._services[service_name] = container
        service_config = config or {}
        service_config["startup_priority"] = startup_priority
        self._service_configs[service_name] = service_config

        # Insert into startup order based on priority
        self._startup_order = [s for s in self._startup_order if s != service_name]
        inserted = False
        for i, existing_service in enumerate(self._startup_order):
            existing_priority = self._service_configs[existing_service].get(
                "startup_priority", 0
            )
            if startup_priority < existing_priority:
                self._startup_order.insert(i, service_name)
                inserted = True
                break

        if not inserted:
            self._startup_order.append(service_name)

        logger.info(
            f"Registered service '{service_name}' with priority {startup_priority}"
        )

    def unregister(self, service_name: str) -> None:
        """
        Unregister a service container.

        Args:
            service_name: Name of the service to unregister
        """
        if service_name in self._services:
            del self._services[service_name]
            del self._service_configs[service_name]
            self._health_status.pop(service_name, None)

            if service_name in self._startup_order:
                self._startup_order.remove(service_name)

            logger.info(f"Unregistered service '{service_name}'")
        else:
            logger.warning(f"Attempted to unregister unknown service '{service_name}'")

    def get_service(self, service_name: str) -> ServiceContainer:
        """
        Get a registered service container.

        Args:
            service_name: Name of the service

        Returns:
            Service container instance

        Raises:
            ServiceContainerError: If service is not registered
        """
        if service_name not in self._services:
            raise ServiceContainerError(f"Service '{service_name}' is not registered")

        return self._services[service_name]

    def list_services(self) -> list[str]:
        """
        Get list of all registered service names.

        Returns:
            List of service names
        """
        return list(self._services.keys())

    def is_registered(self, service_name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            service_name: Name of the service

        Returns:
            True if service is registered, False otherwise
        """
        return service_name in self._services

    async def start_all(self, fail_fast: bool = False) -> dict[str, bool]:
        """
        Start all registered services in priority order.

        Args:
            fail_fast: If True, stop on first failure; if False, continue with other services

        Returns:
            Dictionary mapping service names to success status
        """
        results = {}

        for service_name in self._startup_order:
            try:
                container = self._services[service_name]
                await container.connect()
                results[service_name] = True
                logger.info(f"Successfully started service '{service_name}'")
            except Exception as e:
                results[service_name] = False
                logger.error(f"Failed to start service '{service_name}': {e}")

                if fail_fast:
                    logger.error("Fail-fast mode enabled, stopping startup process")
                    break

        return results

    async def stop_all(self) -> dict[str, bool]:
        """
        Stop all registered services in reverse priority order.

        Returns:
            Dictionary mapping service names to success status
        """
        results = {}

        # Stop in reverse order
        for service_name in reversed(self._startup_order):
            try:
                container = self._services[service_name]
                await container.disconnect()
                results[service_name] = True
                logger.info(f"Successfully stopped service '{service_name}'")
            except Exception as e:
                results[service_name] = False
                logger.error(f"Failed to stop service '{service_name}': {e}")

        return results

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """
        Perform health check on all registered services.

        Returns:
            Dictionary mapping service names to health status information
        """
        results = {}

        for service_name, container in self._services.items():
            try:
                health_info = await container.health_check()
                results[service_name] = health_info
                self._health_status[service_name] = health_info
            except Exception as e:
                error_info = {
                    "service": service_name,
                    "status": "error",
                    "error": str(e),
                }
                results[service_name] = error_info
                self._health_status[service_name] = error_info
                logger.error(f"Health check failed for service '{service_name}': {e}")

        return results

    def get_healthy_services(self) -> list[str]:
        """
        Get list of currently healthy services.

        Returns:
            List of service names that are healthy
        """
        healthy = []

        for service_name, container in self._services.items():
            if container.is_healthy:
                healthy.append(service_name)

        return healthy

    def get_unhealthy_services(self) -> list[str]:
        """
        Get list of currently unhealthy services.

        Returns:
            List of service names that are unhealthy
        """
        unhealthy = []

        for service_name, container in self._services.items():
            if not container.is_healthy:
                unhealthy.append(service_name)

        return unhealthy

    async def restart_service(self, service_name: str) -> bool:
        """
        Restart a specific service.

        Args:
            service_name: Name of the service to restart

        Returns:
            True if restart was successful, False otherwise
        """
        if service_name not in self._services:
            logger.error(f"Cannot restart unknown service '{service_name}'")
            return False

        container = self._services[service_name]

        try:
            # Stop the service
            await container.disconnect()
            logger.info(f"Stopped service '{service_name}' for restart")

            # Wait a moment before restarting
            await asyncio.sleep(0.5)

            # Start the service
            await container.connect()
            logger.info(f"Successfully restarted service '{service_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to restart service '{service_name}': {e}")
            return False

    def get_service_config(self, service_name: str) -> dict[str, Any]:
        """
        Get configuration for a service.

        Args:
            service_name: Name of the service

        Returns:
            Service configuration dictionary

        Raises:
            ServiceContainerError: If service is not registered
        """
        if service_name not in self._service_configs:
            raise ServiceContainerError(f"Service '{service_name}' is not registered")

        return self._service_configs[service_name].copy()

    def update_service_config(self, service_name: str, config: dict[str, Any]) -> None:
        """
        Update configuration for a service.

        Args:
            service_name: Name of the service
            config: New configuration dictionary

        Raises:
            ServiceContainerError: If service is not registered
        """
        if service_name not in self._service_configs:
            raise ServiceContainerError(f"Service '{service_name}' is not registered")

        self._service_configs[service_name].update(config)
        logger.info(f"Updated configuration for service '{service_name}'")

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of all services and their status.

        Returns:
            Dictionary containing service registry summary
        """
        healthy_services = self.get_healthy_services()
        unhealthy_services = self.get_unhealthy_services()

        return {
            "total_services": len(self._services),
            "healthy_services": len(healthy_services),
            "unhealthy_services": len(unhealthy_services),
            "services": {
                "healthy": healthy_services,
                "unhealthy": unhealthy_services,
            },
            "startup_order": self._startup_order.copy(),
        }

    async def __aenter__(self) -> "ServiceRegistry":
        """Async context manager entry."""
        await self.start_all()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop_all()

    def __str__(self) -> str:
        """String representation of the service registry."""
        healthy = len(self.get_healthy_services())
        total = len(self._services)
        return f"ServiceRegistry({healthy}/{total} healthy services)"

    def __repr__(self) -> str:
        """Detailed representation of the service registry."""
        return (
            f"ServiceRegistry("
            f"services={list(self._services.keys())}, "
            f"healthy={self.get_healthy_services()})"
        )


# Global service registry instance
_global_registry: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """
    Get the global service registry instance.

    Returns:
        Global ServiceRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
    return _global_registry


def reset_service_registry() -> None:
    """
    Reset the global service registry.

    Useful for testing to ensure clean state.
    """
    global _global_registry
    _global_registry = None
