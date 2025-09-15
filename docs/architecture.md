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

## CLI Architecture (New Modular Design)

The Edge-Terrarium CLI has been completely redesigned with a modern, modular architecture that provides better separation of concerns and maintainability.

### CLI Architecture Overview

```mermaid
%%{init: {'themeVariables': {'darkMode': true}}}%%
flowchart TD
    subgraph "User Interface"
        USER[User Commands<br/>uv run terrarium.py]
    end
    
    subgraph "CLI Layer"
        MAIN[main.py<br/>CLI Entry Point]
        COMMANDS[commands/<br/>Command Implementations]
        DEPLOY[deploy.py<br/>914 lines ↓29.4%]
        BUILD[build.py]
        TEST[test.py]
        VAULT[vault.py]
        OTHER[Other Commands...]
    end
    
    subgraph "Core Layer"
        CORE_DEPLOY[deployment/<br/>Common Helpers]
        CORE_INFRA[infrastructure/<br/>Database & Vault]
    end
    
    subgraph "Platform Layer"
        DOCKER_MGR[docker/<br/>DockerDeploymentManager]
        K3S_MGR[k3s/<br/>K3sDeploymentManager]
    end
    
    subgraph "Config Layer"
        LOADERS[loaders/<br/>Configuration Loading]
        GENERATORS[generators/<br/>Config Generation]
        TEMPLATES[templates/<br/>Jinja2 Templates]
    end
    
    subgraph "Utils Layer"
        SYSTEM[system/<br/>Shell & Dependencies]
        VALIDATION[validation/<br/>YAML Validation]
        COLORS[colors.py]
        LOGGING[logging.py]
    end
    
    USER --> MAIN
    MAIN --> COMMANDS
    COMMANDS --> DEPLOY
    COMMANDS --> BUILD
    COMMANDS --> TEST
    COMMANDS --> VAULT
    COMMANDS --> OTHER
    
    DEPLOY --> DOCKER_MGR
    DEPLOY --> K3S_MGR
    
    DOCKER_MGR --> CORE_DEPLOY
    K3S_MGR --> CORE_DEPLOY
    
    DOCKER_MGR --> CORE_INFRA
    K3S_MGR --> CORE_INFRA
    
    COMMANDS --> LOADERS
    COMMANDS --> GENERATORS
    GENERATORS --> TEMPLATES
    
    COMMANDS --> SYSTEM
    COMMANDS --> VALIDATION
    COMMANDS --> COLORS
    COMMANDS --> LOGGING
    
    classDef user fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef cli fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef core fill:#e8f5e8,stroke:#388e3c,stroke-width:2px,color:#000
    classDef platform fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef config fill:#fff8e1,stroke:#fbc02d,stroke-width:2px,color:#000
    classDef utils fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    
    class USER user
    class MAIN,COMMANDS,DEPLOY,BUILD,TEST,VAULT,OTHER cli
    class CORE_DEPLOY,CORE_INFRA core
    class DOCKER_MGR,K3S_MGR platform
    class LOADERS,GENERATORS,TEMPLATES config
    class SYSTEM,VALIDATION,COLORS,LOGGING utils
```

### Layer Responsibilities

#### 🎯 CLI Layer (`terrarium_cli/cli/`)
**Purpose**: User interface and command handling
- **Entry Point**: `main.py` - CLI argument parsing and command routing
- **Commands**: Individual command implementations with clear responsibilities
- **Optimization**: Main deploy.py reduced from 1,294 to 914 lines (29.4% reduction)

#### 🧠 Core Layer (`terrarium_cli/core/`)
**Purpose**: Core business logic and shared functionality
- **Deployment**: Common deployment helpers used by all platforms
- **Infrastructure**: Database, Vault, and infrastructure service utilities

#### 🚀 Platform Layer (`terrarium_cli/platforms/`)
**Purpose**: Platform-specific deployment implementations
- **Docker Manager**: Complete Docker Compose orchestration
- **K3s Manager**: Complete Kubernetes/K3s orchestration
- **Isolation**: Platform-specific logic cleanly separated

#### ⚙️ Config Layer (`terrarium_cli/config/`)
**Purpose**: Configuration management and generation
- **Loaders**: Application configuration parsing and loading
- **Generators**: Dynamic configuration file generation
- **Templates**: Jinja2 templates for all generated configurations

#### 🔧 Utils Layer (`terrarium_cli/utils/`)
**Purpose**: Shared utilities and helpers
- **System**: Shell command execution and dependency checking
- **Validation**: YAML configuration validation
- **Common**: Colors, logging, and other shared utilities

### Key Architectural Benefits

#### **Separation of Concerns**
Each layer has a single, well-defined responsibility:
- CLI handles user interaction
- Core provides business logic
- Platform handles deployment specifics
- Config manages configuration
- Utils provides shared functionality

#### **Platform Abstraction**
Deployment logic is cleanly separated by platform:
```python
# Docker deployment
docker_manager = DockerDeploymentManager()
docker_manager.deploy(dependencies, cleanup_k3s)

# K3s deployment  
k3s_manager = K3sDeploymentManager()
k3s_manager.deploy(dependencies, cleanup_docker, certificates, images)
```

#### **Modular Import Structure**
Clear, logical import paths:
```python
# CLI commands
from terrarium_cli.cli.commands.deploy import DeployCommand

# Platform managers
from terrarium_cli.platforms.docker.docker_manager import DockerDeploymentManager
from terrarium_cli.platforms.k3s.k3s_manager import K3sDeploymentManager

# Core functionality
from terrarium_cli.core.deployment.common import CommonDeploymentHelpers

# Configuration management
from terrarium_cli.config.loaders.app_loader import AppLoader
from terrarium_cli.config.generators.generator import ConfigGenerator

# System utilities
from terrarium_cli.utils.system.shell import run_command
from terrarium_cli.utils.validation.yaml_validator import validate_all_app_configs
```

#### **Extensibility**
The modular design makes it easy to:
- Add new deployment platforms (e.g., `platforms/aws/`, `platforms/gcp/`)
- Add new commands (e.g., `cli/commands/monitor.py`)
- Add new configuration generators (e.g., `config/generators/helm_generator.py`)
- Add new utilities (e.g., `utils/monitoring/`)

#### **Maintainability**
- **29.4% code reduction** in main deployment file
- **Clear ownership**: Each module has a specific purpose
- **Reduced coupling**: Modules interact through well-defined interfaces
- **Easy testing**: Each layer can be tested independently

### Deployment Flow

```mermaid
%%{init: {'themeVariables': {'darkMode': true}}}%%
sequenceDiagram
    participant User
    participant CLI as CLI Layer
    participant Platform as Platform Layer
    participant Core as Core Layer
    participant Config as Config Layer
    participant Utils as Utils Layer
    
    User->>CLI: uv run terrarium.py deploy docker
    CLI->>Utils: Validate dependencies
    CLI->>Config: Load app configurations
    Config->>Config: Generate Docker Compose files
    CLI->>Platform: DockerDeploymentManager.deploy()
    Platform->>Core: Generate certificates
    Platform->>Utils: Execute shell commands
    Platform->>Core: Build and start services
    Platform->>Core: Verify deployment
    Platform->>CLI: Return success/failure
    CLI->>User: Display results
```

This modular CLI architecture provides a solid foundation for managing complex deployment orchestration while maintaining clean separation of concerns and enabling easy extension and maintenance.

## Summary

This architecture provides a solid foundation for understanding modern microservices patterns, containerization, orchestration technologies, and clean software architecture principles.
