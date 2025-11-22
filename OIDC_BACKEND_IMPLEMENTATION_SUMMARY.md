# OIDC Backend Authentication Implementation Summary

## Overview
Implemented OIDC authentication support for backend-to-NiFi connections, allowing the application to authenticate with NiFi instances using OAuth2/OIDC tokens instead of client certificates.

## Implementation Date
November 22, 2025

## Key Features

### 1. Backend-Only OIDC Providers
- Added `backend` field to OIDC provider configuration
- Providers marked with `backend: true` are used only for backend authentication
- Backend-only providers are automatically excluded from user login page
- Supports multiple backend providers for different environments

### 2. Global OIDC Configuration
- New environment variable: `OIDC_BACKEND_PROVIDER`
- When set, all NiFi instances use the specified OIDC provider for authentication
- Simplifies configuration for environments with multiple NiFi instances

### 3. Instance-Specific OIDC
- Added OIDC fields to NiFi instance model
- Supports per-instance OIDC configuration
- Allows mixed authentication methods (OIDC for some instances, certificates for others)

### 4. OAuth2 Flow Support
- **Client Credentials Flow** (recommended): Machine-to-machine authentication
- **Resource Owner Password Flow** (optional): User impersonation

## Files Modified

### Configuration Files
```
config/oidc_providers.yaml
config/oidc_providers.yaml.example
backend/.env.example (NEW)
```

### Backend Core
```
app/core/config.py
app/core/settings_manager.py
```

### Models
```
app/models/nifi_instance.py
  - Added: use_oidc, oidc_token_endpoint, oidc_client_id, 
           oidc_client_secret_encrypted, oidc_username, oidc_password_encrypted
```

### Services
```
app/services/nifi_auth.py
  - Enhanced: configure_nifi_connection() with OIDC support
  - Authentication priority: Instance OIDC → Global OIDC → Certificates → Username/Password
```

### API
```
app/api/oidc.py
  - Updated: get_oidc_providers() to filter backend-only providers
```

### Documentation (NEW)
```
OIDC_BACKEND_AUTHENTICATION.md - Complete setup guide
NIPYAPI_OIDC_SUPPORT.md - NiPyApi OIDC capabilities reference
backend/test_oidc_backend.py - Configuration validation script
```

## Database Schema Changes

### NiFi Instance Table (nifi_instances)
Added columns:
- `use_oidc` (BOOLEAN, default=False) - Enable OIDC for this instance
- `oidc_token_endpoint` (VARCHAR, nullable) - OIDC token endpoint URL
- `oidc_client_id` (VARCHAR, nullable) - OIDC client ID
- `oidc_client_secret_encrypted` (TEXT, nullable) - Encrypted OIDC client secret
- `oidc_username` (VARCHAR, nullable) - Optional username for Resource Owner Password flow
- `oidc_password_encrypted` (TEXT, nullable) - Optional encrypted password for Resource Owner Password flow

**Migration:** Auto-migration on app startup (SQLAlchemy creates new columns automatically)

## Configuration Examples

### 1. Global Backend OIDC Provider

**config/oidc_providers.yaml:**
```yaml
providers:
  nifi_backend:
    enabled: true
    backend: true  # Won't show on login page
    discovery_url: "https://keycloak:7443/realms/nifi/.well-known/openid-configuration"
    client_id: "nifi-backend-service"
    client_secret: "your-client-secret"
    redirect_uri: ""
    scopes:
      - openid
```

**backend/.env:**
```bash
OIDC_BACKEND_PROVIDER=nifi_backend
```

### 2. Instance-Specific OIDC

```python
instance = NiFiInstance(
    hierarchy_attribute="DC",
    hierarchy_value="DC1",
    nifi_url="https://nifi.example.com:8443/nifi-api",
    use_oidc=True,
    oidc_token_endpoint="https://keycloak:7443/realms/nifi/protocol/openid-connect/token",
    oidc_client_id="nifi-dc1-service",
    oidc_client_secret="encrypted-secret"
)
```

## Authentication Flow

### Priority Order
1. **Instance OIDC** - If `instance.use_oidc = True`
2. **Global OIDC** - If `OIDC_BACKEND_PROVIDER` is set
3. **Certificates** - If `instance.certificate_name` is set
4. **Username/Password** - If `instance.username` is set

### OIDC Authentication Process
```
1. Load OIDC configuration (from instance or global provider)
2. Decrypt client secret (if encrypted)
3. Call nipyapi.security.service_login_oidc()
   - Connects to OIDC token endpoint
   - Exchanges client credentials for access token
   - Sets bearer token for all NiFi API calls
4. Log authentication success/failure
```

## Testing

### Configuration Test
```bash
cd backend
python test_oidc_backend.py
```

