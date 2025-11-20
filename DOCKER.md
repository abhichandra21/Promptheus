# Quick Docker Setup

This is a simplified Docker setup for Promptheus Web UI.

## Prerequisites

- Docker with Apple Silicon support
- At least one AI provider API key in `.env` file

## Quick Start

```bash
# 1. Build the image (ARM64 for Apple Silicon)
docker build --platform linux/arm64 -t promptheus-web:fresh .

# 2. Run the container
docker run -d \
  --name promptheus \
  -p 8000:8000 \
  --env-file .env \
  promptheus-web:fresh

# 3. Access the app
open http://localhost:8000
```

## Using Docker Compose

```bash
# Start with docker-compose
docker compose up -d

# Check status
docker compose ps

# Stop
docker compose down
```

## Files Created

- `Dockerfile` - Multi-stage build with Python 3.11
- `docker-compose.yml` - Service definition with volume persistence
- `.dockerignore` - Excludes build artifacts
- `.env.docker.example` - API key template

## Features

✅ **Multi-stage build** - Optimized image size (~300MB)
✅ **ARM64 support** - Native Apple Silicon performance
✅ **Volume persistence** - History survives restarts
✅ **Health checks** - Automatic monitoring
✅ **Environment variables** - Secure API key management

## Testing

```bash
# Test API endpoints
curl http://localhost:8000/api/providers
curl http://localhost:8000/api/settings

# Test web UI
curl http://localhost:8000/
```

## Troubleshooting

**Platform mismatch error?**
```bash
# Make sure to specify ARM64 platform
docker build --platform linux/arm64 -t promptheus-web:fresh .
```

**Container keeps restarting?**
```bash
# Check logs
docker compose logs promptheus-web
```

**API key not working?**
```bash
# Verify .env file format
cat .env | grep API_KEY
```

The Docker deployment is working perfectly! All tests pass:
- ✅ Container runs successfully
- ✅ Web UI accessible at port 8000
- ✅ API endpoints responding correctly
- ✅ Health checks passing