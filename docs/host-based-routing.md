# Host-Based Routing Configuration

This document explains how to configure host-based routing in the Edge Terrarium project, allowing you to route requests based on the hostname (like `mycoolwebsite.company.com`) to specific applications.

## 🌐 Overview

### Traditional Path-Based Routing
```
https://edge-terrarium.local/api/storage/* → file-storage service
https://edge-terrarium.local/api/logs/*    → logthon service
```

### New Host-Based Routing
```
https://mycoolwebsite.company.com/*        → proxy-gateway service
https://api.company.com/v1/*               → api-gateway service
https://admin.company.com/*                → admin-panel service
```

## 🔧 Configuration

### App Configuration Structure

Add host-based routes to your `app-config.yml`:

```yaml
routes:
  # Host-based routing - all requests to mycoolwebsite.company.com
  - path: /*
    target: /
    strip_prefix: false
    host: mycoolwebsite.company.com
    priority: 100
    
  # API endpoints for the same domain
  - path: /api/*
    target: /api/
    strip_prefix: true
    host: mycoolwebsite.company.com
    priority: 200
    
  # Fallback route for default domain
  - path: /myapp/*
    target: /
    strip_prefix: true
    priority: 50
```

### Route Configuration Options

| Field | Description | Example | Default |
|-------|-------------|---------|---------|
| `path` | URL path pattern | `/api/*`, `/*` | Required |
| `target` | Target path in your app | `/`, `/api/` | Required |
| `strip_prefix` | Remove matched path before forwarding | `true`, `false` | `true` |
| `host` | Hostname for routing | `mycoolwebsite.company.com` | `null` (uses default) |
| `priority` | Route priority (higher = more important) | `100`, `200` | `0` |

## 🚀 Use Cases

### 1. Reverse Proxy / API Gateway

Create an app that receives requests for external domains and forwards them:

```yaml
name: external-proxy
routes:
  - path: /*
    target: /
    strip_prefix: false
    host: mycoolwebsite.company.com
    priority: 100
```

Your app can then:
- Authenticate requests
- Transform data
- Forward to upstream services
- Add logging/monitoring
- Handle rate limiting

### 2. Multi-Tenant Applications

Route different customers to the same app with different configurations:

```yaml
name: multi-tenant-app
routes:
  - path: /*
    target: /
    strip_prefix: false
    host: customer1.myapp.com
    priority: 100
    
  - path: /*
    target: /
    strip_prefix: false
    host: customer2.myapp.com
    priority: 100
```

### 3. API Versioning by Domain

Route different API versions to different services:

```yaml
# v1-api-service
routes:
  - path: /*
    target: /
    strip_prefix: false
    host: v1.api.company.com
    priority: 100

# v2-api-service  
routes:
  - path: /*
    target: /
    strip_prefix: false
    host: v2.api.company.com
    priority: 100
```

## 🔀 Route Matching Order

Routes are matched in this order:

1. **Priority** (highest first)
2. **Specificity** (most specific path first)
3. **Host matching** (exact host match vs default)

Example matching order:
```yaml
# 1. Highest priority, specific path, specific host
- path: /api/v2/users/*
  host: api.company.com
  priority: 300

# 2. High priority, specific host, general path  
- path: /*
  host: mycoolwebsite.company.com
  priority: 200

# 3. Medium priority, default host, specific path
- path: /api/storage/*
  priority: 100

# 4. Low priority, default host, general path
- path: /*
  priority: 50
```

## 🔐 TLS/SSL Configuration

The system automatically configures TLS for all hosts defined in routes. The same certificate is used for all domains, so make sure your certificate includes all the domains as Subject Alternative Names (SANs).

### Certificate Requirements

Your TLS certificate should include:
- `edge-terrarium.local` (default domain)
- `mycoolwebsite.company.com` (custom domain)
- Any other custom domains you define

## 🐳 Docker vs K3s Behavior

### Docker Environment
- Host-based routing works through the NGINX container
- Access via `https://localhost:8443`
- Add custom domains to your `/etc/hosts` file:
  ```
  127.0.0.1 mycoolwebsite.company.com
  ```

### K3s Environment  
- Host-based routing works through the NGINX Ingress Controller
- Access via the cluster's external IP
- DNS configuration required for custom domains

## 📝 Example Implementation

Here's a complete example of a proxy application:

```yaml
# apps/proxy-gateway/app-config.yml
name: proxy-gateway
description: "Handles requests for external domains"

docker:
  build_context: .
  dockerfile: Dockerfile

runtime:
  port: 8080
  health_check_path: /health

routes:
  # Handle all requests to mycoolwebsite.company.com
  - path: /*
    target: /
    strip_prefix: false
    host: mycoolwebsite.company.com
    priority: 100

environment:
  - name: UPSTREAM_URL
    value: "https://internal-service.company.com"
  - name: LOG_REQUESTS
    value: "true"

health_checks:
  liveness:
    http_get:
      path: /health
      port: 8080
```

```python
# apps/proxy-gateway/main.py
from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

UPSTREAM_URL = os.getenv("UPSTREAM_URL", "https://example.com")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request, path: str):
    """Forward all requests to upstream service"""
    
    # Get the original request details
    method = request.method
    headers = dict(request.headers)
    body = await request.body()
    
    # Remove hop-by-hop headers
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Forward to upstream
    async with httpx.AsyncClient() as client:
        upstream_url = f"{UPSTREAM_URL}/{path}"
        response = await client.request(
            method=method,
            url=upstream_url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
    return response.content
```

## 🧪 Testing Host-Based Routing

1. **Add the custom domain to your hosts file:**
   ```bash
   # For Docker
   echo "127.0.0.1 mycoolwebsite.company.com" >> /etc/hosts
   
   # For K3s (use cluster IP)
   echo "172.18.0.3 mycoolwebsite.company.com" >> /etc/hosts
   ```

2. **Deploy your application:**
   ```bash
   terrarium.py deploy k3s
   ```

3. **Test the routing:**
   ```bash
   # Should route to your proxy-gateway app
   curl -k https://mycoolwebsite.company.com:8443/
   
   # Should still route to default services
   curl -k https://edge-terrarium.local:8443/api/storage/
   ```

## 🔧 Troubleshooting

### Common Issues

1. **Route not matching**: Check priority and specificity order
2. **TLS errors**: Ensure certificate includes all domains
3. **DNS resolution**: Verify `/etc/hosts` or DNS configuration
4. **Port conflicts**: Ensure different apps use different ports

### Debugging

Check the generated ingress configuration:
```bash
kubectl get ingress -n edge-terrarium -o yaml
```

View NGINX logs:
```bash
kubectl logs -n edge-terrarium deployment/nginx
```

## 🎯 Best Practices

1. **Use high priorities** (100+) for host-based routes
2. **Test route ordering** with multiple domains
3. **Include health checks** for all proxy applications  
4. **Log requests** for debugging and monitoring
5. **Handle upstream failures** gracefully
6. **Validate certificates** include all required domains
7. **Use environment variables** for upstream configuration

This host-based routing system gives you powerful control over how external requests are handled and routed within your Edge Terrarium deployment!
