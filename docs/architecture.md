# Architecture Overview

Edge-Terrarium is designed as a modern microservices platform that demonstrates containerization and orchestration best practices.

## System Architecture

### High-Level Architecture

```mermaid
%%{init: {'themeVariables': {'darkMode': true}}}%%
flowchart TD
    subgraph "External Access"
        USER[User/Browser<br/>localhost:443]
    end
    
    subgraph "K3s Cluster"
        subgraph "NGINX Ingress Controller"
            NGINX[NGINX Gateway<br/>LoadBalancer:443]
        end
        
        subgraph "edge-terrarium Namespace"
            subgraph "Application Workloads"
                CC[custom-client Pod<br/>Port 1337]
                SS[service-sink Pod<br/>Port 8080]
                FS[file-storage Pod<br/>Port 9000]
                LT[logthon Pod<br/>Port 5000]
            end
            
            subgraph "Infrastructure"
                VAULT[vault Pod<br/>Port 8200]
            end
        end
    end
    
    %% Request routing
    USER -->|"HTTPS Requests"| NGINX
    NGINX -->|"/api/fake-provider/*<br/>/api/example-provider/*"| CC
    NGINX -->|"/api/storage/*"| FS
    NGINX -->|"/api/logs/*"| LT
    NGINX -->|"/api/ (default)"| SS
    
    %% Internal communication
    CC -->|"Logs"| LT
    CC -->|"File Operations"| FS
    CC -->|"Secrets"| VAULT
    SS -->|"Logs"| LT
    
    classDef external fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef ingress fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef workload fill:#e8f5e8,stroke:#388e3c,stroke-width:2px,color:#000
    classDef infrastructure fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    
    class USER external
    class NGINX ingress
    class CC,SS,FS,LT workload
    class VAULT infrastructure
```

## Component Overview

### Core Services

#### Custom Client (C Application)
- **Purpose**: Handles special API routes and demonstrates C application containerization
- **Port**: 1337
- **Routes**: `/api/fake-provider/*`, `/api/example-provider/*`
- **Features**:
  - Vault integration for secrets management
  - File creation via File Storage API
  - Request logging to Logthon
  - Health check endpoints

#### Service Sink (C Application)
- **Purpose**: Default route handler for unmatched requests
- **Port**: 8080
- **Routes**: `/api/` (catch-all)
- **Features**:
  - Handles all unmatched API requests
  - Request logging to Logthon
  - Health check endpoints

#### File Storage (Python FastAPI)
- **Purpose**: File management and storage operations
- **Port**: 9000
- **Routes**: `/api/storage/*`
- **Features**:
  - CRUD operations for files
  - Automatic file rotation
  - Integration with Logthon for logging
  - RESTful API design

#### Logthon (Python FastAPI)
- **Purpose**: Log aggregation and web UI
- **Port**: 5000
- **Routes**: `/api/logs/*`
- **Features**:
  - Centralized logging from all services
  - Web UI for log browsing
  - File storage viewer
  - Real-time log monitoring

### Infrastructure Services

#### Vault (HashiCorp Vault)
- **Purpose**: Secrets management and secure storage
- **Port**: 8200
- **Features**:
  - KV secrets engine
  - TLS certificate storage
  - Application secret management
  - RESTful API for secret access

#### NGINX (API Gateway)
- **Purpose**: Request routing and load balancing
- **Port**: 443 (HTTPS), 80 (HTTP)
- **Features**:
  - API gateway functionality
  - SSL/TLS termination
  - Request routing based on URL patterns
  - CORS support
  - Health check routing

## Deployment Architectures

### Docker Compose Architecture

```mermaid
%%{init: {'themeVariables': {'darkMode': true}}}%%
flowchart TD
    subgraph "Docker Host"
        subgraph "Docker Network: edge-terrarium"
            subgraph "Core Services"
                V[vault:8200]
                L[logthon:5000]
                F[file-storage:9000]
            end
            
            subgraph "Application Services"
                C[custom-client:1337]
                S[service-sink:8080]
            end
            
            subgraph "Gateway"
                N[nginx:443/80]
            end
        end
        
        subgraph "External Access"
            U[User: localhost:8443]
        end
    end
    
    U -->|"HTTPS"| N
    N -->|"Route by URL"| C
    N -->|"Route by URL"| S
    N -->|"Route by URL"| F
    N -->|"Route by URL"| L
    
    C -->|"Logs"| L
    C -->|"Files"| F
    C -->|"Secrets"| V
    S -->|"Logs"| L
    
    classDef external fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef gateway fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef core fill:#e8f5e8,stroke:#388e3c,stroke-width:2px,color:#000
    classDef app fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    
    class U external
    class N gateway
    class V,L,F core
    class C,S app
```

### K3s Architecture

