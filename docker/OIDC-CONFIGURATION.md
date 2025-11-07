# OIDC Configuration for Docker Deployment

This guide explains how to configure OpenID Connect (OIDC) Single Sign-On for Datenschleuder when deployed with Docker Compose.

## 📋 Overview

The OIDC configuration file is mounted from the host into the Docker container, allowing you to:
- ✅ Configure OIDC providers without entering the container
- ✅ Update configuration with a simple file edit + restart
- ✅ Version control your OIDC settings
- ✅ Support multiple OIDC providers (Keycloak, Azure AD, Okta, etc.)

## 📁 Configuration File

**Location:** `docker/oidc_providers.yaml`

This file is mounted into the container at `/app/config/oidc_providers.yaml` (read-only).

### Initial Setup

1. **Copy the example file:**
   ```bash
   cd docker
   cp oidc_providers.yaml.example oidc_providers.yaml
   ```

2. **Edit the configuration:**
   ```bash
   nano oidc_providers.yaml
   # or
   vi oidc_providers.yaml
   ```

3. **Restart the application:**
   ```bash
   docker-compose restart datenschleuder
   ```

## 🔧 Configuration Structure

### Basic Configuration

```yaml
providers:
  corporate:
    enabled: true                    # Enable/disable this provider
    name: "Corporate SSO"            # Display name on login page
    description: "Sign in with your company account"
    icon: "building"                 # Icon to display
    display_order: 1                 # Order on login page
    
    # OIDC Discovery URL
    discovery_url: "https://idp.example.com/realms/my-realm/.well-known/openid-configuration"
    
    # OAuth Credentials
    client_id: "datenschleuder"
    client_secret: "your-client-secret-here"
    
    # Redirect URI (optional, auto-detected if omitted)
    redirect_uri: "http://localhost:3000/login/callback"
    
    # OAuth Scopes
    scopes:
      - openid
      - profile
      - email
    
    # Claim Mappings
    claim_mappings:
      username: "preferred_username"  # Required
      email: "email"
      name: "name"
    
    # User Provisioning
    auto_provision: true              # Auto-create users on first login
    default_role: "user"              # Role for new users: "user" or "admin"

global:
  allow_traditional_login: true       # Allow username/password login
  session_timeout: 480                # Session timeout in minutes
  auto_redirect_single_provider: false # Auto-redirect if only one provider
```

## 🔐 Provider-Specific Setup

### Keycloak

1. **Create a new client in Keycloak:**
   - Client Type: `OpenID Connect`
   - Client ID: `datenschleuder`
   - Client Authentication: `ON` (confidential)
   
2. **Configure redirect URIs:**
   ```
   http://localhost:3000/login/callback
   http://your-domain:3000/login/callback
   ```

3. **Get configuration from Keycloak:**
   - Discovery URL: `http(s)://{host}:{port}/realms/{realm}/.well-known/openid-configuration`
   - Client Secret: From Keycloak client "Credentials" tab

4. **Example configuration:**
   ```yaml
   providers:
     keycloak:
       enabled: true
       name: "Company SSO"
       discovery_url: "https://keycloak.company.com/realms/corporate/.well-known/openid-configuration"
       client_id: "datenschleuder"
       client_secret: "your-keycloak-client-secret"
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

### Azure AD (Microsoft Entra ID)

1. **Register app in Azure Portal:**
   - Navigate to Azure Active Directory > App registrations
   - Create new registration
   - Add redirect URI: `http://localhost:3000/login/callback`

2. **Create client secret:**
   - Go to "Certificates & secrets"
   - Create new client secret
   - Save the secret value

3. **Get configuration:**
   - Tenant ID: From "Overview" page
   - Application (client) ID: From "Overview" page
   - Discovery URL: `https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration`

4. **Example configuration:**
   ```yaml
   providers:
     azure:
       enabled: true
       name: "Microsoft Account"
       discovery_url: "https://login.microsoftonline.com/{your-tenant-id}/v2.0/.well-known/openid-configuration"
       client_id: "your-application-id"
       client_secret: "your-client-secret"
       scopes:
         - openid
         - profile
         - email
       claim_mappings:
         username: "email"
         email: "email"
         name: "name"
       auto_provision: true
       default_role: "user"
   ```

### Okta

1. **Create OIDC Application in Okta:**
   - Sign-in redirect URIs: `http://localhost:3000/login/callback`
   - Application type: Web Application
   - Grant types: Authorization Code

2. **Get configuration:**
   - Discovery URL: `https://{your-okta-domain}/.well-known/openid-configuration`
   - Client ID and Secret: From application settings

3. **Example configuration:**
   ```yaml
   providers:
     okta:
       enabled: true
       name: "Okta SSO"
       discovery_url: "https://your-domain.okta.com/.well-known/openid-configuration"
       client_id: "your-client-id"
       client_secret: "your-client-secret"
       scopes:
         - openid
         - profile
         - email
       claim_mappings:
         username: "email"
         email: "email"
         name: "name"
       auto_provision: true
       default_role: "user"
   ```

## 🔄 Updating Configuration

### 1. Edit the Configuration File

```bash
cd docker
nano oidc_providers.yaml
```

### 2. Validate YAML Syntax

```bash
# Install yq if not already installed
# macOS: brew install yq
# Linux: snap install yq

# Validate syntax
yq eval oidc_providers.yaml
```

