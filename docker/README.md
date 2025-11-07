# Datenschleuder Docker Files

This directory contains all files needed to build and deploy Datenschleuder in containerized environments, especially for air-gapped deployments.

## 📁 Directory Contents

### Docker Images
- **`Dockerfile.all-in-one`** - Complete self-contained image for air-gapped environments (Recommended)
- **`Dockerfile.basic`** - Basic Dockerfile for standard deployments

### Build Scripts
- **`prepare-all-in-one.sh`** - Build the all-in-one image with all dependencies (run with internet access)
- **`deploy-all-in-one.sh`** - Deploy the all-in-one image in air-gapped environment
- **`validate-all-in-one.sh`** - Validate deployment and check service health
- **`quick-start.sh`** - Quick start with Docker Compose (includes database)

### Orchestration
- **`docker-compose.yaml`** - Complete stack with PostgreSQL database
- **`.env.example`** - Example environment configuration file
- **`oidc_providers.yaml.example`** - Example OIDC/SSO configuration

### Runtime Configuration
- **`supervisord.conf`** - Supervisor configuration for managing backend and frontend services
- **`start.sh`** - Container startup script
- **`start-docker.sh`** - Helper script for development
- **`test-docker-deployment.sh`** - Testing script

### Documentation
- **`README-ALL-IN-ONE.md`** - Complete guide for air-gap deployment
- **`DOCKER-COMPOSE.md`** - Docker Compose deployment guide
- **`OIDC-CONFIGURATION.md`** - OIDC/SSO configuration guide
- **`AIRGAP-DEPENDENCIES.md`** - External dependencies documentation

## 🚀 Quick Start Options

### Option 1: Docker Compose (Recommended for Development/Testing)

Includes application + PostgreSQL database:

```bash
cd docker
./quick-start.sh
```

Or manually:
```bash
cd docker
cp .env.example .env
# Edit .env with your configuration
docker-compose up -d
```

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

See [DOCKER-COMPOSE.md](./DOCKER-COMPOSE.md) for detailed instructions.

### Option 2: Standalone Air-Gapped Deployment

For production air-gapped environments:

### Step 1: Build (Internet-Connected Machine)
```bash
cd /path/to/datenschleuder
./docker/prepare-all-in-one.sh
```

This creates: `docker/airgap-artifacts/datenschleuder-all-in-one.tar.gz`

### Step 2: Transfer
Transfer the compressed file to your air-gapped environment.

### Step 3: Deploy (Air-Gapped Machine)
```bash
cd /path/to/datenschleuder
./docker/deploy-all-in-one.sh
```

### Step 4: Validate
```bash
./docker/validate-all-in-one.sh
```

## 🌐 Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

## 📦 What's Included

The all-in-one image contains:
- ✅ Vue.js 3 Frontend (pre-built)
- ✅ FastAPI Backend with all Python dependencies
- ✅ Node.js and npm (for serving frontend)
- ✅ Supervisor (process manager)
- ✅ All system dependencies
- ✅ No internet required at runtime

## 🔧 Development

For development builds, see the respective Dockerfile and script comments.

## 📚 Full Documentation

See [README-ALL-IN-ONE.md](./README-ALL-IN-ONE.md) for detailed documentation including:
- Proxy configuration
- Troubleshooting
- Advanced deployment options
- Security considerations

## 🐳 Docker Commands Reference

```bash
# View logs
docker logs datenschleuder

# Follow logs
docker logs -f datenschleuder

# Shell access
docker exec -it datenschleuder /bin/bash

# Restart container
docker restart datenschleuder

# Stop container
docker stop datenschleuder

# Backup data
docker run --rm -v datenschleuder-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/datenschleuder-backup.tar.gz /data
```

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   Datenschleuder Docker Container   │
├─────────────────────────────────────┤
│  Supervisor (Process Manager)       │
│  ├─ Backend (FastAPI) :8000         │
│  └─ Frontend (Vite Preview) :3000   │
├─────────────────────────────────────┤
│  Persistent Data Volume              │
│  /app/data                           │
│  ├─ settings/                        │
│  ├─ git/                             │
│  └─ cache/                           │
└─────────────────────────────────────┘
```

## 📝 Notes

- The `airgap-artifacts/` directory is excluded from git (see `.gitignore`)
- All scripts are executable (`chmod +x *.sh`)
- Proxy settings are automatically detected during build
- Images are compressed for efficient transfer
