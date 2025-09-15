# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with Edge-Terrarium.

## Understanding Console Output

### Expected vs. Actual Errors

The Edge-Terrarium CLI uses intelligent error handling to suppress expected failures and show clean, informative messages:

#### **Clean Output Messages (Normal Behavior)**
These messages indicate expected behavior and are **not errors**:

```
vault health check failed (curl not available or endpoint not ready)
PVCs are still binding (this is normal for WaitForFirstConsumer mode)
No port forwarding processes found
```

#### **What These Mean**:
- **Vault curl check**: Some containers don't have `curl` installed, which is normal. The system falls back to other health check methods.
- **PVC binding delays**: K3s uses `WaitForFirstConsumer` mode, so PVCs only bind when pods actually need them.
- **Port forwarding**: The system cleans up old port forwarding processes before setting up new ones.

#### **Actual Error Indicators**
Real errors that need attention will be clearly marked with:
- ❌ **Red error messages** with specific failure reasons
- **Non-zero exit codes** from the CLI
- **Stack traces** for unexpected failures
- **Deployment verification failures**

### Console Output Improvements

The CLI has been enhanced with:
- **Intelligent error suppression** for expected failures
- **User-friendly messages** instead of technical error logs
- **Clear success indicators** with ✓ checkmarks
- **Informative warnings** that explain expected behaviors

## Common Issues

### Deployment Issues

#### Docker Compose Deployment Fails
**Symptoms**: `docker-compose up` fails or services don't start

**Solutions**:
1. Check Docker is running:
   ```bash
   docker --version
   docker-compose --version
   ```

2. Check for port conflicts:
   ```bash
   lsof -i :8443  # Check if port 8443 is in use
   ```

3. Clean up and retry:
   ```bash
   docker-compose down
   docker system prune -f
   uv run python terrarium.py deploy docker
   ```

#### K3s Cluster Creation Fails
**Symptoms**: `k3d cluster create` fails or cluster is unhealthy

**Solutions**:
1. Check k3d installation:
   ```bash
   k3d --version
   kubectl version --client
   ```

2. Clean up existing clusters:
   ```bash
   k3d cluster list
   k3d cluster delete edge-terrarium
   ```

3. Check system resources:
   ```bash
   docker system df
   docker system prune -f
   ```

4. Retry deployment:
   ```bash
   uv run python terrarium.py deploy k3s
   ```

### Service Issues

#### Services Not Starting
**Symptoms**: Pods/containers in CrashLoopBackOff or not ready

**Solutions**:
1. Check service logs:
   ```bash
   # Docker
   docker logs <container-name>
   
   # K3s
   kubectl logs -n edge-terrarium <pod-name>
   ```

2. Check service configuration:
   ```bash
   # Verify app-config.yml files
   cat apps/<service-name>/app-config.yml
   ```

3. Check dependencies:
   ```bash
   uv run python terrarium.py check-deps
   ```

#### Services Not Accessible
**Symptoms**: 404 errors or connection refused

**Solutions**:
1. Check service status:
   ```bash
   # Docker
   docker ps
   
   # K3s
   kubectl get pods -n edge-terrarium
   kubectl get services -n edge-terrarium
   ```

2. Check port forwarding (K3s):
   ```bash
   kubectl port-forward -n edge-terrarium svc/nginx-service 8443:443
   ```

3. Check ingress configuration:
   ```bash
   kubectl get ingress -n edge-terrarium
   kubectl describe ingress -n edge-terrarium
   ```

### Network Issues

#### Services Can't Communicate
**Symptoms**: Internal service calls fail

**Solutions**:
1. Check network connectivity:
   ```bash
   # Docker
   docker network ls
   docker network inspect edge-terrarium_default
   
   # K3s
   kubectl get networkpolicies -n edge-terrarium
   ```

2. Check DNS resolution:
   ```bash
   # Docker
   docker exec <container> nslookup <service-name>
   
   # K3s
   kubectl exec -n edge-terrarium <pod> -- nslookup <service-name>
   ```

3. Check service discovery:
   ```bash
   kubectl get endpoints -n edge-terrarium
   ```

### Vault Issues

#### Vault Not Accessible
**Symptoms**: Applications can't retrieve secrets

**Solutions**:
1. Check Vault status:
   ```bash
   # Docker
   docker logs vault
   
   # K3s
   kubectl logs -n edge-terrarium vault-pod
   ```