### 3. Restart the Application

```bash
docker-compose restart datenschleuder
```

### 4. Verify Configuration

```bash
# Check logs for OIDC initialization
docker-compose logs datenschleuder | grep -i oidc

# Should see messages like:
# "Loading OIDC configuration from: /app/config/oidc_providers.yaml"
# "Loaded OIDC provider: corporate (enabled)"
```

## 🧪 Testing OIDC Configuration

### 1. Check OIDC Endpoints

```bash
# List available providers
curl http://localhost:8000/api/oidc/providers

# Should return:
# {
#   "providers": [
#     {
#       "id": "corporate",
#       "name": "Corporate SSO",
#       "description": "Sign in with your company account",
#       "icon": "building"
#     }
#   ],
#   "allow_traditional_login": true
# }
```

### 2. Test Authentication Flow

1. Navigate to: http://localhost:3000/login
2. You should see SSO provider button(s)
3. Click the provider button
4. You'll be redirected to your OIDC provider
5. After authentication, you'll be redirected back to Datenschleuder

### 3. Verify User Creation

```bash
# Check if user was created in database
docker-compose exec postgres psql -U postgres -d datenschleuder \
  -c "SELECT username, email, is_admin FROM users;"
```

## 🔒 Security Best Practices

### 1. Protect Client Secrets

**Never commit `oidc_providers.yaml` with real secrets to git!**

The file is in `.gitignore` by default. For production:

- Use environment variable substitution
- Use Docker secrets
- Use external secret management (Vault, AWS Secrets Manager)

### 2. Use HTTPS in Production

```yaml
providers:
  production:
    discovery_url: "https://idp.company.com/..."  # Always HTTPS
    redirect_uri: "https://datenschleuder.company.com/login/callback"
```

### 3. Restrict User Provisioning

```yaml
providers:
  corporate:
    auto_provision: true
    default_role: "user"          # Don't auto-create admins
    username_prefix: ""           # Optional: add prefix to usernames
```

### 4. Regular Token Rotation

- Rotate client secrets regularly
- Update OIDC configuration
- Restart application

## 🐛 Troubleshooting

### Configuration Not Loading

```bash
# Check if file is mounted correctly
docker-compose exec datenschleuder ls -la /app/config/

# Check file permissions
docker-compose exec datenschleuder cat /app/config/oidc_providers.yaml

# Check logs
docker-compose logs datenschleuder | grep -i oidc
```

### Provider Not Appearing on Login Page

1. **Check `enabled: true`** in configuration
2. **Verify YAML syntax** (no tabs, correct indentation)
3. **Restart container:** `docker-compose restart datenschleuder`
4. **Check API response:** `curl http://localhost:8000/api/oidc/providers`

### Authentication Fails

1. **Verify discovery URL** is accessible:
   ```bash
   curl https://your-idp.com/.well-known/openid-configuration
   ```

2. **Check redirect URI** matches exactly in both:
   - OIDC provider configuration
   - `oidc_providers.yaml`

3. **Verify client credentials** are correct

4. **Check container logs:**
   ```bash
   docker-compose logs -f datenschleuder
   ```

### Users Not Auto-Provisioned

1. **Check `auto_provision: true`**
2. **Verify claim mappings** match your provider's claims
3. **Check which claims are being received:**
   - Enable debug logging: `LOG_LEVEL=DEBUG` in `.env`
   - Check logs for claim information

### Multiple Providers Not Showing

```yaml
providers:
  provider1:
    enabled: true
    display_order: 1
  
  provider2:
    enabled: true
    display_order: 2
```

Make sure each provider has a unique name and is enabled.

## 📊 Monitoring

### View Current Configuration

```bash
# Show loaded OIDC configuration
docker-compose exec datenschleuder cat /app/config/oidc_providers.yaml

# Check API
curl http://localhost:8000/api/oidc/providers | jq
```

### Log Monitoring

```bash
# Follow OIDC-related logs
docker-compose logs -f datenschleuder | grep -i oidc

# Check authentication attempts
docker-compose logs -f datenschleuder | grep -i auth
```

## 🔄 Hot Reload

The application automatically reloads OIDC configuration on certain operations, but for immediate effect:

```bash
# Restart just the application (database stays running)
docker-compose restart datenschleuder
```

## 📚 Additional Resources

- [Main OIDC Documentation](../OIDC_SETUP_GUIDE.md)
- [OIDC Implementation Summary](../OIDC_IMPLEMENTATION_SUMMARY.md)
- [Docker Compose Guide](./DOCKER-COMPOSE.md)

## ❓ FAQ

**Q: Can I have multiple OIDC providers?**  
A: Yes, define multiple providers in the `providers:` section with different names.

**Q: Can I disable traditional login?**  
A: Yes, set `global.allow_traditional_login: false` to only allow SSO.

**Q: How do I update OIDC config without downtime?**  
A: Edit the file and restart the container. Downtime is minimal (few seconds).

**Q: Where are the client secrets stored?**  
A: In `oidc_providers.yaml` on the host, mounted read-only into the container.

**Q: Can I use environment variables for secrets?**  
A: Not directly in the YAML, but you can use docker-compose environment variable substitution in future versions.

**Q: What happens if OIDC provider is down?**  
A: Users can still login with traditional username/password if enabled.
