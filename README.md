# Edge-Terrarium - Dynamic Microservices Platform

A modern, dynamic microservices platform that demonstrates Docker containerization and K3s orchestration through a real-world application. Features a unified Python CLI, dynamic configuration generation, and automatic service discovery. Start with simple Docker containers and progress to full K3s deployment with NGINX ingress routing, secrets management, and monitoring.

## Quick Navigation

### Getting Started
- [Getting Started Guide](docs/getting-started.md) - Prerequisites, installation, and quick start
- [Learning Path](docs/learning-path.md) - Step-by-step learning progression
- [Architecture Overview](docs/architecture.md) - System design and component relationships

### Documentation
- [Project Structure](docs/project-structure.md) - Code organization and file structure
- [Configuration Guide](docs/configuration.md) - Configuration files and settings
- [Service Communication](docs/service-communication.md) - How services interact
- [Testing Guide](docs/testing.md) - Testing strategies and procedures
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Development Guide](docs/development.md) - Contributing and extending the platform

### Configuration Documentation
- [Configuration Overview](configs/README.md) - Overview of Docker and K3s configurations
- [Docker Compose Configuration](configs/docker/README.md) - Docker Compose file interactions and structure
- [Kubernetes Configuration](configs/k3s/README.md) - K3s YAML manifests and resource interactions

## What You'll Learn

This project teaches you:

### Docker Fundamentals
- Containerizing applications
- Multi-container orchestration with Docker Compose
- Service networking and communication
- Volume management and data persistence

### K3s Basics
- Pods, Services, and Deployments
- Ingress controllers and routing
- Secrets management with Vault
- Health checks and monitoring

### Advanced Concepts
- Dynamic configuration generation
- Service discovery and load balancing
- TLS/SSL termination
- Log aggregation and monitoring
- API gateway patterns

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd c-edge-terrarium

# Install dependencies
pip install -r requirements.txt

# Check system requirements
python terrarium.py check-deps

# Deploy to Docker
python terrarium.py deploy docker

# Or deploy to K3s
python terrarium.py deploy k3s

# Run tests
python terrarium.py test
```

## Key Features

- **Docker & K3s Support** - Deploy to both Docker Compose and Kubernetes
- **Dynamic Configuration** - Auto-generate configs from app definitions
- **Secrets Management** - Integrated Vault for secure secret storage
- **Monitoring & Logging** - Built-in log aggregation and monitoring
- **API Gateway** - NGINX-based routing and load balancing
- **Comprehensive Testing** - Automated testing for both environments
- **CLI Interface** - Unified command-line interface for all operations

## Architecture

The platform consists of several microservices working together:

- **custom-client** - C application handling special API routes
- **service-sink** - Default route handler for unmatched requests
- **file-storage** - Python FastAPI service for file operations
- **logthon** - Log aggregation and web UI
- **vault** - HashiCorp Vault for secrets management
- **nginx** - API gateway and ingress controller

## Contributing

See [Development Guide](docs/development.md) for information on contributing to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
