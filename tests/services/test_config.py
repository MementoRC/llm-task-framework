"""Tests for service configuration management."""

import os
from unittest.mock import patch

import pytest
import toml
import yaml

from llm_task_framework.services.config import (
    ConfigurationManager,
    RedisConfig,
    ServiceConfig,
    ServicesConfig,
    get_config_manager,
    get_services_config,
    reset_config_manager,
)


class TestRedisConfig:
    """Test cases for RedisConfig."""

    def test_default_values(self):
        """Test RedisConfig with default values."""
        config = RedisConfig()

        assert config.redis_url == "redis://localhost:6379"
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.connection_timeout == 5.0
        assert config.socket_timeout == 5.0
        assert config.decode_responses is True
        assert config.test_database == 15

    def test_custom_values(self):
        """Test RedisConfig with custom values."""
        config = RedisConfig(
            redis_url="redis://custom:6380",
            max_retries=5,
            retry_delay=2.0,
            connection_timeout=10.0,
            socket_timeout=15.0,
            decode_responses=False,
            test_database=5,
        )

        assert config.redis_url == "redis://custom:6380"
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.connection_timeout == 10.0
        assert config.socket_timeout == 15.0
        assert config.decode_responses is False
        assert config.test_database == 5

    def test_from_env_default_prefix(self):
        """Test creating RedisConfig from environment with default prefix."""
        env_vars = {
            "REDIS_URL": "redis://env:6379",
            "REDIS_MAX_RETRIES": "10",
            "REDIS_RETRY_DELAY": "3.0",
            "REDIS_CONNECTION_TIMEOUT": "20.0",
            "REDIS_SOCKET_TIMEOUT": "25.0",
            "REDIS_DECODE_RESPONSES": "false",
            "REDIS_TEST_DATABASE": "10",
        }

        with patch.dict(os.environ, env_vars):
            config = RedisConfig.from_env()

            assert config.redis_url == "redis://env:6379"
            assert config.max_retries == 10
            assert config.retry_delay == 3.0
            assert config.connection_timeout == 20.0
            assert config.socket_timeout == 25.0
            assert config.decode_responses is False
            assert config.test_database == 10

    def test_from_env_custom_prefix(self):
        """Test creating RedisConfig from environment with custom prefix."""
        env_vars = {
            "CUSTOM_URL": "redis://custom:6379",
            "CUSTOM_MAX_RETRIES": "7",
        }

        with patch.dict(os.environ, env_vars):
            config = RedisConfig.from_env(prefix="CUSTOM_")

            assert config.redis_url == "redis://custom:6379"
            assert config.max_retries == 7
            # Other values should be defaults
            assert config.retry_delay == 1.0

    def test_from_env_partial_vars(self):
        """Test creating RedisConfig with only some environment variables."""
        env_vars = {
            "REDIS_URL": "redis://partial:6379",
            "REDIS_MAX_RETRIES": "8",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = RedisConfig.from_env()

            assert config.redis_url == "redis://partial:6379"
            assert config.max_retries == 8
            # Other values should be defaults
            assert config.retry_delay == 1.0
            assert config.decode_responses is True


class TestServiceConfig:
    """Test cases for ServiceConfig."""

    def test_default_values(self):
        """Test ServiceConfig with default values."""
        config = ServiceConfig()

        assert config.enabled is True
        assert config.startup_priority == 0
        assert config.health_check_interval == 30.0
        assert config.startup_timeout == 30.0
        assert config.shutdown_timeout == 10.0
        assert config.retry_on_failure is True

    def test_from_dict(self):
        """Test creating ServiceConfig from dictionary."""
        data = {
            "enabled": False,
            "startup_priority": 5,
            "health_check_interval": 60.0,
            "startup_timeout": 45.0,
            "shutdown_timeout": 15.0,
            "retry_on_failure": False,
        }

        config = ServiceConfig.from_dict(data)

        assert config.enabled is False
        assert config.startup_priority == 5
        assert config.health_check_interval == 60.0
        assert config.startup_timeout == 45.0
        assert config.shutdown_timeout == 15.0
        assert config.retry_on_failure is False

    def test_from_dict_partial(self):
        """Test creating ServiceConfig from partial dictionary."""
        data = {
            "enabled": False,
            "startup_priority": 3,
        }

        config = ServiceConfig.from_dict(data)

        assert config.enabled is False
        assert config.startup_priority == 3
        # Other values should be defaults
        assert config.health_check_interval == 30.0
        assert config.retry_on_failure is True


class TestServicesConfig:
    """Test cases for ServicesConfig."""

    def test_default_values(self):
        """Test ServicesConfig with default values."""
        config = ServicesConfig()

        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.global_config, ServiceConfig)
        assert config.service_configs == {}

    def test_from_env(self):
        """Test creating ServicesConfig from environment."""
        env_vars = {
            "REDIS_URL": "redis://env:6379",
            "REDIS_MAX_RETRIES": "5",
            "SERVICES_ENABLED": "false",
            "SERVICES_STARTUP_PRIORITY": "2",
            "SERVICES_HEALTH_CHECK_INTERVAL": "45.0",
        }

        with patch.dict(os.environ, env_vars):
            config = ServicesConfig.from_env()

            assert config.redis.redis_url == "redis://env:6379"
            assert config.redis.max_retries == 5
            assert config.global_config.enabled is False
            assert config.global_config.startup_priority == 2
            assert config.global_config.health_check_interval == 45.0

    def test_from_dict(self):
        """Test creating ServicesConfig from dictionary."""
        data = {
            "redis": {
                "redis_url": "redis://dict:6379",
                "max_retries": 7,
                "decode_responses": False,
            },
            "global": {
                "enabled": False,
                "startup_priority": 1,
            },
            "services": {
                "custom_service": {
                    "enabled": True,
                    "startup_priority": 5,
                },
            },
        }

        config = ServicesConfig.from_dict(data)

        assert config.redis.redis_url == "redis://dict:6379"
        assert config.redis.max_retries == 7
        assert config.redis.decode_responses is False
        assert config.global_config.enabled is False
        assert config.global_config.startup_priority == 1
        assert "custom_service" in config.service_configs
        assert config.service_configs["custom_service"].startup_priority == 5

    def test_get_service_config_existing(self):
        """Test getting configuration for existing service."""
        config = ServicesConfig()
        service_config = ServiceConfig(startup_priority=3)
        config.service_configs["test_service"] = service_config

        retrieved = config.get_service_config("test_service")

        assert retrieved == service_config

    def test_get_service_config_fallback_to_global(self):
        """Test getting configuration falls back to global config."""
        config = ServicesConfig()
        config.global_config.startup_priority = 5

        retrieved = config.get_service_config("nonexistent_service")

        assert retrieved == config.global_config

    def test_to_dict(self):
        """Test converting ServicesConfig to dictionary."""
        config = ServicesConfig()
        config.redis.redis_url = "redis://test:6379"
        config.global_config.enabled = False
        config.service_configs["test"] = ServiceConfig(startup_priority=2)

        data = config.to_dict()

        assert data["redis"]["redis_url"] == "redis://test:6379"
        assert data["global"]["enabled"] is False
        assert data["services"]["test"]["startup_priority"] == 2

    def test_from_yaml_file(self, tmp_path):
        """Test loading ServicesConfig from YAML file."""
        config_data = {
            "redis": {
                "redis_url": "redis://yaml:6379",
                "max_retries": 4,
            },
            "global": {
                "enabled": True,
                "startup_priority": 1,
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = ServicesConfig.from_file(config_file)

        assert config.redis.redis_url == "redis://yaml:6379"
        assert config.redis.max_retries == 4
        assert config.global_config.enabled is True
        assert config.global_config.startup_priority == 1

    def test_from_toml_file(self, tmp_path):
        """Test loading ServicesConfig from TOML file."""
        config_data = {
            "redis": {
                "redis_url": "redis://toml:6379",
                "max_retries": 6,
            },
            "global": {
                "enabled": False,
                "startup_priority": 3,
            },
        }

        config_file = tmp_path / "config.toml"
        with open(config_file, "w") as f:
            toml.dump(config_data, f)

        config = ServicesConfig.from_file(config_file)

        assert config.redis.redis_url == "redis://toml:6379"
        assert config.redis.max_retries == 6
        assert config.global_config.enabled is False
        assert config.global_config.startup_priority == 3

    def test_from_file_not_found(self, tmp_path):
        """Test loading from non-existent file raises error."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            ServicesConfig.from_file(config_file)

    def test_from_file_unsupported_format(self, tmp_path):
        """Test loading from unsupported file format raises error."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "data"}')

        with pytest.raises(ValueError, match="Unsupported configuration format"):
            ServicesConfig.from_file(config_file)


class TestConfigurationManager:
    """Test cases for ConfigurationManager."""

    def test_init_without_config_file(self):
        """Test initializing ConfigurationManager without config file."""
        manager = ConfigurationManager()

        assert manager._config_file is None
        assert manager._config is None

    def test_init_with_config_file(self, tmp_path):
        """Test initializing ConfigurationManager with config file."""
        config_file = tmp_path / "config.yaml"
        manager = ConfigurationManager(config_file)

        assert manager._config_file == config_file

    def test_load_config_from_env_only(self):
        """Test loading configuration from environment only."""
        env_vars = {
            "REDIS_URL": "redis://env-only:6379",
            "SERVICES_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars):
            manager = ConfigurationManager()
            config = manager.load_config()

            assert config.redis.redis_url == "redis://env-only:6379"
            assert config.global_config.enabled is False

    def test_load_config_with_file_override(self, tmp_path):
        """Test loading configuration with file overriding environment."""
        # Set environment variables
        env_vars = {
            "REDIS_URL": "redis://env:6379",
            "REDIS_MAX_RETRIES": "3",
            "SERVICES_ENABLED": "true",
        }

        # Create config file that overrides some values
        config_data = {
            "redis": {
                "redis_url": "redis://file:6379",
                "max_retries": 8,
            },
            "global": {
                "enabled": False,
            },
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(os.environ, env_vars):
            manager = ConfigurationManager(config_file)
            config = manager.load_config()

            # File values should override environment
            assert config.redis.redis_url == "redis://file:6379"
            assert config.redis.max_retries == 8
            assert config.global_config.enabled is False

    def test_load_config_caching(self):
        """Test that load_config caches the result."""
        manager = ConfigurationManager()

        config1 = manager.load_config()
        config2 = manager.load_config()

        assert config1 is config2

    def test_load_config_force_reload(self):
        """Test force reloading configuration."""
        manager = ConfigurationManager()

        config1 = manager.load_config()
        config2 = manager.load_config(force_reload=True)

        assert config1 is not config2

    def test_get_config(self):
        """Test getting current configuration."""
        manager = ConfigurationManager()

        config = manager.get_config()

        assert isinstance(config, ServicesConfig)

    def test_reload_config(self):
        """Test reloading configuration."""
        manager = ConfigurationManager()

        config1 = manager.get_config()
        config2 = manager.reload_config()

        assert config1 is not config2

    def test_load_config_with_invalid_file(self, tmp_path):
        """Test loading config with invalid file logs warning."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        manager = ConfigurationManager(config_file)

        # Should not raise, should log warning and use env config
        config = manager.load_config()
        assert isinstance(config, ServicesConfig)


class TestGlobalConfigFunctions:
    """Test global configuration functions."""

    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns same instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_get_config_manager_with_file(self, tmp_path):
        """Test get_config_manager with config file on first call."""
        config_file = tmp_path / "test_config.yaml"

        # Reset first to ensure clean state
        reset_config_manager()

        manager = get_config_manager(config_file)

        assert manager._config_file == config_file

    def test_get_services_config(self):
        """Test getting services configuration."""
        config = get_services_config()

        assert isinstance(config, ServicesConfig)

    def test_reset_config_manager(self):
        """Test resetting global configuration manager."""
        manager1 = get_config_manager()
        reset_config_manager()
        manager2 = get_config_manager()

        assert manager1 is not manager2
