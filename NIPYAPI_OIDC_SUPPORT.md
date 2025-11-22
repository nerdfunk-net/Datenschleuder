# NiPyApi OIDC Authentication Support

## Summary
**YES**, nipyapi **DOES support OIDC authentication** for connecting to NiFi instances. This can be used as an alternative to the current certificate-based authentication.

## Current Authentication Method
The application currently uses **client certificate authentication** (mTLS) to authenticate the backend with NiFi instances:
- Certificate files (CA cert, client cert, private key) are configured in `certificates.yaml`
- SSL context is created with client certificates
- Configured in `app/services/nifi_auth.py`

## Available OIDC Authentication in NiPyApi

### Method: `nipyapi.security.service_login_oidc()`

**Signature:**
```python
service_login_oidc(
    service="nifi",
    username=None,
    password=None,
    oidc_token_endpoint=None,
    client_id=None,
    client_secret=None,
    bool_response=False,
    return_token_info=False,
    verify_ssl=None
)
```

**Description:**
Login to NiFi using OpenID Connect (OIDC) OAuth2 authentication. Supports two OAuth2 flows:

1. **Resource Owner Password Credentials Flow** (when username/password provided)
   - Use when you have end-user credentials
   - Requires: `username`, `password`, `client_id`, `client_secret`, `oidc_token_endpoint`

2. **Client Credentials Flow** (when only client credentials provided)
   - Use for machine-to-machine authentication (recommended for backend-to-NiFi)
   - Requires: `client_id`, `client_secret`, `oidc_token_endpoint`

**Parameters:**
- `service`: 'nifi' (OIDC not supported for registry)
- `username`: Username for Resource Owner Password flow (optional)
- `password`: Password for Resource Owner Password flow (optional)
- `oidc_token_endpoint`: OIDC token endpoint URL (e.g., `http://keycloak:8080/realms/nifi/protocol/openid-connect/token`)
- `client_id`: OIDC client ID
- `client_secret`: OIDC client secret
- `bool_response`: Return False instead of raising exception on failure
- `return_token_info`: Return full OAuth2 token response
- `verify_ssl`: Whether to verify SSL certificates for OIDC endpoint

**Returns:**
- `True` on success (default)
- `False` if `bool_response=True` and authentication failed
- Full OAuth2 token response dict if `return_token_info=True`

### Helper Method: `set_service_auth_token()`

Used internally by `service_login_oidc()` to set the bearer token:

```python
set_service_auth_token(
    token=None,
    token_name="bearerAuth",
    service="nifi"
)
```

## Implementation Recommendations

### 1. For Backend-to-NiFi Authentication (Recommended: Client Credentials Flow)

**Why Client Credentials Flow:**
- More secure for machine-to-machine communication
- No need to store user passwords
- Better separation of concerns
- Simpler credential management

**Required Configuration:**
```python
oidc_token_endpoint = "https://keycloak:8080/realms/nifi/protocol/openid-connect/token"
client_id = "nifi-backend-client"
client_secret = "your-client-secret"

nipyapi.security.service_login_oidc(
    service="nifi",
    oidc_token_endpoint=oidc_token_endpoint,
    client_id=client_id,
    client_secret=client_secret,
    verify_ssl=True  # or False for self-signed certs
)
```

### 2. For User Impersonation (Resource Owner Password Flow)

If you need to authenticate as a specific user:

```python
nipyapi.security.service_login_oidc(
    service="nifi",
    username="user@example.com",
    password="user-password",
    oidc_token_endpoint=oidc_token_endpoint,
    client_id=client_id,
    client_secret=client_secret,
    verify_ssl=True
)
```

## Implementation Steps

### 1. Update NiFi Instance Model

Add OIDC configuration fields to `app/models/nifi_instance.py`:

```python
# Authentication method selector
auth_method = Column(String, default="certificate")  # "certificate", "oidc", "username_password"

# OIDC configuration fields
oidc_token_endpoint = Column(String, nullable=True)
oidc_client_id = Column(String, nullable=True)
oidc_client_secret_encrypted = Column(Text, nullable=True)
oidc_username = Column(String, nullable=True)  # Optional, for Resource Owner Password flow
oidc_password_encrypted = Column(Text, nullable=True)  # Optional, for Resource Owner Password flow
```

### 2. Update Authentication Service

Modify `app/services/nifi_auth.py` to support OIDC:

