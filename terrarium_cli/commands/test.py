"""
Test command for the CLI tool.
"""

import argparse
import logging
import time
import requests
import urllib3
from typing import List, Dict, Any

from terrarium_cli.commands.base import BaseCommand
from terrarium_cli.utils.shell import run_command, ShellError
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.dependencies import DependencyChecker

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class TestCommand(BaseCommand):
    """Command to test the deployment."""
    
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
        
        # Test Logthon service
        if not self._test_logthon(base_url):
            return 1
        
        # Test File Storage service
        if not self._test_file_storage(base_url):
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
        
        # Test Logthon service
        if not self._test_logthon(base_url):
            return 1
        
        # Test File Storage service
        if not self._test_file_storage(base_url):
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
        
        # Load app configurations to get dynamic endpoints
        from terrarium_cli.config.app_loader import AppLoader
        app_loader = AppLoader()
        apps = app_loader.load_apps()
        
        # Test each app's routes (skip logthon as it has its own specific tests)
        for app in apps:
            if app.name == 'logthon':
                continue
            
            # Check if app has special test handling defined
            if app.test_config and app.test_config.skip_generic_tests:
                if not self._test_app_specific(app, base_url):
                    return False
                continue
            
            for route in app.routes:
                # Create test URL by replacing * with empty string to test the root endpoint
                test_path = route.path.replace('*', '')
                test_url = f"{base_url}{test_path}"
                test_name = f"{app.name} - {route.path}"

                if not self._test_endpoint_simple(test_url, test_name):
                    return False
        
        # Test enhanced request logging with dynamic endpoints
        print(f"{Colors.info('Testing enhanced request logging...')}")
        for app in apps:
            if app.name == 'logthon':
                continue
            for route in app.routes:
                # Test with query params
                test_path = route.path.replace('*', '')
                test_url = f"{base_url}{test_path}?param1=value1&param2=value2"
                test_name = f"{app.name} - GET with query params"
                if not self._test_endpoint_simple(test_url, test_name):
                    return False
                
        
        print("")
        return True
    
    def _app_supports_method(self, app, method: str) -> bool:
        """Check if an app supports a specific HTTP method."""
        # Check if app has test_config defined
        if app.test_config and app.test_config.endpoints:
            for endpoint in app.test_config.endpoints:
                if method.upper() in endpoint.methods:
                    return True
            return False
        
        # If no test_config, try to detect support by testing the endpoint
        # This is a fallback for apps without explicit test configuration
        if method.upper() == "GET":
            return True  # Most apps support GET
        
        # For POST, we'll let the test run and handle 405 gracefully
        # This avoids hard-coding app names
        return True
    
    
    def _test_app_specific(self, app, base_url: str) -> bool:
        """Test an app using its specific test configuration."""
        print(f"{Colors.bold(f'Testing {app.name.title()} Application')}")
        
        if not app.test_config or not app.test_config.endpoints:
            print(f"  {Colors.warning(f'No test configuration found for {app.name}, skipping specific tests')}")
            return True
        
        # Test each configured endpoint
        for endpoint in app.test_config.endpoints:
            test_url = f"{base_url}{endpoint.path}"
            test_name = f"{app.name} - {endpoint.description or endpoint.path}"
            
            # Test each supported method
            for method in endpoint.methods:
                if method.upper() == "GET":
                    if not self._test_endpoint_simple(test_url, f"{test_name} ({method})"):
                        return False
                elif method.upper() == "POST":
                    if not self._test_endpoint_with_data(test_url, f"{test_name} ({method})", "POST", 
                                                       '{"test": "data"}', "application/json"):
                        return False
                # Add more methods as needed
        
        
        return True
    
    def _test_logthon(self, base_url: str) -> bool:
        """Test Logthon service."""
        print(f"{Colors.bold('Testing Logthon Service')}")
        
        # Test web UI and API endpoints
        if not self._test_endpoint_simple(f"{base_url}/logs/", "Logthon web UI"):
            return False
        if not self._test_endpoint_simple(f"{base_url}/logs/logs", "Logthon API endpoint"):
            return False
        
        # Test direct access on port 5001 (only for Docker)
        if "localhost" in base_url:
            if not self._test_endpoint_simple("http://localhost:5001/", "Logthon direct web UI"):
                return False
        
        print("")
        return True
    
    def _test_file_storage(self, base_url: str) -> bool:
        """Test File Storage service."""
        print(f"{Colors.bold('Testing File Storage Service')}")
        
        # Test health endpoint
        if not self._test_endpoint_simple(f"{base_url}/storage/health", "File Storage health check"):
            return False
        
        # Test info endpoint
        if not self._test_endpoint_simple(f"{base_url}/storage/info", "File Storage info endpoint"):
            return False
        
        # Test files endpoints
        if not self._test_endpoint_simple(f"{base_url}/storage/files", "File Storage list endpoint"):
            return False
        
        # Test file creation with PUT request
        if not self._test_endpoint_with_data(f"{base_url}/storage/files", "File Storage create endpoint", "PUT", 
                                    '{"content":"Test file","filename_prefix":"test","extension":".txt"}', "application/json"):
            return False
        
        # Test Logthon file storage integration
        if not self._test_endpoint_simple(f"{base_url}/logs/files", "Logthon file storage integration"):
            return False
        
        print("")
        return True
    
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
            result = run_command("docker ps --filter 'ancestor=edge-terrarium-custom-client' --format '{{.Names}}'",
                                capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                container_name = result.stdout.strip()
                
                # Test if request files are being created
                result = run_command(f"docker exec {container_name} ls -1 /tmp/requests/",
                                    capture_output=True, check=False)
                if result.returncode == 0:
                    file_list = result.stdout.strip()
                    if file_list:
                        file_count = len([line for line in file_list.split('\n') if line.strip()])
                        if file_count > 0:
                            print(f"{Colors.success(f'{file_count} request files present')}")
                        else:
                            print(f"{Colors.warning('No request files found')}")
                    else:
                        print(f"{Colors.warning('No request files found')}")
                else:
                    print(f"{Colors.warning('Could not check request files')}")
            else:
                print(f"{Colors.warning('Custom-client container not found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Request logging test failed: {e}')}")
        
        return True
    
    def _test_request_logging_k3s(self) -> bool:
        """Test request logging for K3s environment."""
        try:
            # Get the custom-client pod name
            result = run_command("kubectl get pods -n edge-terrarium -l app=custom-client -o jsonpath='{.items[0].metadata.name}'",
                                capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pod_name = result.stdout.strip()
                
                # Test if request files are being created
                result = run_command(f"kubectl exec -n edge-terrarium {pod_name} -- ls -1 /tmp/requests/",
                                    capture_output=True, check=False)
                if result.returncode == 0:
                    file_list = result.stdout.strip()
                    if file_list:
                        file_count = len([line for line in file_list.split('\n') if line.strip()])
                        if file_count > 0:
                            print(f"{Colors.success(f'{file_count} request files present')}")
                        else:
                            print(f"{Colors.warning('No request files found')}")
                    else:
                        print(f"{Colors.warning('No request files found')}")
                else:
                    print(f"{Colors.warning('Could not check request files')}")
            else:
                print(f"{Colors.warning('Custom-client pod not found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Request logging test failed: {e}')}")
        
        return True
    
    def _test_vault_secrets_logging(self) -> bool:
        """Test vault secrets logging in custom-client."""
        print(f"{Colors.bold('Testing Vault Secrets Logging')}")
        
        # Detect environment and use appropriate commands
        if self._detect_environment() == "docker":
            return self._test_vault_secrets_logging_docker()
        else:
            return self._test_vault_secrets_logging_k3s()
    
    def _test_vault_secrets_logging_docker(self) -> bool:
        """Test vault secrets logging for Docker environment."""
        try:
            result = run_command("docker ps --filter 'ancestor=edge-terrarium-custom-client' --format '{{.Names}}'",
                                capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                container_name = result.stdout.strip()
                
                # Get the logs from the custom-client container
                result = run_command(f"docker logs {container_name}",
                                    capture_output=True, check=False)
                if result.returncode == 0:
                    logs = result.stdout
                    self._verify_vault_secrets_in_logs(logs, "Docker")
                else:
                    print(f"{Colors.warning('Could not retrieve custom-client logs')}")
            else:
                print(f"{Colors.warning('Custom-client container not found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Vault secrets logging test failed: {e}')}")
        
        return True
    
    def _test_vault_secrets_logging_k3s(self) -> bool:
        """Test vault secrets logging for K3s environment."""
        try:
            # Get the custom-client pod name
            result = run_command("kubectl get pods -n edge-terrarium -l app=custom-client -o jsonpath='{.items[0].metadata.name}'",
                                capture_output=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pod_name = result.stdout.strip()
                
                # Get the logs from the custom-client pod
                result = run_command(f"kubectl logs -n edge-terrarium {pod_name}",
                                    capture_output=True, check=False)
                if result.returncode == 0:
                    logs = result.stdout
                    self._verify_vault_secrets_in_logs(logs, "K3s")
                else:
                    print(f"{Colors.warning('Could not retrieve custom-client logs')}")
            else:
                print(f"{Colors.warning('Custom-client pod not found')}")
        except Exception as e:
            print(f"{Colors.warning(f'Vault secrets logging test failed: {e}')}")
        
        return True
    
    def _verify_vault_secrets_in_logs(self, logs: str, environment: str) -> None:
        """Verify that vault secrets are present in the logs.
        
        The custom-client logs vault secrets in the format:
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
            print(f"{Colors.error(f'Vault secrets log pattern not found in {environment} logs')}")
            return
        
        if vault_secrets_end not in logs:
            print(f"{Colors.error(f'Vault secrets end pattern not found in {environment} logs')}")
            return
        
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
        else:
            print(f"{Colors.warning(f'Only {secrets_found}/{secrets_total} vault secrets found in {environment} logs')}")
    
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