### Expected Output
```
1. Environment Configuration: ✓
2. All OIDC Providers: ✓
3. User-Facing Providers: ✓
4. Backend Provider Configuration: ✓
5. Configuration Validation: ✓
```

### Manual Testing
1. Configure OIDC provider in `config/oidc_providers.yaml`
2. Set `OIDC_BACKEND_PROVIDER` in `.env`
3. Start backend: `python start.py`
4. Check logs for: "Successfully authenticated to NiFi using OIDC"
5. Test NiFi operations (flow deployment, monitoring, etc.)

## Security Considerations

### Secrets Management
- Client secrets are encrypted using Fernet encryption
- Encryption key stored in `SECRET_KEY` environment variable
- Database stores encrypted values only

### Best Practices
1. Use Client Credentials flow for backend (no user passwords)
2. Enable SSL verification (`verify_ssl=True`)
3. Use separate OIDC clients for user login vs. backend
4. Rotate credentials regularly
5. Monitor authentication logs
6. Configure minimal OIDC permissions

### Token Management
- OIDC tokens expire automatically
- nipyapi handles token refresh transparently
- No manual token management required

## Migration Path

### From Certificates to OIDC

**Phase 1: Setup (No Impact)**
1. Configure OIDC provider in `oidc_providers.yaml`
2. Don't set `OIDC_BACKEND_PROVIDER` yet
3. Test with single instance (`use_oidc=True`)

**Phase 2: Enable (Low Risk)**
1. Set `OIDC_BACKEND_PROVIDER` in `.env`
2. Restart backend
3. Test all NiFi operations
4. Monitor logs for issues

**Phase 3: Cleanup (Optional)**
1. Remove certificate configurations
2. Keep certificates as emergency fallback
3. Update documentation

## Troubleshooting

### Common Issues

**Provider Not Found**
- Check provider ID matches exactly (case-sensitive)
- Verify `enabled: true` is set
- Run `python test_oidc_backend.py`

**Authentication Failed**
- Verify client ID and secret are correct
- Check OIDC provider is accessible
- Verify NiFi is configured for OIDC
- Check SSL certificates (use `ca_cert_path` if needed)

**Backend Provider Shows on Login**
- Set `backend: true` in provider config
- Restart backend service
- Clear browser cache

### Debug Commands
```bash
# Test OIDC provider connectivity
curl -k https://keycloak:7443/realms/nifi/.well-known/openid-configuration

# Test token endpoint
curl -X POST https://keycloak:7443/realms/nifi/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=nifi-backend-service" \
  -d "client_secret=your-secret"

# Check backend logs
tail -f backend/logs/app.log | grep -i oidc
```

## Benefits Achieved

### Operational
- ✅ Centralized credential management
- ✅ No certificate file management
- ✅ Automatic token expiration and refresh
- ✅ Easier credential rotation

### Security
- ✅ Better audit logging via OIDC provider
- ✅ No long-lived credentials (tokens expire)
- ✅ Integration with corporate identity systems
- ✅ Encrypted secret storage

### Development
- ✅ Simpler authentication configuration
- ✅ Consistent authentication across instances
- ✅ Easy to test and validate
- ✅ Comprehensive documentation

## Next Steps

### Recommended Actions
1. **Document NiFi OIDC Setup** - Add NiFi-side OIDC configuration guide
2. **Create Keycloak Templates** - Provide ready-to-use Keycloak client configs
3. **Add Monitoring** - Track OIDC authentication metrics
4. **Performance Testing** - Measure OIDC vs. certificate performance
5. **UI Support** - Add OIDC fields to NiFi instance management UI

### Future Enhancements
- [ ] Support for OIDC token caching
- [ ] Multiple OIDC providers per instance
- [ ] OIDC provider health checks
- [ ] Automatic credential rotation
- [ ] OIDC authentication for NiFi Registry (when nipyapi supports it)

## Related Documentation

- [OIDC Backend Authentication Guide](OIDC_BACKEND_AUTHENTICATION.md) - Complete setup guide
- [NiPyApi OIDC Support](NIPYAPI_OIDC_SUPPORT.md) - Technical reference
- [OIDC Setup Guide](OIDC_SETUP_GUIDE.md) - User OIDC authentication
- [Session Timeout](SESSION_TIMEOUT.md) - Token expiration handling

## Support

For issues or questions:
1. Check [OIDC_BACKEND_AUTHENTICATION.md](OIDC_BACKEND_AUTHENTICATION.md) troubleshooting section
2. Run `python test_oidc_backend.py` for diagnostics
3. Review backend logs for authentication errors
4. Consult nipyapi documentation for OIDC support

---

**Implementation Status:** ✅ Complete and Tested
**Breaking Changes:** None (backward compatible)
**Deployment Impact:** Low (opt-in feature)
