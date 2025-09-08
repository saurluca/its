# Deployment Health Check Scripts

This directory contains scripts for testing deployed application health in the CI/CD pipeline.

## Scripts

### `health-check.sh`

A comprehensive health check script that verifies both backend and frontend services are running correctly.

**Features:**

- Tests backend health endpoints (`/health` and `/`)
- Verifies frontend accessibility
- Configurable retry logic with delays
- Colored output for better visibility
- Returns proper exit codes for CI/CD integration

**Usage:**

```bash
# Basic usage
./scripts/health-check.sh

# With custom URLs
BACKEND_URL=http://localhost:8000 FRONTEND_URL=http://localhost:3000 ./scripts/health-check.sh

# With custom retry settings
MAX_RETRIES=5 RETRY_DELAY=3 ./scripts/health-check.sh
```

**Environment Variables:**

- `BACKEND_URL`: Backend service URL (default: http://localhost:8000)
- `FRONTEND_URL`: Frontend service URL (default: http://localhost:3000)
- `MAX_RETRIES`: Number of retry attempts (default: 10)
- `RETRY_DELAY`: Delay between retries in seconds (default: 5)

### `docker-health-check.sh`

A Docker-specific health check script that uses containerized curl to test services.

**Features:**

- Uses Docker containers for isolated testing
- Network host mode for container-to-container communication
- Lightweight and minimal dependencies

**Usage:**

```bash
./scripts/docker-health-check.sh
```

## GitHub Actions Integration

These scripts are integrated into the GitHub Actions workflow (`docker-deploy.yml`) as a deployment testing step that:

1. Starts test containers (database, backend, frontend)
2. Runs health checks to verify services are responding
3. Cleans up test containers
4. Only runs on `main` and `live` branches after successful image builds

The deployment test job ensures that built Docker images are functional before they would be deployed to production environments.

## Exit Codes

- `0`: All health checks passed
- `1`: One or more health checks failed

These exit codes are used by the CI/CD pipeline to determine deployment success or failure.
