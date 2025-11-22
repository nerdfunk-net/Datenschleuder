# OIDC Backend Authentication Guide

## Overview

This application now supports **OIDC authentication for backend-to-NiFi connections** using the `nipyapi` library. This allows you to authenticate the backend service with NiFi instances using OAuth2/OIDC tokens instead of client certificates or username/password authentication.

## Why Use OIDC for Backend Authentication?

**Benefits:**
- ✅ Centralized credential management through your identity provider
- ✅ Automatic token expiration and refresh
- ✅ No certificate file management (no expiration, rotation, or renewal concerns)
- ✅ Better audit logging through your OIDC provider
- ✅ Easier credential rotation (update in OIDC provider only)
- ✅ Integration with corporate identity systems (Keycloak, Azure AD, Okta, etc.)

**Use Cases:**
- Corporate environments with centralized identity management
- Multi-instance NiFi deployments requiring consistent authentication
- Air-gapped environments with internal OIDC providers
- Scenarios where certificate management is complex or problematic

## Architecture

### Authentication Methods Priority

The backend supports three authentication methods with the following priority:

1. **Instance-specific OIDC** - If `use_oidc=True` on NiFi instance
2. **Global OIDC provider** - If `OIDC_BACKEND_PROVIDER` environment variable is set
3. **Client certificates** - If `certificate_name` is specified
4. **Username/password** - If `username` and `password` are provided

### OIDC Flow Types

**Client Credentials Flow** (Recommended for backend):
- Machine-to-machine authentication
- No user credentials required
- Simpler and more secure
- Backend service authenticates using client ID and secret

**Resource Owner Password Flow** (Optional):
- Authenticates as a specific user
- Requires username and password
- Use only if you need user impersonation

## Configuration

### Step 1: Configure OIDC Provider

Edit `config/oidc_providers.yaml` and add a backend-only provider:

```yaml
providers:
  # Backend-only OIDC provider for NiFi authentication
  nifi_backend:
    enabled: true
    backend: true  # This provider won't be shown on user login page
    
    # Discovery URL for your OIDC provider
    discovery_url: "https://keycloak:7443/realms/nifi/.well-known/openid-configuration"
    
    # Client credentials (from OIDC provider)
    client_id: "nifi-backend-service"
    client_secret: "your-client-secret-here"
    
    # Not needed for backend (Client Credentials flow)
    redirect_uri: ""
    
    # Optional: Custom CA certificate for self-signed certificates
    ca_cert_path: "config/certs/nifi-ca.cert.pem"
    
    # Scopes for backend authentication
    scopes:
      - openid
    
    # Display info (for documentation only, not shown to users)
    name: "NiFi Backend Service"
    description: "Backend authentication for NiFi instances"
```

**Important:** Set `backend: true` to prevent this provider from appearing on the user login page.

### Step 2: Set Environment Variable

Add to your `.env` file:

```bash
# OIDC Backend Provider
# If set, use this OIDC provider from oidc_providers.yaml for backend-to-NiFi authentication
# Leave empty to use certificate-based authentication
OIDC_BACKEND_PROVIDER=nifi_backend
```

### Step 3: Configure OIDC Provider (Keycloak Example)

#### Create Client in Keycloak

1. Go to **Clients** → **Create Client**
2. Set **Client ID**: `nifi-backend-service`
3. Set **Client Protocol**: `openid-connect`
4. Click **Next**

#### Configure Client Settings

1. **Access Type**: `confidential`
2. **Service Accounts Enabled**: `ON`
3. **Standard Flow Enabled**: `OFF` (not needed for backend)
4. **Direct Access Grants Enabled**: `OFF` (not needed for backend)
5. Click **Save**

#### Get Client Secret

1. Go to **Credentials** tab
2. Copy the **Client Secret**
3. Add it to `oidc_providers.yaml`

#### Configure Service Account Roles

1. Go to **Service Account Roles** tab
2. Assign appropriate roles/permissions for NiFi access

#### Token Endpoint URL

The token endpoint is automatically derived from the discovery URL:
- Discovery: `https://keycloak:7443/realms/nifi/.well-known/openid-configuration`
- Token endpoint: `https://keycloak:7443/realms/nifi/protocol/openid-connect/token`

### Step 4: Configure NiFi for OIDC

NiFi must be configured to accept OIDC tokens. See NiFi documentation for:
- Configuring OIDC authentication in `nifi.properties`
- Setting up OIDC providers in NiFi
- Configuring NiFi to use the same OIDC provider as the backend

## Usage

### Option 1: Global OIDC Provider (Recommended)

