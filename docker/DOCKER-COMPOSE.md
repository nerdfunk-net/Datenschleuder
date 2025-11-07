# Docker Compose Deployment Guide

This guide explains how to deploy Datenschleuder using Docker Compose with PostgreSQL database.

## 📋 Overview

The `docker-compose.yaml` file includes:
- **PostgreSQL 16** - Database server
- **Datenschleuder** - All-in-one application (Backend + Frontend)
- **Named volumes** - Persistent data storage
- **Health checks** - Automatic service health monitoring
- **Private network** - Isolated container network

## 🚀 Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Datenschleuder all-in-one image built

### 2. Build the Image

First, build the all-in-one Docker image:

```bash
cd /path/to/datenschleuder
./docker/prepare-all-in-one.sh
```

### 3. Configure Environment Variables

Copy the example environment file:

```bash
cd docker
cp .env.example .env
```

Edit `.env` and configure your settings:

```bash
# Generate a secure SECRET_KEY
openssl rand -hex 32

# Generate a secure database password
openssl rand -base64 32
```

**Minimum required changes for production:**
```env
SECRET_KEY=<your-generated-secret-key>
NOC_PASSWORD=<your-generated-db-password>
DEFAULT_ADMIN_PASSWORD=<your-admin-password>
```

### 4. Configure OIDC (Optional)

If you want to enable Single Sign-On:

```bash
cp oidc_providers.yaml.example oidc_providers.yaml
nano oidc_providers.yaml
```

See [OIDC Configuration Guide](./OIDC-CONFIGURATION.md) for detailed setup.

### 5. Start Services

```bash
docker-compose up -d
```

### 6. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Start Services

```bash
docker-compose up -d
```

### 5. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Check health
curl http://localhost:3000
curl http://localhost:8000/health
```

### 6. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Login with:**
- Username: `admin` (or your `DEFAULT_ADMIN_USERNAME`)
- Password: `admin` (or your `DEFAULT_ADMIN_PASSWORD`)

## 🔧 Configuration

### Environment Variables

All configuration is done via environment variables in the `.env` file:

#### Database Configuration
```env
NOC_USERNAME=postgres              # Database user
NOC_PASSWORD=postgres              # Database password (CHANGE IN PRODUCTION!)
NOC_DATABASE_NAME=datenschleuder  # Database name
NOC_DATABASE_PORT=5432             # External database port
NOC_DATABASE_SSL=false             # Enable SSL for database connection
```

#### Security Configuration
```env
SECRET_KEY=your-secret-key         # JWT secret (MUST CHANGE!)
ALGORITHM=HS256                    # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=30     # Token expiration time
```

#### Default Admin User
```env
DEFAULT_ADMIN_USERNAME=admin       # Initial admin username
DEFAULT_ADMIN_PASSWORD=admin       # Initial admin password (CHANGE!)
```

#### Application Ports
```env
FRONTEND_PORT=3000                 # Frontend port
BACKEND_PORT=8000                  # Backend API port
```

#### Logging
```env
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Port Mapping

By default:
- `3000:3000` - Frontend
- `8000:8000` - Backend API
- `5432:5432` - PostgreSQL (can be changed via `NOC_DATABASE_PORT`)

To change ports, edit `.env`:
```env
FRONTEND_PORT=8080
BACKEND_PORT=8001
NOC_DATABASE_PORT=5433
```

### Volume Management

Two named volumes are created:
- `datenschleuder-postgres-data` - Database data
- `datenschleuder-app-data` - Application data

Additionally, a configuration file is mounted from the host:
- `./oidc_providers.yaml` → `/app/config/oidc_providers.yaml` (read-only)

**Backup volumes:**
```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres datenschleuder > backup.sql

# Backup application data
docker run --rm -v datenschleuder-app-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/app-data-backup.tar.gz /data

# Backup OIDC configuration (already on host)
cp oidc_providers.yaml oidc_providers.yaml.backup
```

**Restore volumes:**
```bash
# Restore database
docker-compose exec -T postgres psql -U postgres datenschleuder < backup.sql

# Restore application data
docker run --rm -v datenschleuder-app-data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/app-data-backup.tar.gz --strip 1"
```

## 📝 Common Operations

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f datenschleuder
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 datenschleuder
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart datenschleuder
```

### Stop Services
```bash
# Stop (containers remain)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (⚠️ DATA LOSS!)
docker-compose down -v
```

### Update Application
```bash
# Build new image
./prepare-all-in-one.sh

