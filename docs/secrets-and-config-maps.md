# Secrets and Config Maps Management

This document explains how secrets and configuration data are managed in the Edge Terrarium project, including how they flow from configuration files into Vault (Docker) and Kubernetes Secrets (K3s), and how applications access them.

## Overview

The Edge Terrarium project uses a dual approach for secrets management:

- **Docker Environment**: Uses HashiCorp Vault for centralized secrets management
- **K3s Environment**: Uses Kubernetes Secrets for native Kubernetes integration

Both approaches provide secure storage and access to sensitive configuration data like API keys, database passwords, and TLS certificates.

## Architecture

```mermaid
graph TB
    subgraph "Configuration Sources"
        A[configs/vault-secrets.yml] --> B[Vault Initialization]
        C[app-config.yml files] --> D[Database Credentials]
        E[TLS Certificates] --> F[Certificate Storage]
    end
    
    subgraph "Docker Environment"
        B --> G[Vault Container]
        G --> H[Applications via HTTP API]
        D --> G
        F --> G
    end
    
    subgraph "K3s Environment"
        B --> I[Kubernetes Secrets]
        D --> I
        F --> I
        I --> J[Applications via Environment Variables]
    end
    
    subgraph "Application Access"
        H --> K[Vault HTTP API Calls]
        J --> L[Environment Variables]
        K --> M[Runtime Configuration]
        L --> M
    end
```

## Configuration Sources

### 1. Vault Secrets Configuration (`configs/vault-secrets.yml`)

This is the primary configuration file for static secrets that need to be available to applications.

```yaml
secrets:
  # Application-specific secrets
  custom-client/config:
    api_key: "mock-api-key-12345"
    database_url: "postgresql://user:pass@db:5432/app"
    jwt_secret: "mock-jwt-secret-67890"
    encryption_key: "mock-encryption-key-abcdef"
    log_level: "INFO"
    max_connections: "100"
  
  # External service configurations
  custom-client/external-apis:
    file_storage_url: "http://file-storage:9000"
    logthon_url: "http://logthon:5000"
  
  # TLS certificates
  terrarium/tls:
    cert: "mock-tls-cert"
    key: "mock-tls-key"
```

**Key Points:**
- Secrets are organized by application and purpose
- Uses a hierarchical path structure (`app/component`)
- Supports both static values and references to other services
- Automatically loaded during Vault initialization

### 2. Application Configuration (`apps/*/app-config.yml`)

Each application can define its own configuration requirements, including database credentials and environment variables.

```yaml
# Database configuration
databases:
  - name: test_app_db
    type: postgresql
    version: "15"
    port_forward: true
    init_scripts:
      - init/schema.sql
      - init/seed.sql

# Environment variables
environment:
  - name: SERVICE_NAME
    value: "my-app"
  - name: API_KEY
    value_from: "vault:secret/myapp#api_key"  # Future feature
```

**Key Points:**
- Database credentials are auto-generated and stored securely
- Environment variables can reference Vault secrets
- Supports both static values and dynamic secret references

### 3. TLS Certificates (`certs/`)

TLS certificates are automatically detected and stored in Vault if present.

```
certs/
├── edge-terrarium.crt    # Certificate file
└── edge-terrarium.key    # Private key file
```

## Secret Flow and Processing

### Docker Environment Flow

1. **Vault Deployment**: Vault container starts with dev mode enabled
2. **Port Forwarding**: Vault port (8200) is forwarded to localhost
3. **Vault Initialization**: 
   - KV secrets engine is enabled
   - Secrets from `vault-secrets.yml` are loaded
   - TLS certificates are base64-encoded and stored
   - Database credentials are generated and stored
4. **Application Access**: Applications make HTTP API calls to Vault

### K3s Environment Flow

1. **Vault Deployment**: Vault is deployed as a Kubernetes service
2. **Vault Initialization**: Same as Docker, but via port forwarding
3. **Kubernetes Secrets Generation**: 
   - Database credentials are stored as Kubernetes Secrets
   - Secrets are mounted as environment variables in pods
4. **Application Access**: Applications read from environment variables

## Secret Storage Formats

### Vault Storage Format

Secrets are stored in Vault using the KV v2 secrets engine:

```
/v1/secret/data/{app}/{component}
```

**Example:**
```json
{
  "data": {
    "data": {
      "api_key": "mock-api-key-12345",
      "database_url": "postgresql://user:pass@db:5432/app",
      "jwt_secret": "mock-jwt-secret-67890"
    }
  }
}
```

### Kubernetes Secrets Format

Database credentials are stored as Kubernetes Secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {app-name}-db-secrets
  namespace: edge-terrarium
type: Opaque
data:
  password: <base64-encoded-password>
  host: <base64-encoded-host>
  port: <base64-encoded-port>
  username: <base64-encoded-username>
  database_name: <base64-encoded-db-name>
  url: <base64-encoded-connection-url>
