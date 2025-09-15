# Development Guide

This guide explains how to contribute to and extend the Edge-Terrarium platform.

## Development Setup

### Prerequisites
- Python 3.8+
- Docker Desktop
- k3d (for K3s development)
- kubectl
- Git

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd edge-terrarium

# Install dependencies with uv
uv sync

# Verify setup
uv run python terrarium.py check-deps
```

## Project Structure

### New Modular CLI Architecture

The CLI has been completely redesigned with a clean, modular architecture:

```
terrarium_cli/
├── cli/                          # 🎯 CLI interface layer
│   ├── commands/                 # All CLI command implementations  
│   └── main.py                   # CLI entry point
├── core/                         # 🧠 Core business logic
│   ├── deployment/               # Common deployment helpers
│   └── infrastructure/           # Infrastructure services (database, vault)
├── platforms/                    # 🚀 Platform-specific implementations
│   ├── docker/                   # Docker deployment manager
│   └── k3s/                      # K3s deployment manager  
├── config/                       # ⚙️ Configuration management
│   ├── loaders/                  # Configuration loaders
│   ├── generators/               # Configuration generators  
│   └── templates/                # Jinja2 templates (moved from root)
└── utils/                        # 🔧 Shared utilities
    ├── system/                   # System utilities (shell, dependencies)
    └── validation/               # Validation utilities
