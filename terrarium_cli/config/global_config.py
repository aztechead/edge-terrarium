"""
Global configuration for the terrarium CLI.
"""

from dataclasses import dataclass
from typing import Dict, Any
import yaml
from pathlib import Path


@dataclass
class GlobalConfig:
    """Global configuration settings."""
    project_name: str = "edge-terrarium"
    namespace: str = "edge-terrarium"
    network_name: str = "edge-terrarium"
    host_name: str = "edge-terrarium.local"
    tls_secret_name: str = "edge-terrarium-tls"
    nginx_port: int = 8443
    vault_port: int = 8200
    dashboard_port: int = 9443
    k3s_api_port: int = 6443
    
    # K3s port mappings
    k3s_port_mappings: Dict[str, int] = None
    
    def __post_init__(self):
        if self.k3s_port_mappings is None:
            self.k3s_port_mappings = {
                "80": 80,
                "443": 443,
                "8200": 8200,
                "5001": 5001
            }


def load_global_config() -> GlobalConfig:
    """Load global configuration from file or use defaults."""
    config_file = Path("terrarium-config.yml")
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return GlobalConfig(
                project_name=data.get("project_name", "edge-terrarium"),
                namespace=data.get("namespace", "edge-terrarium"),
                network_name=data.get("network_name", "edge-terrarium"),
                host_name=data.get("host_name", "edge-terrarium.local"),
                tls_secret_name=data.get("tls_secret_name", "edge-terrarium-tls"),
                nginx_port=data.get("nginx_port", 8443),
                vault_port=data.get("vault_port", 8200),
                dashboard_port=data.get("dashboard_port", 9443),
                k3s_api_port=data.get("k3s_api_port", 6443),
                k3s_port_mappings=data.get("k3s_port_mappings", {
                    "80": 80,
                    "443": 443,
                    "8200": 8200,
                    "5001": 5001
                })
            )
        except Exception as e:
            print(f"Warning: Failed to load global config: {e}")
            return GlobalConfig()
    
    return GlobalConfig()
