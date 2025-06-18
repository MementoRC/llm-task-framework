"""Configuration management for service containers.

Provides centralized configuration loading, validation, and management
for all service containers with support for environment variables,
configuration files, and runtime overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml
import yaml


@dataclass
class RedisConfig:
    """Configuration for Redis service container."""

    redis_url: str = "redis://localhost:6379"
    max_retries: int = 3
    retry_delay: float = 1.0
    connection_timeout: float = 5.0
    socket_timeout: float = 5.0
    decode_responses: bool = True
    test_database: int = 15

    @classmethod
    def from_env(cls, prefix: str = "REDIS_") -> "RedisConfig":
        """
        Create Redis configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix (default: "REDIS_")
            
        Returns:
            RedisConfig instance with values from environment
        """
        return cls(
            redis_url=os.environ.get(f"{prefix}URL", cls.redis_url),
            max_retries=int(os.environ.get(f"{prefix}MAX_RETRIES", cls.max_retries)),
            retry_delay=float(os.environ.get(f"{prefix}RETRY_DELAY", cls.retry_delay)),
            connection_timeout=float(os.environ.get(f"{prefix}CONNECTION_TIMEOUT", cls.connection_timeout)),
            socket_timeout=float(os.environ.get(f"{prefix}SOCKET_TIMEOUT", cls.socket_timeout)),
            decode_responses=os.environ.get(f"{prefix}DECODE_RESPONSES", str(cls.decode_responses)).lower() == "true",
            test_database=int(os.environ.get(f"{prefix}TEST_DATABASE", cls.test_database)),
        )


@dataclass
class ServiceConfig:
    """Generic service configuration container."""

    enabled: bool = True
    startup_priority: int = 0
    health_check_interval: float = 30.0
    startup_timeout: float = 30.0
    shutdown_timeout: float = 10.0
    retry_on_failure: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceConfig":
        """
        Create service configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            ServiceConfig instance
        """
        return cls(
            enabled=data.get("enabled", cls.enabled),
            startup_priority=data.get("startup_priority", cls.startup_priority),
            health_check_interval=data.get("health_check_interval", cls.health_check_interval),
            startup_timeout=data.get("startup_timeout", cls.startup_timeout),
            shutdown_timeout=data.get("shutdown_timeout", cls.shutdown_timeout),
            retry_on_failure=data.get("retry_on_failure", cls.retry_on_failure),
        )


@dataclass
class ServicesConfig:
    """Configuration for all services."""

    redis: RedisConfig = field(default_factory=RedisConfig)
    global_config: ServiceConfig = field(default_factory=ServiceConfig)
    service_configs: dict[str, ServiceConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ServicesConfig":
        """
        Create services configuration from environment variables.
        
        Returns:
            ServicesConfig instance with values from environment
        """
        return cls(
            redis=RedisConfig.from_env(),
            global_config=ServiceConfig.from_dict({
                "enabled": os.environ.get("SERVICES_ENABLED", "true").lower() == "true",
                "startup_priority": int(os.environ.get("SERVICES_STARTUP_PRIORITY", "0")),
                "health_check_interval": float(os.environ.get("SERVICES_HEALTH_CHECK_INTERVAL", "30.0")),
                "startup_timeout": float(os.environ.get("SERVICES_STARTUP_TIMEOUT", "30.0")),
                "shutdown_timeout": float(os.environ.get("SERVICES_SHUTDOWN_TIMEOUT", "10.0")),
                "retry_on_failure": os.environ.get("SERVICES_RETRY_ON_FAILURE", "true").lower() == "true",
            }),
        )

    @classmethod
    def from_file(cls, config_path: str | Path) -> "ServicesConfig":
        """
        Load services configuration from file.
        
        Supports YAML and TOML formats.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            ServicesConfig instance loaded from file
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration format is unsupported
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        if config_path.suffix.lower() in [".yaml", ".yml"]:
            with open(config_path) as f:
                data = yaml.safe_load(f)
        elif config_path.suffix.lower() == ".toml":
            with open(config_path) as f:
                data = toml.load(f)
        else:
            raise ValueError(f"Unsupported configuration format: {config_path.suffix}")

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServicesConfig":
        """
        Create services configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            ServicesConfig instance
        """
        config = cls()

        # Load Redis configuration
        if "redis" in data:
            redis_data = data["redis"]
            config.redis = RedisConfig(
                redis_url=redis_data.get("redis_url", config.redis.redis_url),
                max_retries=redis_data.get("max_retries", config.redis.max_retries),
                retry_delay=redis_data.get("retry_delay", config.redis.retry_delay),
                connection_timeout=redis_data.get("connection_timeout", config.redis.connection_timeout),
                socket_timeout=redis_data.get("socket_timeout", config.redis.socket_timeout),
                decode_responses=redis_data.get("decode_responses", config.redis.decode_responses),
                test_database=redis_data.get("test_database", config.redis.test_database),
            )

        # Load global service configuration
        if "global" in data:
            config.global_config = ServiceConfig.from_dict(data["global"])

        # Load individual service configurations
        if "services" in data:
            for service_name, service_data in data["services"].items():
                config.service_configs[service_name] = ServiceConfig.from_dict(service_data)

        return config

    def get_service_config(self, service_name: str) -> ServiceConfig:
        """
        Get configuration for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceConfig for the service, falls back to global config
        """
        return self.service_configs.get(service_name, self.global_config)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "redis": {
                "redis_url": self.redis.redis_url,
                "max_retries": self.redis.max_retries,
                "retry_delay": self.redis.retry_delay,
                "connection_timeout": self.redis.connection_timeout,
                "socket_timeout": self.redis.socket_timeout,
                "decode_responses": self.redis.decode_responses,
                "test_database": self.redis.test_database,
            },
            "global": {
                "enabled": self.global_config.enabled,
                "startup_priority": self.global_config.startup_priority,
                "health_check_interval": self.global_config.health_check_interval,
                "startup_timeout": self.global_config.startup_timeout,
                "shutdown_timeout": self.global_config.shutdown_timeout,
                "retry_on_failure": self.global_config.retry_on_failure,
            },
            "services": {
                name: {
                    "enabled": config.enabled,
                    "startup_priority": config.startup_priority,
                    "health_check_interval": config.health_check_interval,
                    "startup_timeout": config.startup_timeout,
                    "shutdown_timeout": config.shutdown_timeout,
                    "retry_on_failure": config.retry_on_failure,
                }
                for name, config in self.service_configs.items()
            },
        }