```mermaid
%%{init: {'themeVariables': {'darkMode': true}}}%%
flowchart TD
    subgraph "K3s Cluster"
        subgraph "ingress-nginx Namespace"
            IC[NGINX Ingress Controller<br/>LoadBalancer:443]
        end
        
        subgraph "edge-terrarium Namespace"
            subgraph "Pods"
                VP[vault Pod]
                LP[logthon Pod]
                FP[file-storage Pod]
                CP[custom-client Pod]
                SP[service-sink Pod]
            end
            
            subgraph "Services"
                VS[vault Service]
                LS[logthon Service]
                FS[file-storage Service]
                CS[custom-client Service]
                SS[service-sink Service]
            end
            
            subgraph "Ingress"
                I[edge-terrarium-ingress]
            end
        end
        
        subgraph "External Access"
            U[User: localhost:8443]
        end
    end
    
    U -->|"Port Forward"| IC
    IC -->|"HTTPS"| I
    I -->|"Route by Host/Path"| CS
    I -->|"Route by Host/Path"| SS
    I -->|"Route by Host/Path"| FS
    I -->|"Route by Host/Path"| LS
    
    CS --> VP
    CS --> LP
    CS --> FS
    SS --> LP
    
    classDef external fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef ingress fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef pod fill:#e8f5e8,stroke:#388e3c,stroke-width:2px,color:#000
    classDef service fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    
    class U external
    class IC,I ingress
    class VP,LP,FP,CP,SP pod
    class VS,LS,FS,CS,SS service
```

## Request Flow

### External Request Processing

1. **User Request**: Browser sends HTTPS request to `localhost:8443`
2. **Gateway Routing**: NGINX receives request and routes based on URL pattern
3. **Service Processing**: Target service processes the request
4. **Internal Communication**: Service may communicate with other services
5. **Response**: Service returns response through NGINX to user

### Internal Service Communication

```mermaid
%%{init: {'themeVariables': {'darkMode': true}}}%%
sequenceDiagram
    participant U as User
    participant N as NGINX
    participant C as Custom Client
    participant V as Vault
    participant F as File Storage
    participant L as Logthon

    U->>N: GET /api/fake-provider/test
    N->>C: Route to custom-client
    C->>V: Get secrets
    V->>C: Return secrets
    C->>F: Create file
    F->>C: File created
    C->>L: Log request
    C->>N: Response
    N->>U: Response
```

## Security Architecture

### Network Security

- **Internal Communication**: Services communicate over internal networks
- **TLS Termination**: NGINX handles SSL/TLS encryption
- **Namespace Isolation**: K3s namespaces provide logical separation
- **Service Mesh**: Internal traffic is encrypted and authenticated

### Secrets Management

- **Centralized Storage**: All secrets stored in Vault
- **Encrypted at Rest**: Secrets encrypted using Vault's encryption
- **Access Control**: Token-based authentication
- **No Hardcoded Secrets**: Applications retrieve secrets at runtime

## Scalability Considerations

### Horizontal Scaling

- **Stateless Services**: All services designed to be stateless
- **Load Balancing**: NGINX distributes traffic across instances
- **Service Discovery**: Kubernetes provides automatic service discovery
- **Health Checks**: Automatic health monitoring and failover

### Resource Management

- **Resource Limits**: CPU and memory limits defined for each service
- **Resource Requests**: Minimum resources guaranteed for each service
- **Auto-scaling**: Services can be scaled based on demand
- **Resource Monitoring**: Built-in monitoring and alerting

## Monitoring and Observability

### Logging

- **Centralized Logging**: All services send logs to Logthon
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Log Aggregation**: Real-time log collection and display
- **Log Retention**: Configurable log retention policies

### Health Monitoring

- **Health Endpoints**: Each service exposes health check endpoints
- **Liveness Probes**: Kubernetes monitors service health
- **Readiness Probes**: Ensures services are ready to receive traffic
- **Startup Probes**: Monitors service startup time

### Metrics and Alerting

- **Service Metrics**: Request counts, response times, error rates
- **Resource Metrics**: CPU, memory, and network usage
- **Custom Metrics**: Application-specific metrics
- **Alerting**: Configurable alerts for service issues

## Configuration Management

### Dynamic Configuration

- **Template-based**: Jinja2 templates for consistent configuration
- **Environment-specific**: Different configs for Docker vs K3s
- **Auto-generation**: Configurations generated from app definitions
- **Version Control**: All configurations tracked in Git

### Application Configuration

- **App-based**: Each application defines its own configuration
- **Dependency Management**: Automatic dependency resolution
- **Environment Variables**: Runtime configuration via environment variables
- **Secrets Integration**: Secure secret injection from Vault

This architecture provides a solid foundation for understanding modern microservices patterns, containerization, and orchestration technologies.
