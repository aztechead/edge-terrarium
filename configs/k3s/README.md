# Kubernetes (K3s) Configuration

This directory contains Kubernetes manifests for deploying the Edge Terrarium project to a K3s cluster. The configuration uses declarative YAML files managed by Kustomize for consistent and maintainable deployments.

## File Structure

```
k3s/
├── namespace.yaml                    # Project namespace
├── vault-*.yaml                     # Vault configuration
├── *-deployment.yaml                # Application deployments
├── services.yaml                    # Service definitions
├── logthon-*.yaml                   # Logthon-specific resources
├── ingress.yaml                     # Ingress routing
├── kustomization.yaml               # Kustomize configuration
└── vault-init-scripts-configmap.yaml # Vault initialization scripts
```

## Configuration Categories

### 1. Namespace (`namespace.yaml`)
**Purpose**: Isolates all Edge Terrarium resources

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: edge-terrarium
```

### 2. Vault Configuration
**Files**: `vault-deployment.yaml`, `vault-service.yaml`, `vault-pvc.yaml`, `vault-config.yaml`

**Purpose**: Provides secrets management for the entire application

**Key Components**:
- **Deployment**: Vault server with persistent storage
- **Service**: ClusterIP service for internal access
- **PVC**: Persistent volume for Vault data
- **ConfigMap**: Vault configuration

**Dependencies**: None (foundational service)

### 3. Vault Initialization (`vault-init-job.yaml`)
**Purpose**: One-time job to initialize Vault with secrets

**Key Features**:
- **Job Type**: Runs once and completes
- **Init Container**: Waits for Vault to be ready
- **Scripts**: Uses enhanced initialization script from ConfigMap
- **TLS Integration**: Mounts TLS certificates from Kubernetes secret

**Dependencies**: Vault deployment must be ready

### 4. Application Deployments
**Files**: `custom-client-deployment.yaml`, `service-sink-deployment.yaml`, `logthon-deployment.yaml`, `file-storage-deployment.yaml`

**Purpose**: Deploy the main application services

**Common Features**:
- **Init Containers**: Wait for dependencies to be ready
- **Health Probes**: Liveness and readiness checks
- **Resource Limits**: CPU and memory constraints
- **Security Context**: Non-root user execution
- **Environment Variables**: Service-specific configuration

**Dependencies**:
- All services wait for `vault-init` job completion
- `custom-client` waits for `logthon` and `file-storage`
- `service-sink` waits for `logthon`
- `file-storage` waits for `logthon`

### 5. Services (`services.yaml`)
**Purpose**: Provides stable network endpoints for pods

**Service Types**:
- **ClusterIP**: Internal service communication
- **LoadBalancer**: External access (logthon UI)

**Service Discovery**: Kubernetes DNS resolution
- `vault-service.edge-terrarium.svc.cluster.local:8200`
- `logthon-service.edge-terrarium.svc.cluster.local:5000`
- `file-storage-service.edge-terrarium.svc.cluster.local:9000`

### 6. Logthon Resources
**Files**: `logthon-service.yaml`, `logthon-ingress-service.yaml`, `logthon-ingress.yaml`

**Purpose**: Provides external access to logthon web UI

**Components**:
- **Service**: LoadBalancer for external access
- **Ingress**: Kong ingress for web UI routing
- **Port Mapping**: Maps to k3d load balancer

### 7. Ingress (`ingress.yaml`)
**Purpose**: Routes external HTTP/HTTPS traffic to services

**Features**:
- **Kong Ingress Controller**: Uses Kong for API gateway functionality
- **TLS Termination**: Automatic HTTPS with custom certificates
- **Path-based Routing**: Routes based on URL patterns
- **Host-based Routing**: Supports multiple hostnames

**Routing Rules**:
| Path | Backend Service | Port |
|------|----------------|------|
| `/fake-provider/*` | custom-client-service | 1337 |
| `/example-provider/*` | custom-client-service | 1337 |
| `/storage/*` | file-storage-service | 9000 |
| `/` (root) | service-sink-service | 8080 |

## Kustomize Configuration (`kustomization.yaml`)

**Purpose**: Manages all Kubernetes resources declaratively

**Features**:
- **Resource Management**: Lists all YAML files to apply
- **Namespace**: Ensures all resources are in the correct namespace
- **Ordering**: Applies resources in dependency order
- **Validation**: Ensures all resources are valid before applying

## Service Dependencies and Startup Order

### 1. Namespace Creation
- Creates the `edge-terrarium` namespace
- All other resources are created within this namespace

### 2. Vault Infrastructure
- **vault-pvc.yaml** → **vault-deployment.yaml** → **vault-service.yaml**
- Vault must be running before initialization

### 3. Vault Initialization
- **vault-init-job.yaml** runs after Vault is ready
- Populates Vault with secrets and TLS certificates
- Job must complete successfully before other services start

### 4. Core Services
- **logthon-deployment.yaml** starts after vault-init completion
- **file-storage-deployment.yaml** starts after logthon is ready

### 5. Application Services
- **custom-client-deployment.yaml** starts after vault-init + logthon + file-storage
- **service-sink-deployment.yaml** starts after vault-init + logthon

### 6. Networking and Access
- **services.yaml** provides internal service discovery
- **logthon-ingress-service.yaml** provides external access to logthon
- **ingress.yaml** provides external access to main application

## Init Container Strategy

Each deployment uses init containers to ensure proper startup order:

```yaml
initContainers:
- name: wait-for-vault-init
  image: curlimages/curl:latest
  command: ['sh', '-c', 'until kubectl get job vault-init -n edge-terrarium -o jsonpath="{.status.conditions[?(@.type==\"Complete\")].status}" | grep -q "True"; do sleep 5; done']
- name: wait-for-logthon
  image: curlimages/curl:latest
  command: ['sh', '-c', 'until curl -f http://logthon-service.edge-terrarium.svc.cluster.local:5000/health; do sleep 5; done']
```

## Health Checks and Probes

### Liveness Probes
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 30
  httpHeaders:
  - name: X-Probe-Type
    value: liveness
```

### Readiness Probes
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 10
  httpHeaders:
  - name: X-Probe-Type
    value: readiness
```

## Resource Management

### Resource Requests and Limits
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

### Security Context
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
```

## Environment Variables

### Vault Integration
```yaml
env:
- name: VAULT_ADDR
  value: "http://vault-service.edge-terrarium.svc.cluster.local:8200"
- name: VAULT_TOKEN
  value: "root"
```

### Service Discovery
```yaml
env:
- name: LOGTHON_HOST
  value: "logthon-ingress-service.edge-terrarium.svc.cluster.local"
- name: LOGTHON_PORT
  value: "5000"
```

## Persistent Storage

### Vault Storage
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vault-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### File Storage
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: file-storage-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

## Deployment Commands

### Apply All Resources
```bash
# Deploy everything
kubectl apply -k configs/k3s/

# Check deployment status
kubectl get all -n edge-terrarium
```

### Individual Resource Management
```bash
# Apply specific resource
kubectl apply -f configs/k3s/vault-deployment.yaml

# Check specific resource
kubectl describe deployment vault -n edge-terrarium

# View logs
kubectl logs -n edge-terrarium deployment/vault
```

### Troubleshooting
```bash
# Check pod status
kubectl get pods -n edge-terrarium

# Describe problematic pod
kubectl describe pod <pod-name> -n edge-terrarium

# Check events
kubectl get events -n edge-terrarium --sort-by='.lastTimestamp'

# Check service endpoints
kubectl get endpoints -n edge-terrarium
```

## Access Points

### External Access
- **Main Application**: `https://localhost:443` (via Kong Ingress)
- **Logthon UI**: `http://localhost:5001` (via LoadBalancer)
- **Vault UI**: `http://localhost:8200` (via port-forward)
- **Kubernetes Dashboard**: `https://localhost:9443` (via LoadBalancer)

### Internal Access
- **Service Discovery**: Kubernetes DNS within cluster
- **Port Forwarding**: Direct pod access for debugging
- **Cluster Internal**: Services communicate via ClusterIP

## Scaling and Updates

### Scaling Deployments
```bash
# Scale a deployment
kubectl scale deployment custom-client --replicas=3 -n edge-terrarium

# Check scaling status
kubectl get deployment custom-client -n edge-terrarium
```

### Rolling Updates
```bash
# Update deployment
kubectl set image deployment/custom-client custom-client=edge-terrarium-custom-client:v2 -n edge-terrarium

# Check rollout status
kubectl rollout status deployment/custom-client -n edge-terrarium

# Rollback if needed
kubectl rollout undo deployment/custom-client -n edge-terrarium
```
