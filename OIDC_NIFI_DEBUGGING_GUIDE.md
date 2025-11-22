# OIDC NiFi Authentication Debugging Guide

This guide helps you debug OIDC authentication between your application (using nipyapi) and NiFi.

## Problem: No Username Appearing in NiFi Logs

When using OIDC authentication with NiFi via nipyapi, you may not see any username in `nifi-user.log`. This is usually due to one of the following issues:

### 1. Token Not Being Accepted by NiFi

**Symptoms:**
- Authentication seems to succeed in your application
- No entries in `nifi-user.log`
- API calls to NiFi fail with 401 Unauthorized

**Common Causes:**

#### A. Issuer Mismatch
NiFi validates that the token's issuer (`iss` claim) matches the discovery URL configured in `nifi.properties`.

**Check:**
```bash
# In your backend logs, look for the token issuer
# Example: "Issuer: https://keycloak:7443/realms/oidc"

# In nifi.properties, check this matches:
nifi.security.user.oidc.discovery.url=https://keycloak:7443/realms/oidc/.well-known/openid-configuration
```

**Critical:** The hostname MUST match exactly:
- ❌ Token issuer: `https://localhost:7443/realms/oidc`
- ❌ NiFi discovery: `https://keycloak:7443/realms/oidc/.well-known/openid-configuration`
- ✅ Both should use `keycloak` OR both should use `localhost`

#### B. NiFi Cannot Reach Keycloak to Fetch JWKS

NiFi needs to fetch the public keys from Keycloak to validate the JWT signature.

**Test from NiFi's perspective:**
```bash
# SSH into the NiFi container/host
curl -k https://keycloak:7443/realms/oidc/.well-known/openid-configuration

# Should return JSON with jwks_uri, authorization_endpoint, etc.
```

If this fails, NiFi cannot validate tokens. Fix networking/DNS issues.

#### C. NiFi OIDC Not Properly Configured

**Check `nifi.properties`:**
```properties
# Required settings for OIDC
nifi.security.user.oidc.discovery.url=https://keycloak:7443/realms/oidc/.well-known/openid-configuration
nifi.security.user.oidc.connect.timeout=5 secs
nifi.security.user.oidc.read.timeout=5 secs
nifi.security.user.oidc.client.id=oidc
nifi.security.user.oidc.client.secret=hOpFglgyuFLdb5N2nq6ZwkVbLYclhXnA

# Which claim to use as username (critical!)
nifi.security.user.oidc.claim.identifying.user=preferred_username

# Optional: Additional scopes
nifi.security.user.oidc.additional.scopes=email,profile
```

**Important:** `nifi.security.user.oidc.claim.identifying.user` determines which claim becomes the username in NiFi.

### 2. Determining the Correct Username

The username NiFi uses depends on the `nifi.security.user.oidc.claim.identifying.user` property.

#### Step 1: Use the Enhanced Debugging

Run the OIDC test to see all token claims:

1. Navigate to: `http://localhost:3000/oidc-test` (or your frontend URL)
2. Select **Test Type**: "Backend NiFi OIDC Authentication"
3. Select **OIDC Provider**: "NiPyAPI [Backend]" (or your backend provider)
4. Fill in **NiFi URL**: `https://localhost:8443/nifi-api`
5. Click **Test Backend Auth**

**In the test results**, you'll see:
```
🔍 NIFI USERNAME FOR AUTHORIZATION: service-account-oidc
💡 Grant permissions in NiFi to this exact username
```

#### Step 2: Check Backend Logs

In your backend console, look for the detailed token breakdown:

```
======================================================================
OIDC Token Identity (What NiFi will see):
======================================================================
  - Subject (sub): 12345678-1234-1234-1234-123456789abc
  - Client ID (azp/client_id): oidc
  - Preferred Username: service-account-oidc
  - Email: N/A
  - Name: N/A
  - Issuer: https://keycloak:7443/realms/oidc
  - Audience (aud): account

🔍 NIFI USERNAME TO USE FOR AUTHORIZATION:
   >>> service-account-oidc <<<

💡 In NiFi, grant permissions to this exact username:
   Initial Admin Identity: service-account-oidc
   Or add to User Groups with appropriate policies
```

### 3. Common Username Claim Options

Depending on `nifi.security.user.oidc.claim.identifying.user` in `nifi.properties`:

| Property Value | Token Claim | Example Username | When to Use |
|----------------|-------------|------------------|-------------|
| `preferred_username` | `preferred_username` | `service-account-oidc` | **Default for Keycloak service accounts** |
| `email` | `email` | `user@example.com` | User accounts with email |
| `sub` | `sub` | `12345678-1234-...` | UUID-based identity |
| `azp` | `azp` | `oidc` | Client ID as username |
| `client_id` | `client_id` | `oidc` | Alternative client ID claim |

**For Client Credentials flow (service accounts)**, use `preferred_username` - this is typically `service-account-{client_id}`.

### 4. Granting Permissions in NiFi

Once you know the username, grant it permissions in NiFi:

#### Option A: Initial Admin Identity (Easiest for Testing)

**In `nifi.properties`:**
```properties
# Set this to the username from the token
nifi.security.user.oidc.claim.identifying.user=preferred_username

# Grant initial admin access to the service account
nifi.security.user.oidc.truststore.strategy=
nifi.initial.admin.identity=service-account-oidc
```

