"""
Dependency checking utilities for the terrarium CLI.
"""

import shutil
import platform
import subprocess
from typing import Dict, List, Tuple, Optional
from terrarium_cli.utils.colors import Colors
from terrarium_cli.utils.shell import check_command_exists, run_command


class DependencyError(Exception):
    """Exception raised when required dependencies are missing."""
    pass


class DependencyChecker:
    """Checks for required system dependencies."""
    
    def __init__(self):
        """Initialize the dependency checker."""
        self.system = platform.system().lower()
        self.required_deps = {
            'docker': {
                'command': 'docker',
                'description': 'Docker Engine',
                'required_for': ['Docker Compose deployment', 'Building container images'],
                'install_instructions': self._get_docker_install_instructions()
            },
            'docker_compose': {
                'command': 'docker-compose',
                'description': 'Docker Compose',
                'required_for': ['Docker Compose deployment', 'Multi-container orchestration'],
                'install_instructions': self._get_docker_compose_install_instructions()
            },
            'k3d': {
                'command': 'k3d',
                'description': 'k3d (Kubernetes in Docker)',
                'required_for': ['K3s deployment', 'Local Kubernetes cluster management'],
                'install_instructions': self._get_k3d_install_instructions(),
                'auto_installable': True
            },
            'kubectl': {
                'command': 'kubectl',
                'description': 'kubectl (Kubernetes CLI)',
                'required_for': ['K3s deployment', 'Kubernetes resource management'],
                'install_instructions': self._get_kubectl_install_instructions()
            },
            'curl': {
                'command': 'curl',
                'description': 'curl',
                'required_for': ['Downloading k3d installer', 'Health checks', 'API requests'],
                'install_instructions': self._get_curl_install_instructions()
            },
            'python3': {
                'command': 'python3',
                'description': 'Python 3',
                'required_for': ['Running the terrarium CLI', 'Python application support'],
                'install_instructions': self._get_python3_install_instructions()
            }
        }
    
    def check_all_dependencies(self, required_commands: List[str] = None) -> bool:
        """
        Check all required dependencies.
        
        Args:
            required_commands: List of specific commands to check. If None, checks all.
            
        Returns:
            True if all dependencies are available, False otherwise.
        """
        if required_commands is None:
            required_commands = list(self.required_deps.keys())
        
        missing_deps = []
        auto_installable = []
        
        print(f"{Colors.info('Checking system dependencies...')}")
        
        for dep_name in required_commands:
            if dep_name not in self.required_deps:
                print(f"{Colors.error(f'Unknown dependency: {dep_name}')}")
                missing_deps.append(dep_name)
                continue
                
            dep_info = self.required_deps[dep_name]
            command = dep_info['command']
            
            if check_command_exists(command):
                print(f"{Colors.success(f'✓ {dep_info["description"]}')}")
            else:
                print(f"{Colors.error(f'✗ {dep_info["description"]} - MISSING')}")
                missing_deps.append(dep_name)
                
                if dep_info.get('auto_installable', False):
                    auto_installable.append(dep_name)
        
        if missing_deps:
            print(f"\n{Colors.error('Missing required dependencies:')}")
            self._print_missing_dependencies(missing_deps, auto_installable)
            return False
        
        print(f"{Colors.success('All required dependencies are available!')}")
        return True
    
    def check_dependency(self, dep_name: str) -> bool:
        """
        Check a specific dependency.
        
        Args:
            dep_name: Name of the dependency to check.
            
        Returns:
            True if dependency is available, False otherwise.
        """
        if dep_name not in self.required_deps:
            raise ValueError(f"Unknown dependency: {dep_name}")
        
        dep_info = self.required_deps[dep_name]
        command = dep_info['command']
        
        return check_command_exists(command)
    
    def install_dependency(self, dep_name: str) -> bool:
        """
        Attempt to install a dependency.
        
        Args:
            dep_name: Name of the dependency to install.
            
        Returns:
            True if installation succeeded, False otherwise.
        """
        if dep_name not in self.required_deps:
            raise ValueError(f"Unknown dependency: {dep_name}")
        
        dep_info = self.required_deps[dep_name]
        
        if not dep_info.get('auto_installable', False):
            print(f"{Colors.error(f'Cannot auto-install {dep_info["description"]}')}")
            return False
        
        print(f"{Colors.info(f'Attempting to install {dep_info["description"]}...')}")
        
        try:
            if dep_name == 'k3d':
                return self._install_k3d()
            else:
                print(f"{Colors.error(f'Auto-installation not implemented for {dep_name}')}")
                return False
        except Exception as e:
            print(f"{Colors.error(f'Failed to install {dep_info["description"]}: {e}')}")
            return False
    
    def _print_missing_dependencies(self, missing_deps: List[str], auto_installable: List[str]) -> None:
        """Print detailed information about missing dependencies."""
        for dep_name in missing_deps:
            if dep_name not in self.required_deps:
                print(f"\n{Colors.error(f'❌ {dep_name} (Unknown dependency)')}")
                print(f"   {Colors.warning('This dependency is not recognized by the system.')}")
                continue
                
            dep_info = self.required_deps[dep_name]
            print(f"\n{Colors.error(f'❌ {dep_info["description"]}')}")
            print(f"   Required for: {', '.join(dep_info['required_for'])}")
            
            if dep_name in auto_installable:
                print(f"   {Colors.info('🔄 Auto-installable: Yes')}")
            else:
                print(f"   {Colors.warning('🔄 Auto-installable: No')}")
            
            print(f"   Installation instructions:")
            for instruction in dep_info['install_instructions']:
                print(f"     {Colors.info('•')} {instruction}")
    
    def _install_k3d(self) -> bool:
        """Install k3d."""
        try:
            print(f"{Colors.info('Installing k3d...')}")
            run_command(
                "curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash",
                check=True
            )
            print(f"{Colors.success('k3d installed successfully')}")
            return True
        except Exception as e:
            print(f"{Colors.error(f'Failed to install k3d: {e}')}")
            return False
    
    def _get_docker_install_instructions(self) -> List[str]:
        """Get Docker installation instructions for current system."""
        if self.system == 'darwin':
            return [
                "Install Docker Desktop for Mac: https://docs.docker.com/desktop/mac/install/",
                "Or use Homebrew: brew install --cask docker",
                "Start Docker Desktop after installation"
            ]
        elif self.system == 'linux':
            return [
                "Ubuntu/Debian: sudo apt-get update && sudo apt-get install docker.io",
                "CentOS/RHEL: sudo yum install docker",
                "Start Docker service: sudo systemctl start docker",
                "Add user to docker group: sudo usermod -aG docker $USER"
            ]
        elif self.system == 'windows':
            return [
                "Install Docker Desktop for Windows: https://docs.docker.com/desktop/windows/install/",
                "Enable WSL 2 integration if using WSL",
                "Restart after installation"
            ]
        else:
            return ["Visit https://docs.docker.com/get-docker/ for installation instructions"]
    
    def _get_docker_compose_install_instructions(self) -> List[str]:
        """Get Docker Compose installation instructions for current system."""
        if self.system == 'darwin':
            return [
                "Docker Compose is included with Docker Desktop for Mac",
                "Or install separately: brew install docker-compose"
            ]
        elif self.system == 'linux':
            return [
                "Ubuntu/Debian: sudo apt-get install docker-compose",
                "CentOS/RHEL: sudo yum install docker-compose",
                "Or install via pip: pip install docker-compose"
            ]
        elif self.system == 'windows':
            return [
                "Docker Compose is included with Docker Desktop for Windows",
                "Or install via pip: pip install docker-compose"
            ]
        else:
            return ["Visit https://docs.docker.com/compose/install/ for installation instructions"]
    
    def _get_k3d_install_instructions(self) -> List[str]:
        return [
            "Automatic installation: curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash",
            "Manual installation: https://k3d.io/installation/",
            "Or via package manager: brew install k3d (macOS) or apt install k3d (Linux)"
        ]
    
    def _get_kubectl_install_instructions(self) -> List[str]:
        if self.system == 'darwin':
            return [
                "Install via Homebrew: brew install kubectl",
                "Or download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/"
            ]
        elif self.system == 'linux':
            return [
                "Ubuntu/Debian: curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl",
                "CentOS/RHEL: sudo yum install kubectl",
                "Or via snap: sudo snap install kubectl --classic"
            ]
        elif self.system == 'windows':
            return [
                "Download from: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/",
                "Or via Chocolatey: choco install kubernetes-cli",
                "Or via Scoop: scoop install kubectl"
            ]
        else:
            return ["Visit https://kubernetes.io/docs/tasks/tools/ for installation instructions"]
    
    def _get_curl_install_instructions(self) -> List[str]:
        if self.system == 'darwin':
            return ["curl is pre-installed on macOS", "Or install via Homebrew: brew install curl"]
        elif self.system == 'linux':
            return [
                "Ubuntu/Debian: sudo apt-get install curl",
                "CentOS/RHEL: sudo yum install curl",
                "Most Linux distributions include curl by default"
            ]
        elif self.system == 'windows':
            return [
                "Download from: https://curl.se/windows/",
                "Or install via Chocolatey: choco install curl",
                "Or via Scoop: scoop install curl"
            ]
        else:
            return ["Visit https://curl.se/download.html for installation instructions"]
    
    def _get_python3_install_instructions(self) -> List[str]:
        if self.system == 'darwin':
            return [
                "Install via Homebrew: brew install python@3.11",
                "Or download from: https://www.python.org/downloads/macos/",
                "Python 3 is often pre-installed on macOS"
            ]
        elif self.system == 'linux':
            return [
                "Ubuntu/Debian: sudo apt-get install python3 python3-pip",
                "CentOS/RHEL: sudo yum install python3 python3-pip",
                "Most Linux distributions include Python 3"
            ]
        elif self.system == 'windows':
            return [
                "Download from: https://www.python.org/downloads/windows/",
                "Or install via Chocolatey: choco install python",
                "Or via Scoop: scoop install python"
            ]
        else:
            return ["Visit https://www.python.org/downloads/ for installation instructions"]


def check_dependencies(required_commands: List[str] = None) -> bool:
    """
    Convenience function to check dependencies.
    
    Args:
        required_commands: List of specific commands to check. If None, checks all.
        
    Returns:
        True if all dependencies are available, False otherwise.
    """
    checker = DependencyChecker()
    return checker.check_all_dependencies(required_commands)


def require_dependencies(required_commands: List[str] = None) -> None:
    """
    Check dependencies and raise exception if any are missing.
    
    Args:
        required_commands: List of specific commands to check. If None, checks all.
        
    Raises:
        DependencyError: If any required dependencies are missing.
    """
    checker = DependencyChecker()
    if not checker.check_all_dependencies(required_commands):
        raise DependencyError("Required dependencies are missing. Please install them and try again.")
