# OIDC Multi-Provider Authentication

## Overview

Datenschleuder now supports OpenID Connect (OIDC) Single Sign-On authentication with multiple identity providers. Users can authenticate using corporate SSO systems (Keycloak, Azure AD, Okta, etc.) while maintaining backward compatibility with traditional username/password authentication.

## Architecture

### Backend Components

1. **Configuration System** (`backend/config/oidc_providers.yaml`)
   - YAML-based provider configuration
   - Supports multiple identity providers
   - Per-provider settings (client credentials, scopes, claim mappings)
   - Global OIDC settings

2. **Settings Manager** (`backend/app/core/settings_manager.py`)
   - Loads and parses OIDC configuration
   - Provides methods to query providers and settings
   - Singleton pattern for application-wide access

3. **OIDC Service** (`backend/app/services/oidc_service.py`)
   - Discovery endpoint fetching and caching
   - JWKS (JSON Web Key Set) caching with 1-hour TTL
   - Token exchange (authorization code → tokens)
   - ID token verification using JWT
   - User data extraction with claim mappings
   - Automatic user provisioning

4. **API Endpoints** (`backend/app/api/oidc.py`)
   - `GET /auth/oidc/enabled` - Check if OIDC is enabled
   - `GET /auth/oidc/providers` - List available providers
   - `GET /auth/oidc/{provider_id}/login` - Initiate OAuth flow
   - `POST /auth/oidc/{provider_id}/callback` - Handle OAuth callback

### Frontend Components

1. **Login Page** (`frontend/src/pages/Login.vue`)
   - Fetches OIDC providers on mount
   - Displays provider buttons dynamically
   - Shows traditional login form conditionally
   - Initiates OAuth flow on provider selection

2. **Callback Handler** (`frontend/src/pages/OIDCCallback.vue`)
   - Handles OAuth redirect from identity provider
   - Validates state parameter (CSRF protection)
   - Exchanges authorization code for JWT token
   - Stores token and redirects to dashboard

## Setup Guide

### Prerequisites

1. **Python Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
   
   Required packages:
   - `httpx>=0.27.2` - Async HTTP client for OIDC requests
   - `python-jose[cryptography]==3.3.0` - JWT token verification
   - `PyYAML>=6.0.2` - YAML configuration parsing

2. **Identity Provider Configuration**
   
   You need an OpenID Connect identity provider (e.g., Keycloak, Azure AD, Okta).
   
   **Keycloak Setup Example:**
   - Create a new realm (e.g., `production`)
   - Create a new client (e.g., `datenschleuder`)
   - Set **Access Type** to `confidential`
   - Enable **Standard Flow** (Authorization Code Flow)
   - Add **Valid Redirect URIs**: `http://localhost:3000/login/callback`
   - Save and note the **Client ID** and **Client Secret**

### Configuration

1. **Edit OIDC Configuration**

   Open `backend/config/oidc_providers.yaml`:

   ```yaml
   providers:
     corporate:
       enabled: true  # Enable this provider
       name: "Corporate SSO"
       description: "Sign in with your company account"
       icon: "building"
       display_order: 1
       
       # Discovery URL - Replace with your provider's endpoint
       discovery_url: "https://keycloak.example.com/realms/production/.well-known/openid-configuration"
       
       # OAuth Credentials - From your identity provider
       client_id: "datenschleuder"
       client_secret: "your-client-secret-here"
       
       # Redirect URI - Must match provider configuration
       redirect_uri: "http://localhost:3000/login/callback"
       
       # OAuth Scopes
       scopes:
         - openid
         - profile
         - email
       
       # Claim Mappings - Map OIDC claims to user attributes
       claim_mappings:
         username: "preferred_username"
         email: "email"
         name: "name"
       
       # User Provisioning
       auto_provision: true
       default_role: "user"
       username_prefix: ""
   
   global:
     allow_traditional_login: true  # Allow username/password login
     session_timeout: 480
     auto_redirect_single_provider: false
   ```

2. **Environment Variables** (Optional)

   For production, use environment variables for secrets:
   
   ```bash
   export OIDC_CLIENT_SECRET="your-secret-here"
   ```
   
   Update the configuration to reference environment variables if needed.

### Testing

1. **Start Backend**
   ```bash
   cd backend
   python start.py
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test OIDC Flow**
   - Navigate to `http://localhost:3000/login`
   - You should see OIDC provider buttons
   - Click a provider button to initiate SSO
   - Complete authentication on identity provider
   - You should be redirected back and logged in

## Configuration Reference

### Provider Settings

| Setting | Required | Description |
|---------|----------|-------------|
| `enabled` | Yes | Enable/disable this provider |
| `name` | Yes | Display name on login page |
| `description` | No | Help text shown below button |
| `icon` | No | Icon identifier (building, flask, users, shield) |
| `display_order` | No | Sort order (lower = first) |
| `discovery_url` | Yes | OpenID Connect discovery endpoint |
| `client_id` | Yes | OAuth client identifier |
| `client_secret` | Yes | OAuth client secret |
| `redirect_uri` | Yes | Callback URL after authentication |
| `scopes` | No | OAuth scopes to request (default: openid, profile, email) |
| `claim_mappings` | No | Map OIDC claims to user attributes |
| `auto_provision` | No | Auto-create users on first login (default: false) |
| `default_role` | No | Default role for new users (user/admin) |
| `username_prefix` | No | Prefix for usernames to avoid conflicts |

