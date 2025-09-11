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

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class TestCommand(BaseCommand):
    """Command to test the deployment."""
    
    def run(self) -> int:
        """Run the test command."""
        try:
            print(f"{Colors.info('Testing deployment...')}")
            print(f"{Colors.info('Using self-signed certificates - SSL warnings suppressed')}")
            
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
        self._test_applications(base_url)
        
        # Test Logthon service
        self._test_logthon(base_url)
        
        # Test File Storage service
        self._test_file_storage(base_url)
        
        # Test Vault integration
        self._test_vault(base_url)
        
        # Test request logging
        self._test_request_logging()
        
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
        self._test_applications(base_url)
        
        # Test Logthon service
        self._test_logthon(base_url)
        
        # Test File Storage service
        self._test_file_storage(base_url)
        
        # Test Vault integration
        self._test_vault(base_url)
        
        # Test request logging
        self._test_request_logging()
        
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
    
    def _test_applications(self, base_url: str) -> None:
        """Test application endpoints."""
        print(f"{Colors.bold('Testing Application Endpoints')}")
        
        # Test Custom Client endpoints
        self._test_endpoint_simple(f"{base_url}/fake-provider/my-cool-thing", "Custom Client - fake-provider route")
        self._test_endpoint_simple(f"{base_url}/example-provider/another-awesome-item", "Custom Client - example-provider route")
        
        # Test Service Sink endpoints
        self._test_endpoint_simple(f"{base_url}/api/test", "Service Sink - API route")
        self._test_endpoint_simple(f"{base_url}/", "Service Sink - root route")
        
        # Test enhanced request logging
        print(f"{Colors.info('Testing enhanced request logging...')}")
        self._test_endpoint_simple(f"{base_url}/fake-provider/test?param1=value1&param2=value2", "Custom Client - GET with query params")
        self._test_endpoint_simple(f"{base_url}/api/test?user=testuser&action=login", "Service Sink - GET with query params")
        
        # Test POST requests with JSON
        self._test_endpoint_with_data(f"{base_url}/fake-provider/test", "Custom Client - POST with JSON", "POST", 
                                    '{"username":"testuser","password":"testpass"}', "application/json")
        
        # Test POST requests with form data
        self._test_endpoint_with_data(f"{base_url}/api/test", "Service Sink - POST with form data", "POST", 
                                    "data=test&status=active", "application/x-www-form-urlencoded")
        
        print("")
    
    def _test_logthon(self, base_url: str) -> None:
        """Test Logthon service."""
        print(f"{Colors.bold('Testing Logthon Service')}")
        
        # Test health endpoint
        self._test_endpoint_simple(f"{base_url}/logs/health", "Logthon health check")
        
        # Test web UI and API endpoints
        self._test_endpoint_simple(f"{base_url}/logs/", "Logthon web UI")
        self._test_endpoint_simple(f"{base_url}/logs/api/logs", "Logthon API endpoint")
        
        # Test direct access on port 5001 (only for Docker)
        if "localhost" in base_url:
            self._test_endpoint_simple("http://localhost:5001/health", "Logthon direct health check")
            self._test_endpoint_simple("http://localhost:5001/", "Logthon direct web UI")
        
        print("")
    
    def _test_file_storage(self, base_url: str) -> None:
        """Test File Storage service."""
        print(f"{Colors.bold('Testing File Storage Service')}")
        
        # Test health endpoint
        self._test_endpoint_simple(f"{base_url}/storage/health", "File Storage health check")
        
        # Test info endpoint
        self._test_endpoint_simple(f"{base_url}/storage/info", "File Storage info endpoint")
        
        # Test files endpoints
        self._test_endpoint_simple(f"{base_url}/storage/files", "File Storage list endpoint")
        
        # Test file creation with PUT request
        self._test_endpoint_with_data(f"{base_url}/storage/files", "File Storage create endpoint", "PUT", 
                                    '{"content":"Test file","filename_prefix":"test","extension":".txt"}', "application/json")
        
        # Test Logthon file storage integration
        self._test_endpoint_simple(f"{base_url}/logs/api/files", "Logthon file storage integration")
        
        print("")
    
    def _test_vault(self, base_url: str) -> None:
        """Test Vault integration."""
        print(f"{Colors.bold('Testing Vault Integration')}")
        
        # Test Vault health via NGINX
        self._test_endpoint_simple(f"{base_url}/vault/v1/sys/health", "Vault health via NGINX")
        
        # Test Vault health directly (only for Docker)
        if "localhost" in base_url:
            self._test_endpoint_simple("http://localhost:8200/v1/sys/health", "Vault health direct")
        
        # Test Vault secrets
        try:
            print(f"{Colors.info('Testing Vault secrets access...')}")
            response = requests.get("http://localhost:8200/v1/secret/metadata?list=true", 
                                 headers={"X-Vault-Token": "root"}, timeout=10)
            if response.status_code == 200:
                print(f"{Colors.success('Vault secrets accessible')}")
            else:
                print(f"{Colors.warning('Vault secrets not accessible')}")
        except Exception as e:
            print(f"{Colors.warning(f'Vault secrets test failed: {e}')}")
        
        print("")
    
    def _test_request_logging(self) -> None:
        """Test request logging."""
        print(f"{Colors.bold('Testing Request Logging')}")

        # Detect environment and use appropriate commands
        if self._detect_environment() == "docker":
            self._test_request_logging_docker()
        else:
            self._test_request_logging_k3s()

        print("")
    
    def _test_request_logging_docker(self) -> None:
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
    
    def _test_request_logging_k3s(self) -> None:
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
    
    def _test_endpoint_simple(self, url: str, description: str) -> bool:
        """Test a simple GET endpoint."""
        try:
            print(f"{Colors.info(f'Testing {description}...')}")
            # For K3s, we need to use the correct Host header
            headers = {}
            if "localhost:8443" in url:
                headers['Host'] = 'edge-terrarium.local'
            
            response = requests.get(url, timeout=10, verify=False, headers=headers)
            if response.status_code == 200:
                print(f"{Colors.success(f'{description}: OK ({response.status_code})')}")
                return True
            else:
                print(f"{Colors.error(f'{description}: ERROR ({response.status_code})')}")
                return False
        except Exception as e:
            print(f"{Colors.error(f'{description}: ERROR ({str(e)})')}")
            return False
    
    def _test_endpoint_with_data(self, url: str, description: str, method: str, data: str, content_type: str) -> bool:
        """Test an endpoint with data (POST/PUT)."""
        try:
            print(f"{Colors.info(f'Testing {description}...')}")
            headers = {"Content-Type": content_type}
            # For K3s, we need to use the correct Host header
            if "localhost:8443" in url:
                headers['Host'] = 'edge-terrarium.local'
            
            if method.upper() == "POST":
                response = requests.post(url, data=data, headers=headers, timeout=10, verify=False)
            elif method.upper() == "PUT":
                response = requests.put(url, data=data, headers=headers, timeout=10, verify=False)
            else:
                print(f"{Colors.error(f'{description}: Unsupported method {method}')}")
                return False
            
            if response.status_code in [200, 201]:
                print(f"{Colors.success(f'{description}: OK ({response.status_code})')}")
                return True
            else:
                print(f"{Colors.error(f'{description}: ERROR ({response.status_code})')}")
                return False
        except Exception as e:
            print(f"{Colors.error(f'{description}: ERROR ({str(e)})')}")
            return False
    
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
