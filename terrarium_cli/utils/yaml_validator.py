"""
YAML validation utilities for app-config.yml files.
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from terrarium_cli.utils.colors import Colors

logger = logging.getLogger(__name__)


class YAMLValidationError(Exception):
    """Exception raised when YAML validation fails."""
    pass


class YAMLValidator:
    """Validates YAML configuration files for syntax and structure."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_app_config(self, config_file: Path) -> Tuple[bool, List[str], List[str]]:
        """
        Validate an app-config.yml file.
        
        Args:
            config_file: Path to the app-config.yml file
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        if not config_file.exists():
            self.errors.append(f"Config file not found: {config_file}")
            return False, self.errors, self.warnings
        
        # Validate YAML syntax
        if not self._validate_yaml_syntax(config_file):
            return False, self.errors, self.warnings
        
        # Load and validate structure
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                self.errors.append(f"Config file must contain a YAML object, got {type(data).__name__}")
                return False, self.errors, self.warnings
            
            # Validate required fields
            self._validate_required_fields(data, config_file)
            
            # Validate field types and values
            self._validate_field_types(data, config_file)
            
            # Validate routes structure
            self._validate_routes(data, config_file)
            
            # Validate database configuration
            self._validate_databases(data, config_file)
            
        except Exception as e:
            self.errors.append(f"Failed to load config file: {e}")
            return False, self.errors, self.warnings
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_yaml_syntax(self, config_file: Path) -> bool:
        """Validate YAML syntax."""
        try:
            with open(config_file, 'r') as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error in {config_file.name}: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading {config_file.name}: {e}")
            return False
    
    def _validate_required_fields(self, data: Dict[str, Any], config_file: Path) -> None:
        """Validate required fields are present."""
        required_fields = ['name', 'description', 'docker', 'runtime']
        
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required field '{field}' in {config_file.name}")
    
    def _validate_field_types(self, data: Dict[str, Any], config_file: Path) -> None:
        """Validate field types and basic structure."""
        # Validate name
        if 'name' in data and not isinstance(data['name'], str):
            self.errors.append(f"Field 'name' must be a string in {config_file.name}")
        
        # Validate docker config
        if 'docker' in data:
            if not isinstance(data['docker'], dict):
                self.errors.append(f"Field 'docker' must be an object in {config_file.name}")
            else:
                # Check if this is a pre-built image (no build_context)
                is_prebuilt = 'build_context' not in data['docker'] or not data['docker'].get('build_context')
                
                if is_prebuilt:
                    # For pre-built images, only image_name and tag are required
                    docker_required = ['image_name', 'tag']
                else:
                    # For built images, all fields are required
                    docker_required = ['build_context', 'dockerfile', 'image_name', 'tag']
                
                for field in docker_required:
                    if field not in data['docker']:
                        self.errors.append(f"Missing required docker field '{field}' in {config_file.name}")
        
        # Validate runtime config
        if 'runtime' in data:
            if not isinstance(data['runtime'], dict):
                self.errors.append(f"Field 'runtime' must be an object in {config_file.name}")
            else:
                if 'port' in data['runtime'] and not isinstance(data['runtime']['port'], int):
                    self.errors.append(f"Field 'runtime.port' must be an integer in {config_file.name}")
                
                if 'ssl_port' in data['runtime'] and not isinstance(data['runtime']['ssl_port'], int):
                    self.errors.append(f"Field 'runtime.ssl_port' must be an integer in {config_file.name}")
        
        # Validate routes
        if 'routes' in data and not isinstance(data['routes'], list):
            self.errors.append(f"Field 'routes' must be a list in {config_file.name}")
        
        # Validate databases
        if 'databases' in data and not isinstance(data['databases'], list):
            self.errors.append(f"Field 'databases' must be a list in {config_file.name}")
    
    def _validate_routes(self, data: Dict[str, Any], config_file: Path) -> None:
        """Validate routes configuration."""
        if 'routes' not in data:
            return
        
        routes = data['routes']
        if not isinstance(routes, list):
            return
        
        for i, route in enumerate(routes):
            if not isinstance(route, dict):
                self.errors.append(f"Route {i} must be an object in {config_file.name}")
                continue
            
            # Check required route fields
            required_route_fields = ['path', 'target', 'strip_prefix']
            for field in required_route_fields:
                if field not in route:
                    self.errors.append(f"Route {i} missing required field '{field}' in {config_file.name}")
            
            # Validate field types
            if 'path' in route and not isinstance(route['path'], str):
                self.errors.append(f"Route {i} 'path' must be a string in {config_file.name}")
            
            if 'target' in route and not isinstance(route['target'], str):
                self.errors.append(f"Route {i} 'target' must be a string in {config_file.name}")
            
            if 'strip_prefix' in route and not isinstance(route['strip_prefix'], bool):
                self.errors.append(f"Route {i} 'strip_prefix' must be a boolean in {config_file.name}")
    
    def _validate_databases(self, data: Dict[str, Any], config_file: Path) -> None:
        """Validate database configuration."""
        if 'databases' not in data:
            return
        
        databases = data['databases']
        if not isinstance(databases, list):
            return
        
        # Check if database dependencies are properly configured
        app_name = data.get('name', 'unknown')
        expected_dependencies = []
        
        for i, db in enumerate(databases):
            if not isinstance(db, dict):
                self.errors.append(f"Database {i} must be an object in {config_file.name}")
                continue
            
            # Check required database fields
            required_db_fields = ['name', 'type', 'enabled']
            for field in required_db_fields:
                if field not in db:
                    self.errors.append(f"Database {i} missing required field '{field}' in {config_file.name}")
            
            # Validate field types
            if 'name' in db and not isinstance(db['name'], str):
                self.errors.append(f"Database {i} 'name' must be a string in {config_file.name}")
            
            if 'type' in db and not isinstance(db['type'], str):
                self.errors.append(f"Database {i} 'type' must be a string in {config_file.name}")
            
            if 'enabled' in db and not isinstance(db['enabled'], bool):
                self.errors.append(f"Database {i} 'enabled' must be a boolean in {config_file.name}")
            
            # Validate database type
            if 'type' in db and db['type'] not in ['postgresql', 'postgres', 'mysql', 'mongodb', 'redis']:
                self.warnings.append(f"Database {i} has unsupported type '{db['type']}' in {config_file.name}")
            
            # Check if database dependency is included
            if db.get('enabled', True):
                expected_dependency = f"{app_name}-db"
                expected_dependencies.append(expected_dependency)
        
        # Validate that database dependencies are included in dependencies list
        if expected_dependencies:
            dependencies = data.get('dependencies', [])
            if not isinstance(dependencies, list):
                self.warnings.append(f"App has databases but 'dependencies' is not a list in {config_file.name}")
            else:
                for expected_dep in expected_dependencies:
                    if expected_dep not in dependencies:
                        self.warnings.append(f"Database dependency '{expected_dep}' should be added to dependencies list in {config_file.name}")


def validate_all_app_configs(apps_dir: Path) -> Tuple[bool, Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Validate all app-config.yml files in the apps directory.
    
    Args:
        apps_dir: Path to the apps directory
        
    Returns:
        Tuple of (all_valid, errors_by_file, warnings_by_file)
    """
    validator = YAMLValidator()
    all_valid = True
    errors_by_file = {}
    warnings_by_file = {}
    
    if not apps_dir.exists():
        print(f"{Colors.error(f'Apps directory not found: {apps_dir}')}")
        return False, {}, {}
    
    for app_dir in apps_dir.iterdir():
        if not app_dir.is_dir():
            continue
        
        config_file = app_dir / "app-config.yml"
        if not config_file.exists():
            continue
        
        is_valid, errors, warnings = validator.validate_app_config(config_file)
        
        if not is_valid:
            all_valid = False
        
        if errors:
            errors_by_file[config_file.name] = errors
        if warnings:
            warnings_by_file[config_file.name] = warnings
    
    return all_valid, errors_by_file, warnings_by_file


def print_validation_results(all_valid: bool, errors_by_file: Dict[str, List[str]], 
                           warnings_by_file: Dict[str, List[str]]) -> None:
    """Print validation results in a user-friendly format."""
    if all_valid and not warnings_by_file:
        print(f"{Colors.success('✓ All app-config.yml files are valid!')}")
        return
    
    if errors_by_file:
        print(f"\n{Colors.error('❌ YAML Validation Errors:')}")
        for filename, errors in errors_by_file.items():
            print(f"\n{Colors.error(f'  {filename}:')}")
            for error in errors:
                print(f"    • {error}")
    
    if warnings_by_file:
        print(f"\n{Colors.warning('⚠️  YAML Validation Warnings:')}")
        for filename, warnings in warnings_by_file.items():
            print(f"\n{Colors.warning(f'  {filename}:')}")
            for warning in warnings:
                print(f"    • {warning}")
    
    if not all_valid:
        print(f"\n{Colors.error('Please fix the errors above before deploying.')}")
    elif warnings_by_file:
        print(f"\n{Colors.warning('Warnings above should be reviewed but will not prevent deployment.')}")
