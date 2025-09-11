"""
Configuration generator for Docker Compose and K3s manifests.
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader

from terrarium_cli.config.app_loader import AppConfig
from terrarium_cli.config.nginx_generator import NginxConfigGenerator

logger = logging.getLogger(__name__)


class ConfigGenerator:
    """Generates Docker Compose and K3s configurations from app configs."""
    
    def __init__(self):
        """Initialize the configuration generator."""
        self.templates_dir = Path("terrarium_cli/templates")
        self.configs_dir = Path("configs")
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        
        # Initialize NGINX config generator
        self.nginx_generator = NginxConfigGenerator()
    
    def generate_all_configs(self, apps: List[AppConfig]) -> None:
        """Generate all configuration files including NGINX."""
        # Generate NGINX configurations first
        self.nginx_generator.generate_configs()
        
        # Generate Docker Compose and K3s configurations
        self.generate_docker_compose(apps)
        self.generate_k3s_manifests(apps)
        
        # Generate kustomization.yaml dynamically
        self._generate_kustomization(self.configs_dir / "k3s", apps)
    
    def generate_docker_compose(self, apps: List[AppConfig]) -> None:
        """
        Generate Docker Compose configuration.
        
        Args:
            apps: List of app configurations
        """
        logger.info("Generating Docker Compose configuration")
        
        # Create configs directory if it doesn't exist
        docker_config_dir = self.configs_dir / "docker"
        docker_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate main docker-compose.yml
        self._generate_main_docker_compose(docker_config_dir, apps)
        
        # Generate individual compose files
        self._generate_docker_compose_files(docker_config_dir, apps)
        
        # Generate NGINX configuration
        self._generate_nginx_config(docker_config_dir, apps)
    
    def generate_k3s_manifests(self, apps: List[AppConfig]) -> None:
        """
        Generate K3s manifests.
        
        Args:
            apps: List of app configurations
        """
        logger.info("Generating K3s manifests")
        
        # Create configs directory if it doesn't exist
        k3s_config_dir = self.configs_dir / "k3s"
        k3s_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate namespace
        self._generate_namespace(k3s_config_dir)
        
        # Generate deployments
        for app in apps:
            self._generate_deployment(k3s_config_dir, app)
            self._generate_service(k3s_config_dir, app)
            if app.volumes:
                self._generate_pvc(k3s_config_dir, app)
        
        # Generate NGINX configuration
        self._generate_nginx_k3s_config(k3s_config_dir, apps)
        
        # Generate kustomization
        self._generate_kustomization(k3s_config_dir, apps)
    
    def _generate_main_docker_compose(self, config_dir: Path, apps: List[AppConfig]) -> None:
        """Generate main docker-compose.yml file."""
        template = self.jinja_env.get_template('docker-compose.yml.j2')
        compose_content = template.render(apps=apps)
        
        compose_file = config_dir / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            f.write(compose_content)
    
    def _generate_docker_compose_files(self, config_dir: Path, apps: List[AppConfig]) -> None:
        """Generate individual Docker Compose files."""
        # Base services (Vault)
        base_services = self._generate_vault_services()
        self._write_compose_file(config_dir / "docker-compose.base.yml", base_services)
        
        # Core services (Logthon, File Storage)
        core_services = self._generate_core_services(apps)
        self._write_compose_file(config_dir / "docker-compose.core.yml", core_services)
        
        # App services (Custom Client, Service Sink)
        app_services = self._generate_app_services(apps)
        self._write_compose_file(config_dir / "docker-compose.apps.yml", app_services)
        
        # Gateway services (NGINX)
        gateway_services = self._generate_gateway_services(apps)
        self._write_compose_file(config_dir / "docker-compose.gateway.yml", gateway_services)
    
    def _generate_vault_services(self) -> Dict[str, Any]:
        """Generate Vault services configuration."""
        return {
            "services": {
                "vault": {
                    "image": "hashicorp/vault:latest",
                    "container_name": "edge-terrarium-vault",
                    "ports": ["8200:8200"],
                    "environment": [
                        "VAULT_DEV_ROOT_TOKEN_ID=root",
                        "VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200",
                        "VAULT_ADDR=http://0.0.0.0:8200"
                    ],
                    "volumes": ["vault-data:/vault/data"],
                    "networks": ["edge-terrarium-network"],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": ["CMD", "vault", "status"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "40s"
                    }
                },
                "vault-init": {
                    "image": "hashicorp/vault:latest",
                    "container_name": "edge-terrarium-vault-init",
                    "depends_on": {
                        "vault": {"condition": "service_healthy"}
                    },
                    "volumes": ["./vault-init.sh:/vault-init.sh:ro"],
                    "command": ["/bin/sh", "/vault-init.sh"],
                    "networks": ["edge-terrarium-network"],
                    "restart": "no"
                }
            }
        }
    
    def _generate_core_services(self, apps: List[AppConfig]) -> Dict[str, Any]:
        """Generate core services configuration."""
        services = {}
        
        for app in apps:
            if app.name in ["logthon", "file-storage"]:
                services[app.name] = self._generate_docker_service(app)
        
        return {"services": services}
    
    def _generate_app_services(self, apps: List[AppConfig]) -> Dict[str, Any]:
        """Generate app services configuration."""
        services = {}
        
        for app in apps:
            if app.name in ["custom-client", "service-sink"]:
                services[app.name] = self._generate_docker_service(app)
        
        return {"services": services}
    
    def _generate_gateway_services(self, apps: List[AppConfig]) -> Dict[str, Any]:
        """Generate gateway services configuration."""
        nginx_app = next((app for app in apps if app.name == "nginx"), None)
        if not nginx_app:
            return {"services": {}}
        
        services = {
            "nginx": self._generate_docker_service(nginx_app)
        }
        
        return {"services": services}
    
    def _generate_docker_service(self, app: AppConfig) -> Dict[str, Any]:
        """Generate Docker service configuration for an app."""
        service = {
            "build": {
                "context": f"../../apps/{app.name}",
                "dockerfile": app.docker.dockerfile
            },
            "image": f"{app.docker.image_name}:{app.docker.tag}",
            "container_name": f"edge-terrarium-{app.name}",
            "ports": [f"{app.runtime.port}:{app.runtime.port}"],
            "environment": [f"{env.name}={env.value}" for env in app.environment if env.value],
            "networks": ["edge-terrarium-network"],
            "restart": "unless-stopped"
        }
        
        # Add health check
        if app.health_checks:
            health_check = list(app.health_checks.values())[0]
            service["healthcheck"] = {
                "test": ["CMD", "curl", "-f", f"http://localhost:{health_check.port}{health_check.path}"],
                "interval": f"{health_check.period_seconds}s",
                "timeout": f"{health_check.timeout_seconds}s",
                "retries": health_check.failure_threshold,
                "start_period": "5s"
            }
        
        # Add volumes
        if app.volumes:
            service["volumes"] = [f"{vol.name}:{vol.mount_path}" for vol in app.volumes]
        
        # Add dependencies
        if app.dependencies:
            service["depends_on"] = {dep: {"condition": "service_healthy"} for dep in app.dependencies}
        
        return service
    
    def _generate_docker_volumes(self, apps: List[AppConfig]) -> Dict[str, Any]:
        """Generate Docker volumes configuration."""
        volumes = {}
        
        for app in apps:
            for volume in app.volumes:
                volumes[volume.name] = {"driver": "local"}
        
        # Add standard volumes
        volumes.update({
            "vault-data": {"driver": "local"},
            "vault-logs": {"driver": "local"}
        })
        
        return volumes
    
    def _write_compose_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write Docker Compose file."""
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def _generate_nginx_config(self, config_dir: Path, apps: List[AppConfig]) -> None:
        """Generate NGINX configuration."""
        nginx_dir = config_dir / "nginx"
        nginx_dir.mkdir(exist_ok=True)
        
        # Generate upstreams and routes
        upstreams = []
        routes = []
        
        for app in apps:
            if app.name == "nginx":
                continue
                
            upstreams.append({
                "name": app.name,
                "host": app.name,
                "port": app.runtime.port
            })
            
            for route in app.routes:
                routes.append({
                    "path": route.path,
                    "upstream": app.name,
                    "strip_prefix": route.strip_prefix
                })
        
        # Generate NGINX config using template
        template_data = {
            "upstreams": upstreams,
            "routes": routes
        }
        
        # Load template
        template_file = Path("terrarium_cli/templates/nginx.conf.template")
        if template_file.exists():
            with open(template_file, 'r') as f:
                template = Template(f.read())
            
            nginx_config = template.render(**template_data)
            
            with open(nginx_dir / "default.conf", 'w') as f:
                f.write(nginx_config)
    
    def _generate_namespace(self, config_dir: Path) -> None:
        """Generate namespace manifest."""
        namespace_data = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": "edge-terrarium",
                "labels": {
                    "name": "edge-terrarium",
                    "project": "edge-terrarium"
                }
            }
        }
        
        with open(config_dir / "namespace.yaml", 'w') as f:
            yaml.dump(namespace_data, f, default_flow_style=False, sort_keys=False)
    
    def _generate_deployment(self, config_dir: Path, app: AppConfig) -> None:
        """Generate deployment manifest for an app."""
        template = self.jinja_env.get_template('k3s-deployment.yaml.j2')
        deployment_content = template.render(app=app)
        
        with open(config_dir / f"{app.name}-deployment.yaml", 'w') as f:
            f.write(deployment_content)
    
    def _generate_container_spec(self, app: AppConfig) -> Dict[str, Any]:
        """Generate container specification."""
        container = {
            "name": app.name,
            "image": f"{app.docker.image_name}:{app.docker.tag}",
            "ports": [{
                "containerPort": app.runtime.port,
                "name": "http"
            }],
            "env": []
        }
        
        # Add environment variables
        for env_var in app.environment:
            if env_var.value:
                container["env"].append({
                    "name": env_var.name,
                    "value": env_var.value
                })
            elif env_var.value_from:
                container["env"].append({
                    "name": env_var.name,
                    "valueFrom": {
                        "fieldRef": {
                            "fieldPath": env_var.value_from
                        }
                    }
                })
        
        # Add health checks
        if app.health_checks:
            for check_name, check_config in app.health_checks.items():
                if check_name == "liveness":
                    container["livenessProbe"] = {
                        "httpGet": {
                            "path": check_config.path,
                            "port": check_config.port
                        },
                        "periodSeconds": check_config.period_seconds,
                        "timeoutSeconds": check_config.timeout_seconds,
                        "failureThreshold": check_config.failure_threshold
                    }
                elif check_name == "readiness":
                    container["readinessProbe"] = {
                        "httpGet": {
                            "path": check_config.path,
                            "port": check_config.port
                        },
                        "periodSeconds": check_config.period_seconds,
                        "timeoutSeconds": check_config.timeout_seconds,
                        "failureThreshold": check_config.failure_threshold
                    }
        
        # Add resources
        container["resources"] = {
            "requests": {
                "cpu": app.resources.cpu["request"],
                "memory": app.resources.memory["request"]
            },
            "limits": {
                "cpu": app.resources.cpu["limit"],
                "memory": app.resources.memory["limit"]
            }
        }
        
        # Add security context
        container["securityContext"] = {
            "runAsNonRoot": app.security.run_as_non_root,
            "runAsUser": app.security.run_as_user,
            "runAsGroup": app.security.run_as_group,
            "allowPrivilegeEscalation": app.security.allow_privilege_escalation,
            "readOnlyRootFilesystem": app.security.read_only_root_filesystem
        }
        
        # Add volume mounts
        if app.volumes:
            container["volumeMounts"] = [
                {
                    "name": vol.name,
                    "mountPath": vol.mount_path
                }
                for vol in app.volumes
            ]
        
        return container
    
    def _generate_service(self, config_dir: Path, app: AppConfig) -> None:
        """Generate service manifest for an app."""
        template = self.jinja_env.get_template('k3s-service.yaml.j2')
        service_content = template.render(app=app)
        
        with open(config_dir / f"{app.name}-service.yaml", 'w') as f:
            f.write(service_content)
    
    def _generate_pvc(self, config_dir: Path, app: AppConfig) -> None:
        """Generate PVC manifest for an app."""
        if app.volumes:
            template = self.jinja_env.get_template('k3s-pvc.yaml.j2')
            pvc_content = template.render(apps=[app])
            
            with open(config_dir / f"{app.name}-pvc.yaml", 'w') as f:
                f.write(pvc_content)
    
    def _generate_nginx_k3s_config(self, config_dir: Path, apps: List[AppConfig]) -> None:
        """Generate NGINX configuration for K3s."""
        template = self.jinja_env.get_template('k3s-ingress.yaml.j2')
        ingress_content = template.render(apps=apps)
        
        with open(config_dir / "ingress.yaml", 'w') as f:
            f.write(ingress_content)
    
    def _generate_kustomization(self, config_dir: Path, apps: List[AppConfig]) -> None:
        """Generate kustomization.yaml file dynamically based on available resources."""
        resources = [
            "namespace.yaml",
            "nginx-configmap.yaml"  # NGINX ConfigMap is always needed
        ]
        
        # Add app-specific resources (this includes nginx, vault, etc.)
        for app in apps:
            resources.append(f"{app.name}-deployment.yaml")
            resources.append(f"{app.name}-service.yaml")
            if app.volumes:
                resources.append(f"{app.name}-pvc.yaml")
        
        # Add ingress resources
        resources.extend([
            "ingress.yaml"
        ])
        
        # Add Logthon-specific ingress resources
        resources.extend([
            "logthon-ingress.yaml",
            "logthon-ingress-service.yaml"
        ])
        
        kustomization_data = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": resources
        }
        
        with open(config_dir / "kustomization.yaml", 'w') as f:
            yaml.dump(kustomization_data, f, default_flow_style=False, sort_keys=False)
