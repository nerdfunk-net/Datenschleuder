# OIDC Backend Authentication - Quick Start

## 5-Minute Setup Guide

### Step 1: Configure OIDC Provider (2 min)

Edit `config/oidc_providers.yaml`:

```yaml
providers:
  nifi_backend:
    enabled: true
    backend: true  # Won't show on login page
    discovery_url: "https://YOUR-KEYCLOAK:7443/realms/nifi/.well-known/openid-configuration"
    client_id: "nifi-backend-service"
    client_secret: "YOUR-CLIENT-SECRET"
    redirect_uri: ""
    scopes:
      - openid
```

### Step 2: Enable Backend OIDC (1 min)

Edit `backend/.env`:

```bash
OIDC_BACKEND_PROVIDER=nifi_backend
```

### Step 3: Test Configuration (1 min)

```bash
cd backend
python test_oidc_backend.py
```

Expected: `✅ Configuration is valid`

### Step 4: Restart Backend (1 min)

```bash
cd backend
python start.py
```

Look for: `Successfully authenticated to NiFi using OIDC`

## Done! 🎉

All NiFi instances now use OIDC authentication automatically.

---

## Keycloak Client Setup

### Create Client
1. Go to Keycloak → **Clients** → **Create Client**
2. **Client ID**: `nifi-backend-service`
3. **Client Protocol**: `openid-connect`
4. Click **Next**

### Configure Client
1. **Access Type**: `confidential`
2. **Service Accounts Enabled**: `ON`
3. **Standard Flow**: `OFF`
4. **Direct Access Grants**: `OFF`
5. Click **Save**

### Get Secret
1. Go to **Credentials** tab
2. Copy **Client Secret**
3. Add to `oidc_providers.yaml`

### Configure Permissions
1. Go to **Service Account Roles** tab
2. Assign NiFi permissions

---

## Verify It's Working

### Check Logs
```bash
tail -f backend/logs/app.log | grep -i oidc
```

Expected:
```
INFO:app.services.nifi_auth:Using global OIDC backend provider: nifi_backend
INFO:app.services.nifi_auth:Successfully authenticated to NiFi using OIDC
```

### Test NiFi Connection
```bash
curl -X POST http://localhost:8000/api/nifi/check-connection \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Troubleshooting

### "Provider not found"
- Check provider ID: `nifi_backend` (case-sensitive)
- Verify `enabled: true`
- Run test script

### "Authentication failed"
- Verify client ID and secret
- Check discovery URL is accessible
- Ensure NiFi accepts OIDC tokens

### "Backend provider shows on login"
- Add `backend: true` to provider config
- Restart backend

---

## Full Documentation

- [Complete Setup Guide](OIDC_BACKEND_AUTHENTICATION.md)
- [NiPyApi OIDC Reference](NIPYAPI_OIDC_SUPPORT.md)
- [Implementation Summary](OIDC_BACKEND_IMPLEMENTATION_SUMMARY.md)

---

## Key Points

✅ **Backward Compatible** - Certificate auth still works  
✅ **Zero Code Changes** - Just configuration  
✅ **Auto Token Refresh** - No manual token management  
✅ **Centralized Auth** - One place to manage credentials  
✅ **Secure by Default** - Client secrets encrypted in DB  

---

**Need Help?** Check logs → Run test script → Review documentation
