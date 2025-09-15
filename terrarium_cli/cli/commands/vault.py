"""
Vault command for the CLI tool.
"""

import argparse
import logging
import requests
import json
from typing import Dict, Any

from terrarium_cli.cli.commands.base import BaseCommand
from terrarium_cli.utils.system.shell import run_command, ShellError
from terrarium_cli.utils.colors import Colors

logger = logging.getLogger(__name__)


class VaultCommand(BaseCommand):
    """Command to manage Vault operations."""
    
    def run(self) -> int:
        """Run the vault command."""
        action = self.args.action
        
        if action == "init":
            return self._init_vault()
        elif action == "status":
            return self._check_vault_status()
        elif action == "secrets":
            return self._list_secrets()
        elif action == "get":
            return self._get_secret()
        elif action == "set":
            return self._set_secret()
        else:
            print(f"{Colors.error(f'Unknown action: {action}')}")
            return 1
    
    def _init_vault(self) -> int:
        """Initialize Vault with secrets."""
        try:
            print(f"{Colors.info('Initializing Vault...')}")
            
            # Check if Vault is accessible
            if not self._check_vault_accessible():
                print(f"{Colors.error('Vault is not accessible')}")
                return 1
            
            # Enable KV secrets engine
            self._enable_kv_secrets_engine()
            
            # Store secrets
            self._store_secrets()
            
            print(f"{Colors.success('Vault initialization completed')}")
            return 0
            
        except Exception as e:
            self.logger.error(f"Vault initialization failed: {e}")
            return 1
    
    def _check_vault_status(self) -> int:
        """Check Vault status."""
        try:
            print(f"{Colors.info('Checking Vault status...')}")
            
            if not self._check_vault_accessible():
                print(f"{Colors.error('Vault is not accessible')}")
                return 1
            
            # Get Vault status
            response = self._make_vault_request("GET", "/v1/sys/health")
            
            if response.status_code == 200:
                status = response.json()
                print(f"{Colors.success('Vault is healthy')}")
                print(f"  Version: {status.get('version', 'unknown')}")
                print(f"  Cluster: {status.get('cluster_name', 'unknown')}")
                print(f"  Sealed: {status.get('sealed', 'unknown')}")
                return 0
            else:
                print(f"{Colors.error(f'Vault health check failed: {response.status_code}')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to check Vault status: {e}")
            return 1
    
    def _list_secrets(self) -> int:
        """List Vault secrets."""
        try:
            print(f"{Colors.info('Listing Vault secrets...')}")
            
            if not self._check_vault_accessible():
                print(f"{Colors.error('Vault is not accessible')}")
                return 1
            
            # List secrets
            response = self._make_vault_request("GET", "/v1/secret/metadata?list=true")
            
            if response.status_code == 200:
                secrets = response.json()
                if "data" in secrets and "keys" in secrets["data"]:
                    print(f"{Colors.success('Available secrets:')}")
                    for key in secrets["data"]["keys"]:
                        print(f"  - {key}")
                else:
                    print(f"{Colors.warning('No secrets found')}")
                return 0
            else:
                print(f"{Colors.error(f'Failed to list secrets: {response.status_code}')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}")
            return 1
    
    def _get_secret(self) -> int:
        """Get a Vault secret."""
        try:
            secret_path = self.args.secret_path
            if not secret_path:
                print(f"{Colors.error('Secret path is required')}")
                return 1
            
            print(f"{Colors.info(f'Getting secret: {secret_path}')}")
            
            if not self._check_vault_accessible():
                print(f"{Colors.error('Vault is not accessible')}")
                return 1
            
            # Get secret
            response = self._make_vault_request("GET", f"/v1/secret/data/{secret_path}")
            
            if response.status_code == 200:
                secret = response.json()
                if "data" in secret and "data" in secret["data"]:
                    print(f"{Colors.success(f'Secret {secret_path}:')}")
                    for key, value in secret["data"]["data"].items():
                        print(f"  {key}: {value}")
                else:
                    print(f"{Colors.warning(f'Secret {secret_path} not found')}")
                return 0
            else:
                print(f"{Colors.error(f'Failed to get secret: {response.status_code}')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to get secret: {e}")
            return 1
    
    def _set_secret(self) -> int:
        """Set a Vault secret."""
        try:
            secret_path = self.args.secret_path
            secret_data = self.args.secret_data
            
            if not secret_path or not secret_data:
                print(f"{Colors.error('Secret path and data are required')}")
                return 1
            
            print(f"{Colors.info(f'Setting secret: {secret_path}')}")
            
            if not self._check_vault_accessible():
                print(f"{Colors.error('Vault is not accessible')}")
                return 1
            
            # Parse secret data
            try:
                data = json.loads(secret_data)
            except json.JSONDecodeError:
                print(f"{Colors.error('Secret data must be valid JSON')}")
                return 1
            
            # Set secret
            response = self._make_vault_request("POST", f"/v1/secret/data/{secret_path}", {"data": data})
            
            if response.status_code == 200:
                print(f"{Colors.success(f'Secret {secret_path} set successfully')}")
                return 0
            else:
                print(f"{Colors.error(f'Failed to set secret: {response.status_code}')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Failed to set secret: {e}")
            return 1
    
    def _check_vault_accessible(self) -> bool:
        """Check if Vault is accessible."""
        try:
            response = self._make_vault_request("GET", "/v1/sys/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _get_vault_url(self) -> str:
        """Get Vault URL."""
        return "http://localhost:8200"
    
    def _make_vault_request(self, method: str, endpoint: str, data: dict = None, timeout: int = 10) -> requests.Response:
        """Make a Vault API request with common headers."""
        url = f"{self._get_vault_url()}{endpoint}"
        headers = {
            "X-Vault-Token": "root",
            "Content-Type": "application/json"
        }
        
        if method.upper() == "GET":
            return requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            return requests.post(url, headers=headers, json=data, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    def _enable_kv_secrets_engine(self) -> None:
        """Enable KV secrets engine."""
        print(f"{Colors.info('Enabling KV secrets engine...')}")
        
        response = self._make_vault_request("POST", "/v1/sys/mounts/secret", {
            "type": "kv",
            "options": {
                "version": "2"
            }
        })
        
        if response.status_code == 204:
            print(f"{Colors.success('KV secrets engine enabled')}")
        else:
            print(f"{Colors.warning('KV secrets engine may already be enabled')}")
    
    def _store_secrets(self) -> None:
        """Store secrets from configuration file."""
        print(f"{Colors.info('Storing secrets from configuration file...')}")
        
        # Load secrets from configuration file
        secrets = self._load_secrets_from_file()
        
        for path, data in secrets.items():
            response = self._make_vault_request("POST", f"/v1/secret/data/{path}", {"data": data})
            
            if response.status_code == 200:
                print(f"{Colors.success(f'Stored secret: {path}')}")
            else:
                print(f"{Colors.error(f'Failed to store secret {path}: {response.status_code}')}")
        
        # Store TLS certificates if they exist
        self._store_tls_certificates()
    
    def _load_secrets_from_file(self) -> dict:
        """Load secrets from the vault-secrets.yml configuration file."""
        import yaml
        from pathlib import Path
        
        secrets_file = Path("configs/vault-secrets.yml")
        
        if not secrets_file.exists():
            print(f"{Colors.warning(f'Secrets file not found: {secrets_file}')}")
            print(f"{Colors.info('Using default hardcoded secrets...')}")
            return self._get_default_secrets()
        
        try:
            with open(secrets_file, 'r') as f:
                config = yaml.safe_load(f)
            
            if 'secrets' not in config:
                print(f"{Colors.warning('No secrets section found in configuration file')}")
                return self._get_default_secrets()
            
            print(f"{Colors.success(f'Loaded secrets from {secrets_file}')}")
            return config['secrets']
            
        except Exception as e:
            print(f"{Colors.warning(f'Failed to load secrets from file: {e}')}")
            print(f"{Colors.info('Using default hardcoded secrets...')}")
            return self._get_default_secrets()
    
    def _get_default_secrets(self) -> dict:
        """Get default hardcoded secrets as fallback."""
        return {
            "custom-client/config": {
                "api_key": "mock-api-key-12345",
                "database_url": "postgresql://user:pass@db:5432/app",
                "jwt_secret": "mock-jwt-secret-67890",
                "encryption_key": "mock-encryption-key-abcdef",
                "log_level": "INFO",
                "max_connections": "100"
            },
            "custom-client/external-apis": {
                "file_storage_url": "http://file-storage:9000",
                "logthon_url": "http://logthon:5000"
            },
            "terrarium/tls": {
                "cert": "mock-tls-cert",
                "key": "mock-tls-key"
            }
        }
    
    def _store_tls_certificates(self) -> None:
        """Store TLS certificates in Vault if they exist."""
        import base64
        from pathlib import Path
        
        cert_file = Path("terrarium_cli/certs/edge-terrarium.crt")
        key_file = Path("terrarium_cli/certs/edge-terrarium.key")
        
        if cert_file.exists() and key_file.exists():
            try:
                print(f"{Colors.info('Storing TLS certificates...')}")
                
                # Read and encode certificates
                with open(cert_file, 'rb') as f:
                    cert_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                with open(key_file, 'rb') as f:
                    key_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                # Store in Vault
                response = requests.post(
                    f"{self._get_vault_url()}/v1/secret/data/terrarium/tls",
                    headers={
                        "X-Vault-Token": "root",
                        "Content-Type": "application/json"
                    },
                    json={
                        "data": {
                            "cert": cert_b64,
                            "key": key_b64
                        }
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"{Colors.success('TLS certificates stored in Vault')}")
                else:
                    print(f"{Colors.error(f'Failed to store TLS certificates: {response.status_code}')}")
                    
            except Exception as e:
                print(f"{Colors.error(f'Failed to store TLS certificates: {e}')}")
        else:
            print(f"{Colors.warning('TLS certificates not found, skipping...')}")
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add vault command arguments."""
        subparsers = parser.add_subparsers(
            dest="action",
            help="Vault action to perform",
            required=True
        )
        
        # Init subcommand
        init_parser = subparsers.add_parser(
            "init",
            help="Initialize Vault with default secrets"
        )
        
        # Status subcommand
        status_parser = subparsers.add_parser(
            "status",
            help="Check Vault status"
        )
        
        # List secrets subcommand
        list_parser = subparsers.add_parser(
            "secrets",
            help="List Vault secrets"
        )
        
        # Get secret subcommand
        get_parser = subparsers.add_parser(
            "get",
            help="Get a Vault secret"
        )
        get_parser.add_argument(
            "secret_path",
            help="Path to the secret"
        )
        
        # Set secret subcommand
        set_parser = subparsers.add_parser(
            "set",
            help="Set a Vault secret"
        )
        set_parser.add_argument(
            "secret_path",
            help="Path to the secret"
        )
        set_parser.add_argument(
            "secret_data",
            help="Secret data as JSON"
        )
    
    def process_database_secrets(self, apps: list) -> None:
        """Process and store database secrets for all apps."""
        from terrarium_cli.core.infrastructure.database import DatabaseManager
        
        print(f"{Colors.info('Processing database secrets...')}")
        
        db_manager = DatabaseManager()
        
        for app in apps:
            if hasattr(app, 'databases') and app.databases:
                print(f"{Colors.info(f'Processing databases for {app.name}...')}")
                processed_dbs = db_manager.process_app_databases(app)
                
                if processed_dbs:
                    print(f"{Colors.success(f'Processed {len(processed_dbs)} databases for {app.name}')}")
                else:
                    print(f"{Colors.warning(f'No databases processed for {app.name}')}")
    
    def _store_database_secrets(self, app_name: str, db_name: str, credentials: dict) -> bool:
        """Store database credentials in Vault."""
        secret_path = f"{app_name}/database/{db_name}"
        response = self._make_vault_request("POST", f"/v1/secret/data/{secret_path}", {"data": credentials})
        
        if response.status_code == 200:
            print(f"{Colors.success(f'Stored database secrets: {secret_path}')}")
            return True
        else:
            print(f"{Colors.error(f'Failed to store database secrets: {secret_path}')}")
            return False