```python
def configure_nifi_connection(instance: NiFiInstance, normalize_url: bool = False) -> None:
    """Configure nipyapi connection for a NiFi instance."""
    
    # Configure base URL
    nifi_url = instance.nifi_url.rstrip("/")
    if normalize_url:
        if nifi_url.endswith("/nifi-api"):
            nifi_url = nifi_url[:-9]
        nifi_url = f"{nifi_url}/nifi-api"
    
    config.nifi_config.host = nifi_url
    config.nifi_config.verify_ssl = instance.verify_ssl
    
    if not instance.verify_ssl:
        nipyapi.config.disable_insecure_request_warnings = True
    
    # Authenticate based on method
    if instance.auth_method == "oidc":
        # OIDC authentication
        client_secret = None
        if instance.oidc_client_secret_encrypted:
            client_secret = encryption_service.decrypt_from_string(
                instance.oidc_client_secret_encrypted
            )
        
        # Check if using Resource Owner Password flow
        oidc_username = None
        oidc_password = None
        if instance.oidc_username and instance.oidc_password_encrypted:
            oidc_username = instance.oidc_username
            oidc_password = encryption_service.decrypt_from_string(
                instance.oidc_password_encrypted
            )
        
        security.service_login_oidc(
            service="nifi",
            username=oidc_username,
            password=oidc_password,
            oidc_token_endpoint=instance.oidc_token_endpoint,
            client_id=instance.oidc_client_id,
            client_secret=client_secret,
            verify_ssl=instance.verify_ssl
        )
        
    elif instance.auth_method == "certificate":
        # Existing certificate authentication
        # ... existing certificate code ...
        
    elif instance.auth_method == "username_password":
        # Existing username/password authentication
        # ... existing username/password code ...
```

### 3. Update API Endpoints

Modify `app/api/nifi.py` to support OIDC configuration in create/update endpoints:

```python
class NiFiInstanceCreate(BaseModel):
    hierarchy_attribute: str
    hierarchy_value: str
    nifi_url: str
    auth_method: str = "certificate"  # "certificate", "oidc", "username_password"
    
    # Certificate auth
    certificate_name: Optional[str] = None
    
    # Username/password auth
    username: Optional[str] = None
    password: Optional[str] = None
    
    # OIDC auth
    oidc_token_endpoint: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_username: Optional[str] = None  # Optional for Resource Owner Password flow
    oidc_password: Optional[str] = None  # Optional for Resource Owner Password flow
    
    use_ssl: bool = True
    verify_ssl: bool = True
    check_hostname: bool = True
```

### 4. Update Frontend

Add UI elements to configure OIDC authentication when creating/editing NiFi instances.

## Keycloak/OIDC Provider Configuration

### For Client Credentials Flow (Recommended)

1. Create a new client in Keycloak:
   - Client ID: `nifi-backend-client`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Service Accounts Enabled: `ON`
   - Standard Flow Enabled: `OFF`
   - Direct Access Grants Enabled: `OFF`

2. Configure client credentials:
   - Generate client secret
   - Configure service account roles/permissions

3. Token endpoint URL format:
   ```
   https://{keycloak-host}:{port}/realms/{realm-name}/protocol/openid-connect/token
   ```

### For Resource Owner Password Flow

1. Create a new client in Keycloak:
   - Client ID: `nifi-backend-client`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
   - Direct Access Grants Enabled: `ON`

2. Create user accounts with appropriate NiFi permissions

## Security Considerations

1. **Store secrets securely**: Encrypt `oidc_client_secret` using the existing `encryption_service`
2. **Token expiration**: OIDC tokens expire; nipyapi handles token refresh automatically
3. **Client Credentials vs Resource Owner Password**:
   - Client Credentials: Better for backend services (recommended)
   - Resource Owner Password: Use only if you need to impersonate specific users
4. **SSL verification**: Use `verify_ssl=True` in production
5. **Minimal permissions**: Configure OIDC clients with minimal required permissions

## Migration Path

1. **Phase 1**: Add OIDC support alongside existing certificate authentication
2. **Phase 2**: Test OIDC authentication with new NiFi instances
3. **Phase 3**: Migrate existing instances to OIDC (optional)
4. **Phase 4**: Keep certificate authentication as fallback option

## Benefits of OIDC Authentication

1. **Centralized authentication**: Single source of truth for credentials
2. **Better security**: Token-based authentication with automatic expiration
3. **Easier credential rotation**: Update secrets in OIDC provider without changing NiFi configuration
4. **Audit trail**: OIDC providers typically have better logging
5. **SSO integration**: Can integrate with corporate identity providers
6. **No certificate management**: No need to manage certificate files, expiration, etc.

## Limitations

1. OIDC authentication is **only supported for NiFi**, not NiFi Registry (nipyapi limitation)
2. Requires OIDC provider to be accessible from backend
3. Adds dependency on external OIDC provider availability

## Conclusion

NiPyApi fully supports OIDC authentication for NiFi connections through the `service_login_oidc()` method. The recommended approach is to use **Client Credentials flow** for backend-to-NiFi authentication as it's more secure and simpler to manage than certificates or username/password authentication.

Implementation would require:
1. Database schema updates to store OIDC configuration
2. Updates to authentication service to support OIDC login
3. API and frontend updates to configure OIDC settings
4. OIDC provider (Keycloak) configuration

The existing certificate-based authentication can remain as a fallback option during migration.