```

### Key Directories
- `/apps/` - Application services
- `/terrarium_cli/` - Modular CLI tool source code (new architecture)
- `/configs/` - Generated configuration files
- `/docs/` - Documentation

### Important Files
- `terrarium.py` - Main CLI entry point
- `pyproject.toml` - Python project configuration (replaces requirements.txt)
- `uv.lock` - uv lock file for reproducible dependencies
- `apps/*/app-config.yml` - Service configurations
- `configs/vault-secrets.yml` - Vault secrets

### CLI Layer Structure

#### **Commands** (`terrarium_cli/cli/commands/`)
Each command is a self-contained module:
- `deploy.py` - Main deployment orchestrator (reduced from 1,294 to 914 lines)
- `build.py` - Image building
- `test.py` - Testing functionality
- `vault.py` - Vault management
- `cert.py` - Certificate management
- `add_app.py` - Application scaffolding

#### **Platform Managers** (`terrarium_cli/platforms/`)
Platform-specific deployment logic:
- `docker/docker_manager.py` - Complete Docker Compose orchestration
- `k3s/k3s_manager.py` - Complete K3s/Kubernetes orchestration

#### **Configuration System** (`terrarium_cli/config/`)
- `loaders/app_loader.py` - Loads and parses app-config.yml files
- `generators/generator.py` - Generates Docker Compose and K3s manifests
- `templates/` - All Jinja2 templates for configuration generation

## Adding New Services

### Using the CLI Tool
```bash
# Interactive service creation
uv run python terrarium.py add-app

# Follow the prompts to:
# 1. Choose service type (C or Python)
# 2. Enter service name
# 3. Configure routes and ports
# 4. Set up dependencies
```

### Manual Service Creation
1. Create service directory in `/apps/`
2. Add `app-config.yml` with service configuration
3. Create `Dockerfile` for containerization
4. Add source code and dependencies
5. Update configuration templates if needed

### Service Configuration
Each service needs an `app-config.yml` file:
```yaml
name: my-service
type: python  # or c
port: 8080
routes:
  - path: /my-service/*
    methods: [GET, POST]
dependencies:
  - logthon
  - vault
environment:
  LOG_LEVEL: INFO
  VAULT_ADDR: "http://vault:8200"
```

## Modifying Existing Services

### Code Changes
1. Edit source code in `/apps/<service>/`
2. Test changes locally
3. Rebuild and redeploy:
   ```bash
   uv run python terrarium.py build
   uv run python terrarium.py deploy <environment>
   uv run python terrarium.py test
   ```

### Configuration Changes
1. Edit `app-config.yml` files
2. Regenerate configurations:
   ```bash
   uv run python terrarium.py deploy <environment>
   ```

### Adding Dependencies
1. Update `app-config.yml` dependencies
2. Add dependency configuration
3. Update service code to use dependency
4. Test integration

## CLI Tool Development

### Command Structure
Commands are located in `/terrarium_cli/commands/`:
- `base.py` - Base command class
- `deploy.py` - Deployment logic
- `test.py` - Testing functionality
- `vault.py` - Vault management
- `add_app.py` - Service creation

### Adding New Commands
1. Create new command file in `/terrarium_cli/commands/`
2. Inherit from `BaseCommand`
3. Implement required methods:
   ```python
   class MyCommand(BaseCommand):
       def add_arguments(self, parser):
           # Add command arguments
           pass
       
       def run(self, args):
           # Implement command logic
           pass
   ```
4. Register command in `main.py`

### Template Development
Templates are in `/terrarium_cli/templates/`:
- Use Jinja2 syntax
- Include auto-generated warnings
- Support environment variables
- Follow naming conventions

## Configuration Management

### Dynamic Configuration
The platform uses dynamic configuration generation:
- Templates in `/terrarium_cli/templates/`
- Generated files in `/configs/`
- Auto-generated warnings in all files
- Environment-specific configurations

### Adding New Templates
1. Create template file with `.j2` extension
2. Use Jinja2 syntax for variables
3. Include auto-generated warning
4. Test template generation

### Configuration Variables
Common variables available in templates:
- `{{ apps }}` - List of applications
- `{{ environment }}` - Deployment environment
- `{{ namespace }}` - Kubernetes namespace
- `{{ app.name }}` - Application name
- `{{ app.port }}` - Application port

## Testing

### Running Tests
```bash
# Run all tests
uv run python terrarium.py test

# Test specific environment
uv run python terrarium.py test --environment docker
uv run python terrarium.py test --environment k3s

# Test with verbose output
uv run python terrarium.py test --verbose

# Test with fail-fast
uv run python terrarium.py test --fail-fast
```

### Adding Tests
1. Add test cases to `/terrarium_cli/commands/test.py`
2. Follow existing test patterns
3. Test both Docker and K3s environments
4. Include error handling and cleanup

### Test Best Practices
- Use descriptive test names
- Include setup and teardown
- Test error conditions
- Verify both success and failure cases
- Clean up test data

## Code Quality

### Python Standards
- Follow PEP 8 style guide
- Use type hints where appropriate
- Include docstrings for functions
- Use meaningful variable names
- Keep functions small and focused

### C Standards
- Follow C99 standard
- Use consistent indentation
- Include header guards
- Document function parameters
- Handle errors gracefully

### Code Review
- All changes should be reviewed
- Include tests for new functionality
- Update documentation as needed
- Verify both Docker and K3s deployments
- Check for security issues

## Extending the CLI Architecture

The new modular architecture makes it easy to extend the CLI with new functionality:

### Adding a New Command

1. **Create the command file** in `terrarium_cli/cli/commands/`:
```python
# terrarium_cli/cli/commands/monitor.py
from terrarium_cli.cli.commands.base import BaseCommand
from terrarium_cli.utils.colors import Colors

class MonitorCommand(BaseCommand):
    def run(self, args):
        """Monitor deployment health."""
        print(f"{Colors.info('Monitoring deployment...')}")
        # Implementation here
```

2. **Register the command** in `terrarium_cli/cli/main.py`:
```python
from terrarium_cli.cli.commands.monitor import MonitorCommand

# In create_parser()
monitor_parser = subparsers.add_parser('monitor', help='Monitor deployment health')
monitor_parser.set_defaults(command_class=MonitorCommand)
```

### Adding a New Platform

1. **Create platform manager** in `terrarium_cli/platforms/aws/`:
```python
# terrarium_cli/platforms/aws/aws_manager.py
from terrarium_cli.core.deployment.common import CommonDeploymentHelpers

class AwsDeploymentManager(CommonDeploymentHelpers):
    def deploy(self, dependencies_check, cleanup_other, certificates, images):
        """Deploy to AWS ECS/EKS."""
        # AWS-specific deployment logic
```

2. **Update deploy command** to use the new platform:
```python
# In terrarium_cli/cli/commands/deploy.py
from terrarium_cli.platforms.aws.aws_manager import AwsDeploymentManager

def _deploy_aws(self):
    """Deploy to AWS."""
    return self.aws_manager.deploy(
        self._check_dependencies,
        self._cleanup_other_platforms,
        self._generate_certificates,
        self._build_and_push_images
    )
```

### Adding a New Configuration Generator

1. **Create generator** in `terrarium_cli/config/generators/`:
```python
# terrarium_cli/config/generators/helm_generator.py
from terrarium_cli.config.loaders.app_loader import AppConfig
from jinja2 import Environment, FileSystemLoader

class HelmConfigGenerator:
    def generate_helm_chart(self, apps):
        """Generate Helm charts from app configurations."""
        # Helm chart generation logic
```

2. **Add templates** in `terrarium_cli/config/templates/`:
```yaml
# terrarium_cli/config/templates/helm-chart.yaml.j2
apiVersion: v2
name: {{ app.name }}
# Helm chart template
```

### Adding New Utilities

1. **System utilities** in `terrarium_cli/utils/system/`:
```python
# terrarium_cli/utils/system/network.py
def check_port_availability(port: int) -> bool:
    """Check if a port is available."""
    # Port checking logic
```

2. **Validation utilities** in `terrarium_cli/utils/validation/`:
```python
# terrarium_cli/utils/validation/security_validator.py
def validate_security_config(config: dict) -> bool:
    """Validate security configuration."""
    # Security validation logic
```

### Best Practices for Extensions

#### **Follow Layer Responsibilities**
- **CLI Layer**: Only handle user interaction and command routing
- **Core Layer**: Implement shared business logic
- **Platform Layer**: Keep platform-specific logic isolated
- **Config Layer**: Focus on configuration loading and generation
- **Utils Layer**: Provide reusable, stateless utilities

#### **Import Structure**
Use the logical import paths:
```python
# Good - clear layer separation
from terrarium_cli.cli.commands.base import BaseCommand
from terrarium_cli.platforms.docker.docker_manager import DockerDeploymentManager
from terrarium_cli.core.deployment.common import CommonDeploymentHelpers
from terrarium_cli.utils.system.shell import run_command

# Avoid - crossing layer boundaries inappropriately
from terrarium_cli.platforms.docker.docker_manager import some_utility_function
```

#### **Error Handling**
Implement consistent error handling across layers with intelligent error suppression:
```python
from terrarium_cli.utils.system.shell import ShellError
from terrarium_cli.utils.colors import Colors
import logging

# Standard error handling
try:
    result = self.platform_manager.deploy()
    print(f"{Colors.success('Deployment completed successfully')}")
except ShellError as e:
    print(f"{Colors.error(f'Deployment failed: {e}')}")
    return 1

# For expected failures, suppress error logs
def suppress_expected_shell_errors():
    """Context manager to suppress shell error logs for expected failures."""
    shell_logger = logging.getLogger('terrarium_cli.utils.system.shell')
    original_level = shell_logger.level
    shell_logger.setLevel(logging.CRITICAL)
    
    try:
        yield
    finally:
        shell_logger.setLevel(original_level)

# Usage example
with suppress_expected_shell_errors():
    try:
        run_command("kubectl exec pod -- which curl", check=True)
        # Curl is available, proceed with health check
    except ShellError:
        # Curl not available, use alternative method
        print(f"{Colors.warning('Health check failed (curl not available)')}")
```

#### **Testing New Components**
Each layer should be testable independently:
```python
# Test platform managers
def test_docker_deployment():
    manager = DockerDeploymentManager()
    result = manager.check_docker_prerequisites()
    assert result is True

# Test configuration generators
def test_config_generation():
    generator = ConfigGenerator()
    apps = load_test_apps()
    configs = generator.generate_all_configs(apps)
    assert configs is not None
```

### Migration Guide

When extending existing functionality:

1. **Identify the appropriate layer** for your changes
2. **Follow existing patterns** in that layer
3. **Update imports** to use the new modular structure
4. **Test both Docker and K3s** deployments
5. **Update documentation** to reflect changes

## Documentation

### Updating Documentation
1. Edit relevant markdown files in `/docs/`
2. Update code comments
3. Add examples and usage
4. Verify links and references
5. Test documentation accuracy

### Documentation Standards
- Use clear, concise language
- Include code examples
- Provide step-by-step instructions
- Update when code changes
- Include troubleshooting information

## Deployment

### Local Development
```bash
# Docker development
uv run python terrarium.py deploy docker
uv run python terrarium.py test

# K3s development
uv run python terrarium.py deploy k3s
uv run python terrarium.py test
```

### Production Considerations
- Use specific image tags (not `:latest`)
- Implement proper health checks
- Configure resource limits
- Set up monitoring and logging
- Use secrets management
- Implement backup procedures

## Debugging

### Common Debug Techniques
1. **Check logs**: Use `docker logs` or `kubectl logs`
2. **Verify configuration**: Check generated config files
3. **Test connectivity**: Use `curl` or `telnet`
4. **Check resources**: Monitor CPU, memory, disk usage
5. **Use debug mode**: Enable verbose logging

### Debug Tools
```bash
# Docker debugging
docker exec -it <container> /bin/sh
docker logs <container> --follow

# K3s debugging
kubectl exec -it -n edge-terrarium <pod> -- /bin/sh
kubectl logs -n edge-terrarium <pod> --follow
kubectl describe pod -n edge-terrarium <pod>
```

## Contributing

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

### Commit Messages
Use clear, descriptive commit messages:
```
feat: add new service creation command
fix: resolve port conflict in Docker deployment
docs: update troubleshooting guide
test: add integration tests for vault
```

### Issue Reporting
When reporting issues, include:
- System information
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs and configuration
- Environment details

## Best Practices

### Development Workflow
1. **Plan**: Understand requirements and design
2. **Code**: Implement changes incrementally
3. **Test**: Verify functionality works
4. **Document**: Update documentation
5. **Review**: Get code reviewed
6. **Deploy**: Test in both environments

### Security Considerations
- Never commit secrets or credentials
- Use Vault for secret management
- Validate all inputs
- Implement proper error handling
- Keep dependencies updated
- Use secure coding practices

### Performance Optimization
- Profile code for bottlenecks
- Use appropriate data structures
- Implement caching where beneficial
- Monitor resource usage
- Optimize database queries
- Use connection pooling

This development guide provides the foundation for contributing to and extending the Edge-Terrarium platform effectively.