When `OIDC_BACKEND_PROVIDER` is set, **all NiFi instances** will use OIDC authentication automatically:

```python
from app.models.nifi_instance import NiFiInstance
from app.services.nifi_auth import configure_nifi_connection

# Create NiFi instance (no OIDC fields needed)
instance = NiFiInstance(
    hierarchy_attribute="DC",
    hierarchy_value="DC1",
    nifi_url="https://nifi-dc1.example.com:8443/nifi-api",
    verify_ssl=True
)

# Configure connection (automatically uses global OIDC provider)
configure_nifi_connection(instance)
```

The backend will:
1. Check `OIDC_BACKEND_PROVIDER` environment variable
2. Load provider configuration from `oidc_providers.yaml`
3. Authenticate using OIDC Client Credentials flow
4. Set bearer token for all NiFi API calls

### Option 2: Instance-Specific OIDC

For per-instance OIDC configuration:

```python
instance = NiFiInstance(
    hierarchy_attribute="DC",
    hierarchy_value="DC1",
    nifi_url="https://nifi-dc1.example.com:8443/nifi-api",
    verify_ssl=True,
    
    # Enable OIDC for this instance
    use_oidc=True,
    oidc_token_endpoint="https://keycloak:7443/realms/nifi/protocol/openid-connect/token",
    oidc_client_id="nifi-dc1-service",
    oidc_client_secret="encrypted-secret",  # Will be encrypted
    
    # Optional: Resource Owner Password flow
    oidc_username="service-account",  # Optional
    oidc_password="encrypted-password"  # Optional, will be encrypted
)

configure_nifi_connection(instance)
```

### Option 3: Certificate-Based (Fallback)

If no OIDC is configured, the system falls back to certificates:

```python
instance = NiFiInstance(
    hierarchy_attribute="DC",
    hierarchy_value="DC1",
    nifi_url="https://nifi-dc1.example.com:8443/nifi-api",
    verify_ssl=True,
    certificate_name="nifi_client_cert"  # From certificates.yaml
)

configure_nifi_connection(instance)
```

## Testing

### Test OIDC Configuration

Run the test script to verify OIDC configuration:

```bash
cd backend
python test_oidc_backend.py
```

Expected output:
```
======================================================================
OIDC Backend Configuration Test
======================================================================

1. Environment Configuration:
   OIDC_BACKEND_PROVIDER: 'nifi_backend'

2. All OIDC Providers:
   - nifi_backend:
     Name: NiFi Backend Service
     Enabled: True
     Backend-only: True
   - corporate:
     Name: Corporate SSO
     Enabled: True
     Backend-only: False

3. User-Facing Providers (shown on login page):
   - corporate: Corporate SSO

4. Backend Provider Configuration:
   ✅ Found backend provider: nifi_backend
   Provider name: NiFi Backend Service
   Discovery URL: https://keycloak:7443/realms/nifi/.well-known/openid-configuration
   Client ID: nifi-backend-service
   Client Secret: ***

5. Configuration Validation:
   ✅ Configuration is valid

======================================================================
```

### Test NiFi Connection

Use the existing NiFi connection test endpoint:

```bash
curl -X POST http://localhost:8000/api/nifi/check-connection \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Verify OIDC Authentication

Check backend logs for OIDC authentication:

```
INFO:app.services.nifi_auth:Using global OIDC backend provider: nifi_backend
INFO:app.services.nifi_auth:Authenticating to NiFi using global OIDC provider: nifi_backend
INFO:app.services.nifi_auth:Successfully authenticated to NiFi using OIDC
```

## Troubleshooting

### Error: "OIDC backend provider not found"

**Problem:** `OIDC_BACKEND_PROVIDER` is set but provider doesn't exist in `oidc_providers.yaml`

**Solution:**
1. Check provider ID matches exactly (case-sensitive)
2. Verify `enabled: true` is set
3. Run `python test_oidc_backend.py` to diagnose

### Error: "Failed to authenticate with NiFi using OIDC"

**Possible causes:**
1. **Invalid credentials** - Check client ID and secret
2. **Wrong token endpoint** - Verify discovery URL is correct
3. **NiFi not configured for OIDC** - Ensure NiFi accepts OIDC tokens
4. **Network issues** - Check connectivity to OIDC provider
5. **SSL certificate issues** - Set `ca_cert_path` for self-signed certs

**Debug steps:**
```bash
# Test OIDC provider connectivity
curl -k https://keycloak:7443/realms/nifi/.well-known/openid-configuration

# Test token endpoint directly
curl -X POST https://keycloak:7443/realms/nifi/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=nifi-backend-service" \
  -d "client_secret=your-secret"
