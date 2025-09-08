# Configuration Directory

This directory contains all configuration files for deploying the Edge Terrarium project in different environments.

## Directory Structure

```
configs/
├── docker/          # Docker Compose configurations
└── k3s/            # Kubernetes (K3s) configurations
```

## Environment-Specific Configurations

### Docker Compose (`docker/`)
- **Purpose**: Local development and testing environment
- **Orchestration**: Docker Compose with hierarchical file structure
- **Networking**: Docker bridge networks with custom subnet
- **Gateway**: Kong Gateway for API routing
- **Storage**: Docker volumes for persistent data

### Kubernetes (`k3s/`)
- **Purpose**: Container orchestration and production-like environment
- **Orchestration**: Kubernetes with declarative YAML manifests
- **Networking**: Kubernetes services and ingress controllers
- **Gateway**: Kong Ingress Controller for API routing
- **Storage**: Persistent Volume Claims (PVCs)

## Key Differences

| Aspect | Docker Compose | K3s |
|--------|---------------|-----|
| **Orchestration** | Docker Compose | Kubernetes |
| **Service Discovery** | Container names | Kubernetes DNS |
| **Load Balancing** | Kong Gateway | Kong Ingress + Service LoadBalancer |
| **Storage** | Docker volumes | Persistent Volume Claims |
| **Networking** | Docker networks | Kubernetes services |
| **Health Checks** | Docker healthchecks | Kubernetes probes |
| **Scaling** | Manual container scaling | Kubernetes replica sets |
| **Updates** | Container restart | Rolling updates |

## Configuration Philosophy

Both environments follow the same architectural principles:

1. **Hierarchical Structure**: Base services → Core services → Application services → Gateway
2. **Service Dependencies**: Explicit dependency management and startup ordering
3. **Health Monitoring**: Comprehensive health checks and probes
4. **Centralized Logging**: All services integrate with logthon
5. **Secrets Management**: Vault integration for secure configuration
6. **API Gateway**: Kong for external traffic routing and management

## Getting Started

### Docker Compose
```bash
# Deploy with Docker Compose
./scripts/deploy.sh docker deploy

# Access services
# - Kong Gateway: https://localhost:443
# - Logthon UI: http://localhost:5001
# - Vault UI: http://localhost:8200
```

### K3s
```bash
# Deploy to K3s
./scripts/deploy.sh k3s deploy

# Access services
# - Kong Ingress: https://localhost:443
# - Logthon UI: http://localhost:5001
# - Vault UI: http://localhost:8200
# - Kubernetes Dashboard: https://localhost:9443
```

## Configuration Files

Each subdirectory contains detailed documentation about its specific configuration files and their interactions. See:

- [`docker/README.md`](docker/README.md) - Docker Compose configuration details
- [`k3s/README.md`](k3s/README.md) - Kubernetes configuration details
