# Getting Started Guide

This guide will help you get up and running with Edge-Terrarium quickly.

## Prerequisites

### Required Software
- **Docker Desktop** (includes Docker Compose)
- **k3d** (K3s in Docker) - [Installation Guide](https://k3d.io/v5.4.6/#installation)
- **kubectl** (K3s command-line tool)
- **curl** (for testing HTTP endpoints)

### System Requirements
- **macOS/Linux**: Native support
- **Windows**: WSL2 (Windows Subsystem for Linux) - [WSL2 Setup Guide](https://docs.microsoft.com/en-us/windows/wsl/install)

### Knowledge Assumptions
- Basic command-line usage
- Understanding of HTTP requests and responses
- Familiarity with JSON format

## Quick Start

### Option 1: Docker (Recommended to start here)
```bash
# Clone the repository
git clone <repository-url>
cd edge-terrarium

# Install Python dependencies
pip install -r requirements.txt

# Deploy with Docker Compose
python3 terrarium.py deploy docker

# Test the application
python3 terrarium.py test
```

### Option 2: K3s (Recommended if you're familiar with containers)
```bash
# Deploy to K3s
python3 terrarium.py deploy k3s

# Test the application
python3 terrarium.py test
```

## Available CLI Commands

### Main CLI Tool (`python3 terrarium.py`)
```bash
# Syntax: python3 terrarium.py [COMMAND] [OPTIONS]

# COMMAND options:
deploy    # Deploy the application (Docker or K3s)
build     # Build Docker images
test      # Test the deployed application
add-app   # Add a new application to the platform
vault     # Vault management operations

# Examples:
python3 terrarium.py deploy docker    # Deploy to Docker Compose
python3 terrarium.py deploy k3s       # Deploy to K3s (auto-creates k3d cluster if needed)
python3 terrarium.py test             # Test current deployment
python3 terrarium.py build            # Build all Docker images
python3 terrarium.py add-app          # Interactive app creation wizard
python3 terrarium.py vault init       # Initialize Vault with secrets
python3 terrarium.py vault status     # Check Vault status
```

### Command Options
```bash
# Global options:
--verbose, -v     # Enable verbose output
--quiet, -q       # Suppress output except errors
--help, -h        # Show help message
--version         # Show version information

# Deploy options:
python3 terrarium.py deploy docker --verbose    # Deploy with detailed output
python3 terrarium.py deploy k3s --quiet         # Deploy with minimal output

# Test options:
python3 terrarium.py test --verbose             # Test with detailed output
```

## Dynamic Configuration System

The platform features a **dynamic configuration system** that automatically generates all deployment files from templates:

- **Auto-Generated Files**: All Docker Compose and K3s manifests are generated from templates
- **App-Based Configuration**: Each application defines its own configuration in `app-config.yml`
- **Dynamic Routing**: NGINX routing rules are automatically generated from app route definitions
- **Template System**: Uses Jinja2 templates for consistent, maintainable configuration generation
- **No Manual Editing**: All generated files include warnings and are ignored by Git

**Usage Examples**:
```bash
# Deploy to Docker Compose (auto-generates configs)
python3 terrarium.py deploy docker

# Deploy to K3s (auto-generates configs)
python3 terrarium.py deploy k3s

# Build images only
python3 terrarium.py build

# Add a new application
python3 terrarium.py add-app
```

**Goal**: Get the application running in 5 minutes, then explore each component.

> **Note**: This repository has been cleaned up to remove unused files. All functionality remains intact and working in both Docker and K3s environments. Service-specific documentation is available in individual service directories.

## Next Steps

Once you have the application running:

1. **Explore the Learning Path** - Follow the [Learning Path Guide](learning-path.md) for a structured approach
2. **Understand the Architecture** - Check out the [Architecture Overview](architecture.md)
3. **Test the Application** - Use the [Testing Guide](testing.md) to verify everything works
4. **Troubleshoot Issues** - Refer to the [Troubleshooting Guide](troubleshooting.md) if you encounter problems