**Restart NiFi** after making these changes.

#### Option B: Add to User Groups (Production)

1. Log into NiFi UI as admin
2. Go to **Menu** (☰) → **Users**
3. Click **Add User**
4. Enter the exact username: `service-account-oidc`
5. Add user to appropriate groups or grant specific policies

### 5. Debugging Checklist

Run through this checklist systematically:

- [ ] **Test OIDC configuration** using the test UI (`/oidc-test`)
- [ ] **Verify token claims** in backend logs (look for "OIDC Token Identity")
- [ ] **Note the username** shown in "NIFI USERNAME TO USE FOR AUTHORIZATION"
- [ ] **Check hostname consistency** (token issuer vs NiFi discovery URL)
- [ ] **Verify NiFi can reach Keycloak** (test JWKS endpoint from NiFi host)
- [ ] **Confirm nifi.properties OIDC settings** are correct
- [ ] **Set correct claim mapping** (`nifi.security.user.oidc.claim.identifying.user`)
- [ ] **Grant permissions** to the exact username (Initial Admin Identity or User Groups)
- [ ] **Restart NiFi** after configuration changes
- [ ] **Check `nifi-user.log`** for authentication entries
- [ ] **Check `nifi-app.log`** for OIDC errors

### 6. Checking NiFi Logs

**`logs/nifi-user.log`** - Authentication events:
```
2025-01-22 10:30:15,123 INFO [NiFi Web Server-123] o.a.n.w.s.NiFiAuthenticationFilter Attempting request for (service-account-oidc) GET https://localhost:8443/nifi-api/system/diagnostics
```

If you see this, authentication is working! The username in parentheses is what was extracted from the token.

**`logs/nifi-app.log`** - Errors and debugging:
```
# Look for OIDC-related errors:
grep -i oidc logs/nifi-app.log

# Common errors:
# - "Unable to validate token" → Issuer mismatch or JWKS fetch failure
# - "Unable to retrieve OIDC configuration" → NiFi can't reach discovery URL
# - "No claim found" → The claim specified in nifi.properties doesn't exist in token
```

### 7. Enable NiFi OIDC Debug Logging

Add to `conf/logback.xml`:

```xml
<logger name="org.apache.nifi.web.security.oidc" level="DEBUG"/>
<logger name="org.apache.nifi.web.security.jwt" level="DEBUG"/>
```

Restart NiFi, then check `logs/nifi-app.log` for detailed OIDC validation steps.

### 8. Quick Test Script

To quickly test if your OIDC setup is working:

```bash
cd backend
python test_oidc_backend.py
```

This will:
- Load your OIDC provider configuration
- Validate all settings
- Show which providers are configured
- Identify the backend provider

## Example: Keycloak Service Account Setup

For the `nifi_backend` provider in your config:

1. **In Keycloak** (realm: `oidc`):
   - Client ID: `oidc`
   - Access Type: `confidential`
   - Service Accounts Enabled: `ON`
   - Standard Flow: `OFF` (not needed for backend)
   - Valid Redirect URIs: `https://localhost:8443/nifi-api/access/oidc/callback`

2. **In your application** (`config/oidc_providers.yaml`):
   ```yaml
   nifi_backend:
     enabled: true
     backend: true
     discovery_url: "https://keycloak:7443/realms/oidc/.well-known/openid-configuration"
     client_id: "oidc"
     client_secret: "hOpFglgyuFLdb5N2nq6ZwkVbLYclhXnA"
   ```

3. **In NiFi** (`nifi.properties`):
   ```properties
   nifi.security.user.oidc.discovery.url=https://keycloak:7443/realms/oidc/.well-known/openid-configuration
   nifi.security.user.oidc.client.id=oidc
   nifi.security.user.oidc.client.secret=hOpFglgyuFLdb5N2nq6ZwkVbLYclhXnA
   nifi.security.user.oidc.claim.identifying.user=preferred_username
   nifi.initial.admin.identity=service-account-oidc
   ```

4. **Restart NiFi**

5. **Test** using the OIDC test UI or backend logs

## Still Not Working?

If you've followed all steps and it's still not working:

1. **Capture the actual token**:
   - Look in backend logs for "Set Bearer token in Authorization header"
   - Copy the token (it's the part after "Bearer ")
   - Decode it at https://jwt.io to see all claims

2. **Compare claim names**:
   - Check which claim NiFi is looking for (`nifi.security.user.oidc.claim.identifying.user`)
   - Verify that exact claim exists in your token
   - Check for typos (e.g., `preferredUsername` vs `preferred_username`)

3. **Check network connectivity**:
   - From NiFi container: `curl -k https://keycloak:7443/realms/oidc/.well-known/openid-configuration`
   - From your backend: `curl -k https://keycloak:7443/realms/oidc/protocol/openid-connect/token`

4. **Verify certificate trust**:
   - If using self-signed certs, ensure NiFi trusts the Keycloak CA
   - Check `nifi.security.truststore.*` properties

## Summary

The most common issue is that **NiFi's `nifi.security.user.oidc.claim.identifying.user` doesn't match a claim in your token**.

Use the enhanced debugging (test UI + backend logs) to see exactly what claims are in your token, then configure NiFi to use the right one.
