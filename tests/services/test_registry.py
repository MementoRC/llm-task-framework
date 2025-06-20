"""Tests for service registry implementation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_task_framework.core.protocols import ServiceContainerError
from llm_task_framework.services.registry import ServiceRegistry


class MockServiceContainer:
    """Mock service container for testing."""

    def __init__(self, name: str, healthy: bool = True, connect_succeeds: bool = True):
        self.name = name
        self._healthy = healthy
        self._connect_succeeds = connect_succeeds
        self._connected = False

    @property
    def service_name(self) -> str:
        return self.name

    @property
    def is_healthy(self) -> bool:
        return self._healthy and self._connected

    async def connect(self) -> None:
        if not self._connect_succeeds:
            raise ConnectionError(f"Failed to connect to {self.name}")
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def health_check(self) -> dict:
        return {
            "service": self.name,
            "status": "healthy" if self.is_healthy else "unhealthy",
            "connected": self._connected,
        }

    def get_client(self):
        if not self._connected:
            raise ServiceContainerError(f"{self.name} not connected")
        return f"client_{self.name}"


class TestServiceRegistry:
    """Test cases for ServiceRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh service registry for each test."""
        return ServiceRegistry()

    @pytest.fixture
    def mock_containers(self):
        """Create mock service containers for testing."""
        return {
            "redis": MockServiceContainer("redis"),
            "database": MockServiceContainer("database"),
            "queue": MockServiceContainer("queue"),
        }

    def test_register_service(self, registry, mock_containers):
        """Test registering a service."""
        registry.register("redis", mock_containers["redis"])

        assert registry.is_registered("redis")
        assert "redis" in registry.list_services()
        assert registry.get_service("redis") == mock_containers["redis"]

    def test_register_with_config_and_priority(self, registry, mock_containers):
        """Test registering a service with configuration and priority."""
        config = {"timeout": 30, "retries": 3}
        registry.register("redis", mock_containers["redis"], config=config, startup_priority=1)

        assert registry.get_service_config("redis") == config
        assert registry._startup_order == ["redis"]

    def test_register_multiple_services_with_priority(self, registry, mock_containers):
        """Test registering multiple services with different priorities."""
        registry.register("database", mock_containers["database"], startup_priority=2)
        registry.register("redis", mock_containers["redis"], startup_priority=1)
        registry.register("queue", mock_containers["queue"], startup_priority=3)

        # Should be ordered by priority (lower number = higher priority)
        assert registry._startup_order == ["redis", "database", "queue"]

    def test_register_replaces_existing(self, registry, mock_containers):
        """Test that registering an existing service replaces it."""
        registry.register("redis", mock_containers["redis"])
        new_container = MockServiceContainer("redis_new")
        registry.register("redis", new_container)

        assert registry.get_service("redis") == new_container

    def test_unregister_service(self, registry, mock_containers):
        """Test unregistering a service."""
        registry.register("redis", mock_containers["redis"])
        registry.unregister("redis")

        assert not registry.is_registered("redis")
        assert "redis" not in registry.list_services()

    def test_unregister_nonexistent_service(self, registry):
        """Test unregistering a service that doesn't exist."""
        # Should not raise an error
        registry.unregister("nonexistent")

    def test_get_nonexistent_service_raises_error(self, registry):
        """Test getting a service that doesn't exist raises error."""
        with pytest.raises(ServiceContainerError, match="not registered"):
            registry.get_service("nonexistent")

    def test_list_services(self, registry, mock_containers):
        """Test listing all registered services."""
        registry.register("redis", mock_containers["redis"])
        registry.register("database", mock_containers["database"])

        services = registry.list_services()
        assert set(services) == {"redis", "database"}

    async def test_start_all_services_success(self, registry, mock_containers):
        """Test successfully starting all services."""
        for name, container in mock_containers.items():
            registry.register(name, container)

        results = await registry.start_all()

        assert all(results.values())
        assert all(container._connected for container in mock_containers.values())

    async def test_start_all_services_with_failure(self, registry, mock_containers):
        """Test starting services when some fail."""
        # Make one service fail to connect
        mock_containers["database"]._connect_succeeds = False

        for name, container in mock_containers.items():
            registry.register(name, container)

        results = await registry.start_all()

        assert results["redis"] is True
        assert results["database"] is False
        assert results["queue"] is True

    async def test_start_all_services_fail_fast(self, registry, mock_containers):
        """Test starting services with fail-fast mode."""
        # Make database fail (middle priority)
        mock_containers["database"]._connect_succeeds = False

        registry.register("redis", mock_containers["redis"], startup_priority=1)
        registry.register("database", mock_containers["database"], startup_priority=2)
        registry.register("queue", mock_containers["queue"], startup_priority=3)

        results = await registry.start_all(fail_fast=True)

        # Should stop after database failure
        assert results["redis"] is True
        assert results["database"] is False
        assert "queue" not in results  # Should not be attempted

    async def test_stop_all_services(self, registry, mock_containers):
        """Test stopping all services."""
        for name, container in mock_containers.items():
            registry.register(name, container)
            await container.connect()

        results = await registry.stop_all()

        assert all(results.values())
        assert all(not container._connected for container in mock_containers.values())

    async def test_health_check_all(self, registry, mock_containers):
        """Test health checking all services."""
        for name, container in mock_containers.items():
            registry.register(name, container)
            await container.connect()

        # Make one service unhealthy
        mock_containers["database"]._healthy = False

        health_results = await registry.health_check_all()

        assert health_results["redis"]["status"] == "healthy"
        assert health_results["database"]["status"] == "unhealthy"
        assert health_results["queue"]["status"] == "healthy"

    async def test_health_check_with_exception(self, registry):
        """Test health check when service raises exception."""
        # Create a container that raises an exception during health check
        mock_container = MagicMock()
        mock_container.service_name = "faulty"
        mock_container.health_check = AsyncMock(side_effect=Exception("Health check failed"))

        registry.register("faulty", mock_container)

        health_results = await registry.health_check_all()

        assert health_results["faulty"]["status"] == "error"
        assert "Health check failed" in health_results["faulty"]["error"]

    def test_get_healthy_services(self, registry, mock_containers):
        """Test getting list of healthy services."""
        for name, container in mock_containers.items():
            registry.register(name, container)
            container._connected = True  # Make connected so they're healthy

        # Make one unhealthy
        mock_containers["database"]._healthy = False

        healthy = registry.get_healthy_services()
        assert set(healthy) == {"redis", "queue"}

    def test_get_unhealthy_services(self, registry, mock_containers):
        """Test getting list of unhealthy services."""
        for name, container in mock_containers.items():
            registry.register(name, container)
            container._connected = True

        # Make one unhealthy
        mock_containers["database"]._healthy = False

        unhealthy = registry.get_unhealthy_services()
        assert unhealthy == ["database"]

    async def test_restart_service_success(self, registry, mock_containers):
        """Test successfully restarting a service."""
        registry.register("redis", mock_containers["redis"])
        await mock_containers["redis"].connect()

        success = await registry.restart_service("redis")

        assert success is True
        assert mock_containers["redis"]._connected is True

    async def test_restart_service_failure(self, registry, mock_containers):
        """Test restarting a service that fails to reconnect."""
        registry.register("redis", mock_containers["redis"])
        await mock_containers["redis"].connect()

        # Make reconnection fail
        mock_containers["redis"]._connect_succeeds = False

        success = await registry.restart_service("redis")

        assert success is False

    async def test_restart_nonexistent_service(self, registry):
        """Test restarting a service that doesn't exist."""
        success = await registry.restart_service("nonexistent")
        assert success is False

    def test_get_service_config(self, registry, mock_containers):
        """Test getting service configuration."""
        config = {"timeout": 30, "retries": 3}
        registry.register("redis", mock_containers["redis"], config=config)

        retrieved_config = registry.get_service_config("redis")
        assert retrieved_config == config

        # Should return a copy, not the original
        retrieved_config["timeout"] = 60
        assert registry.get_service_config("redis")["timeout"] == 30

    def test_get_config_nonexistent_service(self, registry):
        """Test getting configuration for nonexistent service."""
        with pytest.raises(ServiceContainerError):
            registry.get_service_config("nonexistent")

    def test_update_service_config(self, registry, mock_containers):
        """Test updating service configuration."""
        config = {"timeout": 30}
        registry.register("redis", mock_containers["redis"], config=config)

        registry.update_service_config("redis", {"retries": 3, "timeout": 60})

        updated_config = registry.get_service_config("redis")
        assert updated_config["timeout"] == 60
        assert updated_config["retries"] == 3

    def test_update_config_nonexistent_service(self, registry):
        """Test updating configuration for nonexistent service."""
        with pytest.raises(ServiceContainerError):
            registry.update_service_config("nonexistent", {})

    def test_get_summary(self, registry, mock_containers):
        """Test getting registry summary."""
        for name, container in mock_containers.items():
            registry.register(name, container)
            container._connected = True

        # Make one unhealthy
        mock_containers["database"]._healthy = False

        summary = registry.get_summary()

        assert summary["total_services"] == 3
        assert summary["healthy_services"] == 2
        assert summary["unhealthy_services"] == 1
        assert set(summary["services"]["healthy"]) == {"redis", "queue"}
        assert summary["services"]["unhealthy"] == ["database"]

    async def test_context_manager(self, registry, mock_containers):
        """Test using registry as async context manager."""
        for name, container in mock_containers.items():
            registry.register(name, container)

        async with registry as reg:
            assert reg == registry
            assert all(container._connected for container in mock_containers.values())

        # Should disconnect all services on exit
        assert all(not container._connected for container in mock_containers.values())

    def test_string_representations(self, registry, mock_containers):
        """Test string representations of registry."""
        for name, container in mock_containers.items():
            registry.register(name, container)
            container._connected = True

        # Make one unhealthy
        mock_containers["database"]._healthy = False

        str_repr = str(registry)
        assert "ServiceRegistry" in str_repr
        assert "2/3 healthy" in str_repr

        repr_str = repr(registry)
        assert "ServiceRegistry" in repr_str
        assert "services=" in repr_str
        assert "healthy=" in repr_str


class TestServiceRegistryGlobalFunctions:
    """Test global service registry functions."""

    def test_get_service_registry_singleton(self):
        """Test that get_service_registry returns same instance."""
        from llm_task_framework.services.registry import get_service_registry

        registry1 = get_service_registry()
        registry2 = get_service_registry()

        assert registry1 is registry2

    def test_reset_service_registry(self):
        """Test resetting the global service registry."""
        from llm_task_framework.services.registry import (
            get_service_registry,
            reset_service_registry,
        )

        registry1 = get_service_registry()
        reset_service_registry()
        registry2 = get_service_registry()

        assert registry1 is not registry2
