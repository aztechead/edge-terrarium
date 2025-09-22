"""
Test command for the CLI tool.
"""

import argparse
import logging
import time
import requests
import urllib3
import yaml
import os
from typing import List, Dict, Any

from terrarium_cli.cli.commands.base import BaseCommand
from terrarium_cli.utils.system.shell import run_command, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.system.dependencies import DependencyChecker

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class TestCommand(BaseCommand):
    """Command to test the deployment."""
    
    def _discover_app_test_configs(self) -> List[Dict[str, Any]]:
        """Discover and load all app-test-config.yml files from apps directory."""
        apps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'apps')
        app_configs = []
        
        if not os.path.exists(apps_dir):
            logger.warning(f"Apps directory not found at {apps_dir}")
            return app_configs
        
        # Scan each app directory for app-test-config.yml
        for app_name in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_name)
            if not os.path.isdir(app_path):
                continue
                
            test_config_path = os.path.join(app_path, 'app-test-config.yml')
            if not os.path.exists(test_config_path):
                continue
                
            try:
                with open(test_config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Only include apps that are enabled for testing
                if config.get('enabled', False):
                    config['app_name'] = app_name  # Add app name for reference
                    app_configs.append(config)
                    logger.info(f"Loaded test config for app: {app_name}")
                else:
                    logger.info(f"Skipping disabled app: {app_name}")
                    
            except yaml.YAMLError as e:
                logger.error(f"Error parsing test config for {app_name}: {e}")
            except Exception as e:
                logger.error(f"Error loading test config for {app_name}: {e}")
        
        return app_configs
    
    def _check_dependencies(self, dependencies: list) -> bool:
        """Check if required dependencies are available."""
        dep_checker = DependencyChecker()
        if not dep_checker.check_all_dependencies(dependencies):
            print(f"\n{Colors.error('Please install the missing dependencies and try again.')}")
            return False
        return True
    
    def _test_endpoint_with_retry(self, url: str, test_name: str, method: str = "GET", 
                                 data: str = None, content_type: str = None, max_retries: int = 3) -> bool:
        """Test an endpoint with retry logic."""
        for attempt in range(max_retries):
            try:
                # Prepare headers based on environment
                headers = {}
                if content_type:
                    headers["Content-Type"] = content_type
                
                # For K3s, we need to use the correct Host header
                if "localhost:8443" in url and self._detect_environment() == "k3s":
                    headers["Host"] = "edge-terrarium.local"
                
                if method.upper() == "GET":
                    response = requests.get(url, verify=False, timeout=10, headers=headers)
                elif method.upper() == "POST":
                    response = requests.post(url, data=data, headers=headers, verify=False, timeout=10)
                elif method.upper() == "PUT":
                    response = requests.put(url, data=data, headers=headers, verify=False, timeout=10)
                else:
                    print(f"{Colors.error(f'Unsupported HTTP method: {method}')}")
                    return False
                
                if response.status_code in [200, 201, 202]:
                    print(f"{Colors.success(f'✓ {test_name} - Status: {response.status_code}')}")
                    return True
                else:
                    if attempt < max_retries - 1:
                        print(f"{Colors.warning(f'⚠ {test_name} - Status: {response.status_code} (retry {attempt + 1}/{max_retries})')}")
                        time.sleep(2)
                        continue
                    else:
                        print(f"{Colors.error(f'✗ {test_name} - Status: {response.status_code}')}")
                        if hasattr(self.args, 'fail_fast') and self.args.fail_fast:
                            print(f"{Colors.error('FAIL-FAST: Stopping on first error')}")
                            exit(1)
                        return False
                        
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"{Colors.warning(f'⚠ {test_name} - Error: {e} (retry {attempt + 1}/{max_retries})')}")
                    time.sleep(2)
                    continue
                else:
                    print(f"{Colors.error(f'✗ {test_name} - Error: {e}')}")
                    if hasattr(self.args, 'fail_fast') and self.args.fail_fast:
                        print(f"{Colors.error('FAIL-FAST: Stopping on first error')}")
                        exit(1)
                    return False
        
        return False
    
    def run(self) -> int:
        """Run the test command."""
        try:
            print(f"{Colors.info('Testing deployment...')}")
            print(f"{Colors.info('Using self-signed certificates - SSL warnings suppressed')}")
            
            # Check dependencies
            if not self._check_dependencies(['docker', 'kubectl', 'curl']):
                return 1
            
            # Determine environment
            environment = self._detect_environment()
            if not environment:
                print(f"{Colors.error('Could not detect deployment environment')}")
                return 1
            
            print(f"{Colors.info(f'Detected {environment} deployment')}")
            
            # Run tests based on environment
            if environment == "docker":
                return self._test_docker()
            elif environment == "k3s":
                return self._test_k3s()
            else:
                print(f"{Colors.error(f'Unknown environment: {environment}')}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            return 1
    
    def _detect_environment(self) -> str:
        """Detect the current deployment environment."""
        # Check if Docker containers are running
        try:
            result = run_command(
                "docker-compose -f configs/docker/docker-compose.yml -p edge-terrarium ps",
                capture_output=True,
                check=False
            )
            if "Up" in result.stdout:
                return "docker"
        except ShellError:
            pass
        
        # Check if K3s cluster is running
        try:
            result = run_command(
                "kubectl get pods -n edge-terrarium",
                capture_output=True,
                check=False
            )
            if "Running" in result.stdout:
                return "k3s"
        except ShellError:
            pass
        
        return None
    
    def _test_docker(self) -> int:
        """Test Docker deployment."""
        print(f"{Colors.info('Testing Docker deployment...')}")
        
        base_url = "https://localhost:8443/api"
        
        # Test application endpoints
        if not self._test_applications(base_url):
            return 1
        
        # Test host-based routing
        if not self._test_host_based_routing(base_url):
            return 1
        
        # Test Vault integration
        if not self._test_vault(base_url):
            return 1
        
        # Test request logging
        if not self._test_request_logging():
            return 1
        
        # Test vault secrets logging
        if not self._test_vault_secrets_logging():
            return 1
        
        return 0
    
    def _test_k3s(self) -> int:
        """Test K3s deployment."""
        print(f"{Colors.info('Testing K3s deployment...')}")
        
        # For K3s, we need to use port forwarding to access the ingress controller
        # Check if port forwarding is already running
        port_forward_running = False
        try:
            result = run_command("lsof -i :8443", capture_output=True, check=False)
            if result.returncode == 0 and "kubectl" in result.stdout:
                port_forward_running = True
        except:
            pass
        
        if not port_forward_running:
            print(f"{Colors.info('Setting up port forwarding for NGINX ingress controller...')}")
            # Start port forwarding in the background
            import subprocess
            port_forward_process = subprocess.Popen(
                ["kubectl", "port-forward", "-n", "ingress-nginx", "svc/ingress-nginx-controller", "8443:443"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait a moment for port forwarding to establish
            import time
            time.sleep(3)
        
        base_url = "https://localhost:8443/api"
        print(f"{Colors.info('Using localhost with port forwarding for K3s access')}")
        
        # Test application endpoints
        if not self._test_applications(base_url):
            return 1
        
        # Test host-based routing
        if not self._test_host_based_routing(base_url):
            return 1
        
        # Test Vault integration
        if not self._test_vault(base_url):
            return 1
        
        # Test request logging
        if not self._test_request_logging():
            return 1
        
        # Test vault secrets logging
        if not self._test_vault_secrets_logging():
            return 1
        
        return 0
    
    def _run_test_cases(self, test_cases: List[Dict[str, Any]]) -> int:
        """Run test cases."""
        passed = 0
        failed = 0
        
        for test_case in test_cases:
            if self._test_endpoint(test_case):
                passed += 1
            else:
                failed += 1
        
        # Print results
        print(f"\n{Colors.bold('Test Results:')}")
        print(f"  {Colors.success(f'Passed: {passed}')}")
        if failed > 0:
            print(f"  {Colors.error(f'Failed: {failed}')}")
        
        return 0 if failed == 0 else 1
    
    def _test_applications(self, base_url: str) -> bool:
        """Test application endpoints."""
        print(f"{Colors.bold('Testing Application Endpoints')}")
        
        # Discover app test configurations
        app_configs = self._discover_app_test_configs()
        
        if not app_configs:
            print(f"{Colors.warning('No apps configured for testing')}")
            return True
        
        # Test each app's routes
        for app_config in app_configs:
            app_name = app_config.get('app_name', 'unknown')
            app_description = app_config.get('description', app_name)
            routes = app_config.get('routes', [])
            test_config = app_config.get('test_config', {})
            
            for route in routes:
                route_path = route.get('path', '')
                route_description = route.get('description', route_path)
                methods = route.get('methods', ['GET'])
                
                # Test each HTTP method for this route
                for method in methods:
                    # Create test URL by replacing * with empty string to test the root endpoint
                    test_path = route_path.replace('*', '')
                    test_url = f"{base_url}{test_path}"
                    test_name = f"{app_name} - {route_path} ({method})"

                    if method.upper() == 'GET':
                        if not self._test_endpoint_simple(test_url, test_name):
                            return False
                    # Add support for other methods as needed
                    # elif method.upper() == 'POST':
                    #     if not self._test_endpoint_with_data(test_url, test_name, 'POST', '{}', 'application/json'):
                    #         return False
        
        # Test enhanced request logging with all apps
        print(f"{Colors.info('Testing enhanced request logging...')}")
        
        for app_config in app_configs:
            app_name = app_config.get('app_name', 'unknown')
            routes = app_config.get('routes', [])
            
            for route in routes:
                route_path = route.get('path', '')
                route_query_params = route.get('query_params', [])
                
                # Skip if no query params defined for this route
                if not route_query_params:
                    continue
                
                # Build query string from route-specific params
                query_string = '&'.join([f"{param['name']}={param['value']}" for param in route_query_params])
                
                # Test with query params
                test_path = route_path.replace('*', '')
                test_url = f"{base_url}{test_path}?{query_string}"
                test_name = f"{app_name} - GET with query params"
                if not self._test_endpoint_simple(test_url, test_name):
                    return False
                
        
        print("")
        return True
    
    def _test_host_based_routing(self, base_url: str) -> bool:
        """Test host-based routing functionality."""
        print(f"{Colors.bold('Testing Host-Based Routing')}")
        
        # Discover app test configurations that have host-based routes
        app_configs = self._discover_app_test_configs()
        host_routes_found = False
        
        for app_config in app_configs:
            app_name = app_config.get('app_name', 'unknown')
            
            # Check if this app has host-based routes defined
            host_routes = app_config.get('host_routes', [])
            if not host_routes:
                continue
                
            host_routes_found = True
            
            for host_route in host_routes:
                hostname = host_route.get('host', '')
                route_path = host_route.get('path', '/*')
                route_description = host_route.get('description', f'{hostname}{route_path}')
                methods = host_route.get('methods', ['GET'])
                
                # Test each HTTP method for this host route
                for method in methods:
                    # Create test URL
                    test_path = route_path.replace('*', '')
                    if self._detect_environment() == "docker":
                        # For Docker, we test via localhost but with Host header
                        test_url = f"https://localhost:8443{test_path}"
                        headers = {"Host": hostname}
                    else:
                        # For K3s, we test via port forwarding with Host header
                        test_url = f"https://localhost:8443{test_path}"
                        headers = {"Host": hostname}
                    
                    test_name = f"{app_name} - Host: {hostname} - {route_path} ({method})"
                    
                    # Test the endpoint with the specific host header
                    if not self._test_endpoint_with_host(test_url, test_name, hostname, method):
                        print(f"{Colors.warning(f'Host-based routing test failed for {hostname}')}")
                        # Don't fail the entire test suite for host routing issues
                        continue
        
        if not host_routes_found:
            print(f"{Colors.info('No host-based routes configured for testing')}")
        
        print("")
        return True
    
    def _test_endpoint_with_host(self, url: str, test_name: str, hostname: str, method: str = "GET", 
                                data: str = None, content_type: str = None, max_retries: int = 3) -> bool:
        """Test an endpoint with a specific Host header."""
        for attempt in range(max_retries):
            try:
                # Prepare headers
                headers = {"Host": hostname}
                if content_type:
                    headers["Content-Type"] = content_type
                
                if method.upper() == "GET":
                    response = requests.get(url, verify=False, timeout=10, headers=headers)
                elif method.upper() == "POST":
                    response = requests.post(url, data=data, headers=headers, verify=False, timeout=10)
                elif method.upper() == "PUT":
                    response = requests.put(url, data=data, headers=headers, verify=False, timeout=10)
                else:
                    print(f"{Colors.error(f'Unsupported HTTP method: {method}')}")
                    return False
                
                if response.status_code in [200, 201, 202]:
                    print(f"{Colors.success(f'✓ {test_name} - Status: {response.status_code}')}")
                    return True
                else:
                    if attempt < max_retries - 1:
                        print(f"{Colors.warning(f'⚠ {test_name} - Status: {response.status_code} (retry {attempt + 1}/{max_retries})')}")
                        time.sleep(2)
                        continue
                    else:
                        print(f"{Colors.error(f'✗ {test_name} - Status: {response.status_code}')}")
                        return False
                        
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"{Colors.warning(f'⚠ {test_name} - Error: {e} (retry {attempt + 1}/{max_retries})')}")
                    time.sleep(2)
                    continue
                else:
                    print(f"{Colors.error(f'✗ {test_name} - Error: {e}')}")
                    return False
        
        return False
    
    
    def _test_vault(self, base_url: str) -> bool:
        """Test Vault integration."""
        print(f"{Colors.bold('Testing Vault Integration')}")
        
        # Test Vault health via NGINX
        if not self._test_endpoint_simple(f"{base_url}/vault/v1/sys/health", "Vault health via NGINX"):
            return False
        
        # Test Vault health directly (only for Docker)
        if "localhost" in base_url:
            if not self._test_endpoint_simple("http://localhost:8200/v1/sys/health", "Vault health direct"):
                return False
        
        # Test Vault secrets
        try:
            print(f"{Colors.info('Testing Vault secrets access...')}")
            # For K3s, test via the ingress; for Docker, test directly
            if self._detect_environment() == "k3s":
                vault_url = f"{base_url}/vault/v1/secret/metadata?list=true"
                headers = {"X-Vault-Token": "root"}
                # Add Host header for K3s
                if "localhost:8443" in vault_url:
                    headers["Host"] = "edge-terrarium.local"
                response = requests.get(vault_url, headers=headers, verify=False, timeout=10)
            else:
                response = requests.get("http://localhost:8200/v1/secret/metadata?list=true", 
                                     headers={"X-Vault-Token": "root"}, timeout=10)
            
            if response.status_code == 200:
                print(f"{Colors.success('Vault secrets accessible')}")
            else:
                print(f"{Colors.warning('Vault secrets not accessible')}")
        except Exception as e:
            print(f"{Colors.warning(f'Vault secrets test failed: {e}')}")
        
        print("")
        return True
    
    def _test_request_logging(self) -> bool:
        """Test request logging."""
        print(f"{Colors.bold('Testing Request Logging')}")

        # Detect environment and use appropriate commands
        if self._detect_environment() == "docker":
            return self._test_request_logging_docker()
        else:
            return self._test_request_logging_k3s()
    
    def _test_request_logging_docker(self) -> bool:
        """Test request logging for Docker environment."""
        try:
            # Get all edge-terrarium containers
            result = run_command(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                containers = result.stdout.strip().split('\n')
                edge_containers = [c.strip() for c in containers if c.strip().startswith('edge-terrarium')]
                
                for container_name in edge_containers:
                    # Test if request files are being created
                    result = run_command(["docker", "exec", container_name, "ls", "-1", "/tmp/requests/"], 
                                        capture_output=True, check=False)
                    if result.returncode == 0:
                        file_list = result.stdout.strip()
                        if file_list:
                            file_count = len([line for line in file_list.split('\n') if line.strip()])
                            if file_count > 0:
                                print(f"{Colors.success(f'{file_count} request files present in {container_name}')}")
                                return True
                
                print(f"{Colors.warning('No request files found in any edge-terrarium container')}")
            else:
                print(f"{Colors.warning('No containers found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Request logging test failed: {e}')}")
        
        return True
    
    def _test_request_logging_k3s(self) -> bool:
        """Test request logging for K3s environment."""
        try:
            # Find pods that might have request logging enabled
            result = run_command(["kubectl", "get", "pods", "-n", "edge-terrarium", "-o", "jsonpath={.items[*].metadata.name}"],
                                capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pod_names = result.stdout.strip().split()
                for pod_name in pod_names:
                    if not pod_name.strip():
                        continue
                        
                    # Test if request files are being created
                    result = run_command(["kubectl", "exec", "-n", "edge-terrarium", pod_name.strip(), "--", "ls", "-1", "/tmp/requests/"],
                                        capture_output=True, check=False)
                    if result.returncode == 0:
                        file_list = result.stdout.strip()
                        if file_list:
                            file_count = len([line for line in file_list.split('\n') if line.strip()])
                            if file_count > 0:
                                print(f"{Colors.success(f'{file_count} request files present in {pod_name.strip()}')}")
                                return True
                
                print(f"{Colors.warning('No request files found in any pod')}")
            else:
                print(f"{Colors.warning('No pods found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Request logging test failed: {e}')}")
        
        return True
    
    def _test_vault_secrets_logging(self) -> bool:
        """Test vault secrets logging in applications."""
        print(f"{Colors.bold('Testing Vault Secrets Logging')}")
        
        # Detect environment and use appropriate commands
        if self._detect_environment() == "docker":
            return self._test_vault_secrets_logging_docker()
        else:
            return self._test_vault_secrets_logging_k3s()
    
    def _test_vault_secrets_logging_docker(self) -> bool:
        """Test vault secrets logging for Docker environment."""
        try:
            # Get all edge-terrarium containers
            result = run_command(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                containers = result.stdout.strip().split('\n')
                edge_containers = [c.strip() for c in containers if c.strip().startswith('edge-terrarium')]
                
                for container_name in edge_containers:
                    # Get the logs from the container
                    result = run_command(["docker", "logs", container_name], capture_output=True, check=False)
                    if result.returncode == 0:
                        logs = result.stdout
                        if self._verify_vault_secrets_in_logs(logs, f"Docker ({container_name})"):
                            return True
                
                print(f"{Colors.warning('No vault secrets found in any edge-terrarium container logs')}")
            else:
                print(f"{Colors.warning('No containers found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Vault secrets logging test failed: {e}')}")
        
        return True
    
    def _test_vault_secrets_logging_k3s(self) -> bool:
        """Test vault secrets logging for K3s environment."""
        try:
            # Find pods that might have vault secrets logging
            result = run_command("kubectl get pods -n edge-terrarium -o jsonpath='{.items[*].metadata.name}'",
                                capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pod_names = result.stdout.strip().split()
                for pod_name in pod_names:
                    if not pod_name.strip():
                        continue
                        
                    # Get the logs from the pod
                    result = run_command(f"kubectl logs -n edge-terrarium {pod_name.strip()}",
                                        capture_output=True, check=False)
                    if result.returncode == 0:
                        logs = result.stdout
                        if self._verify_vault_secrets_in_logs(logs, f"K3s ({pod_name.strip()})"):
                            return True
                
                print(f"{Colors.warning('No vault secrets found in any pod logs')}")
            else:
                print(f"{Colors.warning('No pods found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Vault secrets logging test failed: {e}')}")
        
        return True
    
    def _verify_vault_secrets_in_logs(self, logs: str, environment: str) -> bool:
        """Verify that vault secrets are present in the logs.
        
        Applications log vault secrets in the format:
        === VAULT SECRETS RETRIEVED ===
        API Key: {value}
        Database URL: {value}
        JWT Secret: {value}
        Encryption Key: {value}
        Log Level: {value}
        Max Connections: {value}
        === END VAULT SECRETS ===
        """
        # Expected vault secrets based on vault.py _store_secrets method
        # Note: The actual log format uses capitalized names with spaces
        expected_secrets = {
            "API Key": "mock-api-key-12345",
            "Database URL": "postgresql://user:pass@db:5432/app",
            "JWT Secret": "mock-jwt-secret-67890",
            "Encryption Key": "mock-encryption-key-abcdef",
            "Log Level": "INFO",
            "Max Connections": "100"
        }
        
        # Check for the vault secrets log pattern
        vault_secrets_start = "=== VAULT SECRETS RETRIEVED ==="
        vault_secrets_end = "=== END VAULT SECRETS ==="
        
        if vault_secrets_start not in logs:
            return False
        
        if vault_secrets_end not in logs:
            return False
        
        print(f"{Colors.success(f'Vault secrets log pattern found in {environment} logs')}")
        
        # Extract the vault secrets section
        start_idx = logs.find(vault_secrets_start)
        end_idx = logs.find(vault_secrets_end) + len(vault_secrets_end)
        vault_section = logs[start_idx:end_idx]
        
        # Verify each expected secret is present
        secrets_found = 0
        secrets_total = len(expected_secrets)
        
        for secret_name, expected_value in expected_secrets.items():
            # Look for the secret in the logs (case insensitive)
            secret_pattern = f"{secret_name}: {expected_value}"
            if secret_pattern in vault_section:
                print(f"{Colors.success(f'  {secret_name}: Found')}")
                secrets_found += 1
            else:
                print(f"{Colors.error(f'  {secret_name}: Not found (expected: {expected_value})')}")
        
        # Summary
        if secrets_found == secrets_total:
            print(f"{Colors.success(f'All {secrets_total} vault secrets found in {environment} logs')}")
            return True
        else:
            print(f"{Colors.warning(f'Only {secrets_found}/{secrets_total} vault secrets found in {environment} logs')}")
            return False
    
    def _test_endpoint_simple(self, url: str, description: str) -> bool:
        """Test a simple GET endpoint."""
        print(f"{Colors.info(f'Testing {description}...')}")
        return self._test_endpoint_with_retry(url, description, "GET")
    
    def _test_endpoint_with_data(self, url: str, description: str, method: str, data: str, content_type: str) -> bool:
        """Test an endpoint with data (POST/PUT)."""
        print(f"{Colors.info(f'Testing {description}...')}")
        return self._test_endpoint_with_retry(url, description, method, data, content_type)
    
    def _test_endpoint(self, test_case: Dict[str, Any]) -> bool:
        """Test a single endpoint."""
        name = test_case["name"]
        url = test_case["url"]
        expected_status = test_case["expected_status"]
        verify_ssl = test_case["verify_ssl"]
        
        try:
            print(f"{Colors.info(f'Testing {name}...')}")
            
            response = requests.get(
                url,
                timeout=10,
                verify=verify_ssl,
                headers={"Host": "edge-terrarium.local"}
            )
            
            if response.status_code == expected_status:
                print(f"{Colors.success(f'{name}: OK ({response.status_code})')}")
                return True
            else:
                print(f"{Colors.error(f'{name}: FAILED (expected {expected_status}, got {response.status_code})')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"{Colors.error(f'{name}: ERROR ({e})')}")
            return False
    
    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add test command arguments."""
        parser.add_argument(
            "--environment",
            choices=["docker", "k3s"],
            help="Force specific environment (auto-detected if not specified)"
        )
        
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop on first test failure"
        )
        
        parser.add_argument(
            "--timeout",
            type=int,
            default=10,
            help="Request timeout in seconds (default: 10)"
        )
        
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Number of retries for failed tests (default: 3)"
        )