```

### Error: "SSL: CERTIFICATE_VERIFY_FAILED"

**Problem:** Self-signed certificates not trusted

**Solution:** Add CA certificate to `oidc_providers.yaml`:

```yaml
providers:
  nifi_backend:
    ca_cert_path: "config/certs/nifi-ca.cert.pem"
```

Or disable SSL verification (NOT recommended for production):

```python
instance.verify_ssl = False
```

### Backend Provider Shows on Login Page

**Problem:** Backend provider appears in user login options

**Solution:** Set `backend: true` in provider configuration:

```yaml
providers:
  nifi_backend:
    enabled: true
    backend: true  # Add this line
```

## Security Considerations

### Best Practices

1. **Use Client Credentials Flow** - Simpler and more secure than Resource Owner Password
2. **Encrypt secrets** - Client secrets are automatically encrypted in database
3. **Minimal permissions** - Configure OIDC clients with minimal required permissions
4. **Enable SSL verification** - Always use `verify_ssl=True` in production
5. **Rotate credentials** - Regularly rotate client secrets in OIDC provider
6. **Monitor authentication** - Check logs for failed authentication attempts
7. **Separate providers** - Use different OIDC clients for user login vs. backend

### Token Management

- OIDC tokens have automatic expiration
- `nipyapi` handles token refresh automatically
- No manual token management required

### Secret Storage

- Client secrets are encrypted using Fernet encryption
- Encryption key stored in `.env` (`SECRET_KEY`)
- Database stores encrypted values only

## Migration from Certificates to OIDC

### Phase 1: Set Up OIDC Alongside Certificates

1. Configure OIDC provider in `oidc_providers.yaml`
2. **Don't set** `OIDC_BACKEND_PROVIDER` yet
3. Test with instance-specific OIDC (`use_oidc=True`)
4. Verify authentication works

### Phase 2: Enable Global OIDC

1. Set `OIDC_BACKEND_PROVIDER` in `.env`
2. Restart backend service
3. Test NiFi connections
4. Monitor logs for issues

### Phase 3: Deprecate Certificates (Optional)

1. Remove certificate configurations from instances
2. Keep certificate fallback for emergency access
3. Update documentation

## Advanced Configuration

### Multiple OIDC Providers

You can configure multiple backend providers for different NiFi instances:

```yaml
providers:
  nifi_prod:
    backend: true
    enabled: true
    discovery_url: "https://keycloak-prod:7443/realms/nifi/.well-known/openid-configuration"
    client_id: "nifi-prod-backend"
    client_secret: "prod-secret"
    
  nifi_dev:
    backend: true
    enabled: true
    discovery_url: "https://keycloak-dev:7443/realms/nifi/.well-known/openid-configuration"
    client_id: "nifi-dev-backend"
    client_secret: "dev-secret"
```

Use instance-specific OIDC to choose provider per instance.

### Resource Owner Password Flow

For user impersonation (not recommended):

```python
instance.use_oidc = True
instance.oidc_token_endpoint = "https://..."
instance.oidc_client_id = "client-id"
instance.oidc_client_secret = "encrypted-secret"
instance.oidc_username = "service-user"
instance.oidc_password = "encrypted-password"
```

### Custom Token Endpoint

Override discovery URL parsing:

```python
# nipyapi automatically derives token endpoint from discovery URL
# No manual override needed
```

## Files Modified

### Backend Files
- `app/core/config.py` - Added `OIDC_BACKEND_PROVIDER` setting
- `app/core/settings_manager.py` - Added `get_enabled_user_providers()` and `get_backend_provider()`
- `app/models/nifi_instance.py` - Added OIDC fields to model and schemas
- `app/services/nifi_auth.py` - Added OIDC authentication logic
- `app/api/oidc.py` - Updated to filter backend-only providers

### Configuration Files
- `config/oidc_providers.yaml` - Added `backend` field to providers
- `config/oidc_providers.yaml.example` - Added backend provider example and documentation

### Test Files
- `backend/test_oidc_backend.py` - Test script for OIDC configuration

## References

- [NiPyApi OIDC Support Documentation](NIPYAPI_OIDC_SUPPORT.md)
- [OIDC Setup Guide](OIDC_SETUP_GUIDE.md)
- [Keycloak Documentation](https://www.keycloak.org/docs/)
- [OAuth2 Client Credentials Flow](https://oauth.net/2/grant-types/client-credentials/)
- [NiFi OIDC Configuration](https://nifi.apache.org/docs/nifi-docs/html/administration-guide.html#openid_connect)
