"""
Application configuration loader.
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DockerConfig:
    """Docker configuration for an app."""
    build_context: str
    dockerfile: str
    image_name: str
    tag: str = "latest"


@dataclass
class RuntimeConfig:
    """Runtime configuration for an app."""
    port: int
    health_check_path: str = "/health"
    startup_timeout: int = 30
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    port_forward: Optional[int] = None  # Host port for port forwarding


@dataclass
class EnvironmentVariable:
    """Environment variable configuration."""
    name: str
    value: Optional[str] = None
    value_from: Optional[str] = None


@dataclass
class RouteConfig:
    """Route configuration for an app."""
    path: str
    target: str
    strip_prefix: bool = True


@dataclass
class ResourceConfig:
    """Resource configuration for an app."""
    cpu: Dict[str, str] = field(default_factory=lambda: {"request": "100m", "limit": "200m"})
    memory: Dict[str, str] = field(default_factory=lambda: {"request": "128Mi", "limit": "256Mi"})


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    path: str
    port: int
    period_seconds: int = 30
    timeout_seconds: int = 3
    failure_threshold: int = 3


@dataclass
class VolumeConfig:
    """Volume configuration for an app."""
    name: str
    mount_path: str
    size: str = "1Gi"
    access_mode: str = "ReadWriteOnce"


@dataclass
class SecurityConfig:
    """Security configuration for an app."""
    run_as_non_root: bool = True
    run_as_user: int = 1001
    run_as_group: int = 1001
    allow_privilege_escalation: bool = False
    read_only_root_filesystem: bool = False


@dataclass
class AppConfig:
    """Application configuration."""
    name: str
    description: str
    docker: DockerConfig
    runtime: RuntimeConfig
    environment: List[EnvironmentVariable] = field(default_factory=list)
    routes: List[RouteConfig] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    health_checks: Dict[str, HealthCheckConfig] = field(default_factory=dict)
    volumes: List[VolumeConfig] = field(default_factory=list)
    security: SecurityConfig = field(default_factory=SecurityConfig)


class AppLoader:
    """Loads application configurations from app-config.yml files."""
    
    def __init__(self, apps_dir: str = "apps"):
        """
        Initialize the app loader.
        
        Args:
            apps_dir: Directory containing app configurations
        """
        self.apps_dir = Path(apps_dir)
    
    def load_apps(self) -> List[AppConfig]:
        """
        Load all application configurations.
        
        Returns:
            List of app configurations
        """
        apps = []
        
        if not self.apps_dir.exists():
            logger.warning(f"Apps directory {self.apps_dir} does not exist")
            return apps
        
        for app_dir in self.apps_dir.iterdir():
            if app_dir.is_dir():
                app_config = self._load_app_config(app_dir)
                if app_config:
                    apps.append(app_config)
        
        logger.info(f"Loaded {len(apps)} application configurations")
        return apps
    
    def _load_app_config(self, app_dir: Path) -> Optional[AppConfig]:
        """
        Load configuration for a single app.
        
        Args:
            app_dir: App directory path
            
        Returns:
            App configuration or None if loading failed
        """
        config_file = app_dir / "app-config.yml"
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            return None
        
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return self._parse_app_config(data, app_dir.name)
            
        except Exception as e:
            logger.error(f"Failed to load config for {app_dir.name}: {e}")
            return None
    
    def _parse_app_config(self, data: Dict[str, Any], app_name: str) -> AppConfig:
        """
        Parse app configuration from YAML data.
        
        Args:
            data: YAML data
            app_name: App name
            
        Returns:
            App configuration
        """
        # Parse Docker config
        docker_data = data.get("docker", {})
        docker_config = DockerConfig(
            build_context=docker_data.get("build_context", "."),
            dockerfile=docker_data.get("dockerfile", "Dockerfile"),
            image_name=docker_data.get("image_name", f"edge-terrarium-{app_name}"),
            tag=docker_data.get("tag", "latest")
        )
        
        # Parse runtime config
        runtime_data = data.get("runtime", {})
        runtime_config = RuntimeConfig(
            port=runtime_data.get("port", 8080),
            health_check_path=runtime_data.get("health_check_path", "/health"),
            startup_timeout=runtime_data.get("startup_timeout", 30),
            command=runtime_data.get("command"),
            args=runtime_data.get("args"),
            port_forward=runtime_data.get("port_forward")
        )
        
        # Parse environment variables
        environment = []
        env_data = data.get("environment", [])
        if env_data and isinstance(env_data, list):
            for env_item in env_data:
                if isinstance(env_item, dict):
                    env_var = EnvironmentVariable(
                        name=env_item.get("name", ""),
                        value=env_item.get("value"),
                        value_from=env_item.get("value_from")
                    )
                    environment.append(env_var)
        
        # Parse routes
        routes = []
        routes_data = data.get("routes", [])
        if routes_data and isinstance(routes_data, list):
            for route_data in routes_data:
                if isinstance(route_data, dict):
                    route = RouteConfig(
                        path=route_data.get("path", ""),
                        target=route_data.get("target", "/"),
                        strip_prefix=route_data.get("strip_prefix", True)
                    )
                    routes.append(route)
        
        # Parse resources
        resources_data = data.get("resources", {})
        resources = ResourceConfig(
            cpu=resources_data.get("cpu", {"request": "100m", "limit": "200m"}),
            memory=resources_data.get("memory", {"request": "128Mi", "limit": "256Mi"})
        )
        
        # Parse health checks
        health_checks = {}
        health_checks_data = data.get("health_checks", {})
        for check_name, check_data in health_checks_data.items():
            health_check = HealthCheckConfig(
                path=check_data.get("path", "/health"),
                port=check_data.get("port", runtime_config.port),
                period_seconds=check_data.get("period_seconds", 30),
                timeout_seconds=check_data.get("timeout_seconds", 3),
                failure_threshold=check_data.get("failure_threshold", 3)
            )
            health_checks[check_name] = health_check
        
        # Parse volumes
        volumes = []
        volumes_data = data.get("volumes", [])
        if volumes_data and isinstance(volumes_data, list):
            for volume_data in volumes_data:
                if isinstance(volume_data, dict):
                    volume = VolumeConfig(
                        name=volume_data.get("name", ""),
                        mount_path=volume_data.get("mount_path", ""),
                        size=volume_data.get("size", "1Gi"),
                        access_mode=volume_data.get("access_mode", "ReadWriteOnce")
                    )
                    volumes.append(volume)
        
        # Parse security
        security_data = data.get("security", {})
        security = SecurityConfig(
            run_as_non_root=security_data.get("run_as_non_root", True),
            run_as_user=security_data.get("run_as_user", 1001),
            run_as_group=security_data.get("run_as_group", 1001),
            allow_privilege_escalation=security_data.get("allow_privilege_escalation", False),
            read_only_root_filesystem=security_data.get("read_only_root_filesystem", False)
        )
        
        return AppConfig(
            name=data.get("name", app_name),
            description=data.get("description", ""),
            docker=docker_config,
            runtime=runtime_config,
            environment=environment,
            routes=routes,
            dependencies=data.get("dependencies", []) if data.get("dependencies") is not None else [],
            resources=resources,
            health_checks=health_checks,
            volumes=volumes,
            security=security
        )
