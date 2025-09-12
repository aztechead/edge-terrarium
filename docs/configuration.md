# Configuration Guide

This guide explains the configuration system and how to manage settings for Edge-Terrarium.

## Configuration Overview

Edge-Terrarium uses a dynamic configuration system that automatically generates deployment files from templates and application definitions.

### Configuration Types

1. **Application Configuration** - Service-specific settings in `app-config.yml`
2. **Global Configuration** - Platform-wide settings
3. **Generated Configuration** - Auto-generated Docker Compose and K3s files
4. **Vault Secrets** - Secure secret storage and management

## Application Configuration

### App Config Structure

Each service has an `app-config.yml` file that defines its configuration:

```yaml
name: custom-client
type: c
port: 1337
routes:
  - path: /fake-provider/*
    methods: [GET, POST]
  - path: /example-provider/*
    methods: [GET, POST]
dependencies:
  - vault
  - logthon
  - file-storage
environment:
  VAULT_ADDR: "http://vault:8200"
  VAULT_TOKEN: "root"
  LOG_LEVEL: "INFO"
health_check:
  path: /health
  interval: 30
  timeout: 10
  retries: 3
```

### Configuration Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `name` | string | Service name | Yes |
| `type` | string | Service type (c, python) | Yes |
| `port` | integer | Service port | Yes |
| `routes` | array | URL routing rules | Yes |
| `dependencies` | array | Required services | No |
| `environment` | object | Environment variables | No |
| `health_check` | object | Health check configuration | No |

### Route Configuration

Routes define how requests are routed to services:

```yaml
routes:
  - path: /api/service/*
    methods: [GET, POST, PUT, DELETE]
    strip_prefix: true
  - path: /health
    methods: [GET]
    strip_prefix: false
```

### Environment Variables

Environment variables are injected into containers:

```yaml
environment:
  LOG_LEVEL: "INFO"
  VAULT_ADDR: "http://vault:8200"
  VAULT_TOKEN: "root"
  DATABASE_URL: "postgresql://user:pass@db:5432/app"
```

## Global Configuration

### Platform Settings

Global configuration is managed in `/terrarium_cli/config/global_config.py`:

```python
class GlobalConfig:
    NAMESPACE = "edge-terrarium"
    DOCKER_NETWORK = "edge-terrarium_default"
    K3S_CLUSTER = "edge-terrarium"
    NGINX_PORT = 8443
    VAULT_PORT = 8200
```

### Environment-Specific Settings

Different settings for Docker vs K3s:

```python
DOCKER_CONFIG = {
    "network_mode": "bridge",
    "restart_policy": "unless-stopped"
}

K3S_CONFIG = {
    "namespace": "edge-terrarium",
    "ingress_class": "nginx"
}
```

## Generated Configuration

### Docker Compose Files

Generated files in `/configs/docker/`:
- `docker-compose.yml` - Main compose file
- `docker-compose.base.yml` - Base services
- `docker-compose.core.yml` - Core services
- `docker-compose.apps.yml` - Application services
- `docker-compose.gateway.yml` - Gateway services

### K3s Manifests

Generated files in `/configs/k3s/`:
- `namespace.yaml` - Namespace definition
- `ingress.yaml` - Ingress configuration
- `*-deployment.yaml` - Deployment manifests
- `*-service.yaml` - Service manifests
- `*-pvc.yaml` - Persistent volume claims

### NGINX Configuration

Generated files in `/configs/docker/nginx/`:
- `nginx.conf` - Main NGINX configuration
- `server.conf` - Server block configuration

## Vault Secrets Configuration

### Secrets File

Secrets are defined in `/configs/vault-secrets.yml`:

```yaml
secrets:
  # Custom Client Configuration
  custom-client/config:
    api_key: "mock-api-key-12345"
    database_url: "postgresql://user:pass@db:5432/app"
    jwt_secret: "mock-jwt-secret-67890"
    encryption_key: "mock-encryption-key-abcdef"
    log_level: "INFO"
    max_connections: "100"

  # Custom Client External APIs
  custom-client/external-apis:
    file_storage_url: "http://file-storage:9000"
    logthon_url: "http://logthon:5000"

  # Terrarium TLS Configuration
  terrarium/tls:
    cert: "mock-tls-cert"
    key: "mock-tls-key"
```

### Secret Management

Secrets are managed through the CLI:

```bash
# Initialize Vault with secrets
python terrarium.py vault init

# List all secrets
python terrarium.py vault list

# Get specific secret
python terrarium.py vault get custom-client/config

# Set new secret
python terrarium.py vault set my-app/database host=db.example.com
```

## Configuration Generation

### Template System

Configuration files are generated from Jinja2 templates:

```jinja2
# Template example
apiVersion: v1
kind: Service
metadata:
  name: {{ app.name }}-service
  namespace: {{ namespace }}
spec:
  selector:
    app: {{ app.name }}
  ports:
  - port: {{ app.port }}
    targetPort: {{ app.port }}
```

### Generation Process

1. **Load Applications**: Read all `app-config.yml` files
2. **Process Templates**: Apply Jinja2 templates
3. **Generate Files**: Create configuration files
4. **Add Warnings**: Include auto-generated warnings
5. **Write Files**: Save to appropriate directories

### Auto-Generated Warnings

All generated files include warnings:

```yaml
# AUTO-GENERATED FILE - DO NOT EDIT
# Generated on: 2025-01-12 10:30:00
# Source: terrarium_cli/templates/k3s-deployment.yaml.j2
```

## Environment-Specific Configuration

### Docker Configuration

Docker-specific settings:
- Container networking
- Volume mounts
- Port mappings
- Restart policies
- Health checks

### K3s Configuration

K3s-specific settings:
- Namespace isolation
- Ingress routing
- Service discovery
- Resource limits
- Persistent volumes

## Configuration Validation

### Validation Rules

The system validates configurations:
- Required fields present
- Valid port numbers
- Proper route syntax
- Valid environment variables
- Dependency resolution

### Error Handling

Configuration errors are handled gracefully:
- Clear error messages
- Suggestions for fixes
- Validation before generation
- Rollback on failure

## Best Practices

### Configuration Management

1. **Use Templates**: Leverage Jinja2 templates for consistency
2. **Environment Variables**: Use env vars for runtime configuration
3. **Secret Management**: Store secrets in Vault, not config files
4. **Validation**: Validate configurations before deployment
5. **Documentation**: Document configuration options

### Security Considerations

1. **No Hardcoded Secrets**: Use Vault for all secrets
2. **Environment Separation**: Different configs for different environments
3. **Access Control**: Limit access to configuration files
4. **Audit Trail**: Track configuration changes
5. **Encryption**: Encrypt sensitive configuration data

### Maintenance

1. **Regular Updates**: Keep configurations up to date
2. **Cleanup**: Remove unused configurations
3. **Testing**: Test configuration changes
4. **Backup**: Backup important configurations
5. **Monitoring**: Monitor configuration changes

## Troubleshooting Configuration

### Common Issues

1. **Invalid YAML**: Check syntax and indentation
2. **Missing Fields**: Verify required fields are present
3. **Port Conflicts**: Ensure ports don't conflict
4. **Dependency Issues**: Check service dependencies
5. **Template Errors**: Verify Jinja2 syntax

### Debug Commands

```bash
# Validate configuration
python terrarium.py check-deps

# Test configuration generation
python terrarium.py deploy --dry-run

# Check generated files
ls -la configs/docker/
ls -la configs/k3s/
```

This configuration guide provides comprehensive information about managing and customizing Edge-Terrarium configurations.