### Global Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `allow_traditional_login` | `true` | Show username/password form |
| `session_timeout` | `480` | Session timeout in minutes |
| `auto_redirect_single_provider` | `false` | Skip provider selection if only one |

### Claim Mappings

Standard OIDC claims:
- `sub` - Subject identifier (unique user ID)
- `preferred_username` - Preferred username
- `email` - Email address
- `name` - Full name
- `given_name` - First name
- `family_name` - Last name
- `groups` - Group memberships (for future role mapping)

Example mapping:
```yaml
claim_mappings:
  username: "email"           # Use email as username
  email: "email"              # Email claim
  name: "name"                # Full name
  groups: "realm_access.roles" # Nested claim path
```

## Security Considerations

1. **State Parameter**
   - Each login request generates a unique state parameter
   - State includes provider ID to prevent provider confusion
   - Validated on callback to prevent CSRF attacks

2. **Token Verification**
   - ID tokens are verified using JWKS from provider
   - Signature, issuer, audience, and expiry are validated
   - Tokens are never trusted without verification

3. **JWKS Caching**
   - JWKS keys are cached per provider (1-hour TTL)
   - Reduces latency and provider load
   - Automatic refresh when cache expires

4. **Auto-Provisioning**
   - Disabled by default for security
   - Only creates users when explicitly enabled
   - Respects configured default roles

5. **Client Secrets**
   - Store secrets securely (environment variables in production)
   - Never commit secrets to version control
   - Rotate secrets regularly

## Troubleshooting

### Provider Not Showing on Login Page

1. Check `oidc_providers.yaml` - ensure `enabled: true`
2. Check backend logs for configuration errors
3. Verify YAML syntax is valid
4. Reload backend after configuration changes

### Authentication Fails

1. **Check Discovery URL**
   ```bash
   curl https://your-provider/.well-known/openid-configuration
   ```
   Should return JSON with endpoints

2. **Verify Client Credentials**
   - Client ID and secret must match provider configuration
   - Check for typos or whitespace

3. **Check Redirect URI**
   - Must match exactly (including protocol, port, path)
   - Configure in both provider and `oidc_providers.yaml`

4. **Review Backend Logs**
   - Check for token verification errors
   - Look for claim mapping issues
   - Verify user provisioning settings

### User Not Provisioned

1. Check `auto_provision: true` in provider config
2. Verify claim mappings match provider's claims
3. Check backend logs for provisioning errors
4. Ensure username claim is present in token

### Token Verification Fails

1. Check system clock synchronization (JWT exp/nbf)
2. Verify JWKS is accessible from backend
3. Check token signing algorithm (RS256, RS384, RS512)
4. Ensure audience (client_id) matches

## API Reference

### GET /auth/oidc/enabled

Check if OIDC authentication is enabled.

**Response:**
```json
{
  "enabled": true
}
```

### GET /auth/oidc/providers

Get list of available OIDC providers.

**Response:**
```json
{
  "providers": [
    {
      "provider_id": "corporate",
      "name": "Corporate SSO",
      "description": "Sign in with your company account",
      "icon": "building",
      "display_order": 1
    }
  ],
  "allow_traditional_login": true
}
```

### GET /auth/oidc/{provider_id}/login

Initiate OIDC authentication flow.

**Parameters:**
- `provider_id` (path) - Provider identifier
- `redirect_uri` (query, optional) - Override redirect URI

**Response:**
```json
{
  "authorization_url": "https://provider.com/auth?client_id=...",
  "state": "corporate:random_state_token",
  "provider_id": "corporate"
}
```

### POST /auth/oidc/{provider_id}/callback

Handle OAuth callback and complete authentication.

**Parameters:**
- `provider_id` (path) - Provider identifier

**Request Body:**
```json
{
  "code": "authorization_code_from_provider",
  "state": "corporate:random_state_token"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_for_application",
  "token_type": "bearer"
}
```

## Migration Guide

### Existing Users

- Existing username/password users continue to work
- No database migration required
- OIDC users are auto-provisioned with placeholder passwords
- OIDC users cannot use password authentication (by design)

### Deployment

1. **Development/Staging First**
   - Test OIDC with development provider
   - Verify all flows work correctly
   - Test user provisioning

2. **Production Rollout**
   - Keep `allow_traditional_login: true` initially
   - Add production provider configuration
   - Test with small group of users
   - Monitor logs for issues

3. **SSO-Only Mode** (Optional)
   - Set `allow_traditional_login: false`
   - All users must authenticate via OIDC
   - Ensure admin access via OIDC before disabling

## Support

For issues or questions:
1. Check backend logs (`app.services.oidc_service`, `app.api.oidc`)
2. Review provider's OIDC documentation
3. Verify configuration matches examples
4. Test discovery endpoint accessibility

## License

Same as Datenschleuder application.