2. Check Vault initialization:
   ```bash
   # Test Vault API
   curl -k https://localhost:8443/api/vault/v1/sys/health
   ```

3. Reinitialize Vault:
   ```bash
   uv run python terrarium.py vault init
   ```

#### Secrets Not Found
**Symptoms**: Applications report missing secrets

**Solutions**:
1. Check secrets in Vault:
   ```bash
   uv run python terrarium.py vault list
   ```

2. Verify secret paths:
   ```bash
   uv run python terrarium.py vault get custom-client/config
   ```

3. Check vault-secrets.yml:
   ```bash
   cat configs/vault-secrets.yml
   ```

### Logging Issues

#### Logs Not Appearing
**Symptoms**: No logs in logthon or missing request logs

**Solutions**:
1. Check logthon service:
   ```bash
   # Docker
   docker logs logthon
   
   # K3s
   kubectl logs -n edge-terrarium logthon-pod
   ```

2. Check log configuration:
   ```bash
   # Verify log levels in app-config.yml
   grep -r "log_level" apps/
   ```

3. Check log storage:
   ```bash
   # Check if log files are being created
   ls -la /tmp/requests/
   ```

## Debug Commands

### System Information
```bash
# Check system resources
docker system df
kubectl top nodes
kubectl top pods -n edge-terrarium

# Check service status
docker ps
kubectl get all -n edge-terrarium
```

### Service Debugging
```bash
# Check service logs
docker logs <container> --tail 100
kubectl logs -n edge-terrarium <pod> --tail 100

# Check service configuration
docker inspect <container>
kubectl describe pod -n edge-terrarium <pod>
```

### Network Debugging
```bash
# Check network connectivity
docker exec <container> ping <service>
kubectl exec -n edge-terrarium <pod> -- ping <service>

# Check port accessibility
telnet localhost 8443
kubectl port-forward -n edge-terrarium svc/nginx-service 8443:443
```

## Performance Issues

### High Resource Usage
**Symptoms**: Slow response times or system resource exhaustion

**Solutions**:
1. Check resource limits:
   ```bash
   # Docker
   docker stats
   
   # K3s
   kubectl top pods -n edge-terrarium
   ```

2. Adjust resource limits:
   ```bash
   # Edit app-config.yml files
   # Update CPU/memory limits
   ```

3. Scale services:
   ```bash
   # K3s
   kubectl scale deployment -n edge-terrarium <deployment> --replicas=2
   ```

### Slow Startup
**Symptoms**: Services take too long to start

**Solutions**:
1. Check startup dependencies:
   ```bash
   # Verify health checks
   docker-compose ps
   kubectl get pods -n edge-terrarium
   ```

2. Optimize startup order:
   ```bash
   # Review docker-compose.yml dependencies
   # Check K3s init containers
   ```

## Recovery Procedures

### Complete Reset
```bash
# Docker
docker-compose down
docker system prune -f
uv run python terrarium.py deploy docker

# K3s
k3d cluster delete edge-terrarium
uv run python terrarium.py deploy k3s
```

### Partial Reset
```bash
# Restart specific services
docker-compose restart <service>
kubectl rollout restart deployment -n edge-terrarium <deployment>

# Rebuild specific images
docker build -t <image> apps/<service>/
```

### Data Recovery
```bash
# Backup important data
docker cp <container>:/data ./backup/
kubectl cp edge-terrarium/<pod>:/data ./backup/

# Restore from backup
docker cp ./backup/ <container>:/data
kubectl cp ./backup/ edge-terrarium/<pod>:/data
```

## Getting Help

### Log Collection
When reporting issues, collect these logs:
```bash
# System information
docker version
kubectl version
python --version

# Service logs
docker logs <container> > service.log
kubectl logs -n edge-terrarium <pod> > service.log

# Configuration
cat apps/<service>/app-config.yml
cat configs/docker/docker-compose.yml
cat configs/k3s/<resource>.yaml
```

### Common Solutions
1. **Restart services**: Often resolves temporary issues
2. **Check logs**: Look for error messages and stack traces
3. **Verify configuration**: Ensure all config files are valid
4. **Check dependencies**: Ensure all required services are running
5. **Clean and rebuild**: Remove old containers/images and rebuild

### When to Seek Help
- Services consistently fail to start
- Network connectivity issues persist
- Vault secrets are not accessible
- Performance issues that can't be resolved
- Configuration errors that aren't clear

Remember to include relevant logs and configuration details when seeking help.
