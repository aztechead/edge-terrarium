"""
Database utilities for password generation and Vault integration.
"""

import secrets
import string
import logging
import requests
from typing import Dict, Any, List
from terrarium_cli.config.app_loader import AppConfig, DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database creation, password generation, and Vault integration."""
    
    def __init__(self, vault_url: str = "http://localhost:8200", vault_token: str = "root"):
        """
        Initialize the database manager.
        
        Args:
            vault_url: Vault server URL
            vault_token: Vault authentication token
        """
        self.vault_url = vault_url
        self.vault_token = vault_token
    
    def generate_password(self, length: int = 32) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: Password length
            
        Returns:
            Generated password
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    def generate_database_credentials(self, app_name: str, db_config: DatabaseConfig) -> Dict[str, str]:
        """
        Generate database credentials for a database configuration.
        
        Args:
            app_name: Application name
            db_config: Database configuration
            
        Returns:
            Dictionary containing database credentials
        """
        username = f"{app_name}_{db_config.name}_user"
        password = self.generate_password()
        database_name = db_config.name
        
        return {
            "host": f"{app_name}-{db_config.name}-db",
            "port": "5432",
            "username": username,
            "password": password,
            "database_name": database_name,
            "url": f"postgresql://{username}:{password}@{app_name}-{db_config.name}-db:5432/{database_name}"
        }
    
    def store_database_secrets(self, app_name: str, db_config: DatabaseConfig, credentials: Dict[str, str]) -> bool:
        """
        Store database credentials in Vault.
        
        Args:
            app_name: Application name
            db_config: Database configuration
            credentials: Database credentials
            
        Returns:
            True if successful, False otherwise
        """
        try:
            secret_path = f"{app_name}/database/{db_config.name}"
            secret_data = {
                "host": credentials["host"],
                "port": credentials["port"],
                "username": credentials["username"],
                "password": credentials["password"],
                "database_name": credentials["database_name"],
                "url": credentials["url"]
            }
            
            response = self._make_vault_request("POST", f"/v1/secret/data/{secret_path}", {"data": secret_data})
            
            if response.status_code == 200:
                logger.info(f"Stored database secrets for {app_name}/{db_config.name}")
                return True
            else:
                logger.error(f"Failed to store database secrets for {app_name}/{db_config.name}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing database secrets for {app_name}/{db_config.name}: {e}")
            return False
    
    def process_app_databases(self, app: AppConfig) -> List[Dict[str, Any]]:
        """
        Process all databases for an application.
        
        Args:
            app: Application configuration
            
        Returns:
            List of database configurations with credentials
        """
        processed_dbs = []
        
        for db_config in app.databases:
            if not db_config.enabled:
                continue
                
            # Generate credentials
            credentials = self.generate_database_credentials(app.name, db_config)
            
            # Store in Vault
            if self.store_database_secrets(app.name, db_config, credentials):
                processed_dbs.append({
                    "config": db_config,
                    "credentials": credentials
                })
            else:
                logger.error(f"Failed to process database {db_config.name} for app {app.name}")
        
        return processed_dbs
    
    def _make_vault_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> requests.Response:
        """Make a Vault API request with common headers."""
        url = f"{self.vault_url}{endpoint}"
        headers = {
            "X-Vault-Token": self.vault_token,
            "Content-Type": "application/json"
        }
        
        if method.upper() == "GET":
            return requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            return requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")


def get_database_environment_variables(app_name: str, db_config: DatabaseConfig, credentials: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Generate environment variables for database access.
    
    Args:
        app_name: Application name
        db_config: Database configuration
        credentials: Database credentials
        
    Returns:
        List of environment variable dictionaries
    """
    db_type_upper = db_config.type.upper()
    
    return [
        {
            "name": f"{db_type_upper}_DB_HOST",
            "value": credentials["host"]
        },
        {
            "name": f"{db_type_upper}_DB_PORT",
            "value": credentials["port"]
        },
        {
            "name": f"{db_type_upper}_DB_USER",
            "value": credentials["username"]
        },
        {
            "name": f"{db_type_upper}_DB_PASSWORD",
            "value_from": f"vault:{app_name}/database/{db_config.name}#password"
        },
        {
            "name": f"{db_type_upper}_DB_NAME",
            "value": credentials["database_name"]
        },
        {
            "name": f"{db_type_upper}_DB_URL",
            "value_from": f"vault:{app_name}/database/{db_config.name}#url"
        }
    ]
