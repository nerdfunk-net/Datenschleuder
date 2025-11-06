# OIDC Implementation - Quick Start

## What Was Implemented

✅ **Complete OIDC multi-provider authentication system**
- Backend: FastAPI with OIDC service, JWT verification, auto-provisioning
- Frontend: Vue 3 with provider buttons, callback handler
- Configuration: YAML-based provider management
- Security: State validation, token verification, JWKS caching

## Before You Can Test

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```
New dependency added: `httpx==0.27.2`

### 2. Configure an Identity Provider

You need an OpenID Connect provider. Example with Keycloak:

**Keycloak Setup:**
1. Create realm (e.g., `production`)
2. Create client (e.g., `datenschleuder`)
3. Set Access Type: `confidential`
4. Enable Standard Flow
5. Add Valid Redirect URI: `http://localhost:3000/login/callback`
6. Save and copy Client ID and Client Secret

**Other Providers:**
- Azure AD: Azure Portal → App Registrations
- Okta: Okta Admin → Applications
- Google: Google Cloud Console → OAuth 2.0

### 3. Update Configuration

Edit `backend/config/oidc_providers.yaml`:

```yaml
providers:
  corporate:
    enabled: true  # ← Set to true!
    name: "Corporate SSO"
    discovery_url: "https://YOUR-KEYCLOAK/realms/YOUR-REALM/.well-known/openid-configuration"
    client_id: "YOUR-CLIENT-ID"
    client_secret: "YOUR-CLIENT-SECRET"
    redirect_uri: "http://localhost:3000/login/callback"
    scopes:
      - openid
      - profile
      - email
    claim_mappings:
      username: "preferred_username"
      email: "email"
      name: "name"
    auto_provision: true
    default_role: "user"
```

### 4. Start Application

```bash
# Terminal 1 - Backend
cd backend
python start.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 5. Test

1. Go to http://localhost:3000/login
2. You should see your provider button (e.g., "Corporate SSO")
3. Click the button
4. Authenticate on your identity provider
5. You should be redirected back and logged in

## Files Changed

**Backend (7 new files):**
- `backend/config/oidc_providers.yaml` - Configuration
- `backend/app/core/settings_manager.py` - Settings manager
- `backend/app/services/oidc_service.py` - OIDC service
- `backend/app/models/oidc.py` - Pydantic models
- `backend/app/api/oidc.py` - API endpoints
- `backend/app/main.py` - Router registration (modified)
- `backend/requirements.txt` - Added httpx (modified)

**Frontend (3 files):**
- `frontend/src/pages/Login.vue` - OIDC support (modified)
- `frontend/src/pages/OIDCCallback.vue` - Callback handler (new)
- `frontend/src/router/index.ts` - Callback route (modified)

**Documentation:**
- `OIDC_SETUP_GUIDE.md` - Complete guide
- `OIDC_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `OIDC_QUICK_START.md` - This file

## API Endpoints

```
GET  /auth/oidc/enabled              Check if OIDC enabled
GET  /auth/oidc/providers            List providers
GET  /auth/oidc/{id}/login           Start OAuth flow
POST /auth/oidc/{id}/callback        Complete authentication
```

## Troubleshooting

**Provider not showing:**
- Check `enabled: true` in config
- Restart backend after config changes

**Authentication fails:**
- Verify discovery URL is accessible
- Check client_id and client_secret match
- Ensure redirect_uri matches exactly

**User not created:**
- Check `auto_provision: true`
- Verify claim_mappings match provider's claims
- Check backend logs for errors

## Key Features

- ✅ Multiple providers supported
- ✅ Traditional login still works (configurable)
- ✅ Automatic user provisioning
- ✅ CSRF protection with state parameter
- ✅ JWT token verification with JWKS
- ✅ Per-provider caching
- ✅ Flexible claim mappings

## Next Steps

1. **Configure provider** - Follow instructions above
2. **Test flow** - Complete authentication end-to-end
3. **Review logs** - Check for any errors
4. **Production setup** - See `OIDC_SETUP_GUIDE.md` for HTTPS, secrets management

## Need Help?

- Full setup guide: `OIDC_SETUP_GUIDE.md`
- Implementation details: `OIDC_IMPLEMENTATION_SUMMARY.md`
- Check backend logs for errors
- Verify discovery endpoint: `curl https://provider/.well-known/openid-configuration`