```

## Application Access Patterns

### Docker Environment Access

Applications access Vault secrets via HTTP API calls:

```c
// C application example
int get_vault_secret(const char* secret_path, const char* key, char* output, size_t output_size) {
    // Make HTTP request to Vault API
    // GET /v1/secret/data/{secret_path}
    // Headers: X-Vault-Token: root
}

// Retrieve all secrets for an application
int retrieve_vault_secrets(vault_secrets_t* secrets) {
    get_vault_secret("custom-client/config", "api_key", secrets->api_key, sizeof(secrets->api_key));
    get_vault_secret("custom-client/config", "database_url", secrets->database_url, sizeof(secrets->database_url));
    // ... more secrets
}
```

**Authentication Methods:**
1. **Static Token**: Uses `VAULT_TOKEN=root` (development mode)
2. **Kubernetes Auth**: Uses service account tokens (production mode)
3. **Fallback**: Static token if Kubernetes auth fails

### K3s Environment Access

Applications access secrets via environment variables:

```yaml
# In Kubernetes deployment
env:
- name: POSTGRES_DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: test-db-app-db-secrets
      key: password
- name: POSTGRES_DB_HOST
  valueFrom:
    secretKeyRef:
      name: test-db-app-db-secrets
      key: host
```

**Environment Variable Naming:**
- Database credentials: `{DB_TYPE}_DB_{FIELD}` (e.g., `POSTGRES_DB_HOST`)
- Application secrets: Direct environment variables

## Database Credential Management

### Automatic Generation

Database credentials are automatically generated when an application defines a database in its `app-config.yml`:

```yaml
databases:
  - name: test_app_db
    type: postgresql
    version: "15"
```

**Generated Credentials:**
- **Username**: `{app_name}_{db_name}_user`
- **Password**: 32-character random string
- **Database Name**: `{db_name}`
- **Host**: `{app_name}-db` (Kubernetes service name)
- **Port**: `5432` (PostgreSQL default)

### Storage Locations

**Docker**: Stored in Vault at `/{app_name}/database/{db_name}`
**K3s**: Stored as Kubernetes Secret `{app_name}-db-secrets`

## Security Considerations

### Development Mode

- Vault runs in dev mode with root token authentication
- TLS certificates are base64-encoded but not encrypted
- Secrets are stored in plain text in configuration files

### Production Recommendations

1. **Vault Production Mode**: Enable Vault production mode with proper authentication
2. **Encryption**: Use Vault's encryption capabilities for sensitive data
3. **Access Control**: Implement proper RBAC policies
4. **Secret Rotation**: Implement secret rotation policies
5. **Audit Logging**: Enable Vault audit logging

## Troubleshooting

### Common Issues

1. **Vault Not Accessible**
   - Check if Vault port forwarding is active
   - Verify Vault container is running
   - Check Vault logs for errors

2. **Secrets Not Found**
   - Verify secrets are loaded during initialization
   - Check secret paths match application expectations
   - Verify Vault authentication is working

3. **Database Connection Issues**
   - Check if database credentials are generated
   - Verify Kubernetes secrets are created
   - Check environment variables in pod

### Debugging Commands

```bash
# Check Vault status
python3 terrarium.py vault status

# List Vault secrets
python3 terrarium.py vault secrets

# Get specific secret
python3 terrarium.py vault get custom-client/config

# Check Kubernetes secrets
kubectl get secrets -n edge-terrarium

# Check pod environment variables
kubectl exec -it {pod-name} -n edge-terrarium -- env | grep -E "(DB_|VAULT_)"
```

## Configuration Examples

### Adding New Application Secrets

1. **Add to `vault-secrets.yml`:**
```yaml
secrets:
  my-new-app/config:
    api_key: "your-api-key"
    database_url: "postgresql://user:pass@host:5432/db"
```

2. **Update application code:**
```c
// Retrieve secrets from Vault
get_vault_secret("my-new-app/config", "api_key", api_key, sizeof(api_key));
```

### Adding Database to Application

1. **Update `app-config.yml`:**
```yaml
databases:
  - name: my_database
    type: postgresql
    version: "15"
    port_forward: true
```

2. **Access in application:**
```c
// Environment variables will be available
char* db_host = getenv("POSTGRES_DB_HOST");
char* db_password = getenv("POSTGRES_DB_PASSWORD");
```

## Future Enhancements

### Planned Features

1. **Secret References**: Support for `value_from: "vault:secret/path#key"` in app-config.yml
2. **Secret Rotation**: Automatic secret rotation capabilities
3. **Encryption**: End-to-end encryption for sensitive data
4. **Audit Logging**: Comprehensive audit trail for secret access
5. **Multi-Environment**: Support for different secret sets per environment

### Integration Points

- **CI/CD**: Automatic secret injection during deployment
- **Monitoring**: Secret access monitoring and alerting
- **Compliance**: Audit and compliance reporting
- **Backup**: Secret backup and recovery procedures

## Related Documentation

- [Architecture Overview](architecture.md)
- [Service Communication](service-communication.md)
- [Development Guide](development.md)
- [Troubleshooting Guide](troubleshooting.md)
