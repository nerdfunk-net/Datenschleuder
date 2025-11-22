#!/bin/bash
# OIDC Configuration Checker
# This script helps diagnose OIDC configuration issues between your app and NiFi

set -e

echo "======================================================================="
echo "OIDC Configuration Checker"
echo "======================================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: OIDC Provider Configuration
echo "1. Checking OIDC Provider Configuration..."
if [ -f "config/oidc_providers.yaml" ]; then
    echo -e "${GREEN}✓${NC} Found config/oidc_providers.yaml"

    # Extract nifi_backend provider settings
    BACKEND_DISCOVERY=$(grep -A 20 "nifi_backend:" config/oidc_providers.yaml | grep "discovery_url:" | head -1 | awk -F'"' '{print $2}')
    BACKEND_CLIENT_ID=$(grep -A 20 "nifi_backend:" config/oidc_providers.yaml | grep "client_id:" | head -1 | awk '{print $2}' | tr -d '"')

    echo "  Backend Provider Discovery URL: $BACKEND_DISCOVERY"
    echo "  Backend Provider Client ID: $BACKEND_CLIENT_ID"

    # Extract hostname from discovery URL
    if [[ $BACKEND_DISCOVERY =~ https://([^/:]+) ]]; then
        KEYCLOAK_HOST="${BASH_REMATCH[1]}"
        echo "  Keycloak Hostname: $KEYCLOAK_HOST"
    fi
else
    echo -e "${RED}✗${NC} config/oidc_providers.yaml not found"
    exit 1
fi

echo ""

# Check 2: Test Keycloak Connectivity
echo "2. Testing Keycloak Connectivity..."
if [ ! -z "$BACKEND_DISCOVERY" ]; then
    if curl -k -s --connect-timeout 5 "$BACKEND_DISCOVERY" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Can reach Keycloak at $BACKEND_DISCOVERY"

        # Get issuer from discovery endpoint
        ISSUER=$(curl -k -s "$BACKEND_DISCOVERY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('issuer', 'N/A'))" 2>/dev/null || echo "N/A")
        echo "  Token Issuer will be: $ISSUER"
    else
        echo -e "${RED}✗${NC} Cannot reach Keycloak at $BACKEND_DISCOVERY"
        echo "  This may be normal if Keycloak is in a different network"
    fi
else
    echo -e "${YELLOW}⚠${NC} No discovery URL configured"
fi

echo ""

# Check 3: What the token will contain
echo "3. Token Claims (what NiFi will see)..."
echo "  Based on Client Credentials flow with Keycloak:"
echo "    - Issuer (iss): $ISSUER"
echo "    - Subject (sub): <UUID of service account>"
echo "    - Client ID (azp/client_id): $BACKEND_CLIENT_ID"
echo "    - Preferred Username: service-account-$BACKEND_CLIENT_ID"
echo "    - Audience (aud): account"
echo ""
echo -e "  ${GREEN}→ NiFi Username will be: service-account-$BACKEND_CLIENT_ID${NC}"

echo ""

# Check 4: NiFi Configuration Recommendations
echo "4. Required NiFi Configuration (nifi.properties)..."
echo "======================================================================="
cat <<EOF
# Copy these settings to your nifi.properties file:

# OIDC Configuration - Discovery URL (MUST match token issuer!)
nifi.security.user.oidc.discovery.url=$BACKEND_DISCOVERY

# Client Credentials
nifi.security.user.oidc.client.id=$BACKEND_CLIENT_ID
nifi.security.user.oidc.client.secret=<copy from oidc_providers.yaml>

# Timeouts
nifi.security.user.oidc.connect.timeout=5 secs
nifi.security.user.oidc.read.timeout=5 secs

# Which claim to use as username
nifi.security.user.oidc.claim.identifying.user=preferred_username

# Grant initial admin access to the service account
nifi.initial.admin.identity=service-account-$BACKEND_CLIENT_ID

# Optional: Additional scopes
nifi.security.user.oidc.additional.scopes=email,profile
EOF
echo "======================================================================="

echo ""

# Check 5: Hostname Consistency Warning
echo "5. Hostname Consistency Check..."
if [[ $ISSUER == *"$KEYCLOAK_HOST"* ]]; then
    echo -e "${GREEN}✓${NC} Issuer and Discovery URL use same hostname ($KEYCLOAK_HOST)"
else
    echo -e "${RED}✗${NC} Issuer and Discovery URL may use different hostnames"
    echo "  Issuer: $ISSUER"
    echo "  Discovery: $BACKEND_DISCOVERY"
    echo ""
    echo -e "${YELLOW}  WARNING: This is the #1 cause of OIDC failures!${NC}"
    echo "  The hostname in the token issuer MUST exactly match"
    echo "  the hostname in NiFi's discovery URL."
fi

echo ""

# Check 6: Testing Instructions
echo "6. Testing Instructions..."
echo "  a) Navigate to: http://localhost:3000/oidc-test"
echo "  b) Select: 'Backend NiFi OIDC Authentication'"
echo "  c) Select Provider: 'NiPyAPI [Backend]'"
echo "  d) Enter NiFi URL: https://localhost:8443/nifi-api"
echo "  e) Click 'Test Backend Auth'"
echo ""
echo "  The test will show you the exact username to use in NiFi."

echo ""

# Check 7: NiFi Verification Commands
echo "7. NiFi Verification Commands..."
echo "  After configuring NiFi, verify with these commands:"
echo ""
echo "  # Check NiFi can reach Keycloak"
echo "  docker exec -it <nifi-container> curl -k $BACKEND_DISCOVERY"
echo ""
echo "  # Check NiFi logs for OIDC activity"
echo "  docker exec -it <nifi-container> grep -i oidc logs/nifi-app.log | tail -20"
echo ""
echo "  # Check user authentication logs"
echo "  docker exec -it <nifi-container> tail -20 logs/nifi-user.log"

echo ""
echo "======================================================================="
echo "Summary"
echo "======================================================================="
echo ""
echo -e "${GREEN}NiFi Username to authorize: service-account-$BACKEND_CLIENT_ID${NC}"
echo ""
echo "Steps to fix OIDC authentication:"
echo "1. Update nifi.properties with the configuration above"
echo "2. Ensure hostname in discovery URL matches token issuer"
echo "3. Restart NiFi"
echo "4. Run OIDC test from http://localhost:3000/oidc-test"
echo "5. Check nifi-user.log for authentication entries"
echo ""
echo "For detailed debugging: See OIDC_NIFI_DEBUGGING_GUIDE.md"
echo "For quick fixes: See OIDC_QUICK_FIX.md"
echo "======================================================================="