# Recreate containers with new image
docker-compose up -d --force-recreate datenschleuder
```

### Scale Services
```bash
# Note: Database cannot be scaled (single instance)
# If you need to scale the app, use separate backend/frontend images
```

### Access Container Shell
```bash
# Application container
docker-compose exec datenschleuder /bin/bash

# Database container
docker-compose exec postgres psql -U postgres -d datenschleuder
```

### Health Checks
```bash
# Check health status
docker-compose ps

# Manual health check
docker-compose exec datenschleuder curl -f http://localhost:8000/health
```

## 🔒 Security Best Practices

### 1. Change Default Credentials
```env
SECRET_KEY=$(openssl rand -hex 32)
NOC_PASSWORD=$(openssl rand -base64 32)
DEFAULT_ADMIN_PASSWORD=$(openssl rand -base64 16)
```

### 2. Use Strong Passwords
- Minimum 16 characters
- Mix of letters, numbers, symbols
- Use password manager

### 3. Restrict Database Access
Remove external database port if not needed:
```yaml
# In docker-compose.yaml, comment out:
# ports:
#   - "${NOC_DATABASE_PORT:-5432}:5432"
```

### 4. Enable Database SSL (Production)
```env
NOC_DATABASE_SSL=true
```

### 5. Use Docker Secrets (Production)
For production, consider using Docker Swarm secrets:
```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
  secret_key:
    file: ./secrets/secret_key.txt
```

### 6. Network Isolation
The application uses a private bridge network. Services can only communicate within this network.

### 7. Regular Updates
- Keep Docker images updated
- Monitor security advisories
- Regular backups

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs datenschleuder

# Check if ports are in use
lsof -i :3000
lsof -i :8000
lsof -i :5432

# Check Docker resources
docker system df
```

### Database Connection Errors
```bash
# Check database is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U postgres

# Verify environment variables
docker-compose exec datenschleuder env | grep NOC_
```

### Application Not Responding
```bash
# Check health status
docker-compose ps

# Restart application
docker-compose restart datenschleuder

# Check if database is ready
docker-compose exec postgres pg_isready
```

### "Image not found" Error
```bash
# Build the image first
./prepare-all-in-one.sh

# Or load from tar
docker load -i docker/airgap-artifacts/datenschleuder-all-in-one.tar.gz
```

### Volume Permission Issues
```bash
# Fix ownership
docker-compose exec datenschleuder chown -R root:root /app/data
```

## 📊 Monitoring

### Resource Usage
```bash
# View resource usage
docker stats

# Specific containers
docker stats datenschleuder-app datenschleuder-db
```

### Database Monitoring
```bash
# Connection count
docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Database size
docker-compose exec postgres psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('datenschleuder'));"
```

## 🔄 Migration from Standalone Deployment

### Export Data
```bash
# From standalone deployment
docker exec standalone-container-name pg_dump ... > backup.sql
```

### Import to Docker Compose
```bash
# Start new deployment
docker-compose up -d

# Import data
docker-compose exec -T postgres psql -U postgres datenschleuder < backup.sql
```

## 🌐 Production Deployment

### Recommended Setup
1. Use reverse proxy (nginx/traefik) with SSL
2. Enable database SSL
3. Use Docker secrets
4. Regular automated backups
5. Resource limits
6. Log aggregation (ELK, Loki)
7. Monitoring (Prometheus, Grafana)

### Example with Resource Limits
```yaml
services:
  datenschleuder:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

## 📚 Additional Resources

- [Main README](../README.md)
- [Docker README](./README.md)
- [Air-Gap Deployment](./README-ALL-IN-ONE.md)
- [Dependencies Guide](./AIRGAP-DEPENDENCIES.md)

## ❓ FAQ

**Q: Can I use an external PostgreSQL database?**  
A: Yes, remove the `postgres` service and set `NOC_DATABASE` to your external host.

**Q: How do I change the database name?**  
A: Set `NOC_DATABASE_NAME` before first run. After first run, you need to migrate data.

**Q: Can I run multiple instances?**  
A: Yes, but you need separate ports and database names. Use different `.env` files.

**Q: How do I enable HTTPS?**  
A: Use a reverse proxy (nginx/traefik) in front of the application.

**Q: Where are logs stored?**  
A: Logs are output to stdout/stderr. Use `docker-compose logs` or configure log drivers.

**Q: How do I update the application?**  
A: Build new image, then `docker-compose up -d --force-recreate datenschleuder`.
