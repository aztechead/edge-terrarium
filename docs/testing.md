# Testing Guide

This guide explains how to test the Edge-Terrarium platform in both Docker and K3s environments.

## Test Command

The main test command is:
```bash
uv run python terrarium.py test
```

### Test Options

```bash
# Test with fail-fast (stops on first error)
uv run python terrarium.py test --fail-fast

# Test with verbose output
uv run python terrarium.py test --verbose

# Test specific environment
uv run python terrarium.py test --environment docker
uv run python terrarium.py test --environment k3s
```

## Test Coverage

The test suite covers:

### Application Endpoints
- **Custom Client**: `/api/fake-provider/*`, `/api/example-provider/*`
- **Service Sink**: `/api/` (default route)
- **File Storage**: `/api/storage/*`
- **Logthon**: `/api/logs/*`
- **Vault**: `/api/vault/*`

### HTTP Methods
- **GET**: Basic endpoint testing
- **POST**: JSON data submission
- **PUT**: File creation and updates

### Service Integration
- **Vault Secrets**: Verifies secrets are accessible
- **Request Logging**: Confirms logs are being captured
- **File Operations**: Tests file creation and storage
- **Health Checks**: Validates service health endpoints

## Test Environment Detection

The test command automatically detects the current deployment environment:

### Docker Environment
- Checks for running Docker Compose services
- Uses `localhost:8443` for testing
- Tests direct service access on specific ports

### K3s Environment
- Checks for running Kubernetes pods
- Uses port forwarding to access services
- Automatically sets up port forwarding if needed
- Uses proper Host headers for ingress routing

## Test Results

### Success Indicators
- **Green checkmarks**: Successful test cases
- **Status codes**: 200, 201, 202 are considered successful
- **Service responses**: Valid JSON or expected content

### Failure Indicators
- **Red X marks**: Failed test cases
- **Error status codes**: 404, 500, etc.
- **Connection errors**: Network or service unavailable
- **Timeout errors**: Service not responding

## Troubleshooting Tests

### Common Issues

#### 404 Errors
- **Cause**: Service not running or routing misconfigured
- **Solution**: Check service status and ingress configuration

#### Connection Refused
- **Cause**: Service not listening on expected port
- **Solution**: Verify service configuration and port mappings

#### Timeout Errors
- **Cause**: Service taking too long to respond
- **Solution**: Check service health and resource usage

### Debug Commands

```bash
# Check service status
docker ps  # For Docker
kubectl get pods -n edge-terrarium  # For K3s

# View service logs
docker logs <container-name>  # For Docker
kubectl logs -n edge-terrarium <pod-name>  # For K3s

# Test specific endpoints
curl -k https://localhost:8443/api/health
```

## Test Data

### Request Logging
Tests verify that:
- Request files are created in `/tmp/requests/`
- Logs are sent to the logthon service
- File operations are logged properly

### Vault Secrets
Tests verify that:
- All expected secrets are present
- Secrets are accessible via API
- Applications can retrieve secrets successfully

### File Operations
Tests verify that:
- Files can be created via API
- Files are stored correctly
- File metadata is accessible

## Continuous Integration

The test suite is designed to be run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Test Docker deployment
  run: |
    uv run python terrarium.py deploy docker
    uv run python terrarium.py test --environment docker

- name: Test K3s deployment
  run: |
    uv run python terrarium.py deploy k3s
    uv run python terrarium.py test --environment k3s
```

## Performance Testing

While not included in the basic test suite, you can perform performance testing:

```bash
# Load testing with curl
for i in {1..100}; do
  curl -k https://localhost:8443/api/health &
done
wait

# Monitor resource usage
docker stats  # For Docker
kubectl top pods -n edge-terrarium  # For K3s
```

## Test Maintenance

### Adding New Tests
1. Identify the service or endpoint to test
2. Add test case to the appropriate test method
3. Ensure test follows the existing pattern
4. Test both Docker and K3s environments

### Updating Tests
1. Modify test expectations when services change
2. Update test data when APIs change
3. Verify tests still pass after changes
4. Update documentation if test behavior changes

## Best Practices

### Test Reliability
- Use retry logic for flaky tests
- Implement proper error handling
- Clean up test data after tests
- Use meaningful test descriptions

### Test Performance
- Run tests in parallel when possible
- Use appropriate timeouts
- Minimize test data size
- Cache test results when appropriate

### Test Maintenance
- Keep tests simple and focused
- Use descriptive test names
- Document test assumptions
- Regular test review and cleanup
