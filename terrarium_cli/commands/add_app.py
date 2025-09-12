"""
Add app command for the CLI tool.
"""

import argparse
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.dependencies import DependencyChecker

logger = logging.getLogger(__name__)


class AddAppCommand(BaseCommand):
    """Command to add a new application."""
    
    def __init__(self, args):
        super().__init__(args)
        self.templates_dir = Path(__file__).parent.parent / "templates" / "add_app"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.template_config = self._load_template_config()
    
    def _load_template_config(self) -> Dict[str, Any]:
        """Load template configuration."""
        try:
            config_file = self.templates_dir / "templates.yml"
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load template config: {e}")
            return {"templates": {"generic": {"dockerfile": "Dockerfile.j2", "app_config": "app-config.yml.j2", "readme": "README.md.j2"}}}
    
    def _check_dependencies(self, dependencies: list) -> bool:
        """Check if required dependencies are available."""
        dep_checker = DependencyChecker()
        if not dep_checker.check_all_dependencies(dependencies):
            print(f"\n{Colors.error('Please install the missing dependencies and try again.')}")
            return False
        return True
    
    def _prepare_template_context(self, app_info: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare common template context."""
        # Generate dependencies based on databases
        dependencies = []
        if "databases" in app_info and app_info["databases"]:
            for db in app_info["databases"]:
                if db.get("enabled", True):
                    # Add database as dependency using the simplified format: app_name-db
                    db_dependency = f"{app_info['name']}-db"
                    dependencies.append(db_dependency)
        
        return {
            "app_name": app_info["name"],
            "app_description": app_info["description"],
            "image_name": app_info["image_name"],
            "port": app_info["port"],
            "environment_vars": app_info["environment"],
            "routes": app_info["routes"],
            "volumes": app_info["volumes"],
            "databases": app_info.get("databases", []),
            "dependencies": dependencies
        }
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context."""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)
    
    def run(self) -> int:
        """Run the add-app command."""
        try:
            print(f"{Colors.info('Adding new application...')}")
            
            # Check dependencies
            if not self._check_dependencies(['python3', 'curl']):
                return 1
            
            # Get template selection
            template = self._get_template_selection()
            if not template:
                return 1
            
            # Get app information
            app_info = self._get_app_info(template)
            if not app_info:
                return 1
            
            # Create app directory
            if not self._create_app_directory(app_info):
                return 1
            
            # Create app configuration
            if not self._create_app_config(app_info):
                return 1
            
            # Create Dockerfile
            if not self._create_dockerfile(app_info):
                return 1
            
            # Create basic source structure
            if not self._create_source_structure(app_info):
                return 1
            
            print(f"{Colors.success(f'Application {app_info["name"]} created successfully!')}")
            print(f"\n{Colors.bold('Next steps:')}")
            print(f"  1. Add your source code to apps/{app_info['name']}/")
            print(f"  2. Update the Dockerfile if needed")
            print(f"  3. Run 'terrarium.py build' to build the image")
            print(f"  4. Run 'terrarium.py deploy' to deploy all apps")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to add app: {e}")
            return 1
    
    def _get_template_selection(self) -> str:
        """Get template selection from user."""
        print(f"\n{Colors.info('Available templates:')}")
        templates = self.template_config.get("templates", {})
        
        for i, (key, config) in enumerate(templates.items(), 1):
            description = config.get("description", key)
            print(f"  {i}. {key} - {description}")
        
        while True:
            try:
                choice = input(f"\nSelect template (1-{len(templates)}, default: 1): ").strip()
                if not choice:
                    choice = "1"
                
                choice_idx = int(choice) - 1
                template_keys = list(templates.keys())
                
                if 0 <= choice_idx < len(template_keys):
                    selected_template = template_keys[choice_idx]
                    print(f"{Colors.success(f'Selected template: {selected_template}')}")
                    return selected_template
                else:
                    print(f"{Colors.error(f'Please enter a number between 1 and {len(templates)}')}")
            except ValueError:
                print(f"{Colors.error('Please enter a valid number')}")
    
    def _get_app_info(self, template: str) -> Dict[str, Any]:
        """Get application information from user."""
        app_info = {}
        
        # App name
        app_name = input("Application name (e.g., my-service): ").strip()
        if not app_name:
            print(f"{Colors.error('App name is required')}")
            return None
        
        # Validate app name
        if not app_name.replace("-", "").replace("_", "").isalnum():
            print(f"{Colors.error('App name must contain only alphanumeric characters, hyphens, and underscores')}")
            return None
        
        # Check if app already exists
        if Path(f"apps/{app_name}").exists():
            print(f"{Colors.error(f'App {app_name} already exists')}")
            return None
        
        app_info["name"] = app_name
        
        # Description
        app_info["description"] = input("Application description: ").strip() or f"{app_name} service"
        
        # Port
        while True:
            try:
                port = input("Internal port (e.g., 8080): ").strip()
                if port:
                    app_info["port"] = int(port)
                    break
                else:
                    # Default to 8080 if no port provided
                    app_info["port"] = 8080
                    break
            except ValueError:
                print(f"{Colors.error('Port must be a number')}")
        
        # Docker image name
        app_info["image_name"] = input(f"Docker image name (default: edge-terrarium-{app_name}): ").strip()
        if not app_info["image_name"]:
            app_info["image_name"] = f"edge-terrarium-{app_name}"
        
        # Routes
        routes = []
        print(f"\n{Colors.info('Configure routing (press Enter to skip):')}")
        
        # Default route
        default_route = input(f"Default API route (default: /{app_name}/*): ").strip()
        if not default_route:
            default_route = f"/{app_name}/*"
        
        routes.append({
            "path": default_route,
            "target": "/",
            "strip_prefix": True
        })
        
        # Additional routes
        while True:
            additional_route = input("Additional route (e.g., /custom/* -> /custom/): ").strip()
            if not additional_route:
                break
            
            if " -> " in additional_route:
                path, target = additional_route.split(" -> ", 1)
                routes.append({
                    "path": path.strip(),
                    "target": target.strip(),
                    "strip_prefix": True
                })
            else:
                print(f"{Colors.warning('Route format should be: /path/* -> /target/')}")
        
        app_info["routes"] = routes
        
        # Environment variables
        env_vars = []
        print(f"\n{Colors.info('Environment variables (press Enter to skip):')}")
        
        while True:
            env_var = input("Environment variable (name=value or name=vault:path#key): ").strip()
            if not env_var:
                break
            
            if "=" in env_var:
                name, value = env_var.split("=", 1)
                env_vars.append({
                    "name": name.strip(),
                    "value": value.strip()
                })
            else:
                print(f"{Colors.warning('Environment variable format should be: name=value')}")
        
        app_info["environment"] = env_vars
        
        # Volumes
        volumes = []
        print(f"\n{Colors.info('Persistent volumes (press Enter to skip):')}")
        
        while True:
            volume = input("Volume (mount_path:size, e.g., /app/data:1Gi): ").strip()
            if not volume:
                break
            
            if ":" in volume:
                mount_path, size = volume.split(":", 1)
                volumes.append({
                    "name": f"{app_name}-data",
                    "mount_path": mount_path.strip(),
                    "size": size.strip(),
                    "access_mode": "ReadWriteOnce"
                })
            else:
                print(f"{Colors.warning('Volume format should be: mount_path:size')}")
        
        app_info["volumes"] = volumes
        
        # Database configuration
        databases = []
        print(f"\n{Colors.info('Database configuration (press Enter to skip):')}")
        
        while True:
            needs_db = input("Does this app need a database? (y/n): ").strip().lower()
            if needs_db in ['', 'n', 'no']:
                break
            elif needs_db in ['y', 'yes']:
                db_config = self._get_database_config(app_name)
                if db_config:
                    databases.append(db_config)
                break
            else:
                print(f"{Colors.warning('Please enter y/yes or n/no')}")
        
        app_info["databases"] = databases
        app_info["template"] = template
        
        return app_info
    
    def _get_database_config(self, app_name: str) -> Dict[str, Any]:
        """Get database configuration from user."""
        # Supported database types
        db_types = {
            "1": {"type": "postgres", "name": "PostgreSQL", "default_version": "15"},
            "2": {"type": "mysql", "name": "MySQL", "default_version": "8.0"},
            "3": {"type": "mongodb", "name": "MongoDB", "default_version": "7.0"},
            "4": {"type": "redis", "name": "Redis", "default_version": "7.2"}
        }
        
        print(f"\n{Colors.info('Supported database types:')}")
        for key, db_info in db_types.items():
            print(f"  {key}. {db_info['name']} (default version: {db_info['default_version']})")
        
        # Get database type selection
        while True:
            try:
                choice = input(f"\nSelect database type (1-{len(db_types)}): ").strip()
                if choice in db_types:
                    selected_db = db_types[choice]
                    break
                else:
                    print(f"{Colors.error(f'Please enter a number between 1 and {len(db_types)}')}")
            except KeyboardInterrupt:
                return None
        
        print(f"{Colors.success(f'Selected database: {selected_db["name"]}')}")
        
        # Database name
        db_name = input(f"Database name (default: {app_name}_db): ").strip()
        if not db_name:
            db_name = f"{app_name}_db"
        
        # Database version
        db_version = input(f"Database version (default: {selected_db['default_version']}): ").strip()
        if not db_version:
            db_version = selected_db['default_version']
        
        # Port forwarding
        port_forward = None
        if selected_db["type"] in ["postgres", "mysql", "mongodb"]:
            while True:
                port_input = input("Port forwarding (host port, press Enter to skip): ").strip()
                if not port_input:
                    break
                try:
                    port_forward = int(port_input)
                    if 1 <= port_forward <= 65535:
                        break
                    else:
                        print(f"{Colors.error('Port must be between 1 and 65535')}")
                except ValueError:
                    print(f"{Colors.error('Port must be a number')}")
        
        # Init scripts (for SQL databases)
        init_scripts = []
        if selected_db["type"] in ["postgres", "mysql"]:
            print(f"\n{Colors.info('Database initialization scripts (press Enter to skip):')}")
            while True:
                script_path = input("Init script path (e.g., init/schema.sql): ").strip()
                if not script_path:
                    break
                init_scripts.append(script_path)
        
        return {
            "enabled": True,
            "type": selected_db["type"],
            "name": db_name,
            "version": db_version,
            "init_scripts": init_scripts,
            "port_forward": port_forward
        }
    
    def _create_app_directory(self, app_info: Dict[str, Any]) -> bool:
        """Create app directory structure."""
        try:
            app_dir = Path(f"apps/{app_info['name']}")
            app_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"{Colors.success(f'Created directory: {app_dir}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create app directory: {e}')}")
            return False
    
    def _create_app_config(self, app_info: Dict[str, Any]) -> bool:
        """Create app configuration file."""
        try:
            template_name = self.template_config["templates"][app_info["template"]]["app_config"]
            context = self._prepare_template_context(app_info)
            
            config_content = self._render_template(template_name, context)
            
            config_file = Path(f"apps/{app_info['name']}/app-config.yml")
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            print(f"{Colors.success(f'Created configuration: {config_file}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create app config: {e}')}")
            return False
    
    
    def _create_dockerfile(self, app_info: Dict[str, Any]) -> bool:
        """Create Dockerfile."""
        try:
            template_name = self.template_config["templates"][app_info["template"]]["dockerfile"]
            context = {
                "app_name": app_info["name"],
                "port": app_info["port"]
            }
            
            dockerfile_content = self._render_template(template_name, context)
            
            dockerfile_path = Path(f"apps/{app_info['name']}/Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            print(f"{Colors.success(f'Created Dockerfile: {dockerfile_path}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create Dockerfile: {e}')}")
            return False
    
    def _create_source_structure(self, app_info: Dict[str, Any]) -> bool:
        """Create basic source structure."""
        try:
            app_dir = Path(f"apps/{app_info['name']}")
            
            # Create src directory
            src_dir = app_dir / "src"
            src_dir.mkdir(exist_ok=True)
            
            # Create README using template
            template_name = self.template_config["templates"][app_info["template"]]["readme"]
            context = self._prepare_template_context(app_info)
            
            readme_content = self._render_template(template_name, context)
            
            readme_path = app_dir / "README.md"
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            
            # Create additional files based on template
            self._create_template_specific_files(app_info, app_dir)
            
            print(f"{Colors.success(f'Created source structure: {app_dir}')}")
            return True
            
        except Exception as e:
            print(f"{Colors.error(f'Failed to create source structure: {e}')}")
            return False
    
    def _create_template_specific_files(self, app_info: Dict[str, Any], app_dir: Path) -> None:
        """Create template-specific files like requirements.txt for Python."""
        template = app_info["template"]
        databases = app_info.get("databases", [])
        
        if template == "python":
            # Create requirements.txt for Python
            requirements_content = """fastapi>=0.104.0
uvicorn[standard]>=0.24.0
"""
            
            # Add database dependencies if needed
            for db in databases:
                if db["type"] == "postgres":
                    requirements_content += "psycopg2-binary>=2.9.0\n"
                elif db["type"] == "mysql":
                    requirements_content += "pymysql>=1.1.0\n"
                elif db["type"] == "mongodb":
                    requirements_content += "pymongo>=4.6.0\n"
                elif db["type"] == "redis":
                    requirements_content += "redis>=5.0.0\n"
            
            requirements_path = app_dir / "requirements.txt"
            with open(requirements_path, 'w') as f:
                f.write(requirements_content)
            
            # Create main.py for Python
            main_py_content = self._generate_python_main(app_info)
            main_py_path = app_dir / "main.py"
            with open(main_py_path, 'w') as f:
                f.write(main_py_content)
            
            # Make main.py executable
            main_py_path.chmod(0o755)
        
        # Create database init scripts if configured
        if databases:
            self._create_database_init_scripts(app_info, app_dir)
    
    def _generate_python_main(self, app_info: Dict[str, Any]) -> str:
        """Generate Python main.py content based on app configuration."""
        databases = app_info.get("databases", [])
        has_database = len(databases) > 0
        
        # Base imports
        imports = ["import asyncio", "from fastapi import FastAPI, HTTPException"]
        if has_database:
            imports.extend([
                "import os",
                "from datetime import datetime",
                "from typing import List, Dict"
            ])
            
            # Add database-specific imports
            for db in databases:
                if db["type"] == "postgres":
                    imports.append("import psycopg2")
                elif db["type"] == "mysql":
                    imports.append("import pymysql")
                elif db["type"] == "mongodb":
                    imports.append("from pymongo import MongoClient")
                elif db["type"] == "redis":
                    imports.append("import redis")
        
        # Generate database configuration
        db_config = ""
        if has_database:
            db_config = f"""
# Database configuration from environment variables
DB_HOST = os.getenv("{databases[0]['type'].upper()}_DB_HOST", "{app_info['name']}-{databases[0]['name']}-db")
DB_PORT = os.getenv("{databases[0]['type'].upper()}_DB_PORT", "5432")
DB_USER = os.getenv("{databases[0]['type'].upper()}_DB_USER", "{app_info['name']}_{databases[0]['name']}_user")
DB_PASSWORD = os.getenv("{databases[0]['type'].upper()}_DB_PASSWORD", "default_password")
DB_NAME = os.getenv("{databases[0]['type'].upper()}_DB_NAME", "{databases[0]['name']}")
"""
        
        # Generate database connection function
        db_connection = ""
        if has_database and databases[0]["type"] == "postgres":
            db_connection = '''
def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
'''
        
        # Generate endpoints
        endpoints = f'''
@app.get("/")
async def root():
    return {{"message": "Hello from {app_info['name']}!"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}
'''
        
        if has_database:
            endpoints += f'''
@app.get("/db/test")
async def db_test():
    """Test database connectivity and return sample data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get database version
        cursor.execute("SELECT version()")
        db_version = cursor.fetchone()[0]
        
        # Get test messages
        cursor.execute("SELECT id, message, created_at FROM test_messages ORDER BY created_at DESC LIMIT 5")
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {{
            "status": "success",
            "database_version": db_version,
            "test_data": [
                {{
                    "id": msg[0],
                    "message": msg[1],
                    "created_at": msg[2].isoformat() if msg[2] else None
                }}
                for msg in messages
            ]
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database test failed: {{e}}")
'''
        
        # Generate main content
        main_content = f'''#!/usr/bin/env python3
"""
{app_info['name']} - {app_info['description']}
"""

{chr(10).join(imports)}

app = FastAPI(
    title="{app_info['name']}",
    description="{app_info['description']}",
    version="1.0.0"
)
{db_config}{db_connection}{endpoints}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={app_info['port']})
'''
        
        return main_content
    
    def _create_database_init_scripts(self, app_info: Dict[str, Any], app_dir: Path) -> None:
        """Create database initialization scripts."""
        databases = app_info.get("databases", [])
        
        for db in databases:
            if db.get("init_scripts"):
                # Create init directory
                init_dir = app_dir / "init"
                init_dir.mkdir(exist_ok=True)
                
                # Create schema.sql for SQL databases
                if db["type"] in ["postgres", "mysql"]:
                    schema_content = f"""-- {app_info['name']} Database Schema
-- This script creates the initial database schema

CREATE TABLE IF NOT EXISTS test_messages (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on created_at for better query performance
CREATE INDEX IF NOT EXISTS idx_test_messages_created_at ON test_messages(created_at);
"""
                    schema_path = init_dir / "schema.sql"
                    with open(schema_path, 'w') as f:
                        f.write(schema_content)
                    
                    # Create seed.sql
                    seed_content = f"""-- {app_info['name']} Database Seed Data
-- This script populates the database with initial test data

INSERT INTO test_messages (message) VALUES 
    ('Hello from {app_info['name']}!'),
    ('Database connectivity test successful'),
    ('This is a test message from the seed script');
"""
                    seed_path = init_dir / "seed.sql"
                    with open(seed_path, 'w') as f:
                        f.write(seed_content)
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add add-app command arguments."""
        parser.add_argument(
            "--template",
            choices=["python", "node", "go", "rust", "generic"],
            default="generic",
            help="Application template to use (default: generic)"
        )
        
        parser.add_argument(
            "--interactive",
            action="store_true",
            default=True,
            help="Use interactive mode (default: true)"
        )
