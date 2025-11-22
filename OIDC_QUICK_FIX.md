# OIDC Quick Fix - NiFi Rejecting Token

## Your Current Situation

✅ **Working:**
- OIDC token acquisition from Keycloak
- Token contains correct username: `service-account-oidc`
- Token issuer: `https://keycloak:7443/realms/oidc`

❌ **Not Working:**
- NiFi rejects the token with "Unable to view system diagnostics"
- No username appears in `nifi-user.log`

## Root Cause

**Token issuer mismatch** - The most common cause (99% of cases).

Your token says:
```
Issuer: https://keycloak:7443/realms/oidc
```

NiFi's configuration in `nifi.properties` probably says:
```properties
# Wrong - uses localhost instead of keycloak
nifi.security.user.oidc.discovery.url=https://localhost:7443/realms/oidc/.well-known/openid-configuration
```

**These MUST match!**

## The Fix

### Option 1: Update NiFi to Use 'keycloak' (Recommended)

**In `nifi.properties`:**
```properties
# Change from localhost to keycloak
nifi.security.user.oidc.discovery.url=https://keycloak:7443/realms/oidc/.well-known/openid-configuration
nifi.security.user.oidc.client.id=oidc
nifi.security.user.oidc.client.secret=hOpFglgyuFLdb5N2nq6ZwkVbLYclhXnA
nifi.security.user.oidc.claim.identifying.user=preferred_username
nifi.initial.admin.identity=service-account-oidc
```

**Ensure NiFi can reach Keycloak:**
```bash
# Test from NiFi container
docker exec -it nifi curl -k https://keycloak:7443/realms/oidc/.well-known/openid-configuration

# If this fails, add to Docker Compose or ensure containers are on same network
```

### Option 2: Update Keycloak to Use 'localhost'

**In Keycloak:**
1. Update realm settings to use `localhost` as hostname
2. Reconfigure issuer to be `https://localhost:7443/realms/oidc`

**In `config/oidc_providers.yaml`:**
```yaml
nifi_backend:
  discovery_url: "https://localhost:7443/realms/oidc/.well-known/openid-configuration"
  # ... rest of config
```

## Complete NiFi Configuration Checklist

**Required in `nifi.properties`:**

```properties
# 1. OIDC Discovery (MUST match token issuer hostname)
nifi.security.user.oidc.discovery.url=https://keycloak:7443/realms/oidc/.well-known/openid-configuration

# 2. Client credentials (same as in oidc_providers.yaml)
nifi.security.user.oidc.client.id=oidc
nifi.security.user.oidc.client.secret=hOpFglgyuFLdb5N2nq6ZwkVbLYclhXnA

# 3. Timeouts (optional)
nifi.security.user.oidc.connect.timeout=5 secs
nifi.security.user.oidc.read.timeout=5 secs

# 4. Which claim to use as username (CRITICAL!)
nifi.security.user.oidc.claim.identifying.user=preferred_username

# 5. Grant initial admin access
nifi.initial.admin.identity=service-account-oidc

# 6. Optional: Additional scopes
nifi.security.user.oidc.additional.scopes=email,profile
```

**After changing `nifi.properties`:**
```bash
# Restart NiFi
docker restart nifi
# or
./bin/nifi.sh restart
```

## Verify the Fix

### Step 1: Check NiFi Can Reach Keycloak

```bash
docker exec -it nifi curl -k https://keycloak:7443/realms/oidc/.well-known/openid-configuration
```

Should return JSON with `issuer`, `authorization_endpoint`, `jwks_uri`, etc.

### Step 2: Check NiFi Logs

**Before authentication attempt:**
```bash
# Watch NiFi logs in real-time
docker exec -it nifi tail -f logs/nifi-app.log
```

**Look for:**
- ✅ "Successfully retrieved OIDC configuration"
- ❌ "Unable to retrieve OIDC configuration" → Can't reach Keycloak
- ❌ "Unable to validate token" → Issuer mismatch

### Step 3: Test Authentication

Run the OIDC test again from your test UI or use nipyapi.

### Step 4: Check User Logs

```bash
# After successful authentication, you should see:
docker exec -it nifi tail -20 logs/nifi-user.log
```

Expected output:
```
2025-01-22 10:30:15,123 INFO [NiFi Web Server-123] o.a.n.w.s.NiFiAuthenticationFilter
Attempting request for (service-account-oidc) GET https://localhost:8443/nifi-api/system/diagnostics
```

**The username in parentheses confirms authentication is working!**

## Still Not Working?

### Enable NiFi OIDC Debug Logging

**Edit `conf/logback.xml`:**
```xml
<configuration>
  <!-- Existing configuration -->

  <!-- Add these lines before </configuration> -->
  <logger name="org.apache.nifi.web.security.oidc" level="DEBUG"/>
  <logger name="org.apache.nifi.web.security.jwt" level="DEBUG"/>
</configuration>
```

**Restart NiFi and check logs:**
```bash
docker exec -it nifi grep -i oidc logs/nifi-app.log | tail -50
```

### Common Error Messages

| Error in `nifi-app.log` | Cause | Fix |
|-------------------------|-------|-----|
| "Unable to validate token" | Issuer mismatch or can't fetch JWKS | Check hostname consistency |
| "Unable to retrieve OIDC configuration" | NiFi can't reach discovery URL | Fix networking/DNS |
| "No claim found for 'preferred_username'" | Token missing expected claim | Check token claims in test output |
| "User service-account-oidc is not authorized" | User has no permissions | Set `nifi.initial.admin.identity` |

## Docker Compose Example

If using Docker Compose, ensure NiFi and Keycloak are on the same network:

```yaml
version: '3.8'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: keycloak
    networks:
      - nifi-network
    ports:
      - "7443:7443"

  nifi:
    image: apache/nifi:latest
    container_name: nifi
    networks:
      - nifi-network
    ports:
      - "8443:8443"
    # NiFi can now reach Keycloak via hostname 'keycloak'

networks:
  nifi-network:
    driver: bridge
```

## Common Issue: Wrong Username (UUID Instead of service-account-oidc)

If you see a UUID like `4deaba29-3710-47de-8a2b-6c0158c40d03` in NiFi logs instead of `service-account-oidc`, NiFi is using the wrong claim.

**The Fix:**

Add this line to `nifi.properties`:
```properties
nifi.security.user.oidc.claim.identifying.user=preferred_username
```

This tells NiFi to use `preferred_username` claim (which contains `service-account-oidc`) instead of the default `sub` claim (which contains the UUID).

**Default Behavior:**
- If `nifi.security.user.oidc.claim.identifying.user` is NOT set, NiFi uses `sub` (the UUID)
- If set to `preferred_username`, NiFi uses the service account name

**After changing, restart NiFi.**

## Summary

1. ✅ **Token username identified**: `service-account-oidc`
2. ⚠️ **Issue #1**: NiFi rejects the token (likely issuer mismatch)
   - **Fix**: Update `nifi.properties` to use `https://keycloak:7443/...` (matching token issuer)
3. ⚠️ **Issue #2**: NiFi uses UUID instead of service-account-oidc
   - **Fix**: Set `nifi.security.user.oidc.claim.identifying.user=preferred_username`
4. 🔄 **Restart** NiFi
5. ✅ **Verify** in `nifi-user.log`

The username you need to grant permissions to in NiFi is: **`service-account-oidc`**
