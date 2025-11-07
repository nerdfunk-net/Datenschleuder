#!/bin/bash
# quick-start.sh - Quick start script for Datenschleuder with Docker Compose

set -e

echo "🚀 Datenschleuder Docker Compose Quick Start"
echo "==========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "❌ Error: docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Use 'docker compose' if available, otherwise 'docker-compose'
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Setting up environment configuration..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo ""
        echo "⚠️  IMPORTANT: Please edit .env file and update the following:"
        echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
        echo "   - NOC_PASSWORD (generate with: openssl rand -base64 32)"
        echo "   - DEFAULT_ADMIN_PASSWORD (set a strong password)"
        echo ""
        read -p "Press Enter to continue after updating .env file, or Ctrl+C to exit..."
    else
        echo "❌ Error: .env.example file not found!"
        exit 1
    fi
else
    echo "✅ Found existing .env file"
fi

# Check if oidc_providers.yaml exists
echo ""
if [ ! -f "oidc_providers.yaml" ]; then
    echo "⚙️  Setting up OIDC configuration..."
    if [ -f "oidc_providers.yaml.example" ]; then
        cp oidc_providers.yaml.example oidc_providers.yaml
        echo "✅ Created oidc_providers.yaml from example"
        echo ""
        echo "ℹ️  OIDC Configuration:"
        echo "   - File: oidc_providers.yaml"
        echo "   - Edit this file to configure Single Sign-On providers"
        echo "   - Traditional login is enabled by default"
        echo "   - See DOCKER-COMPOSE.md for OIDC setup guide"
        echo ""
    else
        echo "❌ Error: oidc_providers.yaml.example file not found!"
        exit 1
    fi
else
    echo "✅ Found existing oidc_providers.yaml"
fi

# Check if image exists
echo ""
echo "🔍 Checking for Datenschleuder image..."
if ! docker images | grep -q "datenschleuder.*all-in-one"; then
    echo "⚠️  Datenschleuder image not found!"
    echo ""
    echo "   Please build the image first:"
    echo "   ./prepare-all-in-one.sh"
    echo ""
    read -p "Do you want to build the image now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "./prepare-all-in-one.sh" ]; then
            ./prepare-all-in-one.sh
        else
            echo "❌ Error: prepare-all-in-one.sh not found!"
            exit 1
        fi
    else
        echo "❌ Cannot continue without the image. Exiting."
        exit 1
    fi
else
    echo "✅ Datenschleuder image found"
fi

# Start services
echo ""
echo "🚀 Starting services with Docker Compose..."
$COMPOSE_CMD up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check status
echo ""
echo "📊 Service Status:"
$COMPOSE_CMD ps

# Check health
echo ""
echo "🏥 Health Check:"
echo -n "   Backend: "
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "⚠️  Not responding yet (may take a minute to start)"
fi

echo -n "   Frontend: "
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "⚠️  Not responding yet (may take a minute to start)"
fi

# Show access information
echo ""
echo "✅ Datenschleuder is starting!"
echo "=============================="
echo ""
echo "🌐 Access URLs:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "🔐 Default Credentials:"
echo "   Username:  admin (or check DEFAULT_ADMIN_USERNAME in .env)"
echo "   Password:  admin (or check DEFAULT_ADMIN_PASSWORD in .env)"
echo ""
echo "⚠️  IMPORTANT: Change default credentials after first login!"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:     $COMPOSE_CMD logs -f"
echo "   Stop:          $COMPOSE_CMD stop"
echo "   Restart:       $COMPOSE_CMD restart"
echo "   Full shutdown: $COMPOSE_CMD down"
echo ""
echo "📚 Documentation: See DOCKER-COMPOSE.md for detailed usage"
echo ""
