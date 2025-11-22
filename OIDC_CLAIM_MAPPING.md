# NiFi OIDC Claim Mapping Guide

## The Problem

You're seeing username `4deaba29-3710-47de-8a2b-6c0158c40d03` (UUID) instead of `service-account-oidc`.

## Why This Happens

The OIDC token contains **multiple identity claims**:

```json
{
  "sub": "4deaba29-3710-47de-8a2b-6c0158c40d03",          ← UUID (subject)
  "azp": "oidc",                                          ← Client ID
  "preferred_username": "service-account-oidc",           ← Service account name
  "email": null,                                          ← Usually empty for service accounts
  "iss": "https://keycloak:7443/realms/oidc",            ← Issuer
  "aud": "account"                                        ← Audience
}
```

**NiFi must decide which claim to use as the username.**

## NiFi's Default Behavior

If `nifi.security.user.oidc.claim.identifying.user` is **NOT set**, NiFi uses the `sub` claim by default.

This is why you're seeing the UUID.

## The Solution

Tell NiFi to use `preferred_username` instead of `sub`.

### Add to `nifi.properties`:

```properties
nifi.security.user.oidc.claim.identifying.user=preferred_username
```

## Complete Configuration

Here's the full NiFi OIDC configuration you need:

```properties
# ============================================================================
# NiFi OIDC Configuration for Keycloak Service Account
# ============================================================================

# Discovery endpoint (MUST match token issuer hostname!)
nifi.security.user.oidc.discovery.url=https://keycloak:7443/realms/oidc/.well-known/openid-configuration

# Client credentials
nifi.security.user.oidc.client.id=oidc
nifi.security.user.oidc.client.secret=hOpFglgyuFLdb5N2nq6ZwkVbLYclhXnA

# Connection timeouts
nifi.security.user.oidc.connect.timeout=5 secs
nifi.security.user.oidc.read.timeout=5 secs

# ============================================================================
# CLAIM MAPPING (This is the critical setting!)
# ============================================================================
# Which token claim to use as the NiFi username
# Options:
#   - preferred_username (recommended for service accounts) → "service-account-oidc"
#   - email (for user accounts with email)                  → user@example.com
#   - sub (default if not specified)                        → UUID like 4deaba29-...
#
nifi.security.user.oidc.claim.identifying.user=preferred_username

# ============================================================================
# AUTHORIZATION
# ============================================================================
# Grant initial admin access to the service account
# This MUST match the value of the claim specified above
nifi.initial.admin.identity=service-account-oidc

# Optional: Additional scopes (not strictly needed for Client Credentials flow)
nifi.security.user.oidc.additional.scopes=email,profile
```

## Claim Mapping Options

| Property Value | Token Claim | Result | Use Case |
|----------------|-------------|--------|----------|
| `preferred_username` | `preferred_username` | `service-account-oidc` | ✅ **Service accounts (recommended)** |
| `email` | `email` | `user@example.com` | User accounts with email |
| `sub` | `sub` | `4deaba29-3710-47de-8a2b-6c0158c40d03` | ❌ UUID (not human-friendly) |
| `azp` | `azp` | `oidc` | Client ID as username |

## How to Verify

### Step 1: Update nifi.properties

Add the `claim.identifying.user` line as shown above.

### Step 2: Restart NiFi

```bash
# Docker
docker restart nifi

# Or native install
./bin/nifi.sh restart
```

### Step 3: Test Authentication

Run your OIDC test again from `http://localhost:3000/oidc-test`

### Step 4: Check NiFi Logs

**Before the fix:**
```bash
docker exec -it nifi tail logs/nifi-user.log
```

You'll see:
```
Attempting request for (4deaba29-3710-47de-8a2b-6c0158c40d03) GET ...
```

**After the fix:**
```
Attempting request for (service-account-oidc) GET ...
```

## Understanding Keycloak Service Accounts

When you use Client Credentials flow with Keycloak, the token represents a **service account**, not a human user.

Keycloak automatically creates a service account with:
- **Username**: `service-account-{client_id}`
- **Subject (sub)**: A UUID (unique identifier)
- **Email**: Usually empty

For your client ID `oidc`, Keycloak creates:
- `preferred_username`: `service-account-oidc` ✅ (use this!)
- `sub`: `4deaba29-3710-47de-8a2b-6c0158c40d03` (UUID)

## Why Not Use UUID?

While the `sub` claim (UUID) is technically valid, it's problematic:

1. ❌ **Not human-readable** - Hard to recognize in logs
2. ❌ **Hard to configure** - Must copy/paste UUID into nifi.properties
3. ❌ **Changes on reinstall** - If you recreate the service account, the UUID changes

Using `preferred_username` is better:
1. ✅ **Human-readable** - `service-account-oidc` is easy to recognize
2. ✅ **Predictable** - Always follows the pattern `service-account-{client_id}`
3. ✅ **Stable** - Doesn't change unless you rename the client

## Troubleshooting

### "No claim found for 'preferred_username'"

If NiFi logs show this error, it means the token doesn't contain a `preferred_username` claim.

**Check:**
1. Run the OIDC test and look at the token claims in the output
2. Verify that `preferred_username` appears in the list
3. If missing, check your Keycloak client configuration

### Username Still Shows UUID

If you still see the UUID after updating nifi.properties:

1. **Verify the change was saved** - Check the actual file on disk
2. **Restart NiFi** - Changes only take effect after restart
3. **Check for typos** - The property name must be exact: `nifi.security.user.oidc.claim.identifying.user`
4. **Check NiFi logs** - Look for errors about claim mapping

### "User is not authorized"

This means:
1. ✅ Authentication worked (NiFi accepted the token)
2. ✅ Username extraction worked (got `service-account-oidc`)
3. ❌ Authorization failed (user has no permissions)

**Fix:**
Update `nifi.initial.admin.identity` in nifi.properties:
```properties
nifi.initial.admin.identity=service-account-oidc
```

Then restart NiFi.

## Quick Reference

**Problem:** Username is UUID `4deaba29-3710-47de-8a2b-6c0158c40d03`

**Solution:** Add to nifi.properties:
```properties
nifi.security.user.oidc.claim.identifying.user=preferred_username
nifi.initial.admin.identity=service-account-oidc
```

**Restart NiFi**

**Result:** Username becomes `service-account-oidc` ✅

## Testing the Configuration

Use the enhanced OIDC test at `/oidc-test`:

1. The test will decode your token
2. Show all available claims
3. Recommend the best claim to use
4. Show the exact configuration needed

The test output will include:
```
📝 CLAIM MAPPING OPTIONS FOR NIFI:
   In nifi.properties, set one of these:

   nifi.security.user.oidc.claim.identifying.user=preferred_username
   → Username will be: service-account-oidc ✅ RECOMMENDED

   nifi.security.user.oidc.claim.identifying.user=sub
   → Username will be: 4deaba29-3710-47de-8a2b-6c0158c40d03 (UUID)
```

This makes it crystal clear which claim to use!
