"""
NGINX Configuration Generator
Generates NGINX configuration files from templates and app configurations.
"""

import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import List
from terrarium_cli.config.loaders.app_loader import AppLoader, AppConfig


class NginxConfigGenerator:
    """Generates NGINX configuration files from templates."""
    
    def __init__(self):
        self.app_loader = AppLoader()
        self.template_dir = Path(__file__).parent.parent.parent.parent / "apps" / "nginx"
        self.output_dir = Path("configs") / "docker" / "nginx"
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_configs(self) -> None:
        """Generate all NGINX configuration files."""
        apps = self.app_loader.load_apps()
        
        # Generate main nginx.conf
        self._generate_nginx_conf()
        
        # Generate server configuration
        self._generate_server_conf(apps)
        
        # Generate K3s ConfigMap
        self._generate_k3s_configmap()
    
    def _generate_nginx_conf(self) -> None:
        """Generate the main nginx.conf file."""
        template = self.jinja_env.get_template("nginx.conf.template")
        content = template.render()
        
        output_file = self.output_dir / "nginx.conf"
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"Generated {output_file}")
    
    def _generate_server_conf(self, apps: List[AppConfig]) -> None:
        """Generate the server configuration file."""
        template = self.jinja_env.get_template("server.conf.template")
        content = template.render(apps=apps)
        
        output_file = self.output_dir / "server.conf"
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"Generated {output_file}")
    
    def _generate_k3s_configmap(self) -> None:
        """Generate the K3s ConfigMap for nginx configuration."""
        # Read the generated nginx.conf and server.conf files
        nginx_conf_file = self.output_dir / "nginx.conf"
        server_conf_file = self.output_dir / "server.conf"
        
        with open(nginx_conf_file, 'r') as f:
            nginx_conf = f.read()
        
        with open(server_conf_file, 'r') as f:
            server_conf = f.read()
        
        # Generate ConfigMap
        template = self.jinja_env.get_template("k3s-configmap-nginx.yaml.template")
        content = template.render(
            nginx_conf=nginx_conf,
            server_conf=server_conf
        )
        
        output_file = Path("configs") / "k3s" / "nginx-configmap.yaml"
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"Generated {output_file}")
