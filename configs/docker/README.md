# Docker Compose Configuration

This directory contains Docker Compose configuration files for the Edge Terrarium project, organized in a hierarchical structure that ensures proper service startup order and dependency management.

## File Structure

```
docker/
├── docker-compose.yml          # Main compose file (includes all others)
├── docker-compose.base.yml     # Base services (Vault, Vault Init)
├── docker-compose.core.yml     # Core services (Logthon, File Storage)
├── docker-compose.apps.yml     # Application services (Custom Client, Service Sink)
├── docker-compose.gateway.yml  # Gateway services (Kong)
├── kong/
│   └── kong.yml               # Kong Gateway configuration
└── certs/                     # TLS certificates (gitignored)
```

## Configuration Hierarchy

The Docker Compose files are included in a specific order to ensure proper service startup:

### 1. Base Services (`docker-compose.base.yml`)
**Purpose**: Foundational services that other services depend on

**Services**:
- `vault` - HashiCorp Vault for secrets management
- `vault-init` - One-time initialization job

**Key Features**:
- Vault runs in development mode with root token
- Vault-init waits for Vault to be healthy before running
- Persistent volumes for Vault data and logs
- Health checks ensure Vault is ready before other services start

### 2. Core Services (`docker-compose.core.yml`)
**Purpose**: Essential services that application services depend on

**Services**:
- `logthon` - Log aggregation service with web UI
- `file-storage` - File storage API with CRUD operations

**Dependencies**:
- Both services wait for `vault-init` to complete successfully
- `file-storage` waits for `logthon` to be healthy
- All services integrate with logthon for centralized logging

### 3. Application Services (`docker-compose.apps.yml`)
**Purpose**: Main application logic services

**Services**:
- `custom-client` - Handles `/fake-provider/*` and `/example-provider/*` routes
- `service-sink` - Handles all other HTTP requests (default route)

**Dependencies**:
- Both services wait for `vault-init` to complete
- Both services wait for `logthon` to be healthy
- `custom-client` also waits for `file-storage` to be healthy
- Custom client automatically creates files via file-storage API

### 4. Gateway Services (`docker-compose.gateway.yml`)
**Purpose**: External access and API routing

**Services**:
- `kong-gateway` - API Gateway and reverse proxy

**Dependencies**:
- Waits for all application services to be healthy
- Routes external traffic to appropriate backend services
- Provides TLS termination and load balancing

## Service Communication

### Internal Networking
All services communicate through the `edge-terrarium-network` Docker network:

```yaml
networks:
  edge-terrarium-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
```

### Service Discovery
Services find each other using container names:
- `vault:8200` - Vault API
- `logthon:5000` - Log aggregation
- `file-storage:9000` - File storage API
- `custom-client:1337` - Custom client service
- `service-sink:8080` - Service sink

### External Access
Kong Gateway provides external access:
- `https://localhost:443` - Main application gateway
- `http://localhost:5001` - Logthon web UI (direct access)
- `http://localhost:8200` - Vault UI (direct access)

## Kong Gateway Configuration

The Kong Gateway (`kong/kong.yml`) routes external traffic based on URL patterns:

| Route Pattern | Backend Service | Purpose |
|---------------|----------------|---------|
| `/fake-provider/*` | custom-client:1337 | Special handling for fake provider requests |
| `/example-provider/*` | custom-client:1337 | Special handling for example provider requests |
| `/storage/*` | file-storage:9000 | File storage CRUD operations |
| `/logs/*` | logthon:5000 | Log aggregation and web UI |
| `/vault/v1/sys/health` | vault:8200 | Vault health check |
| `/health` | service-sink:8080 | Health check endpoint |
| `/` (root) | service-sink:8080 | Default handler for all other requests |

## Volume Management

### Named Volumes
- `vault-data` - Persistent Vault storage
- `vault-logs` - Vault log files
- `file-storage-data` - File storage persistent data
- `custom-requests` - Custom client request logs

### Volume Mounts
```yaml
volumes:
  - vault-data:/vault/data
  - file-storage-data:/app/storage
  - custom-requests:/tmp/requests
```

## Health Checks

All services include comprehensive health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:PORT/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Environment Variables

### Vault Configuration
```yaml
environment:
  - VAULT_DEV_ROOT_TOKEN_ID=root
  - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
  - VAULT_ADDR=http://0.0.0.0:8200
```

### Service Configuration
```yaml
environment:
  - SERVICE_NAME=service-name
  - CONTAINER_NAME=edge-terrarium-service-name
  - VAULT_ADDR=http://vault:8200
  - VAULT_TOKEN=root
  - LOGTHON_HOST=logthon
  - LOGTHON_PORT=5000
```

## Startup Sequence

The services start in this specific order:

1. **Vault** → **vault-init** (creates secrets)
2. **logthon** (waits for vault-init completion)
3. **file-storage** (waits for logthon to be ready)
4. **custom-client** (waits for vault-init + logthon + file-storage)
5. **service-sink** (waits for vault-init + logthon)
6. **kong-gateway** (waits for all application services)

## Development Workflow

### Local Development
```bash
# Start all services
./scripts/deploy.sh docker deploy

# View logs
docker-compose -f configs/docker/docker-compose.yml logs -f

# Restart specific service
docker-compose -f configs/docker/docker-compose.yml restart service-name

# Scale service
docker-compose -f configs/docker/docker-compose.yml up -d --scale service-name=3
```

### Testing
```bash
# Test all services
./scripts/test-docker.sh

# Test specific endpoint
curl -H "Host: localhost" https://localhost:443/fake-provider/test
```

### Cleanup
```bash
# Stop and remove all containers
./scripts/deploy.sh docker clean

# Remove volumes (WARNING: deletes data)
docker-compose -f configs/docker/docker-compose.yml down -v
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 443, 5001, 8200, 9000 are available
2. **Service Dependencies**: Check that vault-init completes successfully
3. **Health Check Failures**: Verify service endpoints are responding
4. **Network Issues**: Ensure all services are on the same Docker network

### Debugging Commands

```bash
# Check service status
docker-compose -f configs/docker/docker-compose.yml ps

# View service logs
docker-compose -f configs/docker/docker-compose.yml logs service-name

# Check network connectivity
docker exec -it edge-terrarium-custom-client ping logthon

# Inspect service configuration
docker-compose -f configs/docker/docker-compose.yml config
```