class ConfigurationManager:
    """Manager for service configuration with environment and file support."""

    def __init__(self, config_file: str | Path | None = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self._config_file = Path(config_file) if config_file else None
        self._config: ServicesConfig | None = None

    def load_config(self, force_reload: bool = False) -> ServicesConfig:
        """
        Load configuration with precedence: file -> environment -> defaults.
        
        Args:
            force_reload: Force reload even if config is already loaded
            
        Returns:
            Loaded ServicesConfig instance
        """
        if self._config is not None and not force_reload:
            return self._config

        # Start with environment-based configuration
        config = ServicesConfig.from_env()

        # Override with file-based configuration if available
        if self._config_file and self._config_file.exists():
            try:
                file_config = ServicesConfig.from_file(self._config_file)
                # Merge configurations (file takes precedence)
                config = self._merge_configs(config, file_config)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load config file {self._config_file}: {e}")

        self._config = config
        return config

    def _merge_configs(self, base: ServicesConfig, override: ServicesConfig) -> ServicesConfig:
        """
        Merge two configurations with override taking precedence.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        # Create new config starting with base
        merged = ServicesConfig(
            redis=base.redis,
            global_config=base.global_config,
            service_configs=base.service_configs.copy(),
        )

        # Apply Redis overrides
        merged.redis = override.redis

        # Apply global config overrides
        merged.global_config = override.global_config

        # Apply service-specific overrides
        merged.service_configs.update(override.service_configs)

        return merged

    def get_config(self) -> ServicesConfig:
        """
        Get current configuration, loading if necessary.
        
        Returns:
            Current ServicesConfig instance
        """
        return self.load_config()

    def reload_config(self) -> ServicesConfig:
        """
        Force reload configuration from sources.
        
        Returns:
            Reloaded ServicesConfig instance
        """
        return self.load_config(force_reload=True)


# Global configuration manager instance
_global_config_manager: ConfigurationManager | None = None


def get_config_manager(config_file: str | Path | None = None) -> ConfigurationManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_file: Optional configuration file path (only used on first call)
        
    Returns:
        Global ConfigurationManager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager(config_file)
    return _global_config_manager


def get_services_config() -> ServicesConfig:
    """
    Get the current services configuration.
    
    Returns:
        Current ServicesConfig instance
    """
    return get_config_manager().get_config()


def reset_config_manager() -> None:
    """
    Reset the global configuration manager.
    
    Useful for testing to ensure clean state.
    """
    global _global_config_manager
    _global_config_manager = None